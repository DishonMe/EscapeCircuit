export const paths = {
  home: {
    getHref: () => '/',
  },

  auth: {
    register: {
      getHref: (redirectTo?: string | null | undefined) =>
        `/auth/register${redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''}`,
    },
    login: {
      getHref: (redirectTo?: string | null | undefined) =>
        `/auth/login${redirectTo ? `?redirectTo=${encodeURIComponent(redirectTo)}` : ''}`,
    },
    completeGoogle: {
      getHref: () => `/auth/complete-google`,
    },
  },

  app: {
    root: {
      getHref: () => '/app',
    },
    dashboard: {
      getHref: () => '/app',
    },
    puzzles: {
      getHref: () => '/app/puzzles',
    },
    puzzle: {
      getHref: (id: string) => `/app/puzzles/${id}`,
    },
    arsenal: {
      root: {
        getHref: () => '/app/arsenal',
      },
      creator: {
        getHref: () => '/app/arsenal/creator',
      },
    },
    discussions: {
      getHref: () => '/app/discussions',
    },
    discussion: {
      getHref: (id: string) => `/app/discussions/${id}`,
    },
    users: {
      getHref: () => '/app/users',
    },
    profile: {
      getHref: () => '/app/profile',
    },
    notifications: {
      getHref: () => '/app/notifications',
    },
  },
  public: {
    discussion: {
      getHref: (id: string) => `/public/discussions/${id}`,
    },
  },
} as const;
