import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: 'localhost',
    port: 3000,
    proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: 'ws://127.0.0.1:8000',
          ws: true,
          changeOrigin: true,
        },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})