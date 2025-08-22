# Frontend Developer Standards

## Critical Coding Rules

**Performance & Bundle Size:**
- Never import entire libraries - use tree-shaking and dynamic imports: `const Map = dynamic(() => import('@/components/maps/InteractiveMap'), { ssr: false })`
- Lazy load heavy components (maps, PDF generator) and non-critical features
- Use React.memo() for expensive re-renders in travel list components
- Implement proper loading states for all async operations

**Type Safety:**
- All props must have TypeScript interfaces - no `any` types allowed
- API responses must match backend TypeScript types exactly
- Use discriminated unions for component variants: `type CardVariant = 'flight' | 'hotel' | 'activity'`

**State Management:**
- Never mutate state directly - use Zustand actions for all state changes
- Keep component state minimal - lift shared state to Zustand stores
- Use proper dependency arrays in useEffect - avoid infinite re-renders

**API Integration:**
- All API calls must include error handling and loading states
- Use proper TypeScript types for API responses - never `any`
- Implement request cancellation for component unmounting: `useEffect(() => { const controller = new AbortController(); return () => controller.abort(); }, [])`

**Accessibility:**
- All interactive elements must be keyboard accessible with proper `tabIndex`
- Images require descriptive `alt` text, especially for travel photos and maps
- Form inputs must have associated labels: `<label htmlFor="destination">Destination</label>`
- Use proper ARIA labels for complex components: `aria-label`, `aria-describedby`

**Mobile & Responsive:**
- Test all components at 320px width minimum (iPhone SE)
- Use touch-friendly targets (44px minimum) for mobile interactions
- Implement proper swipe gestures for mobile card carousels
- Never rely on hover states for critical functionality

## Quick Reference

**Development Commands:**
```bash