"""
Interview database models
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Interview(Base):
    """Interview session model"""
    __tablename__ = "interviews"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    title = Column(String, nullable=False)
    domain = Column(String, nullable=False)  # AI/ML, DSA, Web Dev, etc.
    difficulty = Column(String, default="medium")  # easy, medium, hard
    status = Column(String, default="in_progress")  # in_progress, completed
    eval_mode = Column(String, default="semantic")  # semantic, llm
    overall_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="interviews")
    resume = relationship("Resume")
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")
    violations = relationship("AntiCheatViolation", back_populates="interview", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    """Interview question and answer model"""
    __tablename__ = "interview_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String)  # technical, behavioral, coding
    difficulty = Column(String)
    user_answer = Column(Text)
    expected_answer = Column(Text)
    score = Column(Float, default=0.0)
    feedback = Column(Text)
    retrieved_context = Column(JSON)  # Store retrieved chunks with sources
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    answered_at = Column(DateTime, nullable=True)
    
    # Relationships
    interview = relationship("Interview", back_populates="questions")


class Resume(Base):
    """Resume model"""
    __tablename__ = "resumes"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    extracted_text = Column(Text)
    skills = Column(JSON)  # Extracted skills
    experience_years = Column(Float)
    education = Column(JSON)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="resumes")


class AntiCheatViolation(Base):
    """Anti-cheat violation log"""
    __tablename__ = "anticheat_violations"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    violation_type = Column(String, nullable=False)  # tab_switch, copy_paste, multiple_displays, fullscreen_exit, devtools, right_click
    details = Column(Text)
    occurred_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    interview = relationship("Interview", back_populates="violations")


class SystemSetting(Base):
    """System-wide settings (key-value)"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
