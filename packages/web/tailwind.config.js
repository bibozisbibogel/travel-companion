/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    // Custom breakpoints for responsive design
    screens: {
      'xs': '475px',   // Extra small devices
      'sm': '640px',   // Small devices (tablets)
      'md': '768px',   // Medium devices (small laptops)  
      'lg': '1024px',  // Large devices (desktops)
      'xl': '1280px',  // Extra large devices
      '2xl': '1536px', // 2X large devices
    },
    extend: {
      // Travel Companion Color Palette
      colors: {
        primary: {
          50: 'rgb(var(--color-primary-50) / <alpha-value>)',
          100: 'rgb(var(--color-primary-100) / <alpha-value>)',
          200: 'rgb(var(--color-primary-200) / <alpha-value>)',
          300: 'rgb(var(--color-primary-300) / <alpha-value>)',
          400: 'rgb(var(--color-primary-400) / <alpha-value>)',
          500: 'rgb(var(--color-primary-500) / <alpha-value>)',
          600: 'rgb(var(--color-primary-600) / <alpha-value>)',
          700: 'rgb(var(--color-primary-700) / <alpha-value>)',
          800: 'rgb(var(--color-primary-800) / <alpha-value>)',
          900: 'rgb(var(--color-primary-900) / <alpha-value>)',
          950: 'rgb(var(--color-primary-950) / <alpha-value>)',
        },
        secondary: {
          50: 'rgb(var(--color-secondary-50) / <alpha-value>)',
          100: 'rgb(var(--color-secondary-100) / <alpha-value>)',
          200: 'rgb(var(--color-secondary-200) / <alpha-value>)',
          300: 'rgb(var(--color-secondary-300) / <alpha-value>)',
          400: 'rgb(var(--color-secondary-400) / <alpha-value>)',
          500: 'rgb(var(--color-secondary-500) / <alpha-value>)',
          600: 'rgb(var(--color-secondary-600) / <alpha-value>)',
          700: 'rgb(var(--color-secondary-700) / <alpha-value>)',
          800: 'rgb(var(--color-secondary-800) / <alpha-value>)',
          900: 'rgb(var(--color-secondary-900) / <alpha-value>)',
          950: 'rgb(var(--color-secondary-950) / <alpha-value>)',
        },
        gray: {
          50: 'rgb(var(--color-gray-50) / <alpha-value>)',
          100: 'rgb(var(--color-gray-100) / <alpha-value>)',
          200: 'rgb(var(--color-gray-200) / <alpha-value>)',
          300: 'rgb(var(--color-gray-300) / <alpha-value>)',
          400: 'rgb(var(--color-gray-400) / <alpha-value>)',
          500: 'rgb(var(--color-gray-500) / <alpha-value>)',
          600: 'rgb(var(--color-gray-600) / <alpha-value>)',
          700: 'rgb(var(--color-gray-700) / <alpha-value>)',
          800: 'rgb(var(--color-gray-800) / <alpha-value>)',
          900: 'rgb(var(--color-gray-900) / <alpha-value>)',
          950: 'rgb(var(--color-gray-950) / <alpha-value>)',
        },
        success: {
          500: 'rgb(var(--color-success-500) / <alpha-value>)',
          600: 'rgb(var(--color-success-600) / <alpha-value>)',
        },
        warning: {
          500: 'rgb(var(--color-warning-500) / <alpha-value>)',
          600: 'rgb(var(--color-warning-600) / <alpha-value>)',
        },
        error: {
          500: 'rgb(var(--color-error-500) / <alpha-value>)',
          600: 'rgb(var(--color-error-600) / <alpha-value>)',
        },
      },
      
      // Custom spacing scale
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      // Enhanced font sizes
      fontSize: {
        'xs': ['var(--font-size-xs)', { lineHeight: '1.4' }],
        'sm': ['var(--font-size-sm)', { lineHeight: '1.5' }],
        'base': ['var(--font-size-base)', { lineHeight: '1.6' }],
        'lg': ['var(--font-size-lg)', { lineHeight: '1.6' }],
        'xl': ['var(--font-size-xl)', { lineHeight: '1.5' }],
        '2xl': ['var(--font-size-2xl)', { lineHeight: '1.4' }],
        '3xl': ['var(--font-size-3xl)', { lineHeight: '1.3' }],
        '4xl': ['var(--font-size-4xl)', { lineHeight: '1.2' }],
      },

      // Custom border radius
      borderRadius: {
        'xs': 'var(--radius-sm)',
        'sm': 'var(--radius-md)',
        'md': 'var(--radius-lg)',
        'lg': 'var(--radius-xl)',
        'full': 'var(--radius-full)',
      },

      // Box shadow scale
      boxShadow: {
        'travel-sm': 'var(--shadow-sm)',
        'travel-md': 'var(--shadow-md)',
        'travel-lg': 'var(--shadow-lg)',
        'travel-xl': 'var(--shadow-xl)',
      },

      // Background gradients
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "gradient-travel": "linear-gradient(135deg, rgb(var(--color-primary-500)), rgb(var(--color-secondary-500)))",
      },

      // Animation keyframes
      keyframes: {
        fadeIn: {
          'from': { opacity: '0' },
          'to': { opacity: '1' },
        },
        slideUp: {
          'from': { opacity: '0', transform: 'translateY(1rem)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          'from': { opacity: '0', transform: 'translateY(-1rem)' },
          'to': { opacity: '1', transform: 'translateY(0)' },
        },
        slideLeft: {
          'from': { opacity: '0', transform: 'translateX(1rem)' },
          'to': { opacity: '1', transform: 'translateX(0)' },
        },
        slideRight: {
          'from': { opacity: '0', transform: 'translateX(-1rem)' },
          'to': { opacity: '1', transform: 'translateX(0)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.5' },
        },
      },

      // Animation classes
      animation: {
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'slide-left': 'slideLeft 0.3s ease-out',
        'slide-right': 'slideRight 0.3s ease-out',
        'pulse-slow': 'pulse 2s ease-in-out infinite',
      },

      // Grid template columns for layout
      gridTemplateColumns: {
        'auto-fit-xs': 'repeat(auto-fit, minmax(16rem, 1fr))',
        'auto-fit-sm': 'repeat(auto-fit, minmax(20rem, 1fr))',
        'auto-fit-md': 'repeat(auto-fit, minmax(24rem, 1fr))',
      },
    },
  },
  plugins: [],
};