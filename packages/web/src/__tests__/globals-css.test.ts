import { describe, it, expect } from 'vitest'
import fs from 'fs'
import path from 'path'

describe('globals.css Design System', () => {
  const globalsCssPath = path.resolve(__dirname, '../app/globals.css')
  const globalsCssContent = fs.readFileSync(globalsCssPath, 'utf-8')

  it('should have Travel Companion design system variables', () => {
    // Check for primary colors
    expect(globalsCssContent).toContain('--color-primary-50: 240, 249, 255')
    expect(globalsCssContent).toContain('--color-primary-500: 14, 165, 233')
    expect(globalsCssContent).toContain('--color-primary-950: 8, 47, 73')

    // Check for secondary colors  
    expect(globalsCssContent).toContain('--color-secondary-50: 255, 251, 235')
    expect(globalsCssContent).toContain('--color-secondary-500: 245, 158, 11')
    expect(globalsCssContent).toContain('--color-secondary-950: 69, 26, 3')
  })

  it('should have neutral gray colors', () => {
    expect(globalsCssContent).toContain('--color-gray-50: 249, 250, 251')
    expect(globalsCssContent).toContain('--color-gray-500: 107, 114, 128')
    expect(globalsCssContent).toContain('--color-gray-950: 3, 7, 18')
  })

  it('should have status colors defined', () => {
    expect(globalsCssContent).toContain('--color-success-500: 34, 197, 94')
    expect(globalsCssContent).toContain('--color-warning-500: 245, 158, 11')
    expect(globalsCssContent).toContain('--color-error-500: 239, 68, 68')
  })

  it('should have shadow design tokens', () => {
    expect(globalsCssContent).toContain('--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05)')
    expect(globalsCssContent).toContain('--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1)')
    expect(globalsCssContent).toContain('--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1)')
    expect(globalsCssContent).toContain('--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1)')
  })

  it('should have spacing scale tokens', () => {
    expect(globalsCssContent).toContain('--spacing-xs: 0.25rem')
    expect(globalsCssContent).toContain('--spacing-sm: 0.5rem')
    expect(globalsCssContent).toContain('--spacing-md: 1rem')
    expect(globalsCssContent).toContain('--spacing-lg: 1.5rem')
    expect(globalsCssContent).toContain('--spacing-xl: 2rem')
    expect(globalsCssContent).toContain('--spacing-2xl: 3rem')
  })

  it('should have typography scale tokens', () => {
    expect(globalsCssContent).toContain('--font-size-xs: 0.75rem')
    expect(globalsCssContent).toContain('--font-size-sm: 0.875rem')
    expect(globalsCssContent).toContain('--font-size-base: 1rem')
    expect(globalsCssContent).toContain('--font-size-4xl: 2.25rem')
  })

  it('should have border radius tokens', () => {
    expect(globalsCssContent).toContain('--radius-sm: 0.125rem')
    expect(globalsCssContent).toContain('--radius-md: 0.375rem')
    expect(globalsCssContent).toContain('--radius-lg: 0.5rem')
    expect(globalsCssContent).toContain('--radius-full: 9999px')
  })

  it('should have dark mode support', () => {
    expect(globalsCssContent).toContain('@media (prefers-color-scheme: dark)')
    // Dark mode should invert gray scale
    expect(globalsCssContent).toContain('--color-gray-50: 3, 7, 18')
    expect(globalsCssContent).toContain('--color-gray-950: 249, 250, 251')
  })

  it('should have component layer styles', () => {
    expect(globalsCssContent).toContain('@layer components')
    expect(globalsCssContent).toContain('.btn-primary')
    expect(globalsCssContent).toContain('.btn-secondary')
    expect(globalsCssContent).toContain('.btn-outline')
    expect(globalsCssContent).toContain('.card')
    expect(globalsCssContent).toContain('.form-input')
    expect(globalsCssContent).toContain('.form-label')
    expect(globalsCssContent).toContain('.form-error')
  })

  it('should have utility layer styles', () => {
    expect(globalsCssContent).toContain('@layer utilities')
    expect(globalsCssContent).toContain('.text-balance')
    expect(globalsCssContent).toContain('.bg-gradient-travel')
    expect(globalsCssContent).toContain('.text-gradient-travel')
    expect(globalsCssContent).toContain('.shadow-travel')
    expect(globalsCssContent).toContain('.animate-fade-in')
    expect(globalsCssContent).toContain('.animate-slide-up')
  })

  it('should have keyframe animations', () => {
    expect(globalsCssContent).toContain('@keyframes fadeIn')
    expect(globalsCssContent).toContain('@keyframes slideUp')
    expect(globalsCssContent).toContain('from { opacity: 0; }')
    expect(globalsCssContent).toContain('to { opacity: 1; }')
  })

  it('should have proper base styles', () => {
    expect(globalsCssContent).toContain('* {')
    expect(globalsCssContent).toContain('box-sizing: border-box')
    expect(globalsCssContent).toContain('margin: 0')
    expect(globalsCssContent).toContain('padding: 0')
    
    expect(globalsCssContent).toContain('html {')
    expect(globalsCssContent).toContain('scroll-behavior: smooth')
    
    expect(globalsCssContent).toContain('body {')
    expect(globalsCssContent).toContain('-webkit-font-smoothing: antialiased')
  })
})