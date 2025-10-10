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