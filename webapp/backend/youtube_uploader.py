"""
YouTube Upload Integration for Video Automation
Handles OAuth authentication and video uploads to YouTube
"""

import os
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class YouTubeUploader:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/youtube.readonly',
            'https://www.googleapis.com/auth/youtube.force-ssl'
        ]
        self.api_service_name = 'youtube'
        self.api_version = 'v3'
        self.credentials = None
        self.service = None
        
        # Configuration
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        self.upload_enabled = os.getenv('YOUTUBE_UPLOAD_ENABLED', 'false').lower() == 'true'
        self.default_privacy = os.getenv('DEFAULT_YOUTUBE_PRIVACY', 'private')
        self.default_category = os.getenv('DEFAULT_YOUTUBE_CATEGORY', '22')  # People & Blogs
        
        # Paths
        self.token_file = 'config/youtube_token.json'
        self.credentials_file = 'config/youtube_credentials.json'
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
    def _create_credentials_file(self):
        """Create OAuth credentials file from environment variables"""
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your .env file.\n"
                "Get these from: https://console.developers.google.com/\n"
                "1. Create a project\n"
                "2. Enable YouTube Data API v3\n" 
                "3. Create OAuth 2.0 credentials (Desktop application)\n"
                "4. Add the client ID and secret to your .env file"
            )
            
        credentials_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost", "urn:ietf:wg:oauth:2.0:oob"]
            }
        }
        
        # Ensure config directory exists
        os.makedirs('config', exist_ok=True)
        
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials_config, f, indent=2)
            
        return self.credentials_file
    
    async def authenticate(self, force_reauth: bool = False):
        """Authenticate with YouTube API using OAuth2"""
        creds = None
        
        # Load existing credentials if available
        if os.path.exists(self.token_file) and not force_reauth:
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
                self.logger.info("Loaded existing YouTube credentials")
            except Exception as e:
                self.logger.warning(f"Failed to load existing credentials: {e}")
                creds = None
                
        # Check if credentials are valid
        if creds and creds.valid:
            self.credentials = creds
            self.service = build(self.api_service_name, self.api_version, credentials=creds)
            self.logger.info("YouTube API service initialized with existing credentials")
            return True
            
        # Refresh expired credentials
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self.logger.info("YouTube credentials refreshed successfully")
                
                # Save refreshed credentials
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                    
                self.credentials = creds
                self.service = build(self.api_service_name, self.api_version, credentials=creds)
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to refresh YouTube credentials: {e}")
                creds = None
                
        # Need new authentication
        if not creds or force_reauth:
            self.logger.info("Starting new YouTube authentication flow...")
            
            # Create credentials file
            credentials_file = self._create_credentials_file()
            
            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, self.scopes)
            creds = flow.run_local_server(port=8080, prompt='consent')
            
            # Save credentials for future use
            os.makedirs('config', exist_ok=True)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                
            self.logger.info("New YouTube authentication completed and saved")
            
        self.credentials = creds
        self.service = build(self.api_service_name, self.api_version, credentials=creds)
        self.logger.info("YouTube API service initialized successfully")
        return True
        
    async def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the authenticated YouTube channel"""
        if not self.service:
            await self.authenticate()
            
        try:
            request = self.service.channels().list(
                part="snippet,contentDetails,statistics,brandingSettings",
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                self.logger.info(f"Connected to YouTube channel: {channel['snippet']['title']}")
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'description': channel['snippet']['description'],
                    'thumbnail': channel['snippet']['thumbnails']['high']['url'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', '0'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0'),
                    'custom_url': channel['snippet'].get('customUrl', ''),
                    'country': channel['snippet'].get('country', ''),
                    'published_at': channel['snippet']['publishedAt']
                }
            else:
                self.logger.error("No YouTube channel found for authenticated user")
                return None
                
        except HttpError as e:
            self.logger.error(f"Failed to get YouTube channel info: {e}")
            return None
            
    async def upload_video(self, 
                          video_path: str,
                          title: str,
                          description: str = "",
                          tags: list = None,
                          category_id: str = None,
                          privacy: str = None,
                          thumbnail_path: str = None) -> Optional[Dict[str, Any]]:
        """Upload a video to YouTube"""
        
        if not self.upload_enabled:
            raise ValueError("YouTube upload is disabled. Set YOUTUBE_UPLOAD_ENABLED=true in .env")
            
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        if not self.service:
            await self.authenticate()
            
        try:
            # Default values
            if not tags:
                tags = ["AI Generated", "Sora", "Automation", "Video"]
            if not category_id:
                category_id = self.default_category
            if not privacy:
                privacy = self.default_privacy
                
            # Video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': tags,
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy,
                    'embeddable': True,
                    'license': 'youtube',
                    'publicStatsViewable': True
                }
            }
            
            # Media upload
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/*'
            )
            
            self.logger.info(f"Starting YouTube upload: {title}")
            
            # Insert video
            insert_request = self.service.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            # Execute upload with progress tracking
            video_response = None
            while video_response is None:
                status, video_response = insert_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    self.logger.info(f"Upload progress: {progress}%")
                    
            video_id = video_response['id']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            self.logger.info(f"✅ Video uploaded successfully!")
            self.logger.info(f"Video ID: {video_id}")
            self.logger.info(f"Video URL: {video_url}")
            
            # Upload thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    thumbnail_media = MediaFileUpload(
                        thumbnail_path,
                        mimetype='image/jpeg',
                        resumable=True
                    )
                    
                    thumbnail_request = self.service.thumbnails().set(
                        videoId=video_id,
                        media_body=thumbnail_media
                    )
                    thumbnail_request.execute()
                    self.logger.info("✅ Custom thumbnail uploaded")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to upload thumbnail: {e}")
            
            return {
                'success': True,
                'video_id': video_id,
                'video_url': video_url,
                'title': title,
                'privacy': privacy,
                'uploaded_at': datetime.now().isoformat()
            }
            
        except HttpError as e:
            error_msg = f"YouTube upload failed: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'error_code': e.resp.status if hasattr(e, 'resp') else 'unknown'
            }
        except Exception as e:
            error_msg = f"Unexpected error during YouTube upload: {e}"
            self.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
            
    async def test_connection(self) -> Dict[str, Any]:
        """Test the YouTube API connection"""
        try:
            if not self.client_id or not self.client_secret:
                return {
                    'success': False,
                    'error': 'Google OAuth credentials not configured',
                    'setup_required': True
                }
                
            await self.authenticate()
            channel_info = await self.get_channel_info()
            
            if channel_info:
                return {
                    'success': True,
                    'message': 'YouTube API connection successful',
                    'channel': channel_info,
                    'upload_enabled': self.upload_enabled
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to retrieve channel information'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'YouTube API connection test failed: {str(e)}'
            }


# Global instance
youtube_uploader = YouTubeUploader()


async def upload_video_to_youtube(video_path: str, title: str, description: str = "", **kwargs):
    """Convenience function for uploading videos"""
    return await youtube_uploader.upload_video(
        video_path=video_path,
        title=title,
        description=description,
        **kwargs
    )


if __name__ == "__main__":
    # Test the YouTube upload system
    async def test_youtube():
        uploader = YouTubeUploader()
        result = await uploader.test_connection()
        
        if result['success']:
            print("✅ YouTube API setup successful!")
            if 'channel' in result:
                channel = result['channel']
                print(f"Connected to: {channel['title']}")
                print(f"Channel ID: {channel['id']}")
                print(f"Subscribers: {channel['subscriber_count']}")
        else:
            print("❌ YouTube API setup failed:")
            print(f"Error: {result['error']}")
            
            if result.get('setup_required'):
                print("\n🔧 Setup Instructions:")
                print("1. Go to https://console.developers.google.com/")
                print("2. Create a new project or select existing one")
                print("3. Enable YouTube Data API v3")
                print("4. Create OAuth 2.0 credentials (Desktop application)")
                print("5. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env file")
    
    asyncio.run(test_youtube())