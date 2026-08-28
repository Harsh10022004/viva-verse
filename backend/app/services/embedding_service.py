import logging
import os
from typing import List

logger = logging.getLogger(__name__)

def generate_embedding(text: str) -> List[float]:
    """Generate a vector embedding for a single text string via Gemini API."""
    if not text or not text.strip():
        return []
    try:
        from google import genai
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text.strip(),
            config={"output_dimensionality": 768}
        )
        return list(result.embeddings[0].values)
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return []

def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate vector embeddings for a list of text strings."""
    if not texts:
        return []
    return [generate_embedding(t) for t in texts]
