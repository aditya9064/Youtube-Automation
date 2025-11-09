"""
Pipeline Manager - Core automation orchestration
"""

import asyncio
import time
import json
import os
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uuid
from enum import Enum

# Add parent directories to path for importing automation modules
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.video_uploader import VideoUploader
from src.file_monitor import VideoMonitor
from src.config_manager import ConfigManager
from core.websocket_manager import WebSocketManager

class PipelineStatus(Enum):
    IDLE = "idle"
    RUNNING = "running" 
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"

class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Job:
    """Represents a pipeline job"""
    
    def __init__(self, job_id: str, job_type: str, data: Dict[str, Any], priority: int = 0):
        self.job_id = job_id
        self.job_type = job_type
        self.data = data
        self.priority = priority
        self.status = JobStatus.QUEUED
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.progress = 0.0
        self.result = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "data": self.data,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "progress": self.progress,
            "result": self.result
        }

class PipelineManager:
    """Main pipeline orchestration manager"""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager
        self.status = PipelineStatus.IDLE
        self.started_at = None
        self.stopped_at = None
        
        # Job management
        self.job_queue: List[Job] = []
        self.active_jobs: Dict[str, Job] = {}
        self.completed_jobs: List[Job] = []
        self.max_concurrent_jobs = 3
        
        # Components
        self.config_manager = ConfigManager()
        self.video_uploader = VideoUploader()
        self.file_monitor = None
        
        # Statistics
        self.stats = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "videos_uploaded": 0,
            "total_processing_time": 0,
            "last_activity": None
        }
        
        # Background tasks
        self.main_task = None
        self.monitor_task = None
        
    async def start(self) -> bool:
        """Start the pipeline"""
        if self.status == PipelineStatus.RUNNING:
            return False
            
        try:
            self.status = PipelineStatus.RUNNING
            self.started_at = datetime.now()
            self.stopped_at = None
            
            # Start main processing loop
            self.main_task = asyncio.create_task(self._main_loop())
            
            # Start monitoring task
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            # Notify via WebSocket
            await self.websocket_manager.send_pipeline_status({
                "status": self.status.value,
                "started_at": self.started_at.isoformat(),
                "message": "Pipeline started successfully"
            })
            
            print(f"Pipeline started at {self.started_at}")
            return True
            
        except Exception as e:
            self.status = PipelineStatus.ERROR
            print(f"Failed to start pipeline: {e}")
            
            await self.websocket_manager.send_error(
                "pipeline_start_error",
                f"Failed to start pipeline: {str(e)}"
            )
            return False
    
    async def stop(self) -> bool:
        """Stop the pipeline"""
        if self.status not in [PipelineStatus.RUNNING, PipelineStatus.PAUSED]:
            return False
            
        try:
            self.status = PipelineStatus.STOPPING
            self.stopped_at = datetime.now()
            
            # Cancel running tasks
            if self.main_task and not self.main_task.done():
                self.main_task.cancel()
                
            if self.monitor_task and not self.monitor_task.done():
                self.monitor_task.cancel()
                
            # Wait for active jobs to complete or cancel them
            for job in self.active_jobs.values():
                job.status = JobStatus.CANCELLED
                
            self.status = PipelineStatus.IDLE
            
            # Notify via WebSocket
            await self.websocket_manager.send_pipeline_status({
                "status": self.status.value,
                "stopped_at": self.stopped_at.isoformat(),
                "message": "Pipeline stopped successfully"
            })
            
            print(f"Pipeline stopped at {self.stopped_at}")
            return True
            
        except Exception as e:
            self.status = PipelineStatus.ERROR
            print(f"Failed to stop pipeline: {e}")
            return False
    
    async def pause(self) -> bool:
        """Pause the pipeline"""
        if self.status != PipelineStatus.RUNNING:
            return False
            
        self.status = PipelineStatus.PAUSED
        
        await self.websocket_manager.send_pipeline_status({
            "status": self.status.value,
            "message": "Pipeline paused"
        })
        
        return True
    
    async def resume(self) -> bool:
        """Resume the pipeline"""
        if self.status != PipelineStatus.PAUSED:
            return False
            
        self.status = PipelineStatus.RUNNING
        
        await self.websocket_manager.send_pipeline_status({
            "status": self.status.value,
            "message": "Pipeline resumed"
        })
        
        return True
    
    async def add_job(self, job_type: str, video_id: int = None, data: Dict[str, Any] = None, priority: int = 0) -> str:
        """Add a job to the queue"""
        job_id = str(uuid.uuid4())
        
        job_data = data or {}
        if video_id:
            job_data["video_id"] = video_id
            
        job = Job(job_id, job_type, job_data, priority)
        
        # Insert job based on priority (higher priority first)
        inserted = False
        for i, queued_job in enumerate(self.job_queue):
            if job.priority > queued_job.priority:
                self.job_queue.insert(i, job)
                inserted = True
                break
                
        if not inserted:
            self.job_queue.append(job)
            
        # Notify via WebSocket
        await self.websocket_manager.broadcast({
            "type": "job_added",
            "job": job.to_dict(),
            "queue_size": len(self.job_queue)
        })
        
        print(f"Added job {job_id} ({job_type}) to queue with priority {priority}")
        return job_id
    
    async def remove_job(self, job_id: str) -> bool:
        """Remove a job from the queue"""
        # Check queue
        for i, job in enumerate(self.job_queue):
            if job.job_id == job_id:
                removed_job = self.job_queue.pop(i)
                
                await self.websocket_manager.broadcast({
                    "type": "job_removed",
                    "job_id": job_id,
                    "queue_size": len(self.job_queue)
                })
                
                return True
                
        # Check active jobs
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = JobStatus.CANCELLED
            
            await self.websocket_manager.broadcast({
                "type": "job_cancelled",
                "job_id": job_id
            })
            
            return True
            
        return False
    
    async def _main_loop(self):
        """Main processing loop"""
        while self.status in [PipelineStatus.RUNNING, PipelineStatus.PAUSED]:
            try:
                # Skip processing if paused
                if self.status == PipelineStatus.PAUSED:
                    await asyncio.sleep(1)
                    continue
                
                # Process jobs if there's capacity
                if len(self.active_jobs) < self.max_concurrent_jobs and self.job_queue:
                    job = self.job_queue.pop(0)
                    await self._start_job(job)
                
                # Clean up completed jobs
                completed_job_ids = []
                for job_id, job in self.active_jobs.items():
                    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                        completed_job_ids.append(job_id)
                
                for job_id in completed_job_ids:
                    completed_job = self.active_jobs.pop(job_id)
                    self.completed_jobs.append(completed_job)
                    
                    # Update statistics
                    if completed_job.status == JobStatus.COMPLETED:
                        self.stats["jobs_processed"] += 1
                        if completed_job.job_type == "upload_video":
                            self.stats["videos_uploaded"] += 1
                    elif completed_job.status == JobStatus.FAILED:
                        self.stats["jobs_failed"] += 1
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in main loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _monitor_loop(self):
        """Monitoring and status update loop"""
        while self.status in [PipelineStatus.RUNNING, PipelineStatus.PAUSED]:
            try:
                # Send periodic status updates
                await self.websocket_manager.send_pipeline_status({
                    "status": self.status.value,
                    "queue_size": len(self.job_queue),
                    "active_jobs": len(self.active_jobs),
                    "stats": self.stats,
                    "uptime": self.get_uptime()
                })
                
                # Update last activity
                if self.job_queue or self.active_jobs:
                    self.stats["last_activity"] = datetime.now().isoformat()
                
                await asyncio.sleep(5)  # Update every 5 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                await asyncio.sleep(10)
    
    async def _start_job(self, job: Job):
        """Start processing a job"""
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now()
        self.active_jobs[job.job_id] = job
        
        # Notify job started
        await self.websocket_manager.broadcast({
            "type": "job_started",
            "job": job.to_dict()
        })
        
        # Create task for job processing
        task = asyncio.create_task(self._process_job(job))
        
    async def _process_job(self, job: Job):
        """Process a specific job"""
        try:
            if job.job_type == "generate_video":
                await self._process_video_generation(job)
            elif job.job_type == "upload_video":
                await self._process_video_upload(job)
            elif job.job_type == "process_existing_video":
                await self._process_existing_video(job)
            else:
                raise ValueError(f"Unknown job type: {job.job_type}")
                
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now()
            
            print(f"Job {job.job_id} failed: {e}")
            
            await self.websocket_manager.send_error(
                "job_processing_error",
                f"Job {job.job_id} failed: {str(e)}",
                {"job_id": job.job_id, "job_type": job.job_type}
            )
        
        # Notify job completed
        await self.websocket_manager.broadcast({
            "type": "job_completed",
            "job": job.to_dict()
        })
    
    async def _process_video_generation(self, job: Job):
        """Process video generation job (placeholder for Sora AI integration)"""
        # This is a placeholder for future Sora AI integration
        video_id = job.data.get("video_id")
        prompt = job.data.get("prompt", "")
        
        # Simulate video generation progress
        for progress in range(0, 101, 10):
            job.progress = progress
            
            await self.websocket_manager.send_generation_progress(
                video_id, progress, "generating"
            )
            
            await asyncio.sleep(2)  # Simulate processing time
        
        # For now, we'll just mark as completed
        # In the future, this would call Sora AI API
        job.result = {
            "status": "generated",
            "message": "Video generation completed (simulated)",
            "file_path": f"videos/input/generated_{video_id}.mp4"
        }
    
    async def _process_video_upload(self, job: Job):
        """Process video upload job"""
        video_id = job.data.get("video_id")
        file_path = job.data.get("file_path")
        
        if not file_path or not Path(file_path).exists():
            raise ValueError(f"Video file not found: {file_path}")
        
        # Upload video using existing uploader
        result = self.video_uploader.upload_video(
            file_path,
            job.data.get("metadata")
        )
        
        if result and result.get("success"):
            job.result = result
            
            # Move file to processed folder
            self.video_uploader.move_processed_file(file_path)
            
            # Notify upload success
            await self.websocket_manager.send_video_update(video_id, {
                "status": "uploaded",
                "youtube_url": result.get("video_url"),
                "youtube_video_id": result.get("video_id")
            })
        else:
            raise Exception("Video upload failed")
    
    async def _process_existing_video(self, job: Job):
        """Process an existing video file"""
        file_path = job.data.get("file_path")
        
        if not file_path or not Path(file_path).exists():
            raise ValueError(f"Video file not found: {file_path}")
        
        # Add upload job for the existing video
        await self.add_job(
            "upload_video",
            video_id=job.data.get("video_id"),
            data={
                "file_path": file_path,
                "metadata": job.data.get("metadata")
            }
        )
    
    # Status and utility methods
    def is_running(self) -> bool:
        return self.status == PipelineStatus.RUNNING
    
    def get_status(self) -> str:
        return self.status.value
    
    def get_queue_size(self) -> int:
        return len(self.job_queue)
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        return [job.to_dict() for job in self.active_jobs.values()]
    
    def get_queue(self) -> List[Dict[str, Any]]:
        return [job.to_dict() for job in self.job_queue]
    
    def get_stats(self) -> Dict[str, Any]:
        return self.stats.copy()
    
    def get_last_activity(self) -> Optional[str]:
        return self.stats.get("last_activity")
    
    def get_uptime(self) -> Optional[float]:
        if self.started_at and self.status == PipelineStatus.RUNNING:
            return (datetime.now() - self.started_at).total_seconds()
        return None
    
    def get_config(self) -> Dict[str, Any]:
        return self.config_manager.config
    
    def get_default_config(self) -> Dict[str, Any]:
        return self.config_manager.get_default_config()
    
    async def update_config(self, config: Dict[str, Any]):
        """Update pipeline configuration"""
        # Update configuration
        for key, value in config.items():
            if hasattr(self.config_manager, key):
                setattr(self.config_manager, key, value)
        
        # Save configuration
        self.config_manager.save_config()
        
        # Notify configuration updated
        await self.websocket_manager.broadcast({
            "type": "config_updated",
            "config": self.get_config()
        })
    
    async def test_components(self) -> Dict[str, Any]:
        """Test pipeline components"""
        results = {}
        
        # Test YouTube API
        try:
            youtube_test = self.video_uploader.youtube_api.test_connection()
            results["youtube_api"] = {"status": "success" if youtube_test else "failed"}
        except Exception as e:
            results["youtube_api"] = {"status": "error", "error": str(e)}
        
        # Test file system
        try:
            paths = self.config_manager.get_paths()
            for name, path in paths.items():
                path.mkdir(parents=True, exist_ok=True)
            results["file_system"] = {"status": "success"}
        except Exception as e:
            results["file_system"] = {"status": "error", "error": str(e)}
        
        # Test configuration
        try:
            valid, missing = self.config_manager.validate_credentials()
            results["configuration"] = {
                "status": "success" if valid else "warning",
                "missing_credentials": missing if not valid else []
            }
        except Exception as e:
            results["configuration"] = {"status": "error", "error": str(e)}
        
        return results

# Global pipeline manager instance
_pipeline_manager = None

def get_pipeline_manager() -> PipelineManager:
    """Get the global pipeline manager instance"""
    global _pipeline_manager
    if _pipeline_manager is None:
        from core.websocket_manager import get_websocket_manager
        websocket_manager = get_websocket_manager()
        _pipeline_manager = PipelineManager(websocket_manager)
    return _pipeline_manager