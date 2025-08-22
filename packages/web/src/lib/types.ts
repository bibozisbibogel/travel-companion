/**
 * Shared TypeScript type definitions for the Travel Companion frontend
 */

export interface IUser {
  id: string;
  email: string;
  name: string;
  createdAt: string;
}

export interface ITripRequest {
  destination: string;
  startDate: string;
  endDate: string;
  budget?: number;
  travelers: number;
  preferences?: string[];
}

export interface IFlightOption {
  id: string;
  airline: string;
  origin: string;
  destination: string;
  departureTime: string;
  arrivalTime: string;
  price: number;
  duration: string;
}