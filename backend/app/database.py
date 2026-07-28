from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./viva_verse_v2.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_fts():
    """Initialize SQLite FTS5 virtual table and triggers for BM25 search."""
    # Only need to run once, IF NOT EXISTS handles subsequent runs
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE VIRTUAL TABLE IF NOT EXISTS interview_questions_fts USING fts5(
                id UNINDEXED,
                question_text,
                content='interview_questions',
                content_rowid='rowid'
            )
        """))
        
        # Triggers to keep FTS table in sync with interview_questions table
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS interview_questions_ai AFTER INSERT ON interview_questions BEGIN
                INSERT INTO interview_questions_fts(rowid, id, question_text) VALUES (new.rowid, new.id, new.question_text);
            END;
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS interview_questions_ad AFTER DELETE ON interview_questions BEGIN
                INSERT INTO interview_questions_fts(interview_questions_fts, rowid, id, question_text) VALUES('delete', old.rowid, old.id, old.question_text);
            END;
        """))
        conn.execute(text("""
            CREATE TRIGGER IF NOT EXISTS interview_questions_au AFTER UPDATE ON interview_questions BEGIN
                INSERT INTO interview_questions_fts(interview_questions_fts, rowid, id, question_text) VALUES('delete', old.rowid, old.id, old.question_text);
                INSERT INTO interview_questions_fts(rowid, id, question_text) VALUES (new.rowid, new.id, new.question_text);
            END;
        """))
        conn.commit()
