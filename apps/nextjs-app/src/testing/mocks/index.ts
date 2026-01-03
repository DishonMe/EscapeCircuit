import { env } from '@/config/env';

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
    console.log('MSW Worker started successfully');
  }
};
