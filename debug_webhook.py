#!/usr/bin/env python3
"""Debug script to test webhook endpoints directly"""

import os
import sys
sys.path.append('/home/runner/workspace')

from main import app
from models import Bot

def test_webhook_direct():
    """Test webhook endpoint directly"""
    with app.app_context():
        # Check if Bot 2 exists
        bot = Bot.query.get(2)
        if not bot:
            print("❌ Bot 2 not found in database")
            return
        
        print(f"✅ Bot 2 found: {bot.name}")
        print(f"   Verify Token: {bot.whatsapp_verify_token}")
        print(f"   Phone Number ID: {bot.whatsapp_phone_number_id}")
        print(f"   Access Token: {bot.whatsapp_access_token[:20]}..." if bot.whatsapp_access_token else "None")
        
        # Test Flask app routes
        print("\n📊 Flask Routes:")
        for rule in app.url_map.iter_rules():
            if 'whatsapp' in rule.rule:
                print(f"   {rule.rule} -> {rule.endpoint} {list(rule.methods)}")

if __name__ == "__main__":
    test_webhook_direct()