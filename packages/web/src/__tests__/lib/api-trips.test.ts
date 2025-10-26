/**
 * API Client Trip Methods Tests
 * Story 3.5: User Trip List Dashboard
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { ApiClient } from '@/lib/api';
import type { IPaginatedResponse, ITripSummary } from '@/lib/types';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('ApiClient - Trip List Methods', () => {
  let apiClient: ApiClient;

  beforeEach(() => {
    apiClient = new ApiClient('http://localhost:8000');
    apiClient.setToken('test-token-123');
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('getUserTrips', () => {
    it('fetches trips with default pagination', async () => {
      const mockResponse: IPaginatedResponse<ITripSummary[]> = {
        data: [
          {
            trip_id: 'trip-1',
            user_id: 'user-1',
            name: 'Trip to Rome',
            description: 'Amazing trip',
            destination: { city: 'Rome', country: 'Italy' },
            requirements: {
              budget: 3000,
              currency: 'USD',
              start_date: '2025-06-01',
              end_date: '2025-06-07',
              travelers: 2,
            },
            status: 'confirmed',
            created_at: '2025-03-15T10:30:00Z',
            updated_at: '2025-03-15T10:30:00Z',
          },
        ],
        pagination: {
          page: 1,
          per_page: 20,
          total_items: 1,
          total_pages: 1,
          has_next: false,
          has_prev: false,
        },
        message: 'Trips retrieved successfully',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.getUserTrips();

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/trips?page=1&per_page=20',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token-123',
          }),
        })
      );

      expect(result).toEqual(mockResponse);
    });

    it('fetches trips with custom pagination', async () => {
      const mockResponse: IPaginatedResponse<ITripSummary[]> = {
        data: [],
        pagination: {
          page: 2,
          per_page: 10,
          total_items: 45,
          total_pages: 5,
          has_next: true,
          has_prev: true,
        },
        message: 'Trips retrieved successfully',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.getUserTrips(2, 10);

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/trips?page=2&per_page=10',
        expect.anything()
      );

      expect(result.pagination.page).toBe(2);
      expect(result.pagination.per_page).toBe(10);
    });

    it('includes authentication token in request', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          data: [],
          pagination: {
            page: 1,
            per_page: 20,
            total_items: 0,
            total_pages: 0,
            has_next: false,
            has_prev: false,
          },
          message: 'Success',
        }),
      });

      await apiClient.getUserTrips();

      const callArgs = mockFetch.mock.calls[0];
      const headers = callArgs[1].headers;
      expect(headers.Authorization).toBe('Bearer test-token-123');
    });

    it('handles API errors correctly', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({
          message: 'Unauthorized',
        }),
      });

      await expect(apiClient.getUserTrips()).rejects.toThrow();
    });

    it('handles network errors correctly', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(apiClient.getUserTrips()).rejects.toThrow();
    });
  });
});
