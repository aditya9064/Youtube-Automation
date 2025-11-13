import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { useAppStore } from './store';
import { useWebSocket } from './hooks/useWebSocket';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { AIGeneration } from './pages/AIGeneration';
import VideoManager from './pages/VideoManager';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      gcTime: 1000 * 60 * 30, // 30 minutes (renamed from cacheTime)
    },
  },
});

function AppContent() {
  const { auth } = useAppStore();
  
  // Initialize WebSocket connection
  useWebSocket();

  // Auto-authenticate for YouTube integration
  useEffect(() => {
    if (!auth.isAuthenticated) {
      // Automatically authenticate with YouTube credentials
      useAppStore.getState().setAuth({
        isAuthenticated: true,
        user: {
          id: 'youtube_user',
          email: 'youtube@automation.ai',
          name: 'YouTube Automation',
          created_at: new Date().toISOString(),
          subscription_tier: 'pro',
        },
        token: 'youtube_oauth_token',
        isLoading: false,
      });
    }
  }, [auth.isAuthenticated]);

  // Always show the main interface (no login required)

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/ai-generation" element={<AIGeneration />} />
        <Route path="/videos" element={<VideoManager />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Layout>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-gray-50">
          <AppContent />
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#363636',
                color: '#fff',
              },
              success: {
                duration: 3000,
                iconTheme: {
                  primary: '#10b981',
                  secondary: '#fff',
                },
              },
              error: {
                duration: 5000,
                iconTheme: {
                  primary: '#ef4444',
                  secondary: '#fff',
                },
              },
            }}
          />
        </div>
      </Router>
    </QueryClientProvider>
  );
}
