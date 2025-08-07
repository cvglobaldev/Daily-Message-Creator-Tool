# New Telegram Bot Creation & Testing Checklist

## Pre-Creation Steps
- [ ] Decide on bot purpose and content strategy
- [ ] Choose appropriate bot name and username
- [ ] Create bot via @BotFather on Telegram
- [ ] Save the bot token securely

## Bot Setup in System
- [ ] Create new bot entry in admin panel (/create_bot)
- [ ] Enter bot name, description, and Telegram token
- [ ] Configure greeting message and help content
- [ ] Set journey duration (10-90 days)
- [ ] Add Day 1-N content via CMS
- [ ] Assign content tags and categories

## Automated Testing (Run: `python bot_testing.py [bot_id]`)
- [ ] Database Configuration Test
- [ ] Token Validation Test
- [ ] Webhook Routing Test  
- [ ] Message Sending Test

## Manual Testing
- [ ] Send `/start` command - verify welcome message and Day 1 content delivery
- [ ] Send `/help` command - verify help message response
- [ ] Send `/stop` command - verify unsubscribe confirmation
- [ ] Send reflection response - verify AI processing and tagging
- [ ] Send `/human` command - verify human handoff trigger

## Production Verification
- [ ] Test with real user account
- [ ] Verify content scheduling works (check after 10 minutes)
- [ ] Confirm user progression through journey days
- [ ] Test AI sentiment analysis on user responses
- [ ] Verify admin chat management interface shows conversations

## Quality Assurance Checklist
✅ **System Requirements Met:**
- Flask app context properly managed for database operations
- Bot-specific service creation with correct token routing
- Direct content delivery system bypasses threading issues
- Comprehensive error handling and debug logging
- Multi-bot isolation ensures no cross-contamination

✅ **Common Issues Resolved:**
- Webhook processing failures due to missing app context
- Bot service creation errors in multi-bot environments
- Content delivery delays or failures
- Message routing to wrong bot services
- Database connection issues in threaded operations

## Emergency Troubleshooting
If a new bot doesn't work:
1. Run `python bot_testing.py [bot_id]` to identify specific failure
2. Check webhook logs in console for processing errors
3. Verify bot token via @BotFather
4. Test manual API call: `curl https://api.telegram.org/bot[TOKEN]/getMe`
5. Check database for proper bot configuration
6. Verify Flask app context is available during service creation

## Success Indicators
- ✅ All automated tests pass (4/4)
- ✅ START command triggers welcome + Day 1 content
- ✅ HELP command shows bot-specific help message
- ✅ User progresses from Day 1 to Day 2 after content delivery
- ✅ Message logs show both incoming commands and outgoing responses
- ✅ Admin interface displays user conversations correctly