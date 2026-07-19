import logging
from typing import List, Union

logger = logging.getLogger(__name__)

# Lazy load model to avoid slow startup if not used
_model = None

def _get_model():
    global _model
    if _model is None:
        logger.info("[INFO] Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def generate_embedding(text: str) -> List[float]:
    """Generate a vector embedding for a single text string."""
    if not text or not text.strip():
        return []
    
    try:
        model = _get_model()
        embedding = model.encode(text.strip())
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings for a list of text strings."""
    if not texts:
        return []
    
    try:
        model = _get_model()
        embeddings = model.encode([t.strip() for t in texts])
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.error(f"Error generating batch embeddings: {e}")
        return []
