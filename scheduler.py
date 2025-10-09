import logging
import os
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
        """Send daily content to users based on their bot's delivery interval"""
        try:
            from models import Bot, User
            from main import app
            
            # Get all active bots and check their delivery intervals
            bots = Bot.query.filter(Bot.status == 'active').all()
            
            for bot in bots:
                try:
                    # Check if it's time to send content for this bot
                    if self._should_send_content_for_bot(bot):
                        # Get active users for this bot
                        active_users = User.query.filter(
                            User.bot_id == bot.id,
                            User.status == 'active'
                        ).all()
                        
                        logger.info(f"Sending content to {len(active_users)} users for bot '{bot.name}' (interval: {bot.delivery_interval_minutes} min)")
                        
                        for user in active_users:
                            try:
                                self.send_content_to_user(user.phone_number)
                                # Small delay between users to avoid rate limiting
                                time.sleep(1)
                            except Exception as e:
                                logger.error(f"Error sending content to {user.phone_number}: {e}")
                        
                        # Update the bot's last content delivery time
                        self._update_bot_last_delivery(bot.id)
                        
                except Exception as e:
                    logger.error(f"Error processing bot {bot.name}: {e}")
            
            logger.info("Daily content delivery check completed")
            
        except Exception as e:
            logger.error(f"Error in daily content delivery: {e}")
    
    def _should_send_content_for_bot(self, bot) -> bool:
        """Check if it's time to send content for a specific bot based on its delivery interval"""
        try:
            from models import SystemSettings
            import datetime
            
            # Get the last delivery time for this bot
            key = f"bot_{bot.id}_last_delivery"
            setting = SystemSettings.query.filter_by(key=key).first()
            
            if not setting:
                # First time sending content for this bot
                return True
            
            # Parse the last delivery time
            last_delivery = datetime.datetime.fromisoformat(setting.value)
            
            # Calculate minutes since last delivery
            minutes_since = (datetime.datetime.utcnow() - last_delivery).total_seconds() / 60
            
            # Check if enough time has passed based on bot's interval
            return minutes_since >= bot.delivery_interval_minutes
            
        except Exception as e:
            logger.error(f"Error checking delivery time for bot {bot.id}: {e}")
            return False
    
    def _update_bot_last_delivery(self, bot_id: int) -> None:
        """Update the last delivery time for a bot"""
        try:
            from models import SystemSettings, db
            import datetime
            
            key = f"bot_{bot_id}_last_delivery"
            setting = SystemSettings.query.filter_by(key=key).first()
            
            if setting:
                setting.value = datetime.datetime.utcnow().isoformat()
                setting.updated_at = datetime.datetime.utcnow()
            else:
                setting = SystemSettings()
                setting.key = key
                setting.value = datetime.datetime.utcnow().isoformat()
                setting.description = f"Last content delivery time for bot {bot_id}"
                db.session.add(setting)
            
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error updating last delivery time for bot {bot_id}: {e}")
    
    def send_content_to_user(self, phone_number: str) -> bool:
        """Send content to a specific user and advance their journey with atomic pre-delivery lock"""
        lock_key = f"delivery_lock_{phone_number}"
        lock_acquired = False
        
        try:
            # ATOMIC PRE-DELIVERY LOCK - Create delivery intent BEFORE checking anything
            from models import db, SystemSettings
            from datetime import datetime, timedelta
            from sqlalchemy import text
            
            # Try to atomically create a delivery lock for this user
            now = datetime.utcnow()
            lock_expires = now + timedelta(minutes=5)  # Lock expires in 5 minutes (handles slow media uploads)
            
            try:
                # Use raw SQL with INSERT ... ON CONFLICT for true atomicity
                result = db.session.execute(
                    text("""
                        INSERT INTO system_settings (key, value, description, updated_at)
                        VALUES (:key, :value, :description, :updated_at)
                        ON CONFLICT (key) DO NOTHING
                        RETURNING key
                    """),
                    {
                        'key': lock_key,
                        'value': lock_expires.isoformat(),
                        'description': f'Content delivery lock for {phone_number}',
                        'updated_at': now
                    }
                )
                
                # If INSERT succeeded, we got the lock
                inserted = result.fetchone()
                if inserted:
                    db.session.commit()
                    lock_acquired = True
                    logger.info(f"🔒 Acquired new lock for {phone_number}")
                else:
                    # Lock already exists - check if it's stale (within same transaction)
                    existing_lock = SystemSettings.query.filter_by(key=lock_key).with_for_update(nowait=False).first()
                    
                    if not existing_lock:
                        # Lock was deleted between operations - defensive fallback
                        logger.warning(f"Lock disappeared for {phone_number}, skipping delivery")
                        db.session.rollback()
                        return True
                    
                    lock_age = (now - existing_lock.updated_at).total_seconds()
                    
                    if lock_age < 180:  # 3 minutes - increased for slow deliveries
                        logger.info(f"🔒 ATOMIC LOCK: Another worker is delivering content to {phone_number} (lock age: {lock_age:.1f}s), skipping")
                        db.session.rollback()
                        return True
                    else:
                        # Lock is stale, take it over
                        existing_lock.value = lock_expires.isoformat()
                        existing_lock.updated_at = now
                        db.session.commit()
                        lock_acquired = True
                        logger.info(f"🔓 Acquired stale lock for {phone_number} (was {lock_age:.1f}s old)")
                    
            except Exception as lock_error:
                logger.warning(f"Lock acquisition error for {phone_number}: {lock_error}")
                db.session.rollback()
                return False
            
            # Now proceed with normal delivery (lock is held)
            user = self.db.get_user_by_phone(phone_number)
            if not user or user.status != 'active':
                logger.warning(f"User {phone_number} is not active, skipping content delivery")
                return False
            
            current_day = user.current_day
            
            # Check if user has completed the journey
            if current_day > 30:
                self._complete_user_journey(phone_number, user)
                return True
            
            # ULTRA-STRONG duplicate prevention - multiple layers of protection
            
            # Check recent messages for any outgoing content
            recent_messages = self.db.get_user_messages_by_id(user.id, limit=10)
            if recent_messages:
                now = datetime.now()
                
                # Layer 1: Check for exact day content within last 24 hours
                day_content_text = f"Day {current_day}"
                day_content_emoji = f"📖 Day {current_day}"
                twenty_four_hours_ago = now - timedelta(hours=24)
                
                for msg in recent_messages:
                    if (msg.direction == 'outgoing' and 
                        msg.timestamp > twenty_four_hours_ago and 
                        (day_content_text in msg.raw_text or day_content_emoji in msg.raw_text)):
                        logger.info(f"🚫 DAY DUPLICATE PREVENTION: User {phone_number} already received Day {current_day} content in last 24h, skipping")
                        return True
                
                # Layer 2: Check for ANY outgoing message within last 5 minutes (prevents rapid-fire duplicates)
                five_minutes_ago = now - timedelta(minutes=5)
                for msg in recent_messages:
                    if (msg.direction == 'outgoing' and 
                        msg.timestamp > five_minutes_ago):
                        logger.info(f"🚫 RAPID-FIRE PREVENTION: User {phone_number} received message within 5 min, skipping (timestamp: {msg.timestamp})")
                        return True
                
                # Layer 3: Bot-specific delivery interval check  
                bot_id = user.bot_id
                from models import Bot
                bot = Bot.query.get(bot_id)
                if bot and bot.delivery_interval_minutes:
                    interval_ago = now - timedelta(minutes=bot.delivery_interval_minutes)
                    for msg in recent_messages:
                        if (msg.direction == 'outgoing' and 
                            msg.timestamp > interval_ago):
                            logger.info(f"🚫 BOT INTERVAL PREVENTION: User {phone_number} within {bot.delivery_interval_minutes}min interval, skipping")
                            return True
                
            # Get content for current day
            content = self.db.get_content_by_day(current_day, bot_id=user.bot_id)
            if not content:
                logger.warning(f"No content found for day {current_day} for user {phone_number} (bot_id: {user.bot_id})")
                # Handle users who have completed available content
                self._handle_content_completion(phone_number, current_day, user)
                return True  # Return True so we don't keep retrying
            
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
        finally:
            # ALWAYS release the lock after delivery attempt (success or failure)
            if lock_acquired:
                try:
                    from models import db, SystemSettings
                    lock = SystemSettings.query.filter_by(key=lock_key).first()
                    if lock:
                        db.session.delete(lock)
                        db.session.commit()
                        logger.info(f"🔓 Released lock for {phone_number}")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to release lock for {phone_number}: {cleanup_error}")
                    try:
                        db.session.rollback()
                    except:
                        pass
    
    def _deliver_content_with_reflection(self, phone_number: str, content: dict) -> bool:
        """Deliver the actual content based on media type"""
        try:
            media_type = content.get('media_type', 'text')
            content_text = content.get('content', '')  # Updated to match our Content model
            day = content.get('day_number', 0)  # Updated to match our Content model
            title = content.get('title', 'Faith Journey')  # Add title
            
            # Construct proper media URL from filenames with file validation
            media_url = None
            if media_type == 'image' and content.get('image_filename'):
                # Validate file exists before constructing URL
                file_path = f"static/uploads/images/{content.get('image_filename')}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/images/{content.get('image_filename')}"
                    logger.info(f"✅ Image file validated: {file_path}")
                else:
                    logger.error(f"❌ Image file not found: {file_path}")
                    logger.warning(f"Available image files: {os.listdir('static/uploads/images/') if os.path.exists('static/uploads/images/') else 'Directory not found'}")
                    media_type = 'text'  # Fallback to text-only
            elif media_type == 'video' and content.get('video_filename'):
                file_path = f"static/uploads/videos/{content.get('video_filename')}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/videos/{content.get('video_filename')}"
                else:
                    logger.error(f"❌ Video file not found: {file_path}")
                    media_type = 'text'  # Fallback to text-only
            elif media_type == 'audio' and content.get('audio_filename'):
                file_path = f"static/uploads/audio/{content.get('audio_filename')}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/audio/{content.get('audio_filename')}"
                else:
                    logger.error(f"❌ Audio file not found: {file_path}")
                    media_type = 'text'  # Fallback to text-only
            
            # Add day header with title and reflection question
            reflection_question = content.get('reflection_question', '')
            message = f"📖 Day {day} - {title}\n\n{content_text}"
            
            # Add reflection question to the same message
            if reflection_question:
                message += f"\n\n{reflection_question}"
            
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
                
                content_delivered = False
                if media_type == 'text' or not media_url:
                    content_delivered = telegram_service.send_message(chat_id, message)
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
                        content_delivered = telegram_service.send_message(chat_id, message)
                    else:
                        # If media failed, still send text
                        content_delivered = telegram_service.send_message(chat_id, message)
                else:
                    content_delivered = telegram_service.send_message(chat_id, message)
                
                # Send confirmation buttons after content is delivered
                if content_delivered:
                    time.sleep(5)  # 5 second pause before asking for confirmation
                    self._send_content_confirmation_buttons(phone_number, platform, telegram_service, day)
                
                return content_delivered
            else:
                # WhatsApp user - use bot-specific service
                platform = "whatsapp"
                user = self.db.get_user_by_phone(phone_number)
                if user and user.bot_id:
                    from main import get_whatsapp_service_for_bot
                    whatsapp_service = get_whatsapp_service_for_bot(user.bot_id)
                    logger.info(f"Using bot-specific WhatsApp service for bot_id {user.bot_id}")
                else:
                    whatsapp_service = self.whatsapp_service
                
                content_delivered = False
                if media_type == 'text' or not media_url:
                    content_delivered = whatsapp_service.send_message(phone_number, message)
                elif media_type in ['image', 'video', 'audio']:
                    # For WhatsApp, send media WITH text as caption (single message for proper order)
                    if media_url:
                        if media_type == 'image':
                            # Send image with message text as caption
                            content_delivered = whatsapp_service.send_media_message(phone_number, 'image', media_url, caption=message)
                            logger.info(f"WhatsApp image sent with caption to {phone_number}: {media_url}")
                        elif media_type == 'video':
                            # Send video with message text as caption
                            content_delivered = whatsapp_service.send_video(phone_number, media_url, caption=message)
                            logger.info(f"WhatsApp video sent with caption to {phone_number}: {media_url}")
                        elif media_type == 'audio':
                            # Audio doesn't support caption in WhatsApp, send separately
                            media_sent = whatsapp_service.send_media_message(phone_number, 'audio', media_url)
                            if media_sent:
                                time.sleep(1)
                                content_delivered = whatsapp_service.send_message(phone_number, message)
                            else:
                                content_delivered = whatsapp_service.send_message(phone_number, message)
                            logger.info(f"WhatsApp audio sent to {phone_number}: {media_url}")
                        else:
                            # For other media types, log but don't implement yet
                            logger.info(f"Media content delivery to WhatsApp user {phone_number} - {media_type} not yet implemented, media URL: {media_url}")
                            content_delivered = whatsapp_service.send_message(phone_number, message)
                    else:
                        # If no media URL, send text only
                        content_delivered = whatsapp_service.send_message(phone_number, message)
                else:
                    content_delivered = whatsapp_service.send_message(phone_number, message)
                
                # Send confirmation buttons after content is delivered
                if content_delivered:
                    time.sleep(5)  # 5 second pause before asking for confirmation
                    self._send_content_confirmation_buttons(phone_number, platform, whatsapp_service, day)
                
                return content_delivered
                
        except Exception as e:
            logger.error(f"Error delivering content: {e}")
            return False
    
    def _send_content_confirmation_buttons(self, phone_number: str, platform: str, service, day: int):
        """Send confirmation buttons asking if user has read the content"""
        try:
            # Get user to check bot language
            user = self.db.get_user_by_phone(phone_number)
            if not user:
                return False
            
            # Get bot for language check
            from models import Bot, Content
            bot = Bot.query.get(user.bot_id) if user.bot_id else None
            is_indonesian = bot and "indonesia" in bot.name.lower() if bot else False
            
            # Try to get custom confirmation messages from the content object
            content = Content.query.filter_by(bot_id=user.bot_id, day_number=day).first()
            
            # Use custom messages if available, otherwise use defaults
            if content and content.confirmation_message:
                confirmation_message = content.confirmation_message
            else:
                # Default confirmation message based on language
                if is_indonesian:
                    confirmation_message = f"📌 Apakah Anda sudah membaca pesan Hari {day}?"
                else:
                    confirmation_message = f"📌 Have you read today's Day {day} message?"
            
            if content and content.yes_button_text:
                yes_text = content.yes_button_text
            else:
                # Default yes button text based on language
                if is_indonesian:
                    yes_text = "✅ Ya, sudah baca"
                else:
                    yes_text = "✅ Yes, I've read it"
            
            if content and content.no_button_text:
                no_text = content.no_button_text
            else:
                # Default no button text based on language
                if is_indonesian:
                    no_text = "⏰ Nanti saja"
                else:
                    no_text = "⏰ Not yet"
            
            # Send buttons based on platform
            if platform == "telegram":
                # Telegram inline keyboard
                chat_id = phone_number[3:] if phone_number.startswith('tg_') else phone_number
                buttons = [
                    [{"text": yes_text, "callback_data": f"content_confirm_yes_{day}"}],
                    [{"text": no_text, "callback_data": f"content_confirm_no_{day}"}]
                ]
                service.send_message_with_inline_keyboard(chat_id, confirmation_message, buttons)
                logger.info(f"Sent content confirmation buttons to Telegram user {chat_id} for Day {day}")
            else:
                # WhatsApp interactive buttons
                buttons = [
                    {"id": f"content_confirm_yes_{day}", "title": yes_text[:20]},  # WhatsApp has 20 char limit
                    {"id": f"content_confirm_no_{day}", "title": no_text[:20]}
                ]
                service.send_interactive_buttons(phone_number, confirmation_message, buttons)
                logger.info(f"Sent content confirmation buttons to WhatsApp user {phone_number} for Day {day}")
            
            return True
        except Exception as e:
            logger.error(f"Error sending confirmation buttons: {e}")
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
    
    def _handle_content_completion(self, phone_number: str, current_day: int, user) -> None:
        """Handle users who have reached the end of available content"""
        try:
            from models import Bot, Content
            
            # Get the bot to check journey duration and available content
            bot = Bot.query.get(user.bot_id)
            if not bot:
                logger.error(f"Bot not found for user {phone_number}")
                return
            
            # Check how many days of content are available for this bot
            available_content = Content.query.filter_by(
                bot_id=user.bot_id,
                content_type='daily',
                is_active=True
            ).count()
            
            logger.info(f"User {phone_number} on day {current_day}, bot has {available_content} days of content")
            
            # **FIX: Check if completion message was already sent in the last 24 hours**
            # This prevents the message from being sent repeatedly every 10 minutes
            recent_messages = self.db.get_user_messages_by_id(user.id, limit=20)
            if recent_messages:
                from datetime import timedelta
                twenty_four_hours_ago = datetime.now() - timedelta(hours=24)
                
                for msg in recent_messages:
                    if (msg.direction == 'outgoing' and 
                        msg.timestamp > twenty_four_hours_ago and 
                        "completed the available journey content" in msg.raw_text):
                        logger.info(f"🚫 Completion message already sent to {phone_number} within 24h, skipping duplicate")
                        
                        # Mark user as 'completed' to stop scheduler from checking them repeatedly
                        if user.status == 'active':
                            self.db.update_user(phone_number, status='completed', completion_date=datetime.now())
                            logger.info(f"User {phone_number} marked as completed to prevent duplicate messages")
                        
                        return  # Don't send the message again
            
            # Determine platform
            platform = 'telegram' if phone_number.startswith('tg_') else 'whatsapp'
            
            # Get completion message from bot (with fallback to default)
            completion_message = bot.completion_message if bot.completion_message else (
                f"🎉 You've completed the available journey content!\n\n"
                f"Thank you for taking this journey with us. "
                f"We hope it has been meaningful and enriching for you.\n\n"
                f"📱 What would you like to do next?\n\n"
                f"• Continue exploring with AI-guided conversations\n"
                f"• Type 'HUMAN' or '/human' to connect with a counselor\n"
                f"• Type 'START' or '/start' to restart the journey\n\n"
                f"Feel free to share your thoughts, ask questions, or explore further. I'm here to help! 💬"
            )
            
            # Send message via appropriate platform
            if platform == 'telegram':
                chat_id = phone_number[3:]  # Remove 'tg_' prefix
                telegram_service = TelegramService(bot.telegram_bot_token) if bot.telegram_bot_token else self.telegram_service
                telegram_service.send_message(chat_id, completion_message)
            else:
                # WhatsApp
                whatsapp_service = WhatsAppService(
                    bot.whatsapp_access_token,
                    bot.whatsapp_phone_number_id
                ) if bot.whatsapp_access_token else self.whatsapp_service
                whatsapp_service.send_message(phone_number, completion_message)
            
            # Log the message
            self.db.log_message(
                user=user,
                direction='outgoing',
                raw_text=completion_message,
                sentiment='positive',
                tags=['CONTENT_COMPLETION', 'SYSTEM_MESSAGE'],
                confidence=1.0
            )
            
            # **FIX: Always mark as completed when no more content is available**
            # This prevents the scheduler from repeatedly checking and sending the message
            self.db.update_user(phone_number, status='completed', completion_date=datetime.now())
            logger.info(f"User {phone_number} marked as completed (no content available for day {current_day})")
            
        except Exception as e:
            logger.error(f"Error handling content completion for {phone_number}: {e}")
    
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
