/**
 * Form validation schemas and utilities for Travel Companion
 */

import { z } from 'zod'
import type { IPasswordStrength } from './types'

// Login validation schema
export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters long'),
})

// Registration validation schema
export const registerSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .min(2, 'Name must be at least 2 characters long')
    .max(50, 'Name cannot exceed 50 characters'),
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters long')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number')
    .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
  confirmPassword: z
    .string()
    .min(1, 'Please confirm your password'),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
})

// Travel request validation schema
export const travelRequestSchema = z.object({
  destination: z
    .string()
    .min(1, 'Destination is required')
    .min(2, 'Please enter a valid destination'),
  startDate: z
    .string()
    .min(1, 'Start date is required')
    .refine((date) => {
      const selected = new Date(date)
      const today = new Date()
      today.setHours(0, 0, 0, 0)
      return selected >= today
    }, 'Start date cannot be in the past'),
  endDate: z
    .string()
    .min(1, 'End date is required'),
  budget: z
    .number()
    .min(100, 'Budget must be at least $100')
    .max(100000, 'Budget cannot exceed $100,000')
    .optional(),
  travelers: z
    .number()
    .min(1, 'At least 1 traveler is required')
    .max(20, 'Cannot exceed 20 travelers'),
  preferences: z
    .array(z.string())
    .optional(),
}).refine((data) => {
  const start = new Date(data.startDate)
  const end = new Date(data.endDate)
  return end > start
}, {
  message: "End date must be after start date",
  path: ["endDate"],
})

export type LoginFormData = z.infer<typeof loginSchema>
export type RegisterFormData = z.infer<typeof registerSchema>
export type TravelRequestFormData = z.infer<typeof travelRequestSchema>

/**
 * Calculate password strength score based on various criteria
 */
export function calculatePasswordStrength(password: string): IPasswordStrength {
  if (!password) {
    return {
      score: 0,
      feedback: { suggestions: ['Enter a password'] },
      isValid: false,
    }
  }

  let score = 0
  const feedback: string[] = []

  // Length check
  if (password.length >= 8) score += 1
  else feedback.push('Use at least 8 characters')

  // Character variety
  if (/[a-z]/.test(password)) score += 1
  else feedback.push('Add lowercase letters')

  if (/[A-Z]/.test(password)) score += 1
  else feedback.push('Add uppercase letters')

  if (/[0-9]/.test(password)) score += 1
  else feedback.push('Add numbers')

  if (/[^A-Za-z0-9]/.test(password)) score += 1
  else feedback.push('Add special characters (!@#$%^&*)')

  // Bonus points for longer passwords
  if (password.length >= 12) score += 1
  if (password.length >= 16) score += 1

  // Cap the score at 4
  score = Math.min(score, 4)

  // Determine if password meets minimum requirements
  const isValid = score >= 4 && 
    password.length >= 8 && 
    /[A-Z]/.test(password) && 
    /[a-z]/.test(password) && 
    /[0-9]/.test(password) && 
    /[^A-Za-z0-9]/.test(password)

  let warning: string | undefined
  if (score < 2) warning = 'This password is too weak'
  else if (score < 3) warning = 'This password could be stronger'

  const feedbackObj: { warning?: string; suggestions: string[] } = {
    suggestions: feedback,
  }
  
  if (warning) {
    feedbackObj.warning = warning
  }

  return {
    score,
    feedback: feedbackObj,
    isValid,
  }
}

/**
 * Get password strength color based on score
 */
export function getPasswordStrengthColor(score: number): string {
  switch (score) {
    case 0:
    case 1:
      return 'text-red-600 bg-red-100'
    case 2:
      return 'text-yellow-600 bg-yellow-100'
    case 3:
      return 'text-blue-600 bg-blue-100'
    case 4:
    default:
      return 'text-green-600 bg-green-100'
  }
}

/**
 * Get password strength label based on score
 */
export function getPasswordStrengthLabel(score: number): string {
  if (score < 0) return 'Very Weak'
  
  switch (score) {
    case 0:
      return 'Very Weak'
    case 1:
      return 'Weak'
    case 2:
      return 'Fair'
    case 3:
      return 'Good'
    case 4:
    default:
      return 'Strong'
  }
}