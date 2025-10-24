# WAHA (WhatsApp HTTP API) Setup Guide

## Overview

WAHA (WhatsApp HTTP API) is a simpler, self-hosted alternative to the Meta Business WhatsApp API. It runs WhatsApp Web via Docker and provides clean REST endpoints without the complexity of Meta Business Manager.

## Why Choose WAHA?

### Advantages over Meta Business API:
- ✅ **Simpler Setup**: Just Docker + QR code scan (no Meta Business Manager)
- ✅ **No Third-Party Dependency**: Self-hosted, full control
- ✅ **Free Core Version**: No conversation-based pricing
- ✅ **Easier Debugging**: Built-in dashboard and simple API
- ✅ **No Approval Process**: No business verification required
- ✅ **Multiple Engines**: WEBJS (browser), NOWEB (Node.js), GOWS (Go)

### When to Use WAHA:
- Development and testing environments
- Small to medium-scale deployments
- Projects requiring full control over infrastructure
- Cost-sensitive applications (no per-conversation fees)
- Rapid prototyping and MVP development

### When to Use Meta Business API:
- Large enterprise deployments (1000+ concurrent users)
- Official business verification required
- Need for official Meta support and SLA
- Template messages and business features

---

## Part 1: WAHA Server Setup

### Option A: Local Setup (Docker)

1. **Install Docker**
   - macOS/Windows: [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Linux: `sudo apt install docker.io`

2. **Run WAHA Container**
   ```bash
   docker run -d \
     -p 3000:3000 \
     -e WAHA_API_KEY=your-secret-api-key-here \
     -e WAHA_DASHBOARD_USERNAME=admin \
     -e WAHA_DASHBOARD_PASSWORD=your-password \
     -v $(pwd)/sessions:/app/.sessions \
     --name waha \
     --restart unless-stopped \
     devlikeapro/waha
   ```

3. **For ARM devices (Apple M1/M2, Raspberry Pi)**
   ```bash
   docker pull devlikeapro/waha:arm
   docker tag devlikeapro/waha:arm devlikeapro/waha
   # Then run the command above
   ```

4. **Verify WAHA is Running**
   - Open http://localhost:3000
   - You should see the WAHA dashboard

### Option B: Cloud Deployment

Deploy WAHA on a cloud provider for production use:

**Recommended Providers:**
- [DigitalOcean](https://www.digitalocean.com/) - Droplet with Docker
- [Hetzner](https://www.hetzner.com/) - Affordable VPS
- [AWS](https://aws.amazon.com/) - EC2 instance
- [Google Cloud](https://cloud.google.com/) - Compute Engine

**Minimum Requirements:**
- 1GB RAM (2GB recommended for multiple sessions)
- 10GB storage
- Ubuntu 20.04+ or Debian 11+

**Docker Compose Setup (docker-compose.yml):**
```yaml
version: '3.8'
services:
  waha:
    image: devlikeapro/waha
    ports:
      - "3000:3000"
    environment:
      - WAHA_API_KEY=${WAHA_API_KEY}
      - WAHA_DASHBOARD_USERNAME=${WAHA_DASHBOARD_USERNAME}
      - WAHA_DASHBOARD_PASSWORD=${WAHA_DASHBOARD_PASSWORD}
      - WHATSAPP_DEFAULT_ENGINE=WEBJS  # or NOWEB, GOWS
    volumes:
      - ./sessions:/app/.sessions
    restart: unless-stopped
```

Run with: `docker-compose up -d`

---

## Part 2: WAHA Session Setup

### Step 1: Access WAHA Dashboard

1. Open your WAHA server URL (e.g., http://localhost:3000/dashboard)
2. Login with your dashboard credentials:
   - Username: `admin` (or your custom username)
   - Password: (your WAHA_DASHBOARD_PASSWORD)

### Step 2: Start a New Session

1. Click **"Start Session"** or navigate to Sessions tab
2. Enter session name (e.g., `default` or `bot1`)
3. Click **"Start"**
4. Wait for QR code to appear

### Step 3: Scan QR Code

1. Open WhatsApp on your mobile device
2. Go to **Settings** → **Linked Devices**
3. Tap **"Link a Device"**
4. Scan the QR code displayed in WAHA dashboard
5. Wait for session status to change to **"WORKING"**

### Step 4: Verify Session

Test your session with a simple API call:
```bash
curl -X POST http://localhost:3000/api/sendText \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-secret-api-key-here" \
  -d '{
    "session": "default",
    "chatId": "6281234567890@c.us",
    "text": "Hello from WAHA!"
  }'
```

---

## Part 3: Configure Bot to Use WAHA

### Step 1: Edit Bot Configuration

1. Navigate to **Bot Management** in your admin dashboard
2. Select the bot you want to configure for WAHA
3. Click **"Edit Bot"**

### Step 2: Configure WhatsApp Connection

1. Scroll to **WhatsApp Configuration** section
2. Select **Connection Type**: **WAHA (WhatsApp HTTP API)**
3. Fill in WAHA settings:
   - **WAHA Base URL**: Your WAHA server URL (e.g., `http://localhost:3000` or `https://waha.yourserver.com`)
   - **WAHA API Key**: Your WAHA_API_KEY (set during WAHA installation)
   - **WAHA Session Name**: Your session name (e.g., `default`)

### Step 3: Configure Webhook

1. In WAHA Dashboard, go to your session settings
2. Set **Webhook URL** to:
   ```
   https://your-replit-app.replit.app/waha/<bot_id>
   ```
   Replace `<bot_id>` with your bot's ID (e.g., `/waha/1` for bot ID 1)

3. Subscribe to webhook events:
   - ✅ `message`
   - ✅ `message.any`

4. Alternatively, set webhook via API:
   ```bash
   curl -X POST http://localhost:3000/api/sessions/default/config \
     -H "Content-Type: application/json" \
     -H "X-Api-Key: your-api-key" \
     -d '{
       "webhookUrl": "https://your-replit-app.replit.app/waha/1",
       "webhookEvents": ["message", "message.any"]
     }'
   ```

### Step 4: Test the Integration

1. Send a message to your WhatsApp number from another phone
2. Check your application logs to verify webhook received
3. The bot should respond automatically

---

## Part 4: Phone Number Format

WAHA uses a different phone number format than Meta Business API:

**WAHA Format:**
- Input: `6281234567890@c.us`
- The application automatically converts between formats

**Examples:**
- `+62 812 3456 7890` → `6281234567890@c.us` (WAHA)
- User sees: `+62 812 3456 7890` (normalized)

---

## Part 5: Advanced Configuration

### Environment Variables

You can also configure WAHA settings via environment variables:

```bash
# Add to your .env file or Replit Secrets
WAHA_BASE_URL=http://localhost:3000
WAHA_API_KEY=your-secret-key
WAHA_SESSION=default
```

These will be used as defaults if bot-specific settings are not configured.

### Multiple Sessions

You can run multiple WhatsApp sessions for different bots:

1. Start multiple sessions in WAHA dashboard:
   - `bot1` for Bot 1
   - `bot2` for Bot 2
   - `bot3` for Bot 3

2. Configure each bot with its own session name

### Security Best Practices

1. **Use Strong API Keys**
   ```bash
   # Generate a secure random key
   openssl rand -hex 32
   ```

2. **Enable HTTPS** (for production)
   - Use reverse proxy (nginx/Caddy) with SSL certificate
   - Let's Encrypt for free SSL

3. **Firewall Rules**
   - Only expose port 3000 to your application server
   - Use VPN or private network if possible

4. **Regular Updates**
   ```bash
   docker pull devlikeapro/waha
   docker-compose restart
   ```

---

## Part 6: Troubleshooting

### Issue: QR Code Not Appearing

**Solution:**
1. Check WAHA logs: `docker logs waha`
2. Ensure port 3000 is accessible
3. Try different engine (NOWEB or GOWS instead of WEBJS)

### Issue: Session Disconnected

**Causes:**
- WhatsApp Web session expired
- Too many linked devices (max 4 companion devices)
- WhatsApp account banned/restricted

**Solution:**
1. Stop session in WAHA dashboard
2. Restart session and scan new QR code
3. Ensure you're using a legitimate WhatsApp account

### Issue: Webhook Not Receiving Messages

**Checklist:**
1. Verify webhook URL is correctly set in WAHA
2. Check your application is publicly accessible
3. Review application logs for incoming webhooks
4. Test webhook with cURL:
   ```bash
   curl -X POST https://your-app.replit.app/waha/1 \
     -H "Content-Type: application/json" \
     -d '{
       "event": "message",
       "session": "default",
       "payload": {
         "from": "6281234567890@c.us",
         "body": "test",
         "type": "chat"
       }
     }'
   ```

### Issue: Messages Not Sending

**Solution:**
1. Check WAHA session status (should be "WORKING")
2. Verify phone number format includes `@c.us`
3. Review WAHA logs for API errors
4. Test with WAHA Swagger UI: http://localhost:3000/

### Issue: Voice Messages Not Working

**WAHA Requirements:**
- Voice messages require media URL to be publicly accessible
- Ensure your Replit app serves `/static/uploads/audio/` publicly
- Check media file format (MP3 for WhatsApp)

---

## Part 7: WAHA vs Meta API Feature Comparison

| Feature | WAHA | Meta Business API |
|---------|------|-------------------|
| Setup Complexity | ⭐ Simple (Docker + QR) | ⭐⭐⭐⭐⭐ Complex (Business Manager) |
| Cost | Free (self-hosted) | Pay per conversation |
| Text Messages | ✅ | ✅ |
| Media Messages | ✅ | ✅ |
| Interactive Buttons | ✅ (WAHA Plus) | ✅ |
| Voice Messages | ✅ | ✅ |
| Template Messages | ❌ | ✅ |
| Business Verification | ❌ Not required | ✅ Required for production |
| Scale | Up to 500 sessions | Unlimited |
| Official Support | Community | Meta Support |

---

## Part 8: Migration from Meta Business API

### Switching an Existing Bot

1. **Backup Current Configuration**
   - Note down your Meta API credentials
   - Export user data if needed

2. **Set Up WAHA** (follow Part 1-2)

3. **Update Bot Settings**
   - Edit bot in admin dashboard
   - Change Connection Type to "WAHA"
   - Enter WAHA configuration

4. **Test with Test User**
   - Send message from test phone
   - Verify bot responds correctly

5. **Go Live**
   - Existing users will continue working
   - All new messages route through WAHA
   - Old Meta webhook can be removed

### Rollback to Meta API

If you need to switch back:
1. Edit bot configuration
2. Change Connection Type back to "Meta Business API"
3. All messages will route back to Meta API

---

## Part 9: Production Deployment Checklist

- [ ] WAHA running on reliable cloud server (not localhost)
- [ ] HTTPS enabled with valid SSL certificate
- [ ] Strong API key configured (32+ characters)
- [ ] Dashboard password changed from default
- [ ] Webhook URL uses HTTPS
- [ ] Firewall configured (only necessary ports exposed)
- [ ] Docker container set to restart automatically
- [ ] Session backups configured (`-v ./sessions:/app/.sessions`)
- [ ] Monitoring/alerts set up for server downtime
- [ ] Rate limiting configured if needed

---

## Part 10: Getting Help

### Resources

- **WAHA Official Docs**: https://waha.devlike.pro/docs/
- **WAHA GitHub**: https://github.com/devlikeapro/waha
- **API Documentation**: http://your-waha-server:3000/ (Swagger UI)
- **Postman Collection**: https://www.postman.com/devlikeapro/waha

### Support Channels

- GitHub Issues: https://github.com/devlikeapro/waha/issues
- Community Discord: (check WAHA docs)
- Stack Overflow: Tag `waha` or `whatsapp-api`

---

## Summary

You've successfully configured WAHA as a WhatsApp integration alternative! WAHA provides:
- Simpler setup compared to Meta Business API
- No per-conversation costs
- Full control over infrastructure
- Easy development and testing

Your bot can now send and receive WhatsApp messages through WAHA with the same features as the Meta Business API integration.

Need help? Check the troubleshooting section or reach out to WAHA community support.
