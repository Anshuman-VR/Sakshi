/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0A2540',
        paper: '#F4F6F8',
        lime: '#059669',
        accent: '#002D62',
        coral: '#8B0000',
        lavender: '#EAF0F7',
        surface: '#FFFFFF',
        line: '#E2E8F0'
      },
      boxShadow: {
        brutal: '0 2px 0 rgba(10,37,64,.08)',
        'brutal-sm': '0 1px 2px rgba(15,23,42,.04)'
      },
      fontFamily: { sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'] }
    }
  },
  plugins: []
};
