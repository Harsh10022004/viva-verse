import logging
import uuid
import re
import random
from typing import List, Dict, Optional
from io import BytesIO
import numpy as np

from PyPDF2 import PdfReader
from sklearn.metrics.pairwise import cosine_similarity

from app.services.llm_service import SBERTSingleton
from app.utils.constants import STOPWORDS, QUESTION_TYPES

logger = logging.getLogger(__name__)

class DocumentStore:
    """Holds text chunks and their SBERT embeddings for semantic retrieval."""

    def __init__(self):
        self.chunks: List[str] = []
        self.chunk_labels: List[str] = []
        self.embeddings: Optional[np.ndarray] = None
        self.model = SBERTSingleton()

    def add_chunks(self, chunks: List[str], labels: List[str]):
        logger.info(f"[INFO] Adding {len(chunks)} chunks to DocumentStore.")
        self.chunks.extend(chunks)
        self.chunk_labels.extend(labels)
        self.embeddings = self.model.encode(self.chunks)
        logger.info("[SUCCESS] Chunks embedded successfully.")

    def get_context(self, query: str, top_k: int = 3) -> List[Dict]:
        if self.embeddings is None or len(self.chunks) == 0:
            return []
        query_emb = self.model.encode([query])
        sims = cosine_similarity(query_emb, self.embeddings)[0]
        top_indices = np.argsort(sims)[::-1][:top_k]
        return [
            {"index": int(i), "text": self.chunks[i], "score": float(sims[i]), "label": self.chunk_labels[i]}
            for i in top_indices
        ]


def extract_text_from_pdf(file_bytes: bytes) -> List[Dict]:
    """Returns a list of {page, text} dicts from a PDF."""
    logger.info("[INFO] Parsing Started for a PDF file.")
    reader = PdfReader(BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({"page": i + 1, "text": text.strip()})
    logger.info(f"[SUCCESS] Extracted text from {len(pages)} pages.")
    return pages


def chunk_text(pages: List[Dict], max_words: int = 200) -> tuple[List[str], List[str]]:
    """Split page texts into semantic chunks of ~max_words words."""
    chunks: List[str] = []
    labels: List[str] = []
    for p in pages:
        words = p["text"].split()
        for start in range(0, len(words), max_words):
            chunk = " ".join(words[start : start + max_words])
            if len(chunk.split()) > 15:           # ignore tiny fragments
                chunks.append(chunk)
                labels.append(f"Page {p['page']}")
    return chunks, labels


def _summarize_chunk_topic(chunk: str) -> str:
    sentences = re.split(r'[.!?]+', chunk)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) > 5]

    if not sentences:
        return chunk[:200]

    best_sentence = ""
    best_density = 0
    for sent in sentences:
        words = re.findall(r'[A-Za-z]+', sent.lower())
        meaningful = [w for w in words if w not in STOPWORDS and len(w) > 3]
        density = len(meaningful) / max(len(words), 1)
        if density > best_density and len(meaningful) >= 3:
            best_density = density
            best_sentence = sent
    return best_sentence or sentences[0]


def _extract_topic_phrases(chunk: str) -> List[str]:
    words = chunk.split()
    meaningful_words = []
    for w in words:
        clean = re.sub(r'[^A-Za-z]', '', w).lower()
        if clean and clean not in STOPWORDS and len(clean) > 3:
            meaningful_words.append(clean)

    phrases = []
    current_phrase = []
    for i, word in enumerate(words):
        clean = re.sub(r'[^A-Za-z]', '', word).lower()
        if clean and clean not in STOPWORDS and len(clean) > 3:
            current_phrase.append(word.strip('.,;:!?()[]'))
            if len(current_phrase) >= 2:
                phrases.append(' '.join(current_phrase[-3:]))
        else:
            if len(current_phrase) >= 2:
                phrases.append(' '.join(current_phrase))
            current_phrase = []
    if len(current_phrase) >= 2:
        phrases.append(' '.join(current_phrase))

    seen = set()
    unique_phrases = []
    for p in phrases:
        p_lower = p.lower()
        if p_lower not in seen and 2 <= len(p.split()) <= 5:
            seen.add(p_lower)
            unique_phrases.append(p)

    return unique_phrases[:10]


def _select_diverse_chunks(store: "DocumentStore", num: int = 6) -> List[int]:
    total = len(store.chunks)
    if total <= num:
        return list(range(total))

    embeddings = store.embeddings
    mean_emb = np.mean(embeddings, axis=0, keepdims=True)
    dist_from_mean = 1 - cosine_similarity(embeddings, mean_emb).flatten()

    richness_scores = []
    for chunk in store.chunks:
        words = re.findall(r'[A-Za-z]+', chunk.lower())
        meaningful = [w for w in words if w not in STOPWORDS and len(w) > 3]
        unique_ratio = len(set(meaningful)) / max(len(meaningful), 1)
        richness_scores.append(len(meaningful) * unique_ratio)
    richness = np.array(richness_scores)
    richness = richness / max(richness.max(), 1)  # normalize

    importance = dist_from_mean * 0.4 + richness * 0.6

    selected = [int(np.argmax(importance))]
    for _ in range(num - 1):
        remaining = [i for i in range(total) if i not in selected]
        if not remaining:
            break
        best_idx = -1
        best_score = -1
        for i in remaining:
            sims_to_selected = cosine_similarity(
                [embeddings[i]], [embeddings[j] for j in selected]
            )[0]
            min_sim = float(np.max(sims_to_selected))
            diversity_score = (1 - min_sim) * 0.6 + importance[i] * 0.4
            if diversity_score > best_score:
                best_score = diversity_score
                best_idx = i
        if best_idx >= 0:
            selected.append(best_idx)

    selected.sort()
    return selected


def generate_questions(store: "DocumentStore", num: int = 6) -> List[Dict]:
    logger.info(f"[INFO] Generating {num} questions from document chunks.")
    if len(store.chunks) == 0:
        logger.warning("[WARNING] No chunks in DocumentStore.")
        return []

    selected_indices = _select_diverse_chunks(store, num)

    questions = []
    used_intents = set()

    for idx in selected_indices[:num]:
        chunk = store.chunks[idx]

        topic_phrases = _extract_topic_phrases(chunk)
        core_sentence = _summarize_chunk_topic(chunk)

        if topic_phrases:
            topic = topic_phrases[0]
        else:
            topic = ' '.join(core_sentence.split()[:8])

        available_intents = [i for i in range(len(QUESTION_TYPES)) if i not in used_intents]
        if not available_intents:
            available_intents = list(range(len(QUESTION_TYPES)))
        intent_idx = random.choice(available_intents)
        used_intents.add(intent_idx)

        q_type = QUESTION_TYPES[intent_idx]
        template = random.choice(q_type["templates"])
        question_text = template.format(topic=topic)

        questions.append({
            "id": str(uuid.uuid4()),
            "question": question_text,
            "source_chunk_index": idx,
            "intent": q_type["intent"],
            "topic": topic,
        })

    logger.info(f"[SUCCESS] Questions Generated ({len(questions)} items).")
    return questions
