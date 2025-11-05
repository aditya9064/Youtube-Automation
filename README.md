# YouTube Video Automation Pipeline for Sora AI

This project provides an automated pipeline to upload Sora AI-generated videos to your YouTube channel using the YouTube Data API v3.

## Features

- 🤖 **Automated Upload**: Automatically uploads videos from a watched folder
- 📁 **File Monitoring**: Monitors a directory for new Sora AI videos
- ⚡ **Real-time Processing**: Processes videos as soon as they're detected
- 🔄 **Retry Logic**: Robust error handling with automatic retries
- 📊 **Comprehensive Logging**: Detailed logging for monitoring and debugging
- ⚙️ **Configurable**: Easy configuration via JSON and environment variables
- 🎯 **Multiple Modes**: Continuous monitoring, scheduled checks, or manual uploads
- 📈 **Progress Tracking**: Upload progress monitoring with detailed status

## Quick Start

### 1. Prerequisites

- Python 3.8 or higher
- Google Cloud Platform account
- YouTube channel

### 2. Installation

```bash
# Clone or download this project
cd "video automation"

# Install dependencies (virtual environment already configured)
pip install -r requirements.txt
```

### 3. Google API Setup

1. **Enable YouTube Data API v3**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the YouTube Data API v3
   - Go to APIs & Services > Credentials

2. **Create OAuth2 Credentials**:
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Desktop Application" as the application type
   - Download the credentials JSON file
   - Extract `client_id` and `client_secret` from the JSON

3. **Configure Environment Variables**:
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env with your credentials
   nano .env
   ```
   
   Fill in your values:
   ```
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   YOUTUBE_CHANNEL_ID=your_channel_id_here
   ```

### 4. First Run & Authentication

```bash
# Test the setup and authenticate
python main.py status
```

This will:
- Check your configuration
- Prompt you to authenticate with Google (opens browser)
- Save authentication tokens for future use

### 5. Start Automation

```bash
# Option 1: Continuous monitoring (recommended)
python main.py monitor

# Option 2: Scheduled checks every 30 minutes
python main.py schedule --interval 30

# Option 3: Upload a specific file
python main.py upload --file "path/to/video.mp4"
```

## Usage Modes

### 1. Continuous Monitoring
Watches the `videos/input` folder and uploads new videos immediately:

```bash
python main.py monitor
```

### 2. Scheduled Checks
Periodically checks for new videos:

```bash
# Check every 15 minutes
python main.py schedule --interval 15

# Check every hour
python main.py schedule --interval 60
```

### 3. Manual Upload
Upload specific videos with custom metadata:

```bash
# Basic upload
python main.py upload --file "my_video.mp4"

# Upload with custom title and description
python main.py upload --file "my_video.mp4" --title "My Custom Title" --description "Custom description"

# Upload as public video
python main.py upload --file "my_video.mp4" --privacy public
```

### 4. Batch Upload
Upload all videos from a folder:

```bash
python main.py batch --folder "path/to/video/folder"
```

### 5. Status Check
Check system status and view recent uploads:

```bash
python main.py status
```

## Configuration

### Video Metadata Template
Edit `config/config.json` to customize default video metadata:

```json
{
  "video_metadata_template": {
    "title_prefix": "Sora AI Generated: ",
    "description_template": "This video was generated using Sora AI...",
    "default_tags": ["Sora AI", "AI Generated", "OpenAI"]
  },
  "channel_settings": {
    "default_privacy": "private",
    "default_category": "22"
  }
}
```

### File Processing Settings
Configure file handling in `config/settings.py`:

```python
# Supported video formats
VALID_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']

# File size limit (YouTube's limit is 128GB, but we use 2GB for efficiency)
MAX_FILE_SIZE_MB = 2048

# Upload retry settings
UPLOAD_RETRY_ATTEMPTS = 3
UPLOAD_RETRY_DELAY = 60  # seconds
```

## Folder Structure

```
video automation/
├── main.py                 # Main entry point
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
├── .env                   # Your environment variables (create this)
├── src/
│   ├── youtube_auth.py    # YouTube API authentication
│   ├── video_uploader.py  # Video upload functionality
│   ├── file_monitor.py    # File monitoring system
│   ├── config_manager.py  # Configuration management
│   └── error_handler.py   # Error handling and logging
├── config/
│   ├── settings.py        # Application settings
│   ├── config.json        # Configuration file
│   └── token.json         # OAuth tokens (auto-generated)
├── videos/
│   ├── input/            # Place Sora AI videos here
│   └── processed/        # Successfully uploaded videos moved here
└── logs/
    ├── automation.log    # Main application logs
    ├── uploads.log       # Upload-specific logs
    ├── monitor.log       # File monitoring logs
    ├── errors.log        # Error logs
    └── upload_records.json # Upload history
```

## Sora AI Integration

### Automated Workflow
1. **Generate Videos**: Use Sora AI to create videos
2. **Save to Input Folder**: Place generated videos in `videos/input/`
3. **Automatic Processing**: The system detects and uploads them automatically
4. **File Management**: Processed videos are moved to `videos/processed/`

### Filename-Based Metadata
The system can extract metadata from Sora AI filenames:

```python
# Example: "sora_amazing_sunset_scene_20241104.mp4"
# Becomes: Title "Sora AI: Amazing Sunset Scene"
```

You can customize this in `src/file_monitor.py` in the `extract_metadata_from_filename()` function.

## Monitoring and Logging

### Log Files
- `logs/automation.log` - Main application events
- `logs/uploads.log` - Detailed upload progress and results  
- `logs/monitor.log` - File monitoring events
- `logs/errors.log` - Error details with stack traces
- `logs/upload_records.json` - Complete upload history

### System Health
```bash
# Check system status
python main.py status

# View recent logs
tail -f logs/automation.log

# Check upload history
cat logs/upload_records.json
```

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   ```
   Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set
   ```
   - Check your `.env` file
   - Verify credentials from Google Cloud Console
   - Ensure YouTube Data API v3 is enabled

2. **Upload Failed - Quota Exceeded**
   - YouTube API has daily quotas
   - Default quota is usually sufficient for personal use
   - Request quota increase in Google Cloud Console if needed

3. **File Not Detected**
   - Ensure file is in `videos/input/` folder
   - Check file extension is supported (`.mp4`, `.mov`, etc.)
   - Wait for file to finish copying before the system processes it

4. **Permission Denied**
   - Run the authentication flow again
   - Delete `config/token.json` to force re-authentication
   - Check OAuth consent screen configuration

### Debug Mode
Enable detailed logging by editing `src/error_handler.py`:

```python
# Change logging level for more details
self.main_logger.setLevel(logging.DEBUG)
```

## Security Considerations

- Keep your `.env` file secure and never commit it to version control
- The `config/token.json` file contains sensitive authentication tokens
- Consider using a service account for production deployments
- Regularly rotate your API credentials

## Customization

### Custom Video Titles
Edit the `generate_metadata()` function in `src/video_uploader.py`:

```python
def generate_metadata(self, file_path, custom_metadata=None):
    # Your custom title generation logic here
    metadata['snippet']['title'] = f"My Custom Prefix: {file_path.stem}"
```

### Notification Integration
Add webhook notifications in `src/file_monitor.py`:

```python
def send_notification(self, upload_result, file_path):
    # Add Discord, Slack, or email notifications here
    webhook_url = os.getenv('WEBHOOK_URL')
    if webhook_url:
        # Send notification to webhook
        pass
```

### Custom Processing
Modify `src/file_monitor.py` to add custom video processing before upload:

```python
def process_new_file(self, file_path):
    # Add custom processing here
    # E.g., video compression, thumbnail generation, etc.
    self.upload_video_file(file_path)
```

## API Limits and Best Practices

### YouTube API Quotas
- Default quota: 10,000 units per day
- Video upload costs: ~1,600 units per upload
- Monitor usage in Google Cloud Console

### Best Practices
- Upload videos as "private" initially, then make public manually
- Use appropriate video categories and tags
- Keep video titles under 100 characters
- Ensure video descriptions are meaningful

## Support

### Getting Help
1. Check the logs in the `logs/` folder
2. Run `python main.py status` to diagnose issues
3. Verify your Google Cloud Console setup
4. Check that all dependencies are installed correctly

### Common Commands
```bash
# Full system check
python main.py status

# Test authentication
python src/youtube_auth.py

# Test configuration
python src/config_manager.py

# Test logging system
python src/error_handler.py
```

## License

This project is provided as-is for educational and personal use. Please ensure compliance with YouTube's Terms of Service and API usage policies.

---

**Ready to automate your Sora AI video uploads?** Start with `python main.py status` to verify your setup!