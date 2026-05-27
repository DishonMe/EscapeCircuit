'use client';

import { useRouter } from 'next/navigation';

import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';
import { paths } from '@/config/paths';
import { CompleteGoogleForm } from '@/features/auth/components/complete-google-form';

const CompleteGooglePage = () => {
  const router = useRouter();
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
