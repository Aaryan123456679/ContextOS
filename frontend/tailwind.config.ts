import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './hooks/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Minimal black & white: the accent palette is a neutral grayscale ramp, so
        // every `brand-*` utility resolves to grayscale — primary near-black, active
        // light-gray — for a monochrome look across the whole app.
        brand: {
          50: '#fafafa',
          100: '#f1f1f1',
          200: '#dcdcdc',
          300: '#bdbdbd',
          400: '#9e9e9e',
          500: '#6e6e6e',
          600: '#171717', // primary — near-black
          700: '#0a0a0a', // hover
          800: '#000000', // active
          900: '#000000',
          950: '#111111', // subtle dark-mode accent
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}

export default config
