#!/usr/bin/env python3
"""
Immediate Fixes for Content Gap Crisis
- Generate missing content for active bots
- Implement scheduler safety checks
- Create content gap monitoring
"""

import os
import psycopg2
from urllib.parse import urlparse
from datetime import datetime

def get_db_connection():
    """Get database connection using DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    url = urlparse(database_url)
    return psycopg2.connect(
        host=url.hostname, port=url.port, user=url.username,
        password=url.password, database=url.path[1:]
    )

def analyze_critical_gaps():
    """Identify bots with users beyond available content"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Find critical gaps where users are ahead of content
    cur.execute("""
        WITH bot_content AS (
            SELECT bot_id, MAX(day_number) as max_content_day, COUNT(*) as content_count
            FROM content 
            GROUP BY bot_id
        ),
        bot_users AS (
            SELECT bot_id, MAX(current_day) as max_user_day, COUNT(*) as active_users
            FROM users 
            WHERE status = 'active' 
            GROUP BY bot_id
        )
        SELECT 
            b.id, b.name, 
            COALESCE(bc.max_content_day, -1) as max_content_day,
            COALESCE(bc.content_count, 0) as content_count,
            COALESCE(bu.max_user_day, 0) as max_user_day,
            COALESCE(bu.active_users, 0) as active_users,
            GREATEST(0, COALESCE(bu.max_user_day, 0) - COALESCE(bc.max_content_day, -1)) as gap_days
        FROM bots b
        LEFT JOIN bot_content bc ON b.id = bc.bot_id
        LEFT JOIN bot_users bu ON b.id = bu.bot_id
        WHERE COALESCE(bu.active_users, 0) > 0
        ORDER BY gap_days DESC, bu.active_users DESC
    """)
    
    critical_bots = []
    results = cur.fetchall()
    
    print("🔍 CRITICAL CONTENT GAP ANALYSIS")
    print("=" * 60)
    
    for row in results:
        bot_id, name, max_content, content_count, max_user, active_users, gap_days = row
        
        is_critical = gap_days > 0
        is_empty = content_count == 0 and active_users > 0
        
        status = "🔥 CRITICAL" if is_critical or is_empty else "✅ OK"
        
        print(f"{status} Bot {bot_id}: {name}")
        print(f"   Content: Days 0-{max_content} ({content_count} pieces)")
        print(f"   Users: {active_users} active, max at Day {max_user}")
        if is_critical or is_empty:
            print(f"   🚨 GAP: {gap_days} days missing content")
            critical_bots.append({
                'bot_id': bot_id, 'name': name, 'gap_days': gap_days,
                'max_content': max_content, 'max_user': max_user,
                'active_users': active_users, 'is_empty': is_empty
            })
        print()
    
    cur.close()
    conn.close()
    return critical_bots

def generate_emergency_content_templates():
    """Generate content templates for critical bots"""
    
    templates = {
        'Islam - Indonesian': {
            'cultural_context': 'Indonesian Islamic background, respectful approach to Isa al-Masih',
            'language': 'Indonesian',
            'tone': 'Warm, respectful, Bang Kris personality'
        },
        'Islam - Hausa': {
            'cultural_context': 'Hausa Islamic background, culturally sensitive approach',  
            'language': 'English with Hausa cultural context',
            'tone': 'Respectful, culturally aware'
        },
        'Buddhism - Burmese': {
            'cultural_context': 'Burmese Buddhist background, gentle introduction',
            'language': 'English with Burmese context',
            'tone': 'Gentle, philosophical, respectful'
        },
        'Hinduism - Nepalese': {
            'cultural_context': 'Nepalese Hindu background, respectful spiritual exploration',
            'language': 'English with Nepalese context', 
            'tone': 'Respectful, spiritual, culturally sensitive'
        },
        'Atheist - English': {
            'cultural_context': 'Atheist/secular background, evidence-based approach',
            'language': 'English',
            'tone': 'Intellectual, evidence-based, respectful'
        }
    }
    
    return templates

def create_scheduler_safety_patch():
    """Generate scheduler patch to handle missing content gracefully"""
    
    patch_code = '''
# SCHEDULER SAFETY PATCH - Add to scheduler.py

def check_content_availability(bot_id, day_number):
    """Check if content exists before trying to send"""
    from db_manager import get_content_for_day
    content = get_content_for_day(day_number, bot_id)
    return content is not None

def send_content_safely(bot_id, day_number, users):
    """Send content with safety checks"""
    if not check_content_availability(bot_id, day_number):
        logging.warning(f"Missing content for Bot {bot_id}, Day {day_number} - pausing {len(users)} users")
        
        # Send apology message instead
        bot = get_bot_by_id(bot_id)
        apology_msg = f"Selamat! Kamu sudah mencapai akhir konten yang tersedia. Tim kami sedang menyiapkan materi selanjutnya. Terima kasih atas kesabaranmu! 🙏"
        
        for user in users:
            try:
                send_message_to_user(user, apology_msg, bot)
            except Exception as e:
                logging.error(f"Failed to send apology to user {user.id}: {e}")
        
        return False
    
    # Normal content sending logic continues here
    return True
'''
    
    print("📄 SCHEDULER SAFETY PATCH")
    print("=" * 60)
    print("Add this code to scheduler.py to handle missing content:")
    print(patch_code)
    return patch_code

if __name__ == "__main__":
    print("🚨 IMMEDIATE CONTENT GAP CRISIS RESPONSE")
    print("=" * 80)
    
    # Step 1: Analyze critical gaps
    critical_bots = analyze_critical_gaps()
    
    if not critical_bots:
        print("✅ No critical content gaps found!")
        exit(0)
    
    # Step 2: Generate templates for missing content
    print("\n💡 EMERGENCY CONTENT TEMPLATES")
    print("=" * 60)
    templates = generate_emergency_content_templates()
    
    for bot in critical_bots:
        bot_name = bot['name']
        if bot_name in templates:
            template = templates[bot_name]
            days_needed = bot['gap_days'] if not bot['is_empty'] else 30
            
            print(f"\nBot {bot['bot_id']}: {bot_name}")
            print(f"Days needed: {days_needed}")
            print(f"Context: {template['cultural_context']}")
            print(f"Language: {template['language']}")
            print(f"Tone: {template['tone']}")
    
    # Step 3: Create scheduler safety patch
    print("\n🛡️ SCHEDULER SAFETY MEASURES")
    create_scheduler_safety_patch()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Use AI content generator to create missing days")
    print("2. Apply scheduler safety patch")
    print("3. Monitor for remaining gaps")
    print("4. Set up automated gap detection")