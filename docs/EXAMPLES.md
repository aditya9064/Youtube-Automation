# Example Usage Scripts

Here are some example scripts and commands for common use cases.

## Basic Usage Examples

### 1. First-time Setup
```bash
# Run the setup script
./setup.sh

# Configure your credentials
cp .env.example .env
nano .env  # Add your Google API credentials

# Test the configuration
python main.py status
```

### 2. Start Monitoring for Sora AI Videos
```bash
# Continuous monitoring (recommended for active use)
python main.py monitor

# Scheduled checks (good for occasional use)
python main.py schedule --interval 15  # Check every 15 minutes
```

### 3. Manual Video Uploads
```bash
# Upload a single video
python main.py upload --file "path/to/sora_video.mp4"

# Upload with custom metadata
python main.py upload \
  --file "sora_amazing_scene.mp4" \
  --title "Amazing AI Generated Scene" \
  --description "This incredible scene was generated using Sora AI" \
  --privacy public

# Batch upload all videos in a folder
python main.py batch --folder "/path/to/sora/videos"
```

## Advanced Examples

### 4. Sora AI Workflow Integration
```bash
# Example: Process Sora AI outputs automatically
#!/bin/bash

SORA_OUTPUT_DIR="/path/to/sora/output"
AUTOMATION_INPUT="/Users/adityamiriyala/Documents/video automation/videos/input"

# Copy new Sora videos to automation input folder
rsync -av --include="*.mp4" --exclude="*" "$SORA_OUTPUT_DIR/" "$AUTOMATION_INPUT/"

# The automation system will detect and upload them automatically
echo "Sora videos copied to automation pipeline"
```

### 5. Custom Metadata Based on Filename
```python
# Example custom metadata extraction (add to file_monitor.py)
def extract_metadata_from_filename(self, file_path):
    filename = file_path.stem
    metadata = {}
    
    # Parse Sora AI filename patterns
    # Example: "sora_prompt_description_timestamp.mp4"
    if filename.startswith('sora_'):
        parts = filename.split('_')
        if len(parts) >= 3:
            prompt_part = ' '.join(parts[1:-1])  # Everything except 'sora' and timestamp
            metadata['title'] = f"Sora AI: {prompt_part.replace('_', ' ').title()}"
            metadata['description'] = f"Generated with prompt: {prompt_part}"
    
    return metadata
```

### 6. Notification Integration
```python
# Example Discord webhook notification
import requests

def send_discord_notification(self, upload_result, file_path):
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not webhook_url:
        return
        
    message = {
        "embeds": [{
            "title": "🎥 New Video Uploaded!",
            "description": f"**{upload_result['title']}**",
            "fields": [
                {"name": "File", "value": file_path.name, "inline": True},
                {"name": "Video ID", "value": upload_result['video_id'], "inline": True}
            ],
            "url": upload_result['video_url'],
            "color": 0x00ff00
        }]
    }
    
    requests.post(webhook_url, json=message)
```

## Systemd Service (Linux)

### 7. Run as System Service
Create `/etc/systemd/system/youtube-automation.service`:
```ini
[Unit]
Description=YouTube Video Automation Pipeline
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/video automation
Environment=PATH=/path/to/video automation/.venv/bin
ExecStart=/path/to/video automation/.venv/bin/python main.py monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable youtube-automation
sudo systemctl start youtube-automation
```

## Cron Job Examples

### 8. Scheduled Automation
```bash
# Add to crontab (crontab -e)

# Check for new videos every 30 minutes
*/30 * * * * cd "/Users/adityamiriyala/Documents/video automation" && .venv/bin/python main.py schedule --interval 1

# Daily cleanup of processed videos older than 30 days
0 2 * * * find "/Users/adityamiriyala/Documents/video automation/videos/processed" -name "*.mp4" -mtime +30 -delete

# Weekly status report
0 9 * * 1 cd "/Users/adityamiriyala/Documents/video automation" && .venv/bin/python main.py status > /tmp/youtube_status.txt && mail -s "YouTube Automation Status" your_email@example.com < /tmp/youtube_status.txt
```

## Monitoring and Maintenance

### 9. Health Check Script
```bash
#!/bin/bash
# health_check.sh - Monitor the automation system

AUTOMATION_DIR="/Users/adityamiriyala/Documents/video automation"
cd "$AUTOMATION_DIR"

# Check if the system is running properly
if python main.py status | grep -q "Configuration Status: ✅ Valid"; then
    echo "✅ System healthy"
else
    echo "❌ System issue detected"
    # Restart or send alert
fi

# Check for stuck uploads (files older than 1 hour in input folder)
find videos/input -name "*.mp4" -mmin +60 -exec echo "⚠️ Stuck file: {}" \;

# Check log file size and rotate if needed
if [ $(du -m logs/automation.log | cut -f1) -gt 100 ]; then
    echo "🔄 Rotating large log file"
    mv logs/automation.log logs/automation.log.old
fi
```

### 10. Backup Script
```bash
#!/bin/bash
# backup.sh - Backup important configuration and logs

AUTOMATION_DIR="/Users/adityamiriyala/Documents/video automation"
BACKUP_DIR="/path/to/backups/youtube-automation-$(date +%Y%m%d)"

mkdir -p "$BACKUP_DIR"

# Backup configuration (excluding sensitive files)
cp "$AUTOMATION_DIR/.env.example" "$BACKUP_DIR/"
cp "$AUTOMATION_DIR/config/config.json" "$BACKUP_DIR/"
cp "$AUTOMATION_DIR/logs/upload_records.json" "$BACKUP_DIR/"

# Backup recent logs
cp "$AUTOMATION_DIR/logs"/*.log "$BACKUP_DIR/" 2>/dev/null || true

echo "✅ Backup completed: $BACKUP_DIR"
```

## Development and Testing

### 11. Test Environment Setup
```bash
# Create a test environment
cp -r "/Users/adityamiriyala/Documents/video automation" "/tmp/youtube-automation-test"
cd "/tmp/youtube-automation-test"

# Use test configuration
echo "GOOGLE_CLIENT_ID=test_client_id" > .env
echo "GOOGLE_CLIENT_SECRET=test_secret" >> .env

# Run tests
python -m pytest tests/ -v
```

### 12. Debug Mode
```bash
# Run with verbose logging
export PYTHONPATH="$PWD/src"
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from main import AutomationScheduler
scheduler = AutomationScheduler()
scheduler.run_single_upload('test_video.mp4')
"
```

## Performance Optimization

### 13. Large File Handling
```python
# For handling large Sora AI videos efficiently
# Add to config/settings.py

# Chunk size for resumable uploads (use -1 for automatic)
UPLOAD_CHUNK_SIZE = 1024 * 1024 * 8  # 8MB chunks

# Parallel processing for multiple files
MAX_CONCURRENT_UPLOADS = 2

# Compression before upload (optional)
COMPRESS_BEFORE_UPLOAD = False
COMPRESSION_QUALITY = "medium"  # low, medium, high
```

### 14. Resource Monitoring
```bash
# Monitor system resources during uploads
#!/bin/bash
while true; do
    echo "$(date): CPU: $(top -l 1 | awk '/CPU usage/ {print $3}') Memory: $(vm_stat | awk '/free/ {print $3}' | sed 's/\.//')"
    sleep 30
done > system_monitor.log &
```

These examples should help you integrate the YouTube automation pipeline with your Sora AI workflow effectively!