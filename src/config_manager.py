import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ConfigManager:
    """Manage configuration settings for the video automation pipeline"""
    
    def __init__(self, config_path='config/config.json'):
        self.config_path = Path(config_path)
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            else:
                return self.get_default_config()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.get_default_config()
            
    def get_default_config(self):
        """Return default configuration"""
        return {
            "channel_settings": {
                "default_privacy": "private",
                "default_category": "22",
                "default_language": "en",
                "notify_subscribers": False
            },
            "video_metadata_template": {
                "title_prefix": "Sora AI Generated: ",
                "description_template": "This video was generated using Sora AI and automatically uploaded.\n\n📅 Generated: {timestamp}\n🤖 AI Model: Sora AI by OpenAI\n⚡ Automated Upload: YouTube Upload Automation Pipeline\n\n{custom_description}\n\n#SoraAI #AIGenerated #AutomatedUpload #AIVideo",
                "default_tags": [
                    "Sora AI",
                    "AI Generated", 
                    "Automated Upload",
                    "OpenAI",
                    "Artificial Intelligence",
                    "AI Video"
                ]
            },
            "upload_settings": {
                "retry_attempts": 3,
                "retry_delay_seconds": 60,
                "chunk_size": -1,
                "resumable_upload": True
            },
            "notification_settings": {
                "enabled": False,
                "webhook_url": "",
                "discord_webhook": "",
                "slack_webhook": "",
                "email_notifications": False
            },
            "file_processing": {
                "valid_extensions": [".mp4", ".mov", ".avi", ".mkv", ".webm"],
                "max_file_size_mb": 2048,
                "file_stability_checks": 3,
                "stability_check_interval": 5
            }
        }
        
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
            
    def get(self, section, key=None, default=None):
        """Get configuration value"""
        if key is None:
            return self.config.get(section, default)
        else:
            return self.config.get(section, {}).get(key, default)
            
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        
    def update_channel_settings(self, **kwargs):
        """Update channel settings"""
        for key, value in kwargs.items():
            self.set('channel_settings', key, value)
            
    def update_video_template(self, **kwargs):
        """Update video metadata template"""
        for key, value in kwargs.items():
            self.set('video_metadata_template', key, value)
            
    def get_api_credentials(self):
        """Get API credentials from environment variables"""
        return {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'youtube_channel_id': os.getenv('YOUTUBE_CHANNEL_ID')
        }
        
    def validate_credentials(self):
        """Validate that required credentials are set"""
        creds = self.get_api_credentials()
        
        missing = []
        if not creds['client_id']:
            missing.append('GOOGLE_CLIENT_ID')
        if not creds['client_secret']:
            missing.append('GOOGLE_CLIENT_SECRET')
            
        return len(missing) == 0, missing
        
    def get_paths(self):
        """Get important file paths"""
        return {
            'input_folder': Path('videos/input'),
            'processed_folder': Path('videos/processed'),
            'logs_folder': Path('logs'),
            'config_folder': Path('config')
        }
        
    def ensure_directories(self):
        """Ensure all necessary directories exist"""
        paths = self.get_paths()
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
            
    def get_notification_config(self):
        """Get notification configuration"""
        return self.get('notification_settings', default={})
        
    def is_notifications_enabled(self):
        """Check if notifications are enabled"""
        return self.get('notification_settings', 'enabled', False)


if __name__ == "__main__":
    # Test configuration management
    config = ConfigManager()
    
    print("=== Configuration Test ===")
    print(f"Default privacy: {config.get('channel_settings', 'default_privacy')}")
    print(f"Upload retry attempts: {config.get('upload_settings', 'retry_attempts')}")
    
    # Test credential validation
    valid, missing = config.validate_credentials()
    if valid:
        print("✅ API credentials are configured")
    else:
        print(f"❌ Missing credentials: {', '.join(missing)}")
        
    # Ensure directories exist
    config.ensure_directories()
    print("✅ Directories created/verified")
    
    print("Configuration management test completed!")