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
            print(f"🔥 GENERATOR: Creating {request.journey_duration} days of content for audience: {request.target_audience}")
            logger.info(f"Generating {request.journey_duration} days of content for audience: {request.target_audience}")
            
            # Skip AI for now - just create working mock content to test bot isolation
            daily_contents = []
            
            # Create content based on target audience and language
            content_theme = "spiritual growth" if "spiritual" in request.content_prompt.lower() else "motivation"
            language = request.audience_language.lower()
            
            for day in range(1, request.journey_duration + 1):
                if language == "indonesian":
                    title = f"Hari {day}: Perjalanan {content_theme.title()}"
                    content = f"Ini adalah konten {content_theme} untuk hari {day}. Terus bertumbuh dan tetap semangat dalam perjalanan Anda!"
                    question = f"Apa yang bisa Anda pelajari dari pesan hari ke-{day} ini?"
                else:
                    title = f"Day {day}: {content_theme.title()} Journey"
                    content = f"This is {content_theme} content for day {day}. Stay positive and keep growing on your journey!"
                    question = f"What can you learn from today's message on day {day}?"
                
                daily_content = DailyContent(
                    day_number=day,
                    title=title,
                    content=content,
                    reflection_question=question,
                    tags=[content_theme, "growth", "daily"]
                )
                daily_contents.append(daily_content)
            
            print(f"🔥 GENERATOR: Successfully created {len(daily_contents)} days of content")
            logger.info(f"Successfully created {len(daily_contents)} days of content")
            
            logger.info(f"Successfully generated {len(daily_contents)} days of content")
            return daily_contents
            
        except Exception as e:
            logger.error(f"Error generating AI content: {e}")
            raise Exception(f"Content generation failed: {e}")
    
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