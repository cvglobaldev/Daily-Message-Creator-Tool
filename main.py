import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session, flash, send_from_directory
from models import db, User, Content, MessageLog, AdminUser
from db_manager import DatabaseManager
from services import WhatsAppService, TelegramService, GeminiService
from scheduler import ContentScheduler
import threading
import time
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm, EditUserForm, ChangePasswordForm, ContentForm
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "faith-journey-secret-key")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return AdminUser.query.get(int(user_id))

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
                logger.info("Running content scheduler (every 10 minutes for testing)...")
                with app.app_context():  # Ensure Flask app context for database operations
                    scheduler.send_daily_content()
                # Sleep for 10 minutes (600 seconds) between content deliveries
                time.sleep(600)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")

@app.route('/')
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
def telegram_webhook():
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
                
                # Process the message
                process_incoming_message(phone_number, message_text, platform="telegram", 
                                       user_data={"username": username, "first_name": first_name, "chat_id": chat_id})
        
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
                    
                    # Process as regular message
                    process_incoming_message(phone_number, reply_text, platform="telegram", 
                                           user_data={"username": user_info.get('username', ''), 
                                                     "first_name": user_info.get('first_name', ''), 
                                                     "chat_id": chat_id})
                    
                    # Answer the callback query
                    telegram_service.answer_callback_query(callback_query_id, "Thank you for your response!")
                
                else:
                    # Answer unknown callback queries
                    telegram_service.answer_callback_query(callback_query_id, "Response received")
                
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/whatsapp', methods=['POST'])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        logger.debug(f"Received webhook data: {data}")
        
        # Extract message data (structure may vary based on WhatsApp provider)
        # This is a generic structure that works with most providers
        if 'messages' in data:
            for message_data in data['messages']:
                phone_number = message_data.get('from', '').replace('whatsapp:', '')
                message_text = message_data.get('text', {}).get('body', '').strip()
                
                if phone_number and message_text:
                    process_incoming_message(phone_number, message_text, platform="whatsapp")
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return jsonify({"error": str(e)}), 500

def process_incoming_message(phone_number: str, message_text: str, platform: str = "whatsapp", user_data: dict = None):
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
            handle_start_command(phone_number, platform, user_data)
            return
        
        elif message_lower == 'stop' or message_lower == '/stop':
            handle_stop_command(phone_number, platform)
            return
        
        elif message_lower == 'help' or message_lower == '/help':
            handle_help_command(phone_number, platform)
            return
        
        elif message_lower == 'human' or message_lower == '/human':
            handle_human_command(phone_number, platform)
            return
        
        # Check for human handoff triggers
        if any(keyword in message_lower for keyword in HUMAN_HANDOFF_KEYWORDS):
            handle_human_handoff(phone_number, message_text, platform)
            return
        
        # Handle regular response (likely to a reflection question)
        handle_reflection_response(phone_number, message_text, platform)
        
    except Exception as e:
        logger.error(f"Error processing message from {phone_number}: {e}")
        # Send error message to user
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error processing your message. Please try again or type HELP for assistance."
        )

def send_message_to_platform(phone_number: str, platform: str, message: str, 
                           with_quick_replies: bool = False, copy_text: str = "", 
                           copy_label: str = "Copy Text") -> bool:
    """Send message to the appropriate platform with enhanced features"""
    try:
        if platform == "telegram":
            # Extract chat_id from tg_ prefixed phone number
            if phone_number.startswith("tg_"):
                chat_id = phone_number[3:]  # Remove 'tg_' prefix
                
                # Enhanced Telegram messaging with 2025 features
                if copy_text and copy_label:
                    # Send message with copy button for Bible verses or inspirational content
                    return telegram_service.send_copy_text_message(chat_id, message, copy_text, copy_label)
                elif with_quick_replies:
                    # Send message with quick reply buttons for common responses
                    quick_replies = [
                        "Tell me more", "I have a question", 
                        "This is helpful", "I need time to think"
                    ]
                    return telegram_service.send_quick_reply_message(chat_id, message, quick_replies)
                else:
                    return telegram_service.send_message(chat_id, message)
            else:
                logger.error(f"Invalid Telegram chat_id format: {phone_number}")
                return False
        else:
            # Default to WhatsApp (enhanced features not yet implemented)
            return whatsapp_service.send_message(phone_number, message)
    except Exception as e:
        logger.error(f"Error sending message to {platform}: {e}")
        return False

def handle_start_command(phone_number: str, platform: str = "whatsapp", user_data: dict = None):
    """Handle START command - onboard new user"""
    try:
        logger.info(f"Processing START command for {phone_number} on {platform}")
        # Check if user already exists
        existing_user = db_manager.get_user_by_phone(phone_number)
        
        if existing_user and existing_user.status == 'active':
            # Allow restart - reset to Day 1
            db_manager.update_user(phone_number, 
                                 current_day=1, 
                                 join_date=datetime.now())
            platform_emoji = "📱" if platform == "telegram" else "📱"
            restart_message = (f"Restarting your Faith Journey! {platform_emoji}\n\n"
                              "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                              "After each piece of content, I'll ask you a simple reflection question.\n\n"
                              "Available Commands:\n"
                              f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                              f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                              f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                              f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                              "Day 1 content will arrive in 10 seconds!")
            send_message_to_platform(phone_number, platform, restart_message)
            
            # Log the RESTART command for chat management visibility
            db_manager.log_message(
                user=existing_user,
                direction='incoming',
                raw_text=f'/start' if platform == 'telegram' else 'START',
                sentiment='positive',
                tags=['RESTART', 'RETURNING_USER', 'ONBOARDING'],
                confidence=1.0
            )
            
            # Send Day 1 content after 10 second delay
            def delayed_content():
                with app.app_context():
                    time.sleep(10)
                    scheduler.send_content_to_user(phone_number)
            threading.Thread(target=delayed_content, daemon=True).start()
            logger.info(f"User {phone_number} restarted journey from Day 1")
            return
        
        # Create or reactivate user
        if existing_user:
            db_manager.update_user(phone_number, 
                                 status='active', 
                                 current_day=1, 
                                 join_date=datetime.now())
        else:
            db_manager.create_user(phone_number, 
                                 status='active', 
                                 current_day=1, 
                                 tags=[])
        
        # Send welcome message
        platform_emoji = "📱" if platform == "telegram" else "📱"
        welcome_message = (f"Welcome to your Faith Journey! {platform_emoji}\n\n"
                          "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                          "After each piece of content, I'll ask you a simple reflection question.\n\n"
                          "Available Commands:\n"
                          f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                          f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                          f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                          f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                          "Day 1 content will arrive in 10 seconds!")
        
        logger.info(f"Sending welcome message to {phone_number}: {welcome_message[:100]}...")
        send_message_to_platform(phone_number, platform, welcome_message)
        
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
        
        # Send Day 1 content after 10 second delay
        def delayed_content():
            with app.app_context():
                time.sleep(10)
                scheduler.send_content_to_user(phone_number)
        threading.Thread(target=delayed_content, daemon=True).start()
        
        logger.info(f"User {phone_number} successfully onboarded")
        
    except Exception as e:
        logger.error(f"Error handling START command for {phone_number}: {e}")
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error setting up your journey. Please try again."
        )

def handle_stop_command(phone_number: str, platform: str = "whatsapp"):
    """Handle STOP command - deactivate user"""
    try:
        user = db_manager.get_user_by_phone(phone_number)
        if user:
            db_manager.update_user(phone_number, status='inactive')
            
            message = ("You have been unsubscribed from the Faith Journey. "
                      "If you'd like to restart your journey, simply send START anytime. "
                      "Peace be with you. 🙏")
        else:
            message = "You weren't subscribed to any journey. Send START to begin your faith journey."
        
        send_message_to_platform(phone_number, platform, message)
        logger.info(f"User {phone_number} unsubscribed")
        
    except Exception as e:
        logger.error(f"Error handling STOP command for {phone_number}: {e}")

def handle_help_command(phone_number: str, platform: str = "whatsapp"):
    """Handle HELP command"""
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
    
    send_message_to_platform(phone_number, platform, help_message)

def handle_human_command(phone_number: str, platform: str = "whatsapp"):
    """Handle HUMAN command - direct human chat request"""
    try:
        # Get or create user
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number, status='active', current_day=1)
        
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
        
        # Send response to user
        response_message = ("🤝 Direct Human Chat Requested\n\n"
                          "Thank you for reaching out! A member of our team will connect with you shortly. "
                          "This conversation has been flagged for priority human response.\n\n"
                          "In the meantime, know that you are valued and your journey matters. "
                          "Feel free to share what's on your heart. 🙏")
        
        send_message_to_platform(phone_number, platform, response_message)
        
        logger.warning(f"HUMAN COMMAND - Direct chat requested by {phone_number} on {platform}")
        
    except Exception as e:
        logger.error(f"Error handling HUMAN command for {phone_number}: {e}")
        send_message_to_platform(
            phone_number, platform,
            "Sorry, there was an error connecting you with a human. Please try again or contact us directly."
        )

def handle_human_handoff(phone_number: str, message_text: str, platform: str = "whatsapp"):
    """Handle messages that require human intervention"""
    try:
        # Get or create user
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number)
        
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
        
        send_message_to_platform(phone_number, platform, response_message)
        
        logger.warning(f"HUMAN HANDOFF requested by {phone_number}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error handling human handoff for {phone_number}: {e}")

def handle_reflection_response(phone_number: str, message_text: str, platform: str = "whatsapp"):
    """Handle user's reflection response with contextual AI response"""
    try:
        # Analyze the response with Gemini
        analysis = gemini_service.analyze_response(message_text)
        
        # Get or create user
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            user = db_manager.create_user(phone_number)
        
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
        content = db_manager.get_content_by_day(current_day) if current_day > 0 else None
        
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
        send_message_to_platform(phone_number, platform, contextual_response)
        
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
        send_message_to_platform(phone_number, platform, fallback_response)

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
    """API endpoint to get all content"""
    try:
        content = db_manager.get_all_content()
        return jsonify([c.to_dict() for c in content])
    except Exception as e:
        logger.error(f"Error getting content: {e}")
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
            youtube_url=data.get('youtube_url'),
            audio_filename=data.get('audio_filename'),
            is_active=data.get('is_active', True)
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
@app.route('/chat/<int:user_id>')
def chat_history(user_id):
    """Display chat history for a specific user"""
    try:
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return "User not found", 404
            
        messages = db_manager.get_user_messages(user_id)
        return render_template('chat_history.html', user=user, messages=messages)
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return f"Error loading chat history: {e}", 500

@app.route('/settings')
@login_required
def settings_page():
    """Display chatbot settings page"""
    try:
        settings = db_manager.get_chatbot_settings()
        default_prompt = """You are a compassionate AI assistant helping people on their faith journey to learn about Jesus. 

Your role:
- Respond with warmth, understanding, and respect for the user's background
- Reference their current day's content when relevant
- Encourage reflection and spiritual growth
- Be sensitive to users from Muslim backgrounds
- Provide biblical insights in an accessible way
- Guide users toward a deeper understanding of Jesus

Always maintain a respectful, caring tone and be ready to offer prayer or encouragement when needed."""
        
        return render_template('settings.html', settings=settings, default_prompt=default_prompt, user=current_user)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return f"Error loading settings: {e}", 500

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
    """API endpoint to get filtered messages"""
    try:
        # Get filter parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        sort_field = request.args.get('sort_field', 'timestamp')
        sort_order = request.args.get('sort_order', 'desc')
        
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
        
        # Get filtered messages
        result = db_manager.get_filtered_messages(
            page=page,
            limit=limit,
            sort_field=sort_field,
            sort_order=sort_order,
            filters=filters
        )
        
        # Get stats for current filter
        stats = db_manager.get_chat_management_stats(filters)
        
        return jsonify({
            'success': True,
            'messages': result['messages'],
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
    """Get recent messages for dashboard display"""
    try:
        # Get the 10 most recent messages
        messages = db_manager.get_filtered_messages(
            page=1,
            limit=10,
            sort_field='timestamp',
            sort_order='desc',
            filters={}
        )
        
        return jsonify(messages['messages'])
    except Exception as e:
        logger.error(f"Error getting recent messages: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat/<int:user_id>')
@login_required
def view_full_chat(user_id):
    """Display full chat history for a specific user"""
    try:
        # Get user information
        user = User.query.get(user_id)
        if not user:
            return "User not found", 404
        
        # Get all messages for this user
        messages = db_manager.get_user_messages_by_id(user_id, limit=1000)
        
        # Create a user dict to ensure template compatibility
        user_dict = {
            'id': user.id,
            'phone_number': user.phone_number,
            'status': user.status,
            'current_day': user.current_day,
            'join_date': user.join_date
        }
        
        return render_template('full_chat.html', user=user_dict, messages=messages, current_user=current_user)
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

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded multimedia files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
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
    
    # Start background scheduler
    start_scheduler()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
