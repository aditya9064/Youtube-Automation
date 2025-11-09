"""
Simple FastAPI server for YouTube Automation Web App
Testing without complex dependencies
"""

import os
import sys
import json
import traceback
import asyncio
import io
import numpy as np
import imageio
from pathlib import Path
from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from datetime import datetime
from typing import Optional, Dict, Any, List
from PIL import Image

# Initialize directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
PROCESSED_DIR = os.path.join(VIDEOS_DIR, "processed")

# Create necessary directories without printing
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load environment variables silently
load_dotenv()

# Add parent directory for automation imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import YouTube uploader
try:
    from youtube_uploader import youtube_uploader
    YOUTUBE_AVAILABLE = True
    print("✅ YouTube integration loaded successfully")
except ImportError as e:
    print(f"⚠️ YouTube integration not available: {e}")
    YOUTUBE_AVAILABLE = False

# Custom exceptions
class AIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

# Network-related exceptions
class NetworkError(AIError):
    def __init__(self, message: str = "Network error occurred. Please try again."):
        super().__init__(message, status_code=503)

class TimeoutError(AIError):
    def __init__(self, message: str = "Request timed out. Please try again."):
        super().__init__(message, status_code=504)

# Configure OpenAI API with validation
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not found in environment variables.")
    print("Sora AI integration will be disabled. Video generation will use placeholder videos.")
    print("To enable Sora AI:")
    print("1. Get API access to Sora (when available)")
    print("2. Add your API key to the .env file: OPENAI_API_KEY=your_key_here")
    OPENAI_API_KEY = None

# Configuration flags
USE_SORA_AI = OPENAI_API_KEY is not None and os.getenv('USE_SORA_AI', 'true').lower() == 'true'

# Configure API client with robust error handling
transport = httpx.AsyncHTTPTransport(
    retries=3,  # Retry failed requests up to 3 times
    verify=True  # Verify SSL certificates
)

ai_client = httpx.AsyncClient(
    base_url="https://api.openai.com",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    },
    transport=transport,
    timeout=120.0,  # 120 second timeout for video generation
    verify=True,  # Verify SSL certificates
    follow_redirects=True  # Follow redirects automatically
)

async def generate_sora_video(prompt: str, duration: str, style: str, orientation: str) -> str:
    """
    Generate a video using Sora 2 Pro AI with the given parameters
    Returns the filename of the generated video
    """
    try:
        print(f"\n=== Attempting Sora 2 Pro Video Generation ===")
        print(f"Prompt: {prompt}")
        print(f"Duration: {duration}, Style: {style}, Orientation: {orientation}")
        print(f"Sora AI Enabled: {USE_SORA_AI}")
        
        # Check if Sora AI is available
        if not USE_SORA_AI:
            raise AIError("Sora AI is not configured or not available. Please check your API key and configuration.", status_code=503)
        
        # Convert duration to seconds
        duration_seconds = int(duration.replace("s", ""))
        
        # Prepare Sora 2 Pro API request with correct parameters
        # Supported sizes: '720x1280', '1280x720', '1024x1792', '1792x1024'
        if orientation == "portrait":
            size = "720x1280"  # Portrait format
        else:
            size = "1280x720"  # Landscape format
            
        sora_data = {
            "model": "sora-2-pro", 
            "prompt": prompt,
            "size": size
        }
        
        print(f"🎬 Sora 2 Pro Request: {sora_data}")
        
        # Use the correct Sora endpoint with a fresh client
        sora_endpoint = "/v1/videos"
        
        # Create a fresh client to ensure we have the latest API key
        fresh_client = httpx.AsyncClient(
            base_url="https://api.openai.com",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
                "Content-Type": "application/json"
            },
            timeout=180.0,
            verify=True
        )
        
        try:
            print(f"🔍 Using Sora endpoint: {sora_endpoint}")
            print(f"🔑 API Key (last 10 chars): ...{os.getenv('OPENAI_API_KEY', '')[-10:]}")
            
            response = await fresh_client.post(
                sora_endpoint,
                json=sora_data,
                timeout=180.0  # 3 minutes for video generation
            )
            
            print(f"📡 Sora API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Sora 2 Pro API successful!")
                result = response.json()
                print(f"📋 Sora Response: {result}")
                
                # Sora API returns a job object, we need to poll for completion
                video_id = result.get("id")
                status = result.get("status")
                
                if video_id and status:
                    print(f"🎬 Sora video job created: {video_id}, status: {status}")
                    
                    # Poll for completion (Sora videos take time to generate)
                    max_attempts = 60  # 5 minutes max wait
                    attempt = 0
                    
                    while attempt < max_attempts:
                        print(f"🔄 Polling attempt {attempt + 1}/{max_attempts} for video {video_id}")
                        
                        # Check video status
                        status_response = await fresh_client.get(f"/v1/videos/{video_id}")
                        
                        if status_response.status_code == 200:
                            status_result = status_response.json()
                            current_status = status_result.get("status")
                            progress = status_result.get("progress", 0)
                            
                            print(f"📊 Video {video_id} status: {current_status}, progress: {progress}%")
                            
                            if current_status == "completed":
                                # Video is ready! The Sora API doesn't provide direct URLs in the status response
                                # Instead, we need to get the video content from the video ID endpoint
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                filename = f"sora2pro_{video_id}_{timestamp}.mp4"
                                filepath = os.path.join(PROCESSED_DIR, filename)
                                
                                print(f"📥 Downloading Sora video content for ID: {video_id}")
                                
                                # Get video content directly from the video endpoint
                                # According to Sora API docs, completed videos can be accessed via the video ID
                                try:
                                    # Try to get the video file content directly
                                    video_content_response = await fresh_client.get(f"/v1/videos/{video_id}")
                                    
                                    if video_content_response.status_code == 200:
                                        content_type = video_content_response.headers.get('content-type', '')
                                        
                                        if 'video' in content_type.lower() or 'octet-stream' in content_type.lower():
                                            # This is the actual video content
                                            with open(filepath, 'wb') as f:
                                                f.write(video_content_response.content)
                                            
                                            file_size = len(video_content_response.content)
                                            print(f"🎉 Sora 2 Pro video downloaded: {filename} ({file_size} bytes)")
                                            
                                            if file_size > 10000:  # Sanity check - real videos should be > 10KB
                                                return filename
                                            else:
                                                print("⚠️ Downloaded file seems too small, may be corrupted")
                                                
                                        else:
                                            # Still getting JSON, try to find download link
                                            response_data = video_content_response.json()
                                            
                                            # Look for any URL-like fields
                                            download_url = None
                                            for field in ['download_url', 'file_url', 'url', 'video_url', 'content_url', 'asset_url']:
                                                if field in response_data:
                                                    download_url = response_data[field]
                                                    break
                                            
                                            if download_url:
                                                print(f"📥 Found download URL: {download_url}")
                                                # Download from the provided URL
                                                async with httpx.AsyncClient(timeout=120.0) as download_client:
                                                    video_response = await download_client.get(download_url)
                                                    
                                                    if video_response.status_code == 200:
                                                        with open(filepath, 'wb') as f:
                                                            f.write(video_response.content)
                                                        
                                                        file_size = len(video_response.content)
                                                        print(f"🎉 Sora 2 Pro video downloaded: {filename} ({file_size} bytes)")
                                                        return filename
                                                    else:
                                                        print(f"❌ Failed to download from URL: HTTP {video_response.status_code}")
                                            else:
                                                print(f"❌ No download URL found. Available fields: {list(response_data.keys())}")
                                    
                                    # If direct download doesn't work, try alternative approach
                                    print("🔄 Trying alternative download method...")
                                    
                                    # Some APIs provide content via different endpoints
                                    for alt_endpoint in [f"/v1/videos/{video_id}/download", f"/v1/videos/{video_id}/content"]:
                                        try:
                                            alt_response = await fresh_client.get(alt_endpoint)
                                            if alt_response.status_code == 200:
                                                content_type = alt_response.headers.get('content-type', '')
                                                if 'video' in content_type.lower():
                                                    with open(filepath, 'wb') as f:
                                                        f.write(alt_response.content)
                                                    
                                                    file_size = len(alt_response.content)
                                                    print(f"🎉 Sora video downloaded via {alt_endpoint}: {filename} ({file_size} bytes)")
                                                    return filename
                                        except:
                                            continue
                                    
                                    # If all download methods fail, create a placeholder but log this as an issue
                                    print(f"⚠️ Could not download Sora video content. Video completed but download failed.")
                                    print(f"📋 Completed video info: {status_result}")
                                    raise AIError("Sora video completed but could not be downloaded")
                                    
                                except Exception as download_error:
                                    print(f"❌ Error downloading Sora video: {download_error}")
                                    raise AIError(f"Failed to download completed Sora video: {str(download_error)}")
                            
                            elif current_status == "failed" or current_status == "error":
                                error_msg = status_result.get("error", "Unknown error")
                                print(f"❌ Sora video generation failed: {error_msg}")
                                raise AIError(f"Sora video generation failed: {error_msg}")
                            
                            elif current_status in ["queued", "processing", "generating"]:
                                # Still processing, wait and retry
                                await asyncio.sleep(5)  # Wait 5 seconds between polls
                                attempt += 1
                                continue
                            else:
                                print(f"⚠️ Unknown status: {current_status}")
                                await asyncio.sleep(5)
                                attempt += 1
                                continue
                        else:
                            print(f"❌ Status check failed: HTTP {status_response.status_code}")
                            await asyncio.sleep(5)
                            attempt += 1
                            continue
                    
                    # If we get here, we timed out
                    print(f"⏰ Sora video generation timed out after {max_attempts} attempts")
                    raise TimeoutError(f"Sora video generation timed out for job {video_id}")
                else:
                    print(f"❌ Invalid Sora response format: {result}")
                    raise AIError("Sora API returned invalid response format")
                
            elif response.status_code == 400:
                error_text = response.text
                print(f"❌ Sora API Bad Request: {error_text}")
                raise AIError(f"Sora API request error: {error_text}", status_code=400)
            elif response.status_code == 401:
                print(f"❌ Sora API Authentication Error")
                raise AIError("Sora API authentication failed. Please check your API key.", status_code=401)
            elif response.status_code == 403:
                print(f"❌ Sora API Access Forbidden")
                raise AIError("Sora API access denied. Your account may not have Sora access.", status_code=403)
            elif response.status_code == 429:
                print(f"❌ Sora API Rate Limited")
                raise AIError("Sora API rate limit exceeded. Please try again later.", status_code=429)
            else:
                error_text = response.text
                print(f"⚠️ Sora API returned: {response.status_code} - {error_text}")
                raise AIError(f"Sora API error: {response.status_code} - {error_text}", status_code=response.status_code)
                
        except httpx.TimeoutException:
            print(f"❌ Sora API request timed out")
            raise TimeoutError("Sora API request timed out")
        except httpx.NetworkError as e:
            print(f"❌ Network error: {str(e)}")
            raise NetworkError(f"Network error connecting to Sora API: {str(e)}")
        except AIError:
            # Re-raise AIError exceptions
            raise
        except Exception as e:
            print(f"❌ Unexpected error with Sora API: {str(e)}")
            raise AIError(f"Unexpected Sora API error: {str(e)}")
        finally:
            # Always close the fresh client
            await fresh_client.aclose()
        
        # If all Sora endpoints fail, fall back to DALL-E + video conversion
        print("⚠️ All Sora endpoints failed, falling back to DALL-E image conversion")
        
        # Generate image with DALL-E as fallback
        dalle_data = {
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "standard",
            "response_format": "url"
        }
        
        response = await ai_client.post("/v1/images/generations", json=dalle_data)
        
        if response.status_code != 200:
            raise AIError(f"DALL-E API failed: {response.status_code}", status_code=response.status_code)
        
        result = response.json()
        image_url = result["data"][0]["url"]
        
        # Convert single image to simple video
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dalle_video_{timestamp}.mp4"
        filepath = os.path.join(PROCESSED_DIR, filename)
        
        # Download and convert image to video
        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            img = Image.open(io.BytesIO(img_response.content))
            
            # Create simple video from single image
            frames = []
            for _ in range(duration_seconds * 5):  # 5 fps for simplicity
                frames.append(np.array(img))
            
            imageio.mimsave(filepath, frames, fps=5, format='mp4')
        
        print(f"📹 DALL-E fallback video created: {filename}")
        return filename
        
    except Exception as e:
        print(f"❌ Error in video generation: {str(e)}")
        raise AIError(f"Video generation failed: {str(e)}", status_code=500)


# Helper function for error handling
class AIErrorHTTP(HTTPException):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=message)


# Process video generation
async def process_video_generation(video: Dict[str, Any]):
    """Async task to handle video generation process for multiple versions"""
    try:
        print("\n=== Starting Video Generation Processing ===")
        print(f"Starting job {video.get('job_id')} for video {video.get('id')}")
        
        # Get and validate paths
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            videos_dir = os.path.join(project_root, "videos")
            processed_dir = os.path.join(videos_dir, "processed")
            
            print(f"Directory structure:")
            print(f"- Current: {current_dir}")
            print(f"- Project root: {project_root}")
            print(f"- Videos: {videos_dir}")
            print(f"- Processed: {processed_dir}")
            
            # Ensure directories exist
            for dir_path in [videos_dir, processed_dir]:
                try:
                    os.makedirs(dir_path, exist_ok=True)
                    print(f"Verified directory: {dir_path}")
                except Exception as dir_error:
                    error_msg = f"Failed to create directory {dir_path}: {str(dir_error)}"
                    print(f"Directory error: {error_msg}")
                    raise RuntimeError(error_msg)
                
        except Exception as path_error:
            error_msg = f"Path setup error: {str(path_error)}"
            print(f"Path error: {error_msg}")
            raise RuntimeError(error_msg)

        # Setup video metadata and tracking
        try:
            # Initialize version tracking
            video["version_statuses"] = {i: "pending" for i in range(3)}
            video["processed_dir"] = processed_dir
            video["versions"] = []
            print(f"Initialized version tracking")
            
            stages = [
                ("initializing", 2),
                ("processing", 3),
                ("rendering", 2),
                ("finalizing", 1)
            ]
            
        except Exception as setup_error:
            error_msg = f"Video setup error: {str(setup_error)}"
            print(f"Setup error: {error_msg}")
            raise RuntimeError(error_msg)

        # Process each version
        async def process_version(version: int):
            """Process a single version of the video"""
            try:
                print(f"\n--- Processing Version {version + 1} ---")
                version_data = {
                    "id": f"v{version + 1}_{datetime.now().timestamp()}",
                    "version": version + 1,
                    "status": "processing",
                    "created_at": datetime.now().isoformat()
                }
                
                # Simulate processing stages
                for stage, duration in stages:
                    print(f"Version {version + 1}: {stage}")
                    video["version_statuses"][version] = stage
                    await asyncio.sleep(duration)
                
                # Generate output video using Sora AI
                try:
                    print(f"Generating video with Sora AI for version {version + 1}")
                    
                    # Try to generate video with AI (DALL-E + video conversion or Sora)
                    try:
                        print(f"Starting AI video generation for: {video.get('prompt', 'A beautiful landscape scene')}")
                        filename = await generate_sora_video(
                            prompt=video.get("prompt", "A beautiful landscape scene"),
                            duration=video.get("duration", "10s"),
                            style=video.get("style", "realistic"),
                            orientation=video.get("orientation", "landscape")
                        )
                        filepath = os.path.join(processed_dir, filename)
                        print(f"✅ AI generated video successfully: {filename}")
                        
                        # Update version data with AI result
                        generation_method = "dalle_video" if "dalle" in filename else "sora_ai"
                        version_data.update({
                            "status": "completed",
                            "url": f"/api/v1/videos/view/{filename}",
                            "filename": filename,
                            "completed_at": datetime.now().isoformat(),
                            "generated_with": generation_method
                        })
                        
                    except (AIError, NetworkError, TimeoutError) as ai_error:
                        # If Sora fails, fall back to placeholder video
                        print(f"Sora AI failed (falling back to placeholder): {str(ai_error)}")
                        
                        # Generate filename for fallback
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"fallback_video_{video['id']}_{timestamp}_v{version+1}.mp4"
                        filepath = os.path.join(processed_dir, filename)
                        
                        # Create fallback placeholder video
                        try:
                            import numpy as np
                            import imageio
                            
                            duration = int(video.get("duration", "10s").replace("s", ""))
                            fps = 30
                            total_frames = duration * fps
                            
                            frames = []
                            for i in range(total_frames):
                                # Create a more interesting placeholder with text overlay
                                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                                frame.fill(50)  # Dark gray background
                                
                                # Add some visual elements to indicate it's a placeholder
                                if i % 30 < 15:  # Blinking effect
                                    frame[200:280, 220:420] = [100, 100, 150]  # Blue rectangle
                                    
                                frames.append(frame)
                            
                            imageio.mimsave(filepath, frames, fps=fps, format='mp4')
                            print(f"Created fallback video: {filepath}")
                            
                            # Update version data with fallback info
                            version_data.update({
                                "status": "completed",
                                "url": f"/api/v1/videos/view/{filename}",
                                "filename": filename,
                                "completed_at": datetime.now().isoformat(),
                                "generated_with": "fallback_placeholder",
                                "sora_error": str(ai_error)
                            })
                            
                        except ImportError as imp_error:
                            error_msg = f"Missing required package for fallback: {str(imp_error)}"
                            print(f"Import error: {error_msg}")
                            raise RuntimeError(error_msg)
                        except Exception as fallback_error:
                            error_msg = f"Error creating fallback video: {str(fallback_error)}"
                            print(f"Fallback error: {error_msg}")
                            raise RuntimeError(error_msg)
                    
                except Exception as gen_error:
                    error_msg = f"Video generation error: {str(gen_error)}"
                    print(f"Generation error: {error_msg}")
                    version_data["status"] = "error"
                    version_data["error"] = error_msg
                    raise
                
                return version_data
                
            except Exception as version_error:
                print(f"Version {version + 1} failed: {str(version_error)}")
                return {
                    "id": f"error_{version}_{datetime.now().timestamp()}",
                    "version": version + 1,
                    "status": "error",
                    "error": str(version_error),
                    "created_at": datetime.now().isoformat()
                }

        # Process all versions
        try:
            version_tasks = [process_version(i) for i in range(3)]
            completed_versions = await asyncio.gather(*version_tasks, return_exceptions=True)
            
            # Process results
            successful_versions = []
            failed_versions = []
            
            for v in completed_versions:
                if isinstance(v, dict):
                    if v["status"] == "completed":
                        successful_versions.append(v)
                    else:
                        failed_versions.append(v)
                else:
                    failed_versions.append({
                        "status": "error",
                        "error": str(v),
                        "created_at": datetime.now().isoformat()
                    })
            
            # Update video status
            video["versions"] = successful_versions + failed_versions
            
            if successful_versions:
                video["status"] = "completed"
                video["filename"] = successful_versions[0]["filename"]
                video["completed_at"] = datetime.now().isoformat()
                print(f"Video processing completed with {len(successful_versions)} successful versions")
            else:
                video["status"] = "failed"
                video["error"] = "No versions were successfully generated"
                print(f"Video processing failed: no successful versions")
            
            # Add metadata
            video["metadata"] = {
                "selected_version": None,
                "generated_title": None,
                "generated_description": None,
                "generated_thumbnail": None,
                "youtube_status": "pending"
            }
            
        except Exception as gather_error:
            error_msg = f"Error processing versions: {str(gather_error)}"
            print(f"Processing error: {error_msg}")
            video["status"] = "failed"
            video["error"] = error_msg
            raise
        
    except Exception as e:
        error_msg = f"Fatal error in video processing: {str(e)}"
        print(f"Fatal error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        video["status"] = "failed"
        video["error"] = error_msg

app = FastAPI(
    title="YouTube Automation Pipeline",
    description="AI-powered video generation and YouTube upload automation",
    version="1.0.0"
)

# WebSocket Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001", "http://localhost:3005", "http://127.0.0.1:3005"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling
@app.exception_handler(AIErrorHTTP)
async def ai_exception_handler(request, exc: AIErrorHTTP):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail}
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Keep connection alive with heartbeat
            await websocket.send_json({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# In-memory storage for demo
pipeline_status = {
    "status": "idle",
    "queue_size": 0,
    "active_jobs": 0,
    "videos_processed": 147,
    "videos_uploaded": 134,
    "success_rate": 91.2,
    "uptime": 0,
    "last_activity": datetime.now().isoformat(),
    "avg_processing_time": 180  # Average processing time in seconds
}

videos_data = [
    {
        "id": 1,
        "title": "AI Generated Sunset Scene",
        "filename": "sunset_scene_001.mp4",
        "status": "uploaded",
        "youtube_url": "https://youtube.com/watch?v=abc123",
        "views": 1247,
        "created_at": "2024-11-04T15:30:00Z"
    },
    {
        "id": 2,
        "title": "Futuristic City Landscape", 
        "filename": "city_landscape_002.mp4",
        "status": "uploading",
        "progress": 67,
        "created_at": "2024-11-04T16:45:00Z"
    },
    {
        "id": 3,
        "title": "Ocean Waves Animation",
        "filename": "ocean_waves_003.mp4", 
        "status": "pending",
        "created_at": "2024-11-04T17:12:00Z"
    }
]

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "YouTube Automation Pipeline API",
        "version": "1.0.0",
        "status": "running",
        "docs_url": "/docs",
        "dashboard_url": "http://localhost:3000"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "ai_services": {
            "sora_configured": USE_SORA_AI,
            "openai_api_available": OPENAI_API_KEY is not None
        }
    }

@app.post("/api/v1/ai/test-sora")
async def test_sora_connection():
    """Test Sora AI connection and API access"""
    if not USE_SORA_AI:
        return {
            "success": False,
            "message": "Sora AI is not configured. Please add your OpenAI API key to enable Sora integration.",
            "status": "not_configured"
        }
    
    try:
        # Test a simple API call to check access
        test_response = await ai_client.get("/v1/models")
        
        if test_response.status_code == 200:
            models = test_response.json()
            sora_models = [m for m in models.get('data', []) if 'sora' in m.get('id', '').lower()]
            
            return {
                "success": True,
                "message": "OpenAI API connection successful",
                "sora_models_found": len(sora_models),
                "models": sora_models,
                "status": "connected"
            }
        else:
            return {
                "success": False,
                "message": f"OpenAI API error: {test_response.status_code}",
                "status": "connection_error"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "status": "error"
        }

# Pipeline endpoints
@app.get("/api/v1/pipeline/status")
async def get_pipeline_status():
    """Get current pipeline status"""
    return pipeline_status

@app.post("/api/v1/pipeline/start")
async def start_pipeline():
    """Start the pipeline"""
    global pipeline_status
    pipeline_status["status"] = "running"
    pipeline_status["last_activity"] = datetime.now().isoformat()
    
    return {
        "status": "success",
        "message": "Pipeline started successfully"
    }

@app.post("/api/v1/pipeline/stop")
async def stop_pipeline():
    """Stop the pipeline"""
    global pipeline_status
    pipeline_status["status"] = "idle"
    pipeline_status["last_activity"] = datetime.now().isoformat()
    
    return {
        "status": "success", 
        "message": "Pipeline stopped successfully"
    }

@app.get("/api/v1/pipeline/stats")
async def get_pipeline_stats():
    """Get pipeline statistics"""
    return {
        "total_videos": len(videos_data),
        "uploaded_videos": len([v for v in videos_data if v["status"] == "uploaded"]),
        "failed_videos": 0,
        "success_rate": 91.2,
        "pipeline_stats": pipeline_status
    }

# Video generation endpoints
from pydantic import BaseModel, validator
from enum import Enum
from typing import Optional

class VideoOrientation(str, Enum):
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"

class VideoDuration(str, Enum):
    SECONDS_4 = "4s"
    SECONDS_10 = "10s"
    SECONDS_15 = "15s"

class VideoStyle(str, Enum):
    REALISTIC = "realistic"
    ANIMATED = "animated"
    CINEMATIC = "cinematic"
    DOCUMENTARY = "documentary"
    ARTISTIC = "artistic"
    VINTAGE = "vintage"

class CameraView(str, Enum):
    WIDE = "wide"
    CLOSE_UP = "close-up"
    AERIAL = "aerial"
    POV = "pov"
    TRACKING = "tracking"
    STATIC = "static"

class BackgroundType(str, Enum):
    NATURAL = "natural"
    URBAN = "urban"
    STUDIO = "studio"
    ABSTRACT = "abstract"
    MINIMAL = "minimal"

class GenerationRequest(BaseModel):
    base_prompt: str
    orientation: VideoOrientation
    duration: VideoDuration
    style: VideoStyle
    camera_view: CameraView
    background: BackgroundType
    lighting: Optional[str] = "natural"
    color_palette: Optional[str] = None
    weather: Optional[str] = None
    time_of_day: Optional[str] = None
    additional_details: Optional[str] = None

class VersionSelectionRequest(BaseModel):
    video_id: int
    version: int  # 0, 1, or 2

class YouTubeUploadRequest(BaseModel):
    video_id: int
    upload: bool  # Whether to proceed with upload

class DirectUploadRequest(BaseModel):
    video_id: int
    version_index: int  # 0, 1, or 2
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list] = None

def generate_detailed_prompt(request: GenerationRequest) -> str:
    """Generate a detailed prompt for Sora based on user preferences"""
    try:
        print("\n=== Generating Detailed Prompt ===")
        print(f"Base prompt: {request.base_prompt}")
        print(f"Duration: {request.duration}")
        print(f"Style: {request.style}")
        print(f"Orientation: {request.orientation}")
        print(f"Camera view: {request.camera_view}")
        print(f"Background: {request.background}")
        
        # Base components
        components = [
            f"Create a {request.duration.value} {request.style.value} video in {request.orientation.value} format",
            f"showing {request.base_prompt}",
            f"using a {request.camera_view.value} camera perspective",
            f"with a {request.background.value} background"
        ]
        
        # Optional components
        if request.lighting:
            components.append(f"with {request.lighting} lighting")
        if request.color_palette:
            components.append(f"using a {request.color_palette} color palette")
        if request.weather:
            components.append(f"during {request.weather} weather")
        if request.time_of_day:
            components.append(f"during {request.time_of_day}")
            
        # Style-specific enhancements
        style_enhancements = {
            VideoStyle.CINEMATIC: "with dramatic camera movements, depth of field, and film-like quality",
            VideoStyle.REALISTIC: "with photorealistic details and natural motion",
            VideoStyle.ANIMATED: "with smooth animation and stylized visuals",
            VideoStyle.DOCUMENTARY: "with authentic, unfiltered capturing of the scene",
            VideoStyle.ARTISTIC: "with creative and expressive visual elements",
            VideoStyle.VINTAGE: "with a nostalgic, period-appropriate look"
        }
        components.append(style_enhancements[request.style])
        
        # Additional details
        if request.additional_details:
            components.append(request.additional_details)
        
        return ". ".join(components) + "."
    except Exception as e:
        print(f"Error generating detailed prompt: {str(e)}")
        raise

@app.post("/api/v1/videos/generate")
async def generate_video(request: GenerationRequest):
    """Generate multiple versions of a video"""
    try:
        print("\n=== Starting New Video Generation ===")
        print(f"Request parameters: {request.dict()}")
        
        # Validate base prompt
        if not request.base_prompt or len(request.base_prompt.strip()) < 10:
            error_msg = "Please provide a more detailed video description (at least 10 characters)"
            print(f"Validation error: {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }

        # Generate detailed prompt
        detailed_prompt = generate_detailed_prompt(request)
        
        # Initialize job ID and video entry
        global videos_data
        new_id = len(videos_data) + 1 if videos_data else 1
        job_id = f"job_{new_id}"
        print(f"Created new job ID: {job_id}")

        try:
            # Create new video entry with better default values
            new_video = {
                "id": new_id,
                "job_id": job_id,
                "prompt": detailed_prompt,
                "style": request.style.value,
                "orientation": request.orientation.value,
                "duration": request.duration.value,
                "camera_view": request.camera_view.value,
                "background": request.background.value,
                "lighting": request.lighting,
                "color_palette": request.color_palette,
                "weather": request.weather,
                "time_of_day": request.time_of_day,
                "additional_details": request.additional_details,
                "status": "initializing",
                "created_at": datetime.now().isoformat(),
                "versions": [],
                "error": None
            }
            
            videos_data.append(new_video)
            print(f"Created video entry: {new_video}")

            # Verify required directories exist
            os.makedirs(PROCESSED_DIR, exist_ok=True)
            print(f"Verified output directory: {PROCESSED_DIR}")

            # Start async processing
            try:
                print("Starting video generation process...")
                generation_task = asyncio.create_task(process_video_generation(new_video))
                new_video["status"] = "generating"
                print(f"Generation task created for job {job_id}")
            except Exception as task_error:
                error_msg = f"Failed to start generation process: {str(task_error)}"
                print(f"Task creation error: {error_msg}")
                print(f"Traceback: {traceback.format_exc()}")
                new_video["status"] = "error"
                new_video["error"] = error_msg
                return {
                    "success": False,
                    "message": error_msg,
                    "job_id": job_id
                }
            
            return {
                "success": True,
                "message": "Video generation started successfully",
                "job_id": job_id,
                "video": new_video
            }

        except Exception as video_error:
            error_msg = f"Error setting up video generation: {str(video_error)}"
            print(f"Setup error: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "message": error_msg
            }

    except Exception as e:
        error_msg = f"Unexpected error in generate_video: {str(e)}"
        print(f"Global error: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        return {
            "success": False,
            "message": error_msg
        }

@app.get("/api/v1/videos/jobs")
async def get_generation_jobs():
    """Get all generation jobs with all versions"""
    jobs = []
    for v in videos_data:
        if "job_id" in v:
            job = {
                "job_id": v["job_id"],
                "video_id": v["id"],
                "prompt": v["prompt"],
                "style": v["style"],
                "status": v["status"],
                "started_at": v["created_at"],
                "versions": []
            }
            
            # Add all video versions if the job is completed
            if v["status"] == "completed" and "versions" in v:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                
                for idx, version in enumerate(v["versions"]):
                    if version.get("status") == "completed" and version.get("filename"):
                        video_path = os.path.join(base_dir, "videos", "processed", version["filename"])
                        file_exists = os.path.exists(video_path)
                        
                        job["versions"].append({
                            "version": idx,
                            "filename": version["filename"],
                            "url": f"/api/v1/videos/view/{version['filename']}",
                            "status": version["status"],
                            "generated_with": version.get("generated_with", "unknown"),
                            "file_exists": file_exists,
                            "completed_at": version.get("completed_at")
                        })
                        
                        print(f"Version {idx} - {version['filename']} exists: {file_exists}")
                        
                # Add metadata if available
                if "metadata" in v:
                    job["metadata"] = v["metadata"]
                    
            jobs.append(job)
    
    return {"jobs": jobs}

@app.post("/api/v1/videos/{video_id}/select-version")
async def select_version(request: VersionSelectionRequest):
    """Select a version of the generated video and generate metadata"""
    video = next((v for v in videos_data if v["id"] == request.video_id), None)
    if not video:
        raise AIErrorHTTP("Video not found", status_code=404)
    
    if request.version not in [0, 1, 2]:
        raise AIErrorHTTP("Invalid version number", status_code=400)
    
    try:
        # Update selected version
        video["metadata"]["selected_version"] = request.version
        
        # Generate engaging title (simulated)
        video["metadata"]["generated_title"] = f"🔥 MUST WATCH: {video['prompt'][:50]}... | Stunning {video['style']} Video"
        
        # Generate SEO-optimized description
        video["metadata"]["generated_description"] = f"""🎥 Experience this incredible {video['style']} video!
        
{video['prompt']}

Shot in stunning {video['orientation']} format with {video['camera_view']} views.
        
🎬 Created using cutting-edge AI technology
⏱️ Duration: {video['duration']}
🎨 Style: {video['style']}
        
👍 Like & Subscribe for more amazing content!
🔔 Turn on notifications to never miss an upload!

#AI #Video #Content #Trending #{video['style'].capitalize()}"""
        
        # Simulate thumbnail generation
        video["metadata"]["generated_thumbnail"] = f"https://example.com/thumbnail_{video['id']}.jpg"
        
        return {
            "success": True,
            "message": "Version selected and metadata generated",
            "video": video
        }
        
    except Exception as e:
        raise AIErrorHTTP(f"Error selecting version: {str(e)}", status_code=500)

@app.post("/api/v1/videos/{video_id}/youtube-upload")
async def youtube_upload(request: YouTubeUploadRequest):
    """Upload the selected version to YouTube"""
    video = next((v for v in videos_data if v["id"] == request.video_id), None)
    if not video:
        raise AIErrorHTTP("Video not found", status_code=404)
    
    if video["metadata"]["selected_version"] is None:
        raise AIErrorHTTP("No version selected for this video", status_code=400)
        
    if not request.upload:
        return {
            "success": True,
            "message": "Upload cancelled by user"
        }
    
    if not YOUTUBE_AVAILABLE:
        raise AIErrorHTTP("YouTube integration not available. Please check configuration.", status_code=503)
    
    try:
        video["metadata"]["youtube_status"] = "uploading"
        
        # Get the selected version's video file
        selected_version_index = video["metadata"]["selected_version"]
        if not video["versions"] or len(video["versions"]) <= selected_version_index:
            raise AIErrorHTTP("Selected version not found", status_code=400)
        
        selected_version = video["versions"][selected_version_index]
        video_filename = selected_version.get("filename")
        
        if not video_filename:
            raise AIErrorHTTP("Video file not found for selected version", status_code=400)
        
        # Get video file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        video_path = os.path.join(project_root, "videos", "processed", video_filename)
        
        if not os.path.exists(video_path):
            raise AIErrorHTTP(f"Video file not found: {video_filename}", status_code=404)
        
        # Upload to YouTube using our YouTube uploader
        upload_result = await youtube_uploader.upload_video(
            video_path=video_path,
            title=video["metadata"]["generated_title"],
            description=video["metadata"]["generated_description"],
            tags=["AI Generated", "Sora", "Automation", video["style"]],
            privacy=os.getenv('DEFAULT_YOUTUBE_PRIVACY', 'private')
        )
        
        if upload_result and upload_result.get("success"):
            video["metadata"]["youtube_status"] = "completed"
            video["metadata"]["youtube_url"] = upload_result["video_url"]
            video["metadata"]["youtube_video_id"] = upload_result["video_id"]
            
            return {
                "success": True,
                "message": "Video uploaded to YouTube successfully",
                "youtube_url": upload_result["video_url"],
                "video_id": upload_result["video_id"]
            }
        else:
            video["metadata"]["youtube_status"] = "failed"
            error_msg = upload_result.get("error", "Unknown upload error") if upload_result else "Upload failed"
            raise AIErrorHTTP(f"YouTube upload failed: {error_msg}", status_code=500)
        
    except Exception as e:
        video["metadata"]["youtube_status"] = "failed"
        raise AIErrorHTTP(f"Error uploading to YouTube: {str(e)}", status_code=500)

@app.post("/api/v1/videos/upload-direct")
async def upload_video_direct(request: DirectUploadRequest):
    """Upload a specific video version directly to YouTube without pre-selection"""
    video = next((v for v in videos_data if v["id"] == request.video_id), None)
    if not video:
        raise AIErrorHTTP("Video not found", status_code=404)
    
    if request.version_index not in [0, 1, 2]:
        raise AIErrorHTTP("Invalid version index. Must be 0, 1, or 2", status_code=400)
    
    if not YOUTUBE_AVAILABLE:
        raise AIErrorHTTP("YouTube integration not available. Please check configuration.", status_code=503)
    
    try:
        # Check if video has versions
        if not video.get("versions") or len(video["versions"]) <= request.version_index:
            raise AIErrorHTTP("Requested version not found", status_code=400)
        
        selected_version = video["versions"][request.version_index]
        video_filename = selected_version.get("filename")
        
        if not video_filename or selected_version.get("status") != "completed":
            raise AIErrorHTTP("Video version not ready or filename missing", status_code=400)
        
        # Get video file path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        video_path = os.path.join(project_root, "videos", "processed", video_filename)
        
        if not os.path.exists(video_path):
            raise AIErrorHTTP(f"Video file not found: {video_filename}", status_code=404)
        
        # Generate title and description if not provided
        upload_title = request.title or f"🔥 AI Generated Video: {video['prompt'][:50]}... | {video['style'].capitalize()} Style"
        upload_description = request.description or f"""🎥 Amazing AI-generated video created with Sora 2 Pro!

{video['prompt']}

📹 Video Details:
⏱️ Duration: {video.get('duration', 'N/A')}
🎨 Style: {video.get('style', 'N/A').capitalize()}
📐 Orientation: {video.get('orientation', 'N/A').capitalize()}
🎬 Camera: {video.get('camera_view', 'N/A').capitalize()}
🌅 Background: {video.get('background', 'N/A').capitalize()}

🤖 Created using cutting-edge AI technology
🚀 Generated with: {selected_version.get('generated_with', 'AI')}

👍 Like & Subscribe for more amazing AI content!
🔔 Turn on notifications to never miss an upload!

#AI #SoraAI #VideoGeneration #AIContent #TechDemo #{video.get('style', 'video').capitalize()}"""

        upload_tags = request.tags or [
            "AI Generated", 
            "Sora AI", 
            "Video Generation", 
            "AI Content",
            video.get('style', 'video').capitalize(),
            "Tech Demo",
            "Artificial Intelligence"
        ]
        
        print(f"Starting direct YouTube upload for video {request.video_id}, version {request.version_index}")
        
        # Initialize metadata if not exists
        if "metadata" not in video:
            video["metadata"] = {}
        
        video["metadata"]["youtube_status"] = "uploading"
        
        # Upload to YouTube using our YouTube uploader
        upload_result = await youtube_uploader.upload_video(
            video_path=video_path,
            title=upload_title,
            description=upload_description,
            tags=upload_tags,
            privacy=os.getenv('DEFAULT_YOUTUBE_PRIVACY', 'private')
        )
        
        if upload_result and upload_result.get("success"):
            video["metadata"]["youtube_status"] = "completed"
            video["metadata"]["youtube_url"] = upload_result["video_url"]
            video["metadata"]["youtube_video_id"] = upload_result["video_id"]
            video["metadata"]["uploaded_version"] = request.version_index
            video["metadata"]["uploaded_at"] = datetime.now().isoformat()
            
            print(f"✅ Direct upload successful: {upload_result['video_url']}")
            
            return {
                "success": True,
                "message": f"Video version {request.version_index + 1} uploaded to YouTube successfully!",
                "youtube_url": upload_result["video_url"],
                "youtube_video_id": upload_result["video_id"],
                "uploaded_version": request.version_index,
                "title": upload_title
            }
        else:
            video["metadata"]["youtube_status"] = "failed"
            error_msg = upload_result.get("error", "Unknown upload error") if upload_result else "Upload failed"
            raise AIErrorHTTP(f"YouTube upload failed: {error_msg}", status_code=500)
        
    except Exception as e:
        if "metadata" in video:
            video["metadata"]["youtube_status"] = "failed"
        raise AIErrorHTTP(f"Error uploading to YouTube: {str(e)}", status_code=500)

@app.get("/api/v1/videos/")
async def get_videos():
    """Get list of videos"""
    return {
        "videos": videos_data,
        "total": len(videos_data)
    }

@app.get("/api/v1/videos/{video_id}")
async def get_video(video_id: int):
    """Get specific video"""
    video = next((v for v in videos_data if v["id"] == video_id), None)
    if not video:
        return {"error": "Video not found"}, 404
    return video

from fastapi.responses import FileResponse
from fastapi.responses import StreamingResponse
import os

@app.get("/api/v1/videos/view/{filename}")
async def view_video(filename: str):
    """Stream a video file for viewing"""
    try:
        # Get absolute paths
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        video_path = os.path.join(project_root, "videos", "processed", filename)
        
        print(f"Current directory: {current_dir}")
        print(f"Project root: {project_root}")
        print(f"Attempting to access video at: {video_path}")
        
        # Create test video content if it doesn't exist
        if not os.path.exists(video_path):
            print(f"Video not found, creating test video at: {video_path}")
            os.makedirs(os.path.dirname(video_path), exist_ok=True)
            
            # Create a simple test video file (1-second black video)
            import imageio
            import numpy as np
            
            # Create a 1-second black video (30 frames)
            frames = []
            for _ in range(30):  # 1 second at 30fps
                # Create a black frame (480x640 pixels)
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frames.append(frame)
            
            # Save as MP4
            imageio.mimsave(video_path, frames, fps=30, format='mp4')
            
            print(f"Created test video file at: {video_path}")
            print(f"File exists after creation: {os.path.exists(video_path)}")
            print(f"File size: {os.path.getsize(video_path)} bytes")
        
        if not os.path.exists(video_path):
            raise HTTPException(status_code=404, detail=f"Video not found at {video_path}")
        
        # List directory contents for debugging
        dir_contents = os.listdir(os.path.dirname(video_path))
        print(f"Directory contents: {dir_contents}")
        
        # Use FileResponse for better video streaming support
        return FileResponse(
            path=video_path,
            media_type="video/mp4",
            filename=filename,
            headers={
                "Accept-Ranges": "bytes",
                "Content-Disposition": f'inline; filename="{filename}"',
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
            }
        )
        
    except Exception as e:
        error_msg = f"Error in view_video: {str(e)}"
        print(error_msg)
        print(f"Stack trace: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/api/v1/videos/download/{filename}")
async def download_video(filename: str):
    """Download a video file"""
    video_path = os.path.join("videos", "processed", filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        path=video_path,
        filename=filename,
        media_type="video/mp4"
    )

@app.get("/api/v1/videos/stats/summary")
async def get_video_stats():
    """Get video statistics"""
    return {
        "total_videos": len(videos_data),
        "uploaded_videos": len([v for v in videos_data if v["status"] == "uploaded"]),
        "pending_videos": len([v for v in videos_data if v["status"] == "pending"]),
        "success_rate": 91.2
    }

# YouTube API endpoints
@app.get("/api/v1/youtube/status")
async def get_youtube_status():
    """Get YouTube API connection status"""
    if not YOUTUBE_AVAILABLE:
        return {
            "success": False,
            "error": "YouTube integration not available",
            "setup_required": True
        }
    
    try:
        status = await youtube_uploader.test_connection()
        return status
    except Exception as e:
        return {
            "success": False,
            "error": f"YouTube API test failed: {str(e)}"
        }

@app.post("/api/v1/youtube/authenticate") 
async def authenticate_youtube(force_reauth: bool = False):
    """Authenticate with YouTube API"""
    if not YOUTUBE_AVAILABLE:
        return {
            "success": False,
            "error": "YouTube integration not available"
        }
    
    try:
        success = await youtube_uploader.authenticate(force_reauth=force_reauth)
        if success:
            channel_info = await youtube_uploader.get_channel_info()
            return {
                "success": True,
                "message": "YouTube authentication successful",
                "channel": channel_info
            }
        else:
            return {
                "success": False,
                "error": "YouTube authentication failed"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"YouTube authentication error: {str(e)}"
        }

@app.get("/api/v1/youtube/channel")
async def get_youtube_channel():
    """Get YouTube channel information"""
    if not YOUTUBE_AVAILABLE:
        return {
            "success": False,
            "error": "YouTube integration not available"
        }
    
    try:
        channel_info = await youtube_uploader.get_channel_info()
        if channel_info:
            return {
                "success": True,
                "channel": channel_info
            }
        else:
            return {
                "success": False,
                "error": "Failed to get channel information. Please authenticate first."
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting channel info: {str(e)}"
        }

# Configuration endpoints
@app.get("/api/v1/config")
async def get_config():
    """Get current configuration"""
    youtube_status = "not_configured"
    if YOUTUBE_AVAILABLE:
        try:
            status = await youtube_uploader.test_connection()
            youtube_status = "configured" if status.get("success") else "authentication_required"
        except:
            youtube_status = "error"
    
    return {
        "youtube": {
            "available": YOUTUBE_AVAILABLE,
            "status": youtube_status,
            "upload_enabled": os.getenv('YOUTUBE_UPLOAD_ENABLED', 'false').lower() == 'true',
            "default_privacy": os.getenv('DEFAULT_YOUTUBE_PRIVACY', 'private'),
            "default_category": os.getenv('DEFAULT_YOUTUBE_CATEGORY', '22')
        },
        "pipeline": {
            "check_interval": 30,
            "max_concurrent_uploads": 3
        },
        "ai": {
            "sora_available": USE_SORA_AI,
            "openai_api_configured": OPENAI_API_KEY is not None,
            "video_generation_mode": "sora_ai" if USE_SORA_AI else "placeholder"
        }
    }

@app.get("/api/v1/ai/status")
async def get_ai_status():
    """Get AI service status and configuration"""
    return {
        "sora_ai": {
            "available": USE_SORA_AI,
            "api_key_configured": OPENAI_API_KEY is not None,
            "status": "ready" if USE_SORA_AI else "not_configured",
            "message": "Sora AI is ready for video generation" if USE_SORA_AI else "Sora AI requires API key configuration"
        },
        "alternatives": {
            "runway_ml": {
                "name": "Runway ML Gen-2",
                "status": "not_integrated",
                "description": "Alternative AI video generation service",
                "website": "https://runwayml.com"
            },
            "stable_video": {
                "name": "Stable Video Diffusion",
                "status": "not_integrated", 
                "description": "Open-source video generation model",
                "website": "https://stability.ai/stable-video"
            },
            "pika_labs": {
                "name": "Pika Labs",
                "status": "not_integrated",
                "description": "AI video generation platform",
                "website": "https://pika.art"
            }
        },
        "setup_instructions": {
            "sora_ai": [
                "1. Obtain OpenAI API access (Sora may require special access)",
                "2. Add OPENAI_API_KEY to your .env file",
                "3. Restart the backend server",
                "4. Test video generation through the web interface"
            ]
        }
    }

# Analytics endpoints
@app.get("/api/v1/analytics/overview")
async def get_analytics_overview():
    """Get analytics overview"""
    return {
        "total_views": 15420,
        "total_videos": len(videos_data),
        "avg_views_per_video": 1028,
        "trending_video": {
            "title": "AI Generated Sunset Scene",
            "views": 1247
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting YouTube Automation Backend Server")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🎬 Frontend Interface: http://localhost:3000")
    print("🔧 Health Check: http://localhost:8000/health")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)