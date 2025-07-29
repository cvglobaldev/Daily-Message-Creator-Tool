#!/usr/bin/env python3
"""
Script to re-analyze all previous chat messages with the new tagging rules
"""

import sys
sys.path.append('/home/runner/workspace')

from services import GeminiService
import psycopg2
import os
import json
import logging

# Configure logging 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(os.environ.get("DATABASE_URL"))

def preview_changes():
    """Preview what changes would be made"""
    gemini_service = GeminiService()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get recent incoming messages
        cursor.execute("""
            SELECT id, raw_text, llm_tags, llm_sentiment 
            FROM message_logs 
            WHERE direction = 'incoming' 
            AND raw_text IS NOT NULL 
            AND raw_text != ''
            AND raw_text != '/start'
            ORDER BY timestamp DESC 
            LIMIT 10
        """)
        
        messages = cursor.fetchall()
        print(f"\n=== PREVIEW: Re-tagging {len(messages)} recent messages ===\n")
        
        for message in messages:
            message_id, raw_text, current_tags, current_sentiment = message
            
            try:
                # Analyze with new rules
                analysis = gemini_service.analyze_response(raw_text)
                new_tags = analysis.get('tags', ['Christian Learning'])
                new_sentiment = analysis.get('sentiment', 'neutral')
                
                print(f"Message ID {message_id}: '{raw_text[:60]}...'")
                print(f"  OLD: {current_sentiment} | {current_tags}")
                print(f"  NEW: {new_sentiment} | {new_tags}")
                print(f"  Confidence: {analysis.get('confidence', 0.5):.2f}")
                print("-" * 80)
                
            except Exception as e:
                print(f"Error analyzing message ID {message_id}: {e}")
                
    finally:
        cursor.close()
        conn.close()

def retag_all_messages():
    """Re-analyze and update all messages"""
    gemini_service = GeminiService()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all incoming messages that aren't start commands
        cursor.execute("""
            SELECT id, raw_text, llm_tags, llm_sentiment 
            FROM message_logs 
            WHERE direction = 'incoming' 
            AND raw_text IS NOT NULL 
            AND raw_text != ''
            AND raw_text != '/start'
            ORDER BY timestamp DESC
        """)
        
        messages = cursor.fetchall()
        logger.info(f"Found {len(messages)} incoming messages to re-analyze")
        
        updated_count = 0
        for message in messages:
            message_id, raw_text, old_tags, old_sentiment = message
            
            try:
                logger.info(f"Re-analyzing message ID {message_id}: '{raw_text[:50]}...'")
                
                # Re-analyze with new tagging rules
                analysis = gemini_service.analyze_response(raw_text)
                
                # Update the message
                cursor.execute("""
                    UPDATE message_logs 
                    SET llm_sentiment = %s, llm_tags = %s, llm_confidence = %s
                    WHERE id = %s
                """, (
                    analysis.get('sentiment', 'neutral'),
                    json.dumps(analysis.get('tags', ['Christian Learning'])),
                    analysis.get('confidence', 0.5),
                    message_id
                ))
                
                logger.info(f"Updated - Tags: {analysis.get('tags')} | Sentiment: {analysis.get('sentiment')}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error re-analyzing message ID {message_id}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        logger.info(f"Successfully updated {updated_count} messages with new tagging rules")
        
    except Exception as e:
        logger.error(f"Error during re-tagging: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--preview":
        preview_changes()
    elif len(sys.argv) > 1 and sys.argv[1] == "--update":
        retag_all_messages()
    else:
        print("Usage:")
        print("  python retag_script.py --preview   # Preview changes")
        print("  python retag_script.py --update    # Apply new tagging")