import { describe, it, expect } from 'vitest'
import { 
  loginSchema, 
  registerSchema,
  travelRequestSchema,
  calculatePasswordStrength, 
  getPasswordStrengthColor, 
  getPasswordStrengthLabel 
} from '../../lib/validation'

describe('Login Schema Validation', () => {
  it('should validate a correct login form', () => {
    const validData = {
      email: 'test@example.com',
      password: 'Password123!'
    }
    
    const result = loginSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('should reject invalid email formats', () => {
    const invalidData = {
      email: 'invalid-email',
      password: 'Password123!'
    }
    
    const result = loginSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0]?.message).toContain('valid email')
    }
  })

  it('should reject empty email', () => {
    const invalidData = {
      email: '',
      password: 'Password123!'
    }
    
    const result = loginSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe('Email is required')
    }
  })

  it('should reject short passwords', () => {
    const invalidData = {
      email: 'test@example.com',
      password: 'short'
    }
    
    const result = loginSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('at least 8 characters')
    }
  })

  it('should reject empty password', () => {
    const invalidData = {
      email: 'test@example.com',
      password: ''
    }
    
    const result = loginSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe('Password is required')
    }
  })
})

describe('Register Schema Validation', () => {
  it('should validate a correct registration form', () => {
    const validData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'Password123!',
      confirmPassword: 'Password123!'
    }
    
    const result = registerSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('should reject names that are too short', () => {
    const invalidData = {
      name: 'J',
      email: 'john@example.com',
      password: 'Password123!',
      confirmPassword: 'Password123!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('at least 2 characters')
    }
  })

  it('should reject names that are too long', () => {
    const invalidData = {
      name: 'a'.repeat(51),
      email: 'john@example.com',
      password: 'Password123!',
      confirmPassword: 'Password123!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('cannot exceed 50 characters')
    }
  })

  it('should reject password without uppercase letter', () => {
    const invalidData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'password123!',
      confirmPassword: 'password123!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.message.includes('uppercase'))).toBe(true)
    }
  })

  it('should reject password without lowercase letter', () => {
    const invalidData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'PASSWORD123!',
      confirmPassword: 'PASSWORD123!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.message.includes('lowercase'))).toBe(true)
    }
  })

  it('should reject password without number', () => {
    const invalidData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'Password!',
      confirmPassword: 'Password!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.message.includes('number'))).toBe(true)
    }
  })

  it('should reject password without special character', () => {
    const invalidData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'Password123',
      confirmPassword: 'Password123'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.message.includes('special character'))).toBe(true)
    }
  })

  it('should reject mismatched passwords', () => {
    const invalidData = {
      name: 'John Doe',
      email: 'john@example.com',
      password: 'Password123!',
      confirmPassword: 'DifferentPassword123!'
    }
    
    const result = registerSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.some(issue => issue.message.includes("don't match"))).toBe(true)
    }
  })
})

describe('Password Strength Calculation', () => {
  it('should return score 0 for empty password', () => {
    const result = calculatePasswordStrength('')
    expect(result.score).toBe(0)
    expect(result.isValid).toBe(false)
    expect(result.feedback.suggestions).toContain('Enter a password')
  })

  it('should return low score for weak password', () => {
    const result = calculatePasswordStrength('password')
    expect(result.score).toBeLessThan(3)
    expect(result.isValid).toBe(false)
    expect(result.feedback.suggestions.length).toBeGreaterThan(0)
  })

  it('should return high score for strong password', () => {
    const result = calculatePasswordStrength('MyStrongPassword123!')
    expect(result.score).toBeGreaterThanOrEqual(4)
    expect(result.isValid).toBe(true)
  })

  it('should provide feedback for missing requirements', () => {
    const result = calculatePasswordStrength('password')
    expect(result.feedback.suggestions).toContain('Add uppercase letters')
    expect(result.feedback.suggestions).toContain('Add numbers')
    expect(result.feedback.suggestions).toContain('Add special characters (!@#$%^&*)')
  })

  it('should give bonus points for longer passwords', () => {
    const shortPassword = calculatePasswordStrength('Pass123!')
    const longPassword = calculatePasswordStrength('MyVeryLongAndSecurePassword123!')
    expect(longPassword.score).toBeGreaterThanOrEqual(shortPassword.score)
  })

  it('should cap score at 4', () => {
    const result = calculatePasswordStrength('MyExtremelyLongAndVerySecurePasswordWithManyCharacters123!@#$%^&*()')
    expect(result.score).toBeLessThanOrEqual(4)
  })

  it('should set warning for very weak passwords', () => {
    const result = calculatePasswordStrength('ab')
    expect(result.feedback.warning).toBe('This password is too weak')
  })

  it('should set warning for weak passwords', () => {
    const result = calculatePasswordStrength('password')
    // This password has 2 criteria (length + lowercase) so score is 2
    expect(result.score).toBe(2)
    expect(result.feedback.warning).toBe('This password could be stronger')
  })

  it('should not set warning for strong passwords', () => {
    const result = calculatePasswordStrength('MyStrongPassword123!')
    expect(result.feedback.warning).toBeUndefined()
  })
})

describe('Travel Request Schema Validation', () => {
  it('should validate a correct travel request form', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const validData = {
      destination: 'Tokyo, Japan',
      startDate,
      endDate,
      budget: 3000,
      travelers: 2,
      preferences: ['culture', 'food']
    }
    
    const result = travelRequestSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })

  it('should reject empty destination', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const invalidData = {
      destination: '',
      startDate,
      endDate,
      travelers: 2
    }
    
    const result = travelRequestSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toBe('Destination is required')
    }
  })

  it('should reject past start dates', () => {
    const invalidData = {
      destination: 'Paris',
      startDate: '2020-01-01',
      endDate: '2020-01-07',
      travelers: 2
    }
    
    const result = travelRequestSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues[0].message).toContain('cannot be in the past')
    }
  })

  it('should reject end date before start date', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() - 3) // End date before start date
    const endDate = futureDate.toISOString().split('T')[0]
    
    const invalidData = {
      destination: 'London',
      startDate,
      endDate,
      travelers: 2
    }
    
    const result = travelRequestSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      const errorMessage = result.error.issues.find(issue => issue.path.includes('endDate'))?.message
      expect(errorMessage).toBe('End date must be after start date')
    }
  })

  it('should reject budget below minimum', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const invalidData = {
      destination: 'Rome',
      startDate,
      endDate,
      budget: 50,
      travelers: 2
    }
    
    const result = travelRequestSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      const budgetError = result.error.issues.find(issue => issue.path.includes('budget'))
      expect(budgetError?.message).toContain('at least $100')
    }
  })

  it('should reject budget above maximum', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const invalidData = {
      destination: 'Dubai',
      startDate,
      endDate,
      budget: 200000,
      travelers: 2
    }
    
    const result = travelRequestSchema.safeParse(invalidData)
    expect(result.success).toBe(false)
    if (!result.success) {
      const budgetError = result.error.issues.find(issue => issue.path.includes('budget'))
      expect(budgetError?.message).toContain('cannot exceed $100,000')
    }
  })

  it('should reject invalid traveler counts', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const invalidDataZero = {
      destination: 'Barcelona',
      startDate,
      endDate,
      travelers: 0
    }
    
    const resultZero = travelRequestSchema.safeParse(invalidDataZero)
    expect(resultZero.success).toBe(false)

    const invalidDataTooMany = {
      destination: 'Barcelona',
      startDate,
      endDate,
      travelers: 25
    }
    
    const resultTooMany = travelRequestSchema.safeParse(invalidDataTooMany)
    expect(resultTooMany.success).toBe(false)
  })

  it('should accept optional budget and preferences', () => {
    const futureDate = new Date()
    futureDate.setMonth(futureDate.getMonth() + 2)
    const startDate = futureDate.toISOString().split('T')[0]
    futureDate.setDate(futureDate.getDate() + 6)
    const endDate = futureDate.toISOString().split('T')[0]
    
    const validData = {
      destination: 'Amsterdam',
      startDate,
      endDate,
      travelers: 1
    }
    
    const result = travelRequestSchema.safeParse(validData)
    expect(result.success).toBe(true)
  })
})

describe('Password Strength Utilities', () => {
  it('should return correct colors for different scores', () => {
    expect(getPasswordStrengthColor(0)).toContain('red')
    expect(getPasswordStrengthColor(1)).toContain('red')
    expect(getPasswordStrengthColor(2)).toContain('yellow')
    expect(getPasswordStrengthColor(3)).toContain('blue')
    expect(getPasswordStrengthColor(4)).toContain('green')
  })

  it('should return correct labels for different scores', () => {
    expect(getPasswordStrengthLabel(0)).toBe('Very Weak')
    expect(getPasswordStrengthLabel(1)).toBe('Weak')
    expect(getPasswordStrengthLabel(2)).toBe('Fair')
    expect(getPasswordStrengthLabel(3)).toBe('Good')
    expect(getPasswordStrengthLabel(4)).toBe('Strong')
  })

  it('should handle scores outside normal range', () => {
    expect(getPasswordStrengthLabel(5)).toBe('Strong')
    expect(getPasswordStrengthLabel(-1)).toBe('Very Weak')
  })
})