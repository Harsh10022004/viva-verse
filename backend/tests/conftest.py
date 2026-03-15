import pytest
from fastapi.testclient import TestClient

from main import app
from app.services.llm_service import SBERTSingleton

# Create a mock SBERT model for fast tests without downloading large ML models
class MockEncoder:
    def encode(self, texts, convert_to_numpy=True):
        import numpy as np
        res = []
        for t in texts:
            if "Medieval" in t:
                res.append(np.array([1.0, 0.0, 0.0] * 128))
            elif "Python" in t:
                res.append(np.array([0.0, 1.0, 0.0] * 128))
            elif "gradients" in t:
                # Dot product with populations is 128, norm is sqrt(256)=16. 128/256 = 0.5 similarity
                res.append(np.array([1.0, 1.0, 0.0] * 128))
            elif "populations" in t:
                res.append(np.array([1.0, 0.0, 1.0] * 128))
            else:
                res.append(np.ones(384))
        return np.array(res)

@pytest.fixture(scope="session", autouse=True)
def mock_sbert():
    # Force the SBERTSingleton to use our MockEncoder
    instance = SBERTSingleton()
    instance._model = MockEncoder()

@pytest.fixture
def client():
    return TestClient(app)
