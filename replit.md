# Daily Message Creator - WhatsApp Chatbot

## Overview
This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide individuals from diverse non-Christian backgrounds through a spiritual journey to learn about Jesus. It delivers daily drip content, collects user reflections, and uses AI to analyze responses for engagement tracking and insights. The system aims to facilitate culturally sensitive spiritual exploration of customizable duration (10-90 days). The business vision is to provide a scalable and accessible tool for spiritual guidance, leveraging AI for personalized user interaction and content generation, with the ambition to reach a global audience.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system is a scalable and maintainable Flask web application in Python, utilizing a PostgreSQL relational database. It supports multiple independent bot instances, each with its own content, users, and configurations.

### UI/UX Decisions
A consistent "CV Global" design theme is applied across all management interfaces (dashboard, bot management, CMS, chat management) with professional branding and consistent color schemes.

### Technical Implementations
- **Backend**: Flask web application with Python.
- **Database**: PostgreSQL for all data storage.
- **AI Integration**: Leverages Google Gemini API for sentiment analysis, keyword tagging, and AI-powered content generation.
- **Messaging Integration**: Integrates with WhatsApp Business API and Telegram Bot API.
- **Scheduling**: A background thread-based scheduler manages daily content delivery and user progression.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, CRUD operations, multimedia delivery, and support for configurable journey durations.
- **Voice Conversation Feature**: Includes end-to-end voice message handling with language-aware transcription and synthesis using Google Cloud Speech-to-Text and Text-to-Speech APIs.
- **Dual-Layer Tagging System**: Combines AI semantic analysis with rule-based automation.
- **Atomic Lock System**: Implements a database-backed atomic locking system for duplicate message prevention.
- **Multi-Language Support**: Supports 40+ languages including Hausa, with culturally appropriate AI prompts and templates for diverse audiences.
- **Manual Webhook Setup**: Admin interface includes manual webhook configuration for recovering from failed automatic setups.
- **Double-Submit Prevention**: Form submission protection prevents duplicate bot creation during long-running operations.
- **AI Tag Validation System**: AI content generation enforces strict tag alignment with the tag management system. The AI fetches active tags from the TagRule database on initialization, validates all AI-generated tags against this list, and filters out any unauthorized tags. Fallback content uses only managed tags, and if no tags exist in the database, content is created with empty tags rather than hardcoded defaults. All tag validations are logged for monitoring and debugging.
- **Context-Aware Day-by-Day AI Generation**: The day-by-day AI content generation system includes journey memory and continuity. When generating content for any day, the AI receives a summary of the previous 5 days' content, ensuring progressive learning without topic repetition. The system fetches previous content from the database, creates a token-efficient summary, and instructs the AI to build upon prior days while avoiding repetition. This ensures each day feels like a natural progression of the journey rather than a standalone piece.
- **Scheduler Lock System**: Implements a database-backed lock mechanism to ensure only one gunicorn worker runs the content scheduler, preventing duplicate scheduler instances and resource exhaustion. The lock uses a 30-second TTL and automatic takeover for stale locks.
- **Comprehensive Database Query Optimization**: 
  - **Bot Management Pages**: Uses optimized SQL queries with joins and aggregations to fetch bot counts in a single query, eliminating N+1 query problems across all pages (bot management, CMS, chat management).
  - **Analytics Dashboard**: Reduced from 200+ queries to 3-4 queries using SQL CASE aggregations for journey funnel data and bulk fetching for dropoff calculations, achieving 50x performance improvement.
  - **Progressive Loading UX**: Analytics page displays a loading animation while data loads, improving perceived performance and user experience.
- **Dynamic Journey Length Management in CMS**: The content management system dynamically adapts to each bot's configured journey duration. The journey length filter dropdown automatically includes the bot's actual duration as a selected option (even for non-standard durations like 10 or 45 days), and JavaScript initialization uses the bot's journey_duration_days to display the correct day range on page load. This ensures UI consistency between the filter display and content cards across all journey configurations.
- **API Endpoint Authentication Pattern**: API endpoints that return JSON (e.g., `/api/delete-user-history`, `/api/media/browse`) use manual authentication checks with `current_user.is_authenticated` instead of `@login_required` decorator. This prevents Flask-Login from redirecting to HTML login pages when sessions expire, ensuring consistent JSON responses (401 errors) that frontend JavaScript can properly parse and handle.
- **CMS Content Creation Dual-Path Handler**: The `/cms/content/create` endpoint handles both JavaScript FormData submissions (from the CMS interface) and traditional Flask WTForms submissions. JavaScript submissions are identified by the presence of the 'content_type' field (which the CMS JavaScript always sends), while traditional forms may not have this field. The endpoint correctly handles field names with underscores ('day_number', 'bot_id') as sent by the JavaScript. This ensures CMS greeting/welcome message creation works correctly while preserving backward compatibility with WTForms-based workflows. The endpoint requires explicit bot_id for CMS submissions to prevent wrong-bot content creation.

### System Design Choices
- **Multi-Bot System**: Enables creation and management of independent bots.
- **Culturally Sensitive Content**: Content is designed for diverse non-Christian backgrounds.
- **AI Response Analysis**: AI analyzes user reflections for sentiment and tags them with spiritual milestones.
- **Command System**: Recognizes user commands like "START," "STOP," "HELP," and "HUMAN."
- **User Progression**: Tracks user progress through customizable journey durations (10-90 days).
- **Contextual AI Response System**: AI responses are contextually aware of the user's current daily content, journey stage, and spiritual topic.
- **Human Connection Option System**: Proactively offers users the option to connect with a human team member for sensitive topics.

## External Dependencies

### APIs
- WhatsApp Business API
- Google Gemini API
- Telegram Bot API
- Google Cloud Speech-to-Text API
- Google Cloud Text-to-Speech API

### Environment Variables
- `WHATSAPP_ACCESS_TOKEN`
- `WHATSAPP_PHONE_NUMBER_ID`
- `GEMINI_API_KEY`
- `SESSION_SECRET`
- `GOOGLE_CLOUD_CREDENTIALS_JSON`

### Python Packages
- `flask`
- `google-genai`
- `google-cloud-speech`
- `google-cloud-texttospeech`
- `requests`
- `replit`
- `psycopg2-binary`
- `Flask-Login`
- `Flask-WTF`
- `passlib`
- `python-dotenv`
- `python-telegram-bot`
- `pydub`