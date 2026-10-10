/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        lenny: {
          50: '#fcf8f2',
          100: '#f7eee0',
          200: '#eedabf',
          300: '#e3c196',
          400: '#d5a168',
          500: '#c58343',
          600: '#b16b37',
          700: '#93532f',
          800: '#77432b',
          900: '#623826',
        },
      },
    },
  },
  plugins: [],
}
