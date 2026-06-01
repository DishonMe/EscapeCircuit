'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

import { paths } from '@/config/paths';

export default function AppPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to puzzles page
    router.replace(paths.app.puzzles.getHref());
  }, [router]);

  return null;
}
