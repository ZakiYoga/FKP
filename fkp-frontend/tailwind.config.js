/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        // Brand colors FKP SaktiFood
        brand: {
          50: '#fff7ed',
          100: '#ffedd5',
          200: '#fed7aa',
          300: '#fdba74',
          400: '#fb923c',
          500: '#FF8C00',  // primary
          600: '#ea7500',
          700: '#c45e00',
          800: '#9a4a00',
          900: '#7c3a00',
          950: '#431e00',
        },
        // Status FKP colors
        status: {
          draft: '#94a3b8',
          submitted: '#3b82f6',
          apsm_review: '#8b5cf6',
          in_review: '#f59e0b',
          need_revision: '#ef4444',
          investigation: '#f97316',
          investigated: '#06b6d4',
          rsm_review: '#8b5cf6',
          direktur_review: '#a855f7',
          accepted: '#10b981',
          rejected: '#ef4444',
          resolved: '#22c55e',
          closed: '#64748b',
        },
        // Prioritas colors
        prioritas: {
          top_urgent: '#dc2626',
          urgent: '#ea580c',
          reguler: '#16a34a',
          low: '#2563eb',
        },
      },
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'card': '0 1px 3px 0 rgb(0 0 0 / 0.06), 0 1px 2px -1px rgb(0 0 0 / 0.06)',
        'card-hover': '0 4px 6px -1px rgb(0 0 0 / 0.08), 0 2px 4px -2px rgb(0 0 0 / 0.08)',
        'modal': '0 20px 25px -5px rgb(0 0 0 / 0.15), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'spin-slow': 'spin 2s linear infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
