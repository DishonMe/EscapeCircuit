'use client';

import type { ReactNode } from 'react';
import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { Spinner } from '@/components/ui/spinner';
import { paths } from '@/config/paths';
import { useUser } from '@/lib/auth';

const normalizeRole = (role: string | undefined) => (role || '').toLowerCase();

type AccessGateProps = {
  allowedRoles: Array<'admin' | 'creator' | 'solver'>;
  children: ReactNode;
};

export const AccessGate = ({ allowedRoles, children }: AccessGateProps) => {
  const user = useUser();
  const router = useRouter();

  const normalizedRole = normalizeRole(user.data?.role);
  const hasAccess =
    !!user.data &&
    allowedRoles.includes(normalizedRole as 'admin' | 'creator' | 'solver');

  useEffect(() => {
    if (user.status === 'success' && user.data && !hasAccess) {
      router.replace(paths.app.puzzles.getHref());
    }
  }, [hasAccess, router, user.data, user.status]);

  if (user.status !== 'success') {
    return <Spinner className="m-4" />;
  }

  if (!user.data) {
    return <Spinner className="m-4" />;
  }

  if (!hasAccess) {
    return null;
  }

  return children;
};