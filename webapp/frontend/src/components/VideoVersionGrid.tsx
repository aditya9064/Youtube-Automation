import { useState } from 'react';
import { Eye, Download, CheckCircle, XCircle, RefreshCw, Play, Youtube } from 'lucide-react';
import { VideoVersion, YouTubeUploadRequest } from '../types';
import { toast } from 'react-hot-toast';

interface VideoVersionGridProps {
  jobId: string;
  videoId: number;
  versions: VideoVersion[];
  onUploadSuccess?: (versionIndex: number, youtubeUrl: string) => void;
}

export function VideoVersionGrid({ jobId, videoId, versions, onUploadSuccess }: VideoVersionGridProps) {
  const [uploadingStates, setUploadingStates] = useState<Record<number, boolean>>({});

  const handleView = (version: VideoVersion) => {
    // Create a video modal
    const modal = document.createElement('div');
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0,0,0,0.8);
      display: flex;
      justify-content: center;
      align-items: center;
      z-index: 1000;
    `;
    
    const video = document.createElement('video');
    video.style.cssText = `
      max-width: 90%;
      max-height: 90%;
      border-radius: 8px;
    `;
    video.controls = true;
    video.src = version.url;
    
    // Close modal on click outside video
    modal.onclick = (e) => {
      if (e.target === modal) {
        document.body.removeChild(modal);
      }
    };
    
    // Add escape key handler
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        document.body.removeChild(modal);
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
    
    modal.appendChild(video);
    document.body.appendChild(modal);
    video.play();
  };

  const handleDownload = (version: VideoVersion) => {
    const link = document.createElement('a');
    link.href = `/api/v1/videos/download/${version.filename}`;
    link.download = version.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleUploadToYouTube = async (versionIndex: number, version: VideoVersion) => {
    setUploadingStates(prev => ({ ...prev, [versionIndex]: true }));
    
    try {
      const uploadData: YouTubeUploadRequest = {
        video_id: videoId,
        version_index: versionIndex,
        title: `AI Generated Video - ${version.generated_with}`,
        description: `Generated with ${version.generated_with} - Video automation tool`,
        tags: ['AI', 'generated', 'video', version.generated_with.toLowerCase()]
      };

      const response = await fetch('/api/v1/videos/upload-direct', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(uploadData),
      });

      const result = await response.json();

      if (result.success) {
        toast.success(`Successfully uploaded to YouTube!`, {
          duration: 5000
        });
        
        if (result.youtube_url && onUploadSuccess) {
          onUploadSuccess(versionIndex, result.youtube_url);
        }
      } else {
        toast.error(result.message || 'Failed to upload to YouTube', {
          duration: 7000
        });
      }
    } catch (error) {
      console.error('YouTube upload error:', error);
      toast.error('Network error while uploading to YouTube', {
        duration: 7000
      });
    } finally {
      setUploadingStates(prev => ({ ...prev, [versionIndex]: false }));
    }
  };

  const getStatusIcon = (status: VideoVersion['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'generating':
        return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <RefreshCw className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: VideoVersion['status']) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'generating':
        return 'bg-blue-100 text-blue-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  if (!versions || versions.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <Play className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>No video versions generated yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">Generated Video</h3>
        <span className="text-sm text-gray-500">
          {versions.filter(v => v.status === 'completed').length > 0 ? 'Completed' : 'Generating...'}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {versions.map((version, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-4 bg-white hover:shadow-md transition-shadow"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center space-x-2">
                {getStatusIcon(version.status)}
                <span className={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(version.status)}`}>
                  {version.status.charAt(0).toUpperCase() + version.status.slice(1)}
                </span>
              </div>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                AI Generated
              </span>
            </div>

            {/* Generator Info */}
            <div className="mb-3">
              <p className="text-sm font-medium text-gray-900">
                {version.generated_with}
              </p>
              {version.completed_at && (
                <p className="text-xs text-gray-500">
                  Completed: {new Date(version.completed_at).toLocaleString()}
                </p>
              )}
            </div>

            {/* Video Preview */}
            {version.status === 'completed' && version.file_exists && (
              <div className="mb-3">
                <div className="bg-gray-100 rounded-lg h-32 flex items-center justify-center relative overflow-hidden">
                  <video
                    src={version.url}
                    className="w-full h-full object-cover rounded-lg"
                    muted
                    onMouseEnter={(e) => {
                      const video = e.target as HTMLVideoElement;
                      video.currentTime = 1; // Show a frame from the video
                    }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-20 hover:bg-opacity-10 transition-all">
                    <Play className="w-8 h-8 text-white opacity-80" />
                  </div>
                </div>
                <p className="text-xs text-gray-500 mt-1 truncate">
                  {version.filename}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex flex-col space-y-2">
              {version.status === 'completed' && version.file_exists && (
                <>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => handleView(version)}
                      className="flex-1 btn-secondary text-xs py-2 flex items-center justify-center space-x-1"
                      title="View video"
                    >
                      <Eye className="w-3 h-3" />
                      <span>View</span>
                    </button>
                    <button
                      onClick={() => handleDownload(version)}
                      className="flex-1 btn-secondary text-xs py-2 flex items-center justify-center space-x-1"
                      title="Download video"
                    >
                      <Download className="w-3 h-3" />
                      <span>Download</span>
                    </button>
                  </div>
                  
                  <button
                    onClick={() => handleUploadToYouTube(index, version)}
                    disabled={uploadingStates[index]}
                    className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-xs py-2 rounded-lg flex items-center justify-center space-x-1 transition-colors"
                    title="Upload to YouTube"
                  >
                    {uploadingStates[index] ? (
                      <>
                        <RefreshCw className="w-3 h-3 animate-spin" />
                        <span>Uploading...</span>
                      </>
                    ) : (
                      <>
                        <Youtube className="w-3 h-3" />
                        <span>Upload to YouTube</span>
                      </>
                    )}
                  </button>
                </>
              )}

              {version.status === 'generating' && (
                <div className="text-center py-2 text-sm text-blue-600">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1" />
                  Generating...
                </div>
              )}

              {version.status === 'failed' && (
                <div className="text-center py-2 text-sm text-red-600">
                  <XCircle className="w-4 h-4 mx-auto mb-1" />
                  Generation failed
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}