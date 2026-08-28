import os
from app.database import SessionLocal, init_fts, engine
from app.database_models import InterviewExperience
from app.services.vector_store import vector_store
from sqlalchemy import text
import json

def rebuild():
    db = SessionLocal()
    
    # 1. Rebuild FTS
    print("Rebuilding FTS...")
    try:
        with engine.connect() as conn:
            # Drop tables first to avoid FTS corruption from DELETE FROM
            conn.execute(text("DROP TABLE IF EXISTS interview_experiences_fts"))
            conn.execute(text("DROP TABLE IF EXISTS interview_questions_fts"))
            conn.commit()
            
        init_fts()
        
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO interview_experiences_fts(rowid, id, company, role, topics, overall_experience) 
                SELECT rowid, id, company, role, topics, overall_experience FROM interview_experiences;
            """))
            conn.execute(text("""
                INSERT INTO interview_questions_fts(rowid, id, question_text) 
                SELECT rowid, id, question_text FROM interview_questions;
            """))
            conn.commit()
            print("FTS rebuilt.")
    except Exception as e:
        print(f"Error rebuilding FTS: {e}")

    # 2. Rebuild FAISS
    print("Rebuilding FAISS...")
    vector_store.clear()
    
    experiences = db.query(InterviewExperience).all()
    count = 0
    for e in experiences:
        if e.embedding:
            try:
                emb = json.loads(e.embedding)
                vector_store.add_embedding(e.id, emb)
                count += 1
            except:
                pass
    
    # We do not need to save the index as it's an in-memory index rebuilt from SQLite on startup.
    print(f"Rebuilt FAISS index with {count} vectors!")

if __name__ == "__main__":
    rebuild()
