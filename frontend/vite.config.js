import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
    plugins: [vue()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        '/voice': {
          target: 'http://localhost:8008',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/voice/, ''),
        },
        '/api': {
          target: 'http://localhost:8002',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
        '/auth': {
          target: 'http://localhost:8080',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/auth/, ''),
        },
      },
    },
})
