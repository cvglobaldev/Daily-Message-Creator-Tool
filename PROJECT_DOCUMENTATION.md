# Faith Journey Drip Content Chatbot - Project Documentation

## Overview

The Faith Journey Drip Content Chatbot is an advanced AI-powered spiritual guidance system designed to guide people from diverse non-Christian backgrounds through a structured spiritual journey to learn about Jesus Christ. The system supports both WhatsApp and Telegram platforms with configurable automated content delivery (10-90 days), AI-powered content generation, multi-bot management, and comprehensive analytics.

## Project Goals

- Provide culturally sensitive spiritual guidance for people from any non-Christian background (Muslim, Hindu, Buddhist, Secular, etc.)
- Deliver structured daily content over configurable periods (10-90 days, default 30)
- Support multiple languages and cultural contexts through multi-bot architecture
- Track spiritual journey milestones through AI-powered analysis
- Enable human intervention when needed through intelligent handoff detection

## System Architecture

### Backend Framework
- **Flask Web Application**: Python-based web framework handling all API endpoints and web interfaces
- **PostgreSQL Database**: Full relational database with proper schemas, relationships, and indexing
- **Gunicorn Server**: Production-grade WSGI server for deployment
- **Threading**: Background scheduler runs in separate daemon threads

### Multi-Platform Support
- **WhatsApp Business API**: For WhatsApp message delivery (with simulation mode for development)
- **Telegram Bot API**: Real-time Telegram bot integration with webhook support
- **Platform Detection**: Automatic user platform identification and appropriate routing

### AI Integration
- **Google Gemini 2.5 Flash**: Advanced AI for contextual response generation and sentiment analysis
- **Faith Journey Tagging**: Automatic milestone detection (Introduction to Jesus, Gospel Presentation, Prayer, etc.)
- **Contextual Responses**: AI uses bot-specific daily content for personalized user interactions

### Multi-Bot Management
- **Bot Isolation**: Complete separation between different bots for different audiences and languages
- **Platform Configuration**: Independent WhatsApp/Telegram setup per bot
- **Content Isolation**: Each bot has its own content library and user base
- **Token Management**: Separate API tokens for each bot's messaging services
- **AI Content Generation**: Automated content creation with audience-specific customization for different cultural and religious backgrounds

## Key Features

### 1. Automated Content Delivery
- **Scheduled Delivery**: Background scheduler delivers content at configurable intervals
- **Journey Progression**: Users automatically advance through daily content
- **Duplicate Prevention**: System prevents sending same content multiple times
- **Media Support**: Images, videos, audio files, and text content delivery

### 2. Content Management System (CMS)
- **CRUD Operations**: Create, read, update, delete content for any day of journey
- **Media Upload**: Support for images, videos, audio files with preview functionality
- **Faith Journey Tags**: Predefined tags for content categorization and milestone tracking
- **Bot-Specific Content**: Each bot maintains its own content library
- **AI Content Generation**: Automated creation of complete journey content (10-90 days) using Google Gemini 2.5 Pro with audience-specific prompts for different cultural and religious backgrounds

### 3. User Management
- **User Registration**: Automatic user creation on first interaction
- **Journey Tracking**: Current day, completion status, and progress monitoring
- **Location Detection**: IP-based location detection and user profiling
- **Premium Support**: Premium user identification and special handling

### 4. Chat Management Interface
- **Conversation History**: Full chat history with message threading
- **Manual Tagging**: Admin interface for faith journey milestone tagging
- **Human Handoff**: Automatic detection and flagging of messages requiring human intervention
- **Message Export**: Export chat histories for record keeping

### 5. AI Analysis System
- **Sentiment Analysis**: Real-time emotional state analysis of user messages
- **Faith Journey Milestones**: Automatic detection of spiritual progress markers
- **Keyword Tagging**: Intelligent tagging based on message content
- **Confidence Scoring**: AI confidence levels for analysis accuracy

### 6. Administrative Dashboard
- **User Statistics**: Real-time metrics on user engagement and progress
- **Message Analytics**: Comprehensive message flow and sentiment tracking
- **Bot Management**: Multi-bot configuration and status monitoring
- **Human Handoff Queue**: Priority queue for messages requiring human attention

### 7. AI Content Generation System
- **Automated Content Creation**: Generate complete spiritual journeys (10-90 days) using Google Gemini 2.5 Pro
- **Audience Customization**: Target specific demographics with cultural and religious background considerations
- **Language Support**: Create content in multiple languages for diverse audiences
- **Cultural Sensitivity**: Built-in prompts ensure respectful content for different faith backgrounds (Muslim, Hindu, Buddhist, Secular, etc.)
- **Content Quality**: AI generates daily messages with reflection questions, spiritual themes, and progressive journey structure
- **Toggle Activation**: User-friendly form interface with validation and error handling
- **Flexible Duration**: Support for 10, 30, or 90-day journey durations with appropriate content depth

## Technical Implementation

### Database Schema

#### Users Table
- Primary user information (phone, name, location, premium status)
- Journey tracking (current_day, join_date, completion_date)
- Bot assignment (bot_id for multi-bot isolation)
- Platform identification (WhatsApp/Telegram)

#### Bots Table
- Bot configuration (name, description, journey_days)
- Platform settings (WhatsApp tokens, Telegram tokens)
- AI customization (custom prompts, response style)
- Status management (active/inactive)

#### Content Table
- Daily content storage (day_number, title, content text)
- Media attachments (image, video, audio filenames)
- Reflection questions for user engagement
- Faith journey tags and bot assignment

#### Message Logs Table
- Complete message history (raw_text, direction, timestamp)
- AI analysis results (sentiment, tags, confidence)
- Human handoff flags and priority markers
- User relationship and bot tracking

### API Endpoints

#### Bot Management
- `/api/bots` - List and create bots
- `/api/bots/{id}` - Update and delete specific bots
- `/api/bots/{id}/content` - Bot-specific content management

#### Content Management
- `/api/content` - CRUD operations for daily content
- `/api/upload/image` - Image file upload handling
- `/api/upload/video` - Video file upload handling
- `/api/upload/audio` - Audio file upload handling

#### Chat Management
- `/api/chat-management/messages` - Filtered message retrieval
- `/api/send-admin-message` - Manual message sending
- `/api/update-message-tags` - Manual tag editing
- `/api/export-user-chat/{id}` - Chat export functionality

#### Platform Webhooks
- `/telegram` - Default bot webhook (Bot 1)
- `/telegram/{bot_id}` - Bot-specific webhook routing
- `/whatsapp` - WhatsApp webhook handling

### Scheduling System

#### Background Scheduler
- **Threading Model**: Daemon thread running parallel to web application
- **Configurable Intervals**: Currently 10 minutes for testing (600 seconds)
- **Production Ready**: Easily configurable to 24-hour intervals for production
- **Error Handling**: Automatic recovery and logging of delivery failures

#### Content Delivery Logic
1. **User Retrieval**: Get all active users from database
2. **Duplicate Check**: Verify user hasn't received current day content
3. **Content Fetching**: Retrieve bot-specific content for user's current day
4. **Platform Routing**: Send via appropriate service (WhatsApp/Telegram)
5. **Progress Update**: Advance user to next day and log delivery

## Multi-Bot Configuration

### Bot 1: English Faith Journey
- **Target Audience**: English-speaking users
- **Content Style**: Western Christian terminology and approach
- **Platform**: Telegram and WhatsApp support
- **Journey Length**: Configurable (default 30 days)

### Bot 2: Indonesian Bang Kris
- **Target Audience**: Indonesian-speaking Muslim background
- **Content Style**: Culturally sensitive Islamic-to-Christian bridge content
- **Language**: Bahasa Indonesia with Islamic terminology (Isa al-Masih, Allah SWT)
- **Platform**: Telegram with token 8342973377:AAF3pdo5YH6AkBosijP0G7Rct542_4GlEu4

## Faith Journey Milestone Tags

### Core Milestones
- **Introduction to Jesus (ITJ)**: First exposure to Jesus content
- **Gospel Presentation**: Clear gospel message delivery
- **Prayer**: User engaging in prayer or prayer requests
- **Bible Exposure**: Introduction to biblical content
- **Bible Engagement**: Active biblical study or questions
- **Christian Learning**: Deeper theological education
- **Salvation Prayer**: Decision prayer or conversion moment
- **Holy Spirit Empowerment**: Spiritual gifts and growth

### Status Tags
- **Human**: Requires human intervention
- **Blocked**: User has blocked or stopped communication
- **Already in church**: User already Christian/in church
- **Not connected**: No response or engagement
- **Not genuine**: Suspected fake or testing account
- **No response**: User silent after content delivery

## Security and Privacy

### Data Protection
- **Secure File Handling**: All uploads validated and securely stored
- **Environment Variables**: Sensitive credentials stored as environment secrets
- **Session Management**: Secure session handling for admin interfaces
- **Input Validation**: All user inputs sanitized and validated

### Authentication
- **Admin Authentication**: Login required for all management interfaces
- **Role-Based Access**: Different permission levels for admin users
- **Session Security**: Secure session management with timeout handling

## Deployment Configuration

### Environment Variables
- `TELEGRAM_BOT_TOKEN`: Default bot token for Bot 1
- `WHATSAPP_ACCESS_TOKEN`: WhatsApp Business API token
- `WHATSAPP_PHONE_NUMBER_ID`: WhatsApp business phone number
- `GEMINI_API_KEY`: Google Gemini API key for AI analysis
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: PostgreSQL database connection string

### Production Settings
- **Database**: PostgreSQL with connection pooling and pre-ping
- **File Storage**: Static file serving for uploaded media
- **Error Handling**: Comprehensive logging and error recovery
- **Rate Limiting**: API call throttling to respect service limits

## Development vs Production

### Development Mode Features
- **Simulation Mode**: WhatsApp and Telegram message simulation
- **Rapid Testing**: 10-minute content delivery intervals
- **Debug Logging**: Verbose logging for troubleshooting
- **Console Output**: Real-time debug information

### Production Mode Features
- **Live API Integration**: Real WhatsApp and Telegram message delivery
- **24-Hour Intervals**: Daily content delivery schedule
- **Performance Optimization**: Database connection pooling and caching
- **Error Recovery**: Automatic retry and fallback mechanisms

## Monitoring and Analytics

### Real-Time Metrics
- **User Engagement**: Active users, message counts, journey completion rates
- **Sentiment Tracking**: Emotional state analysis and trends
- **Milestone Progress**: Faith journey advancement tracking
- **Platform Distribution**: WhatsApp vs Telegram usage statistics

### Administrative Tools
- **Chat Management**: Real-time conversation monitoring
- **Manual Intervention**: Human takeover capabilities
- **Content Performance**: Engagement metrics per content piece
- **Error Monitoring**: System health and delivery success rates

## Future Enhancements

### Planned Features
- **Multi-Language Support**: Additional language bots beyond English and Indonesian
- **Advanced AI Training**: Custom AI models trained on faith journey conversations
- **Mobile App**: Dedicated mobile application for enhanced user experience
- **Video Calling**: Integration with video calling platforms for human handoff

### Scalability Considerations
- **Microservices**: Breaking system into independent services
- **Cloud Deployment**: Migration to cloud infrastructure for global reach
- **CDN Integration**: Content delivery network for media files
- **Load Balancing**: Multiple server instances for high availability

## Technical Support

### System Requirements
- **Python 3.11+**: Core runtime environment
- **PostgreSQL 12+**: Database server
- **Redis**: Optional caching layer for performance
- **SSL Certificates**: HTTPS support for webhook endpoints

### Maintenance Procedures
- **Database Backups**: Regular automated backups
- **Log Rotation**: Automated log management
- **Security Updates**: Regular dependency updates
- **Performance Monitoring**: Continuous system health checks

This documentation provides a comprehensive overview of the Faith Journey Drip Content Chatbot system, covering all major components, features, and technical implementation details.