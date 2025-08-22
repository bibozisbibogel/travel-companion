# Styling Guidelines

## Styling Approach

**Primary Method:** Tailwind CSS with custom component classes for complex travel-specific components.

**Design System Integration:** Tailwind configured with Travel Companion design tokens, extended with shadcn/ui components for accessibility and consistency.

**Component Styling Pattern:**
- Tailwind utility classes for layout, spacing, and common styling
- CSS custom properties for theme values and dynamic styling
- Component-specific CSS classes for complex animations and travel-domain styling
- Conditional classes using `clsx` or `cn` utility for dynamic styling

## Global Theme Variables

```css
/* styles/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Brand Colors - Travel Companion Theme */
  --brand-primary: #2563eb;
  --brand-secondary: #0ea5e9;
  --brand-accent: #10b981;
  
  /* Travel-specific Semantic Colors */
  --flight-color: #3b82f6;
  --hotel-color: #8b5cf6;
  --activity-color: #f59e0b;
  --restaurant-color: #ef4444;
  --budget-color: #10b981;
  
  /* Status Colors */
  --success: #059669;
  --warning: #d97706;
  --error: #dc2626;
  --info: #0ea5e9;
  
  /* Neutral Colors */
  --gray-50: #f8fafc;
  --gray-100: #f1f5f9;
  --gray-200: #e2e8f0;
  --gray-300: #cbd5e1;
  --gray-400: #94a3b8;
  --gray-500: #64748b;
  --gray-600: #475569;
  --gray-700: #334155;
  --gray-800: #1e293b;
  --gray-900: #0f172a;
  
  /* Background Colors */
  --background: #ffffff;
  --surface: #f8fafc;
  --card: #ffffff;
  --overlay: rgba(15, 23, 42, 0.8);
  
  /* Text Colors */
  --text-primary: var(--gray-900);
  --text-secondary: var(--gray-600);
  --text-tertiary: var(--gray-400);
  --text-inverse: #ffffff;
  
  /* Border Colors */
  --border-light: var(--gray-200);
  --border-medium: var(--gray-300);
  --border-strong: var(--gray-400);
  
  /* Spacing Scale (rem units) */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  --spacing-3xl: 4rem;
  
  /* Typography Scale */
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;
  --text-4xl: 2.25rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  
  /* Border Radius */
  --radius-sm: 0.25rem;
  --radius-md: 0.375rem;
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;
  --radius-full: 9999px;
  
  /* Transitions */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 500ms cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Layout Constraints */
  --container-sm: 640px;
  --container-md: 768px;
  --container-lg: 1024px;
  --container-xl: 1280px;
  --container-2xl: 1536px;
}

/* Dark Theme Variables */
[data-theme="dark"] {
  --background: var(--gray-900);
  --surface: var(--gray-800);
  --card: var(--gray-800);
  --overlay: rgba(0, 0, 0, 0.8);
  
  --text-primary: var(--gray-100);
  --text-secondary: var(--gray-300);
  --text-tertiary: var(--gray-500);
  
  --border-light: var(--gray-700);
  --border-medium: var(--gray-600);
  --border-strong: var(--gray-500);
}

/* Base Styles */
@layer base {
  * {
    box-sizing: border-box;
  }
  
  html {
    scroll-behavior: smooth;
    font-size: 16px;
  }
  
  body {
    background-color: var(--background);
    color: var(--text-primary);
    font-family: 'Inter', system-ui, sans-serif;
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  
  /* Focus styles for accessibility */
  *:focus-visible {
    outline: 3px solid var(--brand-primary);
    outline-offset: 2px;
  }
}

/* Component Layer - Travel-specific components */
@layer components {
  /* Travel Card Base Styles */
  .travel-card {
    @apply bg-card rounded-lg border border-border-light p-6 shadow-sm transition-all duration-300;
    @apply hover:shadow-md hover:-translate-y-1;
  }
  
  .travel-card--selected {
    @apply ring-2 ring-brand-primary ring-offset-2;
  }
  
  .travel-card--flight {
    @apply border-l-4 border-l-flight-color;
  }
  
  .travel-card--hotel {
    @apply border-l-4 border-l-hotel-color;
  }
  
  .travel-card--activity {
    @apply border-l-4 border-l-activity-color;
  }
  
  .travel-card--restaurant {
    @apply border-l-4 border-l-restaurant-color;
  }
  
  /* Budget Tracker Styles */
  .budget-tracker {
    @apply bg-card rounded-lg p-4 border border-border-light;
  }
  
  .budget-bar {
    @apply h-2 rounded-full bg-gray-200 overflow-hidden;
  }
  
  .budget-progress {
    @apply h-full transition-all duration-500;
  }
  
  .budget-progress--under {
    @apply bg-success;
  }
  
  .budget-progress--at {
    @apply bg-warning;
  }
  
  .budget-progress--over {
    @apply bg-error;
  }
  
  /* Map Marker Styles */
  .map-marker {
    @apply w-8 h-8 rounded-full border-2 border-white shadow-lg cursor-pointer;
    @apply transition-transform duration-200 hover:scale-110;
  }
  
  .map-marker--flight {
    @apply bg-flight-color;
  }
  
  .map-marker--hotel {
    @apply bg-hotel-color;
  }
  
  .map-marker--activity {
    @apply bg-activity-color;
  }
  
  .map-marker--restaurant {
    @apply bg-restaurant-color;
  }
  
  /* Loading Animation */
  .loading-skeleton {
    @apply animate-pulse bg-gray-200 rounded;
  }
  
  /* Travel Input Field */
  .travel-input {
    @apply w-full px-4 py-3 border border-border-medium rounded-lg;
    @apply focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent;
    @apply transition-all duration-200;
  }
  
  /* Responsive Navigation */
  .nav-mobile {
    @apply fixed inset-x-0 bottom-0 bg-card border-t border-border-light;
    @apply flex items-center justify-around py-2 z-50;
  }
  
  .nav-item {
    @apply flex flex-col items-center p-2 rounded-lg transition-colors duration-200;
    @apply hover:bg-gray-100 active:bg-gray-200;
  }
  
  .nav-item--active {
    @apply text-brand-primary;
  }
}

/* Utility Layer - Custom utilities */
@layer utilities {
  /* Travel-specific spacing */
  .space-travel {
    @apply space-y-6 md:space-y-8;
  }
  
  /* Grid layouts for travel cards */
  .travel-grid {
    @apply grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3;
  }
  
  .travel-grid--flights {
    @apply grid-cols-1 lg:grid-cols-2;
  }
  
  /* Responsive text */
  .text-responsive-sm {
    @apply text-sm md:text-base;
  }
  
  .text-responsive-lg {
    @apply text-lg md:text-xl lg:text-2xl;
  }
  
  /* Safe area for mobile */
  .safe-area-bottom {
    padding-bottom: env(safe-area-inset-bottom);
  }
  
  /* Scroll behavior */
  .scroll-smooth {
    scroll-behavior: smooth;
  }
  
  /* Hide scrollbar but keep functionality */
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
  
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
}

/* Print Styles */
@media print {
  .print-hidden {
    display: none !important;
  }
  
  .travel-card {
    break-inside: avoid;
    box-shadow: none;
    border: 1px solid var(--border-light);
  }
}

/* Reduced Motion */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```
