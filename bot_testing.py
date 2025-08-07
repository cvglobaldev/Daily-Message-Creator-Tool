#!/usr/bin/env python3
"""
Bot Testing and Validation System
Ensures new Telegram bots work correctly before deployment
"""

import requests
import json
import time
import os
import sys
sys.path.append('.')

from main import app
from models import Bot, db

def test_bot_token(bot_token):
    """Test if a Telegram bot token is valid"""
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getMe")
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_info = data['result']
                return True, {
                    'id': bot_info['id'],
                    'username': bot_info['username'],
                    'first_name': bot_info['first_name']
                }
        return False, "Invalid token or API error"
    except Exception as e:
        return False, str(e)

def test_bot_webhook_routing(bot_id, test_chat_id="960173404"):
    """Test if webhook routing works for a specific bot"""
    webhook_url = f"https://smart-budget-cvglobaldev.replit.app/telegram/{bot_id}"
    
    test_payload = {
        "update_id": int(time.time()),
        "message": {
            "message_id": int(time.time()),
            "from": {
                "id": int(test_chat_id),
                "is_bot": False,
                "first_name": "Test",
                "username": "testuser"
            },
            "chat": {
                "id": int(test_chat_id),
                "first_name": "Test",
                "username": "testuser",
                "type": "private"
            },
            "date": int(time.time()),
            "text": "HELP"
        }
    }
    
    try:
        response = requests.post(webhook_url, 
                               headers={'Content-Type': 'application/json'}, 
                               data=json.dumps(test_payload))
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def test_message_sending(bot_token, test_chat_id="960173404"):
    """Test if bot can send messages"""
    try:
        test_message = f"🧪 Bot Test - {time.strftime('%Y-%m-%d %H:%M:%S')}\n\nThis is an automated test to verify bot functionality."
        
        response = requests.post(f"https://api.telegram.org/bot{bot_token}/sendMessage",
                               headers={'Content-Type': 'application/json'},
                               data=json.dumps({
                                   'chat_id': test_chat_id,
                                   'text': test_message
                               }))
        
        if response.status_code == 200:
            data = response.json()
            return data['ok'], data.get('result', {}).get('message_id')
        return False, response.text
    except Exception as e:
        return False, str(e)

def comprehensive_bot_test(bot_id, test_chat_id="960173404"):
    """Run comprehensive tests on a bot"""
    print(f"\n🧪 COMPREHENSIVE BOT TEST - Bot ID: {bot_id}")
    print("=" * 50)
    
    results = {
        'bot_id': bot_id,
        'tests_passed': 0,
        'tests_total': 4,
        'details': []
    }
    
    with app.app_context():
        # Test 1: Database Configuration
        print("Test 1: Database Configuration...")
        bot = Bot.query.get(bot_id)
        if bot and bot.telegram_bot_token:
            print(f"✅ Bot found: {bot.name}")
            print(f"✅ Token configured: {bot.telegram_bot_token[:20]}...")
            results['tests_passed'] += 1
            results['details'].append(f"✅ Database: Bot '{bot.name}' configured properly")
        else:
            print("❌ Bot not found or token missing")
            results['details'].append("❌ Database: Bot not found or token missing")
            return results
        
        # Test 2: Token Validation
        print("\nTest 2: Token Validation...")
        token_valid, token_info = test_bot_token(bot.telegram_bot_token)
        if token_valid:
            print(f"✅ Token valid: @{token_info['username']}")
            results['tests_passed'] += 1
            results['details'].append(f"✅ Token: Valid (@{token_info['username']})")
        else:
            print(f"❌ Token invalid: {token_info}")
            results['details'].append(f"❌ Token: {token_info}")
            return results
        
        # Test 3: Webhook Routing
        print("\nTest 3: Webhook Routing...")
        routing_works, routing_response = test_bot_webhook_routing(bot_id, test_chat_id)
        if routing_works:
            print("✅ Webhook routing successful")
            results['tests_passed'] += 1
            results['details'].append("✅ Webhook: Routing works correctly")
        else:
            print(f"❌ Webhook routing failed: {routing_response}")
            results['details'].append(f"❌ Webhook: {routing_response}")
        
        # Test 4: Message Sending
        print("\nTest 4: Message Sending...")
        message_sent, message_id = test_message_sending(bot.telegram_bot_token, test_chat_id)
        if message_sent:
            print(f"✅ Message sent successfully (ID: {message_id})")
            results['tests_passed'] += 1
            results['details'].append(f"✅ Messaging: Test message sent (ID: {message_id})")
        else:
            print(f"❌ Message sending failed: {message_id}")
            results['details'].append(f"❌ Messaging: {message_id}")
    
    # Test Summary
    print(f"\n📊 TEST RESULTS: {results['tests_passed']}/{results['tests_total']} passed")
    if results['tests_passed'] == results['tests_total']:
        print("🎉 ALL TESTS PASSED - Bot is ready for production!")
    else:
        print("⚠️  Some tests failed - Bot needs attention before deployment")
    
    return results

def test_all_bots():
    """Test all bots in the system"""
    print("\n🔍 TESTING ALL BOTS IN SYSTEM")
    print("=" * 50)
    
    with app.app_context():
        bots = Bot.query.filter(Bot.telegram_bot_token.isnot(None)).all()
        
        if not bots:
            print("❌ No bots with Telegram tokens found")
            return
        
        for bot in bots:
            comprehensive_bot_test(bot.id)
            print()

if __name__ == "__main__":
    # Test specific bot or all bots
    import sys
    
    if len(sys.argv) > 1:
        bot_id = int(sys.argv[1])
        comprehensive_bot_test(bot_id)
    else:
        test_all_bots()