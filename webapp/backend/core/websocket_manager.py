"""
WebSocket Manager for Real-time Updates
"""

import json
import asyncio
from typing import Dict, Set, List, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

class WebSocketManager:
    """Manages WebSocket connections and real-time updates"""
    
    def __init__(self):
        # Store active connections
        self.connections: Set[WebSocket] = set()
        
        # Channel subscriptions
        self.subscriptions: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.connections.add(websocket)
        
        # Store connection info
        self.connection_info[websocket] = {
            "connected_at": datetime.now(),
            "last_activity": datetime.now(),
            "subscriptions": set()
        }
        
        # Send welcome message
        await self.send_personal_message(websocket, {
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to YouTube Automation Pipeline"
        })
        
        print(f"WebSocket connected. Total connections: {len(self.connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.connections:
            self.connections.remove(websocket)
            
            # Remove from all subscriptions
            if websocket in self.connection_info:
                subscriptions = self.connection_info[websocket].get("subscriptions", set())
                for channel in subscriptions:
                    if channel in self.subscriptions:
                        self.subscriptions[channel].discard(websocket)
                        
                # Clean up empty channels
                empty_channels = [
                    channel for channel, subs in self.subscriptions.items() 
                    if not subs
                ]
                for channel in empty_channels:
                    del self.subscriptions[channel]
                    
                # Remove connection info
                del self.connection_info[websocket]
                
        print(f"WebSocket disconnected. Total connections: {len(self.connections)}")
    
    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe a connection to a specific channel"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
            
        self.subscriptions[channel].add(websocket)
        
        # Update connection info
        if websocket in self.connection_info:
            self.connection_info[websocket]["subscriptions"].add(channel)
            
        await self.send_personal_message(websocket, {
            "type": "subscription",
            "channel": channel,
            "status": "subscribed",
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"WebSocket subscribed to channel '{channel}'. Channel subscribers: {len(self.subscriptions[channel])}")
    
    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe a connection from a channel"""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(websocket)
            
            # Update connection info
            if websocket in self.connection_info:
                self.connection_info[websocket]["subscriptions"].discard(channel)
                
            # Clean up empty channel
            if not self.subscriptions[channel]:
                del self.subscriptions[channel]
                
        await self.send_personal_message(websocket, {
            "type": "subscription", 
            "channel": channel,
            "status": "unsubscribed",
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Send message to a specific WebSocket connection"""
        try:
            if websocket in self.connections:
                await websocket.send_json(message)
                
                # Update last activity
                if websocket in self.connection_info:
                    self.connection_info[websocket]["last_activity"] = datetime.now()
                    
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.connections:
            return
            
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
            
        # Send to all connections
        disconnected = set()
        
        for websocket in self.connections.copy():
            try:
                await websocket.send_json(message)
                
                # Update last activity
                if websocket in self.connection_info:
                    self.connection_info[websocket]["last_activity"] = datetime.now()
                    
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                print(f"Error broadcasting to websocket: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """Broadcast message to all subscribers of a specific channel"""
        if channel not in self.subscriptions:
            return
            
        # Add timestamp and channel info
        message.update({
            "timestamp": datetime.now().isoformat(),
            "channel": channel
        })
        
        disconnected = set()
        subscribers = self.subscriptions[channel].copy()
        
        for websocket in subscribers:
            try:
                await websocket.send_json(message)
                
                # Update last activity
                if websocket in self.connection_info:
                    self.connection_info[websocket]["last_activity"] = datetime.now()
                    
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                print(f"Error broadcasting to channel subscriber: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected websockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    # Convenience methods for different message types
    async def send_pipeline_status(self, status: Dict[str, Any]):
        """Send pipeline status update"""
        message = {
            "type": "pipeline_status",
            "data": status
        }
        await self.broadcast_to_channel("pipeline", message)
    
    async def send_video_update(self, video_id: int, video_data: Dict[str, Any]):
        """Send video status update"""
        message = {
            "type": "video_update",
            "video_id": video_id,
            "data": video_data
        }
        await self.broadcast_to_channel("videos", message)
    
    async def send_upload_progress(self, video_id: int, progress: float, status: str = "uploading"):
        """Send upload progress update"""
        message = {
            "type": "upload_progress",
            "video_id": video_id,
            "progress": progress,
            "status": status
        }
        await self.broadcast_to_channel("uploads", message)
    
    async def send_generation_progress(self, video_id: int, progress: float, status: str = "generating"):
        """Send video generation progress update"""
        message = {
            "type": "generation_progress",
            "video_id": video_id,
            "progress": progress,
            "status": status
        }
        await self.broadcast_to_channel("generation", message)
    
    async def send_error(self, error_type: str, message: str, details: Dict[str, Any] = None):
        """Send error notification"""
        error_message = {
            "type": "error",
            "error_type": error_type,
            "message": message,
            "details": details or {}
        }
        await self.broadcast(error_message)
    
    async def send_notification(self, title: str, message: str, level: str = "info"):
        """Send general notification"""
        notification = {
            "type": "notification",
            "title": title,
            "message": message,
            "level": level  # info, warning, error, success
        }
        await self.broadcast(notification)
    
    # Statistics and monitoring
    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.connections)
    
    def get_channel_subscribers(self, channel: str) -> int:
        """Get number of subscribers for a channel"""
        return len(self.subscriptions.get(channel, set()))
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.connections),
            "channels": {
                channel: len(subscribers) 
                for channel, subscribers in self.subscriptions.items()
            },
            "active_channels": len(self.subscriptions)
        }

# Global WebSocket manager instance
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager