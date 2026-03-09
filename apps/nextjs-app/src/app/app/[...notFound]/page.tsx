'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { paths } from '@/config/paths';

export default function NotFoundPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to puzzles page for any undefined route
    router.replace(paths.app.puzzles.getHref());
  }, [router]);

  return null;
}
