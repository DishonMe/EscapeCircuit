import { NextRequest, NextResponse } from 'next/server';
import { AUTH_TOKEN_COOKIE_NAME } from './utils/auth-constants';

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  // Public routes that don't require authentication (can be accessed without login)
  const publicRoutes = [
    '/',
    '/auth/login',
    '/auth/register',
    '/auth/complete-google',
  ];

  // Protected routes that are only for logged-in users
  const loggedInOnlyRoutes = [
    '/auth/login',
    '/auth/register',
    '/auth/complete-google',
  ];

  // Check if the current path is a public route
  const isPublicRoute = publicRoutes.includes(pathname);
  
  // Check if the current path is a logged-in only route
  const isLoggedInOnlyRoute = loggedInOnlyRoutes.includes(pathname);

  // Check if user has an auth token
  const hasAuthToken = request.cookies.has(AUTH_TOKEN_COOKIE_NAME);

  // If user is logged in and tries to access auth pages or base URL, redirect to app
  if (hasAuthToken && (isLoggedInOnlyRoute || pathname === '/')) {
    const appUrl = new URL('/app/puzzles', request.url);
    // Add reason for notification
    if (isLoggedInOnlyRoute) {
      appUrl.searchParams.set('reason', 'already-logged-in');
    }
    return NextResponse.redirect(appUrl);
  }

  // If trying to access a protected route without a token, redirect to login
  if (!isPublicRoute && !hasAuthToken) {
    const loginUrl = new URL('/auth/login', request.url);
    // Add redirectTo parameter to return user to original page after login
    loginUrl.searchParams.set('redirectTo', pathname);
    // Add reason parameter for notification
    loginUrl.searchParams.set('reason', 'unauthorized');
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    // Match all routes except:
    // - _next/static/* (static files)
    // - _next/image/* (image optimization files)
    // - favicon.ico (favicon file)
    // - public/* (public files)
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};
