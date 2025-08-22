# Component Standards

## Component Template

```typescript
'use client'

import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

interface FlightCardProps {
  flight: FlightOption
  isSelected?: boolean
  onSelect?: (flightId: string) => void
  onCompare?: (flightId: string) => void
  className?: string
}

export const FlightCard = forwardRef<HTMLDivElement, FlightCardProps>(
  ({ flight, isSelected = false, onSelect, onCompare, className, ...props }, ref) => {
    const handleSelect = () => {
      onSelect?.(flight.flight_id)
    }

    const handleCompare = (e: React.MouseEvent) => {
      e.stopPropagation()
      onCompare?.(flight.flight_id)
    }

    return (
      <div
        ref={ref}
        className={cn(
          'rounded-lg border bg-card text-card-foreground shadow-sm transition-all duration-200',
          'hover:shadow-md hover:-translate-y-1',
          isSelected && 'ring-2 ring-primary ring-offset-2',
          'cursor-pointer',
          className
        )}
        onClick={handleSelect}
        role="button"
        tabIndex={0}
        aria-selected={isSelected}
        aria-label={`Flight ${flight.airline} departing ${flight.departure_time}`}
        {...props}
      >
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">{flight.airline}</p>
              <p className="text-sm text-muted-foreground">{flight.flight_number}</p>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold">${flight.price}</p>
              <p className="text-sm text-muted-foreground">{flight.currency}</p>
            </div>
          </div>
          
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm">
              <p className="font-medium">{flight.departure_time}</p>
              <p className="text-muted-foreground">{flight.origin}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-muted-foreground">
                {Math.floor(flight.duration_minutes / 60)}h {flight.duration_minutes % 60}m
              </p>
              <p className="text-xs text-muted-foreground">
                {flight.stops === 0 ? 'Direct' : `${flight.stops} stop${flight.stops > 1 ? 's' : ''}`}
              </p>
            </div>
            <div className="text-right text-sm">
              <p className="font-medium">{flight.arrival_time}</p>
              <p className="text-muted-foreground">{flight.destination}</p>
            </div>
          </div>
          
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={handleCompare}>
              Compare
            </Button>
            <Button size="sm" disabled={isSelected}>
              {isSelected ? 'Selected' : 'Select Flight'}
            </Button>
          </div>
        </div>
      </div>
    )
  }
)

FlightCard.displayName = 'FlightCard'

export type { FlightCardProps }
```

## Naming Conventions

**Components:**
- PascalCase for component names: `FlightCard`, `TravelRequestForm`
- Props interfaces: `ComponentNameProps` (e.g., `FlightCardProps`)
- Event handlers: `handleActionName` (e.g., `handleSelect`, `handleFilterChange`)

**Files:**
- Component files: PascalCase matching component name
- Utility files: camelCase (e.g., `apiClient.ts`, `formatUtils.ts`)
- Hook files: camelCase with "use" prefix (e.g., `useAuth.ts`)
- Type definition files: camelCase (e.g., `travel.ts`, `api.ts`)

**CSS Classes:**
- Tailwind utility classes preferred
- Custom classes: kebab-case with component prefix (e.g., `flight-card-selected`)
- CSS custom properties: kebab-case (e.g., `--brand-primary`)

**State and Variables:**
- camelCase for variables and state: `selectedFlight`, `isLoading`
- UPPER_SNAKE_CASE for constants: `API_BASE_URL`, `MAX_TRAVELERS`
- Boolean variables: prefix with "is", "has", "can", "should" (e.g., `isSelected`, `hasError`)
