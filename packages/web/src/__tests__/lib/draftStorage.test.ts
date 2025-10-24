import { describe, it, expect, beforeEach, vi } from 'vitest'
import {
  saveDraft,
  loadDraft,
  clearDraft,
  hasDraft,
  getDraftTimestamp,
} from '../../lib/draftStorage'

const mockFormData = {
  destination: 'Paris',
  origin: 'New York',
  startDate: '2025-11-01',
  endDate: '2025-11-07',
  travelers: {
    adults: 2,
    children: 1,
    infants: 0,
  },
  budget: {
    amount: 3000,
    currency: 'EUR',
  },
  preferences: ['culture', 'food'],
  dietaryRestrictions: ['vegetarian'],
  accommodationTypes: ['hotel'],
  cuisinePreferences: ['local', 'french'],
}

describe('draftStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('saveDraft', () => {
    it('saves draft to localStorage', () => {
      saveDraft(mockFormData)

      const saved = localStorage.getItem('trip-preferences-draft')
      expect(saved).toBeTruthy()
      expect(JSON.parse(saved!)).toEqual(mockFormData)
    })

    it('saves timestamp when saving draft', () => {
      const beforeSave = new Date()
      saveDraft(mockFormData)
      const afterSave = new Date()

      const timestamp = localStorage.getItem('trip-preferences-draft-timestamp')
      expect(timestamp).toBeTruthy()

      const savedDate = new Date(timestamp!)
      expect(savedDate.getTime()).toBeGreaterThanOrEqual(beforeSave.getTime())
      expect(savedDate.getTime()).toBeLessThanOrEqual(afterSave.getTime())
    })

    it('handles errors gracefully', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const setItemSpy = vi.spyOn(Storage.prototype, 'setItem')
        .mockImplementation(() => {
          throw new Error('Storage error')
        })

      expect(() => saveDraft(mockFormData)).not.toThrow()
      expect(consoleErrorSpy).toHaveBeenCalled()

      setItemSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })
  })

  describe('loadDraft', () => {
    it('loads draft from localStorage', () => {
      localStorage.setItem('trip-preferences-draft', JSON.stringify(mockFormData))

      const loaded = loadDraft()
      expect(loaded).toEqual(mockFormData)
    })

    it('returns null when no draft exists', () => {
      const loaded = loadDraft()
      expect(loaded).toBeNull()
    })

    it('handles corrupted data gracefully', () => {
      localStorage.setItem('trip-preferences-draft', 'invalid json')
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      const loaded = loadDraft()
      expect(loaded).toBeNull()
      expect(consoleErrorSpy).toHaveBeenCalled()

      consoleErrorSpy.mockRestore()
    })
  })

  describe('clearDraft', () => {
    it('removes draft from localStorage', () => {
      localStorage.setItem('trip-preferences-draft', JSON.stringify(mockFormData))
      localStorage.setItem('trip-preferences-draft-timestamp', new Date().toISOString())

      clearDraft()

      expect(localStorage.getItem('trip-preferences-draft')).toBeNull()
      expect(localStorage.getItem('trip-preferences-draft-timestamp')).toBeNull()
    })

    it('handles errors gracefully', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const removeItemSpy = vi.spyOn(Storage.prototype, 'removeItem')
        .mockImplementation(() => {
          throw new Error('Storage error')
        })

      expect(() => clearDraft()).not.toThrow()
      expect(consoleErrorSpy).toHaveBeenCalled()

      removeItemSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })
  })

  describe('hasDraft', () => {
    it('returns true when draft exists', () => {
      localStorage.setItem('trip-preferences-draft', JSON.stringify(mockFormData))

      expect(hasDraft()).toBe(true)
    })

    it('returns false when no draft exists', () => {
      expect(hasDraft()).toBe(false)
    })

    it('returns false on error', () => {
      const getItemSpy = vi.spyOn(Storage.prototype, 'getItem')
        .mockImplementation(() => {
          throw new Error('Storage error')
        })

      expect(hasDraft()).toBe(false)

      getItemSpy.mockRestore()
    })
  })

  describe('getDraftTimestamp', () => {
    it('returns timestamp when it exists', () => {
      const now = new Date()
      localStorage.setItem('trip-preferences-draft-timestamp', now.toISOString())

      const timestamp = getDraftTimestamp()
      expect(timestamp).toBeInstanceOf(Date)
      expect(timestamp?.toISOString()).toBe(now.toISOString())
    })

    it('returns null when no timestamp exists', () => {
      const timestamp = getDraftTimestamp()
      expect(timestamp).toBeNull()
    })

    it('returns null on error', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      const getItemSpy = vi.spyOn(Storage.prototype, 'getItem')
        .mockImplementation(() => {
          throw new Error('Storage error')
        })

      const timestamp = getDraftTimestamp()
      expect(timestamp).toBeNull()
      expect(consoleErrorSpy).toHaveBeenCalled()

      getItemSpy.mockRestore()
      consoleErrorSpy.mockRestore()
    })
  })
})
