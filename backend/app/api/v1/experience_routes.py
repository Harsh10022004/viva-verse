from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
from datetime import datetime

from app.database import get_db
from app.database_models import User, InterviewExperience, InterviewRound, InterviewQuestion
from app.api.v1.auth_routes import get_current_user
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import vector_store
from app.services.search_service import hybrid_search

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
    rounds: List[RoundCreate]

class SearchRequest(BaseModel):
    query: str
    company: Optional[str] = None
    role: Optional[str] = None
    level: Optional[str] = None
    page: int = 1
    page_size: int = 20

# --- Routes ---

@router.post("")
def create_experience(req: ExperienceCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new interview experience."""
    exp = InterviewExperience(
        user_id=current_user.id,
        company=req.company,
        role=req.role,
        level=req.level,
        interview_date=req.interview_date,
        overall_experience=req.overall_experience
    )
    db.add(exp)
    db.flush() # Get exp.id

    questions_to_embed = []
    
    for r_req in req.rounds:
        round_obj = InterviewRound(
            experience_id=exp.id,
            round_name=r_req.round_name,
            notes=r_req.notes
        )
        db.add(round_obj)
        db.flush()
        
        for q_req in r_req.questions:
            q_obj = InterviewQuestion(
                round_id=round_obj.id,
                question_text=q_req.question_text
            )
            db.add(q_obj)
            questions_to_embed.append(q_obj)
            
    # Commit first so FTS5 triggers run and rowids exist
    db.commit()
    
    # Generate embeddings in batch
    if questions_to_embed:
        texts = [q.question_text for q in questions_to_embed]
        embeddings = generate_embeddings(texts)
        
        for q, emb in zip(questions_to_embed, embeddings):
            if emb:
                q.embedding = json.dumps(emb)
                # Add to FAISS directly
                vector_store.add_embedding(q.id, emb)
                
        db.commit()

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
        
    # Cascade delete will handle SQLite tables and triggers (FTS5 sync)
    # Note: FAISS index will still have the embeddings. 
    # For a simple app without soft-deletes or FAISS IDMap removals, it's ok,
    # because vector_search cross-references SQLite. If deleted in SQLite, it gets filtered out.
    
    db.delete(e)
    db.commit()
    return {"status": "success"}

@router.post("/search")
def search_questions(req: SearchRequest):
    """Hybrid search for interview questions using BM25 and Vector Similarity + RRF."""
    filters = {}
    if req.company: filters["company"] = req.company
    if req.role: filters["role"] = req.role
    if req.level: filters["level"] = req.level
    
    results = hybrid_search(
        query=req.query,
        filters=filters,
        page=req.page,
        page_size=req.page_size
    )
    return results
