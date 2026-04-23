'use client';

import Cookies from 'js-cookie';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { paths } from '@/config/paths';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

export default function NotFoundPage() {
  const router = useRouter();

  useEffect(() => {
    const destination = Cookies.get(AUTH_TOKEN_COOKIE_NAME)
      ? paths.app.puzzles.getHref()
      : paths.home.getHref();

    router.replace(destination);
  }, [router]);

  return null;
}
