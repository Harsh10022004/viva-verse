import logging
import random
import uuid
import numpy as np
from typing import Dict, List, Optional
from sklearn.metrics.pairwise import cosine_similarity

from app.services.parser_service import DocumentStore, _extract_topic_phrases, _summarize_chunk_topic
from app.services.llm_service import evaluate_answer, SBERTSingleton
from app.utils.constants import QUESTION_TYPES

logger = logging.getLogger(__name__)

class KnowledgeMapperAgent:
    """Maintains the student's understanding state across the entire document."""
    
    def __init__(self, store: DocumentStore):
        self.store = store
        self.total_chunks = len(store.chunks)
        # scores: 0-100 (initially None meaning unassessed)
        self.scores: List[Optional[float]] = [None] * self.total_chunks
        self.model = SBERTSingleton()
        logger.info(f"[Agent] KnowledgeMapper initialized with {self.total_chunks} chunks.")

    def update_score(self, chunk_index: int, score: float):
        """Update the score for a specific chunk and infer scores for similar chunks."""
        self.scores[chunk_index] = score
        
        # Propagate knowledge to semantically similar chunks
        # If student scores 90 on Chunk A, and Chunk B is 80% similar, we infer a base understanding for B.
        if self.store.embeddings is not None:
            target_emb = self.store.embeddings[chunk_index]
            sims = cosine_similarity([target_emb], self.store.embeddings)[0]
            
            for i, sim in enumerate(sims):
                if i != chunk_index and sim > 0.85: # Increased semantic threshold for propagation
                    inferred_score = score * (sim ** 2) # Penalize inferred score slightly
                    
                    # Only update if unassessed, or if the inferred score is significantly different/better
                    current = self.scores[i]
                    if current is None:
                        self.scores[i] = inferred_score
                    else:
                        # Blend the scores, leaning towards direct assessment if it exists
                        self.scores[i] = (current * 0.7) + (inferred_score * 0.3)

    def get_weakest_unknown_chunk(self, exclude_chunks: set) -> int:
        """Find the most important chunk that hasn't been assessed yet."""
        unassessed = [i for i, s in enumerate(self.scores) if s is None and i not in exclude_chunks]
        if not unassessed:
            # If all are assessed, find the lowest score that wasn't asked
            assessed_not_asked = [i for i in range(self.total_chunks) if i not in exclude_chunks]
            if assessed_not_asked:
                return min(assessed_not_asked, key=lambda i: self.scores[i] if self.scores[i] is not None else 100)
            else:
                return random.choice(range(self.total_chunks))
            
        # For simplicity, pick a random unassessed chunk, but could be enhanced to pick the most central one
        return random.choice(unassessed)

    def get_coverage_percentage(self) -> float:
        """Return percentage of document assessed."""
        assessed = sum(1 for s in self.scores if s is not None)
        return (assessed / self.total_chunks) * 100 if self.total_chunks > 0 else 100

    def get_knowledge_map(self) -> List[Dict]:
        """Return the complete mapped document for UI shading."""
        res = []
        for i in range(self.total_chunks):
            s = self.scores[i]
            if s is None:
                color = "unassessed" # Gray
            elif s >= 75:
                color = "strong"     # Green
            elif s >= 45:
                color = "partial"    # Yellow
            else:
                color = "weak"       # Red
                
            res.append({
                "index": i,
                "text": self.store.chunks[i],
                "label": self.store.chunk_labels[i],
                "score": round(s, 1) if s is not None else None,
                "status": color
            })
        return res

class InterrogatorAgent:
    """Generates targeted questions based on the KnowledgeMapper's target chunk."""
    
    def __init__(self, store: DocumentStore):
        self.store = store
        from app.services.llm_service import GeminiQGSingleton
        self.qg_model = GeminiQGSingleton()
        
    def generate_question(self, chunk_index: int) -> Dict:
        chunk = self.store.chunks[chunk_index]
        chunk_label = self.store.chunk_labels[chunk_index]
        
        # Use batch method with a single-element list
        question_text = self.qg_model.generate_questions_batch([chunk])[0]

        # Still extract core sentence as a simple "topic" for the evaluation agent context
        core_sentence = _summarize_chunk_topic(chunk).strip('.,;:!?')
        topic = core_sentence

        logger.info(f"[Agent] Interrogator generated question for chunk {chunk_index}.")
        return {
            "id": str(uuid.uuid4()),
            "question": question_text,
            "source_chunk_index": chunk_index,
            "intent": "conceptual",
            "topic": topic,
            "context_label": chunk_label,
        }

class EvaluatorAgent:
    """Wraps the existing evaluation logic."""
    
    def __init__(self, model: SBERTSingleton):
        self.model = model
        
    def evaluate(self, answer: str, question: str, source_chunk: str, intent: str, topic: str) -> Dict:
        return evaluate_answer(answer, question, source_chunk, self.model, intent, topic)

class SupervisorAgent:
    """Orchestrates the Viva Session."""
    
    def __init__(self, store: DocumentStore, max_questions: int = 10):
        self.store = store
        self.mapper = KnowledgeMapperAgent(store)
        self.interrogator = InterrogatorAgent(store)
        self.evaluator = EvaluatorAgent(self.mapper.model)
        self.max_questions = max_questions
        self.questions_asked = 0
        self.history = []
        self.asked_chunks = set()

    def get_next_action(self) -> Dict:
        """Determine what to do next: Ask question or Complete."""
        coverage = self.mapper.get_coverage_percentage()
        logger.info(f"[Agent] Supervisor checking state. Coverage: {coverage}%. Asked: {self.questions_asked}/{self.max_questions}")
        
        if self.questions_asked >= self.max_questions or coverage > 95:
            return {
                "action": "complete",
                "knowledge_map": self.mapper.get_knowledge_map(),
                "history": self.history
            }
            
        target_chunk_idx = self.mapper.get_weakest_unknown_chunk(self.asked_chunks)
        self.asked_chunks.add(target_chunk_idx)
        
        question_data = self.interrogator.generate_question(target_chunk_idx)
        self.questions_asked += 1
        
        return {
            "action": "ask",
            "question": question_data
        }

    def process_answer(self, answer: str, question_data: Dict) -> Dict:
        """Process the student's answer, update map, and return grade."""
        chunk_idx = question_data["source_chunk_index"]
        source_chunk = self.store.chunks[chunk_idx]
        
        result = self.evaluator.evaluate(
            answer=answer,
            question=question_data["question"],
            source_chunk=source_chunk,
            intent=question_data["intent"],
            topic=question_data["topic"]
        )
        
        self.mapper.update_score(chunk_idx, result["score"])
        
        log_entry = {
            "question": question_data["question"],
            "answer": answer,
            "score": result["score"],
            "critique": result["critique"]
        }
        self.history.append(log_entry)
        
        return result
