import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Proxies /api/v1/* to the AquaMind AI FastAPI backend during development.
      // In production, set VITE_API_BASE_URL instead (see .env.example).
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        // Prevent buffering of SSE streams (Agent Reasoning Console)
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            proxyRes.headers['Cache-Control'] = 'no-cache';
            proxyRes.headers['Connection'] = 'keep-alive';
          });
        },
      },
    },
  },
})
