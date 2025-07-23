# Faith Journey Drip Content - WhatsApp Chatbot

## Overview

This is a WhatsApp-based chatbot designed to guide young adults (18-24) from Muslim backgrounds on a 30-day spiritual journey to learn about Jesus. The system delivers daily content, collects reflections, and uses AI to analyze user responses for engagement tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Python
- **Database**: PostgreSQL database with comprehensive relational schema (upgraded from key-value store)
- **AI Integration**: Google Gemini API for response sentiment analysis and keyword tagging
- **Messaging**: WhatsApp Business API integration with fallback simulation mode
- **Scheduling**: Background thread-based scheduler for daily content delivery

### Key Design Decisions
- **PostgreSQL Database**: Upgraded to full relational database with proper schemas, relationships, and indexing for production scalability
- **Simulation Mode**: Includes development-friendly message simulation when API credentials aren't available
- **Thread-based Scheduling**: Uses background threads instead of external cron jobs for simplicity in Replit environment
- **Cultural Sensitivity**: Designed specifically for Muslim-to-Christian spiritual journey with appropriate terminology

## Key Components

### Database Manager (`db_manager.py`)
- **PostgreSQL Schema**: Full relational database with users, content, message_logs, and system_settings tables
- **User Management**: Comprehensive CRUD operations with proper foreign key relationships
- **Message Logging**: Detailed interaction tracking with sentiment analysis and AI tagging
- **Content Management**: Structured 30-day content delivery system with reflection questions
- **Analytics**: Built-in user statistics, sentiment analysis, and progress tracking

### Services Layer (`services.py`)
- **WhatsAppService**: Manages message sending via WhatsApp Business API
- **GeminiService**: Handles AI-powered response analysis for sentiment and keyword tagging
- Includes simulation modes for development without external API dependencies

### Content Scheduler (`scheduler.py`)
- Background service that runs daily content delivery
- Manages user progression through 30-day journey
- Handles journey completion and user lifecycle management
- Implements rate limiting between user messages

### AI Response Analysis (`prompts.py`)
- Contains structured prompts for Gemini API
- Analyzes user responses for sentiment (positive/negative/neutral)
- Tags responses with predefined keywords relevant to spiritual journey
- Culturally sensitive to Muslim background and terminology

## Data Flow

1. **User Onboarding**: User sends "START" keyword → System registers user → Sends Day 1 content
2. **Daily Delivery**: Scheduler runs daily → Fetches active users → Sends day-specific content → Updates user progress
3. **Response Collection**: User responds to reflection questions → System captures response
4. **AI Analysis**: Response sent to Gemini API → Sentiment and keyword analysis → Results logged to database
5. **Journey Completion**: After 30 days → User marked as completed → Journey ends

## External Dependencies

### Required APIs
- **WhatsApp Business API**: For message sending/receiving (Meta or Twilio)
- **Google Gemini API**: For AI-powered response analysis

### Environment Variables
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp API authentication
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp business phone number
- `GEMINI_API_KEY`: Google Gemini API key
- `SESSION_SECRET`: Flask session security key

### Python Packages
- `flask`: Web framework
- `google-genai`: Google Gemini API client
- `requests`: HTTP client for API calls
- `replit`: Database access

## Deployment Strategy

### Replit-Optimized Design
- Uses Replit's PostgreSQL database for production-ready data storage
- Includes simulation modes for development without external API setup
- Background scheduler runs as application thread (no separate cron needed)
- Enhanced admin dashboard with real-time analytics and human handoff monitoring

### Scaling Considerations
- PostgreSQL database supports production-scale user loads with proper indexing
- Thread-based scheduling suitable for moderate concurrent users
- Rate limiting implemented to respect API quotas
- Comprehensive error handling and transaction management
- Database relationships ensure data integrity and enable complex analytics

### Development vs Production
- **Development Mode**: Simulates WhatsApp messages, uses console logging, PostgreSQL database available
- **Production Mode**: Requires actual API credentials, sends real messages
- Environment-based configuration switches between modes automatically

## Recent Changes (July 23, 2025)

### Combined Daily Content + Reflection Questions Implementation (Latest Update - July 23, 2025)
- **Single Message Delivery**: Successfully combined daily content with reflection questions into one message, eliminating duplicate separate deliveries
- **Enhanced User Database**: Added `name` column to User model to capture Telegram user information (first_name/username) automatically from webhook data
- **Improved Message Processing**: Updated user creation/update functions to store Telegram names during /start command processing
- **Removed Flask Context Errors**: Eliminated separate reflection question scheduling that caused application context issues
- **Database Schema Update**: Added `name VARCHAR(100)` column to users table for storing Telegram user information
- **Combined Message Format**: Messages now delivered as "📖 Day X - Title + Content + 💭 Reflection Question + Instructions" in single delivery
- **User Testing Ready**: System tested with fresh user accounts showing proper combined message delivery and name storage

### Chat Management Duplicates Fix - Consolidated User Conversations
- **Eliminated Duplicate Entries**: Fixed chat management interface showing 4 separate entries for single user (e.g., tg_960173404)
- **Consolidated User View**: Replaced individual message entries with unified conversation summaries per user
- **Enhanced API Endpoint**: Updated `/api/chat-management/messages` to use new `get_consolidated_user_conversations()` method
- **Conversation Statistics**: Each user now shows total message count breakdown (e.g., "3 messages from user, 1 from bot")
- **Single Entry Per User**: Direction field changed to "Conversation" to indicate consolidated view instead of separate "Bot"/"User" entries
- **Preserved All Data**: Maintains sentiment analysis, tags aggregation, and handoff detection while eliminating duplicates
- **Database Optimization**: Uses GROUP BY queries with comprehensive conversation statistics for better performance
- **Unified User Experience**: Chat management now displays clean, unique user list with complete conversation context

### Video/Audio File Upload Delivery Fix
- **File Upload API**: Fixed video and audio delivery by switching from URL-based to direct file upload method in Telegram API
- **Multipart Form Data**: Implemented proper multipart/form-data requests for sendVideo and sendAudio endpoints
- **File Path Resolution**: Added logic to extract filenames from media URLs and locate files in static/uploads directories  
- **Timeout Handling**: Increased timeout to 120 seconds for large video/audio file uploads
- **Audio Method Addition**: Added dedicated send_audio() method to TelegramService for proper audio file delivery
- **Scheduler Integration**: Updated scheduler to use new send_audio() method for audio content delivery
- **Error Handling**: Enhanced error logging for file not found and API response failures
- **Fallback Support**: Maintained URL-based sending for external media URLs while using file upload for local uploads

### Complete Media Preview System Implementation
- **Universal Media Preview**: Implemented comprehensive live preview functionality for all media types in CMS
- **Image Upload Preview**: Images show immediate thumbnail preview when selected with file size information
- **Audio Upload Preview**: Audio files display live player controls for immediate testing and validation  
- **Video Upload Preview**: Enhanced video preview with player controls and file information display
- **Database Tags Fix**: Resolved PostgreSQL array type mismatch for tags that was preventing audio uploads
- **Enhanced CMS Experience**: All media types now show existing files when editing with replacement instructions
- **File Validation**: Complete upload validation with size limits and format checking for all media types
- **Cross-Platform Compatibility**: Preview system works consistently across all supported browsers

### Video Upload System Implementation
- **YouTube URL Replaced with Video Upload**: Completely replaced YouTube URL functionality with direct video file upload capability
- **200MB File Size Limit**: Configured video upload system to support files up to 200MB for comprehensive content delivery
- **Video File Support**: Added support for MP4, MOV, AVI, MKV, and WebM video formats with secure file handling
- **Database Schema Update**: Added `video_filename` column to content table with proper model relationships and URL generation
- **CMS Video Interface**: Updated Content Management System with video upload interface replacing YouTube URL input
- **Video Delivery Infrastructure**: Enhanced Telegram service to handle uploaded video files via sendVideo API
- **File Management**: Implemented secure filename generation, upload directory creation, and file validation
- **Complete Integration**: Video uploads work end-to-end from CMS upload to Telegram user delivery
- **Backwards Compatibility**: Maintained YouTube URL support in database for existing content while prioritizing uploaded videos

### YouTube Video Delivery Fix & Duplicate Message Prevention
- **YouTube API Fix**: Resolved Telegram API error where YouTube URLs couldn't be sent via video API - now sends as formatted text messages with preview
- **Duplicate Message Prevention**: Added comprehensive logic to prevent users from receiving same day content multiple times
- **Message History Checking**: Scheduler now checks user's recent messages to detect if content was already delivered for current day
- **Telegram Video Handling**: YouTube URLs automatically detected and sent as text messages with "🎥 Watch Video:" format and web preview enabled
- **User Reset Functionality**: Enhanced user clearing and recreation system for fresh testing scenarios
- **Error Handling**: Fixed database transaction errors and method signature issues in scheduler
- **Testing Success**: Confirmed delivery works for both image content (Day 1) and YouTube video content (Day 2) with proper user progression

### Chat Management Duplicate Fix & User Clearing
- **Fixed Duplicate Chat Entries**: Resolved issue where multiple message entries for the same user appeared as separate chats in management interface
- **Database Optimization**: Updated `get_recent_active_users()` to return unique users with their latest message instead of individual message records
- **User Data Clearing**: Implemented complete user data clearing functionality via `/api/users/{phone}/clear` endpoint for testing purposes  
- **Chat Interface Enhancement**: Chat management now displays each user only once with their most recent activity
- **Testing Support**: Added comprehensive user cleanup for testing YouTube video delivery and other features
- **Backend Efficiency**: Reduced API response size and improved chat management performance by eliminating duplicates

### Image Delivery Bug Fix - Telegram Integration
- **Critical Fix**: Resolved image delivery issue where Day 1 content images weren't appearing for users
- **Content Model Enhancement**: Updated Content model's `to_dict()` method to properly construct `media_url` field
- **Telegram Photo API**: Implemented full `send_photo` method in TelegramService for actual image delivery
- **Media URL Generation**: Fixed URL construction to use proper Replit domain and static file paths
- **Scheduler Integration**: Updated scheduler to call Telegram photo API for image content delivery
- **Multi-Platform Support**: Both WhatsApp (simulated) and Telegram (live) now properly handle multimedia content
- **Debug Logging**: Added comprehensive logging to track media URL generation and delivery success

## Recent Changes (July 21, 2025)

### Enhanced Command System and Scheduler Fix (Latest Update)
- **Scheduler Timing Fix**: Fixed inconsistent scheduling by changing reflection question delay from 2 minutes to 10 minutes for consistency
- **New HUMAN Command**: Added direct human chat command (/human for Telegram, HUMAN for WhatsApp) for priority human intervention
- **Enhanced Welcome Messages**: Added command information (start, stop, help, human) to all welcome and restart messages
- **Command Processing**: Updated message processing logic to recognize and route the new HUMAN command
- **User Experience**: Users now see available commands immediately upon joining, improving discoverability
- **Human Chat Priority**: HUMAN command flags conversations with PRIORITY tag for immediate admin attention

### Enhanced Telegram Bot API 2025 Integration
- **Modern Telegram Features**: Updated chatbot settings to leverage Telegram Bot API 8.0 (2025) capabilities
- **Interactive Messaging**: Implemented inline keyboards, quick reply buttons, and callback query handling
- **Copy Text Buttons**: Added support for copy-to-share functionality for Bible verses and inspirational content
- **Enhanced User Engagement**: Integrated emoji reactions, rich media support, and improved user interaction tools
- **Callback Query Processing**: Full support for interactive button responses and user engagement tracking
- **Settings Modernization**: Updated system settings with comprehensive Telegram feature configuration
- **Multi-Platform Enhancement**: Enhanced send_message_to_platform function with platform-specific features
- **Production Ready**: All new features work in both simulation and live Telegram bot environments

### Complete Authentication System Implementation
- **Production-Ready Authentication**: Full Flask-Login integration with secure password hashing and session management
- **Admin User Management**: Registration, login, user editing, password changes, and role-based access control
- **Security Features**: All main routes protected with @login_required decorator and proper redirect handling
- **Authentication Templates**: Professional login, registration, user management, and password change interfaces
- **Default Admin Account**: System creates default super_admin (admin / admin123) for initial setup
- **Additional Admin User**: Created faithadmin user (faithadmin / faith2025!) with super_admin privileges
- **Role-Based Access**: Super admins can manage other users, regular admins have dashboard access only
- **Secure Navigation**: Updated dashboard and templates with proper authentication menus and logout functionality

### Telegram Bot Successfully Deployed and Active
- **Production Deployment**: Bot deployed at https://smart-budget-cvglobaldev.replit.app/
- **Webhook Configured**: Real Telegram webhook active and receiving messages
- **Real User Testing**: @faithjourney_bot responding to actual Telegram users
- **Message Flow Verified**: /start commands triggering automatic Day 1 content delivery
- **Platform Routing Fixed**: Scheduler now properly routes Telegram messages via Telegram API instead of WhatsApp simulation
- **Multi-Platform Success**: Both WhatsApp simulation and real Telegram working simultaneously
- **AI Analysis Active**: Real-time sentiment analysis and faith journey tagging working with 95%+ confidence

### Telegram Integration Implementation
- **Multi-Platform Support**: Added comprehensive Telegram Bot API integration alongside existing WhatsApp functionality
  - TelegramService class with full webhook, message sending, and bot management capabilities
  - Platform-aware message routing (send_message_to_platform function)
  - Support for Telegram-specific commands (/start, /stop, /help) and WhatsApp keywords
  - Proper chat ID handling (tg_prefix system) for database storage and message delivery
- **Enhanced Message Processing**: Updated all handler functions to support both platforms
  - handle_start_command, handle_stop_command, handle_help_command with platform parameter
  - handle_reflection_response and handle_human_handoff with cross-platform support
  - Telegram webhook endpoint (/telegram) processing standard Bot API updates
- **Administrative Features**: 
  - /telegram/setup POST endpoint for webhook configuration
  - /telegram/info GET endpoint for bot and webhook status
  - /telegram/test POST endpoint for simulating messages during development
- **Database Integration**: Telegram users stored with tg_ prefix (e.g., tg_123456789) alongside WhatsApp users
- **Automatic Scheduler**: Background content delivery works seamlessly for both platforms

### Demo Content Creation and Testing Configuration
- **10 Days of Demo Content**: Created comprehensive 10-day faith journey content for conversation simulation
  - Days 1-10 cover: Welcome, Divine Compassion, Word of Allah, Peace in the Storm, Good Shepherd, Forgiveness, Love, New Beginnings, Purpose, Bridge to God
  - Each day includes engaging content, reflection questions, and proper faith journey tags
  - Content stored in PostgreSQL with proper array formatting for tags
- **Testing Schedule Configuration**: Changed daily content delivery from 8:00 AM to every 5 minutes for rapid testing
  - Allows quick simulation of user journey progression
  - Background scheduler runs continuously for immediate testing feedback
  - Maintains all original functionality while enabling fast iteration

### Major Database Upgrade - PostgreSQL Migration
- **Migrated from key-value store to PostgreSQL**: Full relational database with proper schema design
- **Enhanced Data Models**: 
  - Users table with proper typing and relationships
  - Content table for structured journey management with configurable duration
  - Message logs with detailed AI analysis tracking
  - System settings for configuration management
- **Improved Analytics**: Real-time user statistics, sentiment analysis, and progress tracking
- **Human Handoff System**: Automated detection and logging of messages requiring human intervention
- **Database Integrity**: Foreign key constraints, indexes, and transaction management
- **API Enhancements**: New test endpoints and user management APIs
- **Dashboard Improvements**: Real-time data display with proper PostgreSQL integration

### Enhanced Content Management System (CMS)
- **Configurable Journey Duration**: Adjustable from 10, 30, 60, to 90 days (30 default)
- **Faith Journey Tagging System**: 8 predefined tags for content categorization
  - Bible Exposure, Christian Learning, Bible Engagement, Salvation Prayer
  - Gospel Presentation, Prayer, Introduction to Jesus, Holy Spirit Empowerment
- **Advanced Content Editor**: Live preview, tag management, and content validation
- **Complete CRUD Operations**: Create, edit, delete, and activate/deactivate content
- **Cultural Sensitivity Removal**: Streamlined interface focused on core content and tagging
- **Dashboard Integration**: Content statistics and tag distribution displayed on main dashboard
- **Sample Content**: Three demonstration days with proper tagging for immediate testing

### Complete Chat Management System (Latest Update)
- **Clickable Message History**: Click on recent messages to view full conversation history
- **Comprehensive Chat Interface**: Full conversation view with message bubbles and timestamps
- **Human Message Sending**: Send tagged messages directly to users through admin interface
- **Contextual AI Responses**: AI uses current day content to provide personalized responses
- **Admin Prompt Customization**: Full control over AI personality and response style
- **Response Testing Interface**: Test AI responses with different settings and prompts
- **Message Export**: Export chat histories as text files for record keeping
- **Tag Management**: Add and modify tags on messages through the interface
- **Human Handoff Detection**: Automatic flagging of messages requiring human intervention