import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // GitHub Pages serves this repo from /paris-cinema/, not the domain root.
  // Without this every asset 404s once deployed. Router basename and the
  // screenings.json fetch both derive from import.meta.env.BASE_URL, so this
  // is the single place the subpath is declared.
  base: '/paris-cinema/',
})
