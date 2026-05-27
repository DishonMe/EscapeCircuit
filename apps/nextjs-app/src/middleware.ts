import { NextRequest, NextResponse } from 'next/server';

import { AUTH_TOKEN_COOKIE_NAME } from './utils/auth-constants';

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Never gate API routes in page middleware.
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  // Public routes that don't require authentication (can be accessed without login)
  const publicRoutes = [
    '/',
    '/auth/login',
    '/auth/register',
    '/auth/complete-google',
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/google',
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

  // If trying to access a protected route without a token, send the user to
  // the public home page (not the login form). The login form, when reached
  // through a redirect with a `redirectTo` query, has historically failed to
  // submit cleanly; the home page has working "Log in" / "Register" CTAs.
  if (!isPublicRoute && !hasAuthToken) {
    const homeUrl = new URL('/', request.url);
    return NextResponse.redirect(homeUrl);
  }

  return NextResponse.next();
}

// Configure which routes the middleware should run on
export const config = {
  matcher: [
    // Match all routes except:
    // - api/* (API routes)
    // - server/* (backend proxy routes)
    // - _next/static/* (static files)
    // - _next/image/* (image optimization files)
    // - favicon.ico (favicon file)
    // - Static file extensions (svg, png, jpg, ico, mp3, wav, etc.)
    '/((?!api|server|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|mp3|wav|txt|robots\\.txt)$).*)',
  ],
};
