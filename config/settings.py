# YouTube API Configuration
YOUTUBE_API_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'

# Environment variables (create a .env file with your actual values)
# GOOGLE_CLIENT_ID=your_client_id_here
# GOOGLE_CLIENT_SECRET=your_client_secret_here
# YOUTUBE_CHANNEL_ID=your_channel_id_here

# Video processing settings
VALID_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
MAX_FILE_SIZE_MB = 2048  # 2GB limit for YouTube uploads
UPLOAD_RETRY_ATTEMPTS = 3
UPLOAD_RETRY_DELAY = 60  # seconds

# File monitoring settings
WATCH_FOLDER = './videos/input'
PROCESSED_FOLDER = './videos/processed'
CHECK_INTERVAL = 30  # seconds

# Default video metadata
DEFAULT_VIDEO_PRIVACY = 'private'  # private, public, unlisted
DEFAULT_VIDEO_CATEGORY = '22'  # People & Blogs category
DEFAULT_VIDEO_TAGS = ['AI Generated', 'Sora AI', 'Automated Upload']