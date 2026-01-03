import { QueryClient, useQueryClient } from '@tanstack/react-query';
import { createBrowserRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';

import { paths } from '@/config/paths';
import PuzzleBrowser from './routes/puzzle-browser';
import ProfilePage from './routes/profile';
import CreatorDashboard from './routes/creator-dashboard';
import AdminPanel from './routes/admin-panel';
import SolvePuzzle from './routes/solve-puzzle';
import NotFound from './routes/not-found';

export const createAppRouter = (queryClient: QueryClient) =>
  createBrowserRouter([
    {
      path: paths.home.path,
      element: <PuzzleBrowser />,
    },
    {
      path: paths.puzzle.browser.path,
      element: <PuzzleBrowser />,
    },
    {
      path: paths.puzzle.solve.path,
      element: <SolvePuzzle />,
    },
    {
      path: paths.profile.path,
      element: <ProfilePage />,
    },
    {
      path: paths.creator.dashboard.path,
      element: <CreatorDashboard />,
    },
    {
      path: paths.admin.panel.path,
      element: <AdminPanel />,
    },
    {
      path: '*',
      element: <NotFound />,
    },
  ]);

export const AppRouter = () => {
  const queryClient = useQueryClient();

  const router = createAppRouter(queryClient);

  return <RouterProvider router={router} />;
};
