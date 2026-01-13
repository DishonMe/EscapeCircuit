'use client';

import Link from 'next/link';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';

const HomePage = () => {
  const router = useRouter();
  const user = useUser();

  useEffect(() => {
    // Wait for auth query to resolve, then route appropriately
    if (user.status === 'pending') return;
    if (user.data) {
      router.replace(paths.app.puzzles.getHref());
    }
  }, [user.status, user.data, router]);

  // Show a simple landing with a login button when not authenticated
  const showLogin = user.status !== 'pending' && !user.data;

  return (
    <div className="flex min-h-screen flex-col bg-white">
      <header className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
        <div className="text-lg font-semibold text-gray-900">EscapeCircuit</div>
        {showLogin ? (
          <Button asChild variant="primary">
            <Link href={paths.auth.login.getHref()}>Login</Link>
          </Button>
        ) : (
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
        )}
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-10 text-gray-700">
        <div className="max-w-xl text-center">
          <h1 className="text-2xl font-semibold text-gray-900">Welcome</h1>
          <p className="mt-2 text-gray-600">
            Please log in to access puzzles and your dashboard.
          </p>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
