'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { paths } from '@/config/paths';
import { RegisterForm } from '@/features/auth/components/register-form';
import { useTeams } from '@/features/teams/api/get-teams';
import { useNavigationLoading } from '@/components/ui/navigation-loading/navigation-loading';

const RegisterPage = () => {
  const router = useRouter();
  const { startNavigation } = useNavigationLoading();

  const searchParams = useSearchParams();
  const redirectTo = searchParams?.get('redirectTo');

  const [chooseTeam, setChooseTeam] = useState(false);

  const teamsQuery = useTeams({
    queryConfig: {
      enabled: chooseTeam,
    },
  });

  return (
    <RegisterForm
      onSuccess={() => {
        const destination = redirectTo ? decodeURIComponent(redirectTo) : paths.app.puzzles.getHref();
        startNavigation(destination);
        router.replace(destination);
      }}
      chooseTeam={chooseTeam}
      setChooseTeam={() => setChooseTeam(!chooseTeam)}
      teams={teamsQuery.data?.data}
    />
  );
};

export default RegisterPage;
