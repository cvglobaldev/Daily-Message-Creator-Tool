"""
Recovery utilities for fixing user progression issues across all bots
"""
import logging
from datetime import datetime, timedelta
from models import db, User, Bot
from db_manager import DatabaseManager

logger = logging.getLogger(__name__)

def fix_stuck_users():
    """Find and fix users who are stuck in progression due to STOP/START issues"""
    try:
        db_manager = DatabaseManager()
        
        # Find users who should have progressed more based on their join time
        stuck_users = []
        
        # Query users who have been active for more than 1 hour but are still on early days
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        # Get all active users
        users = User.query.filter_by(status='active').all()
        
        for user in users:
            if user.join_date and user.join_date < one_hour_ago:
                # Calculate expected day based on bot's delivery interval
                bot = Bot.query.get(user.bot_id)
                if bot and bot.delivery_interval_minutes:
                    minutes_elapsed = (datetime.now() - user.join_date).total_seconds() / 60
                    expected_day = int(minutes_elapsed / bot.delivery_interval_minutes) + 1
                    
                    # If user is significantly behind expected progression
                    if user.current_day < expected_day - 2:  # Allow 2-day buffer
                        stuck_users.append({
                            'user': user,
                            'expected_day': min(expected_day, bot.journey_duration_days),
                            'current_day': user.current_day,
                            'minutes_elapsed': minutes_elapsed,
                            'bot_interval': bot.delivery_interval_minutes
                        })
        
        logger.info(f"Found {len(stuck_users)} users who appear to be stuck in progression")
        
        # Fix each stuck user
        fixed_count = 0
        for stuck_info in stuck_users:
            user = stuck_info['user']
            target_day = stuck_info['expected_day']
            
            try:
                # Update user to appropriate day
                db_manager.update_user(
                    user.phone_number, 
                    current_day=target_day,
                    join_date=user.join_date  # Keep original join date
                )
                
                logger.info(f"Fixed user {user.phone_number}: {stuck_info['current_day']} → {target_day}")
                fixed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to fix user {user.phone_number}: {e}")
        
        logger.info(f"Successfully fixed {fixed_count} stuck users")
        return fixed_count
        
    except Exception as e:
        logger.error(f"Error in fix_stuck_users: {e}")
        return 0

def test_stop_start_cycle(phone_number: str, bot_id: int = 2):
    """Test the STOP/START cycle to ensure it works properly"""
    try:
        from main import handle_stop_command, handle_start_command
        
        logger.info(f"Testing STOP/START cycle for {phone_number} with bot {bot_id}")
        
        # Test STOP command
        handle_stop_command(phone_number, platform="whatsapp", bot_id=bot_id)
        
        # Wait a moment
        import time
        time.sleep(1)
        
        # Test START command
        handle_start_command(phone_number, platform="whatsapp", bot_id=bot_id)
        
        # Check if user is properly reset
        db_manager = DatabaseManager()
        user = db_manager.get_user_by_phone(phone_number)
        
        if user and user.status == 'active' and user.current_day == 1:
            logger.info(f"STOP/START cycle test PASSED for {phone_number}")
            return True
        else:
            logger.error(f"STOP/START cycle test FAILED for {phone_number}: status={user.status if user else 'None'}, day={user.current_day if user else 'None'}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing STOP/START cycle for {phone_number}: {e}")
        return False