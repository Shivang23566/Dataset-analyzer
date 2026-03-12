import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import fs from 'fs';
import { execSync } from 'child_process';

// One-time CSS module setup: runs setup script if index.css doesn't exist yet
const INDEX_CSS = path.resolve(__dirname, 'src/styles/index.css');
if (!fs.existsSync(INDEX_CSS)) {
  console.log('\n[vite] CSS modules not found — running setup...');
  const scriptRoot = path.resolve(__dirname, '..');
  let done = false;
  // Try node first, then python
  for (const cmd of ['node setup-dirs.js', 'python create_dirs.py']) {
    try {
      execSync(cmd, { cwd: scriptRoot, stdio: 'inherit' });
      done = true;
      break;
    } catch (_) { /* try next */ }
  }
  if (done) console.log('[vite] CSS module setup complete.\n');
  else console.error('[vite] CSS module setup failed — run manually: node setup-dirs.js\n');
}

export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/dashboard': 'http://localhost:8000',
      '/payments': 'http://localhost:8000',
      '/coupons': 'http://localhost:8000',
      '/admin': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
  build: {
    outDir: path.resolve(__dirname, '../backend/static'),
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-three': ['three'],
          'vendor-charts': ['recharts'],
          'vendor-motion': ['framer-motion'],
        },
      },
    },
  },
});
