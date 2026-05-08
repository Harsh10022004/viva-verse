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
        self.pdf_paths: Dict[str, str] = {}
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
    
    # Simple heuristics to identify noisy pages
    noisy_patterns = [
        r"(?i)\b(table of contents|contents|index|acknowledgement)\b",
        r"(?i)^([0-9]+\s*\.*){3,}" # ToC dot leaders
    ]
    
    for p in pages:
        text = p["text"]
        
        # Check if page is mostly ToC or Acknowledgements
        if any(re.search(pat, text[:500]) for pat in noisy_patterns) and len(text.split()) < 300:
            continue # Skip this page
            
        words = text.split()
        for start in range(0, len(words), max_words):
            chunk = " ".join(words[start : start + max_words])
            # Extra noise filtering on chunk level: drop if it's too small or seems like an index
            if len(chunk.split()) > 20: 
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


def _cluster_semantic_chunks(store: "DocumentStore", num: int = 6) -> List[Dict]:
    """
    Groups chunks into `num` semantic clusters using K-Means on their embeddings.
    Returns a list of dicts: {"indices": [int], "best_idx": int}
    """
    from sklearn.cluster import KMeans
    
    total = len(store.chunks)
    if total <= num:
        return [{"indices": [i], "best_idx": i} for i in range(total)]

    embeddings = store.embeddings
    
    # Run K-Means clustering
    kmeans = KMeans(n_clusters=num, random_state=42, n_init=10)
    labels = kmeans.fit_predict(embeddings)
    
    # Calculate richness to find the "best" representative chunk per cluster
    richness_scores = []
    for chunk in store.chunks:
        words = re.findall(r'[A-Za-z]+', chunk.lower())
        meaningful = [w for w in words if w not in STOPWORDS and len(w) > 3]
        unique_ratio = len(set(meaningful)) / max(len(meaningful), 1)
        richness_scores.append(len(meaningful) * unique_ratio)
    
    richness = np.array(richness_scores)
    richness = richness / max(richness.max(), 1)  # normalize

    clusters = []
    for i in range(num):
        indices = np.where(labels == i)[0].tolist()
        if not indices:
            continue
            
        # Find the most semantically rich chunks in this cluster
        cluster_richness = richness[indices]
        sorted_local = np.argsort(cluster_richness)[::-1]
        best_local = int(sorted_local[0])
        best_idx = indices[best_local]
        
        # Take the top 3 most information-dense chunks
        top_3_indices = [indices[idx] for idx in sorted_local[:3]]
        
        clusters.append({
            "cluster_id": i,
            "indices": indices, # All indices for final shading
            "best_idx": best_idx,
            "top_3_indices": top_3_indices # Subset for LLM context
        })

    return clusters


def generate_questions(store: "DocumentStore", num: int = 6) -> List[Dict]:
    logger.info(f"[INFO] Generating {num} questions from semantic clusters.")
    if len(store.chunks) == 0:
        logger.warning("[WARNING] No chunks in DocumentStore.")
        return []

    clusters = _cluster_semantic_chunks(store, num)

    from app.services.llm_service import GeminiQGSingleton
    qg_model = GeminiQGSingleton()

    # Collect all cluster contexts for batch generation
    cluster_contexts = []
    for cluster in clusters:
        top_3_indices = cluster["top_3_indices"]
        cluster_text_parts = [store.chunks[idx] for idx in top_3_indices]
        full_cluster_text = " ".join(cluster_text_parts)
        words = full_cluster_text.split()
        if len(words) > 1000:
            full_cluster_text = " ".join(words[:1000])
        cluster_contexts.append(full_cluster_text)

    # Make ONE single API call to generate all questions
    logger.info("[INFO] Sending batch request to Gemini...")
    generated_questions = qg_model.generate_questions_batch(cluster_contexts)

    questions = []
    for i, cluster in enumerate(clusters):
        indices = cluster["indices"]
        best_idx = cluster["best_idx"]
        
        chunk_label = store.chunk_labels[best_idx]
        topic = _summarize_chunk_topic(store.chunks[best_idx]).strip('.,;:!?')
        
        question_text = generated_questions[i] if i < len(generated_questions) else "Could you explain this topic?"

        questions.append({
            "id": str(uuid.uuid4()),
            "question": question_text,
            "source_chunk_index": best_idx, # fallback backward compat
            "cluster_indices": indices, # ALL chunks in this cluster for highlighting
            "cluster_text": cluster_contexts[i], # The context block
            "intent": "conceptual",
            "topic": topic,
            "context_label": chunk_label,
        })

    logger.info(f"[SUCCESS] Questions Generated ({len(questions)} items).")
    return questions
