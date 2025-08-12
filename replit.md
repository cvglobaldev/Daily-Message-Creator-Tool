# Faith Journey Drip Content - WhatsApp Chatbot

## Overview

This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide people from diverse non-Christian backgrounds on a spiritual journey to learn about Jesus. The system delivers daily drip content, collects user reflections, and uses AI to analyze user responses for engagement tracking and insights. Its core purpose is to facilitate a culturally sensitive spiritual exploration of customizable duration (10-90 days), enabling users from any religious or secular background to engage with Christian teachings at their own pace.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Updates

### ✅ COMPLETED: Bot-Specific WhatsApp Service Implementation (August 12, 2025)
- **Bot Isolation**: Implemented bot-specific WhatsApp services using credentials stored in bot configuration
- **Dynamic Service Creation**: Each bot now uses its own WhatsApp access token and phone number ID from database
- **Cache Management**: Added intelligent caching system with automatic invalidation when bot credentials are updated
- **Real Messaging**: System now automatically uses bot-specific WhatsApp credentials instead of global simulation mode
- **Multi-Bot Support**: Scheduler and message handlers updated to route messages through correct bot-specific WhatsApp services
- **Seamless Integration**: Bot edit forms automatically deploy new WhatsApp connections when credentials are updated

### ✅ COMPLETED: AI Content Generation Feature (August 12, 2025)
- **New Feature**: AI-powered content generation for bot creation using Google Gemini 2.5 Pro
- **Audience Targeting**: Comprehensive audience customization (language, religion, age group, cultural background)
- **Duration Options**: Flexible journey durations (10, 30, 90 days) with automatic content generation
- **Cultural Sensitivity**: Built-in prompts ensure respectful content for diverse religious backgrounds
- **Toggle Activation**: User-friendly form toggle with validation and error handling
- **Multi-Background Support**: Expanded from Muslim-specific to any non-Christian background (Islam, Hindu, Buddhist, Secular, etc.)
- **Content Quality**: AI generates culturally appropriate daily content with reflection questions and spiritual milestones

### ✅ COMPLETED: Full Telegram Bot System Fix (August 7, 2025)
- **Root Cause**: Flask app context was not available during bot service creation, causing webhook processing to fail silently
- **Solution**: Added proper Flask app context management in `get_telegram_service_for_bot` function
- **Database Fix**: Corrected user assignment for Bot 5 routing to ensure proper message flow
- **Testing**: Verified Fun-Meaningful-Transformation-Bot now successfully processes commands and delivers Day 1 content automatically
- **Automatic Content Delivery**: Fixed direct content delivery system with proper bot-specific service routing
- **Multi-Bot Support**: All bots now use their specific tokens for message sending with proper context management
- **Quality Assurance**: Implemented comprehensive debug logging and error handling for reliable bot operations

## System Architecture

### Core Design Principles
The system is built as a Flask web application in Python, designed for scalability and maintainability. A key decision was migrating from a key-value store to a full PostgreSQL relational database for robust data management, schema integrity, and complex querying capabilities. The architecture supports multi-bot instances, allowing independent content, users, and configurations for different spiritual journeys or languages.

### Technical Implementation
- **Backend**: Flask web application with Python.
- **Database**: PostgreSQL for all data storage, including users, content, message logs, and system settings. It features comprehensive relational schemas with foreign keys and indexing for performance.
- **AI Integration**: Leverages the Google Gemini API for sentiment analysis and keyword tagging of user responses, providing insights into user engagement and spiritual milestones.
- **Messaging Integration**: Primarily uses the WhatsApp Business API, with a robust fallback simulation mode for development. Telegram Bot API is also integrated for multi-platform support, allowing bots to operate independently across different messaging channels.
- **Scheduling**: A background thread-based scheduler manages daily content delivery, user progression through the journey, and rate limiting. This avoids external cron job dependencies, simplifying deployment in environments like Replit.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, and full CRUD operations. It supports configurable journey durations (10, 30, 60, 90 days) and predefined faith journey tags for content categorization.
- **AI Content Generation**: Integrated AI-powered content creation using Google Gemini 2.5 Pro with audience-specific customization for different religious and cultural backgrounds. Users can generate complete journeys (10-90 days) with culturally sensitive content tailored to their target demographic.
- **Chat Management System**: Provides a comprehensive interface for viewing consolidated user conversations, sending messages, and detecting human handoff requests. It includes real-time analytics and user profile displays.
- **Authentication**: Implements a production-ready Flask-Login system with secure password hashing, session management, and role-based access control for administrative users.
- **UI/UX**: Applies a consistent "CV Global" design theme across all management interfaces (dashboard, bot management, CMS, chat management) with professional branding, consistent color schemes, and enhanced navigation.

### Feature Specifications
- **Multi-Bot System**: Enables the creation and management of multiple independent bots, each with its own content, user base, AI prompts, and platform configurations (WhatsApp, Telegram).
- **Culturally Sensitive Content**: Content is designed for diverse non-Christian backgrounds (Muslim, Hindu, Buddhist, Secular, etc.), using culturally appropriate terminology and progressive journey structures to respectfully introduce Christian concepts.
- **AI Response Analysis**: AI analyzes user reflections for sentiment (positive/negative/neutral) and tags them with predefined spiritual milestones (e.g., Introduction to Jesus, Gospel Presentation, Salvation Prayer).
- **Multimedia Support**: The system supports the delivery and management of various media types (images, audio, video) directly through the CMS, including a comprehensive live preview system.
- **Command System**: Recognizes user commands like "START," "STOP," "HELP," and "HUMAN" (for priority human intervention), with customizable responses per bot.
- **User Progression**: Tracks user progress through customizable journey durations (10-90 days), ensuring sequential content delivery and managing journey completion.
- **Error Handling & Simulation**: Includes robust error handling, user deactivation for inactive chats, and development-friendly simulation modes for API dependencies.

## External Dependencies

### APIs
- **WhatsApp Business API**: For primary message sending and receiving.
- **Google Gemini API**: For AI-powered sentiment analysis and keyword tagging of user responses.
- **Telegram Bot API**: For multi-platform messaging support.

### Environment Variables
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp API authentication.
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp business phone number ID.
- `GEMINI_API_KEY`: Google Gemini API key.
- `SESSION_SECRET`: Flask session security key.

### Python Packages
- `flask`: Web framework.
- `google-genai`: Google Gemini API client.
- `requests`: HTTP client for API calls.
- `replit`: For database access within the Replit environment.
- `psycopg2-binary`: PostgreSQL adapter for Python.
- `Flask-Login`: User session management.
- `Flask-WTF`: Form handling.
- `passlib`: Password hashing.
- `python-dotenv`: Environment variable management.
- `python-telegram-bot`: Telegram Bot API wrapper.