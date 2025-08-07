import logging
from datetime import datetime
from typing import List
from db_manager import DatabaseManager
from services import WhatsAppService, TelegramService, GeminiService
import time

logger = logging.getLogger(__name__)

class ContentScheduler:
    """Handles scheduled content delivery and user progression"""
    
    def __init__(self, whatsapp_service: WhatsAppService, telegram_service: TelegramService, db: DatabaseManager):
        self.db = db
        self.whatsapp_service = whatsapp_service
        self.telegram_service = telegram_service
    
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
            
            # Check if user already received content for this day (prevent duplicates)
            # Get the most recent message for this user to check if they already got today's content
            recent_messages = self.db.get_user_messages_by_id(user.id, limit=5)
            if recent_messages:
                # Check if any recent message contains content for the current day
                day_content_text = f"Day {current_day}"
                for msg in recent_messages:
                    if msg.direction == 'outgoing' and day_content_text in msg.raw_text:
                        logger.info(f"User {phone_number} already received content for day {current_day}, skipping duplicate")
                        return True
                
            # Get content for current day
            content = self.db.get_content_by_day(current_day, bot_id=user.bot_id)
            if not content:
                logger.error(f"No content found for day {current_day}")
                return False
            
            # Send the main content with reflection question combined
            content_dict = content.to_dict()
            logger.info(f"🔴 Content for day {current_day}: media_type={content_dict.get('media_type')}, media_url={content_dict.get('media_url')}")
            success = self._deliver_content_with_reflection(phone_number, content_dict)
            
            if success:
                # Log the delivered daily content to message history
                self._log_delivered_content(user, content_dict)
                
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
    
    def _deliver_content_with_reflection(self, phone_number: str, content: dict) -> bool:
        """Deliver the actual content based on media type"""
        try:
            media_type = content.get('media_type', 'text')
            content_text = content.get('content', '')  # Updated to match our Content model
            media_url = content.get('media_url')
            day = content.get('day_number', 0)  # Updated to match our Content model
            title = content.get('title', 'Faith Journey')  # Add title
            
            # Add day header with title and reflection question
            reflection_question = content.get('reflection_question', '')
            message = f"📖 Day {day} - {title}\n\n{content_text}"
            
            # Add reflection question to the same message
            if reflection_question:
                message += f"\n\n💭 Reflection Question:\n{reflection_question}\n\nTake your time to think about it and share your thoughts when you're ready."
            
            # Determine platform and service based on phone_number and user's bot_id
            if phone_number.startswith('tg_'):
                # Telegram user - get bot-specific service
                platform = "telegram"
                chat_id = phone_number[3:]  # Remove 'tg_' prefix
                
                # Get user to determine bot_id for service selection
                user = self.db.get_user_by_phone(phone_number)
                if user and user.bot_id:
                    # Get bot-specific service by creating it directly from the bot's token
                    from models import Bot
                    bot = Bot.query.get(user.bot_id)
                    if bot and bot.telegram_bot_token:
                        telegram_service = TelegramService(bot.telegram_bot_token)
                        logger.info(f"Using bot-specific service for bot_id {user.bot_id}")
                    else:
                        # Fallback to default service
                        telegram_service = self.telegram_service
                        logger.info(f"Using default service for bot_id {user.bot_id} (no token found)")
                else:
                    # Use Bot 1's service (default)
                    telegram_service = self.telegram_service
                    logger.info("Using default service (no user found)")
                
                if media_type == 'text' or not media_url:
                    return telegram_service.send_message(chat_id, message)
                elif media_type in ['image', 'video', 'audio']:
                    # For Telegram, send media first, then text content
                    media_sent = False
                    if media_url:
                        if media_type == 'image':
                            # Send photo via Telegram API first
                            media_sent = telegram_service.send_photo(chat_id, media_url)
                            logger.info(f"🔴 TELEGRAM: Photo sent to {chat_id}, success: {media_sent}")
                            if not media_sent:
                                # If photo failed (likely chat not found), mark user as inactive
                                logger.warning(f"Failed to send photo to Telegram chat {chat_id} - marking user as inactive")
                                user = self.db.get_user_by_phone(phone_number)
                                if user:
                                    user.status = 'inactive'
                                    self.db.db.session.commit()
                        elif media_type == 'video':
                            # Send video via Telegram API first
                            media_sent = telegram_service.send_video(chat_id, media_url)
                            logger.info(f"🔴 TELEGRAM: Video sent to {chat_id}, success: {media_sent}")
                        elif media_type == 'audio':
                            # Send audio via Telegram API first
                            media_sent = telegram_service.send_audio(chat_id, media_url)
                            logger.info(f"🔴 TELEGRAM: Audio sent to {chat_id}, success: {media_sent}")
                        else:
                            # For other media types, log but don't implement yet
                            logger.info(f"Media content delivery to Telegram user {chat_id} - {media_type} not yet implemented, media URL: {media_url}")
                    
                    # Now send text content after media
                    if media_sent:
                        time.sleep(1)
                        text_sent = telegram_service.send_message(chat_id, message)
                        return text_sent
                    else:
                        # If media failed, still send text
                        return telegram_service.send_message(chat_id, message)
                else:
                    return telegram_service.send_message(chat_id, message)
            else:
                # WhatsApp user (default)
                if media_type == 'text' or not media_url:
                    return self.whatsapp_service.send_message(phone_number, message)
                elif media_type in ['image', 'video', 'audio']:
                    # For WhatsApp, send media first (simulated), then text content
                    media_sent = False
                    if media_url:
                        if media_type == 'image':
                            # Send image via WhatsApp simulation (media delivery is simulated)
                            logger.info(f"WhatsApp image delivery simulated for {phone_number}: {media_url}")
                            media_sent = True
                        elif media_type == 'video':
                            # Send video via WhatsApp simulation
                            logger.info(f"WhatsApp video delivery simulated for {phone_number}: {media_url}")
                            media_sent = True
                        elif media_type == 'audio':
                            # Send audio via WhatsApp simulation
                            logger.info(f"WhatsApp audio delivery simulated for {phone_number}: {media_url}")
                            media_sent = True
                        else:
                            # For other media types, log but don't implement yet
                            logger.info(f"Media content delivery to WhatsApp user {phone_number} - {media_type} not yet implemented, media URL: {media_url}")
                    
                    # Now send text content after media
                    if media_sent:
                        time.sleep(1)
                        text_sent = self.whatsapp_service.send_message(phone_number, message)
                        return text_sent
                    else:
                        # If media failed, still send text
                        return self.whatsapp_service.send_message(phone_number, message)
                else:
                    return self.whatsapp_service.send_message(phone_number, message)
                
        except Exception as e:
            logger.error(f"Error delivering content: {e}")
            return False
    

    def _log_delivered_content(self, user, content: dict):
        """Log the delivered daily content to message history"""
        try:
            # Create the content message that was sent
            day = content.get('day_number', 0)
            title = content.get('title', 'Faith Journey')
            content_text = content.get('content', '')
            media_type = content.get('media_type', 'text')
            
            message = f"📖 Day {day} - {title}\n\n{content_text}"
            
            # Create appropriate tags
            tags = [
                'DAILY_CONTENT',
                'SCHEDULER_DELIVERY',
                f'Day_{day}',
                media_type.upper() if media_type else 'TEXT'
            ]
            
            # Add content-specific tags if available
            content_tags = content.get('tags')
            if content_tags and isinstance(content_tags, list):
                tags.extend(content_tags)
            
            # Log the message
            self.db.log_message(
                user=user,
                direction='outgoing',
                raw_text=message,
                sentiment='positive',
                tags=tags,
                confidence=1.0
            )
            
            logger.info(f"Daily content logged to message history for user {user.phone_number} (Day {day})")
            
        except Exception as e:
            logger.error(f"Error logging delivered content: {e}")
    
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
