import { cookies } from 'next/headers';

import { AUTH_TOKEN_COOKIE_NAME } from './auth-constants';

export const getAuthTokenCookie = () => {
  if (typeof window !== 'undefined') return '';
  const cookieStore = cookies();
  return cookieStore.get(AUTH_TOKEN_COOKIE_NAME)?.value;
};

export const checkLoggedIn = () => {
  const cookieStore = cookies();
  const isLoggedIn = !!cookieStore.get(AUTH_TOKEN_COOKIE_NAME);
  return isLoggedIn;
};
