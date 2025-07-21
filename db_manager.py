import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc
from models import db, User, Content, MessageLog, SystemSettings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Enhanced PostgreSQL Database Manager for Faith Journey"""
    
    def __init__(self):
        self.db = db
    
    # User Management Methods
    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """Get user by phone number"""
        try:
            return User.query.filter_by(phone_number=phone_number).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user {phone_number}: {e}")
            return None
    
    def create_user(self, phone_number: str, **kwargs) -> Optional[User]:
        """Create a new user"""
        try:
            user = User()
            user.phone_number = phone_number
            user.status = kwargs.get('status', 'active')
            user.current_day = kwargs.get('current_day', 1)
            user.join_date = kwargs.get('join_date', datetime.utcnow())
            user.tags = kwargs.get('tags', [])
            self.db.session.add(user)
            self.db.session.commit()
            logger.info(f"User {phone_number} created successfully")
            return user
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error creating user {phone_number}: {e}")
            return None
    
    def update_user(self, phone_number: str, **kwargs) -> bool:
        """Update user data"""
        try:
            user = self.get_user_by_phone(phone_number)
            if not user:
                return False
            
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            self.db.session.commit()
            logger.info(f"User {phone_number} updated successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error updating user {phone_number}: {e}")
            return False
    
    def get_active_users(self) -> List[User]:
        """Get all active users"""
        try:
            return User.query.filter_by(status='active').all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_users_by_status(self, status: str) -> List[User]:
        """Get users by status"""
        try:
            return User.query.filter_by(status=status).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting users by status {status}: {e}")
            return []
    
    def get_user_stats(self) -> Dict[str, int]:
        """Get user statistics"""
        try:
            total_users = User.query.count()
            active_users = User.query.filter_by(status='active').count()
            completed_users = User.query.filter_by(status='completed').count()
            inactive_users = User.query.filter_by(status='inactive').count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'completed_users': completed_users,
                'inactive_users': inactive_users
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting user stats: {e}")
            return {'total_users': 0, 'active_users': 0, 'completed_users': 0, 'inactive_users': 0}
    
    # Content Management Methods
    def get_content_by_day(self, day: int) -> Optional[Content]:
        """Get content for specific day"""
        try:
            return Content.query.filter_by(day_number=day, is_active=True).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting content for day {day}: {e}")
            return None
    
    def create_content_legacy(self, day: int, media_type: str, content_text: str, 
                      reflection_question: str, media_url: Optional[str] = None) -> Optional[Content]:
        """Legacy method for backward compatibility"""
        return self.create_content(
            day_number=day,
            title="Legacy Content",
            content=content_text,
            reflection_question=reflection_question,
            is_active=True
        )
    
    def get_all_content_legacy(self, active_only: bool = True) -> List[Content]:
        """Legacy method for backward compatibility"""
        try:
            query = Content.query
            if active_only:
                query = query.filter_by(is_active=True)
            return query.order_by(Content.day_number).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all content: {e}")
            return []
    
    # Message Logging Methods
    def log_message(self, user: User, direction: str, raw_text: str,
                   sentiment: Optional[str] = None, tags: Optional[List[str]] = None,
                   confidence: Optional[float] = None, is_human_handoff: bool = False) -> Optional[MessageLog]:
        """Log a message"""
        try:
            message_log = MessageLog()
            message_log.user_id = user.id
            message_log.direction = direction
            message_log.raw_text = raw_text
            message_log.llm_sentiment = sentiment
            message_log.llm_tags = tags or []
            message_log.llm_confidence = confidence
            message_log.is_human_handoff = is_human_handoff
            self.db.session.add(message_log)
            self.db.session.commit()
            return message_log
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error logging message: {e}")
            return None
    
    def get_recent_messages(self, limit: int = 10) -> List[MessageLog]:
        """Get recent messages with user info"""
        try:
            return (MessageLog.query
                   .join(User)
                   .order_by(desc(MessageLog.timestamp))
                   .limit(limit)
                   .all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    def get_user_messages(self, phone_number: str, limit: int = 50) -> List[MessageLog]:
        """Get messages for specific user"""
        try:
            user = self.get_user_by_phone(phone_number)
            if not user:
                return []
            
            return (MessageLog.query
                   .filter_by(user_id=user.id)
                   .order_by(desc(MessageLog.timestamp))
                   .limit(limit)
                   .all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting messages for user {phone_number}: {e}")
            return []
    
    def get_human_handoff_requests(self, unresolved_only: bool = True) -> List[MessageLog]:
        """Get human handoff requests"""
        try:
            query = MessageLog.query.filter_by(is_human_handoff=True)
            return query.join(User).order_by(desc(MessageLog.timestamp)).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting human handoff requests: {e}")
            return []
    
    # System Settings Methods
    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get system setting"""
        try:
            setting = SystemSettings.query.filter_by(key=key).first()
            return setting.value if setting else default
        except SQLAlchemyError as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """Set system setting"""
        try:
            setting = SystemSettings.query.filter_by(key=key).first()
            if setting:
                setting.value = value
                if description:
                    setting.description = description
                setting.updated_at = datetime.utcnow()
            else:
                setting = SystemSettings(
                    key=key,
                    value=value,
                    description=description
                )
                self.db.session.add(setting)
            
            self.db.session.commit()
            logger.info(f"Setting {key} updated successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error setting {key}: {e}")
            return False
    
    # Analytics Methods
    def get_sentiment_stats(self, days: int = 30) -> Dict[str, int]:
        """Get sentiment statistics for recent messages"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            sentiments = (self.db.session.query(MessageLog.llm_sentiment, func.count(MessageLog.id))
                         .filter(MessageLog.timestamp >= cutoff_date)
                         .filter(MessageLog.llm_sentiment.isnot(None))
                         .group_by(MessageLog.llm_sentiment)
                         .all())
            
            return {sentiment: count for sentiment, count in sentiments}
        except SQLAlchemyError as e:
            logger.error(f"Error getting sentiment stats: {e}")
            return {}
    
    def get_user_progress_stats(self) -> Dict[str, Any]:
        """Get user progress statistics"""
        try:
            progress_data = (self.db.session.query(User.current_day, func.count(User.id))
                           .filter_by(status='active')
                           .group_by(User.current_day)
                           .order_by(User.current_day)
                           .all())
            
            avg_progress = (self.db.session.query(func.avg(User.current_day))
                          .filter_by(status='active')
                          .scalar() or 0)
            
            return {
                'progress_distribution': {day: count for day, count in progress_data},
                'average_progress': round(float(avg_progress), 1)
            }
        except SQLAlchemyError as e:
            logger.error(f"Error getting user progress stats: {e}")
            return {'progress_distribution': {}, 'average_progress': 0}
    
    def initialize_sample_content(self):
        """Initialize database with sample content"""
        try:
            # Check if content already exists
            if Content.query.first():
                logger.info("Content already exists, skipping initialization")
                return
            
            sample_content = [
                {
                    "day": 1,
                    "media_type": "text",
                    "content_text": "As-salamu alaykum and welcome to your Faith Journey. We're glad you're here. In the holy Injil, the prophet Isa al-Masih (Jesus) is often described as a light. He said, 'I am the light of the world. Whoever follows me will never walk in darkness, but will have the light of life.' (John 8:12)",
                    "media_url": None,
                    "reflection_question": "What does the idea of 'light' mean to you in your own life?"
                },
                {
                    "day": 2,
                    "media_type": "text",
                    "content_text": "In Islamic tradition, we know that Allah is Ar-Rahman (The Compassionate) and Ar-Raheem (The Merciful). The Injil teaches us that Isa al-Masih showed this same divine compassion. When he saw people who were hurting, 'he had compassion on them, because they were harassed and helpless, like sheep without a shepherd.' (Matthew 9:36)",
                    "media_url": None,
                    "reflection_question": "When have you experienced compassion from others? How did it make you feel?"
                },
                {
                    "day": 3,
                    "media_type": "text",
                    "content_text": "The Quran speaks of Isa al-Masih as 'Kalimatullah' (Word of Allah). In the Injil, we read: 'In the beginning was the Word, and the Word was with Allah, and the Word was Allah... The Word became flesh and made his dwelling among us.' (John 1:1,14) This profound truth shows us that Jesus was not just a messenger, but the very expression of Allah's love coming to earth.",
                    "media_url": None,
                    "reflection_question": "What do you think it means that Jesus is called the 'Word of Allah'?"
                }
            ]
            
            for content_data in sample_content:
                self.create_content(**content_data)
            
            logger.info("Sample content initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing sample content: {e}")
    
    # Content Management Methods
    def get_all_content(self):
        """Get all content ordered by day number"""
        try:
            return Content.query.order_by(Content.day_number).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting all content: {e}")
            return []
    
    def create_content(self, day_number, title, content, reflection_question, tags=None, is_active=True):
        """Create new content"""
        try:
            new_content = Content()
            new_content.day_number = day_number
            new_content.title = title
            new_content.content = content
            new_content.reflection_question = reflection_question
            new_content.tags = tags or []
            new_content.is_active = is_active
            self.db.session.add(new_content)
            self.db.session.commit()
            logger.info(f"Content for day {day_number} created successfully")
            return new_content.id
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error creating content: {e}")
            return None
    
    def update_content(self, content_id, title, content, reflection_question, tags=None, is_active=True):
        """Update existing content"""
        try:
            content_obj = Content.query.get(content_id)
            if not content_obj:
                logger.error(f"Content with id {content_id} not found")
                return False
            
            content_obj.title = title
            content_obj.content = content
            content_obj.reflection_question = reflection_question
            content_obj.tags = tags or []
            content_obj.is_active = is_active
            content_obj.updated_at = datetime.utcnow()
            
            self.db.session.commit()
            logger.info(f"Content {content_id} updated successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error updating content: {e}")
            return False
    
    def delete_content(self, content_id):
        """Delete content"""
        try:
            content_obj = Content.query.get(content_id)
            if not content_obj:
                logger.error(f"Content with id {content_id} not found")
                return False
            
            self.db.session.delete(content_obj)
            self.db.session.commit()
            logger.info(f"Content {content_id} deleted successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error deleting content: {e}")
            return False
    
    # Additional User and Message Management Methods
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            return User.query.get(user_id)
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def get_user_messages(self, user_id: int) -> List[MessageLog]:
        """Get all messages for a specific user"""
        try:
            return MessageLog.query.filter_by(user_id=user_id).order_by(MessageLog.timestamp.asc()).all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user messages: {e}")
            return []
    
    def update_message_tags(self, message_id: int, tags: List[str]) -> bool:
        """Update tags for a specific message"""
        try:
            message = MessageLog.query.get(message_id)
            if not message:
                logger.error(f"Message with id {message_id} not found")
                return False
            
            message.llm_tags = tags
            self.db.session.commit()
            logger.info(f"Message {message_id} tags updated successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error updating message tags: {e}")
            return False
    
    def get_chatbot_settings(self) -> Dict:
        """Get chatbot settings"""
        try:
            settings = SystemSettings.query.filter_by(key='chatbot_settings').first()
            if settings:
                return json.loads(settings.value) if settings.value else {}
            return self._get_default_settings()
        except (SQLAlchemyError, json.JSONDecodeError) as e:
            logger.error(f"Error getting chatbot settings: {e}")
            return self._get_default_settings()
    
    def save_chatbot_settings(self, settings: Dict) -> bool:
        """Save chatbot settings"""
        try:
            setting = SystemSettings.query.filter_by(key='chatbot_settings').first()
            if not setting:
                setting = SystemSettings(key='chatbot_settings')
                self.db.session.add(setting)
            
            setting.value = json.dumps(settings)
            self.db.session.commit()
            logger.info("Chatbot settings saved successfully")
            return True
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error saving chatbot settings: {e}")
            return False
    
    def reset_chatbot_settings(self) -> bool:
        """Reset chatbot settings to defaults"""
        try:
            default_settings = self._get_default_settings()
            return self.save_chatbot_settings(default_settings)
        except Exception as e:
            logger.error(f"Error resetting chatbot settings: {e}")
            return False
    
    def _get_default_settings(self) -> Dict:
        """Get default chatbot settings"""
        return {
            'system_prompt': """You are a compassionate AI assistant helping people on their faith journey to learn about Jesus. 

Your role:
- Respond with warmth, understanding, and respect for the user's background
- Reference their current day's content when relevant
- Encourage reflection and spiritual growth
- Be sensitive to users from Muslim backgrounds
- Provide biblical insights in an accessible way
- Guide users toward a deeper understanding of Jesus

Always maintain a respectful, caring tone and be ready to offer prayer or encouragement when needed.""",
            'response_style': 'compassionate',
            'context_awareness': 'high',
            'use_daily_content_context': True,
            'enable_auto_tagging': True,
            'handoff_triggers': 'suicide, depression, abuse, crisis, emergency, help me, urgent'
        }