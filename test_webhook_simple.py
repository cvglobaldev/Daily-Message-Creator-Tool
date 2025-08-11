#!/usr/bin/env python3
"""Simple webhook test to verify the exact endpoint is working"""

from flask import Flask, request

# Create a minimal test app
test_app = Flask(__name__)

@test_app.route('/whatsapp/<int:bot_id>', methods=['GET', 'POST'])
def test_whatsapp_webhook(bot_id=1):
    """Test WhatsApp webhook verification"""
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"=== WEBHOOK TEST BOT {bot_id} ===")
        print(f"Mode: {mode}")
        print(f"Token: {token}")
        print(f"Challenge: {challenge}")
        
        if mode == 'subscribe' and token == 'CVGlobal_WhatsApp_Verify_2024':
            return challenge, 200, {'Content-Type': 'text/plain'}
        else:
            return 'Verification failed', 403
    
    return 'POST received', 200

@test_app.route('/test')
def test_route():
    return 'Test route working!'

if __name__ == '__main__':
    test_app.run(host='0.0.0.0', port=5001, debug=True)