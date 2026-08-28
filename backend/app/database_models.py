from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student") # student or examiner
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("VivaSession", back_populates="user")
    experiences = relationship("InterviewExperience", back_populates="user")
    subscriptions = relationship("SearchSubscription")

class VivaSession(Base):
    __tablename__ = "viva_sessions"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    mode_name = Column(String, default="behavioral")
    role = Column(String, nullable=True)
    level = Column(String, nullable=True)
    elapsed_seconds = Column(Float, nullable=True)
    question_count = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    answers_json = Column(Text, nullable=True) # Serialized JSON of answers and questions
    remediation_json = Column(Text, nullable=True) # Serialized JSON of knapsack remediation plan
    strengths_json = Column(Text, nullable=True) # Serialized JSON of strengths
    weaknesses_json = Column(Text, nullable=True) # Serialized JSON of weaknesses

    user = relationship("User", back_populates="sessions")

class InterviewExperience(Base):
    __tablename__ = "interview_experiences"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    company = Column(String, index=True, nullable=False)
    role = Column(String, index=True, nullable=False)
    level = Column(String, index=True, nullable=False)
    interview_date = Column(String, nullable=True)
    overall_experience = Column(Text, nullable=True)
    source = Column(String, default="platform") # "platform" or "ingested"
    topics = Column(String, nullable=True) # Comma-separated string
    embedding = Column(Text, nullable=True) # JSON serialized float array for FAISS
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="experiences")
    rounds = relationship("InterviewRound", back_populates="experience", cascade="all, delete-orphan")

class InterviewRound(Base):
    __tablename__ = "interview_rounds"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    experience_id = Column(String, ForeignKey("interview_experiences.id"))
    round_name = Column(String, index=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    experience = relationship("InterviewExperience", back_populates="rounds")
    questions = relationship("InterviewQuestion", back_populates="round", cascade="all, delete-orphan")

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    round_id = Column(String, ForeignKey("interview_rounds.id"))
    question_text = Column(Text, nullable=False)
    embedding = Column(Text, nullable=True) # JSON serialized float array for FAISS persistence
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    round = relationship("InterviewRound", back_populates="questions")

class SearchSubscription(Base):
    __tablename__ = "search_subscriptions"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Optional for non-logged in users if we allow them to subscribe with email/whatsapp
    query_text = Column(String, index=True, nullable=False)
    query_embedding = Column(Text, nullable=True) # JSON serialized float array
    threshold_score = Column(Float, nullable=False)
    contact_email = Column(String, nullable=True)
    contact_whatsapp = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
