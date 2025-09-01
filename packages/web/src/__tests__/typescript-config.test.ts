import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('TypeScript Configuration', () => {
  const tsconfigPath = path.resolve(__dirname, '../../tsconfig.json')
  const tsconfig = JSON.parse(fs.readFileSync(tsconfigPath, 'utf-8'))

  it('should have strict mode enabled', () => {
    expect(tsconfig.compilerOptions.strict).toBe(true)
  })

  it('should have additional strict type checking options', () => {
    const compilerOptions = tsconfig.compilerOptions
    
    expect(compilerOptions.noUncheckedIndexedAccess).toBe(true)
    expect(compilerOptions.noImplicitReturns).toBe(true)
    expect(compilerOptions.noFallthroughCasesInSwitch).toBe(true)
    expect(compilerOptions.noImplicitOverride).toBe(true)
    expect(compilerOptions.exactOptionalPropertyTypes).toBe(true)
  })

  it('should use proper module resolution for Next.js', () => {
    const compilerOptions = tsconfig.compilerOptions
    
    expect(compilerOptions.module).toBe('esnext')
    expect(compilerOptions.moduleResolution).toBe('bundler')
    expect(compilerOptions.jsx).toBe('preserve')
  })

  it('should have path mapping configured', () => {
    expect(tsconfig.compilerOptions.paths).toEqual({
      '@/*': ['./src/*']
    })
  })

  it('should include proper files and exclude node_modules', () => {
    expect(tsconfig.include).toContain('**/*.ts')
    expect(tsconfig.include).toContain('**/*.tsx')
    expect(tsconfig.exclude).toContain('node_modules')
  })
})