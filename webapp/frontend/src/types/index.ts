export interface PipelineStatus {
  active: boolean;
  last_run: string | null;
  videos_processed: number;
  status: 'stopped' | 'running' | 'error';
}

export interface VideoFile {
  name: string;
  size?: number;
  created_at?: string;
  status?: 'pending' | 'processing' | 'completed' | 'error';
}

export interface AIJob {
  job_id: string;
  status: 'starting' | 'generating' | 'processing' | 'rendering' | 'completed' | 'failed' | 'error';
  prompt?: string;
  base_prompt: string;
  orientation: string;
  duration: string;
  style: string;
  camera_view: string;
  background: string;
  lighting?: string;
  color_palette?: string;
  weather?: string;
  time_of_day?: string;
  additional_details?: string;
  started_at: string;
  completed_at?: string;
  error?: string;
  versions?: Array<{
    id: string;
    status: string;
    url?: string;
  }>;
  selected_version?: number;
  video?: {
    success: boolean;
    filename?: string;
    filepath?: string;
    duration?: number;
    resolution?: string;
    format?: string;
    generated_at?: string;
    mock_mode?: boolean;
  };
  metadata?: {
    title: string;
    description: string;
    tags: string[];
    category: string;
  };
  thumbnail?: string;
  duration_seconds?: number;
}

export interface AIStatus {
  openai_available: boolean;
  pil_available: boolean;
  sora_enabled: boolean;
  gpt_enabled: boolean;
  dalle_enabled: boolean;
  config_loaded: boolean;
  error?: string;
}

export interface WebSocketMessage {
  type: 'status' | 'log' | 'ai_job';
  data?: any;
  job_id?: string;
  status?: string;
  message?: string;
  result?: any;
}

export interface GenerationRequest {
  base_prompt: string;
  orientation: 'portrait' | 'landscape';
  duration: '4s' | '10s' | '15s';
  style: 'cinematic' | 'realistic' | 'animated' | 'documentary' | 'artistic' | 'vintage';
  camera_view: 'wide' | 'close-up' | 'aerial' | 'pov' | 'tracking' | 'static';
  background: 'natural' | 'urban' | 'studio' | 'abstract' | 'minimal';
  lighting?: string;
  color_palette?: string;
  weather?: string;
  time_of_day?: string;
  additional_details?: string;
}

export interface PromptEnhanceRequest {
  prompt: string;
}

export interface PromptEnhanceResponse {
  success: boolean;
  original_prompt: string;
  enhanced_prompt: string;
}

export interface VideoMetadata {
  title: string;
  description: string;
  tags: string[];
  category: string;
  privacy?: 'public' | 'unlisted' | 'private';
}

export interface UploadProgress {
  stage: 'uploading' | 'processing' | 'completed' | 'error';
  percent: number;
  message: string;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  created_at: string;
  subscription_tier?: 'free' | 'pro' | 'enterprise';
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface ContentTemplate {
  id: string;
  name: string;
  prompt_template: string;
  style: string;
  metadata_template: VideoMetadata;
  created_at: string;
  updated_at: string;
  usage_count: number;
}

export interface ScheduledJob {
  id: string;
  template_id: string;
  template_name: string;
  prompt: string;
  scheduled_for: string;
  status: 'scheduled' | 'running' | 'completed' | 'failed';
  created_at: string;
  completed_at?: string;
  result?: AIJob;
}

export interface Analytics {
  total_videos_generated: number;
  total_videos_uploaded: number;
  success_rate: number;
  avg_generation_time: number;
  popular_styles: Array<{
    style: string;
    count: number;
  }>;
  recent_activity: Array<{
    date: string;
    videos_generated: number;
    videos_uploaded: number;
  }>;
}

export interface APIResponse<T = any> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}