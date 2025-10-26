import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { getAuthTokenFromCookies, isValidJWT } from "./lib/auth";

/**
 * Next.js middleware for server-side authentication protection
 * Protects /trips/* routes and redirects authenticated users away from /auth/* routes
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const token = getAuthTokenFromCookies(request.headers.get("cookie") || undefined);

  const isAuthenticated = token ? isValidJWT(token) : false;

  // Protect /trips/* routes - require authentication
  if (pathname.startsWith("/trips")) {
    if (!isAuthenticated) {
      // Redirect to login with return URL
      const loginUrl = new URL("/auth/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
    // Allow authenticated users
    return NextResponse.next();
  }

  // /auth/* routes - redirect authenticated users to trips
  if (pathname.startsWith("/auth")) {
    if (isAuthenticated) {
      // Already logged in, redirect to trips
      return NextResponse.redirect(new URL("/trips", request.url));
    }
    // Allow non-authenticated users to access auth pages
    return NextResponse.next();
  }

  // All other routes - allow access
  return NextResponse.next();
}

/**
 * Configure which routes the middleware runs on
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, sitemap.xml, robots.txt (public files)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|sitemap.xml|robots.txt).*)",
  ],
};
