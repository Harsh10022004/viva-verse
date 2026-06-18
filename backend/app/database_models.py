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

class VivaSession(Base):
    __tablename__ = "viva_sessions"

    id = Column(String, primary_key=True, index=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    mode = Column(String, default="quick")
    overall_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    answers_json = Column(Text, nullable=True) # Serialized JSON of answers and questions
    heatmap_json = Column(Text, nullable=True) # Serialized JSON of recall heatmap
    knowledge_map_json = Column(Text, nullable=True) # Serialized JSON of knowledge map

    user = relationship("User", back_populates="sessions")
