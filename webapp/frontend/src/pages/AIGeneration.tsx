import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { 
  Sparkles, 
  Play, 
  Clock, 
  CheckCircle, 
  XCircle, 
  RefreshCw,
  Download,
  Eye
} from 'lucide-react';
import { useAppStore, useAIJobs } from '../store';
import { GenerationRequest, AIJob } from '../types';
import { toast } from 'react-hot-toast';
import { VideoVersionGrid } from '../components/VideoVersionGrid';

const ORIENTATION_OPTIONS = [
  { value: 'portrait', label: 'Portrait', description: 'Vertical 9:16 format, ideal for mobile' },
  { value: 'landscape', label: 'Landscape', description: 'Horizontal 16:9 format, traditional video' },
];

const DURATION_OPTIONS = [
  { value: '4s', label: '4 Seconds', description: 'Short-form, perfect for social media' },
  { value: '10s', label: '10 Seconds', description: 'Medium length for detailed content' },
  { value: '15s', label: '15 Seconds', description: 'Extended duration for complex scenes' },
];

const STYLE_OPTIONS = [
  { value: 'cinematic', label: 'Cinematic', description: 'Movie-like visuals with dramatic lighting' },
  { value: 'realistic', label: 'Realistic', description: 'Photorealistic and natural looking' },
  { value: 'animated', label: 'Animated', description: 'Stylized animation and effects' },
  { value: 'documentary', label: 'Documentary', description: 'Clean and informative style' },
  { value: 'artistic', label: 'Artistic', description: 'Creative and experimental approach' },
  { value: 'vintage', label: 'Vintage', description: 'Classic, retro-inspired look' },
];

const CAMERA_VIEW_OPTIONS = [
  { value: 'wide', label: 'Wide Shot', description: 'Full scene view' },
  { value: 'close-up', label: 'Close-up', description: 'Detailed, intimate perspective' },
  { value: 'aerial', label: 'Aerial View', description: 'Bird\'s eye perspective' },
  { value: 'pov', label: 'POV', description: 'First-person perspective' },
  { value: 'tracking', label: 'Tracking Shot', description: 'Follows the subject' },
  { value: 'static', label: 'Static', description: 'Fixed camera position' },
];

const BACKGROUND_OPTIONS = [
  { value: 'natural', label: 'Natural', description: 'Outdoor environments' },
  { value: 'urban', label: 'Urban', description: 'City and architectural settings' },
  { value: 'studio', label: 'Studio', description: 'Controlled environment' },
  { value: 'abstract', label: 'Abstract', description: 'Non-representational backdrop' },
  { value: 'minimal', label: 'Minimal', description: 'Clean, simple background' },
];

export function AIGeneration() {
  const aiJobs = useAIJobs();
  const [isGenerating, setIsGenerating] = useState(false);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    reset,
  } = useForm<GenerationRequest>({
    defaultValues: {
      style: 'cinematic',
      orientation: 'landscape',
      duration: '10s',
      camera_view: 'wide',
      background: 'natural',
    },
  });

  watch('base_prompt'); // Watch for changes in base prompt

  // Auto-refresh jobs
  useEffect(() => {
    const interval = setInterval(fetchJobs, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchJobs = async () => {
    try {
      const response = await fetch('/api/v1/videos/jobs');
      const data = await response.json();
      if (data.jobs) {
        useAppStore.getState().setAIJobs(data.jobs);
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error);
    }
  };

  const onSubmit = async (data: GenerationRequest) => {
    setIsGenerating(true);
    try {
      // Try to make the API call with a timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

      const response = await fetch('/api/v1/videos/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        // Handle HTTP errors with specific messages
        if (response.status === 401) {
          throw new Error('Authentication failed. Please check your API key.');
        } else if (response.status === 429) {
          throw new Error('Too many requests. Please wait a moment and try again.');
        } else if (response.status >= 500) {
          throw new Error('Server error. Please try again later.');
        }
      }

      const result = await response.json();
      
        if (result.success) {
        toast.success(`AI generation started! Job ID: ${result.job_id}`, {
          duration: 5000
        });
        reset();
      } else {
        // Show error message from server with longer duration
        toast.error(result.message || 'Failed to start generation', {
          duration: 7000
        });
      }
    } catch (error) {
      console.error('Generation error:', error);
      let errorMessage = 'Network error while starting AI generation. Please try again.';
      
      if (error instanceof TypeError && error.message === 'Failed to fetch') {
        errorMessage = 'Cannot connect to server. Please check your internet connection.';
      } else if (error instanceof Error) {
        errorMessage = error.message;
      }

      // Show error toast with longer duration for better visibility
      toast.error(errorMessage, {
        duration: 7000
      });
    } finally {
      setIsGenerating(false);
    }
  };



  const getStatusIcon = (status: AIJob['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'generating':
        return <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />;
      default:
        return <Clock className="w-5 h-5 text-yellow-500" />;
    }
  };

  const getStatusColor = (status: AIJob['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'generating':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-yellow-100 text-yellow-800';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">AI Content Generation</h1>
        <p className="mt-1 text-sm text-gray-600">
          Create amazing videos with AI-powered content generation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Generation Form */}
        <div className="card p-6">
          <div className="flex items-center space-x-2 mb-4">
            <Sparkles className="w-5 h-5 text-primary-600" />
            <h2 className="text-lg font-semibold text-gray-900">Create New Video</h2>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Base Prompt Input */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video Description
              </label>
              <textarea
                {...register('base_prompt', {
                  required: 'Description is required',
                  minLength: {
                    value: 10,
                    message: 'Description must be at least 10 characters',
                  },
                })}
                rows={4}
                className="input resize-none"
                placeholder="Describe what you want to see in the video... (e.g., A serene mountain landscape at golden hour with birds flying)"
              />
              {errors.base_prompt && (
                <p className="mt-1 text-sm text-red-600">{errors.base_prompt.message}</p>
              )}
            </div>

            {/* Orientation Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video Orientation
              </label>
              <div className="grid grid-cols-2 gap-3">
                {ORIENTATION_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                      watch('orientation') === option.value
                        ? 'bg-primary-50 border-primary-500 ring-2 ring-primary-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      {...register('orientation', { required: 'Orientation is required' })}
                      type="radio"
                      value={option.value}
                      className="sr-only"
                    />
                    <div className="flex flex-1 flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {option.description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Duration Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video Duration
              </label>
              <div className="grid grid-cols-3 gap-3">
                {DURATION_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                      watch('duration') === option.value
                        ? 'bg-primary-50 border-primary-500 ring-2 ring-primary-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      {...register('duration', { required: 'Duration is required' })}
                      type="radio"
                      value={option.value}
                      className="sr-only"
                    />
                    <div className="flex flex-1 flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {option.description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Style Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Video Style
              </label>
              <div className="grid grid-cols-3 gap-3">
                {STYLE_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                      watch('style') === option.value
                        ? 'bg-primary-50 border-primary-500 ring-2 ring-primary-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      {...register('style', { required: 'Style is required' })}
                      type="radio"
                      value={option.value}
                      className="sr-only"
                    />
                    <div className="flex flex-1 flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {option.description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Camera View Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Camera View
              </label>
              <div className="grid grid-cols-3 gap-3">
                {CAMERA_VIEW_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                      watch('camera_view') === option.value
                        ? 'bg-primary-50 border-primary-500 ring-2 ring-primary-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      {...register('camera_view', { required: 'Camera view is required' })}
                      type="radio"
                      value={option.value}
                      className="sr-only"
                    />
                    <div className="flex flex-1 flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {option.description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Background Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Background Type
              </label>
              <div className="grid grid-cols-3 gap-3">
                {BACKGROUND_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                      watch('background') === option.value
                        ? 'bg-primary-50 border-primary-500 ring-2 ring-primary-500'
                        : 'border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <input
                      {...register('background', { required: 'Background type is required' })}
                      type="radio"
                      value={option.value}
                      className="sr-only"
                    />
                    <div className="flex flex-1 flex-col">
                      <div className="text-sm font-medium text-gray-900">
                        {option.label}
                      </div>
                      <div className="text-xs text-gray-500">
                        {option.description}
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Additional Options */}
            <div className="grid grid-cols-2 gap-4">
              {/* Lighting */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Lighting (Optional)
                </label>
                <input
                  type="text"
                  {...register('lighting')}
                  className="input"
                  placeholder="e.g., Soft natural light, Dramatic contrast"
                />
              </div>

              {/* Color Palette */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Color Palette (Optional)
                </label>
                <input
                  type="text"
                  {...register('color_palette')}
                  className="input"
                  placeholder="e.g., Warm earth tones, Cool blues"
                />
              </div>

              {/* Weather */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Weather (Optional)
                </label>
                <input
                  type="text"
                  {...register('weather')}
                  className="input"
                  placeholder="e.g., Sunny, Rainy, Cloudy"
                />
              </div>

              {/* Time of Day */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time of Day (Optional)
                </label>
                <input
                  type="text"
                  {...register('time_of_day')}
                  className="input"
                  placeholder="e.g., Sunset, Dawn, Night"
                />
              </div>
            </div>

            {/* Additional Details */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Additional Details (Optional)
              </label>
              <textarea
                {...register('additional_details')}
                rows={2}
                className="input resize-none"
                placeholder="Any other specific details or requirements..."
              />
            </div>

            {/* Generate Button */}
            <button
              type="submit"
              disabled={isGenerating}
              className="btn-primary w-full py-3 flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isGenerating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Generating...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  <span>Generate Video</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Recent Jobs */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Generation History</h2>
            <button
              onClick={fetchJobs}
              className="btn-secondary text-sm flex items-center space-x-1"
            >
              <RefreshCw className="w-4 h-4" />
              <span>Refresh</span>
            </button>
          </div>

          <div className="space-y-3 max-h-96 overflow-y-auto">
            {aiJobs.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No generation jobs yet</p>
                <p className="text-sm">Create your first AI video above!</p>
              </div>
            ) : (
              aiJobs.slice(0, 10).map((job) => (
                <div
                  key={job.job_id}
                  className="border rounded-lg p-4 space-y-3"
                >
                  {/* Job Header */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getStatusIcon(job.status)}
                      <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(job.status)}`}>
                        {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                      </span>
                    </div>
                    <span className="text-xs text-gray-500">
                      {new Date(job.started_at).toLocaleString()}
                    </span>
                  </div>

                  {/* Job Details */}
                  <div>
                    <p className="text-sm font-medium text-gray-900 line-clamp-2">
                      {job.prompt}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Style: {job.style} • Job ID: {job.job_id.slice(-8)}
                    </p>
                  </div>

                  {/* Job Results */}
                  {job.status === 'completed' && job.versions && job.versions.length > 0 && (
                    <div className="bg-green-50 border border-green-200 rounded p-3">
                      <VideoVersionGrid
                        jobId={job.job_id}
                        videoId={job.video_id || 0}
                        versions={job.versions}
                        onUploadSuccess={(versionIndex, _youtubeUrl) => {
                          toast.success(`Version ${versionIndex + 1} uploaded to YouTube!`);
                        }}
                      />
                    </div>
                  )}

                  {/* Fallback for old video format */}
                  {job.status === 'completed' && job.video && !job.versions && (
                    <div className="bg-green-50 border border-green-200 rounded p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-green-800">
                            Video Generated Successfully
                          </p>
                          {job.video.filename && (
                            <p className="text-xs text-green-600">
                              File: {job.video.filename}
                            </p>
                          )}
                          {job.metadata?.title && (
                            <p className="text-xs text-green-600">
                              Title: {job.metadata.title}
                            </p>
                          )}
                        </div>
                        <div className="flex space-x-2">
                          <button 
                            onClick={() => {
                              const url = `/api/v1/videos/view/${job.video?.filename || ''}`;
                              // Create a video element in a modal
                              const modal = document.createElement('div');
                              modal.style.position = 'fixed';
                              modal.style.top = '0';
                              modal.style.left = '0';
                              modal.style.width = '100%';
                              modal.style.height = '100%';
                              modal.style.backgroundColor = 'rgba(0,0,0,0.8)';
                              modal.style.display = 'flex';
                              modal.style.justifyContent = 'center';
                              modal.style.alignItems = 'center';
                              modal.style.zIndex = '1000';
                              
                              const video = document.createElement('video');
                              video.style.maxWidth = '90%';
                              video.style.maxHeight = '90%';
                              video.controls = true;
                              video.src = url;
                              
                              // Close modal on click outside video
                              modal.onclick = (e) => {
                                if (e.target === modal) {
                                  document.body.removeChild(modal);
                                }
                              };
                              
                              modal.appendChild(video);
                              document.body.appendChild(modal);
                              video.play();
                            }}
                            className="btn-secondary text-xs px-2 py-1 hover:bg-gray-100"
                            title="View video"
                          >
                            <Eye className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => {
                              if (job.video?.filename) {
                                const url = `/api/v1/videos/download/${job.video.filename}`;
                                const link = document.createElement('a');
                                link.href = url;
                                link.download = job.video.filename;
                                document.body.appendChild(link);
                                link.click();
                                document.body.removeChild(link);
                              }
                            }}
                            className="btn-secondary text-xs px-2 py-1 hover:bg-gray-100"
                            title="Download video"
                          >
                            <Download className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Error Display */}
                  {(job.status === 'failed' || job.status === 'error') && job.error && (
                    <div className="bg-red-50 border border-red-200 rounded p-3">
                      <p className="text-sm font-medium text-red-800">
                        Generation Failed
                      </p>
                      <p className="text-xs text-red-600 mt-1">
                        {job.error}
                      </p>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}