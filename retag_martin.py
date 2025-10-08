from app import app, db
from models import MessageLog
from services import gemini_service
import sys

with app.app_context():
    # Get Martin's user ID
    user_id = 126
    
    # Get all incoming messages from Martin
    messages = MessageLog.query.filter_by(
        user_id=user_id, 
        direction='incoming'
    ).order_by(MessageLog.timestamp).all()
    
    print(f"Found {len(messages)} incoming messages from Martin")
    
    retagged_count = 0
    error_count = 0
    
    for msg in messages:
        try:
            print(f"Analyzing message {msg.id}: {msg.raw_text[:50]}...")
            
            # Analyze message with current tag rules from database
            analysis = gemini_service.analyze_response(msg.raw_text)
            
            # Update tags
            if 'tags' in analysis and analysis['tags']:
                msg.llm_tags = analysis['tags']
                msg.llm_sentiment = analysis.get('sentiment', 'neutral')
                msg.llm_confidence = analysis.get('confidence', 0.0)
                print(f"  -> Tags: {analysis['tags']}, Sentiment: {analysis.get('sentiment')}")
                retagged_count += 1
            else:
                print(f"  -> No tags found")
                
        except Exception as e:
            print(f"  -> Error: {e}")
            error_count += 1
            continue
    
    db.session.commit()
    print(f"\nCompleted! Retagged {retagged_count} messages. {error_count} errors.")
