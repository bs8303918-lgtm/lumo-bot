import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const base = env.VITE_BASE_PATH || '/app/';

  return {
    base,
    plugins: [react(), tailwindcss()],
    server: {
      port: 5174,
      proxy: {
        '/api': env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8000',
      },
    },
  };
});