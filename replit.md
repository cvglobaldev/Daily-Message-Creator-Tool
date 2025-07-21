# Faith Journey Drip Content - WhatsApp Chatbot

## Overview

This is a WhatsApp-based chatbot designed to guide young adults (18-24) from Muslim backgrounds on a 30-day spiritual journey to learn about Jesus. The system delivers daily content, collects reflections, and uses AI to analyze user responses for engagement tracking.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with Python
- **Database**: Replit Database (key-value store) for user data and message logging
- **AI Integration**: Google Gemini API for response sentiment analysis and keyword tagging
- **Messaging**: WhatsApp Business API integration with fallback simulation mode
- **Scheduling**: Background thread-based scheduler for daily content delivery

### Key Design Decisions
- **Simple Storage**: Uses Replit's built-in database instead of complex SQL databases for rapid MVP development
- **Simulation Mode**: Includes development-friendly message simulation when API credentials aren't available
- **Thread-based Scheduling**: Uses background threads instead of external cron jobs for simplicity in Replit environment
- **Cultural Sensitivity**: Designed specifically for Muslim-to-Christian spiritual journey with appropriate terminology

## Key Components

### Database Manager (`database.py`)
- Handles user CRUD operations with phone numbers as primary keys
- Stores user data as JSON strings in key-value format
- Manages user status tracking (active/inactive)
- Uses prefixed keys (`users:phone_number`) for organization

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
- Uses Replit's built-in database for zero-configuration data storage
- Includes simulation modes for development without external API setup
- Background scheduler runs as application thread (no separate cron needed)
- Static files and templates included for admin dashboard

### Scaling Considerations
- Current design supports moderate user loads with thread-based scheduling
- Database uses simple key-value storage suitable for MVP scale
- Rate limiting implemented to respect API quotas
- Graceful error handling prevents system crashes

### Development vs Production
- **Development Mode**: Simulates WhatsApp messages, uses console logging
- **Production Mode**: Requires actual API credentials, sends real messages
- Environment-based configuration switches between modes automatically