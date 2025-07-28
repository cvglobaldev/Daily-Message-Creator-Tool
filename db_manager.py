import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc, or_, and_, case
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
        """Create a new user with enhanced fields"""
        try:
            user = User()
            user.phone_number = phone_number
            user.bot_id = kwargs.get('bot_id', 1)  # Default to bot 1
            
            # Basic fields
            user.name = kwargs.get('name')
            user.status = kwargs.get('status', 'active')
            user.current_day = kwargs.get('current_day', 1)
            user.join_date = kwargs.get('join_date', datetime.utcnow())
            user.tags = kwargs.get('tags', [])
            
            # Enhanced Telegram fields
            user.username = kwargs.get('username')
            user.first_name = kwargs.get('first_name')
            user.last_name = kwargs.get('last_name')
            user.language_code = kwargs.get('language_code')
            user.is_premium = kwargs.get('is_premium')
            
            # Location fields
            user.country = kwargs.get('country')
            user.region = kwargs.get('region')
            user.city = kwargs.get('city')
            user.timezone = kwargs.get('timezone')
            user.ip_address = kwargs.get('ip_address')
            
            self.db.session.add(user)
            self.db.session.commit()
            logger.info(f"User {phone_number} created successfully with enhanced data: {user.name}")
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
    
    def get_user_messages_by_id(self, user_id: int, limit: int = 50) -> List[MessageLog]:
        """Get messages for specific user by user ID"""
        try:
            return (MessageLog.query
                   .filter_by(user_id=user_id)
                   .order_by(MessageLog.timestamp.asc())
                   .limit(limit)
                   .all())
        except SQLAlchemyError as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
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
    
    def create_content(self, day_number, title, content, reflection_question, tags=None, 
                      media_type='text', image_filename=None, video_filename=None, 
                      youtube_url=None, audio_filename=None, is_active=True, bot_id=1):
        """Create new multimedia content"""
        try:
            new_content = Content()
            new_content.day_number = day_number
            new_content.title = title
            new_content.content = content
            new_content.reflection_question = reflection_question
            new_content.tags = tags or []
            new_content.media_type = media_type
            new_content.image_filename = image_filename
            new_content.video_filename = video_filename
            new_content.youtube_url = youtube_url
            new_content.audio_filename = audio_filename
            new_content.is_active = is_active
            new_content.bot_id = bot_id
            self.db.session.add(new_content)
            self.db.session.commit()
            logger.info(f"Content for day {day_number} created successfully with media type: {media_type}")
            return new_content.id
        except SQLAlchemyError as e:
            self.db.session.rollback()
            logger.error(f"Error creating content: {e}")
            return None
    
    def update_content(self, content_id, title, content, reflection_question, tags=None, 
                      media_type='text', image_filename=None, video_filename=None, 
                      youtube_url=None, audio_filename=None, is_active=True):
        """Update existing multimedia content"""
        try:
            content_obj = Content.query.get(content_id)
            if not content_obj:
                logger.error(f"Content with id {content_id} not found")
                return False
            
            content_obj.title = title
            content_obj.content = content
            content_obj.reflection_question = reflection_question
            content_obj.tags = tags or []
            content_obj.media_type = media_type
            content_obj.image_filename = image_filename
            content_obj.video_filename = video_filename
            content_obj.youtube_url = youtube_url
            content_obj.audio_filename = audio_filename
            content_obj.is_active = is_active
            content_obj.updated_at = datetime.utcnow()
            
            self.db.session.commit()
            logger.info(f"Content {content_id} updated successfully with media type: {media_type}")
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
    
    def get_recent_active_users(self, limit: int = 10, bot_id: int = None) -> List[Dict]:
        """Get recent unique users with their conversation summary (no duplicates)"""
        try:
            # Get unique users with comprehensive conversation stats
            query = self.db.session.query(
                User.id,
                User.phone_number,
                User.status,
                User.current_day,
                User.join_date,
                func.max(MessageLog.timestamp).label('latest_message_time'),
                func.count(MessageLog.id).label('total_messages'),
                func.sum(case(
                    (MessageLog.direction == 'incoming', 1),
                    else_=0
                )).label('incoming_messages'),
                func.sum(case(
                    (MessageLog.direction == 'outgoing', 1),
                    else_=0
                )).label('outgoing_messages'),
                func.sum(case(
                    (MessageLog.is_human_handoff == True, 1),
                    else_=0
                )).label('handoff_requests')
            ).outerjoin(MessageLog, User.id == MessageLog.user_id)
            
            # Add bot filtering if specified
            if bot_id is not None:
                query = query.filter(User.bot_id == bot_id)
            
            query = query.group_by(User.id, User.phone_number, User.status, User.current_day, User.join_date)\
                    .having(func.count(MessageLog.id) > 0)\
                    .order_by(desc('latest_message_time'))\
                    .limit(limit)
            
            results = query.all()
            
            user_list = []
            for row in results:
                # Get the most recent message for preview
                recent_message = self.db.session.query(MessageLog)\
                    .filter_by(user_id=row.id)\
                    .order_by(desc(MessageLog.timestamp))\
                    .first()
                
                # Create conversation summary
                conversation_summary = f"{int(row.incoming_messages or 0)} incoming, {int(row.outgoing_messages or 0)} outgoing"
                if row.handoff_requests and row.handoff_requests > 0:
                    conversation_summary += f", {int(row.handoff_requests)} handoffs"
                
                user_list.append({
                    'id': row.id,
                    'user_phone': row.phone_number,
                    'user_id': row.id,  
                    'status': row.status,
                    'current_day': row.current_day,
                    'join_date': row.join_date.isoformat() if row.join_date else None,
                    'timestamp': row.latest_message_time.isoformat() if row.latest_message_time else None,
                    'total_messages': int(row.total_messages or 0),
                    'conversation_summary': conversation_summary,
                    'raw_text': recent_message.raw_text[:100] + ('...' if len(recent_message.raw_text) > 100 else '') if recent_message else '',
                    'direction': recent_message.direction if recent_message else 'none',
                    'llm_sentiment': recent_message.llm_sentiment if recent_message else None,
                    'is_human_handoff': recent_message.is_human_handoff if recent_message else False
                })
            
            return user_list
            
        except Exception as e:
            logger.error(f"Error getting recent active users: {e}")
            return []
    
    def get_consolidated_user_conversations(self, page: int = 1, limit: int = 20, sort_field: str = 'timestamp', sort_order: str = 'desc', filters: Dict = None) -> Dict:
        """Get consolidated user conversations for chat management (unique users only)"""
        try:
            # Build base query for users with their conversation stats and enhanced fields
            query = self.db.session.query(
                User.id,
                User.phone_number,
                User.name,
                User.username,
                User.first_name,
                User.last_name,
                User.status,
                User.current_day,
                User.join_date,
                User.country,
                User.region,
                User.city,
                User.language_code,
                User.is_premium,
                User.ip_address,
                func.max(MessageLog.timestamp).label('latest_message_time'),
                func.count(MessageLog.id).label('total_messages'),
                func.sum(case(
                    (MessageLog.direction == 'incoming', 1),
                    else_=0
                )).label('incoming_messages'),
                func.sum(case(
                    (MessageLog.direction == 'outgoing', 1),
                    else_=0
                )).label('outgoing_messages'),
                func.sum(case(
                    (MessageLog.is_human_handoff == True, 1),
                    else_=0
                )).label('handoff_requests'),
            ).outerjoin(MessageLog, User.id == MessageLog.user_id)\
            .group_by(User.id, User.phone_number, User.name, User.username, User.first_name, User.last_name,
                     User.status, User.current_day, User.join_date, User.country, User.region, User.city,
                     User.language_code, User.is_premium, User.ip_address)\
            .having(func.count(MessageLog.id) > 0)
            
            # Apply filters if provided
            if filters:
                if filters.get('user_search'):
                    query = query.filter(User.phone_number.ilike(f"%{filters['user_search']}%"))
                
                if filters.get('date_from'):
                    try:
                        date_from = datetime.fromisoformat(filters['date_from'].replace('Z', '+00:00'))
                        query = query.having(func.max(MessageLog.timestamp) >= date_from)
                    except:
                        pass
                        
                if filters.get('date_to'):
                    try:
                        date_to = datetime.fromisoformat(filters['date_to'].replace('Z', '+00:00'))
                        query = query.having(func.max(MessageLog.timestamp) <= date_to)
                    except:
                        pass
                        
                if filters.get('human_handoff'):
                    query = query.having(func.sum(case((MessageLog.is_human_handoff == True, 1), else_=0)) > 0)
            
            # Apply sorting
            if sort_field == 'timestamp':
                if sort_order == 'desc':
                    query = query.order_by(desc('latest_message_time'))
                else:
                    query = query.order_by('latest_message_time')
            elif sort_field == 'phone_number':
                if sort_order == 'desc':
                    query = query.order_by(desc(User.phone_number))
                else:
                    query = query.order_by(User.phone_number)
            else:
                query = query.order_by(desc('latest_message_time'))
            
            # Get total count for pagination
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            results = query.offset(offset).limit(limit).all()
            
            # Convert to list of dictionaries
            conversations = []
            for row in results:
                # Get the most recent message for preview
                recent_message = self.db.session.query(MessageLog)\
                    .filter_by(user_id=row.id)\
                    .order_by(desc(MessageLog.timestamp))\
                    .first()
                
                # Create conversation summary
                conversation_summary = f"{int(row.incoming_messages or 0)} messages from user, {int(row.outgoing_messages or 0)} from bot"
                if row.handoff_requests and row.handoff_requests > 0:
                    conversation_summary += f", {int(row.handoff_requests)} handoff requests"
                
                # Get predominant sentiment from recent messages
                recent_sentiments = self.db.session.query(MessageLog.llm_sentiment)\
                    .filter_by(user_id=row.id)\
                    .filter(MessageLog.llm_sentiment.isnot(None))\
                    .order_by(desc(MessageLog.timestamp))\
                    .limit(5).all()
                
                sentiment_counts = {}
                for s in recent_sentiments:
                    if s[0]:
                        sentiment_counts[s[0]] = sentiment_counts.get(s[0], 0) + 1
                
                if sentiment_counts:
                    predominant_sentiment = max(sentiment_counts.keys(), key=lambda x: sentiment_counts[x])
                else:
                    predominant_sentiment = 'neutral'
                
                # Aggregate tags from recent messages
                recent_tags = self.db.session.query(MessageLog.llm_tags)\
                    .filter_by(user_id=row.id)\
                    .filter(MessageLog.llm_tags.isnot(None))\
                    .order_by(desc(MessageLog.timestamp))\
                    .limit(10).all()
                
                all_tags = []
                for tag_list in recent_tags:
                    if tag_list[0]:
                        all_tags.extend(tag_list[0])
                
                # Get unique tags
                unique_tags = list(set(all_tags)) if all_tags else []
                
                # Create user location string
                location_parts = [row.city, row.region, row.country]
                user_location = ', '.join(filter(None, location_parts)) if any(location_parts) else None
                
                # Create user display name
                user_name = row.name or row.first_name or None
                
                conversations.append({
                    'id': row.id,
                    'user_phone': row.phone_number,
                    'user_id': row.id,
                    'user_name': user_name,
                    'user_location': user_location,
                    'username': row.username,
                    'first_name': row.first_name,
                    'last_name': row.last_name,
                    'language_code': row.language_code,
                    'is_premium': row.is_premium,
                    'ip_address': row.ip_address,
                    'country': row.country,
                    'region': row.region,
                    'city': row.city,
                    'status': row.status,
                    'current_day': row.current_day,
                    'join_date': row.join_date.isoformat() if row.join_date else None,
                    'timestamp': row.latest_message_time.isoformat() if row.latest_message_time else None,
                    'total_messages': int(row.total_messages or 0),
                    'conversation_summary': conversation_summary,
                    'raw_text': recent_message.raw_text[:100] + ('...' if len(recent_message.raw_text) > 100 else '') if recent_message else 'No messages',
                    'direction': 'Conversation',  # Change to indicate this is consolidated
                    'llm_sentiment': predominant_sentiment,
                    'llm_tags': unique_tags,
                    'is_human_handoff': bool(row.handoff_requests and row.handoff_requests > 0)
                })
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'conversations': conversations,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total': total_count,
                    'pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting consolidated user conversations: {e}")
            return {
                'conversations': [],
                'pagination': {
                    'page': 1,
                    'limit': limit,
                    'total': 0,
                    'pages': 0,
                    'has_next': False,
                    'has_prev': False
                }
            }
    
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
    
    def get_chat_management_stats(self, filters: Dict = None, bot_id: int = None) -> Dict:
        """Get statistics for chat management dashboard"""
        try:
            base_query = self.db.session.query(MessageLog).join(User)
            
            # Add bot filtering if specified
            if bot_id is not None:
                base_query = base_query.filter(User.bot_id == bot_id)
            
            if filters:
                base_query = self._apply_message_filters(base_query, filters)
            
            total_chats = base_query.count()
            
            # Human handoff count
            handoff_count = base_query.filter(MessageLog.is_human_handoff == True).count()
            
            # Today's messages
            today = datetime.utcnow().date()
            today_messages = base_query.filter(
                func.date(MessageLog.timestamp) == today
            ).count()
            
            # Active users (messaged in last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            active_users = self.db.session.query(User).filter(
                User.last_message_date >= week_ago
            ).count() if hasattr(User, 'last_message_date') else 0
            
            return {
                'total_chats': total_chats,
                'handoff_count': handoff_count,
                'today_messages': today_messages,
                'active_users': active_users
            }
        except Exception as e:
            logger.error(f"Error getting chat management stats: {e}")
            return {'total_chats': 0, 'handoff_count': 0, 'today_messages': 0, 'active_users': 0}
    
    def get_filtered_messages(self, page: int = 1, limit: int = 20, sort_field: str = 'timestamp',
                            sort_order: str = 'desc', filters: Dict = None) -> Dict:
        """Get filtered and paginated messages"""
        try:
            # Build base query
            query = self.db.session.query(
                MessageLog.id,
                MessageLog.timestamp,
                MessageLog.direction,
                MessageLog.raw_text,
                MessageLog.llm_sentiment,
                MessageLog.llm_tags,
                MessageLog.llm_confidence,
                MessageLog.is_human_handoff,
                User.phone_number.label('user_phone'),
                User.current_day.label('user_day'),
                User.id.label('user_id')
            ).join(User)
            
            # Apply filters
            if filters:
                query = self._apply_message_filters(query, filters)
            
            # Apply sorting
            sort_column = getattr(MessageLog, sort_field, MessageLog.timestamp)
            if sort_order.lower() == 'desc':
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            messages = query.offset(offset).limit(limit).all()
            
            # Convert to dictionaries
            message_list = []
            for msg in messages:
                message_list.append({
                    'id': msg.id,
                    'timestamp': msg.timestamp.isoformat(),
                    'direction': msg.direction,
                    'raw_text': msg.raw_text,
                    'llm_sentiment': msg.llm_sentiment,
                    'llm_tags': msg.llm_tags or [],
                    'llm_confidence': msg.llm_confidence,
                    'is_human_handoff': msg.is_human_handoff,
                    'user_phone': msg.user_phone,
                    'user_day': msg.user_day,
                    'user_id': msg.user_id
                })
            
            # Calculate pagination info
            total_pages = (total + limit - 1) // limit
            
            return {
                'messages': message_list,
                'pagination': {
                    'current_page': page,
                    'total_pages': total_pages,
                    'total': total,
                    'limit': limit
                }
            }
        except Exception as e:
            logger.error(f"Error getting filtered messages: {e}")
            return {'messages': [], 'pagination': {'current_page': 1, 'total_pages': 0, 'total': 0, 'limit': limit}}
    
    def _apply_message_filters(self, query, filters: Dict):
        """Apply filters to message query"""
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(func.date(MessageLog.timestamp) >= date_from)
            except ValueError:
                pass
                
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(func.date(MessageLog.timestamp) <= date_to)
            except ValueError:
                pass
        
        if filters.get('user_search'):
            search_term = f"%{filters['user_search']}%"
            query = query.filter(User.phone_number.like(search_term))
        
        if filters.get('sentiment'):
            query = query.filter(MessageLog.llm_sentiment == filters['sentiment'])
        
        if filters.get('tags'):
            tag_list = filters['tags'].split(',')
            # Filter messages that contain any of the specified tags
            tag_conditions = []
            for tag in tag_list:
                tag_conditions.append(MessageLog.llm_tags.contains([tag.strip()]))
            if tag_conditions:
                query = query.filter(or_(*tag_conditions))
        
        if filters.get('human_handoff'):
            query = query.filter(MessageLog.is_human_handoff == True)
        
        if filters.get('direction'):
            query = query.filter(MessageLog.direction == filters['direction'])
        
        return query
    
    def get_message_details(self, message_id: int) -> Dict:
        """Get detailed information about a specific message"""
        try:
            message = self.db.session.query(
                MessageLog.id,
                MessageLog.timestamp,
                MessageLog.direction,
                MessageLog.raw_text,
                MessageLog.llm_sentiment,
                MessageLog.llm_tags,
                MessageLog.llm_confidence,
                MessageLog.is_human_handoff,
                User.phone_number.label('user_phone'),
                User.current_day.label('user_day'),
                User.id.label('user_id')
            ).join(User).filter(MessageLog.id == message_id).first()
            
            if not message:
                return None
            
            return {
                'id': message.id,
                'timestamp': message.timestamp.isoformat(),
                'direction': message.direction,
                'raw_text': message.raw_text,
                'llm_sentiment': message.llm_sentiment,
                'llm_tags': message.llm_tags or [],
                'llm_confidence': message.llm_confidence,
                'is_human_handoff': message.is_human_handoff,
                'user_phone': message.user_phone,
                'user_day': message.user_day,
                'user_id': message.user_id
            }
        except Exception as e:
            logger.error(f"Error getting message details: {e}")
            return None
    
    def export_filtered_messages(self, filters: Dict = None) -> List[Dict]:
        """Export filtered messages for CSV download"""
        try:
            query = self.db.session.query(
                MessageLog.timestamp,
                MessageLog.direction,
                MessageLog.raw_text,
                MessageLog.llm_sentiment,
                MessageLog.llm_tags,
                MessageLog.is_human_handoff,
                User.phone_number.label('user_phone'),
                User.current_day.label('user_day')
            ).join(User)
            
            # Apply filters
            if filters:
                query = self._apply_message_filters(query, filters)
            
            # Order by timestamp desc
            query = query.order_by(desc(MessageLog.timestamp))
            
            messages = query.all()
            
            # Convert to list of dictionaries
            export_data = []
            for msg in messages:
                export_data.append({
                    'timestamp': msg.timestamp.isoformat(),
                    'user_phone': msg.user_phone,
                    'direction': msg.direction,
                    'raw_text': msg.raw_text,
                    'llm_sentiment': msg.llm_sentiment or '',
                    'llm_tags': msg.llm_tags or [],
                    'is_human_handoff': msg.is_human_handoff,
                    'user_day': msg.user_day or ''
                })
            
            return export_data
        except Exception as e:
            logger.error(f"Error exporting messages: {e}")
            return []

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