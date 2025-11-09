#!/usr/bin/env python3
"""
Minimal test to reproduce the video generation issue
"""

import asyncio
import os
import sys
sys.path.append('/Users/adityamiriyala/Documents/video automation/webapp/backend')

# Import the exact function from our server
from simple_server import generate_sora_video

async def test_video_generation():
    """Test the exact generate_sora_video function"""
    
    try:
        print("🎬 Testing generate_sora_video function...")
        
        filename = await generate_sora_video(
            prompt="A simple test video: sunset over water",
            duration="4s", 
            style="realistic",
            orientation="landscape"
        )
        
        print(f"✅ Success! Generated: {filename}")
        
        # Check if file exists and its size
        video_path = f"/Users/adityamiriyala/Documents/video automation/videos/processed/{filename}"
        if os.path.exists(video_path):
            size = os.path.getsize(video_path)
            print(f"📁 File size: {size} bytes")
            if size > 100000:  # > 100KB means likely real content
                print("🎉 This appears to be a real video (large file size)")
            else:
                print("⚠️  Small file size suggests placeholder content")
        else:
            print("❌ Generated file not found")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_video_generation())