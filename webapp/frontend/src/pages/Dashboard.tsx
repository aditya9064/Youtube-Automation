import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Play, 
  Square, 
  Activity, 
  Video, 
  Sparkles, 
  TrendingUp,
  Clock,
  CheckCircle,
  AlertCircle,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useAppStore, usePipelineStatus, useAIStatus, useUIState } from '../store';
import { toast } from 'react-hot-toast';

export function Dashboard() {
  const pipelineStatus = usePipelineStatus();
  const aiStatus = useAIStatus();
  const { wsConnected } = useUIState();
  const [stats, setStats] = useState({
    totalVideos: 0,
    todayGenerated: 0,
    successRate: 0,
    avgTime: 0,
  });

  const [youtubeChannel, setYouTubeChannel] = useState<any>(null);

  // Fetch initial data
  useEffect(() => {
    fetchPipelineStatus();
    fetchAIStatus();
    fetchStats();
    fetchYouTubeChannel();
  }, []);

  const fetchPipelineStatus = async () => {
    try {
      const response = await fetch('/api/status');
      const data = await response.json();
      useAppStore.getState().setPipelineStatus(data);
    } catch (error) {
      console.error('Failed to fetch pipeline status:', error);
    }
  };

  const fetchAIStatus = async () => {
    try {
      const response = await fetch('/api/ai/status');
      const data = await response.json();
      useAppStore.getState().setAIStatus(data);
    } catch (error) {
      console.error('Failed to fetch AI status:', error);
    }
  };

  const fetchStats = async () => {
    try {
      const [statsResponse, analyticsResponse] = await Promise.all([
        fetch('/api/v1/pipeline/stats'),
        fetch('/api/v1/analytics/overview')
      ]);
      
      const statsData = await statsResponse.json();
      await analyticsResponse.json();
      
      setStats({
        totalVideos: statsData.total_videos || 0,
        todayGenerated: statsData.uploaded_videos || 0,
        successRate: statsData.success_rate || 0,
        avgTime: Math.round(statsData.pipeline_stats?.avg_processing_time || 0)
      });
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      setStats({
        totalVideos: 0,
        todayGenerated: 0,
        successRate: 0,
        avgTime: 0
      });
    }
  };

  const fetchYouTubeChannel = async () => {
    try {
      const response = await fetch('/api/youtube/channel');
      const data = await response.json();
      
      if (data.success) {
        setYouTubeChannel(data.channel);
        // Update stats with real YouTube data
        setStats(prev => ({
          ...prev,
          totalVideos: parseInt(data.channel.video_count) || prev.totalVideos,
        }));
      } else {
        console.error('Failed to fetch YouTube channel:', data.error);
      }
    } catch (error) {
      console.error('Error fetching YouTube channel:', error);
    }
  };

  const handleStartPipeline = async () => {
    try {
      const response = await fetch('/api/v1/pipeline/start', { method: 'POST' });
      const data = await response.json();
      
      if (data.status === 'success') {
        toast.success('Pipeline started successfully');
        fetchPipelineStatus(); // Refresh the status
      } else {
        toast.error(data.message || 'Failed to start pipeline');
      }
    } catch (error) {
      toast.error('Error starting pipeline');
    }
  };

  const handleStopPipeline = async () => {
    try {
      const response = await fetch('/api/v1/pipeline/stop', { method: 'POST' });
      const data = await response.json();
      
      if (data.status === 'success') {
        toast.success('Pipeline stopped');
        fetchPipelineStatus(); // Refresh the status
      } else {
        toast.error(data.message || 'Failed to stop pipeline');
      }
    } catch (error) {
      toast.error('Error stopping pipeline');
    }
  };

  const navigate = useNavigate();

  const handleGenerateVideo = () => {
    navigate('/ai-generation');
  };

  const handleViewVideos = () => {
    navigate('/videos');
  };

  const handleAnalytics = () => {
    navigate('/analytics');
  };

  const handleSettings = () => {
    navigate('/settings');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-600 bg-green-100';
      case 'stopped':
        return 'text-gray-600 bg-gray-100';
      case 'error':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor your AI-powered YouTube automation pipeline
          </p>
        </div>
        
        {/* Connection Status */}
        <div className="mt-4 sm:mt-0 flex items-center space-x-2">
          {wsConnected ? (
            <div className="flex items-center space-x-2 text-green-600">
              <Wifi className="w-4 h-4" />
              <span className="text-sm font-medium">Real-time Connected</span>
            </div>
          ) : (
            <div className="flex items-center space-x-2 text-red-600">
              <WifiOff className="w-4 h-4" />
              <span className="text-sm font-medium">Disconnected</span>
            </div>
          )}
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Video className="w-6 h-6 text-blue-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Total Videos</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.totalVideos}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-green-100 rounded-lg">
              <Sparkles className="w-6 h-6 text-green-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Today Generated</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.todayGenerated}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-purple-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Success Rate</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.successRate}%</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center">
            <div className="p-2 bg-orange-100 rounded-lg">
              <Clock className="w-6 h-6 text-orange-600" />
            </div>
            <div className="ml-4">
              <p className="text-sm font-medium text-gray-600">Avg Generation</p>
              <p className="text-2xl font-semibold text-gray-900">{stats.avgTime}s</p>
            </div>
          </div>
        </div>
      </div>

      {/* YouTube Channel Info */}
      {youtubeChannel && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Connected YouTube Channel</h3>
            <div className="flex items-center space-x-1 text-green-600">
              <CheckCircle className="w-4 h-4" />
              <span className="text-sm font-medium">Connected</span>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <img 
              src={youtubeChannel.thumbnail} 
              alt={youtubeChannel.title}
              className="w-16 h-16 rounded-full"
            />
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900">{youtubeChannel.title}</h4>
              <p className="text-sm text-gray-600 mt-1">{youtubeChannel.description}</p>
              
              <div className="flex space-x-6 mt-3 text-sm text-gray-600">
                <div>
                  <span className="font-medium text-gray-900">{youtubeChannel.subscriber_count}</span>
                  <span className="ml-1">subscribers</span>
                </div>
                <div>
                  <span className="font-medium text-gray-900">{youtubeChannel.video_count}</span>
                  <span className="ml-1">videos</span>
                </div>
                <div>
                  <span className="font-medium text-gray-900">{parseInt(youtubeChannel.view_count).toLocaleString()}</span>
                  <span className="ml-1">views</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pipeline Control */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline Status */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Pipeline Status</h3>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(pipelineStatus.status)}`}>
              {pipelineStatus.status.charAt(0).toUpperCase() + pipelineStatus.status.slice(1)}
            </div>
          </div>
          
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Videos Processed:</span>
              <span className="font-medium">{pipelineStatus.videos_processed}</span>
            </div>
            
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Last Run:</span>
              <span className="font-medium">
                {pipelineStatus.last_run 
                  ? new Date(pipelineStatus.last_run).toLocaleString()
                  : 'Never'
                }
              </span>
            </div>
          </div>

          <div className="mt-6 flex space-x-3">
            {!pipelineStatus.active ? (
              <button
                onClick={handleStartPipeline}
                className="btn-success flex items-center space-x-2 flex-1"
              >
                <Play className="w-4 h-4" />
                <span>Start Pipeline</span>
              </button>
            ) : (
              <button
                onClick={handleStopPipeline}
                className="btn-danger flex items-center space-x-2 flex-1"
              >
                <Square className="w-4 h-4" />
                <span>Stop Pipeline</span>
              </button>
            )}
          </div>
        </div>

        {/* AI Services Status */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">AI Services</h3>
            <Activity className="w-5 h-5 text-gray-400" />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">OpenAI GPT</span>
              <div className="flex items-center space-x-1">
                {aiStatus?.openai_available ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
                <span className="text-sm font-medium">
                  {aiStatus?.openai_available ? 'Available' : 'Unavailable'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Sora AI Video</span>
              <div className="flex items-center space-x-1">
                {aiStatus?.sora_enabled ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                )}
                <span className="text-sm font-medium">
                  {aiStatus?.sora_enabled ? 'Enabled' : 'Mock Mode'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Image Processing</span>
              <div className="flex items-center space-x-1">
                {aiStatus?.pil_available ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
                <span className="text-sm font-medium">
                  {aiStatus?.pil_available ? 'Available' : 'Unavailable'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">DALL-E Thumbnails</span>
              <div className="flex items-center space-x-1">
                {aiStatus?.dalle_enabled ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-yellow-500" />
                )}
                <span className="text-sm font-medium">
                  {aiStatus?.dalle_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <button 
            className="btn-primary p-4 text-left"
            onClick={handleGenerateVideo}
          >
            <Sparkles className="w-5 h-5 mb-2" />
            <div className="text-sm font-medium">Generate Video</div>
            <div className="text-xs text-white/80">Create AI content</div>
          </button>
          
          <button 
            className="btn-secondary p-4 text-left"
            onClick={handleViewVideos}
          >
            <Video className="w-5 h-5 mb-2" />
            <div className="text-sm font-medium">View Videos</div>
            <div className="text-xs text-gray-600">Manage uploads</div>
          </button>
          
          <button 
            className="btn-secondary p-4 text-left"
            onClick={handleAnalytics}
          >
            <TrendingUp className="w-5 h-5 mb-2" />
            <div className="text-sm font-medium">Analytics</div>
            <div className="text-xs text-gray-600">Performance data</div>
          </button>
          
          <button 
            className="btn-secondary p-4 text-left"
            onClick={handleSettings}
          >
            <Activity className="w-5 h-5 mb-2" />
            <div className="text-sm font-medium">Settings</div>
            <div className="text-xs text-gray-600">Configure system</div>
          </button>
        </div>
      </div>
    </div>
  );
}