# WhatsApp Business API Setup Guide

## Your Webhook URLs
Use these URLs in your Meta Business Manager webhook configuration:

**Bot 1 (English):** `https://smart-budget-cvglobaldev.replit.app/whatsapp/1`
**Bot 2 (Indonesian):** `https://smart-budget-cvglobaldev.replit.app/whatsapp/2`
**Bot 5 (Hindi):** `https://smart-budget-cvglobaldev.replit.app/whatsapp/5`
**Default (Bot 1):** `https://smart-budget-cvglobaldev.replit.app/whatsapp`

## Meta Business Manager Configuration Steps

### 1. Access WhatsApp Business API Settings
1. Go to [Meta Business Manager](https://business.facebook.com)
2. Select your app
3. Navigate to WhatsApp > Configuration

### 2. Configure Webhook
1. Click "Edit" next to Webhook
2. Enter your webhook URL (use the URL for the specific bot you want to configure)
3. Enter your verify token (stored in your bot's database configuration)

### 3. Subscribe to Webhook Events
Make sure these events are subscribed:
- ✅ messages
- ✅ message_deliveries
- ✅ message_reads
- ✅ messaging_postbacks (for interactive buttons)

### 4. Phone Number Permissions
Ensure your phone number ID has these permissions:
- ✅ whatsapp_business_messaging
- ✅ whatsapp_business_management

## Verify Token
Each bot has its own verify token stored in the database. You can find them in the bot management interface.

## Testing
1. Send a test message to your WhatsApp Business number
2. Check the logs in your Replit console
3. Verify the webhook receives the message and processes it correctly

## Troubleshooting
- **400 Error with phone number ID**: Check permissions in Meta Business Manager
- **Webhook not receiving messages**: Verify the webhook URL is correctly configured
- **Message delivery failures**: Ensure your access token has the correct scopes

## Current Status
✅ WhatsApp API credentials configured
✅ Webhook endpoints ready
✅ Multi-bot routing functional
✅ Interactive buttons implemented
✅ Contextual AI responses working

Your system is ready to receive and process WhatsApp messages once the webhook is configured in Meta Business Manager!