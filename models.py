import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """User model for Faith Journey participants"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='active')  # active, inactive, completed
    current_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    join_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completion_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Relationships
    messages: Mapped[List["MessageLog"]] = relationship("MessageLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.phone_number} - Day {self.current_day} ({self.status})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'phone_number': self.phone_number,
            'status': self.status,
            'current_day': self.current_day,
            'join_date': self.join_date.isoformat() if self.join_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'tags': self.tags or []
        }

class Content(db.Model):
    """Content model for daily faith journey content"""
    __tablename__ = 'content'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)  # text, image, video, audio
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    media_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    reflection_question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        return f'<Content Day {self.day} - {self.media_type}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'day': self.day,
            'media_type': self.media_type,
            'content_text': self.content_text,
            'media_url': self.media_url,
            'reflection_question': self.reflection_question,
            'created_at': self.created_at.isoformat(),
            'is_active': self.is_active
        }

class MessageLog(db.Model):
    """Message log model for tracking user interactions"""
    __tablename__ = 'message_logs'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)  # incoming, outgoing
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    llm_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # positive, negative, neutral
    llm_tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    llm_confidence: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_human_handoff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    
    def __repr__(self):
        return f'<MessageLog {self.user.phone_number} - {self.direction} - {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_phone': self.user.phone_number if self.user else None,
            'timestamp': self.timestamp.isoformat(),
            'direction': self.direction,
            'raw_text': self.raw_text,
            'llm_sentiment': self.llm_sentiment,
            'llm_tags': self.llm_tags or [],
            'llm_confidence': self.llm_confidence,
            'is_human_handoff': self.is_human_handoff
        }

class SystemSettings(db.Model):
    """System settings for configuration"""
    __tablename__ = 'system_settings'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemSettings {self.key}: {self.value[:50]}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat()
        }