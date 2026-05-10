import logging
import re
import random
from typing import List, Dict, Optional
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from app.utils.constants import STOPWORDS

logger = logging.getLogger(__name__)

class SBERTSingleton:
    """Loads the SBERT model exactly once and reuses it globally."""
    _instance: Optional["SBERTSingleton"] = None
    _model: Optional[SentenceTransformer] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("[INFO] Loading SBERT model (all-MiniLM-L6-v2) …")
            cls._model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("[SUCCESS] SBERT model loaded.")
        return cls._instance

    def encode(self, texts: List[str]) -> np.ndarray:
        return self._model.encode(texts, convert_to_numpy=True)

class GeminiQGSingleton:
    """Uses Google Gemini API for highly accurate, dynamic question formulation."""
    _instance: Optional["GeminiQGSingleton"] = None
    _client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            try:
                from google import genai
                from dotenv import load_dotenv
                import os
                
                load_dotenv(override=True)
                # Initialize the client with explicit api_key
                api_key = os.environ.get("GEMINI_API_KEY")
                if not api_key:
                    logger.error("[ERROR] GEMINI_API_KEY is not set in the environment.")
                cls._client = genai.Client(api_key=api_key)
                logger.info("[SUCCESS] Gemini API Client initialized.")
            except ImportError:
                logger.error("[ERROR] google-genai or python-dotenv library is missing.")
            except Exception as e:
                logger.error(f"[ERROR] Failed to initialize Gemini Client: {str(e)}")
        return cls._instance

    def generate_questions_batch(self, cluster_contexts: List[str]) -> List[str]:
        """Generates all questions in a single API call to bypass strict Free Tier rate limits."""
        if not self._client:
            logger.error("[ERROR] Gemini Client is not initialized.")
            return ["Could you explain the main idea of this section?"] * len(cluster_contexts)
            
        prompt = "You are an expert viva examiner. I will provide you with several distinct semantic clusters from a document.\n"
        prompt += f"For EACH of the {len(cluster_contexts)} clusters, you must generate a single, highly accurate, comprehensive, and conceptual question.\n"
        prompt += "The question should require the user to synthesize and analyze the main ideas across that entire section.\n"
        prompt += "Output your response as a strictly valid JSON array of strings, containing exactly one question per cluster in the same order. Do not include markdown formatting or extra text.\n"
        prompt += "Example Output: [\"What is the core idea of cluster 0?\", \"How does cluster 1 affect the system?\"]\n\n"
        
        for i, ctx in enumerate(cluster_contexts):
            prompt += f"Cluster {i}:\n{ctx}\n\n"

        max_retries = 3
        import time
        import json
        import re
        for attempt in range(max_retries):
            try:
                response = self._client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                raw_text = response.text.strip()
                
                # Extract and parse JSON array
                match = re.search(r'\[.*\]', raw_text, re.DOTALL)
                if match:
                    parsed_json = json.loads(match.group(0))
                else:
                    parsed_json = json.loads(raw_text)
                    
                if isinstance(parsed_json, list):
                    questions = [str(q).strip() for q in parsed_json]
                else:
                    questions = []
                
                # Fallback if the LLM didn't return enough questions
                if len(questions) < len(cluster_contexts):
                    logger.warning(f"[WARNING] Batch generation length mismatch. Expected {len(cluster_contexts)}, got {len(questions)}")
                    while len(questions) < len(cluster_contexts):
                        questions.append("Based on the text, what do you think is the most critical implication of this concept?")
                
                return questions[:len(cluster_contexts)]
                
            except json.JSONDecodeError:
                err_str = "Failed to parse JSON array from Gemini response."
                logger.error(f"[ERROR] {err_str} Raw text: {raw_text[:100]}...")
            except Exception as e:
                err_str = str(e)
                if "429" in err_str and attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)
                    logger.warning(f"[WARNING] Rate limit hit on Batch Request. Waiting {wait_time} seconds before retry {attempt+1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                logger.error(f"[ERROR] Gemini batch generation failed. Exception: {err_str}")
                
            # If we fall through the except block but have retries left, we wait a bit and retry
            if attempt < max_retries - 1:
                time.sleep(5)
                
        # If all retries failed
        return ["Based on the text, what do you think is the most critical implication of this concept?"] * len(cluster_contexts)


def _check_verbatim_copy(answer: str, source_chunk: str) -> float:
    """Return a ratio (0-1) of how much of the answer is directly copied."""
    answer_words = answer.lower().split()
    source_lower = source_chunk.lower()
    if len(answer_words) < 3:
        return 0.0
    window_size = min(5, len(answer_words))
    matches = 0
    total_windows = max(1, len(answer_words) - window_size + 1)
    for i in range(total_windows):
        window = " ".join(answer_words[i:i + window_size])
        if window in source_lower:
            matches += 1
    return matches / total_windows


def _find_uncovered_aspects(answer: str, source_chunk: str, model: SBERTSingleton) -> List[str]:
    """
    Find which semantic aspects of the source material the answer didn't cover.
    Splits the source into sentence-level ideas and checks semantic coverage.
    """
    sentences = re.split(r'[.!?]+', source_chunk)
    sentences = [s.strip() for s in sentences if len(s.strip().split()) > 5]
    if not sentences:
        return []

    # Encode answer and all source sentences
    all_texts = [answer] + sentences
    embeddings = model.encode(all_texts)
    answer_emb = embeddings[0]
    sentence_embs = embeddings[1:]

    # Find which source sentences are NOT well-covered by the answer
    uncovered = []
    for i, sent in enumerate(sentences):
        sim = float(cosine_similarity([answer_emb], [sentence_embs[i]])[0][0])
        if sim < 0.35:  # this idea was not addressed
            # Extract the core idea from this sentence
            words = re.findall(r'[A-Za-z]+', sent.lower())
            meaningful = [w for w in words if w not in STOPWORDS and len(w) > 3]
            if len(meaningful) >= 2:
                idea = ' '.join(meaningful[:4])
                uncovered.append(idea)

    return uncovered[:3]


def _generate_human_critique(
    score: float,
    question: str,
    answer: str,
    source_chunk: str,
    question_relevance: float,
    source_coverage: float,
    copy_ratio: float,
    model: SBERTSingleton,
    intent: str = "",
    topic: str = "",
) -> str:
    """
    Generate natural, mentor-like feedback that's specific to the question
    and answer. Feels like a real examiner's commentary.
    """
    parts = []

    if score >= 75 and copy_ratio < 0.25:
        openers = [
            f"Well articulated! Your understanding of {topic} comes through clearly.",
            f"Solid response - you've captured the essence of what the material covers regarding {topic}.",
            f"Good depth here. You clearly grasp the core ideas around {topic}.",
        ]
        parts.append(random.choice(openers))
    elif score >= 55:
        openers = [
            f"You're on the right track with {topic}, though your answer could go deeper.",
            f"A reasonable start - you've touched on the surface of {topic}, but there's more to unpack.",
            f"You show a basic understanding of {topic}, but an examiner would expect more depth.",
        ]
        parts.append(random.choice(openers))
    elif score >= 35:
        openers = [
            f"Your answer shows only a partial grasp of {topic}.",
            f"There are gaps in your understanding of {topic} that need attention.",
            f"This answer doesn't fully demonstrate comprehension of {topic}.",
        ]
        parts.append(random.choice(openers))
    else:
        openers = [
            f"Your response doesn't adequately address the question about {topic}.",
            f"This answer misses the core ideas around {topic} that were expected.",
            f"The connection between your answer and {topic} is unclear.",
        ]
        parts.append(random.choice(openers))

    if copy_ratio > 0.5:
        parts.append(
            "However, it appears you've reproduced text directly from the source. "
            "In a viva, the examiner wants to hear the concept in your own words to confirm genuine understanding."
        )
    elif copy_ratio > 0.25:
        parts.append(
            "Some portions seem to be taken directly from the document. "
            "Try to rephrase the ideas to show you truly understand them, not just recall them."
        )

    if question_relevance < 0.3:
        parts.append(
            "Your answer seems to discuss something different from what was asked. "
            "Before answering, take a moment to re-read the question and ensure your response is targeted."
        )
    elif question_relevance < 0.45:
        parts.append(
            "While your answer contains relevant information, it doesn't directly address the specific angle the question is probing."
        )

    uncovered = _find_uncovered_aspects(answer, source_chunk, model)
    if uncovered and score < 80:
        if len(uncovered) == 1:
            parts.append(
                f"You might want to explore the aspect of {uncovered[0]} in your answer - "
                "the document discusses this in a way that's relevant to the question."
            )
        else:
            aspects = " and ".join([uncovered[0], uncovered[1]])
            parts.append(
                f"Consider also discussing {aspects} - "
                "these are important threads in the source material that would strengthen your response."
            )

    if score < 70:
        intent_hints = {
            "explain": "When explaining a concept, try to break it down into simpler components and show how they connect.",
            "analyze": "For analysis questions, go beyond description - discuss the 'why' and 'how', not just the 'what'.",
            "apply": "Practical application questions work best when you provide a concrete scenario or example.",
            "compare": "When comparing, explicitly mention similarities and differences, and explain what they mean.",
            "evaluate": "Critical evaluation requires you to weigh pros and cons, and form a reasoned judgment.",
            "synthesize": "Synthesis means connecting multiple ideas together - show how different parts relate to each other.",
        }
        if intent in intent_hints:
            parts.append(intent_hints[intent])

    if score >= 75 and copy_ratio < 0.25:
        parts.append("Keep this quality up!")
    elif score >= 55:
        parts.append("With more depth and specificity, this could be a strong answer.")
    elif score < 35:
        parts.append("Review the relevant section of the document and try to understand the main ideas before answering.")

    return " ".join(parts)


def _check_question_echo(answer: str, question: str) -> float:
    """Return a ratio (0-1) of how much the answer overlaps with the question vocabulary."""
    import re
    from app.utils.constants import STOPWORDS
    
    ans_words = set([w for w in re.findall(r'[a-z]+', answer.lower()) if w not in STOPWORDS and len(w) > 3])
    q_words = set([w for w in re.findall(r'[a-z]+', question.lower()) if w not in STOPWORDS and len(w) > 3])
    
    if not ans_words or not q_words:
        return 0.0
        
    overlap = len(ans_words.intersection(q_words))
    # If the answer mostly consists of words from the question, ratio is high
    echo_ratio = overlap / len(ans_words) 
    return echo_ratio

def evaluate_answer(
    answer: str, question: str, source_chunk: str,
    model: SBERTSingleton, intent: str = "", topic: str = ""
) -> Dict:
    """
    Essence-based semantic evaluation.
    """
    logger.info("[INFO] Execution Started: evaluate_answer")
    if not answer.strip():
        logger.warning("[WARNING] Empty answer provided.")
        return {"score": 0, "critique": "No content was provided. Answering the question is required in a viva examination."}

    ideal_proxy = f"{question} {source_chunk}"

    embeddings = model.encode([answer, question, source_chunk, ideal_proxy])
    ans_emb = embeddings[0]
    q_emb = embeddings[1]
    src_emb = embeddings[2]
    ideal_emb = embeddings[3]

    ideal_sim = float(cosine_similarity([ans_emb], [ideal_emb])[0][0])
    question_relevance = float(cosine_similarity([ans_emb], [q_emb])[0][0])
    source_coverage = float(cosine_similarity([ans_emb], [src_emb])[0][0])

    copy_ratio = _check_verbatim_copy(answer, source_chunk)
    echo_ratio = _check_question_echo(answer, question)

    raw_score = (
        ideal_sim * 0.50 +
        question_relevance * 0.25 +
        source_coverage * 0.25
    ) * 100

    raw_score = min(100, raw_score * 1.3)

    # Severe penalty for just repeating the question
    if echo_ratio > 0.7 or (question_relevance > 0.9 and source_coverage < 0.4):
        penalty = 0.2 # 80% reduction
        raw_score *= penalty
        logger.info(f"[INFO] Applied question echo penalty. Echo Ratio: {echo_ratio}")

    if copy_ratio > 0.5:
        penalty = 0.35 + (0.65 * (1 - copy_ratio))
        raw_score *= penalty
    elif copy_ratio > 0.25:
        penalty = 0.65 + (0.35 * (1 - copy_ratio))
        raw_score *= penalty

    score = round(min(100, max(0, raw_score)), 1)
    logger.info(f"[SUCCESS] Answer Evaluated with Score: {score}")

    critique = _generate_human_critique(
        score, question, answer, source_chunk,
        question_relevance, source_coverage, copy_ratio,
        model, intent, topic,
    )

    return {"score": score, "critique": critique}
