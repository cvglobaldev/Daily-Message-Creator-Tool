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
    
    def __init__(self, bot_token=None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.api_base_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        # For development, we'll simulate message sending
        self.simulate_mode = not self.bot_token
        
        if self.simulate_mode:
            logger.warning("Telegram service running in simulation mode (no bot token)")
        else:
            logger.info("Telegram service initialized with bot token")
    
    def send_message(self, chat_id: str, message: str, reply_markup=None, parse_mode="HTML") -> bool:
        """Send a text message via Telegram with optional inline keyboards"""
        try:
            if self.simulate_mode:
                # Simulate message sending for development
                print(f"\n📱 TELEGRAM MESSAGE TO {chat_id}:")
                print(f"   {message}")
                if reply_markup:
                    print(f"   📱 Inline Keyboard: {reply_markup}")
                print("   ✅ Message simulated (development mode)")
                return True
            
            url = f"{self.api_base_url}/sendMessage"
            payload = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            if reply_markup:
                payload["reply_markup"] = reply_markup
            
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
    
    def send_message_with_inline_keyboard(self, chat_id: str, message: str, buttons: List[List[Dict[str, str]]]) -> bool:
        """Send message with inline keyboard buttons"""
        try:
            reply_markup = {
                "inline_keyboard": buttons
            }
            return self.send_message(chat_id, message, reply_markup)
        except Exception as e:
            logger.error(f"Error sending message with inline keyboard: {e}")
            return False
    
    def send_quick_reply_message(self, chat_id: str, message: str, quick_replies: List[str]) -> bool:
        """Send message with quick reply buttons for common faith journey responses"""
        try:
            # Convert quick replies to inline keyboard format
            buttons = []
            for i in range(0, len(quick_replies), 2):  # 2 buttons per row
                row = []
                for j in range(2):
                    if i + j < len(quick_replies):
                        row.append({
                            "text": quick_replies[i + j],
                            "callback_data": f"quick_reply:{quick_replies[i + j][:20]}"  # Limit callback data
                        })
                buttons.append(row)
            
            return self.send_message_with_inline_keyboard(chat_id, message, buttons)
        except Exception as e:
            logger.error(f"Error sending quick reply message: {e}")
            return False
    
    def send_copy_text_message(self, chat_id: str, message: str, copy_text: str, copy_label: str = "Copy Verse") -> bool:
        """Send message with copy text button for Bible verses or inspirational content"""
        try:
            buttons = [[{
                "text": f"📋 {copy_label}",
                "copy_text": {"text": copy_text}
            }]]
            
            return self.send_message_with_inline_keyboard(chat_id, message, buttons)
        except Exception as e:
            logger.error(f"Error sending copy text message: {e}")
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
    
    def answer_callback_query(self, callback_query_id: str, text: str = "", show_alert: bool = False) -> bool:
        """Answer callback query from inline keyboards"""
        try:
            if self.simulate_mode:
                print(f"📱 CALLBACK QUERY ANSWER (simulated): {text}")
                return True
            
            url = f"{self.api_base_url}/answerCallbackQuery"
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": show_alert
            }
            
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    def send_photo(self, chat_id: str, photo_url: str, caption: str = "") -> bool:
        """Send photo message via Telegram Bot API"""
        try:
            if self.simulate_mode:
                print(f"\n📱 TELEGRAM PHOTO MESSAGE TO {chat_id}:")
                print(f"   Photo URL: {photo_url}")
                if caption:
                    print(f"   Caption: {caption}")
                print("   ✅ Photo message simulated (development mode)")
                return True
            
            # For uploaded image files, send the file directly using multipart/form-data
            import os
            
            # Extract filename from URL
            if "/static/uploads/images/" in photo_url:
                filename = photo_url.split("/static/uploads/images/")[-1]
                file_path = os.path.join("static", "uploads", "images", filename)
                
                if os.path.exists(file_path):
                    # Send image file directly
                    url = f"{self.api_base_url}/sendPhoto"
                    
                    with open(file_path, 'rb') as photo_file:
                        files = {'photo': photo_file}
                        data = {'chat_id': chat_id}
                        if caption:
                            data['caption'] = caption
                        
                        response = requests.post(url, files=files, data=data, timeout=60)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Telegram photo sent successfully to {chat_id}")
                            return True
                        else:
                            logger.error(f"Failed to send Telegram photo: {result.get('description', 'Unknown error')}")
                            return False
                    else:
                        logger.error(f"Failed to send Telegram photo: {response.text}")
                        return False
                else:
                    logger.error(f"Photo file not found: {file_path}")
                    return False
            else:
                # Fallback to URL-based sending for external URLs
                url = f"{self.api_base_url}/sendPhoto"
                payload = {
                    "chat_id": chat_id,
                    "photo": photo_url
                }
                
                if caption:
                    payload["caption"] = caption
                
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Telegram photo sent successfully to {chat_id}")
                        return True
                    else:
                        logger.error(f"Failed to send Telegram photo: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    logger.error(f"Failed to send Telegram photo: {response.text}")
                    return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram photo: {e}")
            return False
    
    def send_video(self, chat_id: str, video_url: str, caption: str = "") -> bool:
        """Send video message via Telegram Bot API - for YouTube, send as formatted text message"""
        try:
            if self.simulate_mode:
                print(f"\n📱 TELEGRAM VIDEO MESSAGE TO {chat_id}:")
                print(f"   Video URL: {video_url}")
                if caption:
                    print(f"   Caption: {caption}")
                print("   ✅ Video message simulated (development mode)")
                return True
            
            # Check if it's a YouTube URL - send as formatted text message instead
            if "youtube.com" in video_url or "youtu.be" in video_url:
                # Create a formatted message with the YouTube link (avoid Markdown issues)
                video_message = f"🎥 Watch Video:\n{video_url}"
                if caption:
                    video_message = f"{caption}\n\n{video_message}"
                
                # Send as a regular text message without parse_mode to avoid entity parsing errors
                url = f"{self.api_base_url}/sendMessage"
                payload = {
                    "chat_id": chat_id,
                    "text": video_message,
                    "disable_web_page_preview": False  # Enable preview for YouTube links
                }
                
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Telegram YouTube video link sent successfully to {chat_id}")
                        return True
                    else:
                        logger.error(f"Telegram YouTube video send failed: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    logger.error(f"Failed to send Telegram YouTube video: {response.text}")
                    return False
            else:
                # For uploaded video files, send the file directly using multipart/form-data
                import os
                
                # Extract filename from URL
                if "/static/uploads/videos/" in video_url:
                    filename = video_url.split("/static/uploads/videos/")[-1]
                    file_path = os.path.join("static", "uploads", "videos", filename)
                    
                    if os.path.exists(file_path):
                        # Send video file directly
                        url = f"{self.api_base_url}/sendVideo"
                        
                        with open(file_path, 'rb') as video_file:
                            files = {'video': video_file}
                            data = {'chat_id': chat_id}
                            if caption:
                                data['caption'] = caption
                            
                            response = requests.post(url, files=files, data=data, timeout=120)
                        
                        if response.status_code == 200:
                            result = response.json()
                            if result.get("ok"):
                                logger.info(f"Telegram video sent successfully to {chat_id}")
                                return True
                            else:
                                logger.error(f"Failed to send Telegram video: {result.get('description', 'Unknown error')}")
                                return False
                        else:
                            logger.error(f"Failed to send Telegram video: {response.text}")
                            return False
                    else:
                        logger.error(f"Video file not found: {file_path}")
                        return False
                else:
                    # Fallback to URL-based sending for external URLs
                    url = f"{self.api_base_url}/sendVideo"
                    payload = {
                        "chat_id": chat_id,
                        "video": video_url
                    }
                    
                    if caption:
                        payload["caption"] = caption
                    
                    response = requests.post(url, json=payload, timeout=60)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Telegram video sent successfully to {chat_id}")
                            return True
                        else:
                            logger.error(f"Failed to send Telegram video: {result.get('description', 'Unknown error')}")
                            return False
                    else:
                        logger.error(f"Failed to send Telegram video: {response.text}")
                        return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram video: {e}")
            return False
    
    def send_audio(self, chat_id: str, audio_url: str, caption: str = "") -> bool:
        """Send audio message via Telegram Bot API"""
        try:
            if self.simulate_mode:
                print(f"\n📱 TELEGRAM AUDIO MESSAGE TO {chat_id}:")
                print(f"   Audio URL: {audio_url}")
                if caption:
                    print(f"   Caption: {caption}")
                print("   ✅ Audio message simulated (development mode)")
                return True
            
            # For uploaded audio files, send the file directly using multipart/form-data
            import os
            
            # Extract filename from URL
            if "/static/uploads/audio/" in audio_url:
                filename = audio_url.split("/static/uploads/audio/")[-1]
                file_path = os.path.join("static", "uploads", "audio", filename)
                
                if os.path.exists(file_path):
                    # Send audio file directly
                    url = f"{self.api_base_url}/sendAudio"
                    
                    with open(file_path, 'rb') as audio_file:
                        files = {'audio': audio_file}
                        data = {'chat_id': chat_id}
                        if caption:
                            data['caption'] = caption
                        
                        response = requests.post(url, files=files, data=data, timeout=120)
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("ok"):
                            logger.info(f"Telegram audio sent successfully to {chat_id}")
                            return True
                        else:
                            logger.error(f"Failed to send Telegram audio: {result.get('description', 'Unknown error')}")
                            return False
                    else:
                        logger.error(f"Failed to send Telegram audio: {response.text}")
                        return False
                else:
                    logger.error(f"Audio file not found: {file_path}")
                    return False
            else:
                # Fallback to URL-based sending for external URLs
                url = f"{self.api_base_url}/sendAudio"
                payload = {
                    "chat_id": chat_id,
                    "audio": audio_url
                }
                
                if caption:
                    payload["caption"] = caption
                
                response = requests.post(url, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        logger.info(f"Telegram audio sent successfully to {chat_id}")
                        return True
                    else:
                        logger.error(f"Failed to send Telegram audio: {result.get('description', 'Unknown error')}")
                        return False
                else:
                    logger.error(f"Failed to send Telegram audio: {response.text}")
                    return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram audio: {e}")
            return False
    
    def set_emoji_status(self, chat_id: str, emoji: str, duration: int = 3600) -> bool:
        """Set emoji status for enhanced user engagement (2025 feature)"""
        try:
            if self.simulate_mode:
                print(f"📱 EMOJI STATUS SET (simulated): {emoji} for {duration}s")
                return True
            
            url = f"{self.api_base_url}/setUserEmojiStatus"
            payload = {
                "user_id": chat_id,
                "emoji_status": {
                    "custom_emoji_id": emoji,
                    "expiration_date": duration
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error setting emoji status: {e}")
            return False

class WhatsAppService:
    """Service for WhatsApp Business API integration"""
    
    def __init__(self, access_token=None, phone_number_id=None):
        self.access_token = access_token or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        # For development, we'll simulate message sending
        self.simulate_mode = not (self.access_token and self.phone_number_id)
        
        if self.simulate_mode:
            logger.warning("WhatsApp service running in simulation mode (no API credentials)")
        else:
            logger.info("WhatsApp service initialized with API credentials")
    
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
    
    def send_video(self, to: str, video_url: str, caption: str = "") -> bool:
        """Send video message via WhatsApp Business API"""
        try:
            if self.simulate_mode:
                print(f"\n📱 WHATSAPP VIDEO MESSAGE TO {to}:")
                print(f"   Video URL: {video_url}")
                if caption:
                    print(f"   Caption: {caption}")
                print("   ✅ Video message simulated (development mode)")
                return True
                
            if not self.access_token or not self.phone_number_id:
                logger.error("WhatsApp credentials not configured")
                return False
                
            url = f"https://graph.facebook.com/v17.0/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "messaging_product": "whatsapp",
                "to": to.replace('+', ''),
                "type": "video",
                "video": {
                    "link": video_url
                }
            }
            
            if caption:
                payload["video"]["caption"] = caption
            
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code == 200:
                logger.info(f"WhatsApp video sent successfully to {to}")
                return True
            else:
                logger.error(f"Failed to send WhatsApp video to {to}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending WhatsApp video to {to}: {e}")
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
        
        # Predefined tags for classification (updated per tagging rules)
        self.predefined_tags = [
            "Introduction to Jesus (ITJ)",
            "Gospel Presentation", 
            "Prayer",
            "Bible Exposure",
            "Bible Engagement",
            "Christian Learning",
            "Salvation Prayer",
            "Holy Spirit Empowerment",
            "Human",
            "Blocked",
            "Already in church",
            "Not connected",
            "Not genuine",
            "No response"
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
        
        # Simple tag assignment based on new tagging rules
        tags = []
        if any(word in text_lower for word in ["jesus", "isa", "christ", "read", "watched", "message"]):
            tags.append("Introduction to Jesus (ITJ)")
        elif any(word in text_lower for word in ["pray", "prayer", "praying", "prayed"]):
            tags.append("Prayer")
        elif any(word in text_lower for word in ["bible", "scripture", "story", "teaching"]):
            tags.append("Bible Exposure")
        elif any(word in text_lower for word in ["learning", "understand", "follow", "video", "link"]):
            tags.append("Christian Learning")
        elif any(word in text_lower for word in ["human", "help", "person", "talk"]):
            tags.append("Human")
        
        if not tags:
            tags = ["Christian Learning"]
        
        return {
            "sentiment": sentiment,
            "tags": tags,
            "confidence": 0.6  # Medium confidence for fallback analysis
        }
    
    def generate_contextual_response(self, user_reflection: str, day_number: int, content_title: str, content_text: str, reflection_question: str) -> str:
        """Generate a contextual response to user's reflection based on current day's content"""
        try:
            if not self.client:
                # Fallback response if Gemini is not available
                return self._get_fallback_contextual_response(user_reflection)
            
            from prompts import CONTEXTUAL_RESPONSE_PROMPT
            
            # Create the prompt with context
            prompt = CONTEXTUAL_RESPONSE_PROMPT.format(
                day_number=day_number,
                content_title=content_title,
                content_text=content_text,
                reflection_question=reflection_question,
                user_reflection=user_reflection
            )
            
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            if response.text:
                # Clean up the response (remove any extra formatting)
                contextual_response = response.text.strip()
                logger.info(f"Generated contextual response for reflection (length: {len(contextual_response)})")
                return contextual_response
            else:
                return self._get_fallback_contextual_response(user_reflection)
                
        except Exception as e:
            logger.error(f"Error generating contextual response: {e}")
            return self._get_fallback_contextual_response(user_reflection)
    
    def _get_fallback_contextual_response(self, user_reflection: str) -> str:
        """Provide fallback contextual responses when Gemini is unavailable"""
        responses = [
            "Thank you for sharing your thoughtful reflection. Your openness to explore these questions shows a sincere heart seeking truth.",
            "I appreciate you taking time to reflect on this. Your insights show that you're truly engaging with these important concepts.",
            "Your reflection shows deep thinking. These are exactly the kind of questions that lead to meaningful spiritual growth.",
            "Thank you for your honest response. Your willingness to explore these ideas is encouraging to see.",
            "I'm grateful you shared your thoughts. Your reflection shows you're genuinely considering what this means for your own life."
        ]
        
        import random
        return random.choice(responses)
    
    def generate_bot_response(self, user_message: str, ai_prompt: str, content_context=None) -> str:
        """Generate a bot-specific response using the bot's AI prompt and optional content context"""
        try:
            if not self.client:
                # Fallback response if Gemini is not available
                return self._get_fallback_contextual_response(user_message)
            
            # Build the context-aware prompt
            system_instruction = ai_prompt
            
            # Add content context if available
            if content_context:
                context_addition = f"""
                
Current journey context:
- Day: {content_context.day_number}
- Topic: {content_context.title}
- Content: {content_context.content[:200]}...
- Reflection Question: {content_context.reflection_question}

Please respond in a way that acknowledges their current journey stage and the content they're reflecting on.
"""
                system_instruction += context_addition
            
            # Generate response using the bot's specific AI prompt
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(role="user", parts=[types.Part(text=user_message)])
                ],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.7,
                    max_output_tokens=500
                )
            )
            
            if response.text:
                # Clean up the response
                bot_response = response.text.strip()
                logger.info(f"Generated bot-specific response (length: {len(bot_response)})")
                return bot_response
            else:
                return self._get_fallback_contextual_response(user_message)
                
        except Exception as e:
            logger.error(f"Error generating bot response: {e}")
            return self._get_fallback_contextual_response(user_message)
    
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


