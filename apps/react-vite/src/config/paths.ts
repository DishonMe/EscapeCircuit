export const paths = {
  home: {
    path: '/',
    getHref: () => '/',
  },

  puzzle: {
    browser: {
      path: '/puzzles',
      getHref: () => '/puzzles',
    },
    solve: {
      path: '/puzzles/:puzzleId/solve',
      getHref: (id: string) => `/puzzles/${id}/solve`,
    },
  },

  profile: {
    path: '/profile',
    getHref: () => '/profile',
  },

  creator: {
    dashboard: {
      path: '/creator',
      getHref: () => '/creator',
    },
  },

  admin: {
    panel: {
      path: '/admin',
      getHref: () => '/admin',
    },
  },

  auth: {
    register: {
      path: '/auth/register',
      getHref: (redirectTo?: string | null | undefined) =>
        `/auth/register${redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''}`,
    },
    login: {
      path: '/auth/login',
      getHref: (redirectTo?: string | null | undefined) =>
        `/auth/login${redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''}`,
    },
  },

  app: {
    root: {
      path: '/app',
      getHref: () => '/app',
    },
    dashboard: {
      path: '',
      getHref: () => '/app',
    },
    discussions: {
      path: 'discussions',
      getHref: () => '/app/discussions',
    },
    discussion: {
      path: 'discussions/:discussionId',
      getHref: (id: string) => `/app/discussions/${id}`,
    },
    users: {
      path: 'users',
      getHref: () => '/app/users',
    },
    profile: {
      path: 'profile',
      getHref: () => '/app/profile',
    },
  },
} as const;
