import os
import json
import logging
import requests
from typing import Dict, Any, List
from google import genai
from google.genai import types
from pydantic import BaseModel
import random

logger = logging.getLogger(__name__)

class TelegramService:
    """Service for Telegram Bot API integration"""
    
    def __init__(self):
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # For development, we'll simulate message sending
        self.simulate_mode = not self.bot_token
        
        if self.simulate_mode:
            logger.warning("Telegram service running in simulation mode (no bot token)")
        else:
            logger.info("Telegram service initialized with bot token")
    
    def send_message(self, chat_id: str, message: str) -> bool:
        """Send a text message via Telegram"""
        try:
            if self.simulate_mode:
                # Simulate message sending for development
                print(f"\n📱 TELEGRAM MESSAGE TO {chat_id}:")
                print(f"   {message}")
                print("   ✅ Message simulated (development mode)")
                return True
            
            url = f"{self.api_base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"  # Allow HTML formatting
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent successfully to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send Telegram message to {chat_id}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message to {chat_id}: {e}")
            return False
    
    def set_webhook(self, webhook_url: str, secret_token: str = "") -> bool:
        """Set webhook URL for receiving messages"""
        try:
            if self.simulate_mode:
                print(f"📡 TELEGRAM WEBHOOK SETUP (simulated):")
                print(f"   URL: {webhook_url}")
                print(f"   Secret Token: {'*' * len(secret_token) if secret_token else 'None'}")
                print("   ✅ Webhook setup simulated")
                return True
            
            url = f"{self.api_base_url}/setWebhook"
            payload = {
                "url": webhook_url
            }
            
            if secret_token:
                payload["secret_token"] = secret_token
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    logger.info(f"Telegram webhook set successfully to {webhook_url}")
                    return True
                else:
                    logger.error(f"Telegram webhook setup failed: {result.get('description', 'Unknown error')}")
                    return False
            else:
                logger.error(f"Failed to set Telegram webhook: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting Telegram webhook: {e}")
            return False
    
    def get_webhook_info(self) -> Dict[str, Any]:
        """Get current webhook information"""
        try:
            if self.simulate_mode:
                return {
                    "url": "https://example.com/webhook",
                    "has_custom_certificate": False,
                    "pending_update_count": 0,
                    "simulated": True
                }
            
            url = f"{self.api_base_url}/getWebhookInfo"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result.get("result", {})
            
            return {}
                
        except Exception as e:
            logger.error(f"Error getting Telegram webhook info: {e}")
            return {}
    
    def get_me(self) -> Dict[str, Any]:
        """Get basic information about the bot"""
        try:
            if self.simulate_mode:
                return {
                    "id": 123456789,
                    "is_bot": True,
                    "first_name": "Faith Journey Bot",
                    "username": "faithjourney_bot",
                    "simulated": True
                }
            
            url = f"{self.api_base_url}/getMe"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result.get("result", {})
            
            return {}
                
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return {}

class WhatsAppService:
    """Service for WhatsApp Business API integration"""
    
    def __init__(self):
        self.access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # For development, we'll simulate message sending
        self.simulate_mode = not (self.access_token and self.phone_number_id)
        
        if self.simulate_mode:
            logger.warning("WhatsApp service running in simulation mode (no API credentials)")
    
    def send_message(self, to: str, message: str) -> bool:
        """Send a text message via WhatsApp"""
        try:
            if self.simulate_mode:
                # Simulate message sending for development
                print(f"\n📱 WHATSAPP MESSAGE TO {to}:")
                print(f"   {message}")
                print("   ✅ Message simulated (development mode)")
                return True
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to.replace('+', ''),  # Remove + from phone number
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {to}")
                return True
            else:
                logger.error(f"Failed to send message to {to}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message to {to}: {e}")
            return False
    
    def send_media_message(self, to: str, media_type: str, media_url: str, caption: str = "") -> bool:
        """Send a media message (image, video, audio) via WhatsApp"""
        try:
            if self.simulate_mode:
                # Simulate media message sending
                print(f"\n📱 WHATSAPP MEDIA MESSAGE TO {to}:")
                print(f"   Type: {media_type}")
                print(f"   URL: {media_url}")
                if caption:
                    print(f"   Caption: {caption}")
                print("   ✅ Media message simulated (development mode)")
                return True
            
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Map media types to WhatsApp API format
            media_mapping = {
                "image": "image",
                "video": "video", 
                "audio": "audio"
            }
            
            whatsapp_type = media_mapping.get(media_type, "document")
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to.replace('+', ''),
                "type": whatsapp_type,
                whatsapp_type: {
                    "link": media_url
                }
            }
            
            if caption and whatsapp_type in ["image", "video"]:
                payload[whatsapp_type]["caption"] = caption
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Media message sent successfully to {to}")
                return True
            else:
                logger.error(f"Failed to send media message to {to}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending media message to {to}: {e}")
            return False


class ResponseAnalysis(BaseModel):
    sentiment: str
    tags: List[str]
    confidence: float


class GeminiService:
    """Service for Google Gemini API integration"""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        
        if not self.api_key:
            logger.warning("No Gemini API key found, using fallback analysis")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("Gemini client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Gemini client: {e}")
                self.client = None
        
        # Predefined tags for classification
        self.predefined_tags = [
            "Bible Engagement",
            "Gospel Presentation", 
            "Christian Learning",
            "Bible Exposure",
            "Salvation Prayer",
            "Question",
            "Doubt",
            "Positive Feedback",
            "Negative Feedback",
            "Spiritual Seeking",
            "Personal Story",
            "Gratitude",
            "Confusion",
            "Interest"
        ]
    
    def analyze_response(self, text: str) -> Dict[str, Any]:
        """Analyze user response for sentiment and tags"""
        try:
            if not self.client:
                # Fallback analysis if Gemini is not available
                return self._fallback_analysis(text)
            
            # Create system prompt for analysis
            system_prompt = f"""
            You are an expert at analyzing religious and spiritual text responses. 
            
            Analyze the following user response and provide:
            1. Sentiment: One of "positive", "negative", or "neutral"
            2. Tags: Select relevant tags from this list: {', '.join(self.predefined_tags)}
            3. Confidence: A number between 0.0 and 1.0 indicating how confident you are in the analysis
            
            Consider cultural sensitivity, especially for users from Muslim backgrounds who may be learning about Christian concepts.
            
            Response format: JSON with fields "sentiment", "tags" (array), and "confidence" (number).
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(role="user", parts=[types.Part(text=f"Analyze this response: {text}")])
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=ResponseAnalysis,
                ),
            )
            
            if response.text:
                analysis_data = json.loads(response.text)
                
                # Validate and clean the response
                sentiment = analysis_data.get("sentiment", "neutral").lower()
                if sentiment not in ["positive", "negative", "neutral"]:
                    sentiment = "neutral"
                
                tags = analysis_data.get("tags", [])
                # Filter tags to only include predefined ones
                filtered_tags = [tag for tag in tags if tag in self.predefined_tags]
                
                confidence = float(analysis_data.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp between 0 and 1
                
                result = {
                    "sentiment": sentiment,
                    "tags": filtered_tags if filtered_tags else ["Christian Learning"],
                    "confidence": confidence
                }
                
                logger.info(f"Gemini analysis completed: {result}")
                return result
            
            else:
                logger.warning("Empty response from Gemini, using fallback")
                return self._fallback_analysis(text)
                
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            return self._fallback_analysis(text)
    
    def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Fallback analysis when Gemini is not available"""
        text_lower = text.lower()
        
        # Simple sentiment analysis
        positive_words = ["good", "great", "love", "peace", "hope", "beautiful", "amazing", "wonderful", "blessed", "grateful", "thank", "inspiring"]
        negative_words = ["bad", "hate", "sad", "angry", "confused", "difficult", "hard", "doubt", "worry", "fear"]
        
        positive_score = sum(1 for word in positive_words if word in text_lower)
        negative_score = sum(1 for word in negative_words if word in text_lower)
        
        if positive_score > negative_score:
            sentiment = "positive"
        elif negative_score > positive_score:
            sentiment = "negative"
        else:
            sentiment = "neutral"
        
        # Simple tag assignment
        tags = []
        if any(word in text_lower for word in ["question", "why", "how", "what", "?"]):
            tags.append("Question")
        if any(word in text_lower for word in ["doubt", "confused", "unsure"]):
            tags.append("Doubt")
        if sentiment == "positive":
            tags.append("Positive Feedback")
        elif sentiment == "negative":
            tags.append("Negative Feedback")
        
        if not tags:
            tags = ["Christian Learning"]
        
        return {
            "sentiment": sentiment,
            "tags": tags,
            "confidence": 0.6  # Medium confidence for fallback analysis
        }
    
    def should_trigger_human_handoff(self, user_message: str) -> bool:
        """Determine if a message should trigger human handoff"""
        if not self.client:
            # Simple keyword-based detection in simulation mode
            handoff_keywords = ['doubt', 'confused', 'angry', 'help me', 'talk to someone', 'need support']
            message_lower = user_message.lower()
            return any(keyword in message_lower for keyword in handoff_keywords)
        
        try:
            prompt = f"""
            Analyze this user message from someone on a faith journey learning about Jesus. 
            Determine if they need human support (true/false).
            
            Trigger human handoff if the user:
            - Expresses doubts or confusion that need personal guidance
            - Shows anger or distress
            - Explicitly asks to speak with someone
            - Indicates they're struggling emotionally
            - Has theological questions beyond basic content
            
            User message: {user_message}
            
            Respond only with: true or false
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            return response.text.strip().lower() == 'true'
            
        except Exception as e:
            logger.error(f"Error determining human handoff: {e}")
            # Default to false to avoid unnecessary handoffs
            return False

    def generate_contextual_response(self, message: str, system_prompt: str, style: str = 'compassionate'):
        """Generate contextual response with custom system prompt and style"""
        try:
            if not self.client:
                return None
            
            style_modifiers = {
                'compassionate': 'Respond with deep empathy, warmth, and understanding.',
                'educational': 'Focus on teaching and providing informative, educational content.',
                'encouraging': 'Provide uplifting, motivational, and supportive responses.',
                'balanced': 'Balance compassion, education, and encouragement in your response.'
            }
            
            full_prompt = f"""{system_prompt}

Style guidance: {style_modifiers.get(style, style_modifiers['compassionate'])}

User message: "{message}"

Please respond according to your role and the style guidance above."""

            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            
            return response.text if response.text else None
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return None
