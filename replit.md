# Daily Message Creator - WhatsApp Chatbot

## Overview
This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide individuals from diverse non-Christian backgrounds through a spiritual journey to learn about Jesus. It delivers daily drip content, collects user reflections, and uses AI to analyze responses for engagement tracking and insights. The system aims to facilitate culturally sensitive spiritual exploration of customizable duration (10-90 days), enabling users to engage with Christian teachings at their own pace. The project's business vision is to provide a scalable and accessible tool for spiritual guidance, leveraging AI for personalized user interaction and content generation, with the ambition to reach a global audience.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The system is a scalable and maintainable Flask web application in Python. It utilizes a PostgreSQL relational database for robust data management and supports multiple independent bot instances, each with its own content, users, and configurations.

### Technical Implementation
- **Backend**: Flask web application with Python.
- **Database**: PostgreSQL for all data storage, including users, content, message logs, and system settings.
- **AI Integration**: Leverages Google Gemini API for sentiment analysis, keyword tagging of user responses, and AI-powered content generation.
- **Messaging Integration**: Integrates with the WhatsApp Business API and Telegram Bot API for multi-platform support, allowing bots to operate independently.
- **Scheduling**: A background thread-based scheduler manages daily content delivery, user progression, and rate limiting.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, CRUD operations, and support for configurable journey durations (10, 30, 60, 90 days) and predefined faith journey tags. It supports multimedia delivery (images, audio, video).
- **AI Content Generation**: Integrated AI-powered content creation using Google Gemini 2.5 Pro, offering audience customization (language, religion, age group, cultural background) and flexible journey durations.
- **Chat Management System**: Provides an interface for consolidated user conversations, message sending, human handoff detection, real-time analytics, and user profiles.
- **Authentication**: Implements Flask-Login for secure password hashing, session management, and role-based access control.
- **UI/UX**: Applies a consistent "CV Global" design theme across all management interfaces (dashboard, bot management, CMS, chat management) with professional branding and consistent color schemes.
- **Multi-Bot System**: Enables creation and management of independent bots, each with its own content, user base, AI prompts, and platform configurations.
- **Culturally Sensitive Content**: Content is designed for diverse non-Christian backgrounds.
- **AI Response Analysis**: AI analyzes user reflections for sentiment and tags them with spiritual milestones.
- **Command System**: Recognizes user commands like "START," "STOP," "HELP," and "HUMAN" with customizable responses.
- **User Progression**: Tracks user progress through customizable journey durations (10-90 days).
- **Error Handling & Simulation**: Includes robust error handling, user deactivation for inactive chats, and development-friendly API simulation modes.
- **Phone Number Normalization**: Automatically handles various phone number formats for consistent user identification.
- **Media Management**: Comprehensive system for managing media files, including prevention of broken references and integrity monitoring.

## External Dependencies

### APIs
- WhatsApp Business API
- Google Gemini API
- Telegram Bot API

### Environment Variables
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `GEMINI_API_KEY`
- `SESSION_SECRET`

### Python Packages
- `flask`
- `google-genai`
- `requests`
- `replit`
- `psycopg2-binary`
- `Flask-Login`
- `Flask-WTF`
- `passlib`
- `python-dotenv`
- `python-telegram-bot`

## Recent Changes

### ✅ COMPLETED: Critical Duplicate Message Bug Fix (October 2, 2025)
- **Root Cause Identified**: Two scheduler threads were running simultaneously due to start_scheduler() being called from both module initialization and dashboard route without proper synchronization
- **Thread-Safe Implementation**: Added threading.Lock() to ensure only one scheduler thread can start, using double-checked locking pattern
- **Race Condition Eliminated**: Flag is now set inside the lock immediately before thread creation, preventing concurrent initialization
- **User Impact Resolved**: Users (including +6281931113811 and tg_960173404) no longer receive duplicate messages
- **Production Stability**: Single scheduler thread now runs reliably across all worker processes
- **Content Completion Handling**: Added proper handling for users who reach the end of available content days, offering AI conversation, human connection, or journey restart options
- **Journey Restart Support**: Users can restart their journey with /start command, resetting to Day 1 with fresh content delivery

### ✅ COMPLETED: Bot Creation Platform Configuration & Multi-Language Support (October 2, 2025)
- **Platform Configuration Display Fixed**: Resolved JavaScript syntax error preventing WhatsApp and Telegram configuration sections from appearing when checkboxes were selected on create bot page
- **Comprehensive Language Support**: Added all 46 Gemini AI-supported languages to both create and edit bot forms with dropdown selection
- **Database Schema Updated**: Implemented language field in Bot model with English as default for backward compatibility
- **Multi-Language Bot Creation**: Users can now select target audience language during bot creation, with language preference persisted to database
- **Form Validation Enhanced**: Both CreateBotForm and EditBotForm now include language selection with proper validation
- **JavaScript Debug Fix**: Removed extra closing brace causing "Unexpected token '}'" error that blocked all JavaScript execution
- **User Experience Improved**: Platform-specific credentials fields (WhatsApp Access Token, Telegram Bot Token) now display immediately upon platform selection

### ✅ COMPLETED: WhatsApp API Integration & Credentials Updated (August 21, 2025)
- **WhatsApp Business API Fully Configured**: Updated with new WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID (727962770406515) for proper authentication
- **Meta Business Manager Integration**: Successfully configured webhook URL (https://smart-budget-cvglobaldev.replit.app/whatsapp/2) with updated verification token
- **Credentials Resolution**: Updated access token and phone number ID to resolve Meta Business permissions and enable message delivery
- **Interactive Button System**: Implemented Yes/No button responses for human connection requests on both WhatsApp and Telegram
- **Multi-Platform Button Support**: Telegram inline keyboards and WhatsApp interactive buttons both fully functional
- **Contextual Response System Validated**: Bot 2 (Indonesian Bang Kris) confirmed working with proper contextual AI responses based on daily spiritual content
- **Human Connection Flow**: Enhanced with proper callback handling and confirmation messages in both English/Indonesian
- **Webhook Routing**: Proper bot-specific webhook URLs configured (/whatsapp/1, /whatsapp/2, etc.) for multi-bot isolation
- **Message Processing**: All platforms now properly receive, process, and generate contextual replies based on user's spiritual journey stage
- **Production Ready**: System successfully processing real WhatsApp messages with proper Indonesian spiritual guidance responses about Isa al-Masih

### ✅ COMPLETED: Human Connection Option System (August 19, 2025)
- **Always Offer Human Connection First**: System now proactively offers users the option to connect with a human team member before providing AI responses for sensitive topics
- **Intelligent Detection**: Enhanced analysis identifies messages containing emotional distress, spiritual concerns, or deep questions requiring personal guidance
- **No Auto "Human" Tags**: Removed automatic assignment of "Human" tags from AI analysis to prevent premature classification
- **User Choice Priority**: Users receive clear options to either connect with human team or continue with contextual AI responses based on daily content
- **Multi-language Support**: Human connection offers available in both English and Indonesian based on bot configuration
- **Comprehensive Coverage**: Applied across all bots to ensure consistent user experience and support availability

### ✅ COMPLETED: Enhanced Contextual AI Response System (August 19, 2025)
- **Intelligent Content-Aware Responses**: Users now receive AI responses that are contextually aware of their current daily content, journey stage, and spiritual topic
- **Enhanced AI Context Integration**: Improved Google Gemini integration with expanded context including current day content, topics, reflection questions, and journey stage
- **Unified Contextual Conversation Handler**: Created comprehensive `handle_contextual_conversation` function that provides intelligent responses for all user messages beyond Day 1
- **Content-Based Response Generation**: AI responses now reference and build upon the user's current daily content, creating more meaningful spiritual conversations
- **Improved Message Routing**: Enhanced logic to route users to appropriate conversation handlers based on their journey progress and content engagement
- **Day 1 Contextual Support**: Even Day 1 users receive contextual responses once they've received their initial content
- **Fallback Enhancement**: Robust fallback system ensures users always receive appropriate responses even during AI service interruptions
- **Journey-Aware AI Prompts**: AI responses now include detailed context about user's current spiritual content, enabling more relevant and helpful conversations