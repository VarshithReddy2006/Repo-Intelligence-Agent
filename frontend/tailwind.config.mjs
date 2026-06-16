/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas: '#010102',
        primary: {
          DEFAULT: '#5e6ad2',
          foreground: '#f7f8f8',
          hover: '#4d5ac0'
        },
        border: '#23252a',
        text: {
          DEFAULT: '#f7f8f8',
          muted: '#8c8c8c'
        },
        card: {
          DEFAULT: '#08080a',
          hover: '#0b0b0e',
          foreground: '#f7f8f8'
        },
        popover: {
          DEFAULT: '#0b0b0e',
          foreground: '#f7f8f8'
        }
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      animation: {
        'pulse-slow': 'pulse 4s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
