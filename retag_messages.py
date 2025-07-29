#!/usr/bin/env python3
"""
Script to re-analyze all previous chat messages with the new tagging rules
"""

import os
import sys
import logging
from db_manager import DatabaseManager
from services import GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def retag_all_messages():
    """Re-analyze all incoming messages with new tagging rules"""
    
    # Initialize services
    db_manager = DatabaseManager()
    gemini_service = GeminiService()
    
    try:
        # Get all incoming messages from database
        query = """
        SELECT id, raw_text, llm_tags, llm_sentiment 
        FROM message_logs 
        WHERE direction = 'incoming' 
        AND raw_text IS NOT NULL 
        AND raw_text != ''
        ORDER BY timestamp DESC
        """
        
        messages = db_manager.execute_query(query)
        logger.info(f"Found {len(messages)} incoming messages to re-analyze")
        
        updated_count = 0
        for message in messages:
            try:
                message_id = message[0]
                raw_text = message[1]
                old_tags = message[2]
                old_sentiment = message[3]
                
                logger.info(f"Re-analyzing message ID {message_id}: '{raw_text[:50]}...'")
                
                # Re-analyze the message with new tagging rules
                analysis = gemini_service.analyze_response(raw_text)
                
                # Update the message with new analysis
                update_query = """
                UPDATE message_logs 
                SET llm_sentiment = %s, llm_tags = %s, llm_confidence = %s
                WHERE id = %s
                """
                
                db_manager.execute_update(
                    update_query,
                    (
                        analysis.get('sentiment', 'neutral'),
                        analysis.get('tags', ['Christian Learning']),
                        analysis.get('confidence', 0.5),
                        message_id
                    )
                )
                
                logger.info(f"Updated tags: {analysis.get('tags')} | Sentiment: {analysis.get('sentiment')}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error re-analyzing message ID {message_id}: {e}")
                continue
        
        logger.info(f"Successfully updated {updated_count} messages with new tagging rules")
        
    except Exception as e:
        logger.error(f"Error during re-tagging process: {e}")
        raise

def preview_changes():
    """Preview what changes would be made without updating database"""
    
    # Initialize services
    db_manager = DatabaseManager()
    gemini_service = GeminiService()
    
    try:
        # Get recent messages for preview
        query = """
        SELECT id, raw_text, llm_tags, llm_sentiment 
        FROM message_logs 
        WHERE direction = 'incoming' 
        AND raw_text IS NOT NULL 
        AND raw_text != ''
        ORDER BY timestamp DESC 
        LIMIT 10
        """
        
        messages = db_manager.execute_query(query)
        print(f"\n=== PREVIEW: Re-tagging {len(messages)} recent messages ===\n")
        
        for message in messages:
            try:
                message_id = message[0]
                raw_text = message[1]
                current_tags = message[2] if message[2] else []
                current_sentiment = message[3] or 'unknown'
                
                # Analyze with new rules
                analysis = gemini_service.analyze_response(raw_text)
                new_tags = analysis.get('tags', ['Christian Learning'])
                new_sentiment = analysis.get('sentiment', 'neutral')
                
                print(f"Message: '{raw_text[:60]}...'")
                print(f"  OLD: {current_sentiment} | {current_tags}")
                print(f"  NEW: {new_sentiment} | {new_tags}")
                print(f"  Confidence: {analysis.get('confidence', 0.5):.2f}")
                print("-" * 80)
                
            except Exception as e:
                print(f"Error analyzing message ID {message_id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error during preview: {e}")
        raise

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        preview_changes()
    elif len(sys.argv) > 1 and sys.argv[1] == "--update":
        retag_all_messages()
    else:
        print("Usage:")
        print("  python retag_messages.py --preview   # Preview changes")
        print("  python retag_messages.py --update    # Apply new tagging")