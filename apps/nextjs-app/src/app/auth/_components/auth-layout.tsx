'use client';

import { useRouter, usePathname, useSearchParams } from 'next/navigation';
import { ReactNode, useEffect, useState } from 'react';
import Cookies from 'js-cookie';

import { Link } from '@/components/ui/link';
import { paths } from '@/config/paths';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

type LayoutProps = {
  children: ReactNode;
};

export const AuthLayout = ({ children }: LayoutProps) => {
  const router = useRouter();
  const pathname = usePathname();
  const isLoginPage = pathname === paths.auth.login.getHref();
  const title = isLoginPage
    ? 'Log in to your account'
    : 'Register your account';

  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');

  const [hasCheckedToken, setHasCheckedToken] = useState(false);

  useEffect(() => {
    // Check if user has a valid token - if so, redirect to dashboard
    // This is done synchronously without an API call to avoid delays on auth pages
    try {
      const token = Cookies.get(AUTH_TOKEN_COOKIE_NAME);
      if (token) {
        // User is already logged in, redirect them
        router.replace(
          `${redirectTo ? `${decodeURIComponent(redirectTo)}` : paths.app.dashboard.getHref()}`,
        );
      }
    } catch (error) {
      console.error('Error checking auth token:', error);
    }
    
    setHasCheckedToken(true);
  }, [router, redirectTo]);

  return (
    <div className="flex min-h-screen flex-col justify-center bg-gray-50 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center">
          <Link
            className="flex items-center text-white"
            href={paths.home.getHref()}
          >
            <img className="h-24 w-auto" src="/logo.svg" alt="Workflow" />
          </Link>
        </div>

        <h2 className="mt-3 text-center text-3xl font-extrabold text-gray-900">
          {title}
        </h2>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white px-4 py-8 shadow sm:rounded-lg sm:px-10">
          {children}
        </div>
      </div>
    </div>
  );
};
