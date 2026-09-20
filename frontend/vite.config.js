import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies /api to the FastAPI backend so cookies/tokens stay simple.
// The GitHub Pages build passes --base=/Ai-Crop-Health/ and --mode pages, which
// loads .env.pages (VITE_STATIC_DEMO=true) so the app serves bundled data
// instead of calling an API that a static host cannot run.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
