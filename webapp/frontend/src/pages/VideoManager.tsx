// (removed duplicate VideoManager export)
import { useEffect, useState } from 'react';

interface VideoLibraryItem {
  id: string;
  filename: string;
  title: string;
  prompt?: string;
  style?: string;
  orientation?: string;
  duration?: string;
  url: string;
  download_url: string;
  thumbnail_url?: string;
  has_thumbnail?: boolean;
  file_size?: number;
  file_size_mb?: number;
  created_at?: string;
  generated_with?: string;
  upload_status?: string;
  youtube_url?: string;
  can_upload?: boolean;
}

const VideoManager = () => {
  const [videos, setVideos] = useState<VideoLibraryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/v1/videos/library')
      .then((res) => res.json())
      .then((data) => {
        setVideos(data.videos || []);
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load videos');
        setLoading(false);
      });
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">Video Manager</h1>
      <p className="text-gray-600">Manage your uploaded and generated videos</p>
      <div className="card p-6 mt-6">
        {loading && <p className="text-gray-500">Loading videos...</p>}
        {error && <p className="text-red-500">{error}</p>}
        {!loading && !error && videos.length === 0 && (
          <p className="text-gray-500">No videos found.</p>
        )}
        {!loading && !error && videos.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {videos.map((video) => (
              <div key={video.id} className="border rounded-lg p-4 bg-white shadow-sm flex flex-col">
                {video.thumbnail_url ? (
                  <img src={video.thumbnail_url} alt={video.title} className="w-full h-40 object-cover rounded mb-2" />
                ) : (
                  <div className="w-full h-40 bg-gray-200 rounded mb-2 flex items-center justify-center text-gray-400">
                    No Thumbnail
                  </div>
                )}
                <div className="flex-1">
                  <h2 className="font-semibold text-lg text-gray-800 mb-1">{video.title}</h2>
                  <p className="text-xs text-gray-500 mb-1">{video.filename}</p>
                  {video.prompt && <p className="text-sm text-gray-700 mb-1">Prompt: {video.prompt}</p>}
                  <p className="text-xs text-gray-500 mb-1">Generated: {video.created_at ? new Date(video.created_at).toLocaleString() : 'Unknown'}</p>
                  <p className="text-xs text-gray-500 mb-1">Size: {video.file_size_mb} MB</p>
                  <p className="text-xs text-gray-500 mb-1">Status: {video.upload_status}</p>
                  {video.youtube_url && (
                    <a href={video.youtube_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline text-xs">YouTube Link</a>
                  )}
                </div>
                <div className="mt-2 flex gap-2">
                  <a href={video.url} target="_blank" rel="noopener noreferrer" className="px-3 py-1 bg-blue-500 text-white rounded text-xs">View</a>
                  <a href={video.download_url} className="px-3 py-1 bg-gray-200 text-gray-800 rounded text-xs">Download</a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default VideoManager;