/**
 * Authentication utilities for JWT cookie management
 * Works with the same JWT tokens issued by the backend
 */

const AUTH_TOKEN_KEY = "auth_token";
const TOKEN_MAX_AGE = 60 * 60 * 24 * 7; // 7 days in seconds

/**
 * Client-side: Set JWT token in cookie
 */
export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;

  if (token) {
    document.cookie = `${AUTH_TOKEN_KEY}=${token}; path=/; max-age=${TOKEN_MAX_AGE}; SameSite=Lax; Secure=${process.env.NODE_ENV === "production"}`;
  } else {
    // Clear cookie
    document.cookie = `${AUTH_TOKEN_KEY}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }
}

/**
 * Client-side: Get JWT token from cookie
 */
export function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;

  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === AUTH_TOKEN_KEY) {
      return value || null;
    }
  }
  return null;
}

/**
 * Server-side: Get JWT token from cookie string
 */
export function getAuthTokenFromCookies(cookieString: string | undefined): string | null {
  if (!cookieString) return null;

  const cookies = cookieString.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === AUTH_TOKEN_KEY) {
      return value || null;
    }
  }
  return null;
}

/**
 * Validate JWT structure and check expiry
 * Does NOT verify signature - backend does that
 */
export function isValidJWT(token: string): boolean {
  if (!token) return false;

  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) return false;

  try {
    const payload = JSON.parse(atob(parts[1]));

    // Check expiry
    if (payload.exp) {
      const expiry = payload.exp * 1000;
      if (Date.now() >= expiry) {
        return false;
      }
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Check if user is authenticated (has valid JWT)
 */
export function isAuthenticated(): boolean {
  const token = getAuthToken();
  return token ? isValidJWT(token) : false;
}
