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

# Configure Sora API - Using OpenAI's video generation endpoint
# Sora might be accessed through different endpoints:
# Option 1: Direct Sora endpoint (if you have access)
SORA_API_ENDPOINT = "https://api.openai.com/v1/video/generations"
# Option 2: Through chat completions with video generation
# SORA_API_ENDPOINT = "https://api.openai.com/v1/chat/completions"

# Configure API client with robust error handling
transport = httpx.AsyncHTTPTransport(
    retries=3,  # Retry failed requests up to 3 times
    verify=True  # Verify SSL certificates
)

ai_client = httpx.AsyncClient(
    base_url="https://api.openai.com/v1",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    },
    transport=transport,
    timeout=120.0,  # 120 second timeout for video generation
    verify=True,  # Verify SSL certificates
    follow_redirects=True  # Follow redirects automatically
)

# Configure Sora API (will be available through OpenAI API)
SORA_API_ENDPOINT = "https://api.openai.com/v1/sora/generations"

# Configure API client with retry logic
transport = httpx.AsyncHTTPTransport(retries=3)  # Retry failed requests up to 3 times
ai_client = httpx.AsyncClient(
    base_url="https://api.openai.com/v1",
    headers={
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    },
    transport=transport,
    timeout=60.0  # 60 second timeout for long-running video generations
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
        
        # Prepare Sora 2 Pro API request
        sora_data = {
            "model": "sora-2-pro",
            "prompt": prompt,
            "size": "1080x1920" if orientation == "portrait" else "1920x1080",
            "duration": duration_seconds,
            "quality": "standard",
            "n": 1
        }
        
        print(f"🎬 Sora 2 Pro Request: {sora_data}")
        
        # Try multiple Sora endpoints
        sora_endpoints = [
            "/video/generations",
            "/sora/generations", 
            "/v1/video/generations",
            "/v1/sora/generations"
        ]
        
        for endpoint in sora_endpoints:
            try:
                print(f"🔍 Trying Sora endpoint: {endpoint}")
                response = await ai_client.post(
                    endpoint,
                    json=sora_data,
                    timeout=180.0  # 3 minutes for video generation
                )
                
                if response.status_code == 200:
                    print(f"✅ Sora 2 Pro API successful!")
                    result = response.json()
                    
                    if "data" in result and len(result["data"]) > 0:
                        video_url = result["data"][0].get("url") or result["data"][0].get("video_url")
                        video_id = result["data"][0].get("id", "unknown")
                        
                        if video_url:
                            # Download the Sora-generated video
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"sora2pro_{video_id}_{timestamp}.mp4"
                            filepath = os.path.join(PROCESSED_DIR, filename)
                            
                            async with httpx.AsyncClient(timeout=60.0) as download_client:
                                video_response = await download_client.get(video_url)
                                with open(filepath, 'wb') as f:
                                    f.write(video_response.content)
                            
                            print(f"🎉 Sora 2 Pro video created: {filename}")
                            return filename
                    
                elif response.status_code == 404:
                    print(f"❌ Endpoint {endpoint} not found")
                    continue
                else:
                    print(f"⚠️ Endpoint {endpoint} returned: {response.status_code}")
                    continue
                    
            except Exception as e:
                print(f"Error with endpoint {endpoint}: {str(e)}")
                continue
        
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
        
        response = await ai_client.post("/images/generations", json=dalle_data)
        
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
class AIError(HTTPException):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(status_code=status_code, detail=message)
            
            try:
                # Generate an image first using DALL-E
                image_prompt = f"{prompt} - high quality, detailed, {style} style"
                image_data = {
                    "model": "dall-e-3",
                    "prompt": image_prompt,
                    "size": "1024x1024",
                    "quality": "hd",
                    "n": 1
                }
                
                print(f"DALL-E Request: {image_prompt}")
                
                # Make API call to DALL-E
                image_response = await ai_client.post(
                    "/images/generations",
                    json=image_data,
                    timeout=60.0
                )
                
                if image_response.status_code == 200:
                    image_result = image_response.json()
                    if "data" in image_result and len(image_result["data"]) > 0:
                        image_url = image_result["data"][0].get("url")
                    if image_url:
                        print(f"DALL-E image generated successfully: {image_url}")
                        
                        # Download the image and convert to video
                        async with httpx.AsyncClient(timeout=30.0) as download_client:
                                print(f"Downloading image from: {image_url}")
                                img_response = await download_client.get(image_url)
                                
                                if img_response.status_code != 200:
                                    raise AIError(f"Failed to download image: {img_response.status_code}")
                                
                                # Check image size (prevent too large images)
                                content_length = len(img_response.content)
                                if content_length > 10 * 1024 * 1024:  # 10MB limit
                                    raise AIError("Downloaded image too large")
                                
                                print(f"Downloaded image size: {content_length} bytes")
                                
                                # Save image temporarily
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                temp_image_path = os.path.join(PROCESSED_DIR, f"temp_image_{timestamp}.jpg")
                                
                                with open(temp_image_path, 'wb') as f:
                                    f.write(img_response.content)
                                
                                print(f"Image saved to: {temp_image_path}")
                        
                        # Convert image to video using imageio
                        filename = f"dalle_video_{timestamp}.mp4"
                        video_path = os.path.join(PROCESSED_DIR, filename)
                        
                        # Create video from static image with simpler approach
                        try:
                            import imageio
                            from PIL import Image
                            import numpy as np
                            
                            print(f"Processing image: {temp_image_path}")
                            
                            # Simple video creation to prevent crashes
                            with Image.open(temp_image_path) as img:
                                if img.mode != 'RGB':
                                    img = img.convert('RGB')
                                
                                # Resize to manageable size
                                img = img.resize((480, 480), Image.Resampling.LANCZOS)
                                img_array = np.array(img, dtype=np.uint8)
                            
                            print(f"Creating simple video from image...")
                            
                            # Create simple video - just repeat the same frame
                            fps = 15  # Lower FPS for stability
                            total_frames = min(duration_seconds * fps, 60)  # Max 4 seconds
                            frames = [img_array.copy() for _ in range(total_frames)]
                            
                            # Save video
                            imageio.mimsave(video_path, frames, fps=fps, format='mp4')
                            print(f"Video created: {video_path}")
                            
                            # Clean up
                            os.remove(temp_image_path)
                            print(f"AI-generated video created: {filename}")
                            return filename
                            
                        except Exception as video_error:
                            print(f"Video creation failed: {str(video_error)}")
                            # Clean up on failure
                            if os.path.exists(temp_image_path):
                                os.remove(temp_image_path)
                            raise AIError(f"Video processing failed: {str(video_error)}")
                            
            # If DALL-E fails, try the Sora endpoints (in case they become available)
            print("DALL-E failed, attempting Sora endpoints...")
            
            # Expected Sora API format (when available)
            data = {
                "model": "sora-1.0-turbo",  # Expected model name
                "prompt": prompt,
                "size": "1080x1920" if orientation == "portrait" else "1920x1080",
                "duration": duration_seconds,
                "n": 1,
                "style": style  # Add style parameter
            }
            
            print(f"Sora API Request: {data}")
            
            # Try the expected Sora endpoint first
            response = await ai_client.post(
                "/video/generations",  # Expected endpoint
                json=data,
                timeout=120.0  # 120 second timeout for video generation
            )
            
            # If that fails, try alternative endpoints that might be available
            if response.status_code == 404:
                print("Trying alternative Sora endpoint...")
                response = await ai_client.post(
                    "/sora/generations",  # Alternative endpoint
                    json=data,
                    timeout=120.0
                )
        except Exception as dalle_error:
            print(f"DALL-E generation failed: {str(dalle_error)}")
            
            # Try Sora as fallback
            data = {
                "model": "sora-1.0-turbo",
                "prompt": prompt,
                "size": "1080x1920" if orientation == "portrait" else "1920x1080", 
                "duration": duration_seconds,
                "n": 1,
                "style": style
            }
            
            response = await ai_client.post(
                "/video/generations",
                json=data,
                timeout=120.0
            )
            
            print(f"API Response Status: {response.status_code}")
            
            # Check for error responses
            if response.status_code != 200:
                response_text = response.text
                print(f"Error response: {response_text}")
                
                try:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown error')
                except:
                    error_message = response_text
                    
                if response.status_code == 401:
                    raise AIError(f"Authentication failed. Please check your API key.", status_code=401)
                elif response.status_code == 403:
                    raise AIError(f"Access denied. Sora API is not yet publicly available. Current status: {error_message}", status_code=403)
                elif response.status_code == 404:
                    raise AIError(f"Sora API endpoint not found. The API may not be available yet. Check OpenAI's documentation for updates.", status_code=404)
                elif response.status_code == 429:
                    raise AIError(f"Rate limit exceeded: {error_message}", status_code=429)
                elif response.status_code >= 500:
                    raise AIError(f"OpenAI service error: {error_message}", status_code=response.status_code)
                else:
                    raise AIError(f"API error ({response.status_code}): {error_message}. Note: Sora API may not be publicly available yet.", status_code=response.status_code)
            
            result = response.json()
            print(f"API Response: {result}")
            
            # Extract video URL from response
            # The response format might be: {"data": [{"url": "...", "id": "..."}]}
            if "data" in result and len(result["data"]) > 0:
                video_url = result["data"][0].get("url") or result["data"][0].get("video_url")
                video_id = result["data"][0].get("id", "unknown")
                print(f"Video URL received: {video_url}")
                
                # Download the video and save it
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"sora_{video_id}_{timestamp}.mp4"
                filepath = os.path.join(PROCESSED_DIR, filename)
                
                # Download video from URL
                async with httpx.AsyncClient() as download_client:
                    video_response = await download_client.get(video_url)
                    with open(filepath, 'wb') as f:
                        f.write(video_response.content)
                
                print(f"Video downloaded to: {filepath}")
                return filename
            else:
                raise AIError("No video data in API response", status_code=500)
            
        except httpx.TimeoutException:
            print("Request timed out")
            raise TimeoutError("Video generation took too long. Please try a shorter duration.")
        except httpx.ConnectError as conn_err:
            print(f"Connection error: {str(conn_err)}")
            raise NetworkError("Failed to connect to OpenAI servers. Please check your internet connection.")
        except httpx.NetworkError as net_err:
            print(f"Network error: {str(net_err)}")
            raise NetworkError(f"Network issue detected: {str(net_err)}")
        except AIError:
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            if "EOF occurred in violation of protocol" in str(e):
                raise NetworkError("Secure connection failed. Please check your network security settings.")
            raise AIError(f"Unexpected error during video generation: {str(e)}", status_code=500)
            
    except Exception as e:
        print(f"Error in generate_sora_video: {str(e)}")
        raise

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
@app.exception_handler(AIError)
async def ai_exception_handler(request, exc: AIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.message}
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
        test_response = await ai_client.get("/models")
        
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
    """Get all generation jobs"""
    jobs = []
    for v in videos_data:
        if "job_id" in v:
            job = {
                "job_id": v["job_id"],
                "prompt": v["prompt"],
                "style": v["style"],
                "status": v["status"],
                "started_at": v["created_at"],
            }
            
            # Add video information if the job is completed
            if v["status"] == "completed":
                # Use the first version's filename if available
                if "versions" in v and len(v["versions"]) > 0:
                    filename = v["versions"][0]["filename"]
                else:
                    filename = v.get("filename")
                
                if filename:
                    job["video"] = {
                        "id": v["id"],
                        "filename": filename
                    }
                    # Check if the video file exists
                    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    video_path = os.path.join(base_dir, "videos", "processed", filename)
                    print(f"Checking video exists at: {video_path}")
            jobs.append(job)
    
    return {"jobs": jobs}

@app.post("/api/v1/videos/{video_id}/select-version")
async def select_version(request: VersionSelectionRequest):
    """Select a version of the generated video and generate metadata"""
    video = next((v for v in videos_data if v["id"] == request.video_id), None)
    if not video:
        raise AIError("Video not found", status_code=404)
    
    if request.version not in [0, 1, 2]:
        raise AIError("Invalid version number", status_code=400)
    
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
        raise AIError(f"Error selecting version: {str(e)}", status_code=500)

@app.post("/api/v1/videos/{video_id}/youtube-upload")
async def youtube_upload(request: YouTubeUploadRequest):
    """Upload the selected version to YouTube"""
    video = next((v for v in videos_data if v["id"] == request.video_id), None)
    if not video:
        raise AIError("Video not found", status_code=404)
    
    if video["metadata"]["selected_version"] is None:
        raise AIError("No version selected for this video", status_code=400)
        
    if not request.upload:
        return {
            "success": True,
            "message": "Upload cancelled by user"
        }
    
    try:
        # Simulate YouTube upload process
        video["metadata"]["youtube_status"] = "uploading"
        await asyncio.sleep(3)  # Simulate upload time
        
        # In real implementation, we would:
        # 1. Get the selected version's video file
        # 2. Use YouTube API to upload
        # 3. Set title, description, thumbnail
        # 4. Configure privacy settings
        
        video["metadata"]["youtube_status"] = "completed"
        video["metadata"]["youtube_url"] = f"https://youtube.com/watch?v=example_{video['id']}"
        
        return {
            "success": True,
            "message": "Video uploaded to YouTube successfully",
            "youtube_url": video["metadata"]["youtube_url"]
        }
        
    except Exception as e:
        video["metadata"]["youtube_status"] = "failed"
        raise AIError(f"Error uploading to YouTube: {str(e)}", status_code=500)

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

# Configuration endpoints
@app.get("/api/v1/config")
async def get_config():
    """Get current configuration"""
    return {
        "youtube": {
            "channel_id": "UCWYRPSsmrXvdDeaQxiMkdJg",
            "default_privacy": "private"
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

# Dashboard endpoint (serves a simple HTML page)
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple dashboard for testing"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Automation Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .card { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }
            .status { color: #28a745; font-weight: bold; }
            .button { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .video { border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🎬 YouTube Automation Pipeline Dashboard</h1>
        
        <div class="card">
            <h2>Pipeline Status</h2>
            <p>Status: <span class="status">Running</span></p>
            <p>Videos Processed: 147</p>
            <p>Success Rate: 91.2%</p>
            <button class="button" onclick="controlPipeline('start')">Start</button>
            <button class="button" onclick="controlPipeline('stop')">Stop</button>
        </div>
        
        <div class="card">
            <h2>Recent Videos</h2>
            <div class="video">
                <strong>AI Generated Sunset Scene</strong><br>
                Status: Uploaded | Views: 1,247 | <a href="https://youtube.com/watch?v=abc123">Watch</a>
            </div>
            <div class="video">
                <strong>Futuristic City Landscape</strong><br>
                Status: Uploading (67%) | Processing...
            </div>
            <div class="video">
                <strong>Ocean Waves Animation</strong><br>
                Status: Pending | Queued for upload
            </div>
        </div>
        
        <div class="card">
            <h2>Quick Actions</h2>
            <button class="button" onclick="uploadVideo()">Upload Video</button>
            <button class="button" onclick="generateVideo()">Generate Video</button>
            <button class="button" onclick="viewLogs()">View Logs</button>
        </div>
        
        <div class="card">
            <h2>API Endpoints</h2>
            <ul>
                <li><a href="/api/v1/pipeline/status">/api/v1/pipeline/status</a></li>
                <li><a href="/api/v1/videos/">/api/v1/videos/</a></li>
                <li><a href="/api/v1/analytics/overview">/api/v1/analytics/overview</a></li>
                <li><a href="/docs">/docs (API Documentation)</a></li>
            </ul>
        </div>
        
        <script>
            function controlPipeline(action) {
                fetch(`/api/v1/pipeline/${action}`, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        location.reload();
                    });
            }
            
            function uploadVideo() {
                alert('Upload video functionality - integrate with file picker');
            }
            
            function generateVideo() {
                alert('Generate video functionality - integrate with Sora AI');
            }
            
            function viewLogs() {
                alert('View logs functionality - show real-time logs');
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)