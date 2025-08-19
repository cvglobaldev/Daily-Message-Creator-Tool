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