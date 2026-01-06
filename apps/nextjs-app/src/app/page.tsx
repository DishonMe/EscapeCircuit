
import { paths } from '@/config/paths';
import { checkLoggedIn } from '@/utils/auth';

import { redirect } from 'next/navigation';

const HomePage = () => {
  const isLoggedIn = checkLoggedIn();

  if (isLoggedIn) {
    redirect(paths.app.puzzles.getHref());
  } else {
    redirect(paths.auth.login.getHref());
  }
};

export default HomePage;
