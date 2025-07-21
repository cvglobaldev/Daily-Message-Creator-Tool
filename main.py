import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from models import db, User, Content, MessageLog
from db_manager import DatabaseManager
from services import WhatsAppService, GeminiService
from scheduler import ContentScheduler
import threading
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "faith-journey-secret-key")

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
gemini_service = GeminiService()
scheduler = ContentScheduler(db_manager, whatsapp_service, gemini_service)

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
                current_time = datetime.now().strftime("%H:%M")
                # Run daily content delivery at 8:00 AM
                if current_time == "08:00":
                    logger.info("Running daily content scheduler...")
                    scheduler.send_daily_content()
                    # Sleep for 60 seconds to avoid running multiple times in the same minute
                    time.sleep(60)
                else:
                    # Check every 30 seconds
                    time.sleep(30)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time.sleep(60)
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("Background scheduler started")

@app.route('/')
def dashboard():
    """Simple dashboard to monitor the system"""
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
                             human_handoffs=human_handoff_data)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        return f"Dashboard error: {e}", 500

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
                    process_incoming_message(phone_number, message_text)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {e}")
        return jsonify({"error": str(e)}), 500

def process_incoming_message(phone_number: str, message_text: str):
    """Process incoming message from user"""
    try:
        logger.info(f"Processing message from {phone_number}: {message_text}")
        
        # Normalize phone number
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number
        
        message_lower = message_text.lower().strip()
        
        # Handle commands
        if message_lower == 'start':
            handle_start_command(phone_number)
            return
        
        elif message_lower == 'stop':
            handle_stop_command(phone_number)
            return
        
        elif message_lower == 'help':
            handle_help_command(phone_number)
            return
        
        # Check for human handoff triggers
        if any(keyword in message_lower for keyword in HUMAN_HANDOFF_KEYWORDS):
            handle_human_handoff(phone_number, message_text)
            return
        
        # Handle regular response (likely to a reflection question)
        handle_reflection_response(phone_number, message_text)
        
    except Exception as e:
        logger.error(f"Error processing message from {phone_number}: {e}")
        # Send error message to user
        whatsapp_service.send_message(
            phone_number, 
            "Sorry, there was an error processing your message. Please try again or type HELP for assistance."
        )

def handle_start_command(phone_number: str):
    """Handle START command - onboard new user"""
    try:
        # Check if user already exists
        existing_user = db_manager.get_user_by_phone(phone_number)
        
        if existing_user and existing_user.status == 'active':
            whatsapp_service.send_message(
                phone_number,
                "You're already on your faith journey! You'll receive your next content at 8:00 AM daily. Type HELP if you need assistance."
            )
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
        welcome_message = ("Welcome to your Faith Journey! 🌟\n\n"
                          "You'll receive daily content for the next 30 days at 8:00 AM. "
                          "After each piece of content, I'll ask you a simple reflection question.\n\n"
                          "Let's start with Day 1 content right now!")
        
        whatsapp_service.send_message(phone_number, welcome_message)
        
        # Send Day 1 content immediately
        scheduler.send_content_to_user(phone_number)
        
        logger.info(f"User {phone_number} successfully onboarded")
        
    except Exception as e:
        logger.error(f"Error handling START command for {phone_number}: {e}")
        whatsapp_service.send_message(
            phone_number,
            "Sorry, there was an error setting up your journey. Please try again."
        )

def handle_stop_command(phone_number: str):
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
        
        whatsapp_service.send_message(phone_number, message)
        logger.info(f"User {phone_number} unsubscribed")
        
    except Exception as e:
        logger.error(f"Error handling STOP command for {phone_number}: {e}")

def handle_help_command(phone_number: str):
    """Handle HELP command"""
    help_message = ("📖 Faith Journey Help\n\n"
                   "Commands:\n"
                   "• START - Begin or restart your 30-day journey\n"
                   "• STOP - Unsubscribe from daily messages\n"
                   "• HELP - Show this help message\n\n"
                   "You'll receive daily content at 8:00 AM followed by a reflection question. "
                   "Feel free to share your thoughts - there are no wrong answers!\n\n"
                   "If you need to speak with someone, just let us know.")
    
    whatsapp_service.send_message(phone_number, help_message)

def handle_human_handoff(phone_number: str, message_text: str):
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
        
        whatsapp_service.send_message(phone_number, response_message)
        
        logger.warning(f"HUMAN HANDOFF requested by {phone_number}: {message_text}")
        
    except Exception as e:
        logger.error(f"Error handling human handoff for {phone_number}: {e}")

def handle_reflection_response(phone_number: str, message_text: str):
    """Handle user's reflection response"""
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
        
        # Send acknowledgment
        acknowledgments = [
            "Thank you for sharing your reflection. 🙏",
            "I appreciate you taking the time to reflect on this.",
            "Your thoughts are valuable. Thank you for sharing.",
            "Thank you for your honest reflection.",
        ]
        
        import random
        response = random.choice(acknowledgments)
        whatsapp_service.send_message(phone_number, response)
        
        logger.info(f"Processed reflection from {phone_number}: sentiment={analysis['sentiment']}, tags={analysis['tags']}")
        
    except Exception as e:
        logger.error(f"Error handling reflection response from {phone_number}: {e}")
        # Still acknowledge the user's response
        whatsapp_service.send_message(phone_number, "Thank you for your reflection. 🙏")

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
def cms():
    """Content Management System for 30-day journey content"""
    return render_template('cms.html')

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
    """API endpoint to create new content"""
    try:
        data = request.get_json()
        content_id = db_manager.create_content(
            day_number=data['day_number'],
            title=data['title'],
            content=data['content'],
            reflection_question=data['reflection_question'],
            cultural_note=data.get('cultural_note', ''),
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
            cultural_note=data.get('cultural_note', ''),
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

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        db.create_all()
        
        # Initialize database with sample content
        db_manager.initialize_sample_content()
    
    # Start background scheduler
    start_scheduler()
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
