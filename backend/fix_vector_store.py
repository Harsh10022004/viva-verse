import json
from app.database import SessionLocal
from app.database_models import InterviewExperience
from app.services.vector_store import vector_store

db = SessionLocal()
experiences = db.query(InterviewExperience).all()
print(f"Found {len(experiences)} experiences in DB.")

for exp in experiences:
    if exp.embedding:
        try:
            emb = json.loads(exp.embedding)
            vector_store.add_vector(exp.id, emb)
        except Exception as e:
            print(f"Error parsing embedding for {exp.id}: {e}")

print(f"Vector store now contains {vector_store.index.ntotal} vectors.")
db.close()
