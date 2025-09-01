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

// Authentication Types
export interface ILoginRequest {
  email: string;
  password: string;
}

export interface IRegisterRequest {
  name: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface IAuthResponse {
  success: boolean;
  user?: IUser;
  token?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

// Form validation types
export interface IPasswordStrength {
  score: number; // 0-4
  feedback: {
    warning?: string;
    suggestions: string[];
  };
  isValid: boolean;
}

export interface IFormError {
  field: string;
  message: string;
}