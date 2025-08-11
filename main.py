import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session, flash, send_from_directory
from models import db, User, Content, MessageLog, AdminUser, Bot
from db_manager import DatabaseManager
from services import WhatsAppService, TelegramService, GeminiService
from scheduler import ContentScheduler
import threading
import time
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm, EditUserForm, ChangePasswordForm, ContentForm
from bot_forms import CreateBotForm, EditBotForm, BotContentForm
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import uuid
from location_utils import extract_telegram_user_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "faith-journey-secret-key")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB max file size for videos

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

# Make current_user available in all templates
@app.context_processor
def inject_user():
    return dict(current_user=current_user)

# Configure PostgreSQL database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize database
db.init_app(app)

# Initialize services
db_manager = DatabaseManager()
whatsapp_service = WhatsAppService()
telegram_service = TelegramService()
gemini_service = GeminiService()
scheduler = ContentScheduler(whatsapp_service, telegram_service, db_manager)

# Global flag to ensure scheduler starts only once
scheduler_started = False

# Cache for bot-specific services
bot_telegram_services = {}

def get_telegram_service_for_bot(bot_id):
    """Get bot-specific Telegram service"""
    logger.info(f"🔥 DEBUG: Getting Telegram service for bot_id {bot_id}")
    try:
        if bot_id not in bot_telegram_services:
            with app.app_context():  # Ensure database context
                # Get bot configuration from database
                bot = Bot.query.get(bot_id)
                logger.info(f"🔥 DEBUG: Bot found: {bot.name if bot else 'None'}, has token: {bool(bot and bot.telegram_bot_token)}")
                if bot and bot.telegram_bot_token:
                    bot_telegram_services[bot_id] = TelegramService(bot.telegram_bot_token)
                    logger.info(f"🔥 DEBUG: Created new TelegramService for bot_id {bot_id}")
                else:
                    # Fallback to default service
                    bot_telegram_services[bot_id] = telegram_service
                    logger.info(f"🔥 DEBUG: Using default TelegramService for bot_id {bot_id}")
        else:
            logger.info(f"🔥 DEBUG: Using cached TelegramService for bot_id {bot_id}")
        return bot_telegram_services[bot_id]
    except Exception as e:
        logger.error(f"🔥 ERROR: Failed to get Telegram service for bot_id {bot_id}: {e}")
        return telegram_service  # Fallback to default

def ensure_scheduler_running():
    """Ensure the scheduler is running (called on first request)"""
    global scheduler_started
    if not scheduler_started:
        with app.app_context():
            # Create database tables if they don't exist
            db.create_all()
            # Initialize sample content if needed
            db_manager.initialize_sample_content()
        # Start the scheduler
        start_scheduler()
        scheduler_started = True

# Keywords that trigger human handoff
HUMAN_HANDOFF_KEYWORDS = [
    "talk to someone", "speak to a person", "pray with me", "need help",
    "counselor", "pastor", "imam", "spiritual guidance", "depression",
    "suicide", "anxiety", "crisis"
]

def start_scheduler():
    """Start the background scheduler in a separate thread"""
    def run_scheduler():
        while True:
            try:
                logger.info("Running content scheduler with bot-specific intervals...")
                with app.app_context():  # Ensure Flask app context for database operations
                    scheduler.send_daily_content()
                # Sleep for 1 minute before checking again (allows for different bot intervals)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Simple dashboard to monitor the system"""
    ensure_scheduler_running()  # Start scheduler on first request
    try:
        # Get basic stats
        user_stats = db_manager.get_user_stats()
        recent_messages = db_manager.get_recent_messages(limit=10)
        human_handoffs = db_manager.get_human_handoff_requests()
        
        # Convert message objects to dicts for template
        recent_messages_data = [msg.to_dict() for msg in recent_messages]
        human_handoff_data = [msg.to_dict() for msg in human_handoffs]
        
        return render_template('dashboard.html', 
                             user_stats=user_stats,
                             recent_messages=recent_messages_data,
                             human_handoffs=human_handoff_data,
                             user=current_user)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Dashboard error: {e}", 500

@app.route('/telegram', methods=['POST'])
@app.route('/telegram/<int:bot_id>', methods=['POST'])
def telegram_webhook(bot_id=1):
    """Handle incoming Telegram messages"""
    try:
        data = request.get_json()
        logger.info(f"🔴 TELEGRAM WEBHOOK RECEIVED: {data}")
        logger.info(f"🔴 Raw request data: {request.get_data()}")
        logger.info(f"🔴 Request method: {request.method}")
        logger.info(f"🔴 Request URL: {request.url}")
        logger.debug(f"Received Telegram webhook data: {data}")
        
        # Handle Telegram update
        if 'message' in data:
            message_data = data['message']
            chat_id = str(message_data.get('chat', {}).get('id', ''))
            message_text = message_data.get('text', '').strip()
            user_info = message_data.get('from', {})
            username = user_info.get('username', '')
            first_name = user_info.get('first_name', '')
            
            if chat_id and message_text:
                # Use chat_id as the phone number equivalent for Telegram
                phone_number = f"tg_{chat_id}"
                
                logger.info(f"Telegram message from {chat_id} ({username}): {message_text}")
                
                # Get client IP address for location data
                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                if client_ip and ',' in client_ip:
                    client_ip = client_ip.split(',')[0].strip()
                
                # Process the message with enhanced user data
                process_incoming_message(phone_number, message_text, platform="telegram", 
                                       user_data=user_info, request_ip=client_ip, bot_id=bot_id)
        
        # Handle callback queries from inline keyboards (2025 feature)
        elif 'callback_query' in data:
            callback_query = data['callback_query']
            callback_query_id = callback_query.get('id')
            callback_data = callback_query.get('data', '')
            chat_id = str(callback_query.get('message', {}).get('chat', {}).get('id', ''))
            user_info = callback_query.get('from', {})
            
            if chat_id and callback_data:
                phone_number = f"tg_{chat_id}"
                
                # Handle different types of callback queries
                if callback_data.startswith('quick_reply:'):
                    reply_text = callback_data.replace('quick_reply:', '')
                    logger.info(f"Quick reply from {chat_id}: {reply_text}")
                    
                    # Get client IP for location data
                    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if client_ip and ',' in client_ip:
                        client_ip = client_ip.split(',')[0].strip()
                    
                    # Process as regular message
                    process_incoming_message(phone_number, reply_text, platform="telegram", 
                                           user_data=user_info, request_ip=client_ip, bot_id=bot_id)
                    
                    # Answer the callback query
                    telegram_service.answer_callback_query(callback_query_id, "Thank you for your response!")
                
                else:
                    # Answer unknown callback queries
                    telegram_service.answer_callback_query(callback_query_id, "Response received")
                
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/whatsapp/<int:bot_id>', methods=['GET', 'POST'])
@app.route('/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook(bot_id=1):
    """Handle WhatsApp webhook verification and incoming messages"""
    
    # GET request for webhook verification
    if request.method == 'GET':
        # Get the bot's verify token from database
        bot = Bot.query.get(bot_id)
        if not bot:
            logger.error(f"Bot {bot_id} not found for webhook verification")
            return 'Bot not found', 404
            
        verify_token = bot.whatsapp_verify_token or "CVGlobal_WhatsApp_Verify_2024"
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        logger.info(f"WhatsApp webhook verification request for bot {bot_id} ({bot.name})")
        logger.info(f"Mode: {mode}, Token: {token}, Challenge: {challenge}")
        logger.info(f"Expected verify token: {verify_token}")
        
        if mode == 'subscribe' and token == verify_token:
            logger.info(f"WhatsApp webhook verified successfully for bot {bot_id}")
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            logger.warning(f"WhatsApp webhook verification failed for bot {bot_id}: mode={mode}, token={token}")
            return 'Verification failed', 403
    
    # POST request for incoming messages
    try:
        data = request.get_json()
        logger.debug(f"Received WhatsApp webhook data for bot {bot_id}: {data}")
        
        # Handle Facebook/Meta WhatsApp Business API format
        if 'entry' in data:
            for entry in data['entry']:
                if 'changes' in entry:
                    for change in entry['changes']:
                        if change.get('field') == 'messages':
                            value = change.get('value', {})
                            
                            # Process incoming messages
                            if 'messages' in value:
                                for message_data in value['messages']:
                                    phone_number = message_data.get('from', '')
                                    message_type = message_data.get('type', '')
                                    
                                    message_text = ''
                                    if message_type == 'text':
                                        message_text = message_data.get('text', {}).get('body', '').strip()
                                    elif message_type == 'button':
                                        message_text = message_data.get('button', {}).get('text', '').strip()
                                    elif message_type == 'interactive':
                                        interactive = message_data.get('interactive', {})
                                        if 'button_reply' in interactive:
                                            message_text = interactive['button_reply'].get('title', '').strip()
                                        elif 'list_reply' in interactive:
                                            message_text = interactive['list_reply'].get('title', '').strip()
                                    
                                    if phone_number and message_text:
                                        # Get client IP for location data
                                        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                                        if client_ip and ',' in client_ip:
                                            client_ip = client_ip.split(',')[0].strip()
                                        
                                        process_incoming_message(phone_number, message_text, platform="whatsapp", 
                                                               request_ip=client_ip, bot_id=bot_id)
        
        # Handle legacy format for other providers
        elif 'messages' in data:
            for message_data in data['messages']:
                phone_number = message_data.get('from', '').replace('whatsapp:', '')
                message_text = message_data.get('text', {}).get('body', '').strip()
                
                if phone_number and message_text:
                    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                    if client_ip and ',' in client_ip:
                        client_ip = client_ip.split(',')[0].strip()
                    
                    process_incoming_message(phone_number, message_text, platform="whatsapp", 
                                           request_ip=client_ip, bot_id=bot_id)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook for bot {bot_id}: {e}")
        return jsonify({"error": str(e)}), 500

def process_incoming_message(phone_number: str, message_text: str, platform: str = "whatsapp", user_data: dict = None, request_ip: str = None, bot_id: int = 1):
    """Process incoming message from user"""
    try:
        logger.info(f"Processing message from {phone_number}: {message_text}")
        
        # Normalize phone number for WhatsApp, keep Telegram chat IDs as-is
        if platform == "whatsapp" and not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        elif platform == "telegram" and phone_number.startswith('+tg_'):
            # Remove incorrect '+' prefix from Telegram IDs
            phone_number = phone_number[1:]
        
        message_lower = message_text.lower().strip()
        
        # Handle commands
        if message_lower == 'start' or message_lower == '/start':
            handle_start_command(phone_number, platform, user_data, request_ip, bot_id)
            return
        
        elif message_lower == 'stop' or message_lower == '/stop':
            handle_stop_command(phone_number, platform, bot_id)
            return
        
        elif message_lower == 'help' or message_lower == '/help':
            handle_help_command(phone_number, platform, bot_id)
            return
        
        elif message_lower == 'human' or message_lower == '/human':
            handle_human_command(phone_number, platform, bot_id)
            return
        
        # Check for human handoff triggers
        if any(keyword in message_lower for keyword in HUMAN_HANDOFF_KEYWORDS):
            handle_human_handoff(phone_number, message_text, platform, bot_id)
            return
        
        # Handle regular response (likely to a reflection question)
        handle_reflection_response(phone_number, message_text, platform, bot_id)
        
    except Exception as e:
        logger.error(f"Error processing message from {phone_number}: {e}")
        # Send error message to user
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error processing your message. Please try again or type HELP for assistance.",
            bot_id=bot_id
        )

def send_message_to_platform(phone_number: str, platform: str, message: str, 
                           with_quick_replies: bool = False, copy_text: str = "", 
                           copy_label: str = "Copy Text", bot_id: int = None) -> bool:
    """Send message to the appropriate platform with enhanced features"""
    try:
        if platform == "telegram":
            # Extract chat_id from tg_ prefixed phone number
            if phone_number.startswith("tg_"):
                chat_id = phone_number[3:]  # Remove 'tg_' prefix
                
                # Get bot-specific Telegram service
                bot_service = get_telegram_service_for_bot(bot_id)
                if not bot_service:
                    logger.error(f"No Telegram service available for bot_id {bot_id}")
                    return False
                
                # Enhanced Telegram messaging with 2025 features
                if copy_text and copy_label:
                    # Send message with copy button for Bible verses or inspirational content
                    return bot_service.send_copy_text_message(chat_id, message, copy_text, copy_label)
                elif with_quick_replies:
                    # Send message with quick reply buttons for common responses
                    quick_replies = [
                        "Tell me more", "I have a question", 
                        "This is helpful", "I need time to think"
                    ]
                    return bot_service.send_quick_reply_message(chat_id, message, quick_replies)
                else:
                    return bot_service.send_message(chat_id, message)
            else:
                logger.error(f"Invalid Telegram chat_id format: {phone_number}")
                return False
        else:
            # Default to WhatsApp (enhanced features not yet implemented)
            return whatsapp_service.send_message(phone_number, message)
    except Exception as e:
        logger.error(f"Error sending message to {platform}: {e}")
        return False



def handle_start_command(phone_number: str, platform: str = "whatsapp", user_data: dict = None, request_ip: str = None, bot_id: int = 1):
    """Handle START command - onboard new user"""
    try:
        logger.info(f"Processing START command for {phone_number} on {platform}")
        # Check if user already exists
        existing_user = db_manager.get_user_by_phone(phone_number)
        
        if existing_user and existing_user.status == 'active':
                    
            # Allow restart - reset to Day 1 and update with enhanced user data
            update_kwargs = {'current_day': 1, 'join_date': datetime.now(), 'bot_id': bot_id}
            if user_data and platform == "telegram":
                enhanced_data = extract_telegram_user_data(user_data, request_ip)
                update_kwargs.update(enhanced_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username')
                if user_name:
                    update_kwargs['name'] = user_name
            db_manager.update_user(phone_number, **update_kwargs)
            platform_emoji = "📱" if platform == "telegram" else "📱"
            # Get bot-specific greeting content
            greeting = db_manager.get_greeting_content(bot_id=bot_id)
            if greeting:
                restart_message = greeting.content
            else:
                # Fallback to default message if no greeting configured
                restart_message = (f"Restarting your Faith Journey! {platform_emoji}\n\n"
                                  "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                                  "After each piece of content, I'll ask you a simple reflection question.\n\n"
                                  "Available Commands:\n"
                                  f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                                  f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                                  f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                                  f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                                  "Day 1 content will arrive in a few seconds!")
            send_message_to_platform(phone_number, platform, restart_message, bot_id=bot_id)
            
            # Log the RESTART command for chat management visibility
            db_manager.log_message(
                user=existing_user,
                direction='incoming',
                raw_text=f'/start' if platform == 'telegram' else 'START',
                sentiment='positive',
                tags=['RESTART', 'RETURNING_USER', 'ONBOARDING'],
                confidence=1.0
            )
            
            # Send Day 1 content directly (bypass scheduler for immediate delivery)
            try:
                logger.info(f"Attempting direct Day 1 content delivery for restart user {phone_number}")
                user = db_manager.get_user_by_phone(phone_number)
                if user and user.bot_id:
                    # Get Day 1 content for this bot
                    content = db_manager.get_content_by_day(1, bot_id=user.bot_id)
                    if content:
                        # Format the message
                        message = f"📖 Day 1 - {content.title}\n\n{content.content}"
                        if content.reflection_question:
                            message += f"\n\n💭 Reflection Question:\n{content.reflection_question}\n\nTake your time to think about it and share your thoughts when you're ready."
                        
                        # Send directly to the platform
                        success = send_message_to_platform(phone_number, platform, message, bot_id=user.bot_id)
                        if success:
                            logger.info(f"✅ Day 1 content delivered successfully to restart user {phone_number}")
                            # Advance user to Day 2
                            db_manager.update_user(phone_number, current_day=2)
                            # Log the delivery
                            db_manager.log_message(
                                user=user,
                                direction='outgoing',
                                raw_text=message,
                                sentiment='positive',
                                tags=['DAY_1', 'CONTENT_DELIVERY', 'RESTART'],
                                confidence=1.0
                            )
                        else:
                            logger.error(f"❌ Failed to send Day 1 content to restart user {phone_number}")
                    else:
                        logger.error(f"❌ No Day 1 content found for restart user bot_id {user.bot_id}")
                else:
                    logger.error(f"❌ No restart user found for {phone_number}")
            except Exception as e:
                logger.error(f"❌ Exception delivering direct content for restart {phone_number}: {e}")
            logger.info(f"User {phone_number} restarted journey from Day 1")
            return
        
        # bot_id is already provided from the webhook routing

        # Create or reactivate user
        if existing_user:
            update_kwargs = {'status': 'active', 'current_day': 1, 'join_date': datetime.now(), 'bot_id': bot_id}
            if user_data and platform == "telegram":
                enhanced_data = extract_telegram_user_data(user_data, request_ip)
                update_kwargs.update(enhanced_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username')
                if user_name:
                    update_kwargs['name'] = user_name
            db_manager.update_user(phone_number, **update_kwargs)
        else:
            create_kwargs = {'status': 'active', 'current_day': 1, 'tags': [], 'bot_id': bot_id}
            if user_data and platform == "telegram":
                enhanced_data = extract_telegram_user_data(user_data, request_ip)
                create_kwargs.update(enhanced_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username')
                if user_name:
                    create_kwargs['name'] = user_name
            db_manager.create_user(phone_number, **create_kwargs)
        
        # Send welcome message
        platform_emoji = "📱" if platform == "telegram" else "📱"
        # Get bot-specific greeting content
        greeting = db_manager.get_greeting_content(bot_id=bot_id)
        if greeting:
            welcome_message = greeting.content
        else:
            # Fallback to default message if no greeting configured
            welcome_message = (f"Welcome to your Faith Journey! {platform_emoji}\n\n"
                              "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                              "After each piece of content, I'll ask you a simple reflection question.\n\n"
                              "Available Commands:\n"
                              f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                              f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                              f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                              f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                              "Day 1 content will arrive in a few seconds!")
        
        logger.info(f"Sending welcome message to {phone_number}: {welcome_message[:100]}...")
        send_message_to_platform(phone_number, platform, welcome_message, bot_id=bot_id)
        
        # Log the START command for chat management visibility
        user = db_manager.get_user_by_phone(phone_number)
        if user:
            db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=f'/start' if platform == 'telegram' else 'START',
                sentiment='positive',
                tags=['START', 'NEW_USER', 'ONBOARDING'],
                confidence=1.0
            )
        
        # Send Day 1 content directly (bypass scheduler for immediate delivery)
        try:
            logger.info(f"🔥 DEBUG: Attempting direct Day 1 content delivery for {phone_number}")
            user = db_manager.get_user_by_phone(phone_number)
            logger.info(f"🔥 DEBUG: User found: {user.phone_number if user else 'None'}, bot_id: {user.bot_id if user else 'None'}")
            if user and user.bot_id:
                # Get Day 1 content for this bot
                content = db_manager.get_content_by_day(1, bot_id=user.bot_id)
                logger.info(f"🔥 DEBUG: Content found: {content.title if content else 'None'}")
                if content:
                    # Format the message
                    message = f"📖 Day 1 - {content.title}\n\n{content.content}"
                    if content.reflection_question:
                        message += f"\n\n💭 Reflection Question:\n{content.reflection_question}\n\nTake your time to think about it and share your thoughts when you're ready."
                    
                    # Send directly to the platform
                    logger.info(f"🔥 DEBUG: About to send message to {phone_number} on {platform} with bot_id {user.bot_id}")
                    logger.info(f"🔥 DEBUG: Message preview: {message[:100]}...")
                    success = send_message_to_platform(phone_number, platform, message, bot_id=user.bot_id)
                    logger.info(f"🔥 DEBUG: Message send result: {success}")
                    if success:
                        logger.info(f"✅ Day 1 content delivered successfully to {phone_number}")
                        # Advance user to Day 2
                        db_manager.update_user(phone_number, current_day=2)
                        # Log the delivery
                        db_manager.log_message(
                            user=user,
                            direction='outgoing',
                            raw_text=message,
                            sentiment='positive',
                            tags=['DAY_1', 'CONTENT_DELIVERY'],
                            confidence=1.0
                        )
                    else:
                        logger.error(f"❌ Failed to send Day 1 content to {phone_number}")
                else:
                    logger.error(f"❌ No Day 1 content found for bot_id {user.bot_id}")
            else:
                logger.error(f"❌ No user found for {phone_number}")
        except Exception as e:
            logger.error(f"❌ Exception delivering direct content for {phone_number}: {e}")
        
        logger.info(f"User {phone_number} successfully onboarded")
        
    except Exception as e:
        logger.error(f"Error handling START command for {phone_number}: {e}")
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error setting up your journey. Please try again.",
            bot_id=bot_id
        )

def handle_stop_command(phone_number: str, platform: str = "whatsapp", bot_id: int = 1):
    """Handle STOP command - deactivate user"""
    try:
        user = db_manager.get_user_by_phone(phone_number)
        if user:
            db_manager.update_user(phone_number, status='inactive')
            
            # Get bot configuration for custom stop message
            bot = Bot.query.get(bot_id)
            if bot and bot.stop_message:
                message = bot.stop_message
            else:
                # Fallback message
                message = ("You have been unsubscribed from the Faith Journey. "
                          "If you'd like to restart your journey, simply send START anytime. "
                          "Peace be with you. 🙏")
        else:
            message = "You weren't subscribed to any journey. Send START to begin your faith journey."
        
        send_message_to_platform(phone_number, platform, message, bot_id=bot_id)
        
        # Log the stop request
        if user:
            db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=f'/stop' if platform == 'telegram' else 'STOP',
                sentiment='neutral',
                tags=['STOP']
            )
        
        logger.info(f"User {phone_number} unsubscribed")
        
    except Exception as e:
        logger.error(f"Error handling STOP command for {phone_number}: {e}")

def handle_help_command(phone_number: str, platform: str = "whatsapp", bot_id: int = 1):
    """Handle HELP command"""
    try:
        logger.info(f"🔥 DEBUG: Processing HELP command for {phone_number} on {platform} with bot_id {bot_id}")
        # Get or create user with bot_id
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number, status='active', current_day=1, bot_id=bot_id)
            logger.info(f"🔥 DEBUG: Created new user for {phone_number}")
        
        # Update existing user to use correct bot_id if different
        elif user.bot_id != bot_id:
            db_manager.update_user(phone_number, bot_id=bot_id)
        
        # Get bot configuration for custom help message
        bot = Bot.query.get(bot_id)
        if bot and bot.help_message:
            help_message = bot.help_message
        else:
            # Fallback message
            commands_prefix = "/" if platform == "telegram" else ""
            help_message = ("📖 Faith Journey Help\n\n"
                           "Commands:\n"
                           f"• {commands_prefix}START - Begin or restart your 10-day journey\n"
                           f"• {commands_prefix}STOP - Unsubscribe from messages\n"
                           f"• {commands_prefix}HELP - Show this help message\n"
                           f"• {commands_prefix}HUMAN - Chat directly with a human\n\n"
                           "You'll receive content every 10 minutes (for testing) followed by a reflection question. "
                           "Feel free to share your thoughts - there are no wrong answers!\n\n"
                           "If you need to speak with someone, just let us know.")
        
        logger.info(f"🔥 DEBUG: About to send help message to {phone_number}: {help_message[:50]}...")
        success = send_message_to_platform(phone_number, platform, help_message, bot_id=bot_id)
        logger.info(f"🔥 DEBUG: Help message send result: {success}")
        
        # Log the help request
        db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=f'/help' if platform == 'telegram' else 'HELP',
            sentiment='neutral',
            tags=['HELP']
        )
        
        if success:
            # Log the outgoing help response
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=help_message,
                sentiment='neutral',
                tags=['HELP_RESPONSE'],
                confidence=1.0
            )
            logger.info(f"✅ Help command processed successfully for {phone_number}")
        else:
            logger.error(f"❌ Help command failed to send for {phone_number}")
        
        logger.info(f"Help command processed for {phone_number}")
        
    except Exception as e:
        logger.error(f"Error handling help command for {phone_number}: {e}")

def handle_human_command(phone_number: str, platform: str = "whatsapp", bot_id: int = 1):
    """Handle HUMAN command - direct human chat request"""
    try:
        # Get or create user with bot_id
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number, status='active', current_day=1, bot_id=bot_id)
        # Update existing user to use correct bot_id if different
        elif user.bot_id != bot_id:
            db_manager.update_user(phone_number, bot_id=bot_id)
        
        # Log the human command for chat management visibility
        db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=f'/human' if platform == 'telegram' else 'HUMAN',
            sentiment='neutral',
            tags=['HUMAN_COMMAND', 'DIRECT_CHAT', 'PRIORITY'],
            is_human_handoff=True,
            confidence=1.0
        )
        
        # Get bot configuration for custom human message
        bot = Bot.query.get(bot_id)
        if bot and bot.human_message:
            response_message = bot.human_message
        else:
            # Fallback message
            response_message = ("🤝 Direct Human Chat Requested\n\n"
                              "Thank you for reaching out! A member of our team will connect with you shortly. "
                              "This conversation has been flagged for priority human response.\n\n"
                              "In the meantime, know that you are valued and your journey matters. "
                              "Feel free to share what's on your heart. 🙏")
        
        send_message_to_platform(phone_number, platform, response_message, bot_id=bot_id)
        
        logger.warning(f"HUMAN COMMAND - Direct chat requested by {phone_number} on {platform}")
        
    except Exception as e:
        logger.error(f"Error handling HUMAN command for {phone_number}: {e}")
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error connecting you with a human. Please try again or contact us directly.",
            bot_id=bot_id
        )

def handle_human_handoff(phone_number: str, message_text: str, platform: str = "whatsapp", bot_id: int = 1):
    """Handle messages that require human intervention"""
    try:
        # Get or create user with bot_id
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number, status='active', current_day=1, bot_id=bot_id)
        # Update existing user to use correct bot_id if different
        elif user.bot_id != bot_id:
            db_manager.update_user(phone_number, bot_id=bot_id)
        
        # Log the handoff request
        db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=message_text,
            sentiment='neutral',
            tags=['HUMAN_HANDOFF', 'URGENT'],
            is_human_handoff=True
        )
        
        # Send response to user
        response_message = ("Thank you for reaching out. A member of our team will contact you shortly. "
                          "In the meantime, know that you are valued and your journey matters. 🙏")
        
        send_message_to_platform(phone_number, platform, response_message, bot_id=bot_id)
        
        logger.warning(f"HUMAN HANDOFF requested by {phone_number}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error handling human handoff for {phone_number}: {e}")

def handle_reflection_response(phone_number: str, message_text: str, platform: str = "whatsapp", bot_id: int = 1):
    """Handle user's reflection response with contextual AI response"""
    try:
        # Analyze the response with Gemini
        analysis = gemini_service.analyze_response(message_text)
        
        # Get or create user with bot_id
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number, status='active', current_day=1, bot_id=bot_id)
        # Update existing user to use correct bot_id if different
        elif user.bot_id != bot_id:
            db_manager.update_user(phone_number, bot_id=bot_id)
        
        # Log the response
        db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=message_text,
            sentiment=analysis['sentiment'],
            tags=analysis['tags'],
            confidence=analysis.get('confidence')
        )
        
        # Get current day content for contextual response
        current_day = user.current_day - 1  # User was advanced after receiving content, so subtract 1 for the content they just reflected on
        content = db_manager.get_content_by_day(current_day, bot_id=user.bot_id) if current_day > 0 else None
        
        if content:
            # Generate contextual response based on current day's content
            contextual_response = gemini_service.generate_contextual_response(
                user_reflection=message_text,
                day_number=content.day_number,
                content_title=content.title,
                content_text=content.content,
                reflection_question=content.reflection_question
            )
            
            logger.info(f"Generated contextual response for {phone_number} (Day {content.day_number})")
        else:
            # Fallback acknowledgment if no content found
            contextual_response = "Thank you for sharing your thoughtful reflection. Your openness to explore these questions shows a sincere heart seeking truth."
            logger.warning(f"No content found for contextual response to {phone_number}")
        
        # Send the contextual response
        send_message_to_platform(phone_number, platform, contextual_response, bot_id=bot_id)
        
        # Log the outgoing contextual response
        db_manager.log_message(
            user=user,
            direction='outgoing',
            raw_text=contextual_response,
            sentiment='positive',
            tags=['AI_Response', 'Contextual'],
            confidence=0.9
        )
        
        logger.info(f"Processed reflection from {phone_number}: sentiment={analysis['sentiment']}, tags={analysis['tags']}")
        
    except Exception as e:
        logger.error(f"Error handling reflection response from {phone_number}: {e}")
        # Still acknowledge the user's response with fallback
        fallback_response = "Thank you for your reflection. Your thoughtfulness is appreciated."
        send_message_to_platform(phone_number, platform, fallback_response, bot_id=bot_id)

@app.route('/telegram/setup', methods=['POST'])
def setup_telegram_webhook():
    """Set up Telegram webhook (for admin use)"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        secret_token = data.get('secret_token', '')
        
        if not webhook_url:
            return jsonify({"error": "webhook_url is required"}), 400
        
        # Set the webhook
        success = telegram_service.set_webhook(webhook_url, secret_token)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Telegram webhook configured successfully",
                "webhook_url": webhook_url
            })
        else:
            return jsonify({
                "status": "error", 
                "message": "Failed to set Telegram webhook"
            }), 500
            
    except Exception as e:
        logger.error(f"Error setting up Telegram webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/telegram/info', methods=['GET'])
def get_telegram_info():
    """Get Telegram bot information"""
    try:
        bot_info = telegram_service.get_me()
        webhook_info = telegram_service.get_webhook_info()
        
        return jsonify({
            "bot_info": bot_info,
            "webhook_info": webhook_info,
            "simulation_mode": telegram_service.simulate_mode
        })
        
    except Exception as e:
        logger.error(f"Error getting Telegram info: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/telegram/test', methods=['POST'])
def test_telegram_message():
    """Test endpoint for simulating Telegram messages"""
    try:
        data = request.get_json()
        chat_id = data.get('chat_id', '123456789')
        message = data.get('message', '/start')
        username = data.get('username', 'testuser')
        first_name = data.get('first_name', 'Test User')
        
        # Simulate Telegram webhook payload
        webhook_data = {
            "update_id": 12345,
            "message": {
                "message_id": 1,
                "date": 1640995200,
                "chat": {"id": int(chat_id), "type": "private"},
                "from": {
                    "id": int(chat_id),
                    "first_name": first_name,
                    "username": username
                },
                "text": message
            }
        }
        
        # Process through telegram webhook handler
        with app.test_request_context('/telegram', method='POST', json=webhook_data):
            response = telegram_webhook()
        
        return jsonify({
            "status": "success",
            "message": f"Simulated Telegram message from {username} ({chat_id}): {message}",
            "chat_id": f"tg_{chat_id}",
            "response": "Check logs for bot responses"
        })
        
    except Exception as e:
        logger.error(f"Error testing Telegram message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": "operational",
            "whatsapp": "operational",
            "gemini": "operational"
        }
    })

@app.route('/debug/routes', methods=['GET'])
def debug_routes():
    """Debug endpoint to show all routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            "rule": rule.rule,
            "endpoint": rule.endpoint,
            "methods": list(rule.methods)
        })
    return jsonify({"routes": routes})

@app.route('/debug/webhook/<int:bot_id>', methods=['GET'])
def debug_webhook_test(bot_id):
    """Debug webhook test endpoint"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    # Get bot from database
    try:
        bot = Bot.query.get(bot_id)
        if not bot:
            return jsonify({"error": f"Bot {bot_id} not found"}), 404
        
        return jsonify({
            "bot_id": bot_id,
            "bot_name": bot.name,
            "verify_token": bot.whatsapp_verify_token,
            "request_params": {
                "mode": mode,
                "token": token,
                "challenge": challenge
            },
            "verification": mode == 'subscribe' and token == bot.whatsapp_verify_token
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/webhook-simple', methods=['GET'])
def simple_webhook():
    """Simple webhook test without parameters"""
    return "Simple webhook working!", 200

@app.route('/whatsapp-test/<int:bot_id>', methods=['GET'])
def whatsapp_test_webhook(bot_id):
    """Test WhatsApp webhook with simplified logic"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token') 
    challenge = request.args.get('hub.challenge')
    
    logger.info(f"WhatsApp test webhook called: bot_id={bot_id}, mode={mode}, token={token}, challenge={challenge}")
    
    if mode == 'subscribe' and token == 'CVGlobal_WhatsApp_Verify_2024':
        return challenge, 200, {'Content-Type': 'text/plain'}
    else:
        return 'Verification failed', 403

@app.route('/test', methods=['POST'])
def test_message():
    """Test endpoint for simulating WhatsApp messages"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number', '+14155551234')
        message = data.get('message', 'START')
        
        # Capture simulated responses
        simulated_responses = []
        
        # Temporarily override WhatsApp service to capture responses
        original_send = whatsapp_service.send_message
        def capture_send(to, message):
            simulated_responses.append(f"Bot: {message}")
            return original_send(to, message)
        whatsapp_service.send_message = capture_send
        
        try:
            # Process message
            message_text = message.strip().upper()
            
            if message_text == 'START':
                handle_start_command(phone_number)
            elif message_text == 'STOP':
                handle_stop_command(phone_number)
            elif message_text == 'HELP':
                handle_help_command(phone_number)
            elif message_text == 'HUMAN':
                handle_human_command(phone_number)
            else:
                # Check for human handoff triggers
                if gemini_service.should_trigger_human_handoff(message):
                    handle_human_handoff(phone_number, message)
                else:
                    handle_reflection_response(phone_number, message)
        finally:
            # Restore original method
            whatsapp_service.send_message = original_send
        
        return jsonify({
            "status": "success", 
            "message": "Message processed",
            "bot_responses": simulated_responses
        })
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/users', methods=['GET'])
def get_users():
    """API endpoint to get user data"""
    try:
        users = db_manager.get_active_users()
        return jsonify([user.to_dict() for user in users])
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/test-interface')
def test_interface():
    """Test interface for simulating WhatsApp messages"""
    return render_template('test.html')

@app.route('/cms')
@login_required
def cms():
    """Content Management System for 30-day journey content with multimedia support"""
    return render_template('cms.html', user=current_user)

@app.route('/api/content', methods=['GET'])
def get_all_content():
    """API endpoint to get all content, optionally filtered by bot_id"""
    try:
        bot_id = request.args.get('bot_id', type=int)
        content_type = request.args.get('content_type', 'daily')  # 'daily' or 'greeting'
        
        if content_type == 'greeting':
            greeting = db_manager.get_greeting_content(bot_id=bot_id)
            return jsonify([greeting.to_dict()] if greeting else [])
        else:
            content = db_manager.get_all_content(bot_id=bot_id, content_type='daily')
            return jsonify([c.to_dict() for c in content])
    except Exception as e:
        logger.error(f"Error getting content: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/greeting', methods=['POST'])
def create_or_update_greeting():
    """API endpoint to create or update greeting content"""
    try:
        data = request.get_json()
        success = db_manager.create_or_update_greeting(
            bot_id=data.get('bot_id', 1),
            title=data['title'],
            content=data['content'],
            reflection_question=data.get('reflection_question', ''),
            tags=data.get('tags', []),
            media_type=data.get('media_type', 'text'),
            image_filename=data.get('image_filename'),
            video_filename=data.get('video_filename'),
            youtube_url=data.get('youtube_url'),
            audio_filename=data.get('audio_filename')
        )
        return jsonify({"status": "success" if success else "error"})
    except Exception as e:
        logger.error(f"Error creating/updating greeting: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/bots/<int:bot_id>/greeting', methods=['GET'])
def get_bot_greeting(bot_id):
    """API endpoint to get greeting content for a specific bot"""
    try:
        greeting = db_manager.get_greeting_content(bot_id=bot_id)
        if greeting:
            return jsonify(greeting.to_dict())
        else:
            return jsonify(None), 200
    except Exception as e:
        logger.error(f"Error getting greeting for bot {bot_id}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/content', methods=['POST'])
def create_content():
    """API endpoint to create new content with multimedia support"""
    try:
        data = request.get_json()
        content_id = db_manager.create_content(
            day_number=data['day_number'],
            title=data['title'],
            content=data['content'],
            reflection_question=data['reflection_question'],
            tags=data.get('tags', []),
            media_type=data.get('media_type', 'text'),
            image_filename=data.get('image_filename'),
            video_filename=data.get('video_filename'),
            youtube_url=data.get('youtube_url'),
            audio_filename=data.get('audio_filename'),
            is_active=data.get('is_active', True),
            bot_id=data.get('bot_id', 1),
            content_type=data.get('content_type', 'daily')
        )
        return jsonify({"status": "success", "id": content_id})
    except Exception as e:
        logger.error(f"Error creating content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/content/<int:content_id>', methods=['PUT'])
def update_content(content_id):
    """API endpoint to update content"""
    try:
        data = request.get_json()
        db_manager.update_content(
            content_id=content_id,
            title=data['title'],
            content=data['content'],
            reflection_question=data['reflection_question'],
            tags=data.get('tags', []),
            is_active=data.get('is_active', True)
        )
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error updating content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/content/<int:content_id>', methods=['DELETE'])
def delete_content(content_id):
    """API endpoint to delete content"""
    try:
        db_manager.delete_content(content_id)
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error deleting content: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Contextual Response Generation
def generate_contextual_response(user_message: str, user = None, custom_settings = None):
    """Generate contextual AI response based on user's journey progress"""
    try:
        # Get settings
        if custom_settings:
            settings = custom_settings
        else:
            settings = db_manager.get_chatbot_settings()
        
        # Get user's current day content if available
        daily_content = None
        if user and settings.get('use_daily_content_context', True):
            daily_content = db_manager.get_content_by_day(user.current_day_number)
        
        # Build context-aware prompt
        system_prompt = settings.get('system_prompt', '')
        if daily_content and settings.get('use_daily_content_context', True):
            context_prompt = f"""
Current day content context:
Title: {daily_content.title}
Content: {daily_content.content[:300]}...
Reflection Question: {daily_content.reflection_question}

Use this context to provide relevant, personalized responses to the user's message.
"""
            system_prompt += "\n\n" + context_prompt
        
        # Generate response using Gemini
        response = gemini_service.generate_contextual_response(
            message=user_message,
            system_prompt=system_prompt,
            style=settings.get('response_style', 'compassionate')
        )
        
        return response
    except Exception as e:
        logger.error(f"Error generating contextual response: {e}")
        return "Thank you for your message. I'm here to support you on your faith journey. Please feel free to share your thoughts or questions."

# Chat Management Routes

# Removed redundant settings route - settings are now handled per bot in bot management

@app.route('/api/send-message', methods=['POST'])
def send_message_to_user():
    """Send a message from admin to user (legacy endpoint)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        tags = data.get('tags', [])
        
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        # Determine platform and send message
        platform = 'telegram' if user.phone_number.startswith('tg_') else 'whatsapp'
        success = send_message_to_platform(user.phone_number, platform, message)
        
        if success:
            # Log the message
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=message,
                tags=tags or ['ADMIN_MESSAGE']
            )
            
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/send-admin-message', methods=['POST'])
def send_admin_message():
    """Send a message from admin to user (new endpoint for full chat interface)"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        tags = data.get('tags', [])
        
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        # Determine platform and send message
        platform = 'telegram' if user.phone_number.startswith('tg_') else 'whatsapp'
        success = send_message_to_platform(user.phone_number, platform, message)
        
        if success:
            # Log the message with admin tags
            admin_tags = tags if tags else ['ADMIN_MESSAGE']
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=message,
                sentiment='neutral',
                tags=admin_tags,
                confidence=1.0
            )
            logger.info(f"Admin message sent to {user.phone_number} ({platform}): {message[:50]}...")
            
        return jsonify({'success': success, 'platform': platform})
    except Exception as e:
        logger.error(f"Error sending admin message: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-video', methods=['POST'])
def upload_video():
    """Handle video file uploads for content"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: mp4, mov, avi, mkv, webm'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
        os.makedirs(video_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(video_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Video uploaded successfully: {unique_filename}")
        return jsonify({'success': True, 'filename': unique_filename})
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-image', methods=['POST'])
def upload_image():
    """Handle image file uploads for content"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: jpg, jpeg, png, gif'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        image_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
        os.makedirs(image_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(image_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Image uploaded successfully: {unique_filename}")
        return jsonify({'success': True, 'filename': unique_filename})
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-audio', methods=['POST'])
def upload_audio():
    """Handle audio file uploads for content"""
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'mp3', 'wav', 'ogg', 'm4a'}
        if not ('.' in file.filename and file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: mp3, wav, ogg, m4a'}), 400
        
        # Generate secure filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(audio_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Audio uploaded successfully: {unique_filename}")
        return jsonify({'success': True, 'filename': unique_filename})
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-message-tags', methods=['POST'])
def update_message_tags():
    """Update tags for a specific message"""
    try:
        data = request.get_json()
        message_id = data.get('message_id')
        tags = data.get('tags', [])
        
        success = db_manager.update_message_tags(message_id, tags)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error updating message tags: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
def save_chatbot_settings():
    """Save chatbot settings"""
    try:
        data = request.get_json()
        success = db_manager.save_chatbot_settings(data)
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings/reset', methods=['POST'])
def reset_chatbot_settings():
    """Reset chatbot settings to defaults"""
    try:
        success = db_manager.reset_chatbot_settings()
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-response', methods=['POST'])
def test_chatbot_response():
    """Test chatbot response with current settings"""
    try:
        data = request.get_json()
        test_message = data.get('message')
        settings = data.get('settings')
        
        # Generate a contextual response
        response = generate_contextual_response(test_message, None, settings)
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        logger.error(f"Error testing response: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-scheduler-user', methods=['POST'])
def test_scheduler_user():
    """Test content delivery for a specific user"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        success = scheduler.send_content_to_user(phone_number)
        return jsonify({'success': success, 'message': f'Content delivery attempted for {phone_number}'})
    except Exception as e:
        logger.error(f"Error testing scheduler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Bot Management Routes
@app.route('/bots')
@login_required
def bot_management():
    """Bot management dashboard"""
    try:
        bots = Bot.query.all()
        logger.info(f"Found {len(bots)} bots")
        # Add user and content counts for each bot
        for bot in bots:
            bot.user_count = User.query.filter_by(bot_id=bot.id).count()
            bot.content_count = Content.query.filter_by(bot_id=bot.id).count()
        
        return render_template('bot_management.html', bots=bots)
    except Exception as e:
        logger.error(f"Bot management error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        flash(f'Error loading bots: {str(e)}', 'error')
        return redirect('/dashboard')

def setup_telegram_webhook(bot_id, telegram_token):
    """Automatically setup Telegram webhook for a bot"""
    try:
        if not telegram_token:
            return None, "No Telegram token provided"
        
        # Generate bot-specific webhook URL
        webhook_url = f"https://smart-budget-cvglobaldev.replit.app/telegram/{bot_id}"
        
        # Set webhook via Telegram API
        import requests
        response = requests.post(
            f"https://api.telegram.org/bot{telegram_token}/setWebhook",
            json={"url": webhook_url},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"Telegram webhook set successfully for bot {bot_id}: {webhook_url}")
                return webhook_url, None
            else:
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Failed to set Telegram webhook for bot {bot_id}: {error_msg}")
                return None, f"Telegram API error: {error_msg}"
        else:
            logger.error(f"HTTP error setting Telegram webhook for bot {bot_id}: {response.status_code}")
            return None, f"HTTP error: {response.status_code}"
            
    except Exception as e:
        logger.error(f"Exception setting Telegram webhook for bot {bot_id}: {e}")
        return None, f"Exception: {str(e)}"

def setup_whatsapp_webhook(bot_id, whatsapp_access_token, whatsapp_phone_number_id):
    """Automatically setup WhatsApp webhook for a bot"""
    try:
        if not whatsapp_access_token or not whatsapp_phone_number_id:
            return None, "Missing WhatsApp access token or phone number ID"
        
        # Generate bot-specific webhook URL
        webhook_url = f"https://smart-budget-cvglobaldev.replit.app/whatsapp/{bot_id}"
        
        # Set webhook via WhatsApp Business API
        import requests
        
        # First, verify the access token by getting the phone number info
        verify_response = requests.get(
            f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}",
            headers={"Authorization": f"Bearer {whatsapp_access_token}"},
            params={"fields": "display_phone_number,verified_name,status"},
            timeout=10
        )
        
        if verify_response.status_code != 200:
            error_data = verify_response.json() if verify_response.content else {}
            error_msg = error_data.get('error', {}).get('message', f'HTTP {verify_response.status_code}')
            logger.error(f"WhatsApp token verification failed for bot {bot_id}: {error_msg}")
            return None, f"Invalid WhatsApp credentials: {error_msg}"
        
        # Update webhook configuration
        webhook_response = requests.post(
            f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}/subscribed_apps",
            headers={"Authorization": f"Bearer {whatsapp_access_token}"},
            json={
                "subscribed_fields": ["messages", "message_deliveries", "message_reads", "message_echoes"]
            },
            timeout=10
        )
        
        if webhook_response.status_code == 200:
            result = webhook_response.json()
            if result.get('success'):
                logger.info(f"WhatsApp webhook configured successfully for bot {bot_id}: {webhook_url}")
                return webhook_url, None
            else:
                error_msg = result.get('error', {}).get('message', 'Unknown error')
                logger.error(f"Failed to configure WhatsApp webhook for bot {bot_id}: {error_msg}")
                return None, f"WhatsApp API error: {error_msg}"
        else:
            logger.error(f"HTTP error configuring WhatsApp webhook for bot {bot_id}: {webhook_response.status_code}")
            return None, f"HTTP error: {webhook_response.status_code}"
            
    except Exception as e:
        logger.error(f"Exception setting WhatsApp webhook for bot {bot_id}: {e}")
        return None, f"Exception: {str(e)}"

def test_whatsapp_connection(whatsapp_access_token, whatsapp_phone_number_id):
    """Test WhatsApp API connection"""
    try:
        import requests
        
        # Test the connection by getting phone number info
        response = requests.get(
            f"https://graph.facebook.com/v18.0/{whatsapp_phone_number_id}",
            headers={"Authorization": f"Bearer {whatsapp_access_token}"},
            params={"fields": "display_phone_number,verified_name,status"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return True, {
                "phone_number": data.get("display_phone_number", "N/A"),
                "verified_name": data.get("verified_name", "N/A"),
                "status": data.get("status", "N/A")
            }
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, f"Connection error: {str(e)}"

@app.route('/test_whatsapp/<int:bot_id>')
@login_required
def test_whatsapp_connection_route(bot_id):
    """Test WhatsApp connection for a specific bot"""
    bot = Bot.query.get_or_404(bot_id)
    
    if not bot.whatsapp_access_token or not bot.whatsapp_phone_number_id:
        return {
            "success": False,
            "error": "Missing WhatsApp credentials"
        }
    
    success, result = test_whatsapp_connection(bot.whatsapp_access_token, bot.whatsapp_phone_number_id)
    
    if success:
        # Test webhook setup
        webhook_url, webhook_error = setup_whatsapp_webhook(bot.id, bot.whatsapp_access_token, bot.whatsapp_phone_number_id)
        if webhook_url:
            bot.whatsapp_webhook_url = webhook_url
            db.session.commit()
            return {
                "success": True,
                "connection": result,
                "webhook": f"Webhook configured: {webhook_url}"
            }
        else:
            return {
                "success": False,
                "connection": result,
                "webhook_error": webhook_error
            }
    else:
        return {
            "success": False,
            "error": result
        }

@app.route('/bots/create', methods=['GET', 'POST'])
@login_required
def create_bot():
    """Create a new bot"""
    form = CreateBotForm()
    
    if form.validate_on_submit():
        try:
            bot = Bot()
            bot.name = form.name.data
            bot.description = form.description.data
            bot.platforms = form.platforms.data or []
            bot.whatsapp_access_token = form.whatsapp_access_token.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_phone_number_id = form.whatsapp_phone_number_id.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_webhook_url = form.whatsapp_webhook_url.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_verify_token = form.whatsapp_verify_token.data or 'CVGlobal_WhatsApp_Verify_2024'
            bot.telegram_bot_token = form.telegram_bot_token.data if 'telegram' in (form.platforms.data or []) else None
            bot.ai_prompt = form.ai_prompt.data
            bot.journey_duration_days = form.journey_duration_days.data
            bot.delivery_interval_minutes = form.delivery_interval_minutes.data
            bot.help_message = form.help_message.data
            bot.stop_message = form.stop_message.data
            bot.human_message = form.human_message.data
            
            # Save bot first to get the ID
            db.session.add(bot)
            db.session.commit()
            
            # Auto-setup webhooks for enabled platforms
            webhook_messages = []
            
            # Auto-setup Telegram webhook if Telegram is enabled
            if 'telegram' in (form.platforms.data or []) and bot.telegram_bot_token:
                webhook_url, error = setup_telegram_webhook(bot.id, bot.telegram_bot_token)
                if webhook_url:
                    bot.telegram_webhook_url = webhook_url
                    webhook_messages.append(f"Telegram webhook configured automatically: {webhook_url}")
                else:
                    webhook_messages.append(f"Warning: Failed to setup Telegram webhook - {error}")
            
            # Auto-setup WhatsApp webhook if WhatsApp is enabled
            if 'whatsapp' in (form.platforms.data or []) and bot.whatsapp_access_token and bot.whatsapp_phone_number_id:
                webhook_url, error = setup_whatsapp_webhook(bot.id, bot.whatsapp_access_token, bot.whatsapp_phone_number_id)
                if webhook_url:
                    bot.whatsapp_webhook_url = webhook_url
                    webhook_messages.append(f"WhatsApp webhook configured automatically: {webhook_url}")
                else:
                    webhook_messages.append(f"Warning: Failed to setup WhatsApp webhook - {error}")
            
            # Commit all webhook updates
            db.session.commit()
            
            # Send welcome message if Telegram is configured
            if 'telegram' in (form.platforms.data or []) and bot.telegram_bot_token and bot.telegram_webhook_url:
                try:
                    import requests
                    welcome_msg = f"🎉 Welcome to {bot.name}!\n\nYour new bot has been created and is ready to serve users. Webhooks have been automatically configured.\n\n✅ Bot ID: {bot.id}\n✅ Platforms: {', '.join(form.platforms.data or [])}\n\nUsers can now start conversations with this bot!\n\n📝 Type 'START' to begin your spiritual journey, or send any message to get personalized guidance."
                    
                    # Bot validation
                    test_response = requests.post(
                        f"https://api.telegram.org/bot{bot.telegram_bot_token}/getMe",
                        timeout=5
                    )
                    if test_response.status_code == 200:
                        webhook_messages.append("Bot validation successful - ready for users!")
                        
                        # Send welcome message to a test chat to verify bot is working
                        # Note: This sends to the admin/creator's chat for verification
                        creator_chat_id = "960173404"  # Admin/creator chat ID
                        try:
                            welcome_response = requests.post(
                                f"https://api.telegram.org/bot{bot.telegram_bot_token}/sendMessage",
                                json={
                                    "chat_id": creator_chat_id,
                                    "text": welcome_msg
                                },
                                timeout=5
                            )
                            if welcome_response.status_code == 200:
                                webhook_messages.append("Bot tested successfully - welcome message sent!")
                            else:
                                webhook_messages.append("Bot created but could not send test message")
                        except Exception as creator_msg_error:
                            logger.info(f"Could not send welcome to creator: {creator_msg_error}")
                            webhook_messages.append("Bot created but test message failed")
                    
                except Exception as e:
                    logger.warning(f"Could not validate new bot {bot.id}: {e}")
            
            success_message = f'Bot "{bot.name}" created successfully!'
            if webhook_messages:
                success_message += " " + " ".join(webhook_messages)
            
            flash(success_message, 'success')
            return redirect('/bots')
            
        except Exception as e:
            logger.error(f"Error creating bot: {e}")
            db.session.rollback()
            flash('Error creating bot. Please try again.', 'error')
    
    return render_template('create_bot.html', form=form)

@app.route('/bots/<int:bot_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bot(bot_id):
    """Edit an existing bot"""
    bot = Bot.query.get_or_404(bot_id)
    form = EditBotForm(obj=bot)
    
    if form.validate_on_submit():
        try:
            # Store old values to detect changes
            old_telegram_token = bot.telegram_bot_token
            old_platforms = bot.platforms
            
            bot.name = form.name.data
            bot.description = form.description.data
            bot.platforms = form.platforms.data or []
            bot.whatsapp_access_token = form.whatsapp_access_token.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_phone_number_id = form.whatsapp_phone_number_id.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_webhook_url = form.whatsapp_webhook_url.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_verify_token = form.whatsapp_verify_token.data or 'CVGlobal_WhatsApp_Verify_2024'
            bot.telegram_bot_token = form.telegram_bot_token.data if 'telegram' in (form.platforms.data or []) else None
            bot.ai_prompt = form.ai_prompt.data
            bot.journey_duration_days = form.journey_duration_days.data
            bot.delivery_interval_minutes = form.delivery_interval_minutes.data
            bot.help_message = form.help_message.data
            bot.stop_message = form.stop_message.data
            bot.human_message = form.human_message.data
            bot.status = 'active' if form.status.data else 'inactive'
            
            # Auto-setup or update webhooks if needed
            webhook_messages = []
            
            # Handle Telegram webhook updates
            telegram_enabled = 'telegram' in (form.platforms.data or [])
            telegram_token_changed = bot.telegram_bot_token != old_telegram_token
            telegram_newly_enabled = telegram_enabled and 'telegram' not in (old_platforms or [])
            
            if telegram_enabled and bot.telegram_bot_token and (telegram_token_changed or telegram_newly_enabled or not bot.telegram_webhook_url):
                webhook_url, error = setup_telegram_webhook(bot.id, bot.telegram_bot_token)
                if webhook_url:
                    bot.telegram_webhook_url = webhook_url
                    webhook_messages.append(f"Telegram webhook updated automatically: {webhook_url}")
                else:
                    webhook_messages.append(f"Warning: Failed to update Telegram webhook - {error}")
            elif not telegram_enabled:
                bot.telegram_webhook_url = None
            
            # Handle WhatsApp webhook updates
            whatsapp_enabled = 'whatsapp' in (form.platforms.data or [])
            whatsapp_token_changed = bot.whatsapp_access_token != getattr(form, 'whatsapp_access_token', {}).get('data', '')
            whatsapp_phone_changed = bot.whatsapp_phone_number_id != getattr(form, 'whatsapp_phone_number_id', {}).get('data', '')
            whatsapp_newly_enabled = whatsapp_enabled and 'whatsapp' not in (old_platforms or [])
            
            if whatsapp_enabled and bot.whatsapp_access_token and bot.whatsapp_phone_number_id and (whatsapp_token_changed or whatsapp_phone_changed or whatsapp_newly_enabled or not bot.whatsapp_webhook_url):
                webhook_url, error = setup_whatsapp_webhook(bot.id, bot.whatsapp_access_token, bot.whatsapp_phone_number_id)
                if webhook_url:
                    bot.whatsapp_webhook_url = webhook_url
                    webhook_messages.append(f"WhatsApp webhook updated automatically: {webhook_url}")
                else:
                    webhook_messages.append(f"Warning: Failed to update WhatsApp webhook - {error}")
            elif not whatsapp_enabled:
                bot.whatsapp_webhook_url = None
            
            db.session.commit()
            
            success_message = f'Bot "{bot.name}" updated successfully!'
            if webhook_messages:
                success_message += " " + " ".join(webhook_messages)
            
            flash(success_message, 'success')
            return redirect('/bots')
            
        except Exception as e:
            logger.error(f"Error updating bot: {e}")
            db.session.rollback()
            flash('Error updating bot. Please try again.', 'error')
    
    # Pre-populate form with current values
    if request.method == 'GET':
        form.status.data = bot.status == 'active'
    
    return render_template('edit_bot.html', form=form, bot=bot)

@app.route('/api/bots/<int:bot_id>/status', methods=['POST'])
@login_required
def toggle_bot_status(bot_id):
    """Toggle bot status via API"""
    try:
        bot = Bot.query.get_or_404(bot_id)
        data = request.get_json()
        new_status = data.get('status')
        
        if new_status not in ['active', 'inactive']:
            return jsonify({'success': False, 'error': 'Invalid status'}), 400
        
        bot.status = new_status
        db.session.commit()
        
        return jsonify({'success': True, 'status': bot.status})
        
    except Exception as e:
        logger.error(f"Error toggling bot status: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/bots/<int:bot_id>/content')
@login_required
def bot_content_management(bot_id):
    """Bot-specific content management"""
    bot = Bot.query.get_or_404(bot_id)
    content_items = Content.query.filter_by(bot_id=bot_id).order_by(Content.day_number).all()
    return render_template('cms.html', bot=bot, content_items=content_items, bot_specific=True)

@app.route('/bots/<int:bot_id>/chats')
@login_required  
def bot_chat_management(bot_id):
    """Bot-specific chat management"""
    bot = Bot.query.get_or_404(bot_id)
    # Get recent users for this specific bot
    recent_users = db_manager.get_recent_active_users(bot_id=bot_id)
    stats = db_manager.get_chat_management_stats(bot_id=bot_id)
    return render_template('chat_management.html', bot=bot, recent_users=recent_users, stats=stats, bot_specific=True)

@app.route('/bots/<int:bot_id>/delete', methods=['POST'])
@login_required
def delete_bot(bot_id):
    """Delete a bot and all associated data"""
    try:
        bot = Bot.query.get_or_404(bot_id)
        bot_name = bot.name
        
        # Delete the bot (cascade will handle users and content)
        db.session.delete(bot)
        db.session.commit()
        
        flash(f'Bot "{bot_name}" and all associated data deleted successfully.', 'success')
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error deleting bot: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

# Chat Management Routes
@app.route('/chat-management')
@login_required
def chat_management_page():
    """Display chat management page"""
    try:
        stats = db_manager.get_chat_management_stats()
        return render_template('chat_management.html', stats=stats, user=current_user)
    except Exception as e:
        logger.error(f"Error loading chat management page: {e}")
        return f"Error loading chat management page: {e}", 500

@app.route('/api/chat-management/messages')
def get_filtered_messages():
    """API endpoint to get consolidated user conversations (no duplicates)"""
    try:
        # Get filter parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        sort_field = request.args.get('sort_field', 'timestamp')
        sort_order = request.args.get('sort_order', 'desc')
        bot_id = request.args.get('bot_id', type=int)  # Get bot_id for filtering
        
        filters = {
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
            'user_search': request.args.get('user_search'),
            'sentiment': request.args.get('sentiment'),
            'tags': request.args.get('tags'),
            'human_handoff': request.args.get('human_handoff') == 'true',
            'direction': request.args.get('direction')
        }
        
        # Remove empty filters
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        # Get consolidated user conversations instead of individual messages
        result = db_manager.get_consolidated_user_conversations(
            page=page,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
            filters=filters,
            bot_id=bot_id  # Pass bot_id for filtering
        )
        
        # Get stats for current filter
        stats = db_manager.get_chat_management_stats(filters, bot_id=bot_id)
        
        return jsonify({
            'success': True,
            'messages': result['conversations'],  # Change 'messages' to 'conversations' for clarity
            'pagination': result['pagination'],
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Error getting filtered messages: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat-management/message/<int:message_id>')
def get_message_details(message_id):
    """API endpoint to get detailed message information"""
    try:
        message = db_manager.get_message_details(message_id)
        if not message:
            return jsonify({'success': False, 'error': 'Message not found'}), 404
            
        return jsonify({
            'success': True,
            'message': message
        })
    except Exception as e:
        logger.error(f"Error getting message details: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat-management/export')
def export_filtered_chats():
    """Export filtered chat data as CSV"""
    try:
        # Get same filters as the main query
        filters = {
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
            'user_search': request.args.get('user_search'),
            'sentiment': request.args.get('sentiment'),
            'tags': request.args.get('tags'),
            'human_handoff': request.args.get('human_handoff') == 'true',
            'direction': request.args.get('direction')
        }
        
        # Remove empty filters
        filters = {k: v for k, v in filters.items() if v is not None and v != ''}
        
        # Get all matching messages for export
        export_data = db_manager.export_filtered_messages(filters)
        
        # Create CSV content
        csv_lines = ["Timestamp,Phone,Direction,Message,Sentiment,Tags,Human Handoff,Journey Day"]
        
        for message in export_data:
            tags = ','.join(message.get('llm_tags', []))
            handoff = 'Yes' if message.get('is_human_handoff') else 'No'
            
            # Escape commas and quotes in message text
            message_text = str(message.get('raw_text', '')).replace('"', '""')
            if ',' in message_text or '"' in message_text or '\n' in message_text:
                message_text = f'"{message_text}"'
            
            csv_lines.append(f"{message.get('timestamp')},{message.get('user_phone')},{message.get('direction')},{message_text},{message.get('llm_sentiment', '')},{tags},{handoff},{message.get('user_day', '')}")
        
        csv_content = '\n'.join(csv_lines)
        
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=chat_export_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
    except Exception as e:
        logger.error(f"Error exporting chats: {e}")
        return f"Error exporting chats: {e}", 500

@app.route('/api/users/<user_phone>/clear', methods=['POST'])
def clear_user_data(user_phone):
    """Clear all data for a specific user - useful for testing"""
    try:
        # Get user first
        user = db_manager.get_user_by_phone(user_phone)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Delete all message logs for this user
        message_count = MessageLog.query.filter_by(user_id=user.id).count()
        MessageLog.query.filter_by(user_id=user.id).delete()
        
        # Delete the user record
        User.query.filter_by(phone_number=user_phone).delete()
        
        # Commit the changes
        db.session.commit()
        
        logger.info(f"Cleared user data for {user_phone}: {message_count} messages deleted")
        
        return jsonify({
            'success': True, 
            'message': f'Successfully cleared user {user_phone}',
            'deleted_messages': message_count
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error clearing user data for {user_phone}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/recent-messages')
def get_recent_messages():
    """Get recent unique users with their latest messages for dashboard display"""
    try:
        # Get recent unique users instead of individual messages to avoid duplicates
        recent_users = db_manager.get_recent_active_users(limit=10)
        return jsonify(recent_users)
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test-image-delivery', methods=['POST'])
def test_image_delivery():
    """Test image delivery functionality"""
    try:
        # Get Day 1 content with image
        content = db_manager.get_content_by_day(1)
        if not content:
            return jsonify({'error': 'No Day 1 content found'}), 404
            
        content_dict = content.to_dict()
        
        # Test with simulation mode
        telegram_service.simulate_mode = True
        
        # Test image delivery
        media_url = content_dict.get('media_url')
        if media_url and content_dict.get('media_type') == 'image':
            # Test photo sending
            result = telegram_service.send_photo('test123', media_url)
            
            return jsonify({
                'success': True,
                'media_url': media_url,
                'media_type': content_dict.get('media_type'),
                'file_exists': 'eedc82fc-a7f5-4f0a-8f92-995d8532aca4_jc-ups2-psd2.jpeg' in media_url,
                'simulation_result': result
            })
        else:
            return jsonify({'error': 'No image content found for Day 1'}), 404
            
    except Exception as e:
        logger.error(f"Error testing image delivery: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat/<int:user_id>')
@login_required
def view_full_chat(user_id):
    """Display full chat history for a specific user with bot isolation"""
    try:
        # Get user information
        user = User.query.get(user_id)
        if not user:
            return "User not found", 404
        
        # Get all messages for this user with bot isolation
        messages = db_manager.get_user_messages_by_id(user_id, limit=1000)
        
        # Create a comprehensive user dict with enhanced information
        user_dict = {
            'id': user.id,
            'phone_number': user.phone_number,
            'name': user.name,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'status': user.status,
            'current_day': user.current_day,
            'join_date': user.join_date,
            'language_code': user.language_code,
            'is_premium': user.is_premium,
            'country': user.country,
            'region': user.region,
            'city': user.city,
            'ip_address': user.ip_address
        }
        
        return render_template('full_chat.html', user=user_dict, messages=messages, current_user=current_user, timestamp=int(datetime.utcnow().timestamp()))
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return f"Error loading chat history: {e}", 500

# Authentication Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard')
            flash('Login successful!', 'success')
            return redirect(next_page)
        flash('Invalid username or password', 'error')
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Registration page (admin only)"""
    if current_user.role != 'super_admin':
        flash('Only super admins can create new users.', 'error')
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = AdminUser(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f'User {form.username.data} has been registered successfully!', 'success')
        return redirect(url_for('user_management'))
    return render_template('auth/register.html', form=form)

@app.route('/user-management')
@login_required
def user_management():
    """User management page"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    users = AdminUser.query.all()
    return render_template('auth/user_management.html', users=users)

@app.route('/edit-user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """Edit user page"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = AdminUser.query.get_or_404(user_id)
    form = EditUserForm(obj=user)
    
    if form.validate_on_submit():
        user.username = form.username.data
        user.email = form.email.data
        user.full_name = form.full_name.data
        user.role = form.role.data
        user.is_active = form.is_active.data
        db.session.commit()
        flash(f'User {user.username} has been updated successfully!', 'success')
        return redirect(url_for('user_management'))
    
    return render_template('auth/edit_user.html', form=form, user=user)

@app.route('/cms/content/create', methods=['POST'])
@login_required
def cms_create_content():
    """Handle CMS content creation with file uploads"""
    try:
        # Handle file uploads first
        image_filename = None
        video_filename = None
        audio_filename = None
        
        # Process image upload
        if 'image_file' in request.files:
            image_file = request.files['image_file']
            if image_file and image_file.filename:
                filename = secure_filename(image_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                image_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
                os.makedirs(image_dir, exist_ok=True)
                image_file.save(os.path.join(image_dir, unique_filename))
                image_filename = unique_filename
                logger.info(f"Image uploaded for content: {unique_filename}")
        
        # Process video upload
        if 'video_file' in request.files:
            video_file = request.files['video_file']
            if video_file and video_file.filename:
                filename = secure_filename(video_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
                os.makedirs(video_dir, exist_ok=True)
                video_file.save(os.path.join(video_dir, unique_filename))
                video_filename = unique_filename
                logger.info(f"Video uploaded for content: {unique_filename}")
        
        # Process audio upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file and audio_file.filename:
                filename = secure_filename(audio_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
                os.makedirs(audio_dir, exist_ok=True)
                audio_file.save(os.path.join(audio_dir, unique_filename))
                audio_filename = unique_filename
                logger.info(f"Audio uploaded for content: {unique_filename}")
        
        # Parse form data
        day_number = int(request.form.get('day_number'))
        title = request.form.get('title')
        content = request.form.get('content')
        reflection_question = request.form.get('reflection_question')
        media_type = request.form.get('media_type', 'text')
        is_active = request.form.get('is_active') == 'true'
        
        # Parse tags from JSON string
        tags_json = request.form.get('tags', '[]')
        try:
            tags = json.loads(tags_json) if tags_json else []
        except json.JSONDecodeError:
            tags = []
        
        # Get bot_id from form data (defaults to 1 for backward compatibility)
        bot_id = int(request.form.get('bot_id', 1))
        
        # Create content
        content_id = db_manager.create_content(
            day_number=day_number,
            title=title,
            content=content,
            reflection_question=reflection_question,
            tags=tags,
            media_type=media_type,
            image_filename=image_filename,
            video_filename=video_filename,
            youtube_url=request.form.get('youtube_url'),  # Keep for backwards compatibility
            audio_filename=audio_filename,
            is_active=is_active,
            bot_id=bot_id,
            content_type=form_data.get('content_type', 'daily')
        )
        
        if content_id:
            logger.info(f"Content created successfully: Day {day_number} with media type {media_type}")
            return jsonify({'success': True, 'id': content_id})
        else:
            return jsonify({'success': False, 'error': 'Failed to create content'}), 500
            
    except Exception as e:
        logger.error(f"Error creating CMS content: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/cms/content/edit/<int:content_id>', methods=['POST'])
@login_required
def cms_edit_content(content_id):
    """Handle CMS content editing with file uploads"""
    try:
        # Handle file uploads first
        image_filename = None
        video_filename = None
        audio_filename = None
        
        # Process image upload
        if 'image_file' in request.files:
            image_file = request.files['image_file']
            if image_file and image_file.filename:
                filename = secure_filename(image_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                image_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
                os.makedirs(image_dir, exist_ok=True)
                image_file.save(os.path.join(image_dir, unique_filename))
                image_filename = unique_filename
                logger.info(f"Image uploaded for content update: {unique_filename}")
        
        # Process video upload
        if 'video_file' in request.files:
            video_file = request.files['video_file']
            if video_file and video_file.filename:
                filename = secure_filename(video_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
                os.makedirs(video_dir, exist_ok=True)
                video_file.save(os.path.join(video_dir, unique_filename))
                video_filename = unique_filename
                logger.info(f"Video uploaded for content update: {unique_filename}")
        
        # Process audio upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file and audio_file.filename:
                filename = secure_filename(audio_file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
                os.makedirs(audio_dir, exist_ok=True)
                audio_file.save(os.path.join(audio_dir, unique_filename))
                audio_filename = unique_filename
                logger.info(f"Audio uploaded for content update: {unique_filename}")
        
        # Parse form data
        title = request.form.get('title')
        content = request.form.get('content')
        reflection_question = request.form.get('reflection_question')
        media_type = request.form.get('media_type', 'text')
        is_active = request.form.get('is_active') == 'true'
        
        # Parse tags from JSON string
        tags_json = request.form.get('tags', '[]')
        try:
            tags = json.loads(tags_json) if tags_json else []
        except json.JSONDecodeError:
            tags = []
        
        # Update content
        success = db_manager.update_content(
            content_id=content_id,
            title=title,
            content=content,
            reflection_question=reflection_question,
            tags=tags,
            media_type=media_type,
            image_filename=image_filename,
            video_filename=video_filename,
            youtube_url=request.form.get('youtube_url'),  # Keep for backwards compatibility
            audio_filename=audio_filename,
            is_active=is_active,
            content_type=request.form.get('content_type', 'daily')
        )
        
        if success:
            logger.info(f"Content updated successfully: ID {content_id} with media type {media_type}")
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to update content'}), 500
            
    except Exception as e:
        logger.error(f"Error updating CMS content: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password page"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash('Your password has been changed successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Current password is incorrect.', 'error')
    return render_template('auth/change_password.html', form=form)

@app.route('/delete-user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    user = AdminUser.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('user_management'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User {username} has been deleted successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/static/uploads/<subfolder>/<filename>')
def serve_uploaded_file(subfolder, filename):
    """Serve uploaded media files from subdirectories"""
    safe_subfolder = secure_filename(subfolder)
    safe_filename = secure_filename(filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_subfolder)
    return send_from_directory(file_path, safe_filename)

# File upload helper functions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, subfolder, allowed_extensions):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename, allowed_extensions):
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Save file
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        return unique_filename
    return None

# Enhanced CMS Routes with Multimedia Support

@app.route('/cms/content/create', methods=['GET', 'POST'])
@login_required
def cms_content_create():
    """Create new multimedia content"""
    form = ContentForm()
    
    if form.validate_on_submit():
        # Handle file uploads
        image_filename = None
        audio_filename = None
        youtube_url = None
        
        if form.media_type.data == 'image' and form.image_file.data:
            image_filename = save_uploaded_file(
                form.image_file.data, 'images', ['jpg', 'jpeg', 'png', 'gif']
            )
        
        if form.media_type.data == 'audio' and form.audio_file.data:
            audio_filename = save_uploaded_file(
                form.audio_file.data, 'audio', ['mp3', 'wav', 'ogg', 'm4a']
            )
        
        if form.media_type.data == 'video' and form.youtube_url.data:
            youtube_url = form.youtube_url.data.strip()
        
        # Process tags
        tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()] if form.tags.data else []
        
        content_id = db_manager.create_content(
            day_number=form.day_number.data,
            title=form.title.data,
            content=form.content.data,
            reflection_question=form.reflection_question.data,
            tags=tags,
            media_type=form.media_type.data,
            image_filename=image_filename,
            youtube_url=youtube_url,
            audio_filename=audio_filename,
            is_active=form.is_active.data
        )
        
        if content_id:
            flash(f'Day {form.day_number.data} multimedia content created successfully!', 'success')
            return redirect(url_for('cms'))
        else:
            flash('Error creating content. Please try again.', 'danger')
    
    return render_template('cms_content_form.html', form=form, title="Create Multimedia Content", user=current_user)

@app.route('/cms/content/edit/<int:content_id>', methods=['GET', 'POST'])
@login_required
def cms_content_edit(content_id):
    """Edit existing multimedia content"""
    content = Content.query.get_or_404(content_id)
    
    if request.method == 'POST':
        # Handle form data from JavaScript FormData
        try:
            # Handle file uploads (keep existing files if no new upload)
            image_filename = content.image_filename
            audio_filename = content.audio_filename
            youtube_url = content.youtube_url
            
            # Get form data
            media_type = request.form.get('media_type', 'text')
            title = request.form.get('title', '')
            content_text = request.form.get('content', '')
            reflection_question = request.form.get('reflection_question', '')
            tags_json = request.form.get('tags', '[]')
            is_active = request.form.get('is_active') == 'true'
            
            # Process tags
            try:
                import json
                tags = json.loads(tags_json) if tags_json else []
            except:
                tags = []
            
            # Handle file uploads
            if media_type == 'image' and 'image_file' in request.files:
                file = request.files['image_file']
                if file and file.filename:
                    image_filename = save_uploaded_file(
                        file, 'images', ['jpg', 'jpeg', 'png', 'gif']
                    )
            
            if media_type == 'audio' and 'audio_file' in request.files:
                file = request.files['audio_file']
                if file and file.filename:
                    audio_filename = save_uploaded_file(
                        file, 'audio', ['mp3', 'wav', 'ogg', 'm4a']
                    )
            
            if media_type == 'video':
                youtube_url = request.form.get('youtube_url', '').strip() or None
            
            # Clear unused media fields based on media type
            if media_type != 'image':
                image_filename = None
            if media_type != 'audio':
                audio_filename = None
            if media_type != 'video':
                youtube_url = None
            
            logger.info(f"Updating content {content_id}: media_type={media_type}, youtube_url={youtube_url}")
            
            success = db_manager.update_content(
                content_id=content_id,
                title=title,
                content=content_text,
                reflection_question=reflection_question,
                tags=tags,
                media_type=media_type,
                image_filename=image_filename,
                youtube_url=youtube_url,
                audio_filename=audio_filename,
                is_active=is_active
            )
            
            if success:
                return '', 200  # Success response for JavaScript
            else:
                return 'Error updating content', 500
                
        except Exception as e:
            logger.error(f"Error updating content {content_id}: {e}")
            return f'Error updating content: {str(e)}', 500
    
    # GET request - show form for template-based editing (fallback)
    form = ContentForm(obj=content)
    if request.method == 'GET':
        form.tags.data = ', '.join(content.tags) if content.tags else ''
        form.youtube_url.data = content.youtube_url
    
    return render_template('cms_content_form.html', form=form, title="Edit Multimedia Content", content=content, user=current_user)

@app.route('/cms/content/delete/<int:content_id>', methods=['POST'])
@login_required
def cms_content_delete(content_id):
    """Delete multimedia content and associated files"""
    content = Content.query.get_or_404(content_id)
    day_number = content.day_number
    
    # Delete associated files
    if content.image_filename:
        try:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], 'images', content.image_filename)
            if os.path.exists(image_path):
                os.remove(image_path)
        except Exception as e:
            logger.warning(f"Could not delete image file: {e}")
    
    if content.audio_filename:
        try:
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], 'audio', content.audio_filename)
            if os.path.exists(audio_path):
                os.remove(audio_path)
        except Exception as e:
            logger.warning(f"Could not delete audio file: {e}")
    
    if db_manager.delete_content(content_id):
        flash(f'Day {day_number} multimedia content deleted successfully!', 'success')
    else:
        flash('Error deleting content. Please try again.', 'danger')
    
    return redirect(url_for('cms'))

@app.route('/test_day1_delivery', methods=['POST'])
def test_day1_delivery():
    """Test endpoint to manually trigger Day 1 content delivery"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        platform = data.get('platform', 'telegram')
        bot_id = data.get('bot_id', 5)
        
        logger.info(f"Manual Day 1 test for {phone_number}, platform: {platform}, bot_id: {bot_id}")
        success = scheduler.send_content_to_user(phone_number)
        
        return jsonify({
            'success': success,
            'message': f'Day 1 content delivery {"successful" if success else "failed"} for {phone_number}'
        })
    except Exception as e:
        logger.error(f"Error in test Day 1 delivery: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Initialize application context for both Gunicorn and development
with app.app_context():
    # Create database tables
    db.create_all()
    
    # Initialize database with sample content
    db_manager.initialize_sample_content()
    
    # Create default super admin if no users exist
    if AdminUser.query.count() == 0:
        admin = AdminUser(
            username='admin',
            email='admin@faithjourney.com',
            full_name='System Administrator',
            role='super_admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        logger.info("Default admin user created: admin / admin123")

# Start background scheduler for both Gunicorn and development
start_scheduler()

if __name__ == '__main__':
    # Start Flask app only when running directly (development mode)
    app.run(host='0.0.0.0', port=5000, debug=True)
