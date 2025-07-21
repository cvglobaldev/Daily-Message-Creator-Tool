import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, make_response
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
                logger.info("Running content scheduler (every 5 minutes for testing)...")
                scheduler.send_daily_content()
                # Sleep for 5 minutes (300 seconds) between content deliveries
                time.sleep(300)
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
            tags=data.get('tags', []),
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
        
        return render_template('settings.html', settings=settings, default_prompt=default_prompt)
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return f"Error loading settings: {e}", 500

@app.route('/api/send-message', methods=['POST'])
def send_message_to_user():
    """Send a message from admin to user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        tags = data.get('tags', [])
        
        user = db_manager.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
            
        # Send message via WhatsApp
        success = whatsapp_service.send_message(user.phone_number, message)
        
        if success:
            # Log the message
            db_manager.log_message(
                user=user,
                direction='outgoing',
                raw_text=message,
                tags=tags
            )
            
        return jsonify({'success': success})
    except Exception as e:
        logger.error(f"Error sending message: {e}")
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
def chat_management_page():
    """Display chat management page"""
    try:
        stats = db_manager.get_chat_management_stats()
        return render_template('chat_management.html', stats=stats)
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

@app.route('/chat/<int:user_id>')
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
        
        return render_template('full_chat.html', user=user_dict, messages=messages)
    except Exception as e:
        logger.error(f"Error loading chat history: {e}")
        return f"Error loading chat history: {e}", 500

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
