from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
from datetime import datetime

from app.database import get_db
from app.database_models import User, InterviewExperience, InterviewRound, InterviewQuestion, SearchSubscription
from app.api.v1.auth_routes import get_current_user
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import vector_store
from app.services.search_service import hybrid_search, calculate_subscription_threshold, check_subscriptions_for_new_post

router = APIRouter()

# --- Schemas ---

class QuestionCreate(BaseModel):
    question_text: str

class RoundCreate(BaseModel):
    round_name: str
    notes: Optional[str] = None
    questions: List[QuestionCreate]

class ExperienceCreate(BaseModel):
    company: str
    role: str
    level: str
    interview_date: Optional[str] = None
    overall_experience: Optional[str] = None
    source: str = "platform"
    topics: Optional[str] = None
    rounds: List[RoundCreate]

class SearchRequest(BaseModel):
    query: str
    company: Optional[str] = None
    role: Optional[str] = None
    level: Optional[str] = None
    source: Optional[str] = "both"
    topics: Optional[str] = None
    page: int = 1
    page_size: int = 20
    top_k: Optional[int] = None

class SummaryRequest(BaseModel):
    experience_ids: List[str]
    api_key: Optional[str] = None


class SubscribeRequest(BaseModel):
    query: str
    email: Optional[str] = None
    whatsapp: Optional[str] = None

# --- Routes ---

@router.post("")
def create_experience(req: ExperienceCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new interview experience."""
    exp = InterviewExperience(
        user_id=current_user.id,
        company=req.company,
        role=req.role,
        level=req.level,
        interview_date=req.interview_date,
        overall_experience=req.overall_experience,
        source=req.source,
        topics=req.topics
    )
    db.add(exp)
    db.flush() # Get exp.id
    
    # Build text for embedding the whole experience (ONLY content, no metadata)
    full_text_parts = []
    if req.overall_experience:
        full_text_parts.append(req.overall_experience)
    for r_req in req.rounds:
        round_obj = InterviewRound(
            experience_id=exp.id,
            round_name=r_req.round_name,
            notes=r_req.notes
        )
        db.add(round_obj)
        db.flush()
        
        full_text_parts.append(r_req.round_name)
        if r_req.notes: full_text_parts.append(r_req.notes)
        
        for q_req in r_req.questions:
            q_obj = InterviewQuestion(
                round_id=round_obj.id,
                question_text=q_req.question_text
            )
            db.add(q_obj)
            full_text_parts.append(q_req.question_text)
            
    db.commit()
    
    # Generate embedding for the entire experience
    full_text = " ".join(full_text_parts)
    try:
        embeddings = generate_embeddings([full_text])
        if embeddings and embeddings[0]:
            emb = embeddings[0]
            exp.embedding = json.dumps(emb)
            # We are currently using vector_store which needs string ID and float array.
            vector_store.add_embedding(exp.id, emb)
            db.commit()
            
            # Trigger background check for subscriptions
            background_tasks.add_task(check_subscriptions_for_new_post, exp.id)
    except Exception as e:
        print(f"Embedding failed: {e}")

    return {"status": "success", "id": exp.id}


@router.get("")
def list_experiences(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):
    """List recent interview experiences."""
    offset = (page - 1) * page_size
    experiences = db.query(InterviewExperience).order_by(InterviewExperience.created_at.desc()).offset(offset).limit(page_size).all()
    total = db.query(InterviewExperience).count()
    
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "data": [{
            "id": e.id,
            "company": e.company,
            "role": e.role,
            "level": e.level,
            "source": e.source,
            "topics": e.topics,
            "interview_date": e.interview_date,
            "created_at": e.created_at.isoformat()
        } for e in experiences]
    }

@router.get("/mine")
def list_my_experiences(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List experiences posted by the current user."""
    experiences = db.query(InterviewExperience).filter(InterviewExperience.user_id == current_user.id).order_by(InterviewExperience.created_at.desc()).all()
    
    return {
        "data": [{
            "id": e.id,
            "company": e.company,
            "role": e.role,
            "level": e.level,
            "source": e.source,
            "topics": e.topics,
            "interview_date": e.interview_date,
            "created_at": e.created_at.isoformat()
        } for e in experiences]
    }

@router.get("/{exp_id}")
def get_experience(exp_id: str, db: Session = Depends(get_db)):
    """Get full details of a specific experience."""
    e = db.query(InterviewExperience).filter(InterviewExperience.id == exp_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experience not found")
        
    rounds_data = []
    for r in e.rounds:
        questions_data = [{"id": q.id, "question_text": q.question_text} for q in r.questions]
        rounds_data.append({
            "id": r.id,
            "round_name": r.round_name,
            "notes": r.notes,
            "questions": questions_data
        })
        
    return {
        "id": e.id,
        "company": e.company,
        "role": e.role,
        "level": e.level,
        "source": e.source,
        "topics": e.topics,
        "interview_date": e.interview_date,
        "overall_experience": e.overall_experience,
        "created_at": e.created_at.isoformat(),
        "rounds": rounds_data
    }

@router.delete("/{exp_id}")
def delete_experience(exp_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete an experience (only owner)."""
    e = db.query(InterviewExperience).filter(InterviewExperience.id == exp_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="Experience not found")
        
    if e.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this experience")
        
    db.delete(e)
    db.commit()
    return {"status": "success"}

@router.post("/search")
def search_experiences(req: SearchRequest):
    """Hybrid search for interview experiences."""
    filters = {}
    if req.company: filters["company"] = req.company
    if req.role: filters["role"] = req.role
    if req.level: filters["level"] = req.level
    if req.source: filters["source"] = req.source
    if req.topics: filters["topics"] = req.topics
    
    results = hybrid_search(
        query=req.query,
        filters=filters,
        page=req.page,
        page_size=req.page_size,
        top_k=req.top_k
    )
    return results

@router.post("/subscribe")
def subscribe_to_search(req: SubscribeRequest, db: Session = Depends(get_db)):
    """Subscribe to a search query for email/whatsapp alerts."""
    if not req.email and not req.whatsapp:
        raise HTTPException(status_code=400, detail="Must provide either email or whatsapp")
        
    query_vector = generate_embeddings([req.query])
    if not query_vector or not query_vector[0]:
        raise HTTPException(status_code=500, detail="Failed to generate embedding for query")
        
    emb = query_vector[0]
    threshold = calculate_subscription_threshold(emb)
    
    sub = SearchSubscription(
        query_text=req.query,
        query_embedding=json.dumps(emb),
        threshold_score=threshold,
        contact_email=req.email,
        contact_whatsapp=req.whatsapp
    )
    db.add(sub)
    db.commit()
    return {"status": "success", "message": "Successfully subscribed"}


@router.post("/summary")
def get_ai_summary(req: SummaryRequest, db: Session = Depends(get_db)):
    """Generate an AI summary of selected experiences."""
    from app.services.llm_service import generate_ai_summary
    
    experiences = db.query(InterviewExperience).filter(InterviewExperience.id.in_(req.experience_ids)).all()
    if not experiences:
        raise HTTPException(status_code=404, detail="No experiences found")
        
    full_text = ""
    for e in experiences:
        full_text += f"Company: {e.company}, Role: {e.role}\n"
        if e.overall_experience:
            full_text += f"Overall Experience: {e.overall_experience}\n"
        for r in e.rounds:
            for q in r.questions:
                full_text += f"- {q.question_text}\n"
        full_text += "\n---\n"
        
    summary = generate_ai_summary(full_text, req.api_key)
    return {"summary": summary}
