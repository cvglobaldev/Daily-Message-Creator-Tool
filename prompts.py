"""
Prompts and templates for the Faith Journey application
"""

# System prompt for Gemini API response analysis
RESPONSE_ANALYSIS_PROMPT = """
You are an expert at analyzing religious and spiritual text responses from users who are on a faith journey learning about Jesus (Isa al-Masih) from a Muslim background.

Your task is to analyze user responses and provide:

1. **Sentiment Analysis**: Classify as "positive", "negative", or "neutral"
   - Positive: Shows interest, appreciation, hope, peace, gratitude, openness
   - Negative: Shows rejection, anger, fear, sadness, strong disagreement
   - Neutral: Questions, uncertainty, simple acknowledgments, factual responses

2. **Keyword Tagging**: Select relevant tags from this predefined list:
   - "Bible Engagement" - User references or asks about biblical content
   - "Gospel Presentation" - User responds to core gospel messages
   - "Christian Learning" - User shows interest in learning about Christianity
   - "Bible Exposure" - User mentions being exposed to biblical concepts
   - "Salvation Prayer" - User expresses interest in prayer or salvation
   - "Question" - User asks questions about faith or content
   - "Doubt" - User expresses doubts or concerns
   - "Positive Feedback" - User gives positive feedback about content
   - "Negative Feedback" - User gives negative feedback
   - "Spiritual Seeking" - User shows spiritual curiosity or seeking
   - "Personal Story" - User shares personal experiences or stories
   - "Gratitude" - User expresses thankfulness
   - "Confusion" - User expresses confusion or need for clarification
   - "Interest" - User shows general interest in continuing

3. **Confidence Score**: Rate your confidence in the analysis from 0.0 to 1.0

**Important Guidelines:**
- Be culturally sensitive to Muslim background and terminology
- Consider that users may use Islamic terms when discussing Christian concepts
- Look for genuine engagement even if expressed hesitantly
- Multiple tags can be applied if relevant
- Focus on the user's heart attitude, not just surface words

**Response Format:** 
Provide a JSON response with exactly these fields:
- "sentiment": string (positive/negative/neutral)
- "tags": array of strings (from predefined list only)
- "confidence": number between 0.0 and 1.0

User Response to Analyze: {user_response}
"""

# System prompt for generating contextual responses to user reflections
CONTEXTUAL_RESPONSE_PROMPT = """
You are a compassionate faith journey guide helping a user from a Muslim background learn about Jesus (Isa al-Masih). The user has just shared their reflection on today's content.

**Your role:**
- Provide a warm, encouraging response that acknowledges their reflection
- Answer any faith questions they may have raised
- Connect their thoughts back to the day's content when appropriate
- Use respectful language that bridges Islamic and Christian terminology
- Be authentic and avoid generic responses
- Keep responses personal and conversational (2-3 sentences max)

**Today's Content Context:**
Day {day_number}: {content_title}
Content: {content_text}
Reflection Question: {reflection_question}

**User's Reflection:**
{user_reflection}

**Guidelines:**
- If they ask a faith question, provide a thoughtful, biblical answer
- If they share a personal insight, affirm and build on it
- If they express doubt or confusion, address it with grace
- Use terms like "Isa al-Masih (Jesus)" when referring to Jesus
- Reference Islamic concepts when it helps bridge understanding
- Be encouraging about their spiritual journey
- Don't be preachy or overly theological

Provide a natural, contextual response that feels like a caring mentor responding to their specific reflection:
"""

# Welcome messages and templates
WELCOME_MESSAGE = """
As-salamu alaykum and welcome to your Faith Journey! 🌟

Over the next 30 days, you'll receive daily content exploring the life and teachings of Isa al-Masih (Jesus) in a way that respects your background and encourages thoughtful reflection.

Each day, you'll receive:
📖 A piece of content (text, image, or video)
💭 A simple reflection question
🕰️ Daily delivery at 8:00 AM

Commands you can use anytime:
• HELP - Get help and see available commands
• STOP - Unsubscribe from the journey

Let's begin your journey with Day 1 content!
"""

HELP_MESSAGE = """
📖 Faith Journey Help

**Available Commands:**
• START - Begin or restart your 30-day journey
• STOP - Unsubscribe from daily messages  
• HELP - Show this help message

**How it works:**
• You'll receive daily content at 8:00 AM
• After each content piece, you'll get a reflection question
• Share your thoughts freely - there are no wrong answers
• Your responses help us understand your journey

**Need human support?**
If you need to speak with someone, just let us know by saying "talk to someone" or "I need help".

May your journey be blessed with peace and understanding. 🙏
"""

STOP_CONFIRMATION_MESSAGE = """
You have been unsubscribed from the Faith Journey.

If you'd like to restart your journey at any time, simply send START.

Thank you for the time you spent with us. May peace be with you. 🙏
"""

HUMAN_HANDOFF_MESSAGE = """
Thank you for reaching out. A member of our team will contact you shortly to provide the support you need.

In the meantime, know that you are valued and your journey matters. 

Peace be with you. 🙏
"""

COMPLETION_MESSAGE = """
🎉 **Congratulations!** 🎉

You have completed your 30-day Faith Journey exploring the life and teachings of Isa al-Masih (Jesus).

**What you've accomplished:**
✅ 30 days of dedicated learning and reflection
✅ Engaged with diverse content about Jesus
✅ Shared your thoughts and insights
✅ Grown in understanding across faith traditions

**Your journey doesn't have to end here.**
If you'd like to continue exploring, have questions, or want to speak with someone about your experience, just let us know.

Thank you for your openness, curiosity, and thoughtful participation.

May you continue to walk in light and peace. 🙏

*Type "talk to someone" if you'd like to connect with a person from our team.*
"""

# Reflection question acknowledgments
REFLECTION_ACKNOWLEDGMENTS = [
    "Thank you for sharing your heart. Your reflection is valued. 🙏",
    "I appreciate you taking the time to think deeply about this.",
    "Your thoughts are meaningful. Thank you for sharing them with us.",
    "Thank you for your honest reflection. Your journey matters.",
    "Your openness to reflect and share is a gift. Thank you. 💙",
    "I'm grateful for your thoughtful response. Keep reflecting!",
    "Your words show a sincere heart. Thank you for sharing.",
    "Thank you for engaging so thoughtfully with today's content."
]

# Error messages
ERROR_MESSAGES = {
    "general": "Sorry, there was an issue processing your message. Please try again or type HELP for assistance.",
    "content_not_found": "We're having trouble accessing today's content. Please try again later or contact support.",
    "user_not_found": "We couldn't find your journey information. Type START to begin your faith journey.",
    "api_error": "We're experiencing technical difficulties. Your message is important to us - please try again in a few minutes."
}

# Content templates for different media types
CONTENT_TEMPLATES = {
    "text": "📖 Day {day} - Faith Journey\n\n{content_text}",
    "image": "📖 Day {day} - Faith Journey\n\n{content_text}\n\n🖼️ Please see the image below:",
    "video": "📖 Day {day} - Faith Journey\n\n{content_text}\n\n🎥 Watch the video here: {media_url}",
    "audio": "📖 Day {day} - Faith Journey\n\n{content_text}\n\n🎵 Listen to the audio here: {media_url}"
}

REFLECTION_QUESTION_TEMPLATE = """
💭 **Reflection Question for Day {day}:**

{reflection_question}

Take your time to think about it. When you're ready, share your thoughts - there are no right or wrong answers, just your honest reflection.
"""

# Sample content for testing (culturally contextualized)
SAMPLE_CONTENT = {
    1: {
        "day": 1,
        "media_type": "text", 
        "content_text": "As-salamu alaykum and welcome to your Faith Journey. We're glad you're here. In the holy Injil, the prophet Isa al-Masih (Jesus) is often described as a light. He said, 'I am the light of the world. Whoever follows me will never walk in darkness, but will have the light of life.' (John 8:12)",
        "media_url": None,
        "reflection_question": "What does the idea of 'light' mean to you in your own life?"
    },
    2: {
        "day": 2,
        "media_type": "text",
        "content_text": "In Islamic tradition, we know that Allah is Ar-Rahman (The Compassionate) and Ar-Raheem (The Merciful). The Injil teaches us that Isa al-Masih showed this same divine compassion. When he saw people who were hurting, 'he had compassion on them, because they were harassed and helpless, like sheep without a shepherd.' (Matthew 9:36)",
        "media_url": None,
        "reflection_question": "When have you experienced compassion from others? How did it make you feel?"
    },
    3: {
        "day": 3,
        "media_type": "text",
        "content_text": "The Quran speaks of Isa al-Masih as 'Kalimatullah' (Word of Allah). In the Injil, we read: 'In the beginning was the Word, and the Word was with Allah, and the Word was Allah... The Word became flesh and made his dwelling among us.' (John 1:1,14) This profound truth shows us that Jesus was not just a messenger, but the very expression of Allah's love coming to earth.",
        "media_url": None,
        "reflection_question": "What do you think it means that Jesus is called the 'Word of Allah'?"
    }
}
