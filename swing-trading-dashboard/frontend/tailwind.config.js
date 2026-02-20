/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"IBM Plex Mono"', 'monospace'],
        condensed: ['"Barlow Condensed"', 'sans-serif'],
      },
      colors: {
        t: {
          bg:          '#000000',
          surface:     '#080c12',
          panel:       '#0c111a',
          border:      '#1a2535',
          borderLight: '#253347',
          text:        '#c8cdd6',
          muted:       '#4a5a72',
          accent:      '#F5A623',
          accentDim:   '#7a5010',
          go:          '#00c87a',
          goDim:       '#003d25',
          halt:        '#ff2d55',
          haltDim:     '#4a0015',
          blue:        '#00C8FF',
          blueDim:     '#003a50',
          purple:      '#9B6EFF',
          pink:        '#FF6EC7',
        },
      },
      keyframes: {
        pulse_halt: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0.7' },
        },
        blink: {
          '0%, 100%': { opacity: '1' },
          '50%':       { opacity: '0' },
        },
        scanIn: {
          '0%':   { transform: 'translateY(-4px)', opacity: '0' },
          '100%': { transform: 'translateY(0)',    opacity: '1' },
        },
        shimmer: {
          '0%':   { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
      },
      animation: {
        pulse_halt: 'pulse_halt 1.4s ease-in-out infinite',
        blink:      'blink 1s step-end infinite',
        scanIn:     'scanIn 0.18s ease-out forwards',
        shimmer:    'shimmer 1.8s linear infinite',
      },
    },
  },
  plugins: [],
}
