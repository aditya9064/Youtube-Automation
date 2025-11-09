import { useEffect, useRef, useCallback } from 'react';
import { useAppStore } from '../store';
import { WebSocketMessage, AIJob } from '../types';
import { toast } from 'react-hot-toast';

const WS_URL = 'ws://127.0.0.1:8000/ws';
const RECONNECT_INTERVAL = 5000;
const MAX_RECONNECT_ATTEMPTS = 10;

export const useWebSocket = () => {
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<number | null>(null);
  
  const {
    setWsConnected,
    setPipelineStatus,
    addAIJob,
    updateAIJob,
  } = useAppStore();

  const connect = useCallback(() => {
    try {
      ws.current = new WebSocket(WS_URL);
      
      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setWsConnected(true);
        reconnectAttempts.current = 0;
        
        if (reconnectTimeout.current) {
          clearTimeout(reconnectTimeout.current);
          reconnectTimeout.current = null;
        }
      };
      
      ws.current.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setWsConnected(false);
        
        // Attempt to reconnect
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current += 1;
          console.log(`Attempting to reconnect (${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`);
          
          reconnectTimeout.current = window.setTimeout(() => {
            connect();
          }, RECONNECT_INTERVAL);
        } else {
          toast.error('WebSocket connection failed. Please refresh the page.');
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
      
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setWsConnected(false);
    }
  }, [setWsConnected]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'status':
        if (message.data) {
          setPipelineStatus(message.data);
        }
        break;
        
      case 'log':
        if (message.message) {
          // Show as toast notification
          if (message.message.includes('error') || message.message.includes('failed')) {
            toast.error(message.message);
          } else if (message.message.includes('success') || message.message.includes('completed')) {
            toast.success(message.message);
          } else {
            toast(message.message);
          }
        }
        break;
        
      case 'ai_job':
        if (message.job_id && message.status) {
          // Check if job exists, if not add it
          const existingJob = useAppStore.getState().aiJobs.find(
            job => job.job_id === message.job_id
          );
          
          if (!existingJob && message.status === 'starting') {
            // Add new job
            const newJob: AIJob = {
              job_id: message.job_id || '',
              status: 'starting',
              base_prompt: message.result?.prompt || '',
              prompt: message.result?.prompt || '',
              orientation: message.result?.orientation || 'landscape',
              duration: message.result?.duration || '10s',
              style: message.result?.style || 'cinematic',
              camera_view: message.result?.camera_view || 'wide',
              background: message.result?.background || 'natural',
              started_at: new Date().toISOString(),
            };
            addAIJob(newJob);
          } else {
            // Update existing job
            const updates: any = {
              status: message.status,
            };
            
            if (message.result) {
              Object.assign(updates, message.result);
            }
            
            updateAIJob(message.job_id, updates);
          }
          
          // Show notification for important status updates
          if (message.message) {
            if (message.status === 'completed') {
              toast.success(message.message);
            } else if (message.status === 'failed' || message.status === 'error') {
              toast.error(message.message);
            } else if (message.status === 'starting') {
              toast(message.message);
            }
          }
        }
        break;
        
      default:
        console.log('Unknown message type:', message);
    }
  }, [setPipelineStatus, addAIJob, updateAIJob]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    
    setWsConnected(false);
  }, [setWsConnected]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    sendMessage,
    disconnect,
    reconnect: connect,
  };
};