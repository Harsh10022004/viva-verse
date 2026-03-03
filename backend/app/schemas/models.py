from pydantic import BaseModel
from typing import Dict, List

class ConfirmUploadRequest(BaseModel):
    upload_id: str
    priorities: Dict[str, List[str]]

class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str

class FinalizeRequest(BaseModel):
    session_id: str
