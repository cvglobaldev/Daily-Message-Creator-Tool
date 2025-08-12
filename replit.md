# Faith Journey Drip Content - WhatsApp Chatbot

## Overview
This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide individuals from diverse non-Christian backgrounds through a spiritual journey to learn about Jesus. It delivers daily drip content, collects user reflections, and uses AI to analyze responses for engagement tracking and insights. The system aims to facilitate culturally sensitive spiritual exploration of customizable duration (10-90 days), enabling users to engage with Christian teachings at their own pace.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Principles
The system is a scalable and maintainable Flask web application in Python. A key decision was migrating to a PostgreSQL relational database for robust data management, schema integrity, and complex querying. The architecture supports multiple independent bot instances, each with its own content, users, and configurations.

### Technical Implementation
- **Backend**: Flask web application with Python.
- **Database**: PostgreSQL for all data storage, including users, content, message logs, and system settings, featuring relational schemas with foreign keys and indexing.
- **AI Integration**: Leverages Google Gemini API for sentiment analysis, keyword tagging of user responses, and AI-powered content generation for bot creation.
- **Messaging Integration**: Integrates with the WhatsApp Business API and Telegram Bot API for multi-platform support, allowing bots to operate independently across different messaging channels. A robust fallback simulation mode is available for development.
- **Scheduling**: A background thread-based scheduler manages daily content delivery, user progression, and rate limiting, simplifying deployment.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, CRUD operations, and support for configurable journey durations (10, 30, 60, 90 days) and predefined faith journey tags.
- **AI Content Generation**: Integrated AI-powered content creation using Google Gemini 2.5 Pro, offering audience customization (language, religion, age group, cultural background) and flexible journey durations with culturally sensitive content.
- **Chat Management System**: Provides an interface for consolidated user conversations, message sending, and human handoff detection, including real-time analytics and user profiles.
- **Authentication**: Implements Flask-Login for secure password hashing, session management, and role-based access control.
- **UI/UX**: Applies a consistent "CV Global" design theme across all management interfaces (dashboard, bot management, CMS, chat management) with professional branding, consistent color schemes, and enhanced navigation.

### Feature Specifications
- **Multi-Bot System**: Enables creation and management of independent bots, each with its own content, user base, AI prompts, and platform configurations.
- **Culturally Sensitive Content**: Content is designed for diverse non-Christian backgrounds, using appropriate terminology and progressive structures.
- **AI Response Analysis**: AI analyzes user reflections for sentiment and tags them with spiritual milestones.
- **Multimedia Support**: Supports delivery and management of various media types (images, audio, video) directly through the CMS with live preview.
- **Command System**: Recognizes user commands like "START," "STOP," "HELP," and "HUMAN" with customizable responses.
- **User Progression**: Tracks user progress through customizable journey durations (10-90 days).
- **Error Handling & Simulation**: Includes robust error handling, user deactivation for inactive chats, and development-friendly API simulation modes.

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

### ✅ COMPLETED: WhatsApp First Message Welcome Flow (August 12, 2025)
- **Standardized Welcome Flow**: All WhatsApp bots now follow: first message → welcome message from CMS → Day 1 content after 10 seconds
- **CMS Integration**: Welcome messages are pulled from bot-specific greeting content stored in CMS
- **Delayed Delivery**: Implemented threaded 10-second delay for Day 1 content delivery after welcome message
- **Media Support**: Day 1 content supports images, videos, and text with proper formatting
- **Universal Implementation**: Flow applies to all current and future WhatsApp bots for consistent user experience
- **Enhanced Logging**: Comprehensive tracking of welcome flow steps and delayed delivery success

### ✅ COMPLETED: Comprehensive Type Safety and Code Robustness (August 12, 2025)
- **Zero LSP Diagnostics**: Resolved all 66+ type safety issues, None type checks, and parameter validation errors
- **User Validation**: Added comprehensive None checks for all user objects before database logging operations
- **File Upload Security**: Enhanced secure_filename usage with proper None handling for all media upload endpoints
- **Parameter Type Safety**: Fixed all request parameter validation and type conversion issues  
- **Error Handling**: Implemented robust fallback mechanisms for all AI response generation and bot operations
- **Universal Protection**: Applied fixes across all current and future WhatsApp bots to prevent runtime errors
- **Production Ready**: Code now meets enterprise-level type safety and robustness standards