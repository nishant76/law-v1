import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    resolve: {
      alias: { '@': path.resolve(__dirname, './src') },
    },
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          configure: (proxy) => {
            // Prevent the Vite dev proxy from re-compressing responses.
            // Without this, SSE (text/event-stream) gets gzipped by the proxy,
            // which buffers the entire stream before the browser sees any data.
            proxy.on('proxyReq', (proxyReq, req) => {
              if (req.url?.includes('/stream')) {
                proxyReq.setHeader('Accept-Encoding', 'identity')
              }
            })
          },
        },
      },
    },
    build: {
      outDir: 'dist',
    },
  }
})
