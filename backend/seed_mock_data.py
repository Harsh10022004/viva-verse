import json
import logging
import os
import sys
import uuid

from sqlalchemy import text
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_fts
from app.database_models import InterviewExperience, InterviewQuestion, InterviewRound, User
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)


def run_seed(force: bool = False) -> bool:
    """
    Seed mock interview experiences into SQLite.

    When force=False (startup mode), skips if any experiences already exist.
    When force=True (CLI mode), wipes existing experience data and reseeds.
    """
    db = SessionLocal()

    try:
        existing_count = db.query(InterviewExperience).count()
        if existing_count > 0 and not force:
            logger.info(
                "Skipping seed: %s interview experience(s) already in database.",
                existing_count,
            )
            return False

        if force:
            logger.info("Force seed requested — wiping existing interview data...")
            try:
                db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_ai"))
                db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_ad"))
                db.execute(text("DROP TRIGGER IF EXISTS interview_experiences_au"))
                db.execute(text("DROP TABLE IF EXISTS interview_experiences_fts"))
                db.commit()
            except Exception:
                db.rollback()

            db.query(InterviewQuestion).delete()
            db.query(InterviewRound).delete()
            db.query(InterviewExperience).delete()
            db.commit()

        init_fts()

        user = db.query(User).first()
        if not user:
            user = User(email="benchmark@vivaverse.com", username="benchmark")
            user.hashed_password = "password123"
            db.add(user)
            db.commit()
            db.refresh(user)

        try:
            from app.rich_mock_data import RICH_EXPERIENCES
        except ImportError:
            logger.error("Could not import RICH_EXPERIENCES from app.rich_mock_data.")
            return False

        logger.info("Seeding %s mock interview experiences...", len(RICH_EXPERIENCES))

        all_exp_texts = []
        all_exp_ids = []

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
                topics=exp_data["topics"],
            )
            db.add(exp)

            full_text_parts = [exp.overall_experience]

            for round_data in exp_data["rounds"]:
                round_id = str(uuid.uuid4())
                round_row = InterviewRound(
                    id=round_id,
                    experience_id=exp_id,
                    round_name=round_data["round_name"],
                    notes=round_data["notes"],
                )
                db.add(round_row)

                full_text_parts.append(round_row.round_name)
                full_text_parts.append(round_row.notes)

                for q_data in round_data["questions"]:
                    question = InterviewQuestion(
                        id=str(uuid.uuid4()),
                        round_id=round_id,
                        question_text=q_data["question_text"],
                    )
                    db.add(question)
                    full_text_parts.append(question.question_text)

            all_exp_ids.append(exp_id)
            all_exp_texts.append(" ".join(full_text_parts))

        db.commit()

        if not os.environ.get("GEMINI_API_KEY"):
            logger.warning(
                "GEMINI_API_KEY not set — experiences seeded without vector embeddings."
            )
            return True

        logger.info("Generating Gemini embeddings for seeded experiences...")
        embedded_count = 0
        for exp_id, exp_text in tqdm(
            zip(all_exp_ids, all_exp_texts),
            total=len(all_exp_ids),
            desc="Embedding experiences",
        ):
            embedding = generate_embedding(exp_text)
            if not embedding:
                logger.warning("Failed to generate embedding for experience %s", exp_id)
                continue

            db.query(InterviewExperience).filter(InterviewExperience.id == exp_id).update(
                {"embedding": json.dumps(embedding)}
            )
            embedded_count += 1

        db.commit()
        logger.info(
            "Seed complete: %s experiences inserted, %s embeddings stored.",
            len(RICH_EXPERIENCES),
            embedded_count,
        )
        return True

    except Exception as exc:
        logger.exception("Error seeding mock data: %s", exc)
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_seed(force=True)
