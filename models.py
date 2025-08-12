import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String, Integer, DateTime, Text, JSON, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional, Dict, Any
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)



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
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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

class Bot(db.Model):
    """Bot model for managing multiple bots"""
    __tablename__ = 'bots'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    platforms: Mapped[List[str]] = mapped_column(ARRAY(String), nullable=False)  # ['whatsapp', 'telegram']
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='active')  # active, inactive
    
    # Platform-specific configurations
    whatsapp_access_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    whatsapp_phone_number_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    whatsapp_verify_token: Mapped[str] = mapped_column(String(255), nullable=False, default='CVGlobal_WhatsApp_Verify_2024')
    
    telegram_bot_token: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    telegram_webhook_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Bot behavior settings
    ai_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="You are a helpful spiritual guide chatbot.")
    journey_duration_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    delivery_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    
    # Customizable command messages
    help_message: Mapped[str] = mapped_column(Text, nullable=False, default="🤝 Available Commands:\n\n📖 START - Begin your faith journey\n⏹️ STOP - Pause the journey\n❓ HELP - Show this help message\n👤 HUMAN - Connect with a human counselor\n\nI'm here to guide you through a meaningful spiritual journey. Feel free to ask questions or share your thoughts anytime!")
    stop_message: Mapped[str] = mapped_column(Text, nullable=False, default="⏸️ Your faith journey has been paused.\n\nTake your time whenever you're ready to continue. Send START to resume your journey, or HUMAN if you'd like to speak with someone.\n\nRemember, this is your personal space for spiritual exploration. There's no pressure - go at your own pace. 🙏")
    human_message: Mapped[str] = mapped_column(Text, nullable=False, default="👤 Human Support Requested\n\nI've flagged your conversation for our human counselors who will respond as soon as possible. They're trained in spiritual guidance and are here to support you.\n\nIn the meantime, feel free to continue sharing your thoughts or questions. Everything you share is treated with care and confidentiality. 💝")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="bot", cascade="all, delete-orphan")
    content: Mapped[List["Content"]] = relationship("Content", back_populates="bot", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Bot {self.name} - {self.platforms}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'platforms': self.platforms or [],
            'status': self.status,
            'whatsapp_access_token': self.whatsapp_access_token,
            'whatsapp_phone_number_id': self.whatsapp_phone_number_id,
            'whatsapp_webhook_url': self.whatsapp_webhook_url,
            'telegram_bot_token': self.telegram_bot_token,
            'telegram_webhook_url': self.telegram_webhook_url,
            'ai_prompt': self.ai_prompt,
            'journey_duration_days': self.journey_duration_days,
            'delivery_interval_minutes': self.delivery_interval_minutes,
            'help_message': self.help_message,
            'stop_message': self.stop_message,
            'human_message': self.human_message,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class User(db.Model):
    """User model for Faith Journey participants"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey('bots.id'), nullable=False, index=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_premium: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    
    # WhatsApp-specific fields
    whatsapp_contact_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_formatted_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Location data
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    location_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='active')
    current_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    join_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    completion_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tags: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True, default=list)
    
    # Relationships
    bot: Mapped["Bot"] = relationship("Bot", back_populates="users")
    messages: Mapped[List["MessageLog"]] = relationship("MessageLog", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<User {self.phone_number} - Bot {self.bot_id} - Day {self.current_day}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'phone_number': self.phone_number,
            'name': self.name,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language_code': self.language_code,
            'is_premium': self.is_premium,
            'whatsapp_contact_name': self.whatsapp_contact_name,
            'whatsapp_formatted_name': self.whatsapp_formatted_name,
            'whatsapp_phone': self.whatsapp_phone,
            'country': self.country,
            'region': self.region,
            'city': self.city,
            'timezone': self.timezone,
            'ip_address': self.ip_address,
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
    bot_id: Mapped[int] = mapped_column(Integer, ForeignKey('bots.id'), nullable=False, index=True)
    day_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reflection_question: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, default=list)
    
    # Multimedia content fields
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, default='text')
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    video_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    youtube_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False, default='daily')  # 'daily' or 'greeting'
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bot: Mapped["Bot"] = relationship("Bot", back_populates="content")
    
    def __repr__(self):
        return f'<Content Bot {self.bot_id} Day {self.day_number} - {self.title}>'
    
    def to_dict(self):
        # Construct media_url based on media type for scheduler compatibility
        media_url = None
        if self.media_type == 'image' and self.image_filename:
            import os
            replit_domains = os.environ.get('REPLIT_DOMAINS', '')
            if replit_domains:
                domain = replit_domains.split(',')[0]
                media_url = f"https://{domain}/static/uploads/images/{self.image_filename}"
            else:
                media_url = f"http://localhost:5000/static/uploads/images/{self.image_filename}"
        elif self.media_type == 'video':
            if self.video_filename:
                import os
                replit_domains = os.environ.get('REPLIT_DOMAINS', '')
                if replit_domains:
                    domain = replit_domains.split(',')[0]
                    media_url = f"https://{domain}/static/uploads/videos/{self.video_filename}"
                else:
                    media_url = f"http://localhost:5000/static/uploads/videos/{self.video_filename}"
            elif self.youtube_url:
                media_url = self.youtube_url
        elif self.media_type == 'audio' and self.audio_filename:
            import os
            replit_domains = os.environ.get('REPLIT_DOMAINS', '')
            if replit_domains:
                domain = replit_domains.split(',')[0]
                media_url = f"https://{domain}/static/uploads/audio/{self.audio_filename}"
            else:
                media_url = f"http://localhost:5000/static/uploads/audio/{self.audio_filename}"
        
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'day_number': self.day_number,
            'title': self.title,
            'content': self.content,
            'reflection_question': self.reflection_question,
            'tags': self.tags or [],
            'media_type': self.media_type,
            'media_url': media_url,
            'image_filename': self.image_filename,
            'video_filename': self.video_filename,
            'youtube_url': self.youtube_url,
            'audio_filename': self.audio_filename,
            'is_active': self.is_active,
            'content_type': getattr(self, 'content_type', 'daily'),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
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