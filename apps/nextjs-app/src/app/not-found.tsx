'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Cookies from 'js-cookie';

import { paths } from '@/config/paths';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

const NotFoundPage = () => {
  const router = useRouter();

  useEffect(() => {
    const destination = Cookies.get(AUTH_TOKEN_COOKIE_NAME)
      ? paths.app.puzzles.getHref()
      : paths.home.getHref();

    router.replace(destination);
  }, [router]);

  return null;
};

export default NotFoundPage;
