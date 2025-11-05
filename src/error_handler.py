import logging
import logging.handlers
import os
import sys
from pathlib import Path
from datetime import datetime
import traceback
import json


class AutomationLogger:
    """Enhanced logging system for the video automation pipeline"""
    
    def __init__(self, log_folder='logs'):
        self.log_folder = Path(log_folder)
        self.log_folder.mkdir(parents=True, exist_ok=True)
        
        # Setup different loggers for different components
        self.setup_main_logger()
        self.setup_upload_logger()
        self.setup_monitor_logger()
        self.setup_error_logger()
        
    def setup_main_logger(self):
        """Setup main application logger"""
        self.main_logger = logging.getLogger('automation.main')
        self.main_logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.main_logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_folder / 'automation.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        
        self.main_logger.addHandler(console_handler)
        self.main_logger.addHandler(file_handler)
        
    def setup_upload_logger(self):
        """Setup YouTube upload logger"""
        self.upload_logger = logging.getLogger('automation.upload')
        self.upload_logger.setLevel(logging.INFO)
        self.upload_logger.handlers = []
        
        # Upload-specific file handler
        upload_handler = logging.handlers.RotatingFileHandler(
            self.log_folder / 'uploads.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        upload_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        upload_handler.setFormatter(upload_formatter)
        self.upload_logger.addHandler(upload_handler)
        
    def setup_monitor_logger(self):
        """Setup file monitoring logger"""
        self.monitor_logger = logging.getLogger('automation.monitor')
        self.monitor_logger.setLevel(logging.INFO)
        self.monitor_logger.handlers = []
        
        # Monitor-specific file handler
        monitor_handler = logging.handlers.RotatingFileHandler(
            self.log_folder / 'monitor.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        monitor_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        monitor_handler.setFormatter(monitor_formatter)
        self.monitor_logger.addHandler(monitor_handler)
        
    def setup_error_logger(self):
        """Setup error logger for critical issues"""
        self.error_logger = logging.getLogger('automation.errors')
        self.error_logger.setLevel(logging.ERROR)
        self.error_logger.handlers = []
        
        # Error-specific file handler
        error_handler = logging.FileHandler(
            self.log_folder / 'errors.log'
        )
        error_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d\n'
            '%(message)s\n'
            '%(exc_info)s\n'
            '-' * 80 + '\n'
        )
        error_handler.setFormatter(error_formatter)
        self.error_logger.addHandler(error_handler)
        
    def log_upload_start(self, filename, file_size_mb):
        """Log upload start"""
        self.upload_logger.info(f"UPLOAD_START: {filename} ({file_size_mb:.2f}MB)")
        
    def log_upload_progress(self, filename, progress_percent):
        """Log upload progress"""
        self.upload_logger.info(f"UPLOAD_PROGRESS: {filename} - {progress_percent}%")
        
    def log_upload_success(self, filename, video_id, video_url):
        """Log successful upload"""
        self.upload_logger.info(f"UPLOAD_SUCCESS: {filename} -> {video_id} ({video_url})")
        
    def log_upload_failure(self, filename, error):
        """Log upload failure"""
        self.upload_logger.error(f"UPLOAD_FAILURE: {filename} - {str(error)}")
        self.error_logger.error(f"Upload failed for {filename}", exc_info=True)
        
    def log_file_detected(self, filename):
        """Log new file detection"""
        self.monitor_logger.info(f"FILE_DETECTED: {filename}")
        
    def log_file_processing(self, filename, action):
        """Log file processing actions"""
        self.monitor_logger.info(f"FILE_PROCESSING: {filename} - {action}")
        
    def log_authentication(self, success, details=""):
        """Log authentication attempts"""
        if success:
            self.main_logger.info(f"AUTHENTICATION_SUCCESS: {details}")
        else:
            self.main_logger.error(f"AUTHENTICATION_FAILURE: {details}")
            self.error_logger.error(f"Authentication failed: {details}")
            
    def log_configuration(self, config_loaded, missing_items=None):
        """Log configuration status"""
        if config_loaded:
            self.main_logger.info("CONFIGURATION_LOADED: All settings loaded successfully")
        else:
            missing = ', '.join(missing_items) if missing_items else 'Unknown items'
            self.main_logger.error(f"CONFIGURATION_ERROR: Missing {missing}")
            
    def log_system_start(self):
        """Log system startup"""
        self.main_logger.info("=" * 50)
        self.main_logger.info("VIDEO AUTOMATION SYSTEM STARTED")
        self.main_logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.main_logger.info("=" * 50)
        
    def log_system_stop(self):
        """Log system shutdown"""
        self.main_logger.info("=" * 50)
        self.main_logger.info("VIDEO AUTOMATION SYSTEM STOPPED")
        self.main_logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.main_logger.info("=" * 50)


class ErrorHandler:
    """Enhanced error handling and recovery system"""
    
    def __init__(self, logger):
        self.logger = logger
        self.error_counts = {}
        self.max_retries = 3
        
    def handle_upload_error(self, error, filename, attempt=1):
        """Handle upload errors with retry logic"""
        error_key = f"upload_{filename}"
        
        if error_key not in self.error_counts:
            self.error_counts[error_key] = 0
            
        self.error_counts[error_key] += 1
        
        self.logger.log_upload_failure(filename, error)
        
        if attempt < self.max_retries:
            self.logger.main_logger.warning(
                f"Upload attempt {attempt} failed for {filename}. Retrying..."
            )
            return True  # Should retry
        else:
            self.logger.main_logger.error(
                f"Upload failed permanently for {filename} after {self.max_retries} attempts"
            )
            return False  # Should not retry
            
    def handle_authentication_error(self, error):
        """Handle authentication errors"""
        self.logger.log_authentication(False, str(error))
        
        # Log detailed error for debugging
        self.logger.error_logger.error("Authentication error details", exc_info=True)
        
        # Suggest recovery actions
        recovery_suggestions = [
            "1. Check your .env file for correct GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET",
            "2. Verify that YouTube Data API v3 is enabled in Google Cloud Console",
            "3. Check that OAuth2 consent screen is properly configured",
            "4. Delete config/token.json to force re-authentication"
        ]
        
        for suggestion in recovery_suggestions:
            self.logger.main_logger.info(f"Recovery suggestion: {suggestion}")
            
    def handle_file_processing_error(self, error, filename):
        """Handle file processing errors"""
        self.logger.monitor_logger.error(f"FILE_PROCESSING_ERROR: {filename} - {str(error)}")
        self.logger.error_logger.error(f"File processing failed for {filename}", exc_info=True)
        
    def handle_api_quota_exceeded(self, error):
        """Handle YouTube API quota exceeded errors"""
        self.logger.main_logger.error("YouTube API quota exceeded")
        self.logger.error_logger.error("API quota exceeded", exc_info=True)
        
        # Log recovery information
        recovery_info = [
            "YouTube API quota has been exceeded.",
            "The system will pause uploads until quota resets (typically daily).",
            "Consider upgrading your Google Cloud project quota if this happens frequently."
        ]
        
        for info in recovery_info:
            self.logger.main_logger.warning(f"Quota info: {info}")
            
    def log_system_health(self):
        """Log overall system health status"""
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'error_counts': self.error_counts,
            'total_errors': sum(self.error_counts.values())
        }
        
        # Save health data to JSON file
        health_file = Path('logs/system_health.json')
        try:
            with open(health_file, 'w') as f:
                json.dump(health_data, f, indent=2)
        except Exception as e:
            self.logger.error_logger.error(f"Failed to save health data: {e}")


# Global logger instance
automation_logger = None
error_handler = None


def get_logger():
    """Get the global logger instance"""
    global automation_logger, error_handler
    
    if automation_logger is None:
        automation_logger = AutomationLogger()
        error_handler = ErrorHandler(automation_logger)
        
    return automation_logger, error_handler


def setup_exception_handler():
    """Setup global exception handler"""
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger, _ = get_logger()
        logger.error_logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
    sys.excepthook = handle_exception


if __name__ == "__main__":
    # Test logging system
    logger, error_handler = get_logger()
    
    logger.log_system_start()
    logger.log_authentication(True, "Test authentication")
    logger.log_file_detected("test_video.mp4")
    logger.log_upload_start("test_video.mp4", 150.5)
    logger.log_upload_progress("test_video.mp4", 50)
    logger.log_upload_success("test_video.mp4", "abc123", "https://youtube.com/watch?v=abc123")
    
    error_handler.log_system_health()
    logger.log_system_stop()
    
    print("✅ Logging system test completed!")