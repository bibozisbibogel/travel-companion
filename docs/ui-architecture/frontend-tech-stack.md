# Frontend Tech Stack

This section aligns with and extends the main architecture document's technology choices, providing frontend-specific implementations.

## Technology Stack Table

| Category | Technology | Version | Purpose | Rationale |
|----------|------------|---------|---------|-----------|
| **Framework** | Next.js | 14.1+ | React-based web application | App Router for performance, built-in optimization, excellent TypeScript support |
| **Language** | TypeScript | 5.3+ | Type-safe frontend development | Matches backend types, prevents runtime errors, excellent DX |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first styling | Rapid development, consistent design system, mobile-first approach |
| **UI Library** | shadcn/ui | Latest | Component foundation | Accessible components, customizable, Tailwind-native |
| **State Management** | Zustand | 4.4+ | Client state management | Lightweight, TypeScript-first, simple patterns for travel data |
| **Routing** | Next.js App Router | Built-in | File-based routing | Server components, layout nesting, parallel routes for dashboard |
| **Build Tool** | Next.js/Turbopack | Built-in | Development and build | Fast refresh, optimized bundles, built-in optimizations |
| **HTTP Client** | Axios | 1.6+ | API communication | Interceptors for auth, request/response transformation |
| **Form Handling** | React Hook Form | 7.48+ | Form state and validation | Performance, TypeScript integration, minimal re-renders |
| **Map Integration** | Mapbox GL JS | 2.15+ | Interactive maps | Travel-focused features, customization, performance |
| **Animation** | Framer Motion | 10.16+ | Animations and transitions | Declarative animations, gesture support, React integration |
| **Testing** | Vitest + React Testing Library | Latest | Unit and integration testing | Fast, Vite-based, excellent React support |
| **E2E Testing** | Playwright | 1.40+ | End-to-end testing | Cross-browser, travel flow testing, screenshot comparison |
| **Component Library** | Headless UI | 1.7+ | Unstyled accessible components | Accessibility-first, full keyboard navigation |
| **Date Handling** | date-fns | 3.0+ | Date manipulation | Lightweight, immutable, excellent timezone support |
| **PDF Generation** | jsPDF + html2canvas | Latest | Client-side PDF export | Offline capability, full itinerary formatting |
| **Dev Tools** | Storybook | 7.6+ | Component development | Isolated development, documentation, testing |
