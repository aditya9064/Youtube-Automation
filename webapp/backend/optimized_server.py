"""
Simple FastAPI server for YouTube Automation Web App
Optimized version with lazy loading
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import traceback

# Initialize directories quietly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEOS_DIR = os.path.join(BASE_DIR, "videos")
PROCESSED_DIR = os.path.join(VIDEOS_DIR, "processed")
os.makedirs(PROCESSED_DIR, exist_ok=True)

# Load environment variables silently
load_dotenv()

# Basic app setup
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for lazy loading
ai_client = None
OPENAI_API_KEY = None
SORA_API_ENDPOINT = None
videos_data = []

# Custom exceptions
class AIError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class NetworkError(AIError):
    def __init__(self, message: str = "Network error occurred. Please try again."):
        super().__init__(message, status_code=503)

class TimeoutError(AIError):
    def __init__(self, message: str = "Request timed out. Please try again."):
        super().__init__(message, status_code=504)

# Lazy initialization function
async def init_api_client():
    global ai_client, OPENAI_API_KEY, SORA_API_ENDPOINT
    
    if ai_client is None:
        try:
            import httpx
            
            # Configure OpenAI API
            OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
            if not OPENAI_API_KEY:
                raise AIError("OPENAI_API_KEY not found. Please set up your API key.", status_code=500)
                
            # Configure Sora API endpoint
            SORA_API_ENDPOINT = "https://api.openai.com/v1/sora/generations"
            
            # Configure API client with retry logic
            transport = httpx.AsyncHTTPTransport(retries=3)
            ai_client = httpx.AsyncClient(
                base_url="https://api.openai.com/v1",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                transport=transport,
                timeout=60.0
            )
            return True
        except Exception as e:
            print(f"Error initializing API client: {str(e)}")
            return False

# API Models
from enum import Enum
from pydantic import BaseModel

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

class GenerationRequest(BaseModel):
    base_prompt: str
    orientation: VideoOrientation
    duration: VideoDuration
    style: VideoStyle
    lighting: Optional[str] = "natural"
    color_palette: Optional[str] = None
    weather: Optional[str] = None
    time_of_day: Optional[str] = None
    additional_details: Optional[str] = None

# API Routes
@app.get("/api/v1/videos/jobs")
async def get_jobs():
    """Get all video generation jobs"""
    return {"jobs": videos_data}

@app.post("/api/v1/videos/generate")
async def generate_video(request: GenerationRequest):
    """Generate a video using Sora AI"""
    try:
        # Initialize API client if needed
        if not ai_client and not await init_api_client():
            raise AIError("Failed to initialize API client. Please try again.", status_code=500)

        # Generate prompt
        prompt = f"Create a {request.duration.value} {request.style.value} video in {request.orientation.value} format showing {request.base_prompt}"
        
        try:
            import httpx
            response = await ai_client.post(
                SORA_API_ENDPOINT,
                json={"prompt": prompt}
            )
            
            if response.status_code != 200:
                raise AIError(f"Sora API error: {response.text}", status_code=response.status_code)
                
            result = response.json()
            
            # Create job entry
            job_id = f"job_{len(videos_data) + 1}"
            job = {
                "id": len(videos_data) + 1,
                "job_id": job_id,
                "status": "generating",
                "prompt": prompt,
                "style": request.style.value,
                "created_at": datetime.now().isoformat(),
                "result": result
            }
            videos_data.append(job)
            
            return {"success": True, "job_id": job_id}
            
        except httpx.TimeoutException:
            raise TimeoutError()
        except httpx.NetworkError as e:
            raise NetworkError(str(e))
        except Exception as e:
            raise AIError(f"Error during video generation: {str(e)}", status_code=500)
            
    except Exception as e:
        if isinstance(e, (AIError, NetworkError, TimeoutError)):
            raise HTTPException(status_code=e.status_code, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("optimized_server:app", host="0.0.0.0", port=8005, reload=True)