import { env } from '@/config/env';
import Cookies from 'js-cookie';
import { AUTH_TOKEN_COOKIE_NAME } from '@/utils/auth-constants';

export const enableMocking = async () => {
  console.log('Checking ENABLE_API_MOCKING:', env.ENABLE_API_MOCKING);
  if (env.ENABLE_API_MOCKING) {
    console.log('Starting MSW Worker...');
    const { worker } = await import('./browser');
    const { initializeDb } = await import('./db');
    await initializeDb();
    await worker.start({
      onUnhandledRequest: 'bypass',
    });
    // Clear any stale auth token cookie to avoid mismatch with freshly seeded mock DB
    Cookies.remove(AUTH_TOKEN_COOKIE_NAME);
    console.log('MSW Worker started successfully');
  }
};
