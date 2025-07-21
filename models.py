import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

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
    day_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reflection_question: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Content Day {self.day_number} - {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'day_number': self.day_number,
            'title': self.title,
            'content': self.content,
            'reflection_question': self.reflection_question,
            'tags': self.tags or [],
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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

class AdminUser(UserMixin, db.Model):
    """Admin user model for authentication"""
    __tablename__ = 'admin_users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default='admin')  # admin, super_admin
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<AdminUser {self.username} ({self.role})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
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