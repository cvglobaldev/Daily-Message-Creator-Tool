# Daily Message Creator - WhatsApp Chatbot

## Overview
This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide individuals from diverse non-Christian backgrounds through a spiritual journey to learn about Jesus. It delivers daily drip content, collects user reflections, and uses AI to analyze responses for engagement tracking and insights. The system aims to facilitate culturally sensitive spiritual exploration of customizable duration (10-90 days), enabling users to engage with Christian teachings at their own pace. The project's business vision is to provide a scalable and accessible tool for spiritual guidance, leveraging AI for personalized user interaction and content generation, with the ambition to reach a global audience.

## User Preferences
Preferred communication style: Simple, everyday language.

## Recent Changes

### Bug Fix: Duplicate Completion Messages (October 9, 2025)
**Issue**: Telegram Bot 1 users on day 11 were receiving the completion message repeatedly every 10 minutes. The bot also appeared unresponsive to START/STOP commands.

**Root Cause**: 
- Bot 1 had content gaps (days 11-14 missing, only 1-10 and 15 available)
- Users reaching day 11 had no content to receive
- Scheduler repeatedly triggered `_handle_content_completion()` every 10 minutes
- Users remained in 'active' status, causing the scheduler to keep checking them
- Each check resulted in sending the completion message again

**Fix Implemented**:
1. Added duplicate message prevention in `_handle_content_completion()`:
   - Checks if completion message was sent in the last 24 hours
   - If found, skips sending the message
   - Marks user as 'completed' to stop scheduler checks
2. Changed completion logic to always mark users as 'completed' when no content is available
3. Updated affected users (tg_960173404, tg_616955431, tg_1021333375) to 'completed' status

**Files Modified**:
- `scheduler.py`: Enhanced `_handle_content_completion()` with duplicate prevention logic

### Bug Fix: Missing Media on Restart/Start Commands (October 9, 2025)
**Issue**: When users restart their journey (START/STOP command), the welcome and Day 1 content were not showing media (images/videos), but Day 2 and subsequent days showed media correctly.

**Root Cause**:
- The `handle_start_command()` function was only sending text messages
- It completely ignored the `media_type` field and associated media files (image_filename, video_filename, etc.)
- Meanwhile, the scheduler's normal delivery properly handled media using `_deliver_content_with_reflection()`
- This created an inconsistency between fresh start and scheduled content delivery

**Fix Implemented**:
1. Modified `handle_start_command()` to use the scheduler's `_deliver_content_with_reflection()` method
2. This method properly:
   - Checks the content's `media_type`
   - Validates if media files exist on disk
   - Constructs proper media URLs
   - Sends media (image/video/audio) first, then text content
   - Includes confirmation buttons
3. Applied fix to both restart path (existing users) and new user onboarding path

**Data Issue Discovered**:
- Day 1 content has `media_type = 'image'` but no actual `image_filename` in the database
- To fully resolve: Upload an image for Day 1 content via CMS, or change media_type to 'text'

**Files Modified**:
- `main.py`: Updated `handle_start_command()` to use scheduler's media delivery method for both restart and new user paths

### Enhancement: WhatsApp Welcome Message Media Support + Delivery Order Fix (October 9, 2025)
**Issues**: 
1. WhatsApp Bot 2 welcome message was ignoring video media configured in greeting
2. Content delivery showed wrong order: Text → Video → Buttons (should be Video → Text → Buttons)

**Root Causes**:
1. Welcome message code only sent text content from greeting, never checked for media files
2. Media and text were sent as **separate messages**, causing WhatsApp to display them out of order

**Fix Implemented**:
1. **Welcome Message Media Support** (main.py lines 1665-1722):
   - Now checks if greeting has media (video/image/audio)
   - Validates media file exists on disk
   - Sends media WITH text as caption (single message for proper order)
   - For video: `send_video(phone_number, media_url, caption=welcome_message)`
   - For image: `send_media_message(phone_number, 'image', media_url, caption=welcome_message)`
   - Audio sent separately (WhatsApp doesn't support audio captions)
   - Falls back to text-only if no media or file missing

2. **Content Delivery Order Fix** (scheduler.py lines 415-450):
   - Changed from sending media + separate text → sends media WITH text as caption
   - For video: `send_video(phone_number, media_url, caption=message)`
   - For image: `send_media_message(phone_number, 'image', media_url, caption=message)`
   - Ensures proper order: Media (with caption) → Buttons
   - No more WhatsApp message reordering issues

**Result**:
- ✅ Welcome message now includes video with text as caption
- ✅ Content delivery order correct: Media appears first with text as caption
- ✅ Confirmation buttons appear after content (separate message)
- ✅ Consistent experience across restart and scheduled delivery

**Files Modified**:
- `main.py`: Added media support to welcome/greeting messages in `handle_start_command()`
- `scheduler.py`: Fixed content delivery order using caption parameter for WhatsApp media

## System Architecture
The system is a scalable and maintainable Flask web application in Python, utilizing a PostgreSQL relational database. It supports multiple independent bot instances, each with its own content, users, and configurations.

### UI/UX Decisions
A consistent "CV Global" design theme is applied across all management interfaces (dashboard, bot management, CMS, chat management) with professional branding and consistent color schemes.

### Technical Implementations
- **Backend**: Flask web application with Python.
- **Database**: PostgreSQL for all data storage.
- **AI Integration**: Leverages Google Gemini API for sentiment analysis, keyword tagging, and AI-powered content generation.
- **Messaging Integration**: Integrates with WhatsApp Business API and Telegram Bot API for multi-platform support.
- **Scheduling**: A background thread-based scheduler manages daily content delivery and user progression.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, CRUD operations, multimedia delivery, and support for configurable journey durations (10, 30, 60, 90 days) and predefined faith journey tags.
- **AI Content Generation**: Integrated AI-powered content creation using Google Gemini 2.5 Pro, offering audience customization (language, religion, age group, cultural background).
- **Chat Management System**: Provides an interface for consolidated user conversations, message sending, human handoff detection, real-time analytics, and user profiles.
- **Authentication**: Implements Flask-Login for secure password hashing, session management, and role-based access control.
- **Voice Conversation Feature**: Includes end-to-end voice message handling with language-aware transcription and synthesis. Uses Google Cloud Speech-to-Text and Text-to-Speech APIs with automatic language detection based on bot configuration. Supports multiple languages (English, Indonesian, Hindi, Arabic, Spanish, French, Burmese, Chinese, Portuguese, Hausa) with platform-specific audio format support (MP3 for WhatsApp, OGG_OPUS for Telegram). Centralized language mapping system ensures accurate voice processing across all supported languages.
- **Dual-Layer Tagging System**: Combines AI semantic analysis with rule-based automation (When-If-Then logic) for comprehensive message tagging.
- **Atomic Lock System**: Implements a database-backed atomic locking system using PostgreSQL for duplicate message prevention during content delivery.

### System Design Choices
- **Multi-Bot System**: Enables creation and management of independent bots, each with its own content, user base, AI prompts, and platform configurations.
- **Culturally Sensitive Content**: Content is designed for diverse non-Christian backgrounds.
- **AI Response Analysis**: AI analyzes user reflections for sentiment and tags them with spiritual milestones.
- **Command System**: Recognizes user commands like "START," "STOP," "HELP," and "HUMAN."
- **User Progression**: Tracks user progress through customizable journey durations (10-90 days).
- **Error Handling & Simulation**: Includes robust error handling, user deactivation for inactive chats, and development-friendly API simulation modes.
- **Phone Number Normalization**: Automatically handles various phone number formats.
- **Media Management**: Comprehensive system for managing media files, including prevention of broken references.
- **Contextual AI Response System**: AI responses are contextually aware of the user's current daily content, journey stage, and spiritual topic.
- **Human Connection Option System**: Proactively offers users the option to connect with a human team member for sensitive topics, with intelligent detection and user choice priority.

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