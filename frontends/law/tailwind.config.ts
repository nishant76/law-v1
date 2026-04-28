import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
        serif: ['Fraunces', 'serif'],
      },
      colors: {
        bg: '#F5F4F0',
        surface: {
          2: '#EFEDE8',
          3: '#E5E2DB',
        },
        border: {
          1: '#E0DDD6',
          2: '#C8C4BC',
        },
        text: {
          1: '#1C1A16',
          2: '#6A6760',
          3: '#A09C95',
        },
        ink: '#1C1A16',
        green: {
          DEFAULT: '#15803D',
          bg: '#F0FDF4',
        },
        amber: {
          DEFAULT: '#B45309',
          bg: '#FFFBEB',
        },
        red: {
          DEFAULT: '#B91C1C',
          bg: '#FEF2F2',
        },
        blue: {
          DEFAULT: '#1D4ED8',
          bg: '#EFF6FF',
        },
      },
      borderRadius: {
        DEFAULT: '10px',
        sm: '7px',
        icon: '6px',
        full: '9999px',
      },
      keyframes: {
        fadeUp: { from: { opacity: '0', transform: 'translateY(5px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        progBar: { from: { width: '0%' }, to: { width: '100%' } },
      },
      animation: {
        fadeUp: 'fadeUp 0.18s ease both',
        progBar: 'progBar 3.5s ease-out forwards',
      },
      fontSize: {
        '2xs': ['9px', { lineHeight: '1.4' }],
        xs: ['10px', { lineHeight: '1.4' }],
        sm: ['11px', { lineHeight: '1.5' }],
        'sm+': ['11.5px', { lineHeight: '1.5' }],
        base: ['12.5px', { lineHeight: '1.6' }],
        md: ['13px', { lineHeight: '1.6' }],
        lg: ['15px', { lineHeight: '1.5' }],
        xl: ['16px', { lineHeight: '1.4' }],
        '2xl': ['21px', { lineHeight: '1.2' }],
        '3xl': ['23px', { lineHeight: '1.2' }],
      },
    },
  },
  plugins: [],
} satisfies Config
