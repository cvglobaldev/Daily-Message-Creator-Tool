import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict
from flask import Flask, request, jsonify, render_template, make_response, redirect, url_for, session, flash, send_from_directory
from models import db, User, Content, MessageLog, AdminUser, Bot
from db_manager import DatabaseManager
from services import WhatsAppService, TelegramService, GeminiService, SpeechToTextService, TextToSpeechService
from rule_engine import rule_engine
from scheduler import ContentScheduler
import threading
import time
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from forms import LoginForm, RegistrationForm, EditUserForm, ChangePasswordForm, ContentForm, AIContentGenerationForm
from bot_forms import CreateBotForm, EditBotForm, BotContentForm
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid
import signal
from sqlalchemy import text, func, cast, ARRAY, String
from sqlalchemy.dialects.postgresql import JSONB
from location_utils import extract_telegram_user_data, get_ip_location_data
from universal_media_prevention_system import validate_and_upload_with_prevention
from media_file_browser import MediaFileBrowser

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Reduce urllib3 logging to prevent token leakage in logs
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size for videos

# Production middleware configuration
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # Needed for url_for to generate with https

# Request timeout handling
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Request timeout")

# Set request timeout (30 seconds)
signal.signal(signal.SIGALRM, timeout_handler)

@app.before_request
def before_request_timeout():
    # Skip timeout for AI content generation endpoints (they need more time)
    if request.endpoint and 'ai_content_generation' in request.endpoint:
        return
    # Set 30 second timeout for other requests
    signal.alarm(30)

@app.after_request
def after_request_timeout(response):
    # Clear the alarm
    signal.alarm(0)
    return response

@app.errorhandler(TimeoutError)
def handle_timeout(e):
    logger.error(f"Request timeout: {e}")
    return jsonify({"error": "Request timeout"}), 408

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

# Enable template debugging
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['EXPLAIN_TEMPLATE_LOADING'] = True

# Initialize database
db.init_app(app)

# Initialize services
db_manager = DatabaseManager()
whatsapp_service = WhatsAppService()
telegram_service = TelegramService()
gemini_service = GeminiService()
scheduler = ContentScheduler(whatsapp_service, telegram_service, db_manager)

# Global flag and lock to ensure scheduler starts only once
scheduler_started = False
scheduler_lock = threading.Lock()

# Cache for bot-specific services
bot_telegram_services = {}
bot_whatsapp_services = {}

def get_whatsapp_service_for_bot(bot_id):
    """Get bot-specific WhatsApp service using environment variables"""
    logger.info(f"🔥 DEBUG: Getting WhatsApp service for bot_id {bot_id}")
    try:
        if bot_id not in bot_whatsapp_services:
            with app.app_context():  # Ensure database context
                # Always use environment variables for WhatsApp credentials
                access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
                phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
                
                if access_token and phone_number_id:
                    bot_whatsapp_services[bot_id] = WhatsAppService(access_token, phone_number_id)
                    logger.info(f"🔥 DEBUG: Created new WhatsAppService for bot_id {bot_id} with environment credentials")
                else:
                    # Fallback to default service
                    bot_whatsapp_services[bot_id] = whatsapp_service
                    logger.info(f"🔥 DEBUG: Using default WhatsAppService for bot_id {bot_id} (missing credentials)")
        else:
            logger.info(f"🔥 DEBUG: Using cached WhatsAppService for bot_id {bot_id}")
        return bot_whatsapp_services[bot_id]
    except Exception as e:
        logger.error(f"🔥 ERROR: Failed to get WhatsApp service for bot_id {bot_id}: {e}")
        return whatsapp_service  # Fallback to default

def invalidate_bot_service_cache(bot_id):
    """Invalidate cached services for a bot when its configuration changes"""
    logger.info(f"Invalidating service cache for bot_id {bot_id}")
    if bot_id in bot_telegram_services:
        del bot_telegram_services[bot_id]
    if bot_id in bot_whatsapp_services:
        del bot_whatsapp_services[bot_id]

def create_initial_test_users(bot_id: int, bot_name: str):
    """Create initial test users for a newly created bot"""
    try:
        # Check if we should create test users
        create_test_users = os.environ.get('CREATE_TEST_USERS', 'true').lower() == 'true'
        if not create_test_users:
            logger.info(f"Skipping test user creation for bot {bot_id} (CREATE_TEST_USERS=false)")
            return
        
        # Create test users for different scenarios
        test_users = [
            {
                'phone_number': f'+test_whatsapp_{bot_id}_001',
                'name': f'WhatsApp Test User - {bot_name}',
                'current_day': 1,
                'status': 'active',
                'platform': 'whatsapp'
            },
            {
                'phone_number': f'tg_test_{bot_id}_001',
                'name': f'Telegram Test User - {bot_name}',
                'current_day': 1,
                'status': 'active', 
                'platform': 'telegram'
            }
        ]
        
        created_count = 0
        for user_data in test_users:
            # Check if test user already exists
            existing_user = db_manager.get_user_by_phone(user_data['phone_number'])
            if not existing_user:
                user = User()
                user.phone_number = user_data['phone_number']
                user.name = user_data['name']
                user.current_day = user_data['current_day']
                user.status = user_data['status']
                user.bot_id = bot_id
                user.join_date = datetime.utcnow()
                
                db.session.add(user)
                created_count += 1
                logger.info(f"Created test user {user_data['phone_number']} for bot {bot_id}")
        
        if created_count > 0:
            db.session.commit()
            logger.info(f"Successfully created {created_count} test users for bot {bot_id}")
        else:
            logger.info(f"No new test users needed for bot {bot_id} (already exist)")
            
    except Exception as e:
        logger.error(f"Error creating test users for bot {bot_id}: {e}")
        db.session.rollback()

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
    """Start the background scheduler in a separate thread with thread-safe initialization"""
    global scheduler_started
    
    # Thread-safe check and initialization
    with scheduler_lock:
        # Double-check inside lock to prevent race conditions
        if scheduler_started:
            logger.warning("Scheduler already running, skipping duplicate start")
            return
        
        # Set flag immediately to prevent other threads from starting
        scheduler_started = True
    
    # Start the scheduler thread (outside lock to avoid blocking)
    def run_scheduler():
        while True:
            try:
                logger.info("Running content scheduler with bot-specific intervals...")
                with app.app_context():  # Ensure Flask app context for database operations
                    # Renew lock to show this worker is still active
                    renew_scheduler_lock()
                    # Run scheduler
                    scheduler.send_daily_content()
                # Sleep for 1 minute before checking again (allows for different bot intervals)
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")

def renew_scheduler_lock():
    """Renew the scheduler lock to show this worker is still active"""
    try:
        from models import SystemSettings, db
        import datetime
        
        lock_key = "scheduler_lock"
        lock = SystemSettings.query.filter_by(key=lock_key).first()
        
        if lock:
            lock.value = datetime.datetime.utcnow().isoformat()
            lock.updated_at = datetime.datetime.utcnow()
            db.session.commit()
    except Exception as e:
        logger.error(f"Failed to renew scheduler lock: {e}")

@app.route('/')
def index():
    """Public landing page that redirects to dashboard if logged in, otherwise to login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

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

@app.route('/analytics')
@login_required
def analytics_dashboard():
    """Comprehensive analytics dashboard with journey and faith insights"""
    try:
        from models import Bot, TagRule
        from sqlalchemy import func
        
        bot_id = request.args.get('bot_id', type=int)
        days_filter = request.args.get('days', type=int)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Default to 30 days if no filter is specified
        if not days_filter and not start_date_str and not end_date_str:
            days_filter = 30
        
        # Filter bots based on user role
        if current_user.role == 'super_admin':
            owned_bot_ids = [bot.id for bot in Bot.query.all()]
        else:
            # Regular admins can only see data from bots they created
            owned_bot_ids = [bot.id for bot in Bot.query.filter_by(creator_id=current_user.id).all()]
        
        query = User.query
        
        # Filter to only show users from owned bots
        if owned_bot_ids:
            query = query.filter(User.bot_id.in_(owned_bot_ids))
        else:
            # If regular admin has no bots, show nothing
            query = query.filter(User.bot_id == -1)
        
        if bot_id:
            # Additional filter by specific bot_id (must be owned)
            if bot_id in owned_bot_ids:
                query = query.filter(User.bot_id == bot_id)
            else:
                # Trying to access a bot they don't own - show nothing
                query = query.filter(User.bot_id == -1)
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            query = query.filter(User.join_date.between(start_date, end_date))
        elif days_filter:
            cutoff_date = datetime.utcnow() - timedelta(days=days_filter)
            query = query.filter(User.join_date >= cutoff_date)
        
        journey_funnel = {
            'Day 1-10': query.filter(User.current_day.between(1, 10)).count(),
            'Day 11-20': query.filter(User.current_day.between(11, 20)).count(),
            'Day 21-30': query.filter(User.current_day.between(21, 30)).count(),
            'Day 31-40': query.filter(User.current_day.between(31, 40)).count(),
            'Day 41-50': query.filter(User.current_day.between(41, 50)).count(),
            'Day 51-60': query.filter(User.current_day.between(51, 60)).count(),
            'Day 61-70': query.filter(User.current_day.between(61, 70)).count(),
            'Day 71-80': query.filter(User.current_day.between(71, 80)).count(),
            'Day 81-90': query.filter(User.current_day.between(81, 90)).count(),
            'Completed': query.filter(User.status == 'completed').count()
        }
        
        dropoff_data = {}
        for day in range(1, 91):
            total_reached = query.filter(User.current_day >= day).count()
            stopped_at = query.filter(User.current_day == day, User.status == 'stopped').count()
            if total_reached > 0:
                dropoff_data[day] = round((stopped_at / total_reached) * 100, 2)
            else:
                dropoff_data[day] = 0
        
        active_users = query.filter(User.status == 'active').all()
        avg_days = round(sum(u.current_day for u in active_users) / len(active_users), 1) if active_users else 0
        
        total_users = query.count()
        completed_users = query.filter(User.status == 'completed').count()
        completion_rate = round((completed_users / total_users) * 100, 1) if total_users > 0 else 0
        
        faith_journey_parent = TagRule.query.filter(
            TagRule.tag_name == 'Faith Journey',
            TagRule.parent_id.is_(None)
        ).first()
        
        faith_tags_distribution = {}
        tag_timeline = {}
        
        if faith_journey_parent:
            faith_tags = TagRule.query.filter(TagRule.parent_id == faith_journey_parent.id).all()
            
            # Optimized: Use database aggregation with proper JSON array checking
            for tag in faith_tags:
                # Cast JSON to JSONB and use @> operator for array contains
                count = query.filter(
                    func.cast(User.tags, JSONB).op('@>')(func.cast([tag.tag_name], JSONB))
                ).count()
                faith_tags_distribution[tag.tag_name] = count
            
            tag_names = [t.tag_name for t in faith_tags]
            
            # Optimized: Single grouped query instead of 90 separate queries
            tag_timeline_query = db.session.query(
                User.current_day,
                func.count(MessageLog.id).label('count')
            ).join(MessageLog, User.id == MessageLog.user_id)
            
            # Apply the same filters as the main query
            if bot_id:
                tag_timeline_query = tag_timeline_query.filter(User.bot_id == bot_id)
            
            if start_date_str and end_date_str:
                tag_timeline_query = tag_timeline_query.filter(
                    User.join_date.between(start_date, end_date)
                )
            elif days_filter:
                cutoff_date = datetime.utcnow() - timedelta(days=days_filter)
                tag_timeline_query = tag_timeline_query.filter(User.join_date >= cutoff_date)
            
            # Filter for messages containing any faith journey tag
            # Cast JSON to JSONB to use PostgreSQL's ?| operator for array overlap checking
            tag_timeline_query = tag_timeline_query.filter(
                func.cast(MessageLog.llm_tags, JSONB).op('?|')(cast(tag_names, ARRAY(String)))
            )
            
            # Group by day and execute
            tag_timeline_query = tag_timeline_query.group_by(User.current_day)
            tag_counts = tag_timeline_query.all()
            
            # Build the tag_timeline dict (initialize all days to 0)
            tag_timeline = {day: 0 for day in range(1, 91)}
            for day, count in tag_counts:
                if 1 <= day <= 90:
                    tag_timeline[day] = count
        
        total_faith_journeys = sum(faith_tags_distribution.values())
        
        # Filter bots based on user role for the dropdown
        if current_user.role == 'super_admin':
            all_bots = Bot.query.filter_by(status='active').all()
        else:
            all_bots = Bot.query.filter_by(status='active', creator_id=current_user.id).all()
        
        analytics_data = {
            'journey_funnel': journey_funnel,
            'dropoff_data': dropoff_data,
            'avg_days': avg_days,
            'total_users': total_users,
            'completed_users': completed_users,
            'completion_rate': completion_rate,
            'avg_journey_day': avg_days,
            'total_faith_journeys': total_faith_journeys,
            'faith_tags_distribution': faith_tags_distribution,
            'tag_timeline': tag_timeline,
            'all_bots': all_bots,
            'selected_bot_id': bot_id,
            'selected_days': days_filter,
            'start_date': start_date_str,
            'end_date': end_date_str
        }
        
        return render_template('analytics.html', **analytics_data)
        
    except Exception as e:
        logger.error(f"Error loading analytics dashboard: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Analytics error: {e}", 500

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
            user_info = message_data.get('from', {})
            username = user_info.get('username', '')
            first_name = user_info.get('first_name', '')
            
            # Get client IP address for location data
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            if client_ip and ',' in client_ip:
                client_ip = client_ip.split(',')[0].strip()
            
            phone_number = f"tg_{chat_id}"
            
            # Check for voice message
            if message_data.get('voice'):
                voice_data = message_data['voice']
                file_id = voice_data.get('file_id')
                duration = voice_data.get('duration', 0)
                
                logger.info(f"🎤 Telegram voice message from {chat_id} ({username}), duration: {duration}s")
                
                try:
                    # Get bot-specific Telegram service
                    bot_service = get_telegram_service_for_bot(bot_id)
                    bot_token = bot_service.bot_token
                    
                    # Download voice file using Telegram API
                    # Step 1: Get file path
                    file_info_url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
                    file_info_response = requests.get(file_info_url, timeout=30)
                    
                    if file_info_response.status_code == 200:
                        file_path = file_info_response.json().get('result', {}).get('file_path')
                        
                        if file_path:
                            # Step 2: Download actual file
                            file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                            file_response = requests.get(file_url, timeout=30)
                            
                            if file_response.status_code == 200:
                                audio_bytes = file_response.content
                                logger.info(f"✅ Downloaded Telegram voice file ({len(audio_bytes)} bytes)")
                                
                                # Process voice message
                                process_voice_message(phone_number, audio_bytes, platform="telegram", 
                                                    user_data=user_info, request_ip=client_ip, bot_id=bot_id)
                            else:
                                logger.error(f"Failed to download Telegram voice file: {file_response.status_code}")
                        else:
                            logger.error("No file_path in Telegram file info response")
                    else:
                        logger.error(f"Failed to get Telegram file info: {file_info_response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error downloading Telegram voice message: {e}")
                    send_message_to_platform(phone_number, "telegram", 
                        "Sorry, there was an error processing your voice message. Please try again or send a text message.", 
                        bot_id=bot_id)
            
            # Check for text message
            elif chat_id and message_data.get('text'):
                message_text = message_data.get('text', '').strip()
                
                logger.info(f"Telegram message from {chat_id} ({username}): {message_text}")
                
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
                if callback_data == 'human_yes':
                    # User chose to connect with human - add Human tag
                    user = db_manager.get_user_by_phone(phone_number)
                    if user:
                        db_manager.log_message(
                            user=user,
                            direction='incoming',
                            raw_text="User requested human connection via button",
                            sentiment='neutral',
                            tags=['Human']  # Add Human tag when user explicitly chooses
                        )
                    
                    # Send confirmation message
                    from models import Bot
                    bot = Bot.query.get(bot_id)
                    
                    if bot and bot.name and "indonesia" in bot.name.lower():
                        confirmation_msg = "✅ Terima kasih! Tim kami akan segera menghubungi Anda untuk memberikan dukungan personal."
                    else:
                        confirmation_msg = "✅ Thank you! Our team will connect with you soon for personal support."
                    
                    send_message_to_platform(phone_number, "telegram", confirmation_msg, bot_id=bot_id)
                    logger.info(f"Human connection requested by {phone_number}")
                    
                elif callback_data == 'human_no':
                    # User chose to continue with bot - provide contextual response
                    user = db_manager.get_user_by_phone(phone_number)
                    if user:
                        # Get the original message from recent logs to provide contextual response
                        recent_messages = db_manager.get_user_messages(phone_number)[:3]  # Get last 3 messages
                        if recent_messages and len(recent_messages) > 1:
                            # Find the original user message (not the human offer)
                            for msg in reversed(recent_messages):
                                if msg.direction == 'incoming' and 'human connection' not in msg.raw_text.lower():
                                    original_message = msg.raw_text
                                    logger.info(f"User chose bot response, providing contextual reply to: {original_message}")
                                    # Generate contextual response to the original message
                                    handle_contextual_conversation(phone_number, original_message, "telegram", bot_id)
                                    break
                    
                elif callback_data.startswith('content_confirm_yes_'):
                    # User confirmed they read the daily content - apply "Christian Learning" tag
                    day = callback_data.replace('content_confirm_yes_', '')
                    logger.info(f"User {phone_number} confirmed reading Day {day} content")
                    
                    user = db_manager.get_user_by_phone(phone_number)
                    if user:
                        # Log the message with tag
                        db_manager.log_message(
                            user=user,
                            direction='incoming',
                            raw_text=f"User confirmed reading Day {day} content",
                            sentiment='positive',
                            tags=['Christian Learning']
                        )
                        # Also add tag to user's profile
                        db_manager.add_user_tag(phone_number, 'Christian Learning')
                    
                    # Send positive feedback
                    from models import Bot
                    bot = Bot.query.get(bot_id)
                    
                    if bot and bot.name and "indonesia" in bot.name.lower():
                        feedback_msg = "✅ Terima kasih! Semoga pesan hari ini bermanfaat untuk perjalanan spiritualmu. 🙏"
                    else:
                        feedback_msg = "✅ Thank you! We hope today's message was meaningful for your spiritual journey. 🙏"
                    
                    send_message_to_platform(phone_number, "telegram", feedback_msg, bot_id=bot_id)
                    telegram_service.answer_callback_query(callback_query_id, "Thank you!")
                
                elif callback_data.startswith('content_confirm_no_'):
                    # User hasn't read it yet - send encouraging message
                    day = callback_data.replace('content_confirm_no_', '')
                    logger.info(f"User {phone_number} hasn't read Day {day} content yet")
                    
                    from models import Bot
                    bot = Bot.query.get(bot_id)
                    
                    if bot and bot.name and "indonesia" in bot.name.lower():
                        reminder_msg = "Tidak apa-apa! Silakan baca kapan pun Anda siap. Kami di sini untuk Anda. 😊"
                    else:
                        reminder_msg = "That's okay! Read it whenever you're ready. We're here for you. 😊"
                    
                    send_message_to_platform(phone_number, "telegram", reminder_msg, bot_id=bot_id)
                    telegram_service.answer_callback_query(callback_query_id, "No problem!")
                
                elif callback_data.startswith('quick_reply:'):
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
        logger.info(f"📥 Received WhatsApp webhook for bot {bot_id}: {data}")
        
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
                                    whatsapp_message_id = message_data.get('id', '')  # Unique WhatsApp message ID
                                    
                                    logger.info(f"📨 WhatsApp message: type={message_type}, from={phone_number}, id={whatsapp_message_id}")
                                    
                                    # **WEBHOOK DEDUPLICATION** - Check WhatsApp message ID first
                                    if whatsapp_message_id and _is_duplicate_webhook(whatsapp_message_id):
                                        logger.info(f"🚫 Duplicate WhatsApp webhook ignored: {whatsapp_message_id} from {phone_number}")
                                        continue
                                    
                                    message_text = ''
                                    button_id = None
                                    if message_type == 'text':
                                        message_text = message_data.get('text', {}).get('body', '').strip()
                                    elif message_type == 'button':
                                        message_text = message_data.get('button', {}).get('text', '').strip()
                                    elif message_type == 'interactive':
                                        interactive = message_data.get('interactive', {})
                                        if 'button_reply' in interactive:
                                            button_id = interactive['button_reply'].get('id', '')
                                            message_text = interactive['button_reply'].get('title', '').strip()
                                        elif 'list_reply' in interactive:
                                            message_text = interactive['list_reply'].get('title', '').strip()
                                    elif message_type in ['audio', 'voice']:
                                        # Handle voice/audio messages
                                        audio_data = message_data.get('audio') or message_data.get('voice')
                                        if audio_data:
                                            media_id = audio_data.get('id')
                                            logger.info(f"🎤 WhatsApp voice/audio message from {phone_number}, media_id: {media_id}")
                                            
                                            try:
                                                # Get client IP for location data
                                                client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                                                if client_ip and ',' in client_ip:
                                                    client_ip = client_ip.split(',')[0].strip()
                                                
                                                # Extract WhatsApp user data from contacts (if available)
                                                contacts_data = value.get('contacts', [])
                                                whatsapp_user_data = extract_whatsapp_user_data(message_data, contacts_data, client_ip)
                                                
                                                # Get bot-specific WhatsApp service
                                                bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                                                access_token = bot_whatsapp_service.access_token
                                                
                                                # Download audio using WhatsApp Media API
                                                # Step 1: Get media URL
                                                media_url_endpoint = f"https://graph.facebook.com/v18.0/{media_id}"
                                                headers = {"Authorization": f"Bearer {access_token}"}
                                                media_url_response = requests.get(media_url_endpoint, headers=headers, timeout=30)
                                                
                                                if media_url_response.status_code == 200:
                                                    media_url = media_url_response.json().get('url')
                                                    
                                                    if media_url:
                                                        # Step 2: Download actual file
                                                        file_response = requests.get(media_url, headers=headers, timeout=30)
                                                        
                                                        if file_response.status_code == 200:
                                                            audio_bytes = file_response.content
                                                            logger.info(f"✅ Downloaded WhatsApp audio file ({len(audio_bytes)} bytes)")
                                                            
                                                            # Process voice message
                                                            process_voice_message(phone_number, audio_bytes, platform="whatsapp", 
                                                                                user_data=whatsapp_user_data, request_ip=client_ip, bot_id=bot_id)
                                                        else:
                                                            logger.error(f"Failed to download WhatsApp audio file: {file_response.status_code}")
                                                    else:
                                                        logger.error("No URL in WhatsApp media response")
                                                else:
                                                    logger.error(f"Failed to get WhatsApp media URL: {media_url_response.status_code}")
                                                    
                                            except Exception as e:
                                                logger.error(f"Error downloading WhatsApp voice message: {e}")
                                                bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                                                bot_whatsapp_service.send_message(phone_number, 
                                                    "Sorry, there was an error processing your voice message. Please try again or send a text message.")
                                            
                                            # Skip normal text processing for voice messages
                                            continue
                                    
                                    # Handle content confirmation buttons (WhatsApp)
                                    if button_id and button_id.startswith('content_confirm_'):
                                        user = db_manager.get_user_by_phone(phone_number)
                                        if button_id.startswith('content_confirm_yes_'):
                                            day = button_id.replace('content_confirm_yes_', '')
                                            logger.info(f"WhatsApp user {phone_number} confirmed reading Day {day} content")
                                            
                                            if user:
                                                # Log the message with tag
                                                db_manager.log_message(
                                                    user=user,
                                                    direction='incoming',
                                                    raw_text=f"User confirmed reading Day {day} content",
                                                    sentiment='positive',
                                                    tags=['Christian Learning']
                                                )
                                                # Also add tag to user's profile
                                                db_manager.add_user_tag(phone_number, 'Christian Learning')
                                            
                                            # Send positive feedback
                                            from models import Bot
                                            bot = Bot.query.get(bot_id)
                                            
                                            if bot and bot.name and "indonesia" in bot.name.lower():
                                                feedback_msg = "✅ Terima kasih! Semoga pesan hari ini bermanfaat untuk perjalanan spiritualmu. 🙏"
                                            else:
                                                feedback_msg = "✅ Thank you! We hope today's message was meaningful for your spiritual journey. 🙏"
                                            
                                            bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                                            bot_whatsapp_service.send_message(phone_number, feedback_msg)
                                            
                                        elif button_id.startswith('content_confirm_no_'):
                                            day = button_id.replace('content_confirm_no_', '')
                                            logger.info(f"WhatsApp user {phone_number} hasn't read Day {day} content yet")
                                            
                                            from models import Bot
                                            bot = Bot.query.get(bot_id)
                                            
                                            if bot and bot.name and "indonesia" in bot.name.lower():
                                                reminder_msg = "Tidak apa-apa! Silakan baca kapan pun Anda siap. Kami di sini untuk Anda. 😊"
                                            else:
                                                reminder_msg = "That's okay! Read it whenever you're ready. We're here for you. 😊"
                                            
                                            bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                                            bot_whatsapp_service.send_message(phone_number, reminder_msg)
                                        
                                        # Skip normal processing for confirmation buttons
                                        continue
                                    
                                    if phone_number and message_text:
                                        # Get client IP for location data
                                        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
                                        if client_ip and ',' in client_ip:
                                            client_ip = client_ip.split(',')[0].strip()
                                        
                                        # Extract WhatsApp user data from contacts (if available)
                                        contacts_data = value.get('contacts', [])
                                        whatsapp_user_data = extract_whatsapp_user_data(message_data, contacts_data, client_ip)
                                        logger.info(f"🔥 DEBUG: Extracted WhatsApp user data: {whatsapp_user_data}")
                                        logger.info(f"🔥 DEBUG: Contacts array length: {len(contacts_data) if contacts_data else 0}")
                                        
                                        # Debug the extracted WhatsApp user data before processing
                                        logger.info(f"🔥 DEBUG: Final WhatsApp user data being passed: {whatsapp_user_data}")
                                        
                                        # Enhanced error handling: ensure message processing always continues
                                        try:
                                            process_incoming_message(phone_number, message_text, platform="whatsapp", 
                                                                   user_data=whatsapp_user_data, request_ip=client_ip, bot_id=bot_id)
                                            logger.info(f"✅ Successfully processed WhatsApp message from {phone_number}")
                                        except Exception as processing_error:
                                            logger.error(f"❌ Error processing WhatsApp message from {phone_number}: {processing_error}")
                                            # Send error response to user
                                            try:
                                                bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                                                bot_whatsapp_service.send_message(
                                                    phone_number, 
                                                    "Sorry, there was a temporary error. Please try sending your message again."
                                                )
                                            except:
                                                logger.error(f"❌ Failed to send error message to {phone_number}")
        
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

@app.route('/send_test_message', methods=['POST'])
def send_test_message():
    """Send a test WhatsApp message to verify system is working"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message', 'Test message from WhatsApp bot system')
        bot_id = data.get('bot_id', 1)
        
        if not phone_number:
            return jsonify({"error": "phone_number required"}), 400
        
        # Send message using WhatsApp service
        logger.info(f"🔥 TEST: Sending test message to {phone_number}")
        result, _ = send_message_to_platform(phone_number, "whatsapp", message, bot_id=bot_id)
        
        if result:
            return jsonify({"status": "success", "message": "Test message sent successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send test message"}), 500
            
    except Exception as e:
        logger.error(f"Error sending test message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/debug_whatsapp', methods=['GET'])
def debug_whatsapp():
    """Debug WhatsApp configuration and test API access"""
    try:
        access_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')
        phone_id = os.environ.get('WHATSAPP_PHONE_NUMBER_ID')
        
        debug_info = {
            "access_token_length": len(access_token) if access_token else 0,
            "phone_number_id": phone_id,
            "has_token": bool(access_token),
            "has_phone_id": bool(phone_id)
        }
        
        return jsonify(debug_info), 200
        
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        return jsonify({"error": str(e)}), 500

# Global cache for recent messages to handle concurrent processing
_recent_messages_cache = {}

# Global cache for processed WhatsApp webhook message IDs
_processed_webhook_ids = {}

def _is_duplicate_message(phone_number: str, message_text: str, window_seconds: int = 60) -> bool:
    """Enhanced duplicate detection with memory cache for concurrent processing"""
    try:
        from datetime import datetime, timedelta
        import hashlib
        
        # Create a unique key for this message
        message_key = f"{phone_number}:{hashlib.md5(message_text.encode()).hexdigest()}"
        current_time = datetime.now()
        
        # Check memory cache first for immediate duplicates (handles concurrent processing)
        if message_key in _recent_messages_cache:
            cached_time = _recent_messages_cache[message_key]
            time_diff = (current_time - cached_time).total_seconds()
            if time_diff < window_seconds:
                logger.warning(f"🚫 CONCURRENT duplicate detected from {phone_number}: '{message_text[:30]}...' (cached {time_diff:.1f}s ago)")
                return True
        
        # Add current message to cache
        _recent_messages_cache[message_key] = current_time
        
        # Clean up old cache entries (keep cache small)
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        keys_to_remove = [k for k, v in _recent_messages_cache.items() if v < cutoff_time]
        for key in keys_to_remove:
            del _recent_messages_cache[key]
        
        # Check database for historical duplicates
        user = db_manager.get_user_by_phone(phone_number)
        if not user:
            return False
            
        # Query recent incoming messages in database
        from models import db
        recent_messages = db.session.execute(
            text("""SELECT raw_text, timestamp FROM message_logs 
               WHERE user_id = :user_id 
               AND direction = 'incoming' 
               AND timestamp > :cutoff_time 
               AND raw_text = :message_text
               ORDER BY timestamp DESC LIMIT 1"""),
            {
                'user_id': user.id,
                'cutoff_time': cutoff_time,
                'message_text': message_text
            }
        ).fetchone()
        
        if recent_messages:
            time_diff = (current_time - recent_messages[1]).total_seconds()
            logger.warning(f"🚫 DATABASE duplicate detected from {phone_number}: '{message_text[:30]}...' ({time_diff:.1f}s ago)")
            return True
            
        return False
        
    except Exception as e:
        logger.error(f"Error checking for duplicate message: {e}")
        return False  # Default to processing the message if check fails

def _is_duplicate_webhook(whatsapp_message_id: str, window_seconds: int = 300) -> bool:
    """Check if this WhatsApp message ID has already been processed"""
    try:
        from datetime import datetime, timedelta
        
        current_time = datetime.now()
        
        # Check if we've already processed this webhook message ID
        if whatsapp_message_id in _processed_webhook_ids:
            processed_time = _processed_webhook_ids[whatsapp_message_id]
            time_diff = (current_time - processed_time).total_seconds()
            if time_diff < window_seconds:
                logger.warning(f"🚫 WEBHOOK duplicate detected: {whatsapp_message_id} (processed {time_diff:.1f}s ago)")
                return True
        
        # Add this message ID to processed cache
        _processed_webhook_ids[whatsapp_message_id] = current_time
        
        # Clean up old webhook IDs (keep cache manageable)
        cutoff_time = current_time - timedelta(seconds=window_seconds)
        ids_to_remove = [wid for wid, processed_time in _processed_webhook_ids.items() if processed_time < cutoff_time]
        for wid in ids_to_remove:
            del _processed_webhook_ids[wid]
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking for duplicate webhook: {e}")
        return False  # Default to processing if check fails

def process_voice_message(phone_number: str, audio_bytes: bytes, platform: str = "whatsapp", 
                         user_data: Dict = None, request_ip: str = None, bot_id: int = 1):
    """Process incoming voice message by transcribing and routing to text handler"""
    try:
        logger.info(f"🎤 Processing voice message from {phone_number} ({platform})")
        
        # Get bot's language for accurate transcription
        from models import Bot
        from language_mapper import get_language_code
        
        bot = Bot.query.get(bot_id)
        bot_language = bot.language if bot else "English"
        language_code = get_language_code(bot_language)
        
        logger.info(f"🎤 Using language '{bot_language}' (code: {language_code}) for voice transcription")
        
        # Initialize voice services
        speech_to_text = SpeechToTextService()
        logger.info(f"🎤 STT Service initialized - Simulation mode: {speech_to_text.simulate_mode}")
        
        # Transcribe audio to text with bot's language
        transcribed_text = speech_to_text.transcribe_audio(audio_bytes, language_code=language_code)
        logger.info(f"🎤 Transcription result: {transcribed_text[:100] if transcribed_text else 'None'}...")
        
        if transcribed_text:
            logger.info(f"🎤 Transcribed: {transcribed_text}")
            # Process as text message through existing pipeline
            process_incoming_message(phone_number, transcribed_text, platform=platform, 
                                   user_data=user_data, request_ip=request_ip, bot_id=bot_id,
                                   is_voice_message=True)
        else:
            logger.error(f"Failed to transcribe voice message from {phone_number}")
            # Send error message
            send_message_to_platform(phone_number, platform, 
                "Sorry, I couldn't understand your voice message. Please try again or send a text message.", 
                bot_id=bot_id)
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")

def process_incoming_message(phone_number: str, message_text: str, platform: str = "whatsapp", user_data: dict = None, request_ip: str = None, bot_id: int = 1, is_voice_message: bool = False):
    """Process incoming message from user"""
    try:
        logger.info(f"Processing message from {phone_number}: {message_text}")
        
        # Enhanced phone number normalization using centralized utility
        if platform == "whatsapp":
            from phone_number_utils import normalize_phone_number
            original_number = phone_number
            phone_number = normalize_phone_number(phone_number, platform)
            logger.info(f"🔥 DEBUG: Normalized phone number from '{original_number}' to '{phone_number}'")
        elif platform == "telegram" and phone_number.startswith('+tg_'):
            # Remove incorrect '+' prefix from Telegram IDs
            phone_number = phone_number[1:]
        
        # **DUPLICATE MESSAGE PREVENTION** - Check for recent identical messages
        if _is_duplicate_message(phone_number, message_text):
            logger.info(f"⏭️ Ignoring duplicate message from {phone_number}: '{message_text[:30]}...'")
            return
        
        message_lower = message_text.lower().strip()
        
        # For WhatsApp: Check if user is new and send welcome message for any first message
        if platform == "whatsapp":
            existing_user = db_manager.get_user_by_phone(phone_number)
            if not existing_user:
                logger.info(f"New WhatsApp user {phone_number}, triggering welcome flow for first message: '{message_text}'")
                handle_whatsapp_first_message(phone_number, platform, user_data, request_ip, bot_id)
                return
            elif existing_user.current_day == 1 and not any(cmd in message_lower for cmd in ['start', 'stop', 'help', 'human']):
                # Day 1 users already received content, so they should get contextual responses too
                logger.info(f"Day 1 user {phone_number} sending message about Day 1 content, using contextual AI response")
                handle_contextual_conversation(phone_number, message_text, platform, bot_id, is_voice_message)
                return
            else:
                # Update user with any new WhatsApp data if available
                if user_data and (user_data.get('whatsapp_formatted_name') or user_data.get('whatsapp_contact_name')):
                    logger.info(f"Updating existing user {phone_number} with new WhatsApp data")
                    db_manager.update_user(phone_number, **user_data)
        
        # Handle commands - support both slash commands (Telegram) and keyword commands (WhatsApp)
        if message_lower in ['start', '/start'] or 'start' in message_lower:
            handle_start_command(phone_number, platform, user_data, request_ip, bot_id)
            return
        
        elif message_lower in ['stop', '/stop'] or 'stop' in message_lower:
            handle_stop_command(phone_number, platform, bot_id)
            return
        
        elif message_lower in ['help', '/help'] or 'help' in message_lower:
            handle_help_command(phone_number, platform, bot_id)
            return
        
        elif message_lower in ['human', '/human'] or 'human' in message_lower:
            handle_human_command(phone_number, platform, bot_id)
            return
        
        # Check for human handoff triggers
        if any(keyword in message_lower for keyword in HUMAN_HANDOFF_KEYWORDS):
            handle_human_handoff(phone_number, message_text, platform, bot_id)
            return
        
        # Enhanced contextual routing based on user's journey stage
        user = db_manager.get_user_by_phone(phone_number)
        if user:
            # Check if user has completed their journey
            from models import Bot
            bot = Bot.query.get(user.bot_id)
            journey_duration = bot.journey_duration_days if bot else 30
            
            if user.current_day > journey_duration:
                # Users who have completed their journey get specialized journey completed handling
                logger.info(f"User {phone_number} (Day {user.current_day}/{journey_duration}) completed journey, using journey completed handler")
                handle_journey_completed_conversation(phone_number, message_text, platform, bot_id, is_voice_message)
            elif user.current_day > 1:
                # Users beyond Day 1 should always get contextual responses based on their current content
                logger.info(f"User {phone_number} (Day {user.current_day}) sending message, providing contextual response based on current journey")
                handle_contextual_conversation(phone_number, message_text, platform, bot_id, is_voice_message)
            else:
                # Day 1 users get general conversation
                logger.info(f"User {phone_number} (Day 1) routing to general conversation")
                handle_general_conversation(phone_number, message_text, platform, bot_id, is_voice_message)
        else:
            # New users get general conversation
            logger.info(f"User {phone_number} (new) routing to general conversation")
            handle_general_conversation(phone_number, message_text, platform, bot_id, is_voice_message)
        
    except Exception as e:
        logger.error(f"Error processing message from {phone_number}: {e}")
        # Send bot-specific error message to user
        from models import Bot
        bot = Bot.query.get(bot_id) if bot_id else None
        if bot and bot.name and "indonesia" in bot.name.lower():
            error_message = "Maaf, ada masalah saat memproses pesan Anda. Silakan coba lagi atau ketik HELP untuk bantuan."
        else:
            error_message = "Sorry, there was an error processing your message. Please try again or type HELP for assistance."
        
        send_message_to_platform(phone_number, platform, error_message, bot_id=bot_id)

def send_message_with_buttons(phone_number: str, platform: str, message: str, bot_id: int = 1) -> bool:
    """Send message with Yes/No buttons for human connection choice"""
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
                
                # Send message with inline keyboard buttons
                from models import Bot
                bot = Bot.query.get(bot_id)
                
                if bot and bot.name and "indonesia" in bot.name.lower():
                    buttons = [
                        [{"text": "✅ Ya, hubungkan dengan tim", "callback_data": "human_yes"}],
                        [{"text": "🤖 Tidak, lanjutkan dengan bot", "callback_data": "human_no"}]
                    ]
                else:
                    buttons = [
                        [{"text": "✅ Yes, connect with team", "callback_data": "human_yes"}],
                        [{"text": "🤖 No, continue with bot", "callback_data": "human_no"}]
                    ]
                
                return bot_service.send_message_with_buttons(chat_id, message, buttons)
                
        elif platform == "whatsapp":
            # Get bot-specific WhatsApp service
            bot_service = get_whatsapp_service_for_bot(bot_id)
            if not bot_service:
                logger.error(f"No WhatsApp service available for bot_id {bot_id}")
                return False
            
            # WhatsApp interactive buttons
            from models import Bot
            bot = Bot.query.get(bot_id)
            
            if bot and bot.name and "indonesia" in bot.name.lower():
                buttons = [
                    {"id": "human_yes", "title": "Ya, hubungkan tim"},
                    {"id": "human_no", "title": "Lanjut dengan bot"}
                ]
            else:
                buttons = [
                    {"id": "human_yes", "title": "Yes, connect team"},
                    {"id": "human_no", "title": "Continue with bot"}
                ]
            
            return bot_service.send_interactive_buttons(phone_number, message, buttons)
            
    except Exception as e:
        logger.error(f"Error sending message with buttons to {phone_number}: {e}")
        # Fallback to regular message
        success, _ = send_message_to_platform(phone_number, platform, message + "\n\nReply 'YES' for human team or 'NO' to continue with bot.", bot_id=bot_id)
        return success
    
    return False

def send_message_to_platform(phone_number: str, platform: str, message: str, 
                           with_quick_replies: bool = False, copy_text: str = "", 
                           copy_label: str = "Copy Text", bot_id: int = 1, retry_count: int = 3,
                           send_as_voice: bool = False) -> tuple[bool, bool]:
    """Send message to the appropriate platform with enhanced reliability and retry logic
    
    Returns:
        tuple[bool, bool]: (success: bool, voice_sent: bool)
            - success: True if message was sent successfully (either as voice or text), False otherwise
            - voice_sent: True if message was sent as voice, False if sent as text
        
    Note: When send_as_voice=True, the function attempts to send voice first. If that fails,
    it falls back to text. The is_voice_message flag should be set based on what was actually sent.
    """
    
    # Track whether voice was actually sent (for logging purposes)
    voice_sent = False
    
    # Voice message handling
    if send_as_voice:
        try:
            logger.info(f"🎙️ Generating voice response for {phone_number} on {platform}")
            
            # Get bot configuration for language
            from models import Bot
            from language_mapper import get_language_code
            
            bot = Bot.query.get(bot_id)
            bot_language = bot.language if bot else "English"
            language_code = get_language_code(bot_language)
            
            logger.info(f"🔊 Using language '{bot_language}' (code: {language_code}) for voice synthesis")
            
            # Initialize TTS service
            tts_service = TextToSpeechService()
            logger.info(f"🔊 TTS Service initialized - Simulation mode: {tts_service.simulate_mode}")
            
            # Determine audio format based on platform
            audio_format = "OGG_OPUS" if platform == "telegram" else "MP3"
            file_extension = "ogg" if platform == "telegram" else "mp3"
            
            # Generate speech audio
            audio_bytes = tts_service.synthesize_speech(
                text=message,
                language_code=language_code,
                voice_gender="NEUTRAL",
                audio_format=audio_format
            )
            
            logger.info(f"🔊 TTS audio generated: {len(audio_bytes) if audio_bytes else 0} bytes")
            
            if audio_bytes:
                temp_file = None
                try:
                    # Generate unique filename
                    temp_file = f"/tmp/voice_{uuid.uuid4()}.{file_extension}"
                    
                    # Save audio to temporary file
                    with open(temp_file, 'wb') as f:
                        f.write(audio_bytes)
                    
                    logger.info(f"🎙️ Voice file saved: {temp_file} ({len(audio_bytes)} bytes)")
                    
                    # Send voice based on platform
                    if platform == "telegram":
                        if phone_number.startswith("tg_"):
                            chat_id = phone_number[3:]
                            bot_service = get_telegram_service_for_bot(bot_id)
                            if bot_service:
                                success = bot_service.send_voice(chat_id, temp_file)
                                if success:
                                    logger.info(f"✅ Voice message sent successfully to Telegram {chat_id}")
                                    voice_sent = True
                                    return (True, True)
                    else:
                        # WhatsApp needs a public URL - save to static/uploads/audio
                        static_audio_dir = "static/uploads/audio"
                        os.makedirs(static_audio_dir, exist_ok=True)
                        
                        static_filename = f"voice_{uuid.uuid4()}.{file_extension}"
                        static_file_path = os.path.join(static_audio_dir, static_filename)
                        
                        # Copy to static directory
                        import shutil
                        shutil.copy(temp_file, static_file_path)
                        
                        # Construct public URL
                        base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                        if not base_url.startswith('http'):
                            base_url = f"https://{base_url}"
                        audio_url = f"{base_url}/static/uploads/audio/{static_filename}"
                        
                        logger.info(f"🎙️ WhatsApp audio URL: {audio_url}")
                        
                        bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                        if bot_whatsapp_service:
                            success = bot_whatsapp_service.send_audio(phone_number, audio_url)
                            if success:
                                logger.info(f"✅ Voice message sent successfully to WhatsApp {phone_number}")
                                voice_sent = True
                                return (True, True)
                    
                finally:
                    # Clean up temporary file
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                            logger.info(f"🗑️ Cleaned up temp file: {temp_file}")
                        except Exception as cleanup_error:
                            logger.error(f"Error cleaning up temp file: {cleanup_error}")
            
            # If voice sending failed, fall back to text
            logger.warning(f"Voice generation failed, falling back to text message for {phone_number}")
            
        except Exception as voice_error:
            logger.error(f"Voice generation error: {voice_error}, falling back to text message")
    
    # Text message handling (original logic)
    success = False
    attempt = 0
    last_error = None
    
    while not success and attempt < retry_count:
        try:
            attempt += 1
            
            if platform == "telegram":
                # Extract chat_id from tg_ prefixed phone number
                if phone_number.startswith("tg_"):
                    chat_id = phone_number[3:]  # Remove 'tg_' prefix
                    
                    # Get bot-specific Telegram service with validation
                    bot_service = get_telegram_service_for_bot(bot_id)
                    if not bot_service:
                        logger.error(f"No Telegram service available for bot_id {bot_id}")
                        return (False, False)
                    
                    # Enhanced Telegram messaging with 2025 features
                    if copy_text and copy_label:
                        # Send message with copy button for Bible verses or inspirational content
                        success = bot_service.send_copy_text_message(chat_id, message, copy_text, copy_label)
                    elif with_quick_replies:
                        # Send message with quick reply buttons for common responses
                        quick_replies = [
                            "Tell me more", "I have a question", 
                            "This is helpful", "I need time to think"
                        ]
                        success = bot_service.send_quick_reply_message(chat_id, message, quick_replies)
                    else:
                        success = bot_service.send_message(chat_id, message)
                else:
                    logger.error(f"Invalid Telegram chat_id format: {phone_number}")
                    return (False, False)
            else:
                # Default to WhatsApp - use bot-specific service with validation
                bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                if not bot_whatsapp_service:
                    logger.error(f"No WhatsApp service available for bot_id {bot_id}")
                    return (False, False)
                    
                success = bot_whatsapp_service.send_message(phone_number, message)
            
            if success:
                if attempt > 1:
                    logger.info(f"Message sent successfully on attempt {attempt} to {phone_number}")
                break
                
        except Exception as e:
            last_error = e
            logger.error(f"Error sending message to {platform} (attempt {attempt}/{retry_count}): {e}")
            
            if attempt < retry_count:
                # Brief delay before retry
                import time
                time.sleep(min(attempt * 0.5, 2.0))  # Exponential backoff, max 2 seconds
    
    if not success and last_error:
        logger.error(f"Failed to send message after {retry_count} attempts. Last error: {last_error}")
        
        # Ultimate fallback - try with a simplified message
        if len(message) > 100:
            try:
                simple_msg = "Message received. Reply when ready." if bot_id != 2 else "Pesan diterima. Balas kapan siap."
                logger.info(f"Attempting fallback with simplified message to {phone_number}")
                if platform == "telegram" and phone_number.startswith("tg_"):
                    chat_id = phone_number[3:]
                    bot_service = get_telegram_service_for_bot(bot_id)
                    if bot_service:
                        success = bot_service.send_message(chat_id, simple_msg)
                else:
                    bot_whatsapp_service = get_whatsapp_service_for_bot(bot_id)
                    if bot_whatsapp_service:
                        success = bot_whatsapp_service.send_message(phone_number, simple_msg)
                
                if success:
                    logger.info(f"Fallback message sent successfully to {phone_number}")
            except Exception as fallback_error:
                logger.error(f"Even fallback message failed: {fallback_error}")
    
    return success, voice_sent



def extract_whatsapp_user_data(message_data: dict, contacts_data: list = None, request_ip: str = None) -> dict:
    """Extract enhanced user data from WhatsApp message payload"""
    enhanced_data = {}
    
    if message_data:
        phone_number = message_data.get('from', '')
        enhanced_data['whatsapp_phone'] = phone_number
        
        # Try to get contact name from contacts array (if available in webhook)
        contact_name = ''
        formatted_name = ''
        if contacts_data:
            for contact in contacts_data:
                if contact.get('wa_id') == phone_number:
                    profile = contact.get('profile', {})
                    contact_name = profile.get('name', '')
                    formatted_name = contact.get('formatted_name', '')
                    logger.info(f"🔥 DEBUG: WhatsApp contact data - wa_id: {contact.get('wa_id')}, profile name: '{contact_name}', formatted_name: '{formatted_name}'")
                    break
        
        # Prefer formatted_name over profile name, fallback to default
        display_name = formatted_name or contact_name or f'WhatsApp User {phone_number[-4:]}'
        enhanced_data['name'] = display_name
        enhanced_data['whatsapp_contact_name'] = contact_name
        enhanced_data['whatsapp_formatted_name'] = formatted_name
        
    if request_ip:
        enhanced_data['ip_address'] = request_ip
        # Simple location stub - can be enhanced with IP geolocation service
        enhanced_data['location_data'] = {'country': 'Unknown', 'region': 'Unknown', 'city': 'Unknown'}
    
    return enhanced_data

def extract_telegram_user_data(user_data: dict, request_ip: str = None) -> dict:
    """Extract enhanced user data from Telegram"""
    enhanced_data = {}
    
    if user_data:
        # Extract Telegram specific fields
        enhanced_data['telegram_user_id'] = str(user_data.get('id', ''))
        enhanced_data['telegram_username'] = user_data.get('username', '')
        enhanced_data['telegram_first_name'] = user_data.get('first_name', '')
        enhanced_data['telegram_last_name'] = user_data.get('last_name', '')
        enhanced_data['telegram_language_code'] = user_data.get('language_code', '')
        enhanced_data['telegram_is_premium'] = user_data.get('is_premium', False)
        
        # Create display name from available data
        name_parts = []
        if enhanced_data['telegram_first_name']:
            name_parts.append(enhanced_data['telegram_first_name'])
        if enhanced_data['telegram_last_name']:
            name_parts.append(enhanced_data['telegram_last_name'])
        if not name_parts and enhanced_data['telegram_username']:
            name_parts.append(f"@{enhanced_data['telegram_username']}")
        
        enhanced_data['name'] = ' '.join(name_parts) if name_parts else 'Telegram User'
        
    if request_ip:
        enhanced_data['ip_address'] = request_ip
        enhanced_data['location_data'] = get_ip_location_data(request_ip)
    
    return enhanced_data

def handle_start_command(phone_number: str, platform: str = "whatsapp", user_data: dict = None, request_ip: str = None, bot_id: int = 1):
    """Handle START command - onboard new user"""
    try:
        logger.info(f"Processing START command for {phone_number} on {platform}")
        # Check if user already exists
        existing_user = db_manager.get_user_by_phone(phone_number)
        
        if existing_user and existing_user.status in ['active', 'inactive']:
                    
            # Allow restart - reset to Day 1 and update with enhanced user data
            # Reset join_date to current time to restart scheduler tracking
            update_kwargs = {'current_day': 1, 'join_date': datetime.now(), 'bot_id': bot_id, 'status': 'active'}
            if user_data and platform == "telegram":
                enhanced_data = extract_telegram_user_data(user_data, request_ip)
                update_kwargs.update(enhanced_data)
            elif user_data and platform == "whatsapp":
                # Use WhatsApp user data
                update_kwargs.update(user_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username') or user_data.get('name')
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
            
            # Check if greeting has media and send appropriately
            media_sent = False
            if greeting and greeting.media_type and greeting.media_type != 'text':
                # Construct media URL from filename with validation
                media_url = None
                media_type = greeting.media_type
                
                if media_type == 'video' and greeting.video_filename:
                    file_path = f"static/uploads/videos/{greeting.video_filename}"
                    if os.path.exists(file_path):
                        base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                        if not base_url.startswith('http'):
                            base_url = f"https://{base_url}"
                        media_url = f"{base_url}/static/uploads/videos/{greeting.video_filename}"
                        logger.info(f"✅ RESTART: Welcome video validated: {file_path}")
                    else:
                        logger.error(f"❌ RESTART: Welcome video not found: {file_path}")
                elif media_type == 'image' and greeting.image_filename:
                    file_path = f"static/uploads/images/{greeting.image_filename}"
                    if os.path.exists(file_path):
                        base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                        if not base_url.startswith('http'):
                            base_url = f"https://{base_url}"
                        media_url = f"{base_url}/static/uploads/images/{greeting.image_filename}"
                        logger.info(f"✅ RESTART: Welcome image validated: {file_path}")
                    else:
                        logger.error(f"❌ RESTART: Welcome image not found: {file_path}")
                elif media_type == 'audio' and greeting.audio_filename:
                    file_path = f"static/uploads/audio/{greeting.audio_filename}"
                    if os.path.exists(file_path):
                        base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                        if not base_url.startswith('http'):
                            base_url = f"https://{base_url}"
                        media_url = f"{base_url}/static/uploads/audio/{greeting.audio_filename}"
                        logger.info(f"✅ RESTART: Welcome audio validated: {file_path}")
                    else:
                        logger.error(f"❌ RESTART: Welcome audio not found: {file_path}")
                
                # Send media with restart message as caption (only for WhatsApp)
                if media_url and platform == "whatsapp":
                    whatsapp_svc = get_whatsapp_service_for_bot(bot_id)
                    if media_type == 'video':
                        media_sent = whatsapp_svc.send_video(phone_number, media_url, caption=restart_message)
                        logger.info(f"RESTART: WhatsApp video sent with caption to {phone_number}")
                    elif media_type == 'image':
                        media_sent = whatsapp_svc.send_media_message(phone_number, 'image', media_url, caption=restart_message)
                        logger.info(f"RESTART: WhatsApp image sent with caption to {phone_number}")
                    elif media_type == 'audio':
                        # Audio doesn't support caption in WhatsApp, send separately
                        whatsapp_svc.send_media_message(phone_number, 'audio', media_url)
                        send_message_to_platform(phone_number, platform, restart_message, bot_id=bot_id)
                        media_sent = True
                        logger.info(f"RESTART: WhatsApp audio sent (caption sent separately) to {phone_number}")
            
            # If no media was sent, send text-only restart message
            if not media_sent:
                logger.info(f"RESTART: Sending restart message to {phone_number}: {restart_message[:100]}...")
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
            
            time.sleep(10)  # 10 second delay before Day 1 content
            
            # Send Day 1 content directly (bypass scheduler for immediate delivery)
            # **FIX: Use scheduler's delivery method to properly handle media (images/videos)**
            try:
                logger.info(f"Attempting direct Day 1 content delivery for restart user {phone_number}")
                user = db_manager.get_user_by_phone(phone_number)
                if user and user.bot_id:
                    # Get Day 1 content for this bot
                    content = db_manager.get_content_by_day(1, bot_id=user.bot_id)
                    if content:
                        # Use scheduler's delivery method which handles media properly
                        content_dict = content.to_dict()
                        success = scheduler._deliver_content_with_reflection(phone_number, content_dict)
                        
                        if success:
                            logger.info(f"✅ Day 1 content (with media) delivered successfully to restart user {phone_number}")
                            # Advance user to Day 2
                            db_manager.update_user(phone_number, current_day=2)
                            # Note: Message logging is handled inside _deliver_content_with_reflection
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
            elif user_data and platform == "whatsapp":
                # Use WhatsApp user data
                update_kwargs.update(user_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username') or user_data.get('name')
                if user_name:
                    update_kwargs['name'] = user_name
            db_manager.update_user(phone_number, **update_kwargs)
        else:
            create_kwargs = {'status': 'active', 'current_day': 1, 'tags': [], 'bot_id': bot_id}
            if user_data and platform == "telegram":
                enhanced_data = extract_telegram_user_data(user_data, request_ip)
                create_kwargs.update(enhanced_data)
            elif user_data and platform == "whatsapp":
                # Use WhatsApp user data
                create_kwargs.update(user_data)
            elif user_data:
                user_name = user_data.get('first_name') or user_data.get('username') or user_data.get('name')
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
            # Generate welcome message using bot-specific AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.ai_prompt:
                try:
                    welcome_message = gemini_service.generate_bot_response(
                        user_message="User just started their spiritual journey. Please welcome them and explain what they can expect.",
                        ai_prompt=bot.ai_prompt,
                        content_context=None,
                        bot_id=bot_id
                    )
                except:
                    # Fallback to default message if AI generation fails
                    welcome_message = (f"Welcome to your Faith Journey! {platform_emoji}\n\n"
                                      "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                                      "After each piece of content, I'll ask you a simple reflection question.\n\n"
                                      "Available Commands:\n"
                                      f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                                      f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                                      f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                                      f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                                      "Day 1 content will arrive in a few seconds!")
            else:
                # No bot found, use default
                welcome_message = (f"Welcome to your Faith Journey! {platform_emoji}\n\n"
                                  "You'll receive daily content for the next 10 days (every 10 minutes for testing). "
                                  "After each piece of content, I'll ask you a simple reflection question.\n\n"
                                  "Available Commands:\n"
                                  f"• {'/start' if platform == 'telegram' else 'START'} - Begin or restart journey\n"
                                  f"• {'/stop' if platform == 'telegram' else 'STOP'} - Unsubscribe from messages\n"
                                  f"• {'/help' if platform == 'telegram' else 'HELP'} - Show help message\n"
                                  f"• {'/human' if platform == 'telegram' else 'HUMAN'} - Chat directly with a human\n\n"
                                  "Day 1 content will arrive in a few seconds!")
        
        # Check if greeting has media and send appropriately
        media_sent = False
        if greeting and greeting.media_type and greeting.media_type != 'text':
            # Construct media URL from filename with validation
            media_url = None
            media_type = greeting.media_type
            
            if media_type == 'video' and greeting.video_filename:
                file_path = f"static/uploads/videos/{greeting.video_filename}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/videos/{greeting.video_filename}"
                    logger.info(f"✅ Welcome video validated: {file_path}")
                else:
                    logger.error(f"❌ Welcome video not found: {file_path}")
            elif media_type == 'image' and greeting.image_filename:
                file_path = f"static/uploads/images/{greeting.image_filename}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/images/{greeting.image_filename}"
                    logger.info(f"✅ Welcome image validated: {file_path}")
                else:
                    logger.error(f"❌ Welcome image not found: {file_path}")
            elif media_type == 'audio' and greeting.audio_filename:
                file_path = f"static/uploads/audio/{greeting.audio_filename}"
                if os.path.exists(file_path):
                    base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                    if not base_url.startswith('http'):
                        base_url = f"https://{base_url}"
                    media_url = f"{base_url}/static/uploads/audio/{greeting.audio_filename}"
                    logger.info(f"✅ Welcome audio validated: {file_path}")
                else:
                    logger.error(f"❌ Welcome audio not found: {file_path}")
            
            # Send media with welcome message as caption (only for WhatsApp)
            if media_url and platform == "whatsapp":
                whatsapp_svc = get_whatsapp_service_for_bot(bot_id)
                if media_type == 'video':
                    media_sent = whatsapp_svc.send_video(phone_number, media_url, caption=welcome_message)
                    logger.info(f"WhatsApp welcome video sent with caption to {phone_number}")
                elif media_type == 'image':
                    media_sent = whatsapp_svc.send_media_message(phone_number, 'image', media_url, caption=welcome_message)
                    logger.info(f"WhatsApp welcome image sent with caption to {phone_number}")
                elif media_type == 'audio':
                    # Audio doesn't support caption in WhatsApp, send separately
                    whatsapp_svc.send_media_message(phone_number, 'audio', media_url)
                    send_message_to_platform(phone_number, platform, welcome_message, bot_id=bot_id)
                    media_sent = True
                    logger.info(f"WhatsApp welcome audio sent (caption sent separately) to {phone_number}")
        
        # If no media was sent, send text-only welcome message
        if not media_sent:
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
        
        time.sleep(10)  # 10 second delay before Day 1 content
        
        # Send Day 1 content directly (bypass scheduler for immediate delivery)
        # **FIX: Use scheduler's delivery method to properly handle media (images/videos)**
        try:
            logger.info(f"🔥 DEBUG: Attempting direct Day 1 content delivery for {phone_number}")
            user = db_manager.get_user_by_phone(phone_number)
            logger.info(f"🔥 DEBUG: User found: {user.phone_number if user else 'None'}, bot_id: {user.bot_id if user else 'None'}")
            if user and user.bot_id:
                # Get Day 1 content for this bot
                content = db_manager.get_content_by_day(1, bot_id=user.bot_id)
                logger.info(f"🔥 DEBUG: Content found: {content.title if content else 'None'}")
                if content:
                    # Use scheduler's delivery method which handles media properly
                    logger.info(f"🔥 DEBUG: Using scheduler delivery method for media support")
                    content_dict = content.to_dict()
                    success = scheduler._deliver_content_with_reflection(phone_number, content_dict)
                    logger.info(f"🔥 DEBUG: Scheduler delivery result: {success}")
                    
                    if success:
                        logger.info(f"✅ Day 1 content (with media) delivered successfully to {phone_number}")
                        # Advance user to Day 2
                        db_manager.update_user(phone_number, current_day=2)
                        # Note: Message logging is handled inside _deliver_content_with_reflection
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
        logger.info(f"🔥 DEBUG: Processing STOP command for {phone_number} on {platform} with bot_id {bot_id}")
        user = db_manager.get_user_by_phone(phone_number)
        if user:
            db_manager.update_user(phone_number, status='inactive')
            
            # Get bot configuration for custom stop message
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.stop_message:
                message = bot.stop_message
            else:
                # Generate stop message using bot-specific AI prompt
                if bot and bot.ai_prompt:
                    try:
                        message = gemini_service.generate_bot_response(
                            user_message="User wants to stop receiving messages. Please acknowledge their request and let them know they can restart anytime.",
                            ai_prompt=bot.ai_prompt,
                            content_context=None,
                            bot_id=bot_id
                        )
                    except:
                        # Fallback message with Indonesian support for Bot 2
                        if bot_id == 2:
                            message = ("Kamu telah berhenti dari perjalanan spiritual Bang Kris. "
                                      "Kalau mau mulai lagi, tinggal kirim START kapan aja. "
                                      "Damai sejahtera bersamamu. 🙏")
                        else:
                            message = ("You have been unsubscribed from the Faith Journey. "
                                      "If you'd like to restart your journey, simply send START anytime. "
                                      "Peace be with you. 🙏")
                else:
                    # No bot found, use generic
                    message = ("You have been unsubscribed from the Faith Journey. "
                              "If you'd like to restart your journey, simply send START anytime. "
                              "Peace be with you. 🙏")
        else:
            # Generate message for non-subscribed user using bot-specific AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.ai_prompt:
                try:
                    message = gemini_service.generate_bot_response(
                        user_message="User wants to stop but they are not subscribed. Please let them know they can start their journey anytime.",
                        ai_prompt=bot.ai_prompt,
                        content_context=None,
                        bot_id=bot_id
                    )
                except:
                    if bot_id == 2:
                        message = "Kamu belum berlangganan perjalanan apapun. Kirim START untuk mulai perjalanan spiritual kamu."
                    else:
                        message = "You weren't subscribed to any journey. Send START to begin your faith journey."
            else:
                message = "You weren't subscribed to any journey. Send START to begin your faith journey."
        
        logger.info(f"🔥 DEBUG: Sending STOP response: {message}")
        success, _ = send_message_to_platform(phone_number, platform, message, bot_id=bot_id)
        logger.info(f"🔥 DEBUG: STOP message send result: {success}")
        
        # Log the stop request
        if user:
            db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=f'/stop' if platform == 'telegram' else 'STOP',
                sentiment='neutral',
                tags=['STOP']
            )
        
        # Log the outgoing stop response if successful
        if success and user:
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=message,
                sentiment='neutral',
                tags=['STOP_RESPONSE'],
                confidence=1.0
            )
            logger.info(f"✅ STOP command processed successfully for {phone_number}")
        else:
            logger.error(f"❌ STOP command failed to send for {phone_number}")
        
        logger.info(f"User {phone_number} unsubscribed")
        
    except Exception as e:
        logger.error(f"Error handling STOP command for {phone_number}: {e}")
        import traceback
        logger.error(f"STOP command traceback: {traceback.format_exc()}")
        
        # Emergency fallback - send basic confirmation
        try:
            emergency_msg = "Request processed." if bot_id != 2 else "Permintaan diproses."
            send_message_to_platform(phone_number, platform, emergency_msg, bot_id=bot_id)
        except Exception as fallback_error:
            logger.error(f"Emergency fallback also failed for {phone_number}: {fallback_error}")

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
        from models import Bot
        bot = Bot.query.get(bot_id)
        if bot and bot.help_message:
            help_message = bot.help_message
        else:
            # Generate help message using bot-specific AI prompt
            if bot and bot.ai_prompt:
                try:
                    help_message = gemini_service.generate_bot_response(
                        user_message="User needs help. Please explain what you offer and what commands are available.",
                        ai_prompt=bot.ai_prompt,
                        content_context=None,
                        bot_id=bot_id
                    )
                except:
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
            else:
                # No bot found, use generic
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
        success, _ = send_message_to_platform(phone_number, platform, help_message, bot_id=bot_id)
        logger.info(f"🔥 DEBUG: Help message send result: {success}")
        
        # Log the help request  
        if user:
            db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=f'/help' if platform == 'telegram' else 'HELP',
                sentiment='neutral',
                tags=['HELP']
            )
        
        if success and user:
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
        import traceback
        logger.error(f"HELP command traceback: {traceback.format_exc()}")
        
        # Emergency fallback - send basic help
        try:
            emergency_msg = "Available commands: START, STOP, HELP, HUMAN" if bot_id != 2 else "Perintah: START, STOP, HELP, HUMAN"
            send_message_to_platform(phone_number, platform, emergency_msg, bot_id=bot_id)
        except Exception as fallback_error:
            logger.error(f"Help emergency fallback failed for {phone_number}: {fallback_error}")

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
        if user:
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
        from models import Bot
        bot = Bot.query.get(bot_id)
        if bot and bot.human_message:
            response_message = bot.human_message
        else:
            # Generate human handoff message using bot-specific AI prompt
            if bot and bot.ai_prompt:
                try:
                    response_message = gemini_service.generate_bot_response(
                        user_message="User wants to speak with a human. Please acknowledge their request and let them know a team member will help them.",
                        ai_prompt=bot.ai_prompt,
                        content_context=None,
                        bot_id=bot_id
                    )
                except:
                    # Fallback message in Indonesian for Bot 2
                    if bot_id == 2:
                        response_message = ("🤝 Permintaan Chat dengan Manusia\n\n"
                                          "Terima kasih sudah menghubungi! Tim kami akan segera terhubung dengan Anda. "
                                          "Percakapan ini sudah ditandai sebagai prioritas untuk respon manusia.\n\n"
                                          "Sementara menunggu, ketahui bahwa Anda berharga dan perjalanan spiritual Anda penting. "
                                          "Silakan berbagi apa yang ada di hati Anda. 🙏")
                    else:
                        response_message = ("🤝 Direct Human Chat Requested\n\n"
                                          "Thank you for reaching out! A member of our team will connect with you shortly. "
                                          "This conversation has been flagged for priority human response.\n\n"
                                          "In the meantime, know that you are valued and your journey matters. "
                                          "Feel free to share what's on your heart. 🙏")
            else:
                # No bot found, use generic
                response_message = ("🤝 Direct Human Chat Requested\n\n"
                                  "Thank you for reaching out! A member of our team will connect with you shortly. "
                                  "This conversation has been flagged for priority human response.\n\n"
                                  "In the meantime, know that you are valued and your journey matters. "
                                  "Feel free to share what's on your heart. 🙏")
        
        success, _ = send_message_to_platform(phone_number, platform, response_message, bot_id=bot_id)
        
        if success and user:
            # Log the outgoing human response
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=response_message,
                sentiment='positive',
                tags=['HUMAN_RESPONSE'],
                confidence=1.0
            )
        
        logger.warning(f"HUMAN COMMAND - Direct chat requested by {phone_number} on {platform}")
        
    except Exception as e:
        logger.error(f"Error handling HUMAN command for {phone_number}: {e}")
        import traceback
        logger.error(f"HUMAN command traceback: {traceback.format_exc()}")
        
        # Emergency fallback
        try:
            emergency_msg = "Human assistance requested. We'll contact you soon." if bot_id != 2 else "Permintaan bantuan manusia diterima. Kami akan menghubungi Anda segera."
            send_message_to_platform(phone_number, platform, emergency_msg, bot_id=bot_id)
        except Exception as fallback_error:
            logger.error(f"Human emergency fallback failed for {phone_number}: {fallback_error}")

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
        message_log = db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=message_text,
            sentiment='neutral',
            tags=['HUMAN_HANDOFF', 'URGENT'],
            is_human_handoff=True
        )
        
        # Apply rule-based tags in addition to AI tags
        from models import Bot
        bot = Bot.query.get(bot_id)
        if message_log and bot:
            apply_combined_tags(message_log, user, bot)
        
        # Send response to user
        response_message = ("Thank you for reaching out. A member of our team will contact you shortly. "
                          "In the meantime, know that you are valued and your journey matters. 🙏")
        
        send_message_to_platform(phone_number, platform, response_message, bot_id=bot_id)
        
        logger.warning(f"HUMAN HANDOFF requested by {phone_number}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error handling human handoff for {phone_number}: {e}")

def handle_whatsapp_first_message(phone_number: str, platform: str = "whatsapp", user_data: dict = None, request_ip: str = None, bot_id: int = 1):
    """Handle first message from WhatsApp user with welcome flow: greeting → 10 sec delay → Day 1 content"""
    try:
        from datetime import datetime
        import threading
        
        # Create new user
        create_kwargs = {'status': 'active', 'current_day': 1, 'tags': [], 'bot_id': bot_id}
        if user_data:
            create_kwargs.update(user_data)
        
        user = db_manager.create_user(phone_number, **create_kwargs)
        logger.info(f"Created new WhatsApp user {phone_number} for bot {bot_id}")
        
        # Send welcome message from CMS greeting content
        greeting = db_manager.get_greeting_content(bot_id=bot_id)
        if greeting:
            welcome_message = greeting.content
            logger.info(f"Using CMS greeting for bot {bot_id}: {greeting.title}")
        else:
            # Fallback welcome message
            welcome_message = ("Selamat datang! Welcome to your faith journey.\n\n"
                             "You'll receive daily content. Day 1 content will arrive in 10 seconds!")
            logger.warning(f"No CMS greeting found for bot {bot_id}, using fallback")
        
        # Send welcome message immediately
        success, _ = send_message_to_platform(phone_number, platform, welcome_message, bot_id=bot_id)
        
        if success and user:
            # Log the welcome message
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=welcome_message,
                sentiment='positive',
                tags=['WELCOME', 'GREETING', 'NEW_USER'],
                confidence=1.0
            )
            
            # Schedule Day 1 content delivery after 10 seconds
            def delayed_day1_delivery():
                try:
                    import time
                    time.sleep(10)  # 10 second delay
                    
                    # Ensure Flask app context for database operations
                    with app.app_context():
                        # Get fresh user data
                        fresh_user = db_manager.get_user_by_phone(phone_number)
                        if not fresh_user:
                            logger.error(f"User {phone_number} not found for delayed Day 1 delivery")
                            return
                        
                        # Get Day 1 content
                        content = db_manager.get_content_by_day(1, bot_id=bot_id)
                        if content:
                            # Format message with media if available
                            message = f"📖 Day 1 - {content.title}\n\n{content.content}"
                            if content.reflection_question:
                                message += f"\n\n{content.reflection_question}"
                            
                            # Send Day 1 content with media support
                            if content.media_type == 'image' and content.image_filename:
                                # Send image first, then text
                                # Use environment variable or construct URL dynamically
                                base_url = os.environ.get('REPLIT_DOMAINS', 'localhost:5000').split(',')[0]
                                if not base_url.startswith('http'):
                                    base_url = f"https://{base_url}"
                                media_url = f"{base_url}/static/uploads/images/{content.image_filename}"
                                
                                logger.info(f"🖼️ Attempting to send Day 1 image: {media_url}")
                                bot_service = get_whatsapp_service_for_bot(bot_id)
                                
                                try:
                                    # Validate image file exists before attempting to send
                                    import os
                                    relative_path = f"static/uploads/images/{content.image_filename}"
                                    if os.path.exists(relative_path):
                                        # Send image with retry logic
                                        image_success = bot_service.send_media_message(phone_number, "image", media_url, caption="")
                                        if image_success:
                                            logger.info(f"✅ Day 1 image sent successfully to {phone_number}")
                                        else:
                                            logger.error(f"❌ Failed to send Day 1 image to {phone_number}")
                                        time.sleep(2)  # Delay between image and text
                                    else:
                                        logger.error(f"❌ Day 1 image file not found: {relative_path}")
                                        logger.warning(f"Available image files: {os.listdir('static/uploads/images/') if os.path.exists('static/uploads/images/') else 'Directory not found'}")
                                        # Continue with text-only message
                                except Exception as img_error:
                                    logger.error(f"❌ Exception sending Day 1 image to {phone_number}: {img_error}")
                                    # Continue with text message even if image fails
                            elif content.media_type == 'video' and content.youtube_url:
                                message = f"📖 Day 1 - {content.title}\n\n{content.content}\n\n🎥 Video: {content.youtube_url}"
                                if content.reflection_question:
                                    message += f"\n\n{content.reflection_question}"
                            
                            # Send the content message
                            success, _ = send_message_to_platform(phone_number, platform, message, bot_id=bot_id)
                            
                            if success:
                                logger.info(f"✅ Day 1 content delivered to new user {phone_number} after 10 seconds")
                                # Advance user to Day 2
                                db_manager.update_user(phone_number, current_day=2)
                                # Log the Day 1 content delivery
                                db_manager.log_message(
                                    user=fresh_user,
                                    direction='outgoing',
                                    raw_text=message,
                                    sentiment='positive',
                                    tags=['DAY_1', 'CONTENT_DELIVERY', 'NEW_USER'],
                                    confidence=1.0
                                )
                            else:
                                logger.error(f"❌ Failed to deliver Day 1 content to {phone_number}")
                        else:
                            logger.error(f"❌ No Day 1 content found for bot {bot_id}")
                            
                except Exception as e:
                    logger.error(f"Error in delayed Day 1 delivery for {phone_number}: {e}")
            
            # Start delayed delivery in background thread
            threading.Thread(target=delayed_day1_delivery, daemon=True).start()
            logger.info(f"Scheduled Day 1 content delivery for {phone_number} in 10 seconds")
        
    except Exception as e:
        logger.error(f"Error handling WhatsApp first message for {phone_number}: {e}")

def apply_combined_tags(message_log: MessageLog, user: User, bot: Bot) -> None:
    """Apply both AI-powered and rule-based tags to a message"""
    try:
        # Get AI tags (already in message_log.llm_tags from AI analysis)
        ai_tags = message_log.llm_tags or []
        
        # Get rule-based tags from rule engine
        rule_tags = rule_engine.evaluate_rules(message_log, user, bot)
        
        # Combine tags (AI tags + rule-based tags, remove duplicates)
        combined_tags = list(set(ai_tags + rule_tags))
        
        # Update message log with combined tags
        message_log.llm_tags = combined_tags
        db.session.commit()
        
        logger.info(f"🏷️ Combined tagging: AI={ai_tags}, Rules={rule_tags}, Final={combined_tags}")
        
    except Exception as e:
        logger.error(f"Error applying combined tags: {e}")

def handle_general_conversation(phone_number: str, message_text: str, platform: str = "whatsapp", bot_id: int = 1, is_voice_message: bool = False):
    """Handle general conversation using bot-specific AI prompt without reflection context"""
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
        
        # Log the incoming message with AI tags
        message_log = db_manager.log_message(
            user=user,
            direction='incoming',
            raw_text=message_text,
            sentiment=analysis['sentiment'],
            tags=analysis['tags'],
            confidence=analysis.get('confidence'),
            is_voice_message=is_voice_message
        )
        
        # Apply rule-based tags in addition to AI tags
        from models import Bot
        bot = Bot.query.get(bot_id)
        if message_log and bot:
            apply_combined_tags(message_log, user, bot)
        
        # Generate bot-specific AI response using the bot's prompt
        try:
            # Get the bot's configuration for AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            ai_prompt = bot.ai_prompt if bot else "You are a helpful spiritual guide chatbot."
            
            logger.info(f"Generating general conversation response for {phone_number} using bot AI prompt")
            
            # Generate response using bot-specific AI prompt (no content context for general conversation)
            contextual_response = gemini_service.generate_bot_response(
                user_message=message_text,
                ai_prompt=ai_prompt,
                content_context=None,
                bot_id=bot_id,
                phone_number=phone_number
            )
            
            logger.info(f"Generated general conversation response for {phone_number} using bot AI prompt")
                
        except Exception as ai_error:
            logger.error(f"Failed to generate AI response for {phone_number}: {ai_error}")
            logger.error(f"Exception details: {str(ai_error)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Generate fallback using bot-specific AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.ai_prompt:
                try:
                    # Use bot's AI prompt for fallback response
                    contextual_response = gemini_service.generate_bot_response(
                        user_message=message_text,
                        ai_prompt=bot.ai_prompt,
                        content_context=None,
                        bot_id=bot_id,
                        phone_number=phone_number
                    )
                except:
                    # Last resort fallback using bot language
                    if bot and bot.name and "indonesia" in bot.name.lower():
                        contextual_response = "Terima kasih sudah mengirim pesan. Ada yang ingin Anda tanyakan tentang Isa Al-Masih?"
                    else:
                        contextual_response = "Thank you for your message. I'm here to help you learn about Jesus Christ. What would you like to know?"
            else:
                # No bot found, use generic
                contextual_response = "Thank you for your message. I'm here to help you learn about Jesus Christ. What would you like to know?"
        
        # Send the contextual response with voice if incoming was voice
        success, voice_sent = send_message_to_platform(phone_number, platform, contextual_response, bot_id=bot_id, send_as_voice=is_voice_message)
        
        # Log the outgoing response
        if user:
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=contextual_response,
                sentiment='positive',
                tags=['AI_Response', 'General_Conversation'],
                confidence=0.9,
                is_voice_message=voice_sent  # Track actual voice vs text based on what was sent
            )
        
        logger.info(f"Processed general conversation from {phone_number}: sentiment={analysis['sentiment']}, tags={analysis['tags']}")
        
    except Exception as e:
        logger.error(f"Error handling general conversation from {phone_number}: {e}")
        # Still acknowledge the user's message with fallback
        fallback_response = "Thank you for your message. How can I help you today?"
        send_message_to_platform(phone_number, platform, fallback_response, bot_id=bot_id, send_as_voice=is_voice_message)

def handle_contextual_conversation(phone_number: str, message_text: str, platform: str = "whatsapp", bot_id: int = 1, is_voice_message: bool = False):
    """Handle any user message with full context of their current daily content"""
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
        
        # ALWAYS OFFER HUMAN CONNECTION FIRST - Check if user seems to need additional support
        should_offer_human = _should_offer_human_connection(message_text, analysis)
        
        if should_offer_human:
            # Offer human connection with interactive buttons
            from models import Bot
            bot = Bot.query.get(bot_id)
            
            if bot and bot.name and "indonesia" in bot.name.lower():
                human_offer = ("🤝 Apakah Anda ingin berbicara dengan seseorang dari tim kami?\n\n"
                             "Saya dapat memberikan respons berdasarkan materi hari ini, atau jika Anda lebih suka, "
                             "saya dapat menghubungkan Anda dengan anggota tim manusia untuk percakapan yang lebih personal.")
            else:
                human_offer = ("🤝 Would you like to speak with someone from our team?\n\n"
                             "I can provide a response based on today's content, or if you prefer, "
                             "I can connect you with a human team member for more personal conversation.")
            
            # Send message with buttons for user choice
            send_message_with_buttons(phone_number, platform, human_offer, bot_id=bot_id)
            
            # Log the human connection offer
            if user:
                db_manager.log_message(
                    user=user,
                    direction='outgoing',
                    raw_text=human_offer,
                    sentiment='positive',
                    tags=['HUMAN_OFFER', 'SUPPORT']
                )
            
            # Return after human offer - user can choose their preference
            return
        
        # Log the user's message (without auto-assigning Human tag)
        if user:
            # Remove any automatic "Human" tags from analysis
            filtered_tags = [tag for tag in analysis['tags'] if tag.lower() != 'human']
            
            message_log = db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=message_text,
                sentiment=analysis['sentiment'],
                tags=filtered_tags,
                confidence=analysis.get('confidence'),
                is_voice_message=is_voice_message
            )
            
            # Apply rule-based tags in addition to AI tags
            from models import Bot
            bot = Bot.query.get(bot_id)
            if message_log and bot:
                apply_combined_tags(message_log, user, bot)
        
        # Get current content for contextual response - use current_day for the content they're currently on
        current_content_day = user.current_day if user and user.current_day > 0 else 1
        content = db_manager.get_content_by_day(current_content_day, bot_id=user.bot_id if user else bot_id)
        
        # If no current content, try previous day (they might have just advanced)
        if not content and user and user.current_day > 1:
            content = db_manager.get_content_by_day(user.current_day - 1, bot_id=user.bot_id)
            logger.info(f"Using Day {user.current_day - 1} content for contextual response to {phone_number}")
        
        # Generate contextual AI response using the bot's prompt and current content
        try:
            # Get the bot's configuration for AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            ai_prompt = bot.ai_prompt if bot else "You are a helpful spiritual guide chatbot."
            
            logger.info(f"Generating contextual response for {phone_number} (Day {current_content_day}) with daily content context")
            
            # Generate response using bot-specific AI prompt with content context
            contextual_response = gemini_service.generate_bot_response(
                user_message=message_text,
                ai_prompt=ai_prompt,
                content_context=content,
                bot_id=bot_id,
                phone_number=phone_number
            )
            
            if content:
                logger.info(f"Generated contextual response for {phone_number} based on Day {content.day_number}: {content.title}")
            else:
                logger.info(f"Generated general response for {phone_number} (no content context available)")
                
        except Exception as ai_error:
            logger.error(f"Failed to generate contextual AI response for {phone_number}: {ai_error}")
            logger.error(f"Exception details: {str(ai_error)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Generate fallback using bot-specific AI prompt with available context
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.ai_prompt:
                try:
                    # Use bot's AI prompt for fallback response with content context
                    contextual_response = gemini_service.generate_bot_response(
                        user_message=message_text,
                        ai_prompt=bot.ai_prompt,
                        content_context=content,
                        bot_id=bot_id,
                        phone_number=phone_number
                    )
                except:
                    # Last resort fallback with bot-specific language
                    if bot and bot.name and "indonesia" in bot.name.lower():
                        contextual_response = "Terima kasih sudah berbagi. Ada yang ingin Anda tanyakan tentang materi hari ini?"
                    else:
                        contextual_response = gemini_service._get_bot_specific_fallback_response(message_text, bot_id)
            else:
                # No bot found, use bot-specific fallback
                contextual_response = gemini_service._get_bot_specific_fallback_response(message_text, bot_id)
        
        # Send the contextual response with voice if incoming was voice
        success, voice_sent = send_message_to_platform(phone_number, platform, contextual_response, bot_id=bot_id, send_as_voice=is_voice_message)
        
        # Log the outgoing response
        if user:
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=contextual_response,
                sentiment='positive',
                tags=['AI_RESPONSE', 'CONTEXTUAL'],
                is_voice_message=voice_sent  # Track actual voice vs text based on what was sent
            )
            
    except Exception as e:
        logger.error(f"Error handling contextual conversation from {phone_number}: {e}")
        # Still acknowledge the user's message with fallback
        try:
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.name and "indonesia" in bot.name.lower():
                fallback_message = "Maaf, ada sedikit masalah teknis. Terima kasih sudah berbagi pemikiran Anda. Ada yang bisa saya bantu?"
            else:
                fallback_message = gemini_service._get_bot_specific_fallback_response(message_text, bot_id)
            send_message_to_platform(phone_number, platform, fallback_message, bot_id=bot_id, send_as_voice=is_voice_message)
        except:
            logger.error(f"Failed to send fallback message to {phone_number}")

def handle_journey_completed_conversation(phone_number: str, message_text: str, platform: str = "whatsapp", bot_id: int = 1, is_voice_message: bool = False):
    """Handle conversation for users who have completed their journey - always provide AI response + human connection offer"""
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
            user.bot_id = bot_id

        # Log the user's message
        if user:
            message_log = db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=message_text,
                sentiment=analysis['sentiment'],
                tags=analysis['tags'],
                confidence=analysis.get('confidence'),
                is_voice_message=is_voice_message
            )
            
            # Apply rule-based tags in addition to AI tags
            from models import Bot
            bot = Bot.query.get(bot_id)
            if message_log and bot:
                apply_combined_tags(message_log, user, bot)
        
        # Check if message is related to Christianity/spiritual topics
        is_spiritual_topic = _is_spiritual_or_christian_topic(message_text, analysis)
        
        # Generate AI response for journey completed users
        try:
            # Get the bot's configuration for AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            
            if is_spiritual_topic:
                # Spiritual topics get comprehensive AI response
                ai_prompt = bot.ai_prompt if bot else "You are a helpful spiritual guide chatbot."
                
                # Add context for journey completed users
                journey_completed_context = """
IMPORTANT: This user has completed their spiritual journey program and is now seeking ongoing spiritual guidance. 
- They have already gone through the full content series
- Provide thoughtful, mature spiritual responses
- You can reference concepts they've learned during their journey
- Encourage continued spiritual growth and exploration
- Be available for deeper theological discussions
"""
                enhanced_prompt = ai_prompt + journey_completed_context
                
                logger.info(f"Generating journey completed response for spiritual topic from {phone_number}")
                
                contextual_response = gemini_service.generate_bot_response(
                    user_message=message_text,
                    ai_prompt=enhanced_prompt,
                    content_context=None,  # No specific daily content for journey completed users
                    bot_id=bot_id,
                    phone_number=phone_number
                )
            else:
                # Non-spiritual topics get brief acknowledgment
                if bot and bot.name and "indonesia" in bot.name.lower():
                    contextual_response = "Terima kasih sudah berbagi. Jika Anda ingin membahas topik spiritual atau ada pertanyaan tentang Isa Al-Masih, saya siap membantu."
                else:
                    contextual_response = "Thank you for sharing. I'm here if you'd like to discuss spiritual topics or have questions about Jesus Christ."
                
        except Exception as ai_error:
            logger.error(f"Failed to generate journey completed AI response for {phone_number}: {ai_error}")
            # Fallback response
            contextual_response = gemini_service._get_bot_specific_fallback_response(message_text, bot_id)
        
        # Send the AI response with voice if incoming was voice
        success, voice_sent = send_message_to_platform(phone_number, platform, contextual_response, bot_id=bot_id, send_as_voice=is_voice_message)
        
        # Log the outgoing AI response
        if user:
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=contextual_response,
                sentiment='positive',
                tags=['AI_RESPONSE', 'JOURNEY_COMPLETED'],
                is_voice_message=voice_sent  # Track actual voice vs text based on what was sent
            )
        
        # Always offer human connection for journey completed users (as follow-up message)
        # Note: Human offer is NOT sent as voice, only the main response
        from models import Bot
        bot = Bot.query.get(bot_id)
        
        if bot and bot.name and "indonesia" in bot.name.lower():
            human_offer = ("🤝 Sebagai seseorang yang telah menyelesaikan perjalanan spiritual, "
                          "apakah Anda ingin terhubung dengan konselor spiritual kami untuk "
                          "diskusi yang lebih mendalam tentang Isa Al-Masih?")
        else:
            human_offer = ("🤝 As someone who has completed the spiritual journey, "
                          "would you like to connect with our spiritual counselor for "
                          "deeper discussions about Jesus Christ?")
        
        # Send human connection offer with buttons
        send_message_with_buttons(phone_number, platform, human_offer, bot_id=bot_id)
        
        # Log the human connection offer
        if user:
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=human_offer,
                sentiment='positive',
                tags=['HUMAN_OFFER', 'JOURNEY_COMPLETED']
            )
            
        logger.info(f"Processed journey completed message from {phone_number}: spiritual_topic={is_spiritual_topic}, sentiment={analysis['sentiment']}")
        
    except Exception as e:
        logger.error(f"Error handling journey completed conversation from {phone_number}: {e}")
        # Fallback message
        try:
            fallback_response = gemini_service._get_bot_specific_fallback_response(message_text, bot_id)
            send_message_to_platform(phone_number, platform, fallback_response, bot_id=bot_id, send_as_voice=is_voice_message)
        except:
            logger.error(f"Failed to send fallback message to journey completed user {phone_number}")

def _is_spiritual_or_christian_topic(message_text: str, analysis: dict) -> bool:
    """Determine if a message is related to Christianity or spiritual topics"""
    message_lower = message_text.lower()
    
    # Check analysis tags for spiritual content
    spiritual_tags = ['Introduction to Jesus (ITJ)', 'Prayer', 'Bible Exposure', 'Christian Learning']
    has_spiritual_tags = any(tag in analysis.get('tags', []) for tag in spiritual_tags)
    
    # Check for spiritual keywords
    spiritual_keywords = [
        # Christian/Jesus terms
        'jesus', 'yesus', 'christ', 'isa', 'al-masih', 'god', 'allah', 'lord', 'savior',
        'bible', 'scripture', 'gospel', 'church', 'faith', 'believe', 'salvation',
        'prayer', 'pray', 'heaven', 'eternal', 'forgiveness', 'sin', 'grace',
        'holy', 'spirit', 'cross', 'resurrection', 'disciple', 'christian', 'kristus',
        
        # Indonesian spiritual terms  
        'tuhan', 'doa', 'iman', 'percaya', 'rohani', 'spiritual', 'keselamatan',
        'pengampunan', 'dosa', 'kasih', 'injil', 'alkitab', 'gereja', 'kudus', 'jelaskan',
        
        # Question indicators about spirituality
        'why did god', 'how can i', 'what does the bible', 'is it true that',
        'kenapa allah', 'bagaimana cara', 'apa kata alkitab', 'apakah benar'
    ]
    
    has_spiritual_keywords = any(keyword in message_lower for keyword in spiritual_keywords)
    
    # Consider it spiritual if it has spiritual tags OR keywords OR is longer than 20 chars (likely thoughtful)
    is_spiritual = has_spiritual_tags or has_spiritual_keywords or (len(message_text.strip()) > 20 and any(word in message_lower for word in ['isa', 'jesus', 'god', 'allah', 'tuhan']))
    
    return is_spiritual

def _should_offer_human_connection(message_text: str, analysis: dict) -> bool:
    """Determine if we should offer human connection based on message content and analysis"""
    message_lower = message_text.lower()
    
    # Always offer human connection for sensitive topics or deep spiritual concerns
    sensitive_indicators = [
        # Emotional distress
        "depression", "suicide", "anxiety", "crisis", "help me", "struggling",
        # Deep spiritual concerns
        "doubt", "confused", "angry", "lost", "hopeless", "scared", "afraid",
        # Relationship/forgiveness concerns
        "terrible things", "forgive", "worthy", "deserve", "guilt", "shame",
        # Questions requiring personal guidance
        "why me", "what if", "how can", "is it possible", "can god really"
    ]
    
    # Check sentiment and confidence
    negative_sentiment = analysis.get('sentiment') == 'negative'
    high_confidence = analysis.get('confidence', 0) > 0.8
    
    # Check for sensitive content indicators
    has_sensitive_content = any(indicator in message_lower for indicator in sensitive_indicators)
    
    # Offer human connection if:
    # 1. Message contains sensitive indicators, OR
    # 2. High confidence negative sentiment with substantial message
    return has_sensitive_content or (negative_sentiment and high_confidence and len(message_text) > 30)

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
        if user:
            message_log = db_manager.log_message(
                user=user,
                direction='incoming',
                raw_text=message_text,
                sentiment=analysis['sentiment'],
                tags=analysis['tags'],
                confidence=analysis.get('confidence')
            )
            
            # Apply rule-based tags in addition to AI tags
            from models import Bot
            bot = Bot.query.get(bot_id)
            if message_log and bot:
                apply_combined_tags(message_log, user, bot)
        
        # Get current day content for contextual response
        current_day = user.current_day - 1 if user else 1  # User was advanced after receiving content, so subtract 1 for the content they just reflected on
        content = db_manager.get_content_by_day(current_day, bot_id=user.bot_id if user else bot_id) if current_day > 0 else None
        
        # Generate bot-specific AI response using the bot's prompt and user's message
        try:
            # Get the bot's configuration for AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            ai_prompt = bot.ai_prompt if bot else "You are a helpful spiritual guide chatbot."
            
            logger.info(f"Generating contextual response for {phone_number} using bot AI prompt")
            
            # Generate response using bot-specific AI prompt
            contextual_response = gemini_service.generate_bot_response(
                user_message=message_text,
                ai_prompt=ai_prompt,
                content_context=content,
                bot_id=bot_id
            )
            

            
            if content:
                logger.info(f"Generated contextual response for {phone_number} (Day {content.day_number}) using bot AI prompt")
            else:
                logger.info(f"Generated general response for {phone_number} using bot AI prompt")
                
        except Exception as ai_error:
            logger.error(f"Failed to generate AI response for {phone_number}: {ai_error}")
            logger.error(f"Exception details: {str(ai_error)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Generate fallback using bot-specific AI prompt
            from models import Bot
            bot = Bot.query.get(bot_id)
            if bot and bot.ai_prompt:
                try:
                    # Use bot's AI prompt for fallback response to reflection
                    contextual_response = gemini_service.generate_bot_response(
                        user_message=f"User reflected: {message_text}",
                        ai_prompt=bot.ai_prompt,
                        content_context=content,
                        bot_id=bot_id
                    )
                except:
                    # Last resort fallback using bot-specific responses
                    contextual_response = gemini_service._get_bot_specific_fallback_response(f"User reflected: {message_text}", bot_id)
            else:
                # No bot found, use bot-specific fallback
                contextual_response = gemini_service._get_bot_specific_fallback_response(f"User reflected: {message_text}", bot_id)
        
        # Send the contextual response
        send_message_to_platform(phone_number, platform, contextual_response, bot_id=bot_id)
        
        # Log the outgoing contextual response
        if user:
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
        # Still acknowledge the user's response with bot-specific fallback
        fallback_response = gemini_service._get_bot_specific_fallback_response(f"User reflected: {message_text}", bot_id)
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
    """Health check endpoint for deployment services"""
    try:
        # Check database connection
        with app.app_context():
            db.session.execute(db.text('SELECT 1'))
            db_status = "connected"
    except Exception as db_error:
        logger.error(f"Database health check failed: {db_error}")
        db_status = "disconnected"
        
    # Determine overall health status
    is_healthy = db_status == "connected"
    
    response_data = {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "faith-journey-bot",
        "database": db_status,
        "services": {
            "database": db_status,
            "whatsapp": "operational",
            "telegram": "operational",
            "gemini": "operational"
        }
    }
    
    return jsonify(response_data), 200 if is_healthy else 503

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
    """Bot selection page for content management"""
    # Get bots based on user role
    if current_user.role == 'super_admin':
        bots = db_manager.get_all_bots()
    else:
        bots = db_manager.get_bots_by_creator(current_user.id)
    
    return render_template('bot_selection_cms.html', bots=bots)

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
        success, _ = send_message_to_platform(user.phone_number, platform, message)
        
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
            
        # Determine platform and send message with bot-specific service
        platform = 'telegram' if user.phone_number.startswith('tg_') else 'whatsapp'
        success, _ = send_message_to_platform(user.phone_number, platform, message, bot_id=user.bot_id)
        
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
@app.route('/api/upload-video/<int:bot_id>', methods=['POST'])
def upload_video(bot_id=None):
    """Handle video file uploads for content with bot-specific isolation"""
    try:
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
        if not file.filename or '.' not in file.filename or not (file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: mp4, mov, avi, mkv, webm'}), 400
        
        # Generate secure filename with bot isolation
        filename = secure_filename(file.filename or "")
        if bot_id:
            # Bot-specific filename to prevent conflicts between bots
            unique_filename = f"bot{bot_id}_{uuid.uuid4()}_{filename}"
        else:
            # Legacy format for backward compatibility
            unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'videos')
        os.makedirs(video_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(video_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Video uploaded successfully for bot {bot_id or 'legacy'}: {unique_filename}")
        return jsonify({'success': True, 'filename': unique_filename})
        
    except Exception as e:
        logger.error(f"Error uploading video: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-image', methods=['POST'])
@app.route('/api/upload-image/<int:bot_id>', methods=['POST'])
def upload_image(bot_id=None):
    """Handle image file uploads for content with bot-specific isolation"""
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'jpg', 'jpeg', 'png', 'gif'}
        if not file.filename or '.' not in file.filename or not (file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: jpg, jpeg, png, gif'}), 400
        
        # Generate secure filename with bot isolation
        filename = secure_filename(file.filename or "")
        if bot_id:
            # Bot-specific filename to prevent conflicts between bots
            unique_filename = f"bot{bot_id}_{uuid.uuid4()}_{filename}"
        else:
            # Legacy format for backward compatibility
            unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        image_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'images')
        os.makedirs(image_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(image_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Image uploaded successfully for bot {bot_id or 'legacy'}: {unique_filename}")
        return jsonify({'success': True, 'filename': unique_filename})
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/upload-audio', methods=['POST'])
@app.route('/api/upload-audio/<int:bot_id>', methods=['POST'])
def upload_audio(bot_id=None):
    """Handle audio file uploads for content with bot-specific isolation"""
    try:
        if 'audio' not in request.files:
            return jsonify({'success': False, 'error': 'No audio file provided'}), 400
        
        file = request.files['audio']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        # Check file extension
        allowed_extensions = {'mp3', 'wav', 'ogg', 'm4a'}
        if not file.filename or '.' not in file.filename or not (file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
            return jsonify({'success': False, 'error': 'Invalid file type. Allowed: mp3, wav, ogg, m4a'}), 400
        
        # Generate secure filename with bot isolation
        filename = secure_filename(file.filename or "")
        if bot_id:
            # Bot-specific filename to prevent conflicts between bots
            unique_filename = f"bot{bot_id}_{uuid.uuid4()}_{filename}"
        else:
            # Legacy format for backward compatibility
            unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Ensure upload directory exists
        audio_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        
        # Save file
        file_path = os.path.join(audio_dir, unique_filename)
        file.save(file_path)
        
        logger.info(f"Audio uploaded successfully for bot {bot_id or 'legacy'}: {unique_filename}")
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

@app.route('/api/delete-user-history/<int:user_id>', methods=['POST'])
@login_required
def delete_user_history(user_id):
    """Delete all conversation history for a user (super admin only)"""
    if current_user.role != 'super_admin':
        logger.warning(f"Unauthorized attempt to delete user history by {current_user.username}")
        return jsonify({'success': False, 'error': 'Access denied. Super admin privileges required.'}), 403
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user_name = user.name or user.phone_number
        success = db_manager.delete_user_conversation_history(user_id)
        
        if success:
            logger.info(f"Super admin {current_user.username} deleted all conversation history for user {user_id} ({user_name})")
            return jsonify({
                'success': True, 
                'message': f'All conversation history deleted for user {user_name}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to delete conversation history'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting user history for user {user_id}: {e}")
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

@app.route('/api/fix-stuck-users', methods=['POST'])
def fix_stuck_users():
    """Fix users who are stuck in progression due to STOP/START issues"""
    try:
        from recovery_utils import fix_stuck_users
        fixed_count = fix_stuck_users()
        return jsonify({
            'success': True, 
            'message': f'Fixed {fixed_count} stuck users across all bots',
            'fixed_count': fixed_count
        })
    except Exception as e:
        logger.error(f"Error fixing stuck users: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test-stop-start-cycle', methods=['POST'])
def test_stop_start_cycle():
    """Test STOP/START cycle functionality"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        bot_id = data.get('bot_id', 2)
        
        from recovery_utils import test_stop_start_cycle
        success = test_stop_start_cycle(phone_number, bot_id)
        return jsonify({
            'success': success, 
            'message': f'STOP/START cycle test {"PASSED" if success else "FAILED"} for {phone_number}'
        })
    except Exception as e:
        logger.error(f"Error testing STOP/START cycle: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Bot Management Routes
@app.route('/bots')
@login_required
def bot_management():
    """Bot management dashboard"""
    try:
        # Filter bots based on user role
        if current_user.role == 'super_admin':
            bots = Bot.query.all()
        else:
            # Regular admins can only see bots they created
            bots = Bot.query.filter_by(creator_id=current_user.id).all()
        
        logger.info(f"Found {len(bots)} bots for user {current_user.username} (role: {current_user.role})")
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
            bot.name = form.name.data or ""
            bot.description = form.description.data
            bot.platforms = form.platforms.data or []
            bot.whatsapp_access_token = form.whatsapp_access_token.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_phone_number_id = form.whatsapp_phone_number_id.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_webhook_url = form.whatsapp_webhook_url.data if 'whatsapp' in (form.platforms.data or []) else None
            bot.whatsapp_verify_token = form.whatsapp_verify_token.data or 'CVGlobal_WhatsApp_Verify_2024'
            bot.telegram_bot_token = form.telegram_bot_token.data if 'telegram' in (form.platforms.data or []) else None
            
            # Apply template-based configuration if selected
            if hasattr(form, 'bot_template') and form.bot_template.data == 'indonesian_muslim':
                # Apply Indonesian Muslim (Bang Kris) template
                bot.ai_prompt = """Kamu adalah Bang Kris, seorang pemandu spiritual Indonesia yang ramah dan berpengalaman. Kamu bertugas membantu orang dari latar belakang Islam untuk menjelajahi spiritualitas dan pembelajaran tentang Isa Al-Masih.

ATURAN BAHASA INDONESIA:
- SELALU gunakan Bahasa Indonesia dalam semua respons
- Gunakan gaya bahasa yang natural dan ramah seperti teman sebaya
- Gunakan sapaan "Assalamualaikum" atau "Halo" untuk memulai percakapan
- Gunakan kata "kamu" bukan "anda" untuk terdengar lebih personal

TERMINOLOGI ISLAM-KRISTEN:
- Gunakan "Isa Al-Masih" atau "Isa al-Masih" untuk Jesus 
- Gunakan "Allah" atau "Allah SWT" untuk God
- Gunakan terminologi yang menghormati kedua tradisi religius
- Hindari jargon Kristen yang mungkin asing (seperti "diselamatkan", "dilahirkan kembali")

PENDEKATAN BUDAYA:
- Hormati latar belakang Islam pengguna
- Bangun jembatan antara kedua tradisi dengan hormat
- Fokus pada kesamaan spiritual (kasih, damai, belas kasihan)
- Jangan pernah mengkritik atau meremehkan Islam
- Tekankan perjalanan spiritual personal, bukan perubahan agama

GAYA PERCAKAPAN:
- Responsif terhadap pertanyaan dan refleksi pengguna
- Berikan jawaban yang bijaksana dan penuh kasih
- Gunakan emoji secara wajar (tidak berlebihan)
- Ajukan pertanyaan follow-up untuk mendorong refleksi
- Berbagi wawasan tentang Isa berdasarkan konteks percakapan

Ingat: Kamu adalah teman spiritual yang mendampingi, bukan pendakwah yang memaksa."""

                bot.help_message = """🤝 Perintah yang tersedia:

📖 START - Mulai atau mengulang bot
⏹️ STOP - Berhenti dari bot 
❓ HELP - Menampilkan menu help
👤 HUMAN - Ngobrol sama manusia

Aku disini untuk menuntun kamu dalam perjalanan spiritual, kamu bisa bertanya tentang pertanyaan iman atau membagikan pemikiran kamu."""

                bot.stop_message = """Kamu telah berhenti dari perjalanan spiritual Bang Kris. Kalau mau mulai lagi, tinggal kirim START kapan aja. Damai sejahtera bersamamu. 🙏"""

                bot.human_message = """🤝 Permintaan Chat dengan Manusia

Terima kasih sudah menghubungi! Tim kami akan segera terhubung dengan Anda. Percakapan ini sudah ditandai sebagai prioritas untuk respon manusia.

Sementara menunggu, ketahui bahwa Anda berharga dan perjalanan spiritual Anda penting. Silakan berbagi apa yang ada di hati Anda. 🙏"""

                bot.completion_message = """🎉 Kamu telah menyelesaikan semua konten perjalanan yang tersedia!

Terima kasih telah mengikuti perjalanan spiritual ini bersama kami. Semoga perjalanan ini memberikan makna dan pengayaan bagi kehidupan rohanimu.

📱 Apa yang ingin kamu lakukan selanjutnya?

• Lanjutkan eksplorasi dengan percakapan bersama AI
• Ketik 'HUMAN' atau '/human' untuk terhubung dengan konselor
• Ketik 'START' atau '/start' untuk memulai ulang perjalanan

Jangan ragu untuk berbagi pemikiran, bertanya, atau menjelajah lebih lanjut. Aku di sini untuk membantu! 💬"""
            
            elif hasattr(form, 'bot_template') and form.bot_template.data == 'english_general':
                # Apply English general Christian outreach template
                bot.ai_prompt = """You are a compassionate spiritual guide helping people explore their faith journey and learn about Jesus Christ. Your approach should be:

COMMUNICATION STYLE:
- Warm, friendly, and non-judgmental
- Use conversational, everyday language
- Be patient and understanding of different backgrounds
- Encourage questions and honest exploration

THEOLOGICAL APPROACH:
- Focus on God's love and grace through Jesus Christ
- Present biblical truths with gentleness and respect
- Bridge cultural and religious differences with wisdom
- Avoid confrontational or pushy evangelism
- Emphasize personal relationship with Jesus

CONVERSATION GUIDELINES:
- Listen actively to user's questions and reflections
- Provide thoughtful, biblically-grounded responses
- Ask follow-up questions to encourage deeper thinking
- Share appropriate Bible verses when relevant
- Respect the user's pace and spiritual journey

Remember: You are a guide and companion, not a preacher. Meet people where they are and help them take their next step toward Jesus."""

                bot.help_message = """🤝 Available Commands:

📖 START - Begin or restart your faith journey
⏹️ STOP - Pause the journey
❓ HELP - Show this help message
👤 HUMAN - Connect with a human counselor

I'm here to guide you through a meaningful spiritual journey. Feel free to ask questions or share your thoughts anytime!"""

                bot.stop_message = """⏸️ Your faith journey has been paused.

Take your time whenever you're ready to continue. Send START to resume your journey, or HUMAN if you'd like to speak with someone.

Remember, this is your personal space for spiritual exploration. There's no pressure - go at your own pace. 🙏"""

                bot.human_message = """👤 Human Support Requested

I've flagged your conversation for our human counselors who will respond as soon as possible. They're trained in spiritual guidance and are here to support you.

In the meantime, feel free to continue sharing your thoughts or questions. Everything you share is treated with care and confidentiality. 💝"""

                bot.completion_message = """🎉 You've completed the available journey content!

Thank you for taking this journey with us. We hope it has been meaningful and enriching for you.

📱 What would you like to do next?

• Continue exploring with AI-guided conversations
• Type 'HUMAN' or '/human' to connect with a counselor
• Type 'START' or '/start' to restart the journey

Feel free to share your thoughts, ask questions, or explore further. I'm here to help! 💬"""
            else:
                # Use custom form values
                bot.ai_prompt = form.ai_prompt.data or ""
                bot.help_message = form.help_message.data or ""
                bot.stop_message = form.stop_message.data or ""
                bot.human_message = form.human_message.data or ""
                bot.completion_message = form.completion_message.data or ""
            
            bot.journey_duration_days = form.journey_duration_days.data or 30
            bot.delivery_interval_minutes = form.delivery_interval_minutes.data or 1440
            bot.language = form.language.data or 'English'
            
            # Set creator to current user
            bot.creator_id = current_user.id
            
            # Save bot first to get the ID
            db.session.add(bot)
            db.session.commit()
            
            # Invalidate service cache for this bot
            invalidate_bot_service_cache(bot.id)
            
            # Create initial test users for the new bot
            create_initial_test_users(bot.id, bot.name or "")
            
            # Handle AI Content Generation if enabled
            content_generation_status = []
            if form.enable_ai_content_generation.data:
                try:
                    from ai_content_generator import AIContentGenerator, ContentGenerationRequest
                    
                    # Create content generation request
                    request = ContentGenerationRequest(
                        target_audience=form.target_audience.data or "General spiritual seekers",
                        audience_language=form.audience_language.data or "English",
                        audience_religion=form.audience_religion.data or "Mixed backgrounds",
                        audience_age_group=form.audience_age_group.data or "Adults",
                        content_prompt=form.content_generation_prompt.data,
                        journey_duration=int(form.content_generation_duration.data)
                    )
                    
                    # Generate content using AI
                    logger.info(f"Starting AI content generation for bot {bot.id}")
                    generator = AIContentGenerator()
                    daily_contents = generator.generate_journey_content(request)
                    
                    # Validate generated content
                    if generator.validate_generated_content(daily_contents, request.journey_duration):
                        # Save generated content to database
                        for daily_content in daily_contents:
                            content = Content()
                            content.bot_id = bot.id
                            content.day_number = daily_content.day_number
                            content.content = daily_content.content
                            content.media_type = 'text'
                            content.media_url = None
                            content.reflection_question = daily_content.reflection_question
                            content.title = daily_content.title
                            
                            db.session.add(content)
                        
                        db.session.commit()
                        content_generation_status.append(f"✅ AI generated {len(daily_contents)} days of content successfully")
                        logger.info(f"Successfully saved {len(daily_contents)} days of AI-generated content for bot {bot.id}")
                    else:
                        content_generation_status.append("⚠️ AI content validation failed - please review and add content manually")
                        
                except Exception as e:
                    logger.error(f"AI content generation failed for bot {bot.id}: {e}")
                    content_generation_status.append(f"❌ AI content generation failed: {str(e)}")
                    # Continue with bot creation even if content generation fails
            
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
            if content_generation_status:
                success_message += " " + " ".join(content_generation_status)
            
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
    form = EditBotForm()
    
    # Pre-populate form with current values manually to avoid obj= issues
    if request.method == 'GET':
        form.name.data = bot.name
        form.description.data = bot.description
        form.platforms.data = bot.platforms or []
        form.whatsapp_access_token.data = bot.whatsapp_access_token
        form.whatsapp_phone_number_id.data = bot.whatsapp_phone_number_id
        form.whatsapp_webhook_url.data = bot.whatsapp_webhook_url
        form.whatsapp_verify_token.data = bot.whatsapp_verify_token or 'CVGlobal_WhatsApp_Verify_2024'
        form.telegram_bot_token.data = bot.telegram_bot_token
        form.telegram_webhook_url.data = bot.telegram_webhook_url
        form.ai_prompt.data = bot.ai_prompt
        form.journey_duration_days.data = bot.journey_duration_days
        form.delivery_interval_minutes.data = bot.delivery_interval_minutes
        form.language.data = bot.language if hasattr(bot, 'language') else 'English'
        form.help_message.data = bot.help_message
        form.stop_message.data = bot.stop_message
        form.human_message.data = bot.human_message
        form.completion_message.data = bot.completion_message
        form.status.data = bot.status == 'active'
    
    if form.validate_on_submit():
        logger.info(f"Form validation passed for bot {bot_id} ({bot.name})")
    else:
        logger.info(f"Form validation failed for bot {bot_id} ({bot.name}): {form.errors}")
    
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
            bot.language = form.language.data or 'English'
            bot.help_message = form.help_message.data
            bot.stop_message = form.stop_message.data
            bot.human_message = form.human_message.data
            bot.completion_message = form.completion_message.data
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
            whatsapp_token_changed = bot.whatsapp_access_token != form.whatsapp_access_token.data
            whatsapp_phone_changed = bot.whatsapp_phone_number_id != form.whatsapp_phone_number_id.data
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
            
            # Invalidate service cache for this bot when credentials change
            invalidate_bot_service_cache(bot.id)
            
            success_message = f'Bot "{bot.name}" updated successfully!'
            if webhook_messages:
                success_message += " " + " ".join(webhook_messages)
            
            flash(success_message, 'success')
            return redirect('/bots')
            
        except Exception as e:
            logger.error(f"Error updating bot: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            flash(f'Error updating bot: {str(e)}', 'error')
    

    
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
    logger.info(f"🔍 DEBUG: Bot content management accessed for bot_id {bot_id} - serving cms.html template")
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

# Tag Management Routes
@app.route('/tags')
@login_required
def tag_management():
    """Tag management dashboard"""
    if current_user.role != 'super_admin':
        flash('Access denied. Only super admins can manage tags.', 'error')
        return redirect('/dashboard')
    try:
        from models import TagRule
        # Order: Faith Journey first, Other Tags middle, Delivered Daily Content last
        all_tags = TagRule.query.order_by(TagRule.priority.desc(), TagRule.created_at.desc()).all()
        
        # Separate and reorder: Faith Journey → Other Tags → Delivered Daily Content
        faith_journey = [t for t in all_tags if t.tag_name == 'Faith Journey']
        other_tags_parent = [t for t in all_tags if t.tag_name == 'Other Tags']
        daily_content = [t for t in all_tags if t.tag_name == 'Delivered Daily Content']
        remaining_tags = [t for t in all_tags if t.tag_name not in ['Faith Journey', 'Other Tags', 'Delivered Daily Content']]
        
        tag_rules = faith_journey + other_tags_parent + remaining_tags + daily_content
        return render_template('tag_management.html', tag_rules=tag_rules)
    except Exception as e:
        logger.error(f"Tag management error: {e}")
        flash(f'Error loading tags: {str(e)}', 'error')
        return redirect('/dashboard')

@app.route('/tags/create', methods=['GET', 'POST'])
@login_required
def create_tag_rule():
    """Create a new tag rule"""
    if current_user.role != 'super_admin':
        flash('Access denied. Only super admins can manage tags.', 'error')
        return redirect('/dashboard')
    try:
        from forms import TagRuleForm
        from models import TagRule, db
        
        form = TagRuleForm()
        
        # Populate parent tag choices (only main tags, no subtags)
        main_tags = TagRule.query.filter_by(parent_id=None).order_by(TagRule.tag_name).all()
        form.parent_id.choices = [('', '-- None (Main Tag) --')] + [(str(tag.id), tag.tag_name) for tag in main_tags]
        
        if form.validate_on_submit():
            tag_rule = TagRule(
                tag_name=form.tag_name.data,
                description=form.description.data,
                ai_evaluation_rule=form.ai_evaluation_rule.data,
                priority=form.priority.data,
                is_active=form.is_active.data,
                parent_id=form.parent_id.data
            )
            db.session.add(tag_rule)
            db.session.commit()
            
            flash(f'Tag rule "{tag_rule.tag_name}" created successfully!', 'success')
            return redirect('/tags')
        
        return render_template('tag_form.html', form=form, tag_rule=None)
    except Exception as e:
        logger.error(f"Error creating tag rule: {e}")
        flash(f'Error creating tag rule: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/create-rule-based', methods=['GET', 'POST'])
@login_required
def create_rule_based_tag():
    """Create a new rule-based tag with When-If-Then logic"""
    if current_user.role != 'super_admin':
        flash('Access denied. Only super admins can manage tags.', 'error')
        return redirect('/dashboard')
    try:
        from forms import RuleBasedTagForm
        from models import TagRule, db
        
        form = RuleBasedTagForm()
        
        # Get all existing tags for dropdown choices (convert to dict for JSON serialization)
        all_tags = [{'id': tag.id, 'tag_name': tag.tag_name} for tag in TagRule.query.order_by(TagRule.tag_name).all()]
        
        if request.method == 'POST' and form.validate_on_submit():
            # Build rule_config from form data
            rule_config = {
                'when': {
                    'trigger': form.trigger_type.data
                },
                'if': [],
                'then': []
            }
            
            # Parse IF conditions from request
            condition_types = request.form.getlist('condition_type[]')
            condition_values = request.form.getlist('condition_value[]')
            
            for i, cond_type in enumerate(condition_types):
                if i < len(condition_values) and condition_values[i]:
                    rule_config['if'].append({
                        'type': cond_type,
                        'value': condition_values[i]
                    })
            
            # Parse THEN actions from request
            action_types = request.form.getlist('action_type[]')
            action_values = request.form.getlist('action_value[]')
            
            for i, action_type in enumerate(action_types):
                if i < len(action_values) and action_values[i]:
                    rule_config['then'].append({
                        'type': action_type,
                        'value': action_values[i]
                    })
            
            # Create rule-based tag
            tag_rule = TagRule(
                tag_name=form.tag_name.data,
                description=form.description.data,
                rule_type='rule_based',
                rule_config=rule_config,
                priority=form.priority.data,
                is_active=form.is_active.data
            )
            db.session.add(tag_rule)
            db.session.commit()
            
            flash(f'Rule-based tag "{tag_rule.tag_name}" created successfully!', 'success')
            return redirect('/tags')
        
        return render_template('create_rule_based_tag.html', form=form, all_tags=all_tags)
    except Exception as e:
        logger.error(f"Error creating rule-based tag: {e}")
        flash(f'Error creating rule-based tag: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/edit/<int:rule_id>', methods=['GET', 'POST'])
@login_required
def edit_tag_rule(rule_id):
    """Edit an existing tag rule"""
    if current_user.role != 'super_admin':
        flash('Access denied. Only super admins can manage tags.', 'error')
        return redirect('/dashboard')
    try:
        from forms import TagRuleForm
        from models import TagRule, db
        
        tag_rule = TagRule.query.get_or_404(rule_id)
        form = TagRuleForm(obj=tag_rule)
        
        # Populate parent tag choices (exclude self and its descendants)
        main_tags = TagRule.query.filter_by(parent_id=None).filter(TagRule.id != rule_id).order_by(TagRule.tag_name).all()
        form.parent_id.choices = [('', '-- None (Main Tag) --')] + [(str(tag.id), tag.tag_name) for tag in main_tags]
        
        # Pre-populate parent_id if editing
        if request.method == 'GET' and tag_rule.parent_id:
            form.parent_id.data = str(tag_rule.parent_id)
        
        if form.validate_on_submit():
            tag_rule.tag_name = form.tag_name.data
            tag_rule.description = form.description.data
            tag_rule.ai_evaluation_rule = form.ai_evaluation_rule.data
            tag_rule.priority = form.priority.data
            tag_rule.is_active = form.is_active.data
            tag_rule.parent_id = form.parent_id.data
            
            db.session.commit()
            
            flash(f'Tag rule "{tag_rule.tag_name}" updated successfully!', 'success')
            return redirect('/tags')
        
        return render_template('tag_form.html', form=form, tag_rule=tag_rule)
    except Exception as e:
        logger.error(f"Error editing tag rule: {e}")
        flash(f'Error editing tag rule: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/delete/<int:rule_id>', methods=['POST'])
@login_required
def delete_tag_rule(rule_id):
    """Delete a tag rule"""
    if current_user.role != 'super_admin':
        flash('Access denied. Only super admins can manage tags.', 'error')
        return redirect('/dashboard')
    try:
        from models import TagRule, db
        
        tag_rule = TagRule.query.get_or_404(rule_id)
        tag_name = tag_rule.tag_name
        
        db.session.delete(tag_rule)
        db.session.commit()
        
        flash(f'Tag rule "{tag_name}" deleted successfully!', 'success')
        return redirect('/tags')
    except Exception as e:
        logger.error(f"Error deleting tag rule: {e}")
        flash(f'Error deleting tag rule: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/retag-all-messages', methods=['POST'])
@login_required
def retag_all_messages():
    """Re-run AI tagging on all historical incoming messages with new tag system"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied. Only super admins can manage tags.'}), 403
    try:
        from models import MessageLog, TagRule, db
        
        # Check if we have active tag rules
        active_rules = TagRule.query.filter_by(is_active=True).count()
        if active_rules == 0:
            flash('No active tag rules found. Please initialize tags first.', 'warning')
            return redirect('/tags')
        
        # Get all incoming messages
        messages = MessageLog.query.filter_by(direction='incoming').order_by(MessageLog.timestamp).all()
        
        if not messages:
            flash('No incoming messages found to retag.', 'info')
            return redirect('/tags')
        
        retagged_count = 0
        error_count = 0
        
        for msg in messages:
            try:
                # Analyze message with current tag rules from database
                # analyze_response() automatically loads tag rules from the database
                analysis = gemini_service.analyze_response(msg.raw_text)
                
                # Update tags
                if 'tags' in analysis and analysis['tags']:
                    msg.llm_tags = analysis['tags']
                    msg.llm_sentiment = analysis.get('sentiment', 'neutral')
                    msg.llm_confidence = analysis.get('confidence', 0.0)
                    retagged_count += 1
                    
            except Exception as e:
                logger.error(f"Error retagging message {msg.id}: {e}")
                error_count += 1
                continue
        
        db.session.commit()
        
        flash(f'Successfully retagged {retagged_count} messages. {error_count} errors encountered.', 'success' if error_count == 0 else 'warning')
        return redirect('/tags')
        
    except Exception as e:
        logger.error(f"Error retagging messages: {e}")
        db.session.rollback()
        flash(f'Error retagging messages: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/retag-user/<int:user_id>', methods=['POST'])
@login_required
def retag_user_messages(user_id):
    """Re-run AI tagging on all messages from a specific user"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied. Only super admins can manage tags.'}), 403
    try:
        from models import MessageLog, TagRule, User, db
        
        # Get user info
        user = User.query.get_or_404(user_id)
        
        # Check if we have active tag rules
        active_rules = TagRule.query.filter_by(is_active=True).count()
        if active_rules == 0:
            flash('No active tag rules found. Please initialize tags first.', 'warning')
            return redirect(f'/chat/{user_id}')
        
        # Get all incoming messages from this user
        messages = MessageLog.query.filter_by(
            user_id=user_id,
            direction='incoming'
        ).order_by(MessageLog.timestamp).all()
        
        if not messages:
            flash(f'No incoming messages found for {user.phone_number}.', 'info')
            return redirect(f'/chat/{user_id}')
        
        retagged_count = 0
        error_count = 0
        
        for msg in messages:
            try:
                # Analyze message with current tag rules from database
                analysis = gemini_service.analyze_response(msg.raw_text)
                
                # Update tags
                if 'tags' in analysis and analysis['tags']:
                    msg.llm_tags = analysis['tags']
                    msg.llm_sentiment = analysis.get('sentiment', 'neutral')
                    msg.llm_confidence = analysis.get('confidence', 0.0)
                    retagged_count += 1
                    
            except Exception as e:
                logger.error(f"Error retagging message {msg.id}: {e}")
                error_count += 1
                continue
        
        db.session.commit()
        
        flash(f'Successfully retagged {retagged_count} messages for {user.phone_number}. {error_count} errors encountered.', 'success' if error_count == 0 else 'warning')
        return redirect(f'/chat/{user_id}')
        
    except Exception as e:
        logger.error(f"Error retagging user messages: {e}")
        db.session.rollback()
        flash(f'Error retagging messages: {str(e)}', 'error')
        return redirect('/chat-management')

@app.route('/tags/initialize-other-tags', methods=['POST'])
@login_required
def initialize_other_tags():
    """Initialize Other Tags parent tag with operational/administrative sub-tags"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied. Only super admins can manage tags.'}), 403
    try:
        from models import TagRule, db
        
        # Check if Other Tags already exists
        existing_other = TagRule.query.filter_by(tag_name='Other Tags').first()
        
        if existing_other:
            flash('Other Tags already exist. Delete them first if you want to reinitialize.', 'warning')
            return redirect('/tags')
        
        # Create Other Tags main tag
        other_tags = TagRule(
            tag_name='Other Tags',
            description='Operational and administrative tags for user engagement tracking and support management',
            ai_evaluation_rule='This is a parent tag for organizing operational tags. Apply relevant sub-tags when users need support, show disengagement, or require administrative actions.',
            priority=5,
            is_active=True,
            parent_id=None
        )
        db.session.add(other_tags)
        db.session.flush()
        
        # Create Other Tags sub-tags
        other_subtags = [
            {
                'name': 'Human',
                'description': 'User requested or needs human connection/support',
                'rule': 'Apply this tag when the user explicitly requests to speak with a human, or when sensitive topics require human intervention.'
            },
            {
                'name': 'Support',
                'description': 'User needs additional support or guidance',
                'rule': 'Apply this tag when the user expresses need for help, guidance, or additional support beyond the daily content.'
            },
            {
                'name': 'Blocked',
                'description': 'User has blocked the bot or been blocked',
                'rule': 'Apply this tag when the user has blocked the bot or when communication has been blocked due to policy violations.'
            },
            {
                'name': 'Already in church',
                'description': 'User was already attending church when chat started',
                'rule': 'Apply this tag when the user indicates they are already part of a church community or actively attending services.'
            },
            {
                'name': 'Not connected',
                'description': 'User not successfully connected to partner/pioneer/church',
                'rule': 'Apply this tag when attempts to connect the user with local church partners, pioneers, or communities have been unsuccessful.'
            },
            {
                'name': 'Not genuine',
                'description': 'User being inappropriate, testing, or spamming',
                'rule': 'Apply this tag when the user displays inappropriate behavior, appears to be testing the system, or is sending spam messages.'
            },
            {
                'name': 'No response',
                'description': 'User never responded after requesting human contact',
                'rule': 'Apply this tag when the user requested human connection but has not responded to follow-up messages or contact attempts.'
            }
        ]
        
        for subtag_data in other_subtags:
            subtag = TagRule(
                tag_name=subtag_data['name'],
                description=subtag_data['description'],
                ai_evaluation_rule=subtag_data['rule'],
                priority=5,
                is_active=True,
                parent_id=other_tags.id
            )
            db.session.add(subtag)
        
        db.session.commit()
        
        flash('Other Tags initialized successfully! Created 7 operational/administrative sub-tags.', 'success')
        return redirect('/tags')
        
    except Exception as e:
        logger.error(f"Error initializing other tags: {e}")
        db.session.rollback()
        flash(f'Error initializing other tags: {str(e)}', 'error')
        return redirect('/tags')

@app.route('/tags/initialize', methods=['POST'])
@login_required
def initialize_predefined_tags():
    """Initialize predefined tag structure"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied. Only super admins can manage tags.'}), 403
    try:
        from models import TagRule, db
        
        # Check if tags already exist
        existing_count = TagRule.query.filter(
            TagRule.tag_name.in_(['Faith Journey', 'Delivered Daily Content'])
        ).count()
        
        if existing_count > 0:
            flash('Predefined tags already exist. Delete them first if you want to reinitialize.', 'warning')
            return redirect('/tags')
        
        # Create Faith Journey main tag
        faith_journey = TagRule(
            tag_name='Faith Journey',
            description='Main category for spiritual milestones and faith development tracking',
            ai_evaluation_rule='This is a parent tag for organizing faith-related sub-tags. Apply relevant sub-tags when users show spiritual progress.',
            priority=10,
            is_active=True,
            parent_id=None
        )
        db.session.add(faith_journey)
        db.session.flush()
        
        # Create Faith Journey sub-tags
        faith_subtags = [
            {
                'name': 'Bible Exposure',
                'description': 'User has been exposed to Bible story or teaching',
                'rule': 'Apply this tag when the user acknowledges reading or being exposed to Bible content, stories, or teachings.'
            },
            {
                'name': 'Christian Learning',
                'description': 'User engaged with material to help them follow Jesus',
                'rule': 'Apply this tag when the user shows engagement with Christian teachings or materials designed to help them understand and follow Jesus.'
            },
            {
                'name': 'Bible Engagement',
                'description': 'User indicates reading/engaging with Bible for spiritual growth',
                'rule': 'Apply this tag when the user actively reads or engages with the Bible for personal spiritual growth and development.'
            },
            {
                'name': 'Salvation Prayer',
                'description': 'User prayed (or indicated they prayed) to follow Jesus',
                'rule': 'Apply this tag when the user has prayed or indicated they have prayed a prayer to accept Jesus and follow Him.'
            },
            {
                'name': 'Gospel Presentation',
                'description': 'User responds to substantial Gospel explanation',
                'rule': 'Apply this tag when the user responds to or acknowledges a substantial explanation of the Gospel message.'
            },
            {
                'name': 'Prayer',
                'description': 'User indicates they have prayed, are praying, or request prayer',
                'rule': 'Apply this tag when the user mentions praying, asks for prayer, or indicates they are engaging in prayer.'
            },
            {
                'name': 'Introduction to Jesus',
                'description': 'User acknowledges reading/watching content about Jesus',
                'rule': 'Apply this tag when the user acknowledges exposure to content introducing them to Jesus Christ and His teachings.'
            },
            {
                'name': 'Holy Spirit Empowerment',
                'description': 'User shows evidence of Holy Spirit work (fruits/gifts)',
                'rule': 'Apply this tag when the user demonstrates evidence of the Holy Spirit working in their life through spiritual fruits or gifts.'
            }
        ]
        
        for subtag_data in faith_subtags:
            subtag = TagRule(
                tag_name=subtag_data['name'],
                description=subtag_data['description'],
                ai_evaluation_rule=subtag_data['rule'],
                priority=5,
                is_active=True,
                parent_id=faith_journey.id
            )
            db.session.add(subtag)
        
        # Create Delivered Daily Content main tag
        daily_content = TagRule(
            tag_name='Delivered Daily Content',
            description='Tracks which daily content has been delivered to users',
            ai_evaluation_rule='This is a parent tag for organizing daily content delivery tracking. Apply day-specific sub-tags when content is delivered.',
            priority=10,
            is_active=True,
            parent_id=None
        )
        db.session.add(daily_content)
        db.session.flush()
        
        # Create Day 1-90 sub-tags
        for day in range(1, 91):
            day_tag = TagRule(
                tag_name=f'Day {day}',
                description=f'Content delivered for Day {day} of the journey',
                ai_evaluation_rule=f'Apply this tag when Day {day} content has been successfully delivered to the user.',
                priority=0,
                is_active=True,
                parent_id=daily_content.id
            )
            db.session.add(day_tag)
        
        db.session.commit()
        
        flash('Predefined tag structure initialized successfully! Created Faith Journey (8 sub-tags) and Delivered Daily Content (90 day tags).', 'success')
        return redirect('/tags')
        
    except Exception as e:
        logger.error(f"Error initializing tags: {e}")
        db.session.rollback()
        flash(f'Error initializing tags: {str(e)}', 'error')
        return redirect('/tags')

# Chat Management Routes
@app.route('/chat-management')
@login_required
def chat_management_page():
    """Bot selection page for chat management"""
    # Get bots based on user role
    if current_user.role == 'super_admin':
        bots = db_manager.get_all_bots()
    else:
        bots = db_manager.get_bots_by_creator(current_user.id)
    
    return render_template('bot_selection_chat.html', bots=bots)

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
        # Check for image content
        if content_dict.get('media_type') == 'image' and content_dict.get('image_filename'):
            # Test photo sending
            # Build image URL from filename
            media_url = f"/static/uploads/images/{content_dict.get('image_filename')}"
            result = telegram_service.send_photo('test123', media_url)
            
            return jsonify({
                'success': True,
                'media_url': media_url,
                'media_type': content_dict.get('media_type'),
                'file_exists': content_dict.get('image_filename') is not None,
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
        if user and user.check_password(form.password.data) and user.active:
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
        user.active = form.active.data
        db.session.commit()
        flash(f'User {user.username} has been updated successfully!', 'success')
        return redirect(url_for('user_management'))
    
    return render_template('auth/edit_user.html', form=form, user=user)


@app.route('/cms/content/edit/<int:content_id>', methods=['POST'])
@login_required
def cms_edit_content(content_id):
    """Handle CMS content editing with file uploads"""
    try:
        # Get the existing content to determine bot_id for proper file isolation
        existing_content = db_manager.get_content_by_id(content_id)
        if not existing_content:
            return jsonify({'success': False, 'error': 'Content not found'}), 404
        
        bot_id = existing_content.bot_id
        
        # Handle file uploads using the proper validation system with bot isolation
        image_filename = None
        video_filename = None
        audio_filename = None
        
        # Process image upload
        if 'image_file' in request.files:
            image_file = request.files['image_file']
            if image_file and image_file.filename:
                upload_result = validate_and_upload_with_prevention(image_file, 'image', bot_id)
                if upload_result['success']:
                    image_filename = upload_result['filename']
                    logger.info(f"✅ Image uploaded for content {content_id}: {image_filename}")
                else:
                    logger.error(f"❌ Image upload failed: {upload_result['errors']}")
                    return jsonify({'success': False, 'error': f"Image upload failed: {', '.join(upload_result['errors'])}"}), 400
        
        # Process video upload
        if 'video_file' in request.files:
            video_file = request.files['video_file']
            if video_file and video_file.filename:
                upload_result = validate_and_upload_with_prevention(video_file, 'video', bot_id)
                if upload_result['success']:
                    video_filename = upload_result['filename']
                    logger.info(f"✅ Video uploaded for content {content_id}: {video_filename}")
                else:
                    logger.error(f"❌ Video upload failed: {upload_result['errors']}")
                    return jsonify({'success': False, 'error': f"Video upload failed: {', '.join(upload_result['errors'])}"}), 400
        
        # Process audio upload
        if 'audio_file' in request.files:
            audio_file = request.files['audio_file']
            if audio_file and audio_file.filename:
                upload_result = validate_and_upload_with_prevention(audio_file, 'audio', bot_id)
                if upload_result['success']:
                    audio_filename = upload_result['filename']
                    logger.info(f"✅ Audio uploaded for content {content_id}: {audio_filename}")
                else:
                    logger.error(f"❌ Audio upload failed: {upload_result['errors']}")
                    return jsonify({'success': False, 'error': f"Audio upload failed: {', '.join(upload_result['errors'])}"}), 400
        
        # Debug: Log all form data received
        logger.info(f"🔍 Content edit debug for ID {content_id}:")
        logger.info(f"🔍 Form data keys: {list(request.form.keys())}")
        for key, value in request.form.items():
            logger.info(f"🔍   {key}: {value}")
        
        # Handle selection of existing files (not uploads) - only if no new upload was processed
        if not image_filename and 'selected_image' in request.form:
            selected_image = request.form.get('selected_image', '').strip()
            logger.info(f"🔍 Processing selected_image: '{selected_image}'")
            if selected_image:
                # Validate that the selected image file exists
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(selected_image, 'image'):
                    image_filename = selected_image
                    logger.info(f"✅ Existing image selected for content {content_id}: {image_filename}")
                else:
                    logger.warning(f"❌ Selected image file does not exist: {selected_image}")
        
        if not video_filename and 'selected_video' in request.form:
            selected_video = request.form.get('selected_video', '').strip()
            logger.info(f"🔍 Processing selected_video: '{selected_video}'")
            if selected_video:
                # Validate that the selected video file exists
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(selected_video, 'video'):
                    video_filename = selected_video
                    logger.info(f"✅ Existing video selected for content {content_id}: {video_filename}")
                else:
                    logger.warning(f"❌ Selected video file does not exist: {selected_video}")
            else:
                logger.info(f"🔍 selected_video field is empty")
        else:
            if video_filename:
                logger.info(f"🔍 video_filename already set from upload: {video_filename}")
            else:
                logger.info(f"🔍 selected_video not in form data")
        
        if not audio_filename and 'selected_audio' in request.form:
            selected_audio = request.form.get('selected_audio', '').strip()
            logger.info(f"🔍 Processing selected_audio: '{selected_audio}'")
            if selected_audio:
                # Validate that the selected audio file exists
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(selected_audio, 'audio'):
                    audio_filename = selected_audio
                    logger.info(f"✅ Existing audio selected for content {content_id}: {audio_filename}")
                else:
                    logger.warning(f"❌ Selected audio file does not exist: {selected_audio}")
        
        logger.info(f"🔍 Final media filenames - image: {image_filename}, video: {video_filename}, audio: {audio_filename}")
        
        # Parse form data
        title = request.form.get('title')
        content = request.form.get('content')
        reflection_question = request.form.get('reflection_question')
        media_type = request.form.get('media_type', 'text')
        is_active = request.form.get('is_active') == 'true'
        
        # Get confirmation button customization fields
        confirmation_message = request.form.get('confirmation_message', '').strip() or None
        yes_button_text = request.form.get('yes_button_text', '').strip() or None
        no_button_text = request.form.get('no_button_text', '').strip() or None
        
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
            content_type=request.form.get('content_type', 'daily'),
            confirmation_message=confirmation_message,
            yes_button_text=yes_button_text,
            no_button_text=no_button_text
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

@app.route('/api/media/browse')
@login_required
def api_media_browse():
    """API endpoint to browse available media files"""
    try:
        from media_file_browser import get_available_media_files
        
        # Get query parameters
        media_type = request.args.get('media_type', None)
        bot_id = request.args.get('bot_id', None, type=int)
        
        # Get available files
        files = get_available_media_files(media_type=media_type, bot_id=bot_id)
        
        return jsonify({
            'success': True,
            'files': files,
            'total': len(files)
        })
        
    except Exception as e:
        logger.error(f"Error browsing media files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# File upload helper functions
def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, subfolder, allowed_extensions, bot_id=None):
    """Save uploaded file and return filename with optional bot isolation"""
    if file and allowed_file(file.filename, allowed_extensions):
        # Generate unique filename with bot isolation
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        
        if bot_id:
            # Bot-specific filename to prevent conflicts between bots
            unique_filename = f"bot{bot_id}_{name}_{uuid.uuid4().hex[:8]}{ext}"
        else:
            # Legacy format for backward compatibility
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
        video_filename = None
        audio_filename = None
        youtube_url = None
        
        if form.media_type.data == 'image':
            # Check if using existing file or uploading new
            existing_image = request.form.get('existing_image_file')
            if existing_image:
                # Validate existing file exists
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(existing_image, 'image'):
                    image_filename = existing_image
                    logger.info(f"✅ Using existing image file: {image_filename}")
                else:
                    logger.error(f"❌ Selected existing image file not found: {existing_image}")
                    flash("Selected image file not found. Please choose another or upload new.", 'danger')
            elif form.image_file.data:
                # Get bot_id from form if available (for new bot content creation)
                bot_id = getattr(form, 'bot_id', None)
                if hasattr(form.bot_id, 'data'):
                    bot_id = form.bot_id.data
                
                # Use universal prevention system for upload validation
                from universal_media_prevention_system import validate_and_upload_with_prevention
                upload_result = validate_and_upload_with_prevention(form.image_file.data, 'image', bot_id or 1)
                
                if upload_result['success']:
                    image_filename = upload_result['filename']
                    logger.info(f"✅ New content image upload successful: {image_filename}")
                else:
                    logger.error(f"❌ New content image upload failed: {upload_result['errors']}")
                    flash(f"Image upload failed: {'; '.join(upload_result['errors'])}", 'danger')
        
        if form.media_type.data == 'audio':
            # Check if using existing file or uploading new
            existing_audio = request.form.get('existing_audio_file')
            if existing_audio:
                # Validate existing file exists
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(existing_audio, 'audio'):
                    audio_filename = existing_audio
                    logger.info(f"✅ Using existing audio file: {audio_filename}")
                else:
                    logger.error(f"❌ Selected existing audio file not found: {existing_audio}")
                    flash("Selected audio file not found. Please choose another or upload new.", 'danger')
            elif form.audio_file.data:
                # Get bot_id from form if available (for new bot content creation)
                bot_id = getattr(form, 'bot_id', None)
                if hasattr(form.bot_id, 'data'):
                    bot_id = form.bot_id.data
                
                # Use universal prevention system for upload validation
                from universal_media_prevention_system import validate_and_upload_with_prevention
                upload_result = validate_and_upload_with_prevention(form.audio_file.data, 'audio', bot_id or 1)
                
                if upload_result['success']:
                    audio_filename = upload_result['filename']
                    logger.info(f"✅ New content audio upload successful: {audio_filename}")
                else:
                    logger.error(f"❌ New content audio upload failed: {upload_result['errors']}")
                    flash(f"Audio upload failed: {'; '.join(upload_result['errors'])}", 'danger')
        
        if form.media_type.data == 'video':
            # Check if using existing video file, uploading new, or using YouTube URL
            existing_video = request.form.get('existing_video_file')
            if existing_video:
                # Use existing video file
                from media_file_browser import validate_media_file_exists
                if validate_media_file_exists(existing_video, 'video'):
                    video_filename = existing_video
                    logger.info(f"✅ Using existing video file: {video_filename}")
                else:
                    logger.error(f"❌ Selected existing video file not found: {existing_video}")
                    flash("Selected video file not found. Please choose another or upload new.", 'danger')
            elif 'video_file' in request.files and request.files['video_file'].filename:
                # Upload new video file
                video_file = request.files['video_file']
                bot_id = getattr(form, 'bot_id', None)
                if hasattr(form.bot_id, 'data'):
                    bot_id = form.bot_id.data
                
                # Use universal prevention system for upload validation
                from universal_media_prevention_system import validate_and_upload_with_prevention
                upload_result = validate_and_upload_with_prevention(video_file, 'video', bot_id or 1)
                
                if upload_result['success']:
                    video_filename = upload_result['filename']
                    logger.info(f"✅ New content video upload successful: {video_filename}")
                else:
                    logger.error(f"❌ New content video upload failed: {upload_result['errors']}")
                    flash(f"Video upload failed: {'; '.join(upload_result['errors'])}", 'danger')
            elif form.youtube_url.data:
                # Use YouTube URL
                youtube_url = form.youtube_url.data.strip()
                logger.info(f"✅ Using YouTube URL: {youtube_url}")
        
        # Process tags
        tags = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()] if form.tags.data else []
        
        # SERVER-SIDE MEDIA TYPE NORMALIZATION - Fix for type persistence bug
        actual_media_type = form.media_type.data
        if video_filename or youtube_url:
            actual_media_type = 'video'
            # Clear conflicting media files to prevent mixed-state records
            image_filename = None
            audio_filename = None
        elif image_filename:
            actual_media_type = 'image'
            # Clear conflicting media files
            video_filename = None
            audio_filename = None
            youtube_url = None
        elif audio_filename:
            actual_media_type = 'audio'
            # Clear conflicting media files
            image_filename = None
            video_filename = None
            youtube_url = None
        else:
            actual_media_type = 'text'
            # Clear all media files for text-only content
            image_filename = None
            video_filename = None
            audio_filename = None
            youtube_url = None
            
        logger.info(f"✅ Server-side media type normalization: {form.media_type.data} → {actual_media_type}")
        
        content_id = db_manager.create_content(
            day_number=form.day_number.data,
            title=form.title.data,
            content=form.content.data,
            reflection_question=form.reflection_question.data,
            tags=tags,
            media_type=actual_media_type,
            image_filename=image_filename,
            video_filename=video_filename,
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
            
            # Validate existing media files and clean up broken references
            if media_type == 'image' and image_filename:
                image_path = os.path.join('static/uploads/images', image_filename)
                if not os.path.exists(image_path):
                    logger.warning(f"Existing image file not found: {image_path}, resetting to text-only")
                    image_filename = None
                    media_type = 'text'
                    
            if media_type == 'audio' and audio_filename:
                audio_path = os.path.join('static/uploads/audio', audio_filename)
                if not os.path.exists(audio_path):
                    logger.warning(f"Existing audio file not found: {audio_path}, resetting to text-only")
                    audio_filename = None
                    media_type = 'text'
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
            
            # Handle image files - check if using existing or uploading new
            if media_type == 'image':
                existing_image = request.form.get('existing_image_file')
                if existing_image:
                    # Use existing file
                    from media_file_browser import validate_media_file_exists
                    if validate_media_file_exists(existing_image, 'image'):
                        image_filename = existing_image
                        logger.info(f"✅ Using existing image file: {image_filename}")
                    else:
                        logger.error(f"❌ Selected existing image file not found: {existing_image}")
                elif 'image_file' in request.files:
                    file = request.files['image_file']
                    if file and file.filename:
                        # Use universal prevention system for upload validation
                        from universal_media_prevention_system import validate_and_upload_with_prevention
                        upload_result = validate_and_upload_with_prevention(file, 'image', content.bot_id)
                        
                        if upload_result['success']:
                            # Remove old image file if upload successful
                            if image_filename and image_filename != upload_result['filename']:
                                old_path = os.path.join('static/uploads/images', image_filename)
                                try:
                                    if os.path.exists(old_path):
                                        os.remove(old_path)
                                        logger.info(f"Removed old image: {image_filename}")
                                except Exception as e:
                                    logger.warning(f"Could not remove old image: {e}")
                            
                            image_filename = upload_result['filename']
                            logger.info(f"✅ Image upload successful for Bot {content.bot_id}: {image_filename}")
                        else:
                            logger.error(f"❌ Image upload failed for Bot {content.bot_id}: {upload_result['errors']}")
                            # Keep existing filename if upload fails
            
            # Handle audio files - check if using existing or uploading new
            if media_type == 'audio':
                existing_audio = request.form.get('existing_audio_file')
                if existing_audio:
                    # Use existing file
                    from media_file_browser import validate_media_file_exists
                    if validate_media_file_exists(existing_audio, 'audio'):
                        audio_filename = existing_audio
                        logger.info(f"✅ Using existing audio file: {audio_filename}")
                    else:
                        logger.error(f"❌ Selected existing audio file not found: {existing_audio}")
                elif 'audio_file' in request.files:
                    file = request.files['audio_file']
                    if file and file.filename:
                        # Use universal prevention system for upload validation
                        from universal_media_prevention_system import validate_and_upload_with_prevention
                        upload_result = validate_and_upload_with_prevention(file, 'audio', content.bot_id)
                        
                        if upload_result['success']:
                            # Remove old audio file if upload successful
                            if audio_filename and audio_filename != upload_result['filename']:
                                old_path = os.path.join('static/uploads/audio', audio_filename)
                                try:
                                    if os.path.exists(old_path):
                                        os.remove(old_path)
                                        logger.info(f"Removed old audio: {audio_filename}")
                                except Exception as e:
                                    logger.warning(f"Could not remove old audio: {e}")
                            
                            audio_filename = upload_result['filename']
                            logger.info(f"✅ Audio upload successful for Bot {content.bot_id}: {audio_filename}")
                        else:
                            logger.error(f"❌ Audio upload failed for Bot {content.bot_id}: {upload_result['errors']}")
                            # Keep existing filename if upload fails
            
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
            
            # Get confirmation button customization fields
            confirmation_message = request.form.get('confirmation_message', '').strip() or None
            yes_button_text = request.form.get('yes_button_text', '').strip() or None
            no_button_text = request.form.get('no_button_text', '').strip() or None
            
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
                is_active=is_active,
                confirmation_message=confirmation_message,
                yes_button_text=yes_button_text,
                no_button_text=no_button_text
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

# AI Content Generation Routes
@app.route('/cms/ai-content-generation', methods=['GET', 'POST'])
@login_required
def ai_content_generation():
    """AI Content Generation setup page (global)"""
    form = AIContentGenerationForm()
    
    if form.validate_on_submit():
        try:
            from ai_content_generator import AIContentGenerator, ContentGenerationRequest
            
            # Create content generation request
            request = ContentGenerationRequest(
                target_audience=form.target_audience.data or "General spiritual seekers",
                audience_language=form.audience_language.data or "English",
                audience_religion=form.audience_religion.data or "Mixed backgrounds",
                audience_age_group=form.audience_age_group.data or "Adults",
                content_prompt=form.content_generation_prompt.data,
                journey_duration=int(form.content_generation_duration.data)
            )
            
            # Generate content using AI
            logger.info(f"Starting AI content generation via CMS (global)")
            generator = AIContentGenerator()
            daily_contents = generator.generate_journey_content(request)
            
            # Validate generated content
            if generator.validate_generated_content(daily_contents, request.journey_duration):
                # Save generated content to database (global content, no bot_id)
                for daily_content in daily_contents:
                    content = Content()
                    content.day_number = daily_content.day_number
                    content.content = daily_content.content
                    content.media_type = 'text'
                    # Set media fields to None for text content
                    content.image_filename = None
                    content.video_filename = None
                    content.youtube_url = None
                    content.audio_filename = None
                    content.reflection_question = daily_content.reflection_question
                    content.title = daily_content.title
                    content.is_active = True
                    content.tags = daily_content.tags or []
                    
                    db.session.add(content)
                
                db.session.commit()
                flash(f'✅ AI generated {len(daily_contents)} days of content successfully!', 'success')
                logger.info(f"Successfully saved {len(daily_contents)} days of AI-generated content via CMS (global)")
                return redirect(url_for('cms'))
            else:
                flash('⚠️ AI content validation failed - please review and add content manually', 'warning')
                
        except Exception as e:
            logger.error(f"AI content generation failed via CMS (global): {e}")
            flash(f'❌ AI content generation failed: {str(e)}', 'danger')
    
    return render_template('ai_content_generation.html', form=form, user=current_user, bot=None)

@app.route('/bots/<int:bot_id>/ai-content-generation', methods=['GET', 'POST'])
@login_required  
def bot_ai_content_generation(bot_id):
    """AI Content Generation setup page (bot-specific) - Day by day approach"""
    # Clear any existing timeout for this long-running operation
    signal.alarm(0)
    
    bot = Bot.query.get_or_404(bot_id)
    form = AIContentGenerationForm()
    
    if form.validate_on_submit():
        try:
            # Start day-by-day generation process
            journey_duration = int(form.content_generation_duration.data)
            
            # Store generation settings in session for day-by-day process
            session['ai_generation'] = {
                'bot_id': bot_id,
                'journey_duration': journey_duration,
                'target_audience': form.target_audience.data or "General spiritual seekers",
                'audience_language': form.audience_language.data or "English", 
                'audience_religion': form.audience_religion.data or "Mixed backgrounds",
                'audience_age_group': form.audience_age_group.data or "Adults",
                'content_prompt': form.content_generation_prompt.data or "Create meaningful daily content",
                'current_day': 1
            }
            
            logger.info(f"🎯 Starting day-by-day AI generation for bot {bot_id} with {journey_duration} days")
            
            # Redirect to day-by-day generation
            return redirect(url_for('bot_ai_content_generation_day_by_day', bot_id=bot_id))
            
        except Exception as e:
            logger.error(f"Error starting day-by-day generation for bot {bot_id}: {e}")
            flash(f'❌ Error starting AI generation: {str(e)}', 'danger')
            return redirect(url_for('bot_ai_content_generation', bot_id=bot_id))
    
    # Check if bot has existing content to show warning
    existing_content_count = Content.query.filter_by(bot_id=bot_id).count()
    has_existing_content = existing_content_count > 0
    
    return render_template('ai_content_generation.html', 
                         form=form, 
                         user=current_user, 
                         bot=bot,
                         existing_content_count=existing_content_count,
                         has_existing_content=has_existing_content)

@app.route('/bots/<int:bot_id>/ai-content-generation/day-by-day', methods=['GET', 'POST'])
@login_required
def bot_ai_content_generation_day_by_day(bot_id):
    """Day-by-day AI content generation interface"""
    bot = Bot.query.get_or_404(bot_id)
    
    # Check if we have generation settings in session
    if 'ai_generation' not in session or session['ai_generation']['bot_id'] != bot_id:
        flash('Please start the AI generation process first.', 'warning')
        return redirect(url_for('bot_ai_content_generation', bot_id=bot_id))
    
    generation_settings = session['ai_generation']
    current_day = generation_settings['current_day']
    total_days = generation_settings['journey_duration']
    
    generated_content = None
    error_message = None
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'generate':
            # Generate content for current day
            try:
                from ai_content_generator import AIContentGenerator, ContentGenerationRequest
                
                # Create request for single day
                content_request = ContentGenerationRequest(
                    target_audience=generation_settings['target_audience'],
                    audience_language=generation_settings['audience_language'],
                    audience_religion=generation_settings['audience_religion'],
                    audience_age_group=generation_settings['audience_age_group'],
                    content_prompt=generation_settings['content_prompt'],
                    journey_duration=1  # Generate only 1 day
                )
                
                generator = AIContentGenerator()
                daily_contents = generator.generate_journey_content(content_request)
                
                if daily_contents:
                    generated_content = daily_contents[0]
                    # Adjust day number to current day
                    generated_content.day_number = current_day
                    
            except Exception as e:
                error_message = f"Failed to generate content: {str(e)}"
                logger.error(f"Day-by-day generation error: {e}")
        
        elif action == 'save':
            # Save the current day's content and move to next day
            try:
                # Get content data from form
                title = request.form.get('title')
                content_text = request.form.get('content')
                reflection_question = request.form.get('reflection_question')
                tags = request.form.get('tags', '').split(',') if request.form.get('tags') else []
                
                # Check if content already exists for this day
                existing = Content.query.filter_by(bot_id=bot_id, day_number=current_day).first()
                if existing:
                    db.session.delete(existing)
                
                # Create new content
                content = Content()
                content.bot_id = bot_id
                content.day_number = current_day
                content.title = title
                content.content = content_text
                content.reflection_question = reflection_question
                content.tags = tags
                content.media_type = 'text'
                content.image_filename = None
                content.video_filename = None
                content.youtube_url = None
                content.audio_filename = None
                content.is_active = True
                
                db.session.add(content)
                db.session.commit()
                
                flash(f'✅ Day {current_day} content saved successfully!', 'success')
                
                # Move to next day
                if current_day < total_days:
                    session['ai_generation']['current_day'] = current_day + 1
                    return redirect(url_for('bot_ai_content_generation_day_by_day', bot_id=bot_id))
                else:
                    # All days completed
                    session.pop('ai_generation', None)
                    flash(f'🎉 All {total_days} days of content generated successfully!', 'success')
                    return redirect(url_for('bot_content_management', bot_id=bot_id))
                    
            except Exception as e:
                error_message = f"Failed to save content: {str(e)}"
                logger.error(f"Day-by-day save error: {e}")
                db.session.rollback()
        
        elif action == 'skip':
            # Skip to next day without saving
            if current_day < total_days:
                session['ai_generation']['current_day'] = current_day + 1
                return redirect(url_for('bot_ai_content_generation_day_by_day', bot_id=bot_id))
            else:
                session.pop('ai_generation', None)
                return redirect(url_for('bot_content_management', bot_id=bot_id))
    
    return render_template('ai_content_generation_day_by_day.html',
                         bot=bot,
                         current_day=current_day,
                         total_days=total_days,
                         generated_content=generated_content,
                         error_message=error_message,
                         generation_settings=generation_settings,
                         user=current_user)
    

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
    
    # Initialize Universal Media Prevention System
    try:
        from universal_media_prevention_system import initialize_prevention_system
        prevention_system = initialize_prevention_system(app)
        logger.info("✅ Universal Media Prevention System initialized")
    except Exception as e:
        logger.error(f"Failed to initialize prevention system: {e}")
    
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

# Start background scheduler with database-based lock (prevent multiple schedulers across all workers)
def try_acquire_scheduler_lock():
    """Try to acquire a database lock for the scheduler. Returns True if successful."""
    try:
        from models import SystemSettings, db
        import datetime
        
        lock_key = "scheduler_lock"
        now = datetime.datetime.utcnow()
        
        # Check if lock exists and is still valid (within last 30 seconds)
        lock = SystemSettings.query.filter_by(key=lock_key).first()
        
        if lock:
            lock_time = datetime.datetime.fromisoformat(lock.value)
            age_seconds = (now - lock_time).total_seconds()
            
            # If lock is fresh (< 30 seconds old), another worker owns it
            if age_seconds < 30:
                logger.info(f"❌ Scheduler lock held by another worker (age: {age_seconds:.1f}s)")
                return False
            else:
                # Lock is stale, take it over
                logger.warning(f"⚠️ Taking over stale scheduler lock (age: {age_seconds:.1f}s)")
                lock.value = now.isoformat()
                lock.updated_at = now
        else:
            # No lock exists, create it
            lock = SystemSettings()
            lock.key = lock_key
            lock.value = now.isoformat()
            lock.description = "Scheduler lock - prevents multiple scheduler instances"
            db.session.add(lock)
        
        db.session.commit()
        logger.info("✅ Scheduler lock acquired successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to acquire scheduler lock: {e}")
        return False

# Start scheduler with duplicate prevention handled by the scheduler itself
try:
    logger.info("🚀 Starting scheduler (duplicate prevention via in-scheduler checks)")
    start_scheduler()
    logger.info("✅ Scheduler initialized successfully")
except Exception as e:
    logger.error(f"❌ CRITICAL: Failed to initialize scheduler: {e}", exc_info=True)

if __name__ == '__main__':
    # Start Flask app only when running directly (development mode)
    app.run(host='0.0.0.0', port=5000, debug=True)
