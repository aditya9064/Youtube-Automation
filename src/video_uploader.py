import os
import time
import json
from datetime import datetime
from pathlib import Path
import logging
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError, ResumableUploadError
from youtube_auth import YouTubeAPI
from config.settings import *


class VideoUploader:
    def __init__(self):
        self.youtube_api = YouTubeAPI()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for video uploads"""
        self.logger = logging.getLogger(__name__)
        
        # Create file handler for upload logs
        upload_log_handler = logging.FileHandler('logs/video_uploads.log')
        upload_log_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        upload_log_handler.setFormatter(formatter)
        
        self.logger.addHandler(upload_log_handler)
        self.logger.setLevel(logging.INFO)
        
    def validate_video_file(self, file_path):
        """Validate video file before upload"""
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False
            
        # Check file extension
        if file_path.suffix.lower() not in VALID_VIDEO_EXTENSIONS:
            self.logger.error(f"Invalid file extension: {file_path.suffix}")
            return False
            
        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            self.logger.error(f"File too large: {file_size_mb:.2f}MB (max: {MAX_FILE_SIZE_MB}MB)")
            return False
            
        self.logger.info(f"Video file validation passed: {file_path.name} ({file_size_mb:.2f}MB)")
        return True
        
    def generate_metadata(self, file_path, custom_metadata=None):
        """Generate video metadata from filename and custom settings"""
        file_path = Path(file_path)
        
        # Default metadata
        metadata = {
            'snippet': {
                'title': file_path.stem.replace('_', ' ').title(),
                'description': self.generate_description(file_path),
                'tags': DEFAULT_VIDEO_TAGS.copy(),
                'categoryId': DEFAULT_VIDEO_CATEGORY
            },
            'status': {
                'privacyStatus': DEFAULT_VIDEO_PRIVACY,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Apply custom metadata if provided
        if custom_metadata:
            if 'title' in custom_metadata:
                metadata['snippet']['title'] = custom_metadata['title']
            if 'description' in custom_metadata:
                metadata['snippet']['description'] = custom_metadata['description']
            if 'tags' in custom_metadata:
                metadata['snippet']['tags'].extend(custom_metadata['tags'])
            if 'privacy' in custom_metadata:
                metadata['status']['privacyStatus'] = custom_metadata['privacy']
                
        return metadata
        
    def generate_description(self, file_path):
        """Generate video description"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        description = f"""This video was generated using Sora AI and automatically uploaded.

📅 Generated: {timestamp}
🤖 AI Model: Sora AI by OpenAI
⚡ Automated Upload: YouTube Upload Automation Pipeline

#SoraAI #AIGenerated #AutomatedUpload #AIVideo"""
        
        return description
        
    def upload_video(self, file_path, custom_metadata=None):
        """Upload video to YouTube with retry logic"""
        if not self.validate_video_file(file_path):
            return None
            
        file_path = Path(file_path)
        metadata = self.generate_metadata(file_path, custom_metadata)
        
        self.logger.info(f"Starting upload for: {file_path.name}")
        
        # Authenticate with YouTube API
        try:
            self.youtube_api.authenticate()
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return None
            
        # Attempt upload with retry logic
        for attempt in range(UPLOAD_RETRY_ATTEMPTS):
            try:
                # Create media upload object
                media = MediaFileUpload(
                    str(file_path),
                    chunksize=-1,
                    resumable=True,
                    mimetype=self.get_mime_type(file_path)
                )
                
                # Create upload request
                request = self.youtube_api.service.videos().insert(
                    part=','.join(metadata.keys()),
                    body=metadata,
                    media_body=media
                )
                
                # Execute upload with progress tracking
                response = None
                error = None
                retry = 0
                
                while response is None:
                    try:
                        status, response = request.next_chunk()
                        if status:
                            progress = int(status.progress() * 100)
                            self.logger.info(f"Upload progress: {progress}%")
                            
                    except HttpError as e:
                        if e.resp.status in [500, 502, 503, 504]:
                            error = f"Retriable HTTP error: {e}"
                            self.logger.warning(error)
                            retry += 1
                            if retry > 3:
                                raise e
                            time.sleep(2 ** retry)
                        else:
                            raise e
                            
                    except ResumableUploadError as e:
                        error = f"Resumable upload error: {e}"
                        self.logger.warning(error)
                        retry += 1
                        if retry > 3:
                            raise e
                        time.sleep(2 ** retry)
                        
                if response:
                    video_id = response['id']
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    
                    self.logger.info(f"Upload successful!")
                    self.logger.info(f"Video ID: {video_id}")
                    self.logger.info(f"Video URL: {video_url}")
                    
                    # Log upload details
                    upload_record = {
                        'timestamp': datetime.now().isoformat(),
                        'filename': file_path.name,
                        'video_id': video_id,
                        'video_url': video_url,
                        'title': metadata['snippet']['title'],
                        'privacy': metadata['status']['privacyStatus']
                    }
                    
                    self.save_upload_record(upload_record)
                    
                    return {
                        'success': True,
                        'video_id': video_id,
                        'video_url': video_url,
                        'title': metadata['snippet']['title']
                    }
                    
            except HttpError as e:
                self.logger.error(f"Upload attempt {attempt + 1} failed: {e}")
                if attempt < UPLOAD_RETRY_ATTEMPTS - 1:
                    self.logger.info(f"Retrying in {UPLOAD_RETRY_DELAY} seconds...")
                    time.sleep(UPLOAD_RETRY_DELAY)
                else:
                    self.logger.error(f"Upload failed after {UPLOAD_RETRY_ATTEMPTS} attempts")
                    
            except Exception as e:
                self.logger.error(f"Unexpected error during upload: {e}")
                break
                
        return None
        
    def get_mime_type(self, file_path):
        """Get MIME type for video file"""
        extension = Path(file_path).suffix.lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm'
        }
        return mime_types.get(extension, 'video/mp4')
        
    def save_upload_record(self, record):
        """Save upload record to JSON file"""
        records_file = Path('logs/upload_records.json')
        
        # Load existing records
        if records_file.exists():
            with open(records_file, 'r') as f:
                try:
                    records = json.load(f)
                except json.JSONDecodeError:
                    records = []
        else:
            records = []
            
        # Add new record
        records.append(record)
        
        # Save updated records
        with open(records_file, 'w') as f:
            json.dump(records, f, indent=2)
            
    def move_processed_file(self, file_path):
        """Move uploaded file to processed folder"""
        try:
            file_path = Path(file_path)
            processed_path = Path(PROCESSED_FOLDER) / file_path.name
            
            # Create processed folder if it doesn't exist
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file
            file_path.rename(processed_path)
            self.logger.info(f"Moved file to processed folder: {processed_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to move file to processed folder: {e}")


if __name__ == "__main__":
    # Test video upload functionality
    uploader = VideoUploader()
    
    # Test with a sample video file (you'll need to place a video in the videos/input folder)
    test_video = Path("videos/input")
    video_files = list(test_video.glob("*"))
    video_files = [f for f in video_files if f.suffix.lower() in VALID_VIDEO_EXTENSIONS]
    
    if video_files:
        print(f"Found {len(video_files)} video file(s) for testing")
        test_file = video_files[0]
        
        # Test upload
        result = uploader.upload_video(test_file)
        if result and result['success']:
            print(f"✅ Test upload successful!")
            print(f"Video URL: {result['video_url']}")
            uploader.move_processed_file(test_file)
        else:
            print("❌ Test upload failed")
    else:
        print("No video files found in videos/input folder for testing")
        print("Add a video file to test the upload functionality")