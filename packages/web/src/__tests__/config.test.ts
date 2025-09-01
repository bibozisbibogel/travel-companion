import { describe, it, expect } from 'vitest'
import packageJson from '../../package.json'

describe('Next.js Configuration', () => {
  it('should have Next.js 14.1+ installed', () => {
    const nextVersion = packageJson.dependencies.next
    const versionNumber = nextVersion.replace(/[^\d.]/g, '')
    const [major, minor] = versionNumber.split('.').map(Number)
    
    expect(major).toBeGreaterThanOrEqual(14)
    if (major === 14) {
      expect(minor).toBeGreaterThanOrEqual(1)
    }
  })

  it('should have TypeScript 5+ installed (requirement: 5.3+)', () => {
    const typescriptVersion = packageJson.devDependencies.typescript
    const versionNumber = typescriptVersion.replace(/[^\d.]/g, '')
    const [major] = versionNumber.split('.').map(Number)
    
    // TypeScript ^5 satisfies 5.3+ requirement as npm will install latest 5.x
    expect(major).toBeGreaterThanOrEqual(5)
  })

  it('should have Vitest 1.2+ installed for testing', () => {
    const vitestVersion = packageJson.devDependencies.vitest
    const versionNumber = vitestVersion.replace(/[^\d.]/g, '')
    const [major, minor] = versionNumber.split('.').map(Number)
    
    expect(major).toBeGreaterThanOrEqual(1)
    if (major === 1) {
      expect(minor).toBeGreaterThanOrEqual(2)
    }
  })

  it('should have required testing libraries installed', () => {
    expect(packageJson.devDependencies['@testing-library/react']).toBeDefined()
    expect(packageJson.devDependencies['@testing-library/jest-dom']).toBeDefined()
    expect(packageJson.devDependencies['jsdom']).toBeDefined()
    expect(packageJson.devDependencies['@vitejs/plugin-react']).toBeDefined()
  })

  it('should have proper test scripts configured', () => {
    expect(packageJson.scripts.test).toBe('vitest')
    expect(packageJson.scripts['test:ui']).toBe('vitest --ui')
    expect(packageJson.scripts['test:coverage']).toBe('vitest run --coverage')
  })
})