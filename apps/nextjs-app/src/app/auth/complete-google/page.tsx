'use client';

import { useRouter } from 'next/navigation';

import { paths } from '@/config/paths';
import { CompleteGoogleForm } from '@/features/auth/components/complete-google-form';
import { useNotifications } from '@/components/ui/notifications';
import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';

const CompleteGooglePage = () => {
  const router = useRouter();
  const { addNotification } = useNotifications();
  const { startNavigation } = useNavigationLoading();

  return (
    <CompleteGoogleForm
      onSuccess={() => {
        const destination = paths.app.puzzles.getHref();
        startNavigation(destination);
        router.push(destination);
      }}
    />
  );
};

export default CompleteGooglePage;
