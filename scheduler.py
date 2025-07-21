import logging
from datetime import datetime
from typing import List
from db_manager import DatabaseManager
from services import WhatsAppService, GeminiService
import time

logger = logging.getLogger(__name__)

class ContentScheduler:
    """Handles scheduled content delivery and user progression"""
    
    def __init__(self, db: DatabaseManager, whatsapp_service: WhatsAppService, gemini_service: GeminiService):
        self.db = db
        self.whatsapp_service = whatsapp_service
        self.gemini_service = gemini_service
    
    def send_daily_content(self) -> None:
        """Send daily content to all active users"""
        try:
            active_users = self.db.get_active_users()
            logger.info(f"Sending daily content to {len(active_users)} active users")
            
            for user in active_users:
                try:
                    self.send_content_to_user(user.phone_number)
                    # Small delay between users to avoid rate limiting
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error sending content to {user.phone_number}: {e}")
            
            logger.info("Daily content delivery completed")
            
        except Exception as e:
            logger.error(f"Error in daily content delivery: {e}")
    
    def send_content_to_user(self, phone_number: str) -> bool:
        """Send content to a specific user and advance their journey"""
        try:
            user = self.db.get_user_by_phone(phone_number)
            if not user or user.status != 'active':
                logger.warning(f"User {phone_number} is not active, skipping content delivery")
                return False
            
            current_day = user.current_day
            
            # Check if user has completed the journey
            if current_day > 30:
                self._complete_user_journey(phone_number, user)
                return True
            
            # Get content for current day
            content = self.db.get_content_by_day(current_day)
            if not content:
                logger.error(f"No content found for day {current_day}")
                return False
            
            # Send the main content
            success = self._deliver_content(phone_number, content.to_dict())
            
            if success:
                # Schedule reflection question after a short delay
                self._schedule_reflection_question(phone_number, content.to_dict(), delay_minutes=2)
                
                # Advance user to next day
                next_day = current_day + 1
                
                # Complete journey if this was day 30
                if current_day == 30:
                    self.db.update_user(phone_number, current_day=next_day, status='completed', completion_date=datetime.now())
                else:
                    self.db.update_user(phone_number, current_day=next_day)
                
                logger.info(f"User {phone_number} advanced to day {next_day}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending content to user {phone_number}: {e}")
            return False
    
    def _deliver_content(self, phone_number: str, content: dict) -> bool:
        """Deliver the actual content based on media type"""
        try:
            media_type = content.get('media_type', 'text')
            content_text = content.get('content_text', '')
            media_url = content.get('media_url')
            day = content.get('day', 0)
            
            # Add day header
            message = f"📖 Day {day} - Faith Journey\n\n{content_text}"
            
            if media_type == 'text' or not media_url:
                # Send as text message
                return self.whatsapp_service.send_message(phone_number, message)
            
            elif media_type in ['image', 'video', 'audio']:
                # Send text first, then media
                text_sent = self.whatsapp_service.send_message(phone_number, message)
                if text_sent:
                    # Small delay before sending media
                    time.sleep(1)
                    return self.whatsapp_service.send_media_message(
                        phone_number, 
                        media_type, 
                        media_url
                    )
                return False
            
            else:
                # Default to text message
                return self.whatsapp_service.send_message(phone_number, message)
                
        except Exception as e:
            logger.error(f"Error delivering content: {e}")
            return False
    
    def _schedule_reflection_question(self, phone_number: str, content: dict, delay_minutes: int = 2):
        """Schedule reflection question to be sent after delay"""
        try:
            import threading
            import time
            
            def send_reflection():
                try:
                    time.sleep(delay_minutes * 60)  # Convert to seconds
                    reflection_question = content.get('reflection_question', '')
                    if reflection_question:
                        message = f"💭 Reflection Question:\n\n{reflection_question}\n\nTake your time to think about it and share your thoughts when you're ready."
                        self.whatsapp_service.send_message(phone_number, message)
                        logger.info(f"Reflection question sent to {phone_number}")
                except Exception as e:
                    logger.error(f"Error sending reflection question to {phone_number}: {e}")
            
            # Start thread to send reflection question after delay
            reflection_thread = threading.Thread(target=send_reflection, daemon=True)
            reflection_thread.start()
            
        except Exception as e:
            logger.error(f"Error scheduling reflection question for {phone_number}: {e}")
    
    def _complete_user_journey(self, phone_number: str, user):
        """Complete user's 30-day journey"""
        try:
            completion_message = (
                "🎉 Congratulations! You have completed your 30-day Faith Journey!\n\n"
                "Thank you for taking this journey to learn about Isa al-Masih (Jesus). "
                "We hope these 30 days have been meaningful and enriching for you.\n\n"
                "If you'd like to continue exploring or have any questions, "
                "feel free to reach out by typing 'talk to someone'.\n\n"
                "May peace be with you. 🙏"
            )
            
            self.whatsapp_service.send_message(phone_number, completion_message)
            
            # Update user status to completed
            self.db.update_user(phone_number, status='completed', completion_date=datetime.now())
            logger.info(f"User {phone_number} completed their 30-day journey")
            
        except Exception as e:
            logger.error(f"Error completing journey for user {phone_number}: {e}")
    
    def get_user_progress(self, phone_number: str) -> dict:
        """Get user's current progress"""
        try:
            user = self.db.get_user_by_phone(phone_number)
            if not user:
                return {"error": "User not found"}
            
            current_day = user.current_day
            status = user.status
            join_date = user.join_date.isoformat() if user.join_date else ''
            
            progress_percentage = min(100, (current_day / 30) * 100)
            
            return {
                "phone_number": phone_number,
                "status": status,
                "current_day": current_day,
                "progress_percentage": progress_percentage,
                "join_date": join_date,
                "days_remaining": max(0, 30 - current_day + 1) if status == 'active' else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting progress for {phone_number}: {e}")
            return {"error": str(e)}
