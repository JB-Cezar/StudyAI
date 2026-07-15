import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Respeita PORT quando definida (ex.: harness de preview atribuindo porta
    // dinâmica porque a 5173 já estava em uso por outro projeto na máquina).
    port: process.env.PORT ? Number(process.env.PORT) : 5173,
    strictPort: Boolean(process.env.PORT),
  },
})
