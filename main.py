#!/usr/bin/env python3
"""
YouTube Video Automation Pipeline
Main entry point for the automated video upload system
"""

import os
import sys
import time
import signal
import argparse
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from file_monitor import VideoMonitor
from video_uploader import VideoUploader
from config_manager import ConfigManager
from error_handler import get_logger, setup_exception_handler, ErrorHandler
import schedule


class AutomationScheduler:
    """Main scheduler for the video automation pipeline"""
    
    def __init__(self):
        self.config = ConfigManager()
        self.logger, self.error_handler = get_logger()
        self.monitor = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Setup global exception handling
        setup_exception_handler()
        
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.main_logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
        
    def validate_setup(self):
        """Validate that the system is properly configured"""
        self.logger.main_logger.info("Validating system setup...")
        
        # Check credentials
        valid_creds, missing = self.config.validate_credentials()
        if not valid_creds:
            self.logger.log_configuration(False, missing)
            return False
            
        # Ensure directories exist
        self.config.ensure_directories()
        
        # Test YouTube API connection
        try:
            uploader = VideoUploader()
            if not uploader.youtube_api.test_connection():
                self.logger.main_logger.error("YouTube API connection test failed")
                return False
        except Exception as e:
            self.error_handler.handle_authentication_error(e)
            return False
            
        self.logger.log_configuration(True)
        return True
        
    def run_continuous_monitoring(self):
        """Run continuous file monitoring mode"""
        self.logger.main_logger.info("Starting continuous monitoring mode...")
        
        if not self.validate_setup():
            return False
            
        self.monitor = VideoMonitor()
        try:
            self.monitor.start_monitoring()
        except KeyboardInterrupt:
            self.logger.main_logger.info("Monitoring stopped by user")
        except Exception as e:
            self.error_handler.handle_file_processing_error(e, "continuous_monitoring")
            
        return True
        
    def run_scheduled_checks(self, interval_minutes=30):
        """Run scheduled periodic checks for new files"""
        self.logger.main_logger.info(f"Starting scheduled mode (every {interval_minutes} minutes)...")
        
        if not self.validate_setup():
            return False
            
        def check_and_process():
            """Check for new files and process them"""
            try:
                self.logger.main_logger.info("Running scheduled file check...")
                
                # Process any existing files in the input folder
                monitor = VideoMonitor()
                input_path = self.config.get_paths()['input_folder']
                monitor.process_existing_files(input_path)
                
                self.logger.main_logger.info("Scheduled file check completed")
                
            except Exception as e:
                self.error_handler.handle_file_processing_error(e, "scheduled_check")
                
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(check_and_process)
        
        self.running = True
        self.logger.main_logger.info("Scheduler started. Press Ctrl+C to stop.")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.main_logger.info("Scheduler stopped by user")
        except Exception as e:
            self.logger.error_logger.error("Scheduler error", exc_info=True)
            
        return True
        
    def run_single_upload(self, video_path, custom_metadata=None):
        """Upload a single video file"""
        self.logger.main_logger.info(f"Single upload mode: {video_path}")
        
        if not self.validate_setup():
            return False
            
        try:
            uploader = VideoUploader()
            result = uploader.upload_video(video_path, custom_metadata)
            
            if result and result['success']:
                self.logger.main_logger.info(f"Upload successful: {result['video_url']}")
                
                # Move to processed folder
                uploader.move_processed_file(video_path)
                return True
            else:
                self.logger.main_logger.error(f"Upload failed for {video_path}")
                return False
                
        except Exception as e:
            self.error_handler.handle_upload_error(e, video_path)
            return False
            
    def run_batch_upload(self, folder_path):
        """Upload all videos in a folder"""
        self.logger.main_logger.info(f"Batch upload mode: {folder_path}")
        
        if not self.validate_setup():
            return False
            
        folder = Path(folder_path)
        if not folder.exists():
            self.logger.main_logger.error(f"Folder does not exist: {folder_path}")
            return False
            
        # Find all video files
        video_extensions = self.config.get('file_processing', 'valid_extensions')
        video_files = []
        
        for ext in video_extensions:
            video_files.extend(folder.glob(f"*{ext}"))
            
        if not video_files:
            self.logger.main_logger.info(f"No video files found in {folder_path}")
            return True
            
        self.logger.main_logger.info(f"Found {len(video_files)} video files for batch upload")
        
        # Upload each file
        success_count = 0
        for video_file in video_files:
            if self.run_single_upload(video_file):
                success_count += 1
                
        self.logger.main_logger.info(f"Batch upload completed: {success_count}/{len(video_files)} successful")
        return success_count == len(video_files)
        
    def show_status(self):
        """Show system status and statistics"""
        print("\n=== YouTube Video Automation Status ===\n")
        
        # Configuration status
        valid_creds, missing = self.config.validate_credentials()
        print(f"Configuration Status: {'✅ Valid' if valid_creds else '❌ Invalid'}")
        if not valid_creds:
            print(f"Missing credentials: {', '.join(missing)}")
            
        # Directory status
        paths = self.config.get_paths()
        print("\nDirectories:")
        for name, path in paths.items():
            exists = path.exists()
            print(f"  {name}: {'✅' if exists else '❌'} {path}")
            
        # Check for pending videos
        input_folder = paths['input_folder']
        if input_folder.exists():
            video_extensions = self.config.get('file_processing', 'valid_extensions')
            pending_videos = []
            for ext in video_extensions:
                pending_videos.extend(input_folder.glob(f"*{ext}"))
            print(f"\nPending videos: {len(pending_videos)}")
            for video in pending_videos[:5]:  # Show first 5
                print(f"  📹 {video.name}")
            if len(pending_videos) > 5:
                print(f"  ... and {len(pending_videos) - 5} more")
                
        # Recent uploads
        try:
            import json
            records_file = Path('logs/upload_records.json')
            if records_file.exists():
                with open(records_file, 'r') as f:
                    records = json.load(f)
                print(f"\nRecent uploads: {len(records)} total")
                for record in records[-3:]:  # Show last 3
                    print(f"  ✅ {record.get('title', 'Unknown')} ({record.get('timestamp', 'Unknown time')})")
        except Exception:
            print("\nRecent uploads: Unable to load upload history")
            
        print("\n" + "=" * 40)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="YouTube Video Automation Pipeline for Sora AI"
    )
    
    parser.add_argument(
        'mode',
        choices=['monitor', 'schedule', 'upload', 'batch', 'status'],
        help='Operation mode'
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Video file path (for upload mode)'
    )
    
    parser.add_argument(
        '--folder',
        help='Folder path (for batch mode)'
    )
    
    parser.add_argument(
        '--interval', '-i',
        type=int,
        default=30,
        help='Check interval in minutes (for schedule mode)'
    )
    
    parser.add_argument(
        '--title',
        help='Custom video title'
    )
    
    parser.add_argument(
        '--description',
        help='Custom video description'
    )
    
    parser.add_argument(
        '--privacy',
        choices=['private', 'public', 'unlisted'],
        help='Video privacy setting'
    )
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = AutomationScheduler()
    scheduler.logger.log_system_start()
    
    try:
        if args.mode == 'monitor':
            success = scheduler.run_continuous_monitoring()
            
        elif args.mode == 'schedule':
            success = scheduler.run_scheduled_checks(args.interval)
            
        elif args.mode == 'upload':
            if not args.file:
                print("Error: --file required for upload mode")
                return 1
                
            custom_metadata = {}
            if args.title:
                custom_metadata['title'] = args.title
            if args.description:
                custom_metadata['description'] = args.description
            if args.privacy:
                custom_metadata['privacy'] = args.privacy
                
            success = scheduler.run_single_upload(args.file, custom_metadata)
            
        elif args.mode == 'batch':
            if not args.folder:
                print("Error: --folder required for batch mode")
                return 1
                
            success = scheduler.run_batch_upload(args.folder)
            
        elif args.mode == 'status':
            scheduler.show_status()
            success = True
            
        else:
            parser.print_help()
            return 1
            
    except Exception as e:
        scheduler.logger.error_logger.error("Main execution error", exc_info=True)
        success = False
        
    finally:
        scheduler.logger.log_system_stop()
        
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())