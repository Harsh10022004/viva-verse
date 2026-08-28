import logging
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.database_models import InterviewExperience, InterviewRound, InterviewQuestion
from app.services.embedding_service import generate_embeddings
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

MOCK_DATA = [
    {
        "company": "Google",
        "role": "Software Engineer",
        "level": "L4",
        "source": "ingested",
        "topics": "system design, graphs, dynamic programming",
        "overall_experience": "The interview was challenging but fair. The interviewers were very helpful and provided good hints. The focus was heavily on algorithmic problem-solving and scalability in system design.",
        "rounds": [
            {
                "round_name": "Phone Screen",
                "notes": "Focused on basic data structures.",
                "questions": ["Given a binary tree, find its maximum depth.", "Explain how a hash map works internally."]
            },
            {
                "round_name": "Onsite 1 - Coding",
                "notes": "Graph traversal.",
                "questions": ["Find the shortest path in a 2D grid with obstacles using BFS.", "What is the time complexity of Dijkstra's algorithm?"]
            },
            {
                "round_name": "Onsite 2 - System Design",
                "notes": "Design a scalable service.",
                "questions": ["Design Google Drive.", "How would you handle concurrent file uploads and synchronize across multiple devices?"]
            }
        ]
    },
    {
        "company": "Amazon",
        "role": "Backend Development Engineer",
        "level": "SDE II",
        "source": "ingested",
        "topics": "leadership principles, microservices, databases",
        "overall_experience": "Very intense loop. Lots of behavioral questions tied to Leadership Principles. Technical rounds focused on practical backend design and object-oriented programming.",
        "rounds": [
            {
                "round_name": "Behavioral & Coding",
                "notes": "Customer obsession.",
                "questions": ["Tell me about a time you went above and beyond for a customer.", "Design an LRU Cache."]
            },
            {
                "round_name": "System Design",
                "notes": "E-commerce architecture.",
                "questions": ["Design Amazon's shopping cart system.", "How do you ensure data consistency across microservices?"]
            }
        ]
    }
]

def run_mock_ingestion():
    """Simulates ingesting data from external platforms."""
    db = SessionLocal()
    try:
        # Assuming admin/system user is id "system" or we just use the first user
        from app.database_models import User
        system_user = db.query(User).first()
        if not system_user:
            system_user = User(
                username="System Ingestion",
                email="system@vivaverse.com",
                hashed_password="pw",
                role="admin"
            )
            db.add(system_user)
            db.commit()
            db.refresh(system_user)

        for data in MOCK_DATA:
            # Check if already exists to avoid duplicates on multiple runs
            exists = db.query(InterviewExperience).filter(
                InterviewExperience.company == data["company"],
                InterviewExperience.source == "ingested"
            ).first()
            
            if exists:
                continue

            exp = InterviewExperience(
                user_id=system_user.id,
                company=data["company"],
                role=data["role"],
                level=data["level"],
                overall_experience=data["overall_experience"],
                source=data["source"],
                topics=data["topics"]
            )
            db.add(exp)
            db.flush()

            full_text_parts = [exp.company, exp.role, exp.level, exp.overall_experience]

            for r_data in data["rounds"]:
                round_obj = InterviewRound(
                    experience_id=exp.id,
                    round_name=r_data["round_name"],
                    notes=r_data.get("notes")
                )
                db.add(round_obj)
                db.flush()
                
                full_text_parts.append(r_data["round_name"])
                if r_data.get("notes"): full_text_parts.append(r_data["notes"])

                for q_text in r_data["questions"]:
                    q_obj = InterviewQuestion(
                        round_id=round_obj.id,
                        question_text=q_text
                    )
                    db.add(q_obj)
                    full_text_parts.append(q_text)

            db.commit()

            # Embed the whole experience
            full_text = " ".join(full_text_parts)
            try:
                embeddings = generate_embeddings([full_text])
                if embeddings and embeddings[0]:
                    emb = embeddings[0]
                    exp.embedding = json.dumps(emb)
                    vector_store.add_embedding(exp.id, emb)
                    db.commit()
            except Exception as e:
                logger.error(f"Failed to embed ingested experience: {e}")
                
        logger.info("Mock ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_mock_ingestion()
