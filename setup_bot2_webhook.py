#!/usr/bin/env python3
"""
Script to set up Bot 2 webhook properly
"""

import requests
import json

def setup_bot2_webhook():
    """Set up webhook for Bot 2"""
    bot_token = "8342973377:AAF3pdo5YH6AkBosijP0G7Rct542_4GlEu4"
    webhook_url = "https://smart-budget-cvglobaldev.replit.app/telegram/2"
    
    # Set the webhook
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        response = requests.post(telegram_api_url, json=payload)
        result = response.json()
        
        if result.get("ok"):
            print("✅ Bot 2 webhook set successfully!")
            print(f"Webhook URL: {webhook_url}")
        else:
            print("❌ Failed to set webhook:")
            print(json.dumps(result, indent=2))
        
        # Check webhook info
        info_response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo")
        info_result = info_response.json()
        
        if info_result.get("ok"):
            webhook_info = info_result.get("result", {})
            print("\n📋 Current webhook info:")
            print(f"URL: {webhook_info.get('url', 'Not set')}")
            print(f"Has custom certificate: {webhook_info.get('has_custom_certificate', False)}")
            print(f"Pending updates: {webhook_info.get('pending_update_count', 0)}")
            if webhook_info.get('last_error_date'):
                print(f"Last error: {webhook_info.get('last_error_message', 'Unknown')}")
        
    except Exception as e:
        print(f"❌ Error setting up webhook: {e}")

if __name__ == "__main__":
    setup_bot2_webhook()