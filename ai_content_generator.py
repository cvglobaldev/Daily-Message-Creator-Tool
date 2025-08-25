#!/usr/bin/env python3
"""AI Content Generation Service for Faith Journey Chatbot"""

import os
import json
import logging
from typing import List, Dict, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class DailyContent(BaseModel):
    day_number: int
    title: str
    content: str
    reflection_question: str
    tags: List[str] = []

class ContentGenerationRequest(BaseModel):
    target_audience: str
    audience_language: str
    audience_religion: str
    audience_age_group: str
    content_prompt: str
    journey_duration: int

class AIContentGenerator:
    def __init__(self):
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
    def generate_journey_content(self, request: ContentGenerationRequest) -> List[DailyContent]:
        """Generate complete journey content based on user specifications"""
        
        try:
            print(f"🔥 GENERATOR: Creating {request.journey_duration} days of AI content for audience: {request.target_audience}")
            logger.info(f"Generating {request.journey_duration} days of AI content for audience: {request.target_audience}")
            
            # Get audience-specific content configuration for AI prompting
            content_config = self._get_audience_content_config(request)
            
            # Generate AI content in smaller batches to avoid timeouts
            daily_contents = self._generate_ai_content_in_batches(request, content_config)
            
            print(f"🔥 GENERATOR: Successfully created {len(daily_contents)} days of AI-generated content for {request.target_audience}")
            logger.info(f"Successfully created {len(daily_contents)} days of AI-generated content")
            
            return daily_contents
            
        except Exception as e:
            logger.error(f"Error generating AI content: {e}")
            raise Exception(f"Content generation failed: {e}")
    
    def _get_audience_content_config(self, request: ContentGenerationRequest) -> Dict:
        """Get content configuration based on target audience"""
        audience = request.target_audience.lower()
        religion = request.audience_religion.lower()
        language = request.audience_language.lower()
        
        # Customize approach based on audience background
        if "atheist" in audience or "non-religious" in audience or "secular" in audience:
            return {
                "approach": "philosophical",
                "tone": "analytical and questioning",
                "themes": ["philosophy", "ethics", "meaning", "purpose", "human connection"],
                "avoid": ["religious terminology", "prayer", "scripture"],
                "focus": "humanistic values and personal growth"
            }
        elif "muslim" in religion or "islam" in religion:
            return {
                "approach": "respectful bridge-building",
                "tone": "gentle and culturally sensitive",
                "themes": ["shared values", "love", "compassion", "community", "spiritual growth"],
                "avoid": ["direct theological challenges"],
                "focus": "common ground and universal truths"
            }
        elif "hindu" in religion or "buddhist" in religion:
            return {
                "approach": "interfaith dialogue",
                "tone": "meditative and reflective",
                "themes": ["inner peace", "mindfulness", "compassion", "spiritual journey"],
                "avoid": ["conflicting doctrines"],
                "focus": "spiritual practices and personal transformation"
            }
        else:
            return {
                "approach": "universal spiritual",
                "tone": "inclusive and welcoming",
                "themes": ["spiritual growth", "love", "hope", "community"],
                "avoid": ["exclusivity"],
                "focus": "universal spiritual principles"
            }
    
    def _generate_day_content(self, day: int, request: ContentGenerationRequest, config: Dict) -> tuple:
        """Generate customized content for a specific day"""
        language = request.audience_language.lower()
        approach = config["approach"]
        themes = config["themes"]
        
        # Day-specific progression
        if day <= 3:
            stage = "introduction"
        elif day <= 10:
            stage = "exploration"
        elif day <= 20:
            stage = "deepening"
        else:
            stage = "integration"
        
        # Customize content based on audience and stage
        if "atheist" in request.target_audience.lower():
            if language == "indonesian":
                title = f"Hari {day}: Refleksi Filosofis"
                content = f"Hari ke-{day} - Mari kita jelajahi pertanyaan mendalam tentang makna dan tujuan hidup. Tanpa mengandalkan keyakinan supranatural, kita dapat menemukan nilai-nilai yang mendalam dalam hubungan manusia, etika, dan pencarian akan kebenaran. Hari ini, mari kita renungkan bagaimana kita dapat hidup dengan integritas dan kasih sayang terhadap sesama."
                question = f"Nilai-nilai apa yang paling penting bagi Anda dalam menjalani hidup yang bermakna?"
            else:
                title = f"Day {day}: Philosophical Reflection"
                content = f"Day {day} - Let's explore profound questions about meaning and purpose in life. Without relying on supernatural beliefs, we can discover deep values in human relationships, ethics, and the search for truth. Today, let's reflect on how we can live with integrity and compassion toward others."
                question = f"What values are most important to you in living a meaningful life?"
            tags = ["philosophy", "ethics", "humanism", "meaning"]
        else:
            # Default spiritual content for other audiences
            if language == "indonesian":
                title = f"Hari {day}: Perjalanan Spiritual"
                content = f"Hari ke-{day} dalam perjalanan spiritual Anda. Mari kita jelajahi tema-tema kasih, harapan, dan pertumbuhan pribadi yang dapat memperkaya hidup kita."
                question = f"Bagaimana Anda dapat menerapkan pembelajaran hari ini dalam kehidupan sehari-hari?"
            else:
                title = f"Day {day}: Spiritual Journey"
                content = f"Day {day} of your spiritual journey. Let's explore themes of love, hope, and personal growth that can enrich our lives."
                question = f"How can you apply today's learning in your daily life?"
            tags = ["spiritual", "growth", "journey"]
        
        return title, content, question, tags
    
    def _generate_ai_content_in_batches(self, request: ContentGenerationRequest, config: Dict) -> List[DailyContent]:
        """Generate AI content in smaller batches to avoid timeouts"""
        # Use smaller batches for faster generation and to prevent timeouts
        batch_size = 2 if request.journey_duration > 5 else 3  # Generate 2 days at a time for longer journeys
        all_daily_contents = []
        
        total_days = request.journey_duration
        
        for start_day in range(1, total_days + 1, batch_size):
            end_day = min(start_day + batch_size - 1, total_days)
            batch_days = end_day - start_day + 1
            
            print(f"🔥 BATCH: Generating days {start_day}-{end_day} ({batch_days} days)")
            
            try:
                # Create a batch request
                batch_request = ContentGenerationRequest(
                    target_audience=request.target_audience,
                    audience_language=request.audience_language,
                    audience_religion=request.audience_religion,
                    audience_age_group=request.audience_age_group,
                    content_prompt=request.content_prompt,
                    journey_duration=batch_days
                )
                
                # Generate this batch using AI
                batch_contents = self._generate_ai_content_with_gemini(batch_request, config, start_day)
                
                # Adjust day numbers for the batch
                for content in batch_contents:
                    content.day_number = start_day + content.day_number - 1
                
                all_daily_contents.extend(batch_contents)
                print(f"🔥 BATCH: Successfully generated days {start_day}-{end_day}")
                
            except Exception as e:
                print(f"🔥 BATCH ERROR: Failed to generate days {start_day}-{end_day}: {e}")
                # Generate fallback content for this batch
                for day in range(start_day, end_day + 1):
                    title, content, question, tags = self._generate_day_content(day, request, config)
                    fallback_content = DailyContent(
                        day_number=day,
                        title=title,
                        content=content,
                        reflection_question=question,
                        tags=tags
                    )
                    all_daily_contents.append(fallback_content)
                print(f"🔥 BATCH: Used fallback for days {start_day}-{end_day}")
        
        return all_daily_contents
    
    def _generate_ai_content_with_gemini(self, request: ContentGenerationRequest, config: Dict, start_day: int = 1) -> List[DailyContent]:
        """Generate content using Gemini AI with audience-specific customization"""
        try:
            # Build customized AI prompt based on audience
            prompt = self._build_audience_specific_prompt(request, config, start_day)
            
            print(f"🔥 GEMINI: Generating content with gemini-2.5-flash for {request.target_audience}")
            
            # Generate content using Gemini 2.5 Flash
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if not response.text:
                raise Exception("Gemini returned empty response")
            
            # Parse the JSON response
            content_data = json.loads(response.text)
            daily_contents = []
            
            for item in content_data.get("daily_content", []):
                daily_content = DailyContent(
                    day_number=item["day_number"],
                    title=item["title"],
                    content=item["content"],
                    reflection_question=item["reflection_question"],
                    tags=item.get("tags", ["growth", "reflection"])
                )
                daily_contents.append(daily_content)
            
            print(f"🔥 GEMINI: Successfully parsed {len(daily_contents)} days of AI content")
            return daily_contents
            
        except Exception as e:
            print(f"🔥 GEMINI ERROR: {e}")
            logger.warning(f"Gemini AI generation failed: {e}. Falling back to customized mock content.")
            
            # Fallback to customized mock content if AI fails
            return self._generate_fallback_content(request, config)
    
    def _generate_fallback_content(self, request: ContentGenerationRequest, config: Dict) -> List[DailyContent]:
        """Generate fallback content if AI fails, using audience customization"""
        daily_contents = []
        
        for day in range(1, request.journey_duration + 1):
            title, content, question, tags = self._generate_day_content(day, request, config)
            
            daily_content = DailyContent(
                day_number=day,
                title=title,
                content=content,
                reflection_question=question,
                tags=tags
            )
            daily_contents.append(daily_content)
        
        return daily_contents
    
    def _build_audience_specific_prompt(self, request: ContentGenerationRequest, config: Dict, start_day: int = 1) -> str:
        """Build AI prompt customized for specific audience"""
        
        approach = config["approach"]
        tone = config["tone"]
        themes = ", ".join(config["themes"])
        avoid = ", ".join(config["avoid"])
        focus = config["focus"]
        
        days_text = f"{request.journey_duration} days" if request.journey_duration > 1 else "1 day"
        if start_day > 1:
            journey_context = f"This is part of a longer journey. You are creating days {start_day} to {start_day + request.journey_duration - 1}."
        else:
            journey_context = f"This is the beginning of the journey."
            
        prompt = f"""You are an expert content creator specializing in culturally sensitive personal growth journeys.

Create {days_text} of personal development content with the following specifications:

**Context:** {journey_context}

**Target Audience:**
- Demographics: {request.target_audience}
- Age Group: {request.audience_age_group}
- Current Background: {request.audience_religion}
- Language: {request.audience_language}

**Content Approach:**
- Approach: {approach}
- Tone: {tone}
- Key Themes: {themes}
- Areas to Avoid: {avoid}
- Primary Focus: {focus}

**Custom Requirements:**
{request.content_prompt}

**Output Format:**
Generate content as a JSON object with this exact structure:

{{
  "daily_content": [
    {{
      "day_number": 1,
      "title": "Clear, engaging title for the day",
      "content": "Main content (200-400 words). Be respectful, encouraging, and culturally appropriate. Focus on {focus}. Use {tone} tone.",
      "reflection_question": "Thoughtful question that encourages personal reflection and growth",
      "tags": ["relevant", "themes", "from", "list"]
    }},
    // ... continue for all {request.journey_duration} days
  ]
}}

**Critical Guidelines:**
1. **Cultural Sensitivity**: Deeply respect the audience's background and beliefs
2. **Progressive Journey**: Build concepts gradually, each day building on previous ones
3. **Practical Application**: Include actionable insights and real-world applications
4. **Encouraging Tone**: Maintain supportive, non-judgmental approach throughout
5. **Personal Growth**: Focus on universal human values like compassion, integrity, purpose
6. **Respectful Language**: Use inclusive, accessible language appropriate for the demographic
7. **Varied Content**: Mix philosophical insights, practical exercises, and personal reflection
8. **Safe Space**: Create content that feels welcoming and non-threatening

Ensure the content progression makes logical sense and builds a coherent journey of personal growth."""

        return prompt
    
    def _build_generation_prompt(self, request: ContentGenerationRequest) -> str:
        """Build the AI generation prompt based on user requirements"""
        
        prompt = f"""You are an expert spiritual content creator specializing in culturally sensitive faith journeys. 

Create a {request.journey_duration}-day spiritual journey with the following specifications:

**Target Audience:**
- Demographics: {request.target_audience}
- Age Group: {request.audience_age_group}
- Current Religious Background: {request.audience_religion}
- Language: {request.audience_language}

**Content Requirements:**
{request.content_prompt}

**Output Format:**
Generate content as a JSON object with the following structure:

{{
  "daily_content": [
    {{
      "day_number": 1,
      "title": "Clear, engaging title for the day",
      "content": "Main spiritual content (200-400 words). Be respectful, encouraging, and culturally sensitive. Include practical insights and gentle guidance.",
      "reflection_question": "Thoughtful question that encourages personal spiritual reflection and growth",
      "tags": ["relevant", "spiritual", "tags"]
    }},
    // ... continue for all {request.journey_duration} days
  ]
}}

**Important Guidelines:**
1. **Cultural Sensitivity**: Be deeply respectful of the audience's current religious background
2. **Progressive Journey**: Structure content to gradually introduce concepts, building on previous days
3. **Personal Engagement**: Include relatable examples and practical applications
4. **Encouraging Tone**: Maintain a supportive, non-judgmental, and loving approach
5. **Reflection Focus**: Each day should encourage personal spiritual growth and introspection
6. **Language**: Use clear, accessible language appropriate for the target demographic
7. **Diversity**: Vary content types - some days focus on concepts, others on practices or personal stories
8. **Safe Space**: Create content that feels like a safe space for spiritual exploration

**Content Themes to Include:**
- Love and compassion
- Spiritual growth and personal transformation  
- Community and relationships
- Hope and purpose
- Prayer and meditation practices
- Forgiveness and healing
- Service to others
- Finding meaning in life's challenges

Generate exactly {request.journey_duration} days of content, numbered 1 through {request.journey_duration}.
"""
        
        return prompt
    
    def validate_generated_content(self, contents: List[DailyContent], expected_days: int) -> bool:
        """Validate that generated content meets requirements"""
        
        if len(contents) != expected_days:
            logger.warning(f"Expected {expected_days} days, got {len(contents)} days")
            return False
        
        # Check for duplicate day numbers
        day_numbers = [c.day_number for c in contents]
        if len(set(day_numbers)) != len(day_numbers):
            logger.warning("Duplicate day numbers found")
            return False
        
        # Check for minimum content length
        for content in contents:
            if len(content.content) < 100:
                logger.warning(f"Day {content.day_number} content too short")
                return False
            
            if len(content.reflection_question) < 20:
                logger.warning(f"Day {content.day_number} reflection question too short")
                return False
        
        return True

# Example usage
def test_content_generation():
    """Test function for content generation"""
    generator = AIContentGenerator()
    
    request = ContentGenerationRequest(
        target_audience="Young Muslim adults seeking spiritual guidance",
        audience_language="English",
        audience_religion="Islam", 
        audience_age_group="18-25",
        content_prompt="Create a gentle, respectful faith journey that introduces Christian concepts to someone from a Muslim background. Focus on love, compassion, and spiritual growth.",
        journey_duration=10
    )
    
    try:
        contents = generator.generate_journey_content(request)
        print(f"Generated {len(contents)} days of content")
        
        for content in contents[:2]:  # Show first 2 days
            print(f"\nDay {content.day_number}: {content.title}")
            print(f"Content: {content.content[:100]}...")
            print(f"Reflection: {content.reflection_question}")
            print(f"Tags: {content.tags}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_content_generation()