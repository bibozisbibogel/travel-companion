import { describe, it, expect } from 'vitest'

describe('Tailwind CSS Responsive Design', () => {
  it('should have custom breakpoints defined', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    
    const expectedBreakpoints = {
      xs: '475px',
      sm: '640px', 
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1536px'
    }
    
    expect(tailwindConfig.theme.screens).toEqual(expectedBreakpoints)
  })

  it('should have custom color palette with CSS variables', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    
    // Verify primary colors are defined
    expect(tailwindConfig.theme.extend.colors.primary).toBeDefined()
    expect(tailwindConfig.theme.extend.colors.primary['500']).toBe('rgb(var(--color-primary-500) / <alpha-value>)')
    
    // Verify secondary colors are defined  
    expect(tailwindConfig.theme.extend.colors.secondary).toBeDefined()
    expect(tailwindConfig.theme.extend.colors.secondary['500']).toBe('rgb(var(--color-secondary-500) / <alpha-value>)')
    
    // Verify status colors
    expect(tailwindConfig.theme.extend.colors.success).toBeDefined()
    expect(tailwindConfig.theme.extend.colors.warning).toBeDefined()
    expect(tailwindConfig.theme.extend.colors.error).toBeDefined()
  })

  it('should have custom spacing scale', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    
    expect(tailwindConfig.theme.extend.spacing).toEqual({
      '18': '4.5rem',
      '88': '22rem', 
      '128': '32rem'
    })
  })

  it('should have enhanced animation keyframes', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    const keyframes = tailwindConfig.theme.extend.keyframes
    
    expect(keyframes.fadeIn).toBeDefined()
    expect(keyframes.slideUp).toBeDefined()
    expect(keyframes.slideDown).toBeDefined()
    expect(keyframes.slideLeft).toBeDefined()
    expect(keyframes.slideRight).toBeDefined()
  })

  it('should have travel-specific animations', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    const animations = tailwindConfig.theme.extend.animation
    
    expect(animations['fade-in']).toBe('fadeIn 0.3s ease-in-out')
    expect(animations['slide-up']).toBe('slideUp 0.3s ease-out')
    expect(animations['slide-down']).toBe('slideDown 0.3s ease-out')
    expect(animations['pulse-slow']).toBe('pulse 2s ease-in-out infinite')
  })

  it('should have custom grid templates for responsive layouts', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    const gridTemplates = tailwindConfig.theme.extend.gridTemplateColumns
    
    expect(gridTemplates['auto-fit-xs']).toBe('repeat(auto-fit, minmax(16rem, 1fr))')
    expect(gridTemplates['auto-fit-sm']).toBe('repeat(auto-fit, minmax(20rem, 1fr))')
    expect(gridTemplates['auto-fit-md']).toBe('repeat(auto-fit, minmax(24rem, 1fr))')
  })

  it('should have travel-specific background gradients', () => {
    const tailwindConfig = require('../../tailwind.config.js')
    const backgroundImage = tailwindConfig.theme.extend.backgroundImage
    
    expect(backgroundImage['gradient-travel']).toBe(
      'linear-gradient(135deg, rgb(var(--color-primary-500)), rgb(var(--color-secondary-500)))'
    )
  })
})