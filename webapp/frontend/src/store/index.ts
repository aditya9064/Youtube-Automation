import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { AuthState, PipelineStatus, AIJob, AIStatus } from '../types';

interface AppState {
  // Auth State
  auth: AuthState;
  setAuth: (auth: Partial<AuthState>) => void;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => void;
  
  // Pipeline State
  pipelineStatus: PipelineStatus;
  setPipelineStatus: (status: Partial<PipelineStatus>) => void;
  
  // AI State
  aiJobs: AIJob[];
  aiStatus: AIStatus | null;
  addAIJob: (job: AIJob) => void;
  updateAIJob: (jobId: string, updates: Partial<AIJob>) => void;
  setAIJobs: (jobs: AIJob[]) => void;
  setAIStatus: (status: AIStatus) => void;
  
  // WebSocket State
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;
  
  // UI State
  sidebarOpen: boolean;
  setSidebarOpen: (open: boolean) => void;
  theme: 'light' | 'dark';
  setTheme: (theme: 'light' | 'dark') => void;
}

export const useAppStore = create<AppState>()(
  devtools(
    persist(
      (set) => ({
        // Auth State
        auth: {
          user: null,
          token: localStorage.getItem('auth_token'),
          isAuthenticated: false,
          isLoading: false,
        },
        
        setAuth: (authUpdates) =>
          set((state) => ({
            auth: { ...state.auth, ...authUpdates },
          })),
        
        login: async (email: string, _password: string) => {
          set((state) => ({
            auth: { ...state.auth, isLoading: true },
          }));
          
          try {
            // TODO: Implement actual login API call
            // For now, simulate login
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            const mockUser = {
              id: '1',
              email,
              name: email.split('@')[0],
              created_at: new Date().toISOString(),
              subscription_tier: 'pro' as const,
            };
            
            const token = 'mock_jwt_token';
            localStorage.setItem('auth_token', token);
            
            set((state) => ({
              auth: {
                ...state.auth,
                user: mockUser,
                token,
                isAuthenticated: true,
                isLoading: false,
              },
            }));
            
            return true;
          } catch (error) {
            set((state) => ({
              auth: { ...state.auth, isLoading: false },
            }));
            return false;
          }
        },
        
        logout: () => {
          localStorage.removeItem('auth_token');
          set(() => ({
            auth: {
              user: null,
              token: null,
              isAuthenticated: false,
              isLoading: false,
            },
          }));
        },
        
        // Pipeline State
        pipelineStatus: {
          active: false,
          last_run: null,
          videos_processed: 0,
          status: 'stopped',
        },
        
        setPipelineStatus: (statusUpdates) =>
          set((state) => ({
            pipelineStatus: { ...state.pipelineStatus, ...statusUpdates },
          })),
        
        // AI State
        aiJobs: [],
        aiStatus: null,
        
        addAIJob: (job) =>
          set((state) => ({
            aiJobs: [job, ...state.aiJobs],
          })),
        
        updateAIJob: (jobId, updates) =>
          set((state) => ({
            aiJobs: state.aiJobs.map((job) =>
              job.job_id === jobId ? { ...job, ...updates } : job
            ),
          })),
        
        setAIJobs: (jobs: AIJob[]) =>
          set(() => ({
            aiJobs: jobs,
          })),

        setAIStatus: (status) =>
          set(() => ({
            aiStatus: status,
          })),
        
        // WebSocket State
        wsConnected: false,
        setWsConnected: (connected) =>
          set(() => ({
            wsConnected: connected,
          })),
        
        // UI State
        sidebarOpen: true,
        setSidebarOpen: (open) =>
          set(() => ({
            sidebarOpen: open,
          })),
        
        theme: 'light',
        setTheme: (theme) =>
          set(() => ({
            theme,
          })),
      }),
      {
        name: 'youtube-automation-store',
        partialize: (state) => ({
          auth: {
            token: state.auth.token,
            user: state.auth.user,
          },
          theme: state.theme,
          sidebarOpen: state.sidebarOpen,
        }),
      }
    )
  )
);

// Selectors
export const useAuth = () => useAppStore((state) => state.auth);
export const usePipelineStatus = () => useAppStore((state) => state.pipelineStatus);
export const useAIJobs = () => useAppStore((state) => state.aiJobs);
export const useAIStatus = () => useAppStore((state) => state.aiStatus);
export const useUIState = () => useAppStore((state) => ({
  sidebarOpen: state.sidebarOpen,
  theme: state.theme,
  wsConnected: state.wsConnected,
}));