import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

class YouTubeAPI:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.readonly'
        ]
        self.api_service_name = 'youtube'
        self.api_version = 'v3'
        self.credentials = None
        self.service = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/youtube_api.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self):
        """Authenticate with YouTube API using OAuth2"""
        creds = None
        token_file = 'config/token.json'
        
        # Load existing credentials if available
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, self.scopes)
            
        # If no valid credentials, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    self.logger.info("Credentials refreshed successfully")
                except Exception as e:
                    self.logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
                    
            if not creds:
                # Use credentials file for OAuth flow
                credentials_file = 'credentials.json'
                
                if os.path.exists(credentials_file):
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
                    # Use a specific port to match redirect URIs
                    creds = flow.run_local_server(port=9000)
                else:
                    # Fallback to environment variables
                    client_config = {
                        "installed": {
                            "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                            "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                            "redirect_uris": ["http://localhost"]
                        }
                    }
                    
                    if not client_config["installed"]["client_id"] or not client_config["installed"]["client_secret"]:
                        raise ValueError("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file")
                    
                    flow = InstalledAppFlow.from_client_config(client_config, self.scopes)
                    # Use a specific port to match redirect URIs
                    creds = flow.run_local_server(port=9000)
                self.logger.info("New authentication completed")
                
            # Save credentials for future use
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
                
        self.credentials = creds
        self.service = build(self.api_service_name, self.api_version, credentials=creds)
        self.logger.info("YouTube API service initialized successfully")
        
    def get_channel_info(self):
        """Get information about the authenticated channel"""
        try:
            request = self.service.channels().list(
                part="snippet,contentDetails,statistics",
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                self.logger.info(f"Connected to channel: {channel['snippet']['title']}")
                return channel
            else:
                self.logger.error("No channel found for authenticated user")
                return None
                
        except HttpError as e:
            self.logger.error(f"Failed to get channel info: {e}")
            return None
            
    def test_connection(self):
        """Test the YouTube API connection"""
        try:
            self.authenticate()
            channel_info = self.get_channel_info()
            if channel_info:
                self.logger.info("YouTube API connection test successful")
                return True
            else:
                self.logger.error("YouTube API connection test failed")
                return False
        except Exception as e:
            self.logger.error(f"YouTube API connection test failed: {e}")
            return False


if __name__ == "__main__":
    # Test the YouTube API connection
    youtube_api = YouTubeAPI()
    if youtube_api.test_connection():
        print("✅ YouTube API setup successful!")
        channel_info = youtube_api.get_channel_info()
        if channel_info:
            print(f"Connected to: {channel_info['snippet']['title']}")
            print(f"Channel ID: {channel_info['id']}")
    else:
        print("❌ YouTube API setup failed. Please check your configuration.")