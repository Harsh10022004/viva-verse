import os
import json
import numpy as np
import faiss
import logging
from typing import List, Dict, Any, Tuple
from app.database import SessionLocal
from app.database_models import InterviewQuestion

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, dimension: int = 384):
        # 384 is default for all-MiniLM-L6-v2
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension) # Inner product for cosine similarity (assuming normalized vectors)
        self.id_map = {} # Maps FAISS internal index ID to question UUID
        self.uuid_to_index = {} # Maps question UUID to FAISS internal index ID
        self.is_initialized = False

    def initialize(self):
        """Load all embeddings from SQLite into FAISS on startup."""
        if self.is_initialized:
            return

        db = SessionLocal()
        try:
            questions = db.query(InterviewQuestion).filter(InterviewQuestion.embedding.isnot(None)).all()
            if not questions:
                self.is_initialized = True
                return

            vectors = []
            for q in questions:
                try:
                    vec = json.loads(q.embedding)
                    if len(vec) == self.dimension:
                        # Normalize vector for cosine similarity with IndexFlatIP
                        v = np.array(vec, dtype=np.float32)
                        faiss.normalize_L2(v.reshape(1, -1))
                        vectors.append(v)
                        idx = len(self.id_map)
                        self.id_map[idx] = q.id
                        self.uuid_to_index[q.id] = idx
                except Exception as e:
                    logger.warning(f"Failed to load embedding for question {q.id}: {e}")

            if vectors:
                vectors_np = np.vstack(vectors)
                self.index.add(vectors_np)
                logger.info(f"[FAISS] Loaded {self.index.ntotal} vectors into index.")

            self.is_initialized = True
        finally:
            db.close()

    def add_embedding(self, question_id: str, vector: List[float]):
        """Add a single embedding to the index."""
        if len(vector) != self.dimension:
            logger.warning(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(vector)}")
            return

        v = np.array(vector, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(v)
        
        self.index.add(v)
        idx = self.index.ntotal - 1
        self.id_map[idx] = question_id
        self.uuid_to_index[question_id] = idx

    def search(self, query_vector: List[float], top_k: int = 100) -> List[Tuple[str, float]]:
        """Search the index and return list of (question_id, score)."""
        if not self.is_initialized or self.index.ntotal == 0:
            return []

        if len(query_vector) != self.dimension:
            return []

        v = np.array(query_vector, dtype=np.float32).reshape(1, -1)
        faiss.normalize_L2(v)

        # Search
        search_k = min(self.index.ntotal, top_k * 2) 
        scores, indices = self.index.search(v, search_k)
        
        results = []
        seen = set()
        
        for i in range(search_k):
            idx = int(indices[0][i])
            if idx == -1:
                break
            score = float(scores[0][i])
            q_id = self.id_map.get(idx)
            if q_id and q_id not in seen:
                results.append((q_id, score))
                seen.add(q_id)
                
            if len(results) >= top_k:
                break
                
        return results

# Global singleton
vector_store = VectorStore()
