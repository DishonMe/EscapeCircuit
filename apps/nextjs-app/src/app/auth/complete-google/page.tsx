'use client';

import { useRouter } from 'next/navigation';

import { paths } from '@/config/paths';
import { CompleteGoogleForm } from '@/features/auth/components/complete-google-form';
import { useNotifications } from '@/components/ui/notifications';

const CompleteGooglePage = () => {
  const router = useRouter();
  const { addNotification } = useNotifications();

  return (
    <CompleteGoogleForm
      onSuccess={() => {
        router.push(paths.app.puzzles.getHref());
      }}
    />
  );
};

export default CompleteGooglePage;
