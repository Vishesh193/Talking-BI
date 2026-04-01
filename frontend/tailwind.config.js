/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // We use CSS custom properties for theming — Tailwind is only used here
  // for reset/utilities that complement our design system
  theme: {
    extend: {
      fontFamily: {
        ui:   ['Segoe UI', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Code', 'Fira Code', 'Consolas', 'monospace'],
      },
      colors: {
        // Power BI brand palette (mirrors CSS vars for Tailwind utility access)
        'pbi-blue':      '#0078D4',
        'pbi-blue-dark': '#005A9E',
        'pbi-blue-lt':   '#EFF6FC',
        'pbi-teal':      '#00B7C3',
        'pbi-purple':    '#8764B8',
        'pbi-red':       '#D13438',
        'pbi-green':     '#107C10',
        'pbi-orange':    '#CA5010',
        'pbi-yellow':    '#FFB900',
        // Neutral scale
        'n-0':   '#FFFFFF',
        'n-10':  '#FAF9F8',
        'n-20':  '#F3F2F1',
        'n-30':  '#EDEBE9',
        'n-40':  '#E1DFDD',
        'n-60':  '#C8C6C4',
        'n-80':  '#A19F9D',
        'n-100': '#797775',
        'n-120': '#605E5C',
        'n-160': '#323130',
        'n-180': '#201F1E',
      },
      boxShadow: {
        'pbi-card':   '0 1.6px 3.6px 0 rgba(0,0,0,.13), 0 .3px .9px 0 rgba(0,0,0,.11)',
        'pbi-panel':  '0 2px 8px rgba(0,0,0,.12)',
        'pbi-modal':  '0 8px 32px rgba(0,0,0,.18)',
      },
      borderRadius: {
        'fluent': '2px',
      },
      animation: {
        'fade-in':  'fadeIn .2s ease',
        'slide-up': 'slideUp .25s ease',
        'pulse-bi': 'pulse 1.5s infinite',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'none' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to:   { opacity: '1', transform: 'none' },
        },
      },
    },
  },
  plugins: [],
}
