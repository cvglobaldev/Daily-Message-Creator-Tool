import json
import logging
from datetime import datetime
from replit import db
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages interactions with Replit Database"""
    
    def __init__(self):
        self.db = db
    
    def get_user(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """Get user data by phone number"""
        try:
            user_data = self.db.get(f"users:{phone_number}")
            if user_data:
                return json.loads(user_data) if isinstance(user_data, str) else user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user {phone_number}: {e}")
            return None
    
    def create_or_update_user(self, phone_number: str, user_data: Dict[str, Any]) -> bool:
        """Create or update user data"""
        try:
            self.db[f"users:{phone_number}"] = json.dumps(user_data)
            logger.info(f"User {phone_number} updated successfully")
            return True
        except Exception as e:
            logger.error(f"Error updating user {phone_number}: {e}")
            return False
    
    def get_active_users(self) -> List[str]:
        """Get all active users"""
        try:
            active_users = []
            # Get all user keys
            for key in self.db.keys():
                if key.startswith("users:"):
                    phone_number = key.replace("users:", "")
                    user_data = self.get_user(phone_number)
                    if user_data and user_data.get('status') == 'active':
                        active_users.append(phone_number)
            return active_users
        except Exception as e:
            logger.error(f"Error getting active users: {e}")
            return []
    
    def get_active_users_count(self) -> int:
        """Get count of active users"""
        return len(self.get_active_users())
    
    def get_total_users_count(self) -> int:
        """Get total count of users"""
        try:
            count = 0
            for key in self.db.keys():
                if key.startswith("users:"):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"Error getting total users count: {e}")
            return 0
    
    def get_content(self, day: int) -> Optional[Dict[str, Any]]:
        """Get content for specific day"""
        try:
            content_data = self.db.get(f"content:{day}")
            if content_data:
                return json.loads(content_data) if isinstance(content_data, str) else content_data
            return None
        except Exception as e:
            logger.error(f"Error getting content for day {day}: {e}")
            return None
    
    def set_content(self, day: int, content_data: Dict[str, Any]) -> bool:
        """Set content for specific day"""
        try:
            self.db[f"content:{day}"] = json.dumps(content_data)
            logger.info(f"Content for day {day} set successfully")
            return True
        except Exception as e:
            logger.error(f"Error setting content for day {day}: {e}")
            return False
    
    def log_message(self, log_id: str, message_data: Dict[str, Any]) -> bool:
        """Log a message"""
        try:
            self.db[f"message_logs:{log_id}"] = json.dumps(message_data)
            return True
        except Exception as e:
            logger.error(f"Error logging message {log_id}: {e}")
            return False
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages for dashboard"""
        try:
            messages = []
            for key in self.db.keys():
                if key.startswith("message_logs:"):
                    message_data = self.db.get(key)
                    if message_data:
                        parsed_data = json.loads(message_data) if isinstance(message_data, str) else message_data
                        messages.append(parsed_data)
            
            # Sort by timestamp and return most recent
            messages.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return messages[:limit]
        except Exception as e:
            logger.error(f"Error getting recent messages: {e}")
            return []
    
    def initialize_content(self):
        """Initialize database with sample content for first 3 days"""
        try:
            # Day 1 content
            day1_content = {
                "day": 1,
                "media_type": "text",
                "content_text": "As-salamu alaykum and welcome to your Faith Journey. We're glad you're here. In the holy Injil, the prophet Isa al-Masih (Jesus) is often described as a light. He said, 'I am the light of the world. Whoever follows me will never walk in darkness, but will have the light of life.' (John 8:12)",
                "media_url": None,
                "reflection_question": "What does the idea of 'light' mean to you in your own life?"
            }
            
            # Day 2 content
            day2_content = {
                "day": 2,
                "media_type": "text",
                "content_text": "In Islamic tradition, we know that Allah is Compassionate and Merciful. The Injil teaches us that Isa al-Masih showed this same divine compassion. When he saw people who were hurting, 'he had compassion on them, because they were harassed and helpless, like sheep without a shepherd.' (Matthew 9:36)",
                "media_url": None,
                "reflection_question": "When have you experienced compassion from others? How did it make you feel?"
            }
            
            # Day 3 content
            day3_content = {
                "day": 3,
                "media_type": "video",
                "content_text": "Today, watch this short video about the concept of peace (salaam) in the teachings of Isa al-Masih. Notice how his message of peace connects with what we already understand about Allah's desire for harmony among all people.",
                "media_url": "https://www.youtube.com/shorts/example-peace-video",
                "reflection_question": "What does true peace look like to you? Is it just absence of conflict, or something more?"
            }
            
            # Check if content already exists before setting
            existing_content = self.get_content(1)
            if not existing_content:
                self.set_content(1, day1_content)
                self.set_content(2, day2_content)
                self.set_content(3, day3_content)
                logger.info("Sample content initialized for days 1-3")
            else:
                logger.info("Content already exists, skipping initialization")
                
        except Exception as e:
            logger.error(f"Error initializing content: {e}")
