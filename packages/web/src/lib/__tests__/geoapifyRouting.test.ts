import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchGeoapifyRoute, fetchDayRoute } from '../geoapifyRouting';

// Mock the fetch function
global.fetch = vi.fn();

describe('geoapifyRouting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up environment variable
    process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY = 'test-api-key';
  });

  describe('fetchGeoapifyRoute', () => {
    it('should return null if API key is missing', async () => {
      process.env.NEXT_PUBLIC_GEOAPIFY_API_KEY = '';
      const result = await fetchGeoapifyRoute([
        { lat: 40.7128, lon: -74.0060 },
        { lat: 40.7589, lon: -73.9851 }
      ]);
      expect(result).toBeNull();
    });

    it('should return null if less than 2 waypoints provided', async () => {
      const result = await fetchGeoapifyRoute([
        { lat: 40.7128, lon: -74.0060 }
      ]);
      expect(result).toBeNull();
    });

    it('should fetch route successfully', async () => {
      const mockResponse = {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [
              [-74.0060, 40.7128],
              [-73.9851, 40.7589]
            ]
          },
          properties: {
            mode: 'walk',
            waypoints: [],
            units: 'metric',
            distance: 1000,
            distance_units: 'meters',
            time: 720,
            legs: [{
              distance: 1000,
              time: 720,
              steps: []
            }]
          }
        }]
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await fetchGeoapifyRoute([
        { lat: 40.7128, lon: -74.0060 },
        { lat: 40.7589, lon: -73.9851 }
      ]);

      expect(result).not.toBeNull();
      expect(result?.coordinates).toHaveLength(2);
      expect(result?.distance).toBe(1000);
      expect(result?.duration).toBe(720);
      expect(result?.legs).toHaveLength(1);
    });

    it('should handle API errors gracefully', async () => {
      (global.fetch as any).mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      });

      const result = await fetchGeoapifyRoute([
        { lat: 40.7128, lon: -74.0060 },
        { lat: 40.7589, lon: -73.9851 }
      ]);

      expect(result).toBeNull();
    });

    it('should handle network errors', async () => {
      (global.fetch as any).mockRejectedValueOnce(new Error('Network error'));

      const result = await fetchGeoapifyRoute([
        { lat: 40.7128, lon: -74.0060 },
        { lat: 40.7589, lon: -73.9851 }
      ]);

      expect(result).toBeNull();
    });
  });

  describe('fetchDayRoute', () => {
    it('should return null if less than 2 locations', async () => {
      const result = await fetchDayRoute([
        { latitude: 40.7128, longitude: -74.0060 }
      ]);
      expect(result).toBeNull();
    });

    it('should call fetchGeoapifyRoute with correct waypoints', async () => {
      const mockResponse = {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          geometry: {
            type: 'LineString',
            coordinates: [
              [-74.0060, 40.7128],
              [-73.9851, 40.7589]
            ]
          },
          properties: {
            mode: 'walk',
            waypoints: [],
            units: 'metric',
            distance: 1000,
            distance_units: 'meters',
            time: 720,
            legs: [{
              distance: 1000,
              time: 720,
              steps: []
            }]
          }
        }]
      };

      (global.fetch as any).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse
      });

      const result = await fetchDayRoute([
        { latitude: 40.7128, longitude: -74.0060 },
        { latitude: 40.7589, longitude: -73.9851 }
      ], 'walk');

      expect(result).not.toBeNull();
      expect(fetch).toHaveBeenCalled();
    });
  });
});
