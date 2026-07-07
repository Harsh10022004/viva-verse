from unittest.mock import patch
from main import app

def test_coach_test_key_empty(client):
    res = client.post("/api/v1/coach/test-key", json={"provider": "google", "api_key": ""})
    assert res.status_code == 400

@patch("app.api.v1.coach_routes.test_api_key_sync")
def test_coach_test_key_success(mock_test, client):
    mock_test.return_value = {"status": "success", "message": "Verified BYOK"}
    res = client.post("/api/v1/coach/test-key", json={"provider": "google", "api_key": "dummy_key"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"

@patch("app.api.v1.coach_routes.call_llm_sync")
def test_coach_init_success(mock_call, client):
    mock_call.return_value = {"status": "success", "content": "Welcome to Viva-Verse Behavioral Q1", "tokens": 42}
    payload = {
        "provider": "google",
        "api_key": "dummy_key",
        "mode": "behavioral",
        "role": "Product Manager",
        "level": "Senior"
    }
    res = client.post("/api/v1/coach/init", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "Welcome to Viva-Verse" in data["initial_message"]
    assert data["tokens"] == 42

@patch("app.api.v1.coach_routes.call_llm_sync")
def test_coach_scorecard(mock_call, client):
    mock_call.return_value = {"status": "success", "content": "## Scorecard 50/50", "tokens": 15}
    payload = {
        "provider": "google",
        "api_key": "dummy_key",
        "messages": [{"role": "user", "content": "hello"}],
        "elapsed": "02:30",
        "question_num": 3
    }
    res = client.post("/api/v1/coach/scorecard", json=payload)
    assert res.status_code == 200
    assert res.json()["content"] == "## Scorecard 50/50"
