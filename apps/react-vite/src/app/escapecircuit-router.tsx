import { createBrowserRouter, RouterProvider } from 'react-router';
import { QueryClient } from '@tanstack/react-query';

import { paths } from '@/config/paths';

import PuzzleBrowserRoute from './routes/puzzle-browser';
import ProfileRoute from './routes/profile';
import CreatorDashboardRoute from './routes/creator-dashboard';
import AdminPanelRoute from './routes/admin-panel';
import SolvePuzzleRoute from './routes/solve-puzzle';

const convert = (queryClient: QueryClient) => (m: any) => {
  const { clientLoader, clientAction, default: Component, ...rest } = m;
  return {
    ...rest,
    loader: clientLoader?.(queryClient),
    action: clientAction?.(queryClient),
    Component,
  };
};

export const createAppRouter = (queryClient: QueryClient) =>
  createBrowserRouter([
    {
      path: paths.home.path,
      lazy: () => import('./routes/puzzle-browser').then(convert(queryClient)),
    },
    {
      path: paths.puzzle.solve.path,
      lazy: () => import('./routes/solve-puzzle').then(convert(queryClient)),
    },
    {
      path: paths.profile.path,
      lazy: () => import('./routes/profile').then(convert(queryClient)),
    },
    {
      path: paths.creator.dashboard.path,
      lazy: () => import('./routes/creator-dashboard').then(convert(queryClient)),
    },
    {
      path: paths.admin.panel.path,
      lazy: () => import('./routes/admin-panel').then(convert(queryClient)),
    },
  ]);

export const AppRouter = ({ queryClient }: { queryClient: QueryClient }) => {
  return <RouterProvider router={createAppRouter(queryClient)} />;
};
