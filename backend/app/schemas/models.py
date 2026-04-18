from pydantic import BaseModel
from typing import Dict, List, Optional

class ConfirmUploadRequest(BaseModel):
    upload_id: str
    priorities: Dict[str, List[str]]

class StartVivaRequest(BaseModel):
    mode: Optional[str] = "quick" # 'quick' or 'comprehensive'
    num_questions: Optional[int] = 6

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

class FinalizeRequest(BaseModel):
    session_id: str
