#!/usr/bin/env python3
"""
Content Gap Analyzer - Identifies and resolves content gaps across all bots
"""

import os
import sys
from datetime import datetime
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Get database connection using DATABASE_URL"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    # Parse the database URL
    url = urlparse(database_url)
    
    return psycopg2.connect(
        host=url.hostname,
        port=url.port,
        user=url.username,
        password=url.password,
        database=url.path[1:]  # Remove leading slash
    )

def analyze_content_gaps():
    """Analyze content gaps across all bots"""
    print("🔍 Analyzing Content Gaps Across All Bots...")
    print("=" * 60)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get comprehensive gap analysis
    cur.execute("""
        SELECT 
            b.id,
            b.name,
            b.journey_length,
            COUNT(c.id) as content_count,
            COALESCE(MIN(c.day_number), -1) as min_content_day,
            COALESCE(MAX(c.day_number), -1) as max_content_day,
            COUNT(u.id) as total_users,
            COUNT(CASE WHEN u.status = 'active' THEN 1 END) as active_users,
            COALESCE(MAX(u.current_day), 0) as max_user_day,
            COALESCE(AVG(u.current_day), 0) as avg_user_day
        FROM bots b 
        LEFT JOIN content c ON b.id = c.bot_id 
        LEFT JOIN users u ON b.id = u.bot_id 
        GROUP BY b.id, b.name, b.journey_length
        ORDER BY b.id
    """)
    
    gaps = []
    results = cur.fetchall()
    
    for row in results:
        bot_id, name, journey_length, content_count, min_day, max_day, total_users, active_users, max_user_day, avg_user_day = row
        
        # Calculate gaps
        expected_content = journey_length if journey_length else 30
        content_gap = expected_content - content_count
        user_content_gap = max(0, max_user_day - max_day) if max_day >= 0 else max_user_day
        
        gap_info = {
            'bot_id': bot_id,
            'name': name,
            'journey_length': journey_length or 30,
            'content_count': content_count,
            'content_range': f"{min_day}-{max_day}" if min_day >= 0 else "No content",
            'total_users': total_users,
            'active_users': active_users,
            'max_user_day': max_user_day,
            'avg_user_day': round(avg_user_day, 1),
            'content_gap': content_gap,
            'user_content_gap': user_content_gap,
            'priority': 'CRITICAL' if user_content_gap > 0 else 'HIGH' if content_gap > 15 else 'MEDIUM'
        }
        
        gaps.append(gap_info)
        
        # Print analysis
        print(f"📊 Bot {bot_id}: {name}")
        print(f"   Journey Length: {journey_length or 30} days")
        print(f"   Content Available: {content_count} pieces (Days {gap_info['content_range']})")
        print(f"   Users: {total_users} total, {active_users} active")
        print(f"   User Progress: Avg Day {gap_info['avg_user_day']}, Max Day {max_user_day}")
        print(f"   Content Gap: {content_gap} days missing")
        print(f"   User-Content Gap: {user_content_gap} days (users ahead of content)")
        print(f"   Priority: {gap_info['priority']}")
        print()
    
    cur.close()
    conn.close()
    
    return gaps

def generate_content_recommendations(gaps):
    """Generate specific content generation recommendations"""
    print("💡 Content Generation Recommendations:")
    print("=" * 60)
    
    critical_bots = [g for g in gaps if g['priority'] == 'CRITICAL']
    high_bots = [g for g in gaps if g['priority'] == 'HIGH']
    
    if critical_bots:
        print("🔥 CRITICAL PRIORITY (Users beyond available content):")
        for gap in critical_bots:
            missing_days = gap['user_content_gap']
            print(f"   Bot {gap['bot_id']} ({gap['name']}): Generate {missing_days} days immediately")
    
    if high_bots:
        print("⚠️ HIGH PRIORITY (Significant content gaps):")
        for gap in high_bots:
            missing_days = gap['content_gap']
            print(f"   Bot {gap['bot_id']} ({gap['name']}): Generate {missing_days} days for complete journey")
    
    return critical_bots, high_bots

def suggest_immediate_fixes(critical_bots):
    """Suggest immediate fixes for critical gaps"""
    if not critical_bots:
        print("✅ No critical content gaps found!")
        return
    
    print("\n🚨 IMMEDIATE ACTION REQUIRED:")
    print("=" * 60)
    
    for gap in critical_bots:
        print(f"Bot {gap['bot_id']} ({gap['name']}):")
        print(f"  1. Generate Days {gap['content_count']+1}-{gap['max_user_day']} immediately")
        print(f"  2. Consider pausing user progression temporarily")
        print(f"  3. Use AI content generator with cultural context")
        print()

if __name__ == "__main__":
    gaps = analyze_content_gaps()
    critical, high = generate_content_recommendations(gaps)
    suggest_immediate_fixes(critical)