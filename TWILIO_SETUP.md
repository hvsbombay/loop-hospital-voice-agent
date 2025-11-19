# Twilio Integration Guide 📞

## Overview

Loop AI now supports phone call integration using Twilio! Users can call a phone number and interact with the voice assistant to search for hospitals.

## Setup Instructions

### 1. Create a Twilio Account

1. Go to [Twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free account (you get $15 credit)
3. Complete phone verification

### 2. Get Your Twilio Credentials

1. Go to [Twilio Console](https://console.twilio.com)
2. Find your **Account SID** and **Auth Token** on the dashboard
3. Go to **Phone Numbers** → **Manage** → **Buy a number**
4. Purchase a phone number with Voice capabilities

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567
```

### 4. Install Twilio SDK

```bash
pip install twilio==8.10.0
# Or reinstall all dependencies
pip install -r requirements.txt
```

### 5. Configure Twilio Webhook

You need to expose your local server to the internet so Twilio can reach it.

#### Option A: Using ngrok (Recommended for testing)

```bash
# Install ngrok
# Download from https://ngrok.com/download

# Start your FastAPI server
python main.py

# In another terminal, start ngrok
ngrok http 8000

# You'll get a URL like: https://abc123.ngrok.io
```

#### Option B: Deploy to a Server

Deploy your app to a cloud server (AWS, Heroku, DigitalOcean, etc.) with a public IP.

### 6. Set Up Twilio Webhook URL

1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to **Phone Numbers** → **Manage** → **Active numbers**
3. Click on your phone number
4. Under **Voice Configuration**:
   - **A CALL COMES IN**: Select "Webhook"
   - **URL**: Enter your webhook URL: `https://your-domain.com/twilio/voice`
   - **HTTP Method**: POST
5. Click **Save**

### 7. Test the Integration

Call your Twilio phone number and interact with Loop AI!

Example conversation:
```
📞 Call connects
🤖 "Hello! I am Loop AI, your hospital network assistant..."
👤 "Tell me hospitals in Mumbai"
🤖 "I found 3 hospitals in Mumbai: 1. Aadhar Multispeciality Hospital..."
👤 "Is Manipal in Bangalore in the network?"
🤖 "Yes, Manipal in Bengaluru is in our network..."
```

## API Endpoints

### `/twilio/voice` (POST)
Handles incoming calls and provides initial greeting.

**Twilio Configuration:**
- Webhook URL: `https://your-domain.com/twilio/voice`
- Method: POST

### `/twilio/process-speech` (POST)
Processes speech-to-text input and returns bot response.

**Parameters:**
- `SpeechResult`: Transcribed speech from caller
- `CallSid`: Unique call identifier

### `/twilio/status` (GET)
Check Twilio integration status.

**Response:**
```json
{
  "twilio_configured": true,
  "phone_number": "+12025551234",
  "account_sid": "AC123456..."
}
```

## How It Works

1. **User calls** your Twilio number
2. **Twilio forwards** the call to `/twilio/voice` webhook
3. **Loop AI greets** the caller with introduction
4. **Twilio captures** speech using speech recognition
5. **Speech is sent** to `/twilio/process-speech`
6. **Loop AI processes** the query using existing conversation logic
7. **Response is spoken** back to the caller using text-to-speech
8. **Call continues** with follow-up questions until user hangs up

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌───────────────┐
│   Caller    │─────▶│   Twilio     │─────▶│   Loop AI     │
│  (Phone)    │      │   (Cloud)    │      │  (FastAPI)    │
└─────────────┘      └──────────────┘      └───────────────┘
      ▲                      │                       │
      │                      │                       │
      └──────────────────────┴───────────────────────┘
           Voice Response (Text-to-Speech)
```

## Voice Features

- **Voice**: Amazon Polly "Joanna" (US English female voice)
- **Speech Recognition**: Twilio's built-in speech-to-text
- **Text-to-Speech**: Twilio's built-in TTS with Polly
- **Session Management**: Uses Twilio's CallSid for conversation continuity

## Costs

### Twilio Free Trial
- $15 credit
- Can make/receive calls for testing

### Twilio Pricing (Pay-as-you-go)
- **Phone Number**: $1/month
- **Voice Calls**: ~$0.013/minute (US)
- **Speech Recognition**: $0.02/minute
- **Text-to-Speech**: $0.004 per 100 characters

**Example Cost:**
- 5-minute call with speech recognition and TTS
- ~$0.13 total

## Troubleshooting

### "Webhook Error"
- Ensure your server is publicly accessible
- Check webhook URL is correct in Twilio Console
- Verify ngrok is running if using local development

### "Speech Not Recognized"
- Speak clearly and at normal pace
- Ensure good phone connection
- Check Twilio Console logs for transcription

### "No Response from Bot"
- Check server logs: `tail -f app.log`
- Verify hospital database is loaded
- Test `/health` endpoint

### Check Integration Status
```bash
curl http://localhost:8000/twilio/status
```

## Testing Without Phone Call

You can test the Twilio webhook logic locally:

```bash
# Test voice endpoint
curl -X POST http://localhost:8000/twilio/voice

# Test speech processing
curl -X POST http://localhost:8000/twilio/process-speech \
  -F "SpeechResult=Tell me hospitals in Delhi" \
  -F "CallSid=test-call-123"
```

## Security Best Practices

1. **Never commit** `.env` file to git
2. **Use environment variables** for credentials
3. **Validate Twilio requests** (optional: add signature validation)
4. **Use HTTPS** in production
5. **Rotate tokens** regularly

## Production Deployment

For production use:

1. **Deploy to cloud**:
   - AWS EC2/ECS
   - Heroku
   - DigitalOcean
   - Google Cloud Run

2. **Set up SSL/TLS** (required by Twilio):
   ```bash
   # Use Let's Encrypt for free SSL
   certbot --nginx -d yourdomain.com
   ```

3. **Configure environment**:
   ```bash
   export TWILIO_ACCOUNT_SID=your_sid
   export TWILIO_AUTH_TOKEN=your_token
   export TWILIO_PHONE_NUMBER=+1234567890
   ```

4. **Run with production server**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## Example .env File

```env
# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_32_character_auth_token_here
TWILIO_PHONE_NUMBER=+15551234567

# Optional: Server Configuration
PORT=8000
HOST=0.0.0.0
```

## Support

For issues with:
- **Twilio**: Check [Twilio Console Logs](https://console.twilio.com/monitor/logs/calls)
- **Loop AI**: Check server logs and GitHub issues
- **General**: Refer to [Twilio Docs](https://www.twilio.com/docs/voice)

## Next Steps

- [ ] Add call recording capability
- [ ] Implement SMS responses
- [ ] Add multi-language support
- [ ] Implement call analytics
- [ ] Add voicemail detection

---

**Last Updated**: November 19, 2025  
**Integration Status**: Complete ✓
