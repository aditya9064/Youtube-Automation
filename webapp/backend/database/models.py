"""
Database Models for YouTube Automation Pipeline
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum as PyEnum
import uuid

Base = declarative_base()

class VideoStatus(PyEnum):
    PENDING = "pending"
    GENERATING = "generating" 
    GENERATED = "generated"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    FAILED = "failed"
    PROCESSING = "processing"

class UploadStatus(PyEnum):
    QUEUED = "queued"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"

class Video(Base):
    """Video model for tracking generated and uploaded videos"""
    __tablename__ = "videos"
    
    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    # Video metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500))
    file_size = Column(Integer)  # in bytes
    duration = Column(Float)  # in seconds
    
    # Generation info
    prompt = Column(Text)
    ai_model = Column(String(100), default="sora")
    generation_parameters = Column(JSON)
    
    # Upload info
    youtube_video_id = Column(String(20), unique=True, index=True)
    youtube_url = Column(String(255))
    upload_status = Column(String(20), default=UploadStatus.QUEUED.value)
    
    # Status and tracking
    status = Column(String(20), default=VideoStatus.PENDING.value)
    progress = Column(Float, default=0.0)  # 0-100
    error_message = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    generated_at = Column(DateTime(timezone=True))
    uploaded_at = Column(DateTime(timezone=True))
    
    # Analytics
    analytics = relationship("VideoAnalytics", back_populates="video", uselist=False)
    
    def to_dict(self):
        return {
            "id": self.id,
            "uuid": self.uuid,
            "title": self.title,
            "description": self.description,
            "filename": self.filename,
            "file_size": self.file_size,
            "duration": self.duration,
            "prompt": self.prompt,
            "ai_model": self.ai_model,
            "youtube_video_id": self.youtube_video_id,
            "youtube_url": self.youtube_url,
            "status": self.status,
            "upload_status": self.upload_status,
            "progress": self.progress,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }

class VideoAnalytics(Base):
    """Analytics data for uploaded videos"""
    __tablename__ = "video_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), unique=True)
    
    # YouTube metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    subscribers_gained = Column(Integer, default=0)
    
    # Performance metrics
    click_through_rate = Column(Float, default=0.0)
    average_view_duration = Column(Float, default=0.0)
    watch_time_minutes = Column(Float, default=0.0)
    
    # Revenue (if monetized)
    estimated_revenue = Column(Float, default=0.0)
    
    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    video = relationship("Video", back_populates="analytics")

class Pipeline(Base):
    """Pipeline execution tracking"""
    __tablename__ = "pipelines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(String(50), default="idle")  # idle, running, paused, stopped
    
    # Configuration
    config = Column(JSON)
    
    # Statistics
    videos_generated = Column(Integer, default=0)
    videos_uploaded = Column(Integer, default=0)
    total_views = Column(Integer, default=0)
    total_revenue = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    stopped_at = Column(DateTime(timezone=True))
    last_activity = Column(DateTime(timezone=True))

class Configuration(Base):
    """System configuration settings"""
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSON)
    description = Column(Text)
    
    # Metadata
    category = Column(String(100))  # youtube, ai, pipeline, etc.
    is_sensitive = Column(Boolean, default=False)  # for API keys
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class SystemLog(Base):
    """System logs and events"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    component = Column(String(100))  # pipeline, uploader, generator, etc.
    
    # Context
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=True)
    extra_data = Column(JSON)
    
    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "component": self.component,
            "video_id": self.video_id,
            "extra_data": self.extra_data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }

class PromptTemplate(Base):
    """AI prompt templates for video generation"""
    __tablename__ = "prompt_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    template = Column(Text, nullable=False)
    category = Column(String(100))
    tags = Column(JSON)  # List of tags
    
    # Usage statistics
    usage_count = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Metadata
    created_by = Column(String(255))
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Initialize database
async def init_db():
    """Initialize database tables"""
    from .connection import engine
    
    # Import all models to ensure they're registered
    import sys
    current_module = sys.modules[__name__]
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database initialized successfully!")

# Export models
__all__ = [
    "Base",
    "Video",
    "VideoAnalytics", 
    "Pipeline",
    "Configuration",
    "SystemLog",
    "PromptTemplate",
    "VideoStatus",
    "UploadStatus",
    "init_db"
]