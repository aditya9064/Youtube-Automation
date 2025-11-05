import os
import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from video_uploader import VideoUploader
from config.settings import VALID_VIDEO_EXTENSIONS, WATCH_FOLDER


class VideoFileHandler(FileSystemEventHandler):
    """Handle new video file events"""
    
    def __init__(self, uploader):
        self.uploader = uploader
        self.processed_files = set()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for file monitoring"""
        self.logger = logging.getLogger(__name__)
        
        # Create file handler for monitoring logs
        monitor_log_handler = logging.FileHandler('logs/file_monitor.log')
        monitor_log_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        monitor_log_handler.setFormatter(formatter)
        
        self.logger.addHandler(monitor_log_handler)
        self.logger.setLevel(logging.INFO)
        
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
            
        self.process_new_file(event.src_path)
        
    def on_moved(self, event):
        """Handle file move events (e.g., when files are moved into the folder)"""
        if event.is_directory:
            return
            
        self.process_new_file(event.dest_path)
        
    def process_new_file(self, file_path):
        """Process a new video file"""
        file_path = Path(file_path)
        
        # Skip if already processed
        if str(file_path) in self.processed_files:
            return
            
        # Check if it's a video file
        if file_path.suffix.lower() not in VALID_VIDEO_EXTENSIONS:
            return
            
        self.logger.info(f"New video file detected: {file_path.name}")
        
        # Wait a moment to ensure file is completely written
        self.wait_for_file_completion(file_path)
        
        # Add to processed set to avoid duplicate processing
        self.processed_files.add(str(file_path))
        
        # Upload the video
        self.upload_video_file(file_path)
        
    def wait_for_file_completion(self, file_path, max_wait=300):
        """Wait for file to be completely written"""
        self.logger.info(f"Waiting for file completion: {file_path.name}")
        
        last_size = 0
        stable_count = 0
        wait_time = 0
        
        while wait_time < max_wait:
            try:
                current_size = file_path.stat().st_size
                
                if current_size == last_size:
                    stable_count += 1
                    if stable_count >= 3:  # File size stable for 3 checks
                        self.logger.info(f"File appears complete: {file_path.name}")
                        return True
                else:
                    stable_count = 0
                    last_size = current_size
                    
                time.sleep(5)  # Wait 5 seconds between checks
                wait_time += 5
                
            except FileNotFoundError:
                self.logger.warning(f"File disappeared during wait: {file_path}")
                return False
                
        self.logger.warning(f"Timeout waiting for file completion: {file_path.name}")
        return True  # Proceed anyway after timeout
        
    def upload_video_file(self, file_path):
        """Upload video file and handle the result"""
        try:
            self.logger.info(f"Starting upload process for: {file_path.name}")
            
            # Extract metadata from filename if possible
            custom_metadata = self.extract_metadata_from_filename(file_path)
            
            # Upload video
            result = self.uploader.upload_video(file_path, custom_metadata)
            
            if result and result['success']:
                self.logger.info(f"Upload successful: {result['video_url']}")
                
                # Move file to processed folder
                self.uploader.move_processed_file(file_path)
                
                # Send notification if configured
                self.send_notification(result, file_path)
                
            else:
                self.logger.error(f"Upload failed for: {file_path.name}")
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path.name}: {e}")
            
    def extract_metadata_from_filename(self, file_path):
        """Extract metadata from filename patterns"""
        filename = file_path.stem
        metadata = {}
        
        # Look for common patterns in Sora AI generated filenames
        # You can customize this based on how Sora AI names its files
        
        # Example: if filename contains "sora_video_title_here_20241104"
        if 'sora_' in filename.lower():
            # Extract title part
            parts = filename.lower().split('sora_')
            if len(parts) > 1:
                title_part = parts[1].replace('_', ' ').title()
                metadata['title'] = f"Sora AI: {title_part}"
                
        # Add timestamp-based titles if no specific pattern found
        if 'title' not in metadata:
            metadata['title'] = f"AI Generated Video - {file_path.stem.replace('_', ' ').title()}"
            
        # Add specific tags for Sora AI content
        metadata['tags'] = ['Sora AI', 'OpenAI', 'AI Generated Video', 'Artificial Intelligence']
        
        return metadata
        
    def send_notification(self, upload_result, file_path):
        """Send notification about successful upload"""
        try:
            # You can implement webhook notifications here
            # For example, Discord, Slack, or email notifications
            notification_message = (
                f"🎥 New video uploaded successfully!\n"
                f"Title: {upload_result['title']}\n"
                f"File: {file_path.name}\n"
                f"URL: {upload_result['video_url']}"
            )
            
            self.logger.info(f"Upload notification: {notification_message}")
            
            # TODO: Implement actual notification sending
            # self.send_webhook_notification(notification_message)
            
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")


class VideoMonitor:
    """Main video monitoring class"""
    
    def __init__(self):
        self.uploader = VideoUploader()
        self.observer = Observer()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup main logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/monitor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def start_monitoring(self, watch_folder=None):
        """Start monitoring for new video files"""
        if watch_folder is None:
            watch_folder = WATCH_FOLDER
            
        watch_path = Path(watch_folder)
        
        # Create watch folder if it doesn't exist
        watch_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Starting video file monitoring...")
        self.logger.info(f"Watching folder: {watch_path.absolute()}")
        
        # Process any existing files first
        self.process_existing_files(watch_path)
        
        # Setup file system watcher
        event_handler = VideoFileHandler(self.uploader)
        self.observer.schedule(event_handler, str(watch_path), recursive=False)
        
        # Start monitoring
        self.observer.start()
        
        try:
            self.logger.info("Video monitoring started. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Stopping video monitoring...")
        finally:
            self.observer.stop()
            self.observer.join()
            self.logger.info("Video monitoring stopped.")
            
    def process_existing_files(self, watch_folder):
        """Process any existing video files in the watch folder"""
        self.logger.info("Checking for existing video files...")
        
        video_files = []
        for ext in VALID_VIDEO_EXTENSIONS:
            video_files.extend(watch_folder.glob(f"*{ext}"))
            
        if video_files:
            self.logger.info(f"Found {len(video_files)} existing video file(s)")
            
            event_handler = VideoFileHandler(self.uploader)
            for video_file in video_files:
                self.logger.info(f"Processing existing file: {video_file.name}")
                event_handler.process_new_file(video_file)
        else:
            self.logger.info("No existing video files found")


if __name__ == "__main__":
    # Start video monitoring
    monitor = VideoMonitor()
    monitor.start_monitoring()