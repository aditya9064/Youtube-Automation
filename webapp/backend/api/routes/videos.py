"""
Videos API Routes - Video management and upload operations
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import os

from database.connection import get_database
from database.models import Video, VideoAnalytics
from core.pipeline_manager import get_pipeline_manager

router = APIRouter()

@router.get("/", response_model=List[Dict[str, Any]])
async def get_videos(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_database)
):
    """Get list of videos with optional filtering"""
    query = db.query(Video).order_by(Video.created_at.desc())
    
    if status:
        query = query.filter(Video.status == status)
    
    videos = query.offset(offset).limit(limit).all()
    
    return {
        "videos": [video.to_dict() for video in videos],
        "total": query.count(),
        "limit": limit,
        "offset": offset
    }

@router.get("/{video_id}", response_model=Dict[str, Any])
async def get_video(video_id: int, db: Session = Depends(get_database)):
    """Get specific video details"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_data = video.to_dict()
    
    # Include analytics if available
    if video.analytics:
        video_data["analytics"] = {
            "views": video.analytics.views,
            "likes": video.analytics.likes,
            "comments": video.analytics.comments,
            "watch_time": video.analytics.watch_time_minutes,
            "ctr": video.analytics.click_through_rate
        }
    
    return video_data

@router.post("/upload", response_model=Dict[str, Any])
async def upload_video_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    prompt: Optional[str] = Form(None),
    db: Session = Depends(get_database)
):
    """Upload a video file and add to processing queue"""
    
    # Validate file type
    if not file.filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Supported: mp4, mov, avi, mkv, webm"
        )
    
    try:
        # Create video record
        video = Video(
            title=title or file.filename,
            description=description or "",
            filename=file.filename,
            prompt=prompt or "",
            status="pending"
        )
        
        db.add(video)
        db.commit()
        db.refresh(video)
        
        # Save uploaded file
        upload_dir = Path("videos/input")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / f"{video.id}_{file.filename}"
        
        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Update video record with file info
        video.file_path = str(file_path)
        video.file_size = len(content)
        db.commit()
        
        # Add to processing queue
        pipeline_manager = get_pipeline_manager()
        job_id = await pipeline_manager.add_job(
            job_type="upload_video",
            video_id=video.id,
            data={
                "file_path": str(file_path),
                "metadata": {
                    "title": video.title,
                    "description": video.description
                }
            }
        )
        
        return {
            "status": "success",
            "message": "Video uploaded and queued for processing",
            "video_id": video.id,
            "job_id": job_id,
            "file_path": str(file_path)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.put("/{video_id}", response_model=Dict[str, Any])
async def update_video(
    video_id: int,
    video_data: Dict[str, Any],
    db: Session = Depends(get_database)
):
    """Update video metadata"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Update allowed fields
    updateable_fields = ['title', 'description', 'prompt']
    for field in updateable_fields:
        if field in video_data:
            setattr(video, field, video_data[field])
    
    video.updated_at = datetime.now()
    db.commit()
    
    return {
        "status": "success",
        "message": "Video updated successfully",
        "video": video.to_dict()
    }

@router.delete("/{video_id}")
async def delete_video(video_id: int, db: Session = Depends(get_database)):
    """Delete a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    try:
        # Delete file if exists
        if video.file_path and Path(video.file_path).exists():
            os.remove(video.file_path)
        
        # Delete from database
        db.delete(video)
        db.commit()
        
        return {
            "status": "success",
            "message": "Video deleted successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/{video_id}/retry")
async def retry_video_upload(video_id: int, db: Session = Depends(get_database)):
    """Retry uploading a failed video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if video.status not in ['failed', 'pending']:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot retry video with status: {video.status}"
        )
    
    # Reset video status
    video.status = "pending"
    video.error_message = None
    video.updated_at = datetime.now()
    db.commit()
    
    # Add to queue again
    pipeline_manager = get_pipeline_manager()
    job_id = await pipeline_manager.add_job(
        job_type="upload_video",
        video_id=video.id,
        data={
            "file_path": video.file_path,
            "metadata": {
                "title": video.title,
                "description": video.description
            }
        },
        priority=5  # Higher priority for retries
    )
    
    return {
        "status": "success",
        "message": "Video queued for retry",
        "job_id": job_id
    }

@router.get("/{video_id}/analytics", response_model=Dict[str, Any])
async def get_video_analytics(video_id: int, db: Session = Depends(get_database)):
    """Get detailed analytics for a video"""
    video = db.query(Video).filter(Video.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    if not video.analytics:
        return {
            "video_id": video_id,
            "message": "No analytics data available",
            "analytics": None
        }
    
    analytics = video.analytics
    return {
        "video_id": video_id,
        "analytics": {
            "views": analytics.views,
            "likes": analytics.likes,
            "dislikes": analytics.dislikes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "subscribers_gained": analytics.subscribers_gained,
            "click_through_rate": analytics.click_through_rate,
            "average_view_duration": analytics.average_view_duration,
            "watch_time_minutes": analytics.watch_time_minutes,
            "estimated_revenue": analytics.estimated_revenue,
            "last_updated": analytics.last_updated.isoformat() if analytics.last_updated else None
        }
    }

@router.post("/batch-upload")
async def batch_upload_from_folder(
    folder_path: str,
    db: Session = Depends(get_database)
):
    """Process all videos in a folder for upload"""
    folder = Path(folder_path)
    
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder path")
    
    # Find video files
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    video_files = []
    
    for ext in video_extensions:
        video_files.extend(folder.glob(f"*{ext}"))
        video_files.extend(folder.glob(f"*{ext.upper()}"))
    
    if not video_files:
        return {
            "status": "warning",
            "message": "No video files found in folder",
            "processed": 0
        }
    
    processed_videos = []
    pipeline_manager = get_pipeline_manager()
    
    for video_file in video_files:
        try:
            # Create video record
            video = Video(
                title=video_file.stem.replace('_', ' ').title(),
                filename=video_file.name,
                file_path=str(video_file),
                file_size=video_file.stat().st_size,
                status="pending"
            )
            
            db.add(video)
            db.commit()
            db.refresh(video)
            
            # Add to processing queue
            job_id = await pipeline_manager.add_job(
                job_type="upload_video",
                video_id=video.id,
                data={
                    "file_path": str(video_file),
                    "metadata": {
                        "title": video.title
                    }
                }
            )
            
            processed_videos.append({
                "video_id": video.id,
                "filename": video.filename,
                "job_id": job_id
            })
            
        except Exception as e:
            print(f"Error processing {video_file}: {e}")
            continue
    
    return {
        "status": "success",
        "message": f"Processed {len(processed_videos)} videos from folder",
        "processed": len(processed_videos),
        "total_found": len(video_files),
        "videos": processed_videos
    }

@router.get("/stats/summary")
async def get_video_stats(db: Session = Depends(get_database)):
    """Get video statistics summary"""
    
    # Basic counts
    total_videos = db.query(Video).count()
    uploaded_videos = db.query(Video).filter(Video.youtube_video_id.isnot(None)).count()
    failed_videos = db.query(Video).filter(Video.status == "failed").count()
    pending_videos = db.query(Video).filter(Video.status.in_(["pending", "generating", "uploading"])).count()
    
    # Recent activity (last 7 days)
    week_ago = datetime.now() - timedelta(days=7)
    recent_uploads = db.query(Video).filter(
        Video.uploaded_at >= week_ago
    ).count()
    
    # Calculate success rate
    success_rate = (uploaded_videos / total_videos * 100) if total_videos > 0 else 0
    
    return {
        "total_videos": total_videos,
        "uploaded_videos": uploaded_videos,
        "failed_videos": failed_videos,
        "pending_videos": pending_videos,
        "recent_uploads": recent_uploads,
        "success_rate": round(success_rate, 2),
        "stats_generated_at": datetime.now().isoformat()
    }