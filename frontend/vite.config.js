import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/upload': 'http://localhost:8000',
            '/start-viva': 'http://localhost:8000',
            '/submit-answer': 'http://localhost:8000',
            '/finalize': 'http://localhost:8000',
        }
    }
})
