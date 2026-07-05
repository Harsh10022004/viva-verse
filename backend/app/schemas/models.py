from pydantic import BaseModel
from typing import Dict, List, Optional

class ConfirmUploadRequest(BaseModel):
    upload_id: str
    priorities: Dict[str, List[str]]

class StartVivaRequest(BaseModel):
    mode: Optional[str] = "quick" # 'quick' or 'comprehensive'
    num_questions: Optional[int] = 6
    api_key: Optional[str] = None
    provider: Optional[str] = "google"
    model: Optional[str] = None

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str
    api_key: Optional[str] = None
    provider: Optional[str] = "google"
    model: Optional[str] = None

class FinalizeRequest(BaseModel):
    session_id: str
