'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { ReactNode, useEffect, useState, useRef } from 'react';
import Cookies from 'js-cookie';

import { Link } from '@/components/ui/link';
import { paths } from '@/config/paths';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';
import { useNotifications } from '@/components/ui/notifications';

type LayoutProps = {
  children: ReactNode;
};

export const AuthLayout = ({ children }: LayoutProps) => {
  const router = useRouter();
  const pathname = usePathname();
  const { addNotification } = useNotifications();
  const hasShownNotificationRef = useRef(false);
  const isLoginPage = pathname === paths.auth.login.getHref();
  const title = isLoginPage
    ? 'Log in to your account 🔐'
    : 'Register your account ✍️';

  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');
  const reason = searchParams?.get('reason');

  const [hasCheckedToken, setHasCheckedToken] = useState(false);

  useEffect(() => {
    // Check if user has a valid token by verifying with the API
    const checkAuth = async () => {
      try {
        const token = Cookies.get(AUTH_TOKEN_COOKIE_NAME);
        if (token) {
          // Verify the token is still valid with the API
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
          const res = await fetch(`${apiUrl}/users/me`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (res.ok) {
            // Token is valid — redirect to dashboard
            const destination = redirectTo
              ? decodeURIComponent(redirectTo)
              : paths.app.puzzles.getHref();
            router.replace(destination);
            return;
          }
          // Token is invalid/expired — clear it and stay on login page
          Cookies.remove(AUTH_TOKEN_COOKIE_NAME);
        }
      } catch (error) {
        // Network error — clear potentially stale cookie
        Cookies.remove(AUTH_TOKEN_COOKIE_NAME);
      }
      setHasCheckedToken(true);
    };
    checkAuth();
  }, [router, redirectTo]);

  // Show notification based on redirect reason
  useEffect(() => {
    if (!hasShownNotificationRef.current && reason && hasCheckedToken) {
      hasShownNotificationRef.current = true;
      
      if (reason === 'unauthorized') {
        addNotification({
          type: 'info',
          title: 'Authentication Required',
          message: 'Please log in to access this page.',
        });
      } else if (reason === 'session-expired') {
        addNotification({
          type: 'warning',
          title: 'Session Expired',
          message: 'Your session has expired. Please log in again to continue.',
        });
      } else if (reason === 'already-logged-in') {
        addNotification({
          type: 'info',
          title: 'Already Logged In',
          message: 'You are already logged in. Redirecting to dashboard.',
        });
      }
    }
  }, [reason, hasCheckedToken, addNotification]);

  return (
    <div className="flex min-h-screen flex-col justify-center bg-background py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Link
            className="flex items-center"
            href={paths.home.getHref()}
          >
            <img className="h-20 w-20" src="/logo.svg" alt="Workflow" />
          </Link>
        </div>

        <h2 className="mt-4 text-center text-2xl font-semibold tracking-tight text-foreground">
          {title}
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="rounded-xl border border-border bg-card px-6 py-8 shadow-card sm:px-10">
          {children}
        </div>
      </div>
    </div>
  );
};
