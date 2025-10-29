import { describe, it, expect } from "vitest";
import {
  getCoordinatesWithFallback,
  hasValidCoordinates,
  isValidLatLng,
  calculateDistance,
} from "../coordinates";
import type { Location } from "@/lib/types/map";

describe("coordinates utility functions", () => {
  describe("getCoordinatesWithFallback", () => {
    it("should return original coordinates when geocoding succeeded", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "success",
      };

      const result = getCoordinatesWithFallback(location);

      expect(result).toEqual({ lat: 41.9009, lng: 12.4833 });
    });

    it("should return original coordinates when geocoding_status is not set", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
      };

      const result = getCoordinatesWithFallback(location);

      expect(result).toEqual({ lat: 41.9009, lng: 12.4833 });
    });

    it("should return default center when geocoding failed", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "failed",
      };

      const defaultCenter = { lat: 41.9, lng: 12.5 };
      const result = getCoordinatesWithFallback(location, { defaultCenter });

      expect(result).toEqual(defaultCenter);
    });

    it("should return default center when geocoding is pending", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "pending",
      };

      const defaultCenter = { lat: 41.9, lng: 12.5 };
      const result = getCoordinatesWithFallback(location, { defaultCenter });

      expect(result).toEqual(defaultCenter);
    });

    it("should use default (0, 0) when no default center provided and geocoding failed", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "failed",
      };

      const result = getCoordinatesWithFallback(location);

      expect(result).toEqual({ lat: 0, lng: 0 });
    });
  });

  describe("hasValidCoordinates", () => {
    it("should return true for successfully geocoded coordinates", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "success",
      };

      expect(hasValidCoordinates(location)).toBe(true);
    });

    it("should return true when geocoding_status is not set and coordinates are valid", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
      };

      expect(hasValidCoordinates(location)).toBe(true);
    });

    it("should return false when geocoding failed", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "failed",
      };

      expect(hasValidCoordinates(location)).toBe(false);
    });

    it("should return false when geocoding is pending", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 12.4833,
        geocoding_status: "pending",
      };

      expect(hasValidCoordinates(location)).toBe(false);
    });

    it("should return false for invalid latitude", () => {
      const location: Location = {
        latitude: 100, // Invalid: > 90
        longitude: 12.4833,
        geocoding_status: "success",
      };

      expect(hasValidCoordinates(location)).toBe(false);
    });

    it("should return false for invalid longitude", () => {
      const location: Location = {
        latitude: 41.9009,
        longitude: 200, // Invalid: > 180
        geocoding_status: "success",
      };

      expect(hasValidCoordinates(location)).toBe(false);
    });
  });

  describe("isValidLatLng", () => {
    it("should return true for valid coordinates", () => {
      expect(isValidLatLng(41.9009, 12.4833)).toBe(true);
      expect(isValidLatLng(0, 0)).toBe(true);
      expect(isValidLatLng(-90, -180)).toBe(true);
      expect(isValidLatLng(90, 180)).toBe(true);
    });

    it("should return false for latitude out of range", () => {
      expect(isValidLatLng(91, 12.4833)).toBe(false);
      expect(isValidLatLng(-91, 12.4833)).toBe(false);
    });

    it("should return false for longitude out of range", () => {
      expect(isValidLatLng(41.9009, 181)).toBe(false);
      expect(isValidLatLng(41.9009, -181)).toBe(false);
    });

    it("should return false for NaN values", () => {
      expect(isValidLatLng(NaN, 12.4833)).toBe(false);
      expect(isValidLatLng(41.9009, NaN)).toBe(false);
    });

    it("should return false for non-numeric values", () => {
      expect(isValidLatLng("41.9009" as any, 12.4833)).toBe(false);
      expect(isValidLatLng(41.9009, "12.4833" as any)).toBe(false);
    });
  });

  describe("calculateDistance", () => {
    it("should calculate distance between two close points", () => {
      const rome = { lat: 41.9028, lng: 12.4964 };
      const vatican = { lat: 41.9029, lng: 12.4534 };

      const distance = calculateDistance(rome, vatican);

      // Distance should be approximately 3.5 km
      expect(distance).toBeGreaterThan(3);
      expect(distance).toBeLessThan(4);
    });

    it("should return 0 for same coordinates", () => {
      const coord = { lat: 41.9028, lng: 12.4964 };

      const distance = calculateDistance(coord, coord);

      expect(distance).toBe(0);
    });

    it("should calculate distance for far apart points", () => {
      const newYork = { lat: 40.7128, lng: -74.006 };
      const london = { lat: 51.5074, lng: -0.1278 };

      const distance = calculateDistance(newYork, london);

      // Distance should be approximately 5570 km
      expect(distance).toBeGreaterThan(5500);
      expect(distance).toBeLessThan(5600);
    });

    it("should handle crossing the equator", () => {
      const north = { lat: 10, lng: 0 };
      const south = { lat: -10, lng: 0 };

      const distance = calculateDistance(north, south);

      // Distance should be approximately 2223 km (20 degrees * ~111 km/degree)
      expect(distance).toBeGreaterThan(2200);
      expect(distance).toBeLessThan(2250);
    });

    it("should handle crossing the prime meridian", () => {
      const west = { lat: 0, lng: -10 };
      const east = { lat: 0, lng: 10 };

      const distance = calculateDistance(west, east);

      // Distance should be approximately 2223 km
      expect(distance).toBeGreaterThan(2200);
      expect(distance).toBeLessThan(2250);
    });
  });
});
