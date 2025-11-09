# YouTube OAuth Setup Guide

This guide will help you configure YouTube OAuth integration for automated video uploads.

## Prerequisites

- Google Cloud Project
- YouTube Data API v3 enabled
- OAuth 2.0 credentials configured

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Click "Create Project" or select existing project
3. Give your project a name (e.g., "YouTube Automation")
4. Click "Create"

## Step 2: Enable YouTube Data API v3

1. In your Google Cloud project, go to "APIs & Services" > "Library"
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace)
   - Fill in app name, user support email, and developer email
   - Add your domain (or use localhost for testing)
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
4. For Application type, choose "Desktop application"
5. Give it a name (e.g., "YouTube Automation Client")
6. Click "Create"

## Step 4: Download and Configure Credentials

1. Download the JSON credentials file
2. Copy the `client_id` and `client_secret` values
3. Add them to your `.env` file:

```env
# YouTube OAuth Configuration
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here
YOUTUBE_UPLOAD_ENABLED=true
DEFAULT_YOUTUBE_PRIVACY=private
DEFAULT_YOUTUBE_CATEGORY=22
```

## Step 5: Test the Integration

1. Restart your backend server
2. Go to the web interface
3. Navigate to Settings or YouTube section
4. Click "Test YouTube Connection"
5. Follow the OAuth flow to authenticate

## Privacy Settings

- `private`: Only you can view the video
- `unlisted`: Anyone with the link can view
- `public`: Anyone can find and view the video

## Category IDs

Common YouTube category IDs:
- 1: Film & Animation
- 2: Autos & Vehicles
- 10: Music
- 15: Pets & Animals
- 17: Sports
- 19: Travel & Events
- 20: Gaming
- 22: People & Blogs (default)
- 23: Comedy
- 24: Entertainment
- 25: News & Politics
- 26: Howto & Style
- 27: Education
- 28: Science & Technology

## Troubleshooting

### "YouTube integration not available"
- Check that all required Python packages are installed
- Verify your `.env` file has the correct credentials

### "Authentication failed"
- Verify your client ID and secret are correct
- Make sure YouTube Data API v3 is enabled
- Check that your OAuth consent screen is configured

### "Access denied"
- Your Google account may not have YouTube channel access
- Ensure you're signing in with the correct Google account
- Check OAuth scopes include YouTube upload permissions

### "Upload failed"
- Verify the video file exists and is not corrupted
- Check that `YOUTUBE_UPLOAD_ENABLED=true` in your `.env`
- Ensure your API quotas haven't been exceeded

## Security Notes

- Keep your client secret secure and never commit it to version control
- Use environment variables for all sensitive configuration
- Consider using service accounts for production deployments
- Monitor your API usage to stay within quotas

## API Quotas

YouTube Data API v3 has daily quotas:
- Default quota: 10,000 units per day
- Video upload: ~1600 units per upload
- You can request quota increases through Google Cloud Console

## Next Steps

Once configured, your YouTube integration will:
1. Automatically authenticate when needed
2. Upload generated videos with metadata
3. Set appropriate privacy and category settings
4. Provide YouTube URLs for successful uploads
5. Handle errors gracefully with detailed logging