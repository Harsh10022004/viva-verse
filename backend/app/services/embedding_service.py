import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Load the model once globally (lazy loading can also be done, but this is fine for backend startup)
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer model: {e}")
    model = None

def generate_embedding(text: str) -> List[float]:
    """Generate a vector embedding for a single text string via SBERT."""
    if not text or not text.strip() or model is None:
        return []
    try:
        embedding = model.encode(text.strip())
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings for a list of text strings."""
    if not texts or model is None:
        return []
    try:
        embeddings = model.encode([t.strip() for t in texts])
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        return []
