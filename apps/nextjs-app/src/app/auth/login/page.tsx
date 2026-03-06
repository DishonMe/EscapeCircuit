'use client';

import { useRouter, useSearchParams } from 'next/navigation';

import { paths } from '@/config/paths';
import { LoginForm } from '@/features/auth/components/login-form';
import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';
import { useNotifications } from '@/components/ui/notifications';

const LoginPage = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');
  const { addNotification } = useNotifications();
  const { startNavigation } = useNavigationLoading();

  return (
    <LoginForm
      onSuccess={() => {
        addNotification({
          type: 'success',
          title: 'Login Successful',
          message: 'Welcome back!',
        });
        startNavigation();
        router.push(
          redirectTo ? decodeURIComponent(redirectTo) : paths.app.puzzles.getHref(),
        );
      }}
    />
  );
};

export default LoginPage;
