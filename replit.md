# Daily Message Creator - WhatsApp Chatbot

## Overview
This project is a multi-platform chatbot (WhatsApp and Telegram) designed to guide individuals from diverse non-Christian backgrounds through a spiritual journey to learn about Jesus. It delivers daily drip content, collects user reflections, and uses AI to analyze responses for engagement tracking and insights. The system aims to facilitate culturally sensitive spiritual exploration of customizable duration (10-90 days), enabling users to engage with Christian teachings at their own pace. The project's business vision is to provide a scalable and accessible tool for spiritual guidance, leveraging AI for personalized user interaction and content generation, with the ambition to reach a global audience.

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
- **Messaging Integration**: Integrates with WhatsApp Business API and Telegram Bot API for multi-platform support.
- **Scheduling**: A background thread-based scheduler manages daily content delivery and user progression.
- **Content Management System (CMS)**: Features an advanced content editor with live preview, tag management, CRUD operations, multimedia delivery, and support for configurable journey durations (10, 30, 60, 90 days) and predefined faith journey tags.
- **AI Content Generation**: Integrated AI-powered content creation using Google Gemini 2.5 Pro, offering audience customization (language, religion, age group, cultural background).
- **Chat Management System**: Provides an interface for consolidated user conversations, message sending, human handoff detection, real-time analytics, and user profiles.
- **Authentication**: Implements Flask-Login for secure password hashing, session management, and role-based access control.
- **Voice Conversation Feature**: Includes end-to-end voice message handling with language-aware transcription and synthesis. Uses Google Cloud Speech-to-Text and Text-to-Speech APIs with automatic language detection based on bot configuration. Supports multiple languages (English, Indonesian, Hindi, Arabic, Spanish, French, Burmese, Chinese, Portuguese) with platform-specific audio format support (MP3 for WhatsApp, OGG_OPUS for Telegram). Centralized language mapping system ensures accurate voice processing across all supported languages.
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