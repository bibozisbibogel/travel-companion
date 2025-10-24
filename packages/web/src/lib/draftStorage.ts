/**
 * Draft storage utilities for persisting trip preferences to localStorage
 */

import type { TravelRequestFormData } from './validation'

const DRAFT_KEY = 'trip-preferences-draft'
const DRAFT_TIMESTAMP_KEY = 'trip-preferences-draft-timestamp'

/**
 * Save trip preferences draft to localStorage
 */
export function saveDraft(data: Partial<TravelRequestFormData>): void {
  try {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(data))
    localStorage.setItem(DRAFT_TIMESTAMP_KEY, new Date().toISOString())
  } catch (error) {
    console.error('Failed to save draft:', error)
  }
}

/**
 * Load trip preferences draft from localStorage
 */
export function loadDraft(): Partial<TravelRequestFormData> | null {
  try {
    const draft = localStorage.getItem(DRAFT_KEY)
    if (!draft) return null

    return JSON.parse(draft)
  } catch (error) {
    console.error('Failed to load draft:', error)
    return null
  }
}

/**
 * Clear trip preferences draft from localStorage
 */
export function clearDraft(): void {
  try {
    localStorage.removeItem(DRAFT_KEY)
    localStorage.removeItem(DRAFT_TIMESTAMP_KEY)
  } catch (error) {
    console.error('Failed to clear draft:', error)
  }
}

/**
 * Get draft timestamp
 */
export function getDraftTimestamp(): Date | null {
  try {
    const timestamp = localStorage.getItem(DRAFT_TIMESTAMP_KEY)
    return timestamp ? new Date(timestamp) : null
  } catch (error) {
    console.error('Failed to get draft timestamp:', error)
    return null
  }
}

/**
 * Check if a draft exists
 */
export function hasDraft(): boolean {
  try {
    return localStorage.getItem(DRAFT_KEY) !== null
  } catch (error) {
    return false
  }
}
