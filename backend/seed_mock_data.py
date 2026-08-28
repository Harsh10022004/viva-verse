import os
import sys
import json
import uuid
import time
from tqdm import tqdm
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_fts
from app.database_models import InterviewExperience, InterviewRound, InterviewQuestion, User
from app.services.embedding_service import generate_embedding

def run_seed():
    print("Initializing Database and dropping old records...")
    db = SessionLocal()
    
    try:
        # Wipe existing data
        try:
            db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_ai"))
            db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_ad"))
            db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_au"))
            db.execute(text("DROP TABLE IF EXISTS interview_experiences_fts"))
            db.commit()
        except Exception as e:
            pass
            
        db.query(InterviewQuestion).delete()
        db.query(InterviewRound).delete()
        db.query(InterviewExperience).delete()
        db.commit()
        
        # Ensure FTS tables exist
        init_fts()
        
        user = db.query(User).first()
        if not user:
            user = User(email="benchmark@vivaverse.com", username="benchmark")
            user.hashed_password = "password123"
            db.add(user)
            db.commit()
            db.refresh(user)
            
        # Load the rich, unique mock data
        try:
            from app.rich_mock_data import RICH_EXPERIENCES
        except ImportError:
            print("Could not import RICH_EXPERIENCES. Please ensure rich_mock_data.py exists.")
            return

        print(f"Seeding {len(RICH_EXPERIENCES)} Ultra-Realistic Human Experiences...")
        
        all_exp_texts = []
        all_exp_ids = []
        
        # Step 1: Insert into SQL
        for exp_data in tqdm(RICH_EXPERIENCES, desc="Inserting into SQLite"):
            exp_id = str(uuid.uuid4())
            exp = InterviewExperience(
                id=exp_id,
                user_id=user.id,
                company=exp_data["company"],
                role=exp_data["role"],
                level=exp_data["level"],
                interview_date=exp_data["interview_date"],
                overall_experience=exp_data["overall_experience"],
                source="ingested",
                topics=exp_data["topics"]
            )
            db.add(exp)
            
            # Build text for embedding
            full_text_parts = [exp.overall_experience]
            
            for round_data in exp_data["rounds"]:
                round_id = str(uuid.uuid4())
                r = InterviewRound(
                    id=round_id,
                    experience_id=exp_id,
                    round_name=round_data["round_name"],
                    notes=round_data["notes"]
                )
                db.add(r)
                
                full_text_parts.append(r.round_name)
                full_text_parts.append(r.notes)
                
                for q_data in round_data["questions"]:
                    q = InterviewQuestion(
                        id=str(uuid.uuid4()),
                        round_id=round_id,
                        question_text=q_data["question_text"]
                    )
                    db.add(q)
                    full_text_parts.append(q.question_text)
                    
            all_exp_ids.append(exp_id)
            all_exp_texts.append(" ".join(full_text_parts))
            
        db.commit()
        
        # Step 2: Generate Vectors in memory and save to SQL
        print("Running hardware-accelerated embedding encoding...")
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embeddings_matrix = model.encode(all_exp_texts, batch_size=32, show_progress_bar=True)
            
            print("Writing embeddings to SQLite...")
            for exp_id, emb_array in tqdm(zip(all_exp_ids, embeddings_matrix), total=len(all_exp_ids)):
                emb_list = emb_array.tolist()
                db.query(InterviewExperience).filter(InterviewExperience.id == exp_id).update(
                    {"embedding": json.dumps(emb_list)}
                )
            db.commit()
            
        except Exception as e:
            print(f"Error during vectorization: {e}")
            db.rollback()
            
        print(f"Done! {len(RICH_EXPERIENCES)} UNIQUE records successfully seeded and indexed.")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
