# YouTube API Setup Guide

This guide walks you through setting up the YouTube Data API v3 for automated video uploads.

## Step 1: Google Cloud Console Setup

### Create a Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter a project name (e.g., "YouTube Video Automation")
4. Click "Create"

### Enable YouTube Data API v3
1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

## Step 2: OAuth2 Credentials

### Create OAuth2 Client
1. Go to "APIs & Services" → "Credentials"
2. Click "+ Create Credentials" → "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen first:
   - Choose "External" user type
   - Fill in application name: "YouTube Video Automation"
   - Add your email as developer contact
   - Add scopes: `../auth/youtube.upload`
   - Add test users (your email)

### Configure OAuth Client
1. Choose "Desktop application" as application type
2. Name: "YouTube Upload Client"
3. Click "Create"
4. Download the JSON file or copy the Client ID and Client Secret

## Step 3: Environment Configuration

### Create .env file
```bash
cp .env.example .env
```

### Fill in credentials in .env:
```
GOOGLE_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_CHANNEL_ID=your_channel_id_here
```

### Find Your Channel ID
1. Go to [YouTube Studio](https://studio.youtube.com/)
2. Go to Settings → Channel → Basic info
3. Copy the Channel ID

OR

1. Go to your channel page on YouTube
2. Look at the URL: `youtube.com/channel/UC...` 
3. The part after `/channel/` is your Channel ID

## Step 4: Test Authentication

Run the test script:
```bash
python src/youtube_auth.py
```

This will:
1. Open a browser window for OAuth authentication
2. Ask you to sign in to Google
3. Request permission to access your YouTube account
4. Save authentication tokens for future use

## Step 5: Verification

Check that everything works:
```bash
python main.py status
```

You should see:
- ✅ Configuration Status: Valid
- ✅ All directories created
- ✅ YouTube API connection successful

## Troubleshooting

### "Client ID not found" Error
- Double-check your GOOGLE_CLIENT_ID in .env
- Ensure there are no extra spaces or quotes
- Verify the client ID ends with `.apps.googleusercontent.com`

### "Access blocked" Error
- Your OAuth consent screen might need verification
- Add yourself as a test user in the OAuth consent screen
- Make sure the app is in "Testing" mode for personal use

### "YouTube API not enabled" Error
- Go back to APIs & Services → Library
- Search for "YouTube Data API v3" and ensure it's enabled
- Wait a few minutes after enabling

### "Quota exceeded" Error
- Check your quota usage in Google Cloud Console
- Default quota should be sufficient for personal use
- Consider requesting a quota increase for heavy usage

## Security Notes

- Keep your Client Secret confidential
- Never commit .env files to version control
- The token.json file contains your access tokens - keep it secure
- Consider using a service account for production deployments

## API Quotas and Limits

### Default Quotas
- Queries per day: 10,000 units
- Video upload: ~1,600 units per upload
- You can upload ~6 videos per day with default quota

### Request Quota Increase
If you need higher limits:
1. Go to Google Cloud Console → APIs & Services → Quotas
2. Find "YouTube Data API v3"
3. Click on the quota limit you want to increase
4. Click "Edit Quotas" and fill out the form

## OAuth Consent Screen Configuration

### Required Information
- Application name: "YouTube Video Automation"
- User support email: Your email
- Developer contact: Your email

### Scopes
Add this scope:
- `https://www.googleapis.com/auth/youtube.upload`

### Test Users
Add your Gmail address as a test user to avoid verification requirements.

## Production Considerations

### Service Account (Optional)
For unattended server deployment, consider using a service account:
1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Use `google.oauth2.service_account.Credentials`
4. Note: Service accounts have limitations with YouTube uploads

### Domain Verification
For public applications, you'll need to:
1. Verify your domain
2. Submit for OAuth verification
3. This is not required for personal use

---

**Need help?** Run `python main.py status` to check your configuration!