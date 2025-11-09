#!/usr/bin/env python3
"""
Simple FastAPI server for YouTube automation pipeline
This is a minimal web interface to test the automation system
"""

import os
import json
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Import our existing automation modules
import sys
sys.path.append('src')

try:
    from video_uploader import VideoUploader
    from config_manager import ConfigManager
    from file_monitor import VideoMonitor
    from youtube_auth import YouTubeAPI
    from ai_manager import AIContentGenerator, ContentPipeline
except ImportError as e:
    print(f"Warning: Could not import automation modules: {e}")
    VideoUploader = None
    ConfigManager = None
    VideoMonitor = None
    YouTubeAPI = None
    AIContentGenerator = None
    ContentPipeline = None

app = FastAPI(title="YouTube Automation Pipeline", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo
pipeline_status = {
    "active": False,
    "last_run": None,
    "videos_processed": 0,
    "status": "stopped"
}

# AI pipeline tracking
ai_jobs = {}
active_connections: List[WebSocket] = []

# Initialize AI components
ai_generator = None
content_pipeline = None

if AIContentGenerator and ContentPipeline:
    try:
        ai_generator = AIContentGenerator()
        content_pipeline = ContentPipeline()
    except Exception as e:
        print(f"Warning: Could not initialize AI components: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "data": pipeline_status
        })
        
        # Keep connection alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)

async def broadcast_update(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    if active_connections:
        for connection in active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Simple HTML dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Automation Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .status { padding: 20px; border-radius: 8px; margin: 20px 0; }
            .active { background-color: #d4edda; border: 1px solid #c3e6cb; }
            .inactive { background-color: #f8d7da; border: 1px solid #f5c6cb; }
            button { padding: 10px 20px; margin: 10px; border: none; border-radius: 4px; cursor: pointer; }
            .start { background-color: #28a745; color: white; }
            .stop { background-color: #dc3545; color: white; }
            .logs { background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; max-height: 300px; overflow-y: auto; }
        </style>
    </head>
    <body>
        <h1>🎬 YouTube Automation Pipeline</h1>
        
        <div id="status" class="status inactive">
            <h3>Pipeline Status: <span id="statusText">Stopped</span></h3>
            <p>Videos Processed: <span id="videoCount">0</span></p>
            <p>Last Run: <span id="lastRun">Never</span></p>
        </div>
        
        <div>
            <button class="start" onclick="startPipeline()">Start Pipeline</button>
            <button class="stop" onclick="stopPipeline()">Stop Pipeline</button>
            <button onclick="uploadTest()">Test Upload</button>
            <button onclick="refreshStatus()">Refresh Status</button>
        </div>
        
        <div>
            <h3>🤖 AI Content Generation</h3>
            <div style="margin: 15px 0;">
                <input type="text" id="aiPrompt" placeholder="Enter video prompt..." style="width: 400px; padding: 8px; margin-right: 10px;">
                <select id="aiStyle" style="padding: 8px; margin-right: 10px;">
                    <option value="cinematic">Cinematic</option>
                    <option value="realistic">Realistic</option>
                    <option value="artistic">Artistic</option>
                    <option value="documentary">Documentary</option>
                </select>
                <button onclick="generateAIContent()">Generate Video</button>
                <button onclick="enhancePrompt()">Enhance Prompt</button>
            </div>
            <button onclick="checkAIStatus()">Check AI Status</button>
            <button onclick="listAIJobs()">List AI Jobs</button>
        </div>
        
        <div>
            <h3>📂 Quick Actions</h3>
            <button onclick="listVideos()">List Videos</button>
            <button onclick="checkConfig()">Check Config</button>
            <button onclick="viewLogs()">View Logs</button>
        </div>
        
        <div class="logs">
            <h4>Activity Log</h4>
            <div id="logs"></div>
        </div>
        
        <script>
            let ws;
            
            function connectWebSocket() {
                ws = new WebSocket(`ws://${window.location.host}/ws`);
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    if (data.type === 'status') {
                        updateStatus(data.data);
                    } else if (data.type === 'log') {
                        addLog(data.message);
                    } else if (data.type === 'ai_job') {
                        handleAIJobUpdate(data);
                    }
                };
                
                ws.onclose = function() {
                    addLog('WebSocket connection closed. Reconnecting...');
                    setTimeout(connectWebSocket, 5000);
                };
            }
            
            function updateStatus(status) {
                document.getElementById('statusText').textContent = status.status;
                document.getElementById('videoCount').textContent = status.videos_processed;
                document.getElementById('lastRun').textContent = status.last_run || 'Never';
                
                const statusDiv = document.getElementById('status');
                if (status.active) {
                    statusDiv.className = 'status active';
                } else {
                    statusDiv.className = 'status inactive';
                }
            }
            
            function addLog(message) {
                const logs = document.getElementById('logs');
                const time = new Date().toLocaleTimeString();
                logs.innerHTML += `<div>[${time}] ${message}</div>`;
                logs.scrollTop = logs.scrollHeight;
            }
            
            function handleAIJobUpdate(data) {
                const statusEmoji = {
                    'starting': '🚀',
                    'generating': '⚡',
                    'completed': '✅',
                    'failed': '❌',
                    'error': '💥'
                };
                
                const emoji = statusEmoji[data.status] || '🤖';
                addLog(`${emoji} AI Job ${data.job_id}: ${data.message}`);
                
                if (data.result && data.result.success) {
                    if (data.result.video && data.result.video.filename) {
                        addLog(`📹 Generated: ${data.result.video.filename}`);
                    }
                    if (data.result.thumbnail) {
                        addLog(`🖼️ Thumbnail: ${data.result.thumbnail}`);
                    }
                }
            }
            
            async function startPipeline() {
                try {
                    const response = await fetch('/api/pipeline/start', { method: 'POST' });
                    const data = await response.json();
                    addLog(data.message || 'Pipeline start requested');
                } catch (e) {
                    addLog('Error starting pipeline: ' + e.message);
                }
            }
            
            async function stopPipeline() {
                try {
                    const response = await fetch('/api/pipeline/stop', { method: 'POST' });
                    const data = await response.json();
                    addLog(data.message || 'Pipeline stop requested');
                } catch (e) {
                    addLog('Error stopping pipeline: ' + e.message);
                }
            }
            
            async function uploadTest() {
                try {
                    const response = await fetch('/api/test/upload', { method: 'POST' });
                    const data = await response.json();
                    addLog(data.message || 'Test upload completed');
                } catch (e) {
                    addLog('Error in test upload: ' + e.message);
                }
            }
            
            async function refreshStatus() {
                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    updateStatus(data);
                    addLog('Status refreshed');
                } catch (e) {
                    addLog('Error refreshing status: ' + e.message);
                }
            }
            
            async function listVideos() {
                try {
                    const response = await fetch('/api/videos');
                    const data = await response.json();
                    addLog(`Found ${data.length} videos in input folder`);
                } catch (e) {
                    addLog('Error listing videos: ' + e.message);
                }
            }
            
            async function checkConfig() {
                try {
                    const response = await fetch('/api/config');
                    const data = await response.json();
                    addLog('Configuration loaded successfully');
                } catch (e) {
                    addLog('Error checking config: ' + e.message);
                }
            }
            
            async function viewLogs() {
                try {
                    const response = await fetch('/api/logs');
                    const data = await response.json();
                    addLog('Recent logs loaded');
                } catch (e) {
                    addLog('Error loading logs: ' + e.message);
                }
            }
            
            // AI Functions
            async function generateAIContent() {
                const prompt = document.getElementById('aiPrompt').value;
                const style = document.getElementById('aiStyle').value;
                
                if (!prompt.trim()) {
                    addLog('Please enter a prompt for AI generation');
                    return;
                }
                
                try {
                    const response = await fetch('/api/ai/generate', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({prompt: prompt, style: style})
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        addLog(`AI generation started - Job ID: ${data.job_id}`);
                        addLog(`Prompt: ${data.prompt}`);
                        
                        // Monitor job progress
                        monitorAIJob(data.job_id);
                    } else {
                        addLog('Error starting AI generation: ' + (data.message || 'Unknown error'));
                    }
                } catch (e) {
                    addLog('Error in AI generation: ' + e.message);
                }
            }
            
            async function enhancePrompt() {
                const prompt = document.getElementById('aiPrompt').value;
                
                if (!prompt.trim()) {
                    addLog('Please enter a prompt to enhance');
                    return;
                }
                
                try {
                    const response = await fetch('/api/ai/enhance-prompt', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({prompt: prompt})
                    });
                    const data = await response.json();
                    
                    if (data.success) {
                        document.getElementById('aiPrompt').value = data.enhanced_prompt;
                        addLog('Prompt enhanced successfully');
                        addLog(`Original: ${data.original_prompt}`);
                        addLog(`Enhanced: ${data.enhanced_prompt}`);
                    } else {
                        addLog('Error enhancing prompt');
                    }
                } catch (e) {
                    addLog('Error enhancing prompt: ' + e.message);
                }
            }
            
            async function checkAIStatus() {
                try {
                    const response = await fetch('/api/ai/status');
                    const data = await response.json();
                    
                    addLog('AI Services Status:');
                    addLog(`- OpenAI Available: ${data.openai_available ? '✅' : '❌'}`);
                    addLog(`- PIL Available: ${data.pil_available ? '✅' : '❌'}`);
                    addLog(`- Sora Enabled: ${data.sora_enabled ? '✅' : '❌'}`);
                    addLog(`- GPT Enabled: ${data.gpt_enabled ? '✅' : '❌'}`);
                    addLog(`- DALL-E Enabled: ${data.dalle_enabled ? '✅' : '❌'}`);
                } catch (e) {
                    addLog('Error checking AI status: ' + e.message);
                }
            }
            
            async function listAIJobs() {
                try {
                    const response = await fetch('/api/ai/jobs');
                    const data = await response.json();
                    
                    addLog(`Found ${data.jobs.length} AI generation jobs`);
                    data.jobs.forEach(job => {
                        addLog(`- ${job.prompt?.substring(0, 30)}... Status: ${job.status}`);
                    });
                } catch (e) {
                    addLog('Error listing AI jobs: ' + e.message);
                }
            }
            
            async function monitorAIJob(jobId) {
                const maxChecks = 60; // Monitor for up to 5 minutes
                let checks = 0;
                
                const checkJob = async () => {
                    try {
                        const response = await fetch(`/api/ai/jobs/${jobId}`);
                        const job = await response.json();
                        
                        if (job.status === 'completed') {
                            addLog(`✅ AI generation completed successfully!`);
                            if (job.video && job.video.filename) {
                                addLog(`📹 Video: ${job.video.filename}`);
                            }
                            if (job.thumbnail) {
                                addLog(`🖼️ Thumbnail: ${job.thumbnail}`);
                            }
                            return;
                        } else if (job.status === 'failed' || job.status === 'error') {
                            addLog(`❌ AI generation failed: ${job.error || 'Unknown error'}`);
                            return;
                        }
                        
                        // Continue monitoring
                        checks++;
                        if (checks < maxChecks) {
                            setTimeout(checkJob, 5000); // Check every 5 seconds
                        } else {
                            addLog(`⏰ Job monitoring timeout for ${jobId}`);
                        }
                    } catch (e) {
                        addLog(`Error monitoring job ${jobId}: ${e.message}`);
                    }
                };
                
                // Start monitoring
                setTimeout(checkJob, 2000);
            }
            
            // Initialize
            connectWebSocket();
            refreshStatus();
            addLog('Dashboard initialized');
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/api/status")
async def get_status():
    """Get current pipeline status"""
    return pipeline_status

@app.post("/api/pipeline/start")
async def start_pipeline():
    """Start the automation pipeline"""
    try:
        pipeline_status["active"] = True
        pipeline_status["status"] = "running"
        pipeline_status["last_run"] = datetime.now().isoformat()
        
        # Broadcast update
        await broadcast_update({
            "type": "status",
            "data": pipeline_status
        })
        
        await broadcast_update({
            "type": "log",
            "message": "Pipeline started successfully"
        })
        
        return {"success": True, "message": "Pipeline started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pipeline/stop")
async def stop_pipeline():
    """Stop the automation pipeline"""
    try:
        pipeline_status["active"] = False
        pipeline_status["status"] = "stopped"
        
        # Broadcast update
        await broadcast_update({
            "type": "status",
            "data": pipeline_status
        })
        
        await broadcast_update({
            "type": "log",
            "message": "Pipeline stopped"
        })
        
        return {"success": True, "message": "Pipeline stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/test/upload")
async def test_upload():
    """Test video upload functionality"""
    try:
        if VideoUploader is None:
            return {"success": False, "message": "VideoUploader not available"}
        
        # Check for videos in input folder
        input_dir = Path("videos/input")
        if not input_dir.exists():
            return {"success": False, "message": "Input directory not found"}
        
        video_files = list(input_dir.glob("*.mp4")) + list(input_dir.glob("*.mov"))
        if not video_files:
            return {"success": False, "message": "No video files found in input directory"}
        
        await broadcast_update({
            "type": "log",
            "message": f"Found {len(video_files)} video files for testing"
        })
        
        return {"success": True, "message": f"Test upload ready - found {len(video_files)} videos"}
        
    except Exception as e:
        await broadcast_update({
            "type": "log",
            "message": f"Test upload error: {str(e)}"
        })
        return {"success": False, "message": str(e)}

@app.get("/api/videos")
async def list_videos():
    """List available videos"""
    try:
        input_dir = Path("videos/input")
        processed_dir = Path("videos/processed")
        
        videos = {
            "input": [],
            "processed": []
        }
        
        if input_dir.exists():
            videos["input"] = [f.name for f in input_dir.glob("*") if f.is_file()]
        
        if processed_dir.exists():
            videos["processed"] = [f.name for f in processed_dir.glob("*") if f.is_file()]
        
        return videos
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/config")
async def get_config():
    """Get configuration status"""
    try:
        config_file = Path("config/config.json")
        token_file = Path("config/token.json")
        
        config_status = {
            "config_exists": config_file.exists(),
            "token_exists": token_file.exists(),
            "youtube_configured": False
        }
        
        if ConfigManager is not None:
            try:
                config_manager = ConfigManager()
                config = config_manager.load_config()
                config_status["youtube_configured"] = bool(config.get("youtube", {}).get("client_id"))
            except:
                pass
        
        return config_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/logs")
async def get_logs():
    """Get recent logs"""
    try:
        logs_file = Path("logs/upload_records.json")
        if logs_file.exists():
            with open(logs_file, 'r') as f:
                logs = json.load(f)
            return {"logs": logs[-10:]}  # Last 10 entries
        else:
            return {"logs": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/youtube/channel")
async def get_youtube_channel():
    """Get YouTube channel information"""
    try:
        if YouTubeAPI:
            youtube_api = YouTubeAPI()
            service = youtube_api.authenticate()
            
            if service:
                # Get channel information
                channels_response = service.channels().list(
                    part='snippet,statistics,brandingSettings',
                    mine=True
                ).execute()
                
                if channels_response['items']:
                    channel = channels_response['items'][0]
                    return {
                        "success": True,
                        "channel": {
                            "id": channel['id'],
                            "title": channel['snippet']['title'],
                            "description": channel['snippet']['description'][:200] + "..." if len(channel['snippet']['description']) > 200 else channel['snippet']['description'],
                            "thumbnail": channel['snippet']['thumbnails']['default']['url'],
                            "subscriber_count": channel['statistics'].get('subscriberCount', 'Hidden'),
                            "video_count": channel['statistics'].get('videoCount', '0'),
                            "view_count": channel['statistics'].get('viewCount', '0'),
                            "country": channel['snippet'].get('country', 'Not specified'),
                            "custom_url": channel['snippet'].get('customUrl', ''),
                        }
                    }
                else:
                    return {"success": False, "error": "No channel found"}
            else:
                return {"success": False, "error": "YouTube authentication failed"}
        else:
            return {"success": False, "error": "YouTube API not available"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/youtube/videos")
async def get_youtube_videos(max_results: int = 10):
    """Get recent YouTube videos from the channel"""
    try:
        if YouTubeAPI:
            youtube_api = YouTubeAPI()
            service = youtube_api.authenticate()
            
            if service:
                # Get channel uploads playlist
                channels_response = service.channels().list(
                    part='contentDetails',
                    mine=True
                ).execute()
                
                if channels_response['items']:
                    uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    
                    # Get recent videos
                    playlist_response = service.playlistItems().list(
                        part='snippet',
                        playlistId=uploads_playlist_id,
                        maxResults=max_results
                    ).execute()
                    
                    videos = []
                    for item in playlist_response['items']:
                        videos.append({
                            "id": item['snippet']['resourceId']['videoId'],
                            "title": item['snippet']['title'],
                            "description": item['snippet']['description'][:100] + "..." if len(item['snippet']['description']) > 100 else item['snippet']['description'],
                            "published_at": item['snippet']['publishedAt'],
                            "thumbnail": item['snippet']['thumbnails']['default']['url'],
                            "url": f"https://www.youtube.com/watch?v={item['snippet']['resourceId']['videoId']}"
                        })
                    
                    return {"success": True, "videos": videos}
                else:
                    return {"success": False, "error": "No channel found"}
            else:
                return {"success": False, "error": "YouTube authentication failed"}
        else:
            return {"success": False, "error": "YouTube API not available"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# AI Content Generation Endpoints

@app.get("/api/ai/status")
async def get_ai_status():
    """Get AI services status"""
    try:
        if ai_generator:
            return ai_generator.get_ai_status()
        else:
            return {
                "openai_available": False,
                "pil_available": False,
                "sora_enabled": False,
                "gpt_enabled": False,
                "dalle_enabled": False,
                "config_loaded": False,
                "error": "AI components not initialized"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/generate")
async def generate_ai_content(request: dict):
    """Generate complete AI content (video + metadata + thumbnail)"""
    try:
        if not content_pipeline:
            raise HTTPException(status_code=503, detail="AI pipeline not available")
        
        prompt = request.get("prompt")
        style = request.get("style", "cinematic")
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Generate unique job ID
        job_id = f"ai_job_{int(time.time())}"
        
        # Start generation process
        ai_jobs[job_id] = {
            "status": "starting",
            "prompt": prompt,
            "style": style,
            "started_at": datetime.now().isoformat()
        }
        
        # Broadcast job start
        await broadcast_update({
            "type": "ai_job",
            "job_id": job_id,
            "status": "starting",
            "message": f"Starting AI content generation: {prompt[:50]}..."
        })
        
        # Start async generation
        asyncio.create_task(run_ai_generation(job_id, prompt, style))
        
        return {
            "success": True,
            "job_id": job_id,
            "message": "AI content generation started",
            "prompt": prompt,
            "style": style
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/jobs/{job_id}")
async def get_ai_job_status(job_id: str):
    """Get status of AI generation job"""
    try:
        if job_id not in ai_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return ai_jobs[job_id]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ai/jobs")
async def list_ai_jobs():
    """List all AI generation jobs"""
    try:
        return {"jobs": list(ai_jobs.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ai/enhance-prompt")
async def enhance_prompt(request: dict):
    """Enhance a basic prompt for better AI generation"""
    try:
        if not ai_generator:
            raise HTTPException(status_code=503, detail="AI generator not available")
        
        prompt = request.get("prompt")
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        enhanced = await ai_generator.enhance_prompt(prompt)
        
        return {
            "success": True,
            "original_prompt": prompt,
            "enhanced_prompt": enhanced
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Background AI generation task
async def run_ai_generation(job_id: str, prompt: str, style: str):
    """Run AI content generation in background"""
    try:
        # Update job status
        ai_jobs[job_id]["status"] = "generating"
        
        await broadcast_update({
            "type": "ai_job",
            "job_id": job_id,
            "status": "generating",
            "message": "Generating AI content..."
        })
        
        # Run the content generation
        result = await content_pipeline.generate_complete_content(prompt, style)
        
        # Update job with results
        ai_jobs[job_id].update(result)
        ai_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        if result.get("success"):
            ai_jobs[job_id]["status"] = "completed"
            message = f"AI content generation completed successfully!"
        else:
            ai_jobs[job_id]["status"] = "failed"
            message = f"AI content generation failed: {result.get('error', 'Unknown error')}"
        
        # Broadcast completion
        await broadcast_update({
            "type": "ai_job",
            "job_id": job_id,
            "status": ai_jobs[job_id]["status"],
            "message": message,
            "result": result
        })
        
        # Update pipeline stats
        if result.get("success"):
            pipeline_status["videos_processed"] += 1
            pipeline_status["last_run"] = datetime.now().isoformat()
            
            await broadcast_update({
                "type": "status",
                "data": pipeline_status
            })
        
    except Exception as e:
        ai_jobs[job_id]["status"] = "error"
        ai_jobs[job_id]["error"] = str(e)
        ai_jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
        await broadcast_update({
            "type": "ai_job",
            "job_id": job_id,
            "status": "error",
            "message": f"AI generation error: {str(e)}"
        })

if __name__ == "__main__":
    print("🎬 Starting YouTube Automation Dashboard...")
    print("📱 Dashboard: http://localhost:8000")
    print("🔌 WebSocket: ws://localhost:8000/ws")
    print("📋 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False
    )