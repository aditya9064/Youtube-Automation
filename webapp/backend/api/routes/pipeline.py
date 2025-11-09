"""
Pipeline API Routes - Main automation control endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

from database.connection import get_database
from database.models import Pipeline, Video, SystemLog
from core.pipeline_manager import get_pipeline_manager
from api.schemas import PipelineStatus, PipelineConfig, PipelineStats

router = APIRouter()

@router.get("/status", response_model=Dict[str, Any])
async def get_pipeline_status():
    """Get current pipeline status and statistics"""
    pipeline_manager = get_pipeline_manager()
    
    return {
        "status": pipeline_manager.get_status(),
        "is_running": pipeline_manager.is_running(),
        "queue_size": pipeline_manager.get_queue_size(),
        "active_jobs": pipeline_manager.get_active_jobs(),
        "stats": pipeline_manager.get_stats(),
        "last_activity": pipeline_manager.get_last_activity(),
        "uptime": pipeline_manager.get_uptime()
    }

@router.post("/start")
async def start_pipeline(background_tasks: BackgroundTasks):
    """Start the automation pipeline"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        result = await pipeline_manager.start()
        if result:
            return {"status": "success", "message": "Pipeline started successfully"}
        else:
            raise HTTPException(status_code=400, detail="Pipeline is already running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {str(e)}")

@router.post("/stop")
async def stop_pipeline():
    """Stop the automation pipeline"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        result = await pipeline_manager.stop()
        if result:
            return {"status": "success", "message": "Pipeline stopped successfully"}
        else:
            raise HTTPException(status_code=400, detail="Pipeline is not running")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop pipeline: {str(e)}")

@router.post("/pause")
async def pause_pipeline():
    """Pause the automation pipeline"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        result = await pipeline_manager.pause()
        return {"status": "success", "message": "Pipeline paused successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause pipeline: {str(e)}")

@router.post("/resume")
async def resume_pipeline():
    """Resume the automation pipeline"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        result = await pipeline_manager.resume()
        return {"status": "success", "message": "Pipeline resumed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume pipeline: {str(e)}")

@router.get("/queue")
async def get_queue():
    """Get current pipeline queue"""
    pipeline_manager = get_pipeline_manager()
    
    return {
        "queue": pipeline_manager.get_queue(),
        "size": pipeline_manager.get_queue_size(),
        "processing": pipeline_manager.get_active_jobs()
    }

@router.post("/queue/add")
async def add_to_queue(
    video_data: Dict[str, Any],
    priority: int = 0,
    db: Session = Depends(get_database)
):
    """Add a video generation job to the queue"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        # Create video record
        video = Video(
            title=video_data.get("title", "Generated Video"),
            description=video_data.get("description", ""),
            prompt=video_data.get("prompt", ""),
            ai_model=video_data.get("ai_model", "sora"),
            generation_parameters=video_data.get("parameters", {}),
            status="pending"
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # Add to pipeline queue
        job_id = await pipeline_manager.add_job(
            job_type="generate_video",
            video_id=video.id,
            data=video_data,
            priority=priority
        )
        
        return {
            "status": "success",
            "message": "Job added to queue",
            "job_id": job_id,
            "video_id": video.id,
            "position": pipeline_manager.get_queue_size()
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add job to queue: {str(e)}")

@router.delete("/queue/{job_id}")
async def remove_from_queue(job_id: str):
    """Remove a job from the queue"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        result = await pipeline_manager.remove_job(job_id)
        if result:
            return {"status": "success", "message": "Job removed from queue"}
        else:
            raise HTTPException(status_code=404, detail="Job not found in queue")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove job: {str(e)}")

@router.get("/logs")
async def get_pipeline_logs(
    limit: int = 100,
    level: Optional[str] = None,
    component: Optional[str] = None,
    db: Session = Depends(get_database)
):
    """Get pipeline logs with filtering"""
    query = db.query(SystemLog).order_by(SystemLog.timestamp.desc())
    
    if level:
        query = query.filter(SystemLog.level == level.upper())
    if component:
        query = query.filter(SystemLog.component == component)
        
    logs = query.limit(limit).all()
    
    return {
        "logs": [log.to_dict() for log in logs],
        "total": query.count()
    }

@router.get("/stats")
async def get_pipeline_stats(
    days: int = 30,
    db: Session = Depends(get_database)
):
    """Get pipeline statistics"""
    pipeline_manager = get_pipeline_manager()
    
    # Get database stats
    total_videos = db.query(Video).count()
    uploaded_videos = db.query(Video).filter(Video.youtube_video_id.isnot(None)).count()
    failed_videos = db.query(Video).filter(Video.status == "failed").count()
    
    # Calculate success rate
    success_rate = (uploaded_videos / total_videos * 100) if total_videos > 0 else 0
    
    return {
        "total_videos": total_videos,
        "uploaded_videos": uploaded_videos,
        "failed_videos": failed_videos,
        "success_rate": round(success_rate, 2),
        "pipeline_stats": pipeline_manager.get_stats(),
        "uptime": pipeline_manager.get_uptime()
    }

@router.post("/config/update")
async def update_pipeline_config(config: Dict[str, Any]):
    """Update pipeline configuration"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        await pipeline_manager.update_config(config)
        return {"status": "success", "message": "Configuration updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")

@router.get("/config")
async def get_pipeline_config():
    """Get current pipeline configuration"""
    pipeline_manager = get_pipeline_manager()
    
    return {
        "config": pipeline_manager.get_config(),
        "defaults": pipeline_manager.get_default_config()
    }

@router.post("/test")
async def test_pipeline_components():
    """Test pipeline components (YouTube API, file system, etc.)"""
    pipeline_manager = get_pipeline_manager()
    
    try:
        results = await pipeline_manager.test_components()
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Component test failed: {str(e)}")

# Health check for pipeline specifically
@router.get("/health")
async def pipeline_health():
    """Pipeline health check endpoint"""
    pipeline_manager = get_pipeline_manager()
    
    health_status = {
        "status": "healthy",
        "pipeline_running": pipeline_manager.is_running(),
        "queue_size": pipeline_manager.get_queue_size(),
        "active_jobs": len(pipeline_manager.get_active_jobs()),
        "last_activity": pipeline_manager.get_last_activity(),
        "uptime": pipeline_manager.get_uptime()
    }
    
    # Determine overall health
    if not pipeline_manager.is_running() and pipeline_manager.get_queue_size() > 0:
        health_status["status"] = "warning"
        health_status["message"] = "Pipeline stopped but queue has pending jobs"
    
    return health_status