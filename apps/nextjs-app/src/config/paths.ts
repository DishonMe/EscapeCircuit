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
      getHref: () => '/app/puzzles',
    },
    dashboard: {
      getHref: () => '/app/puzzles',
    },
    puzzles: {
      getHref: () => '/app/puzzles',
    },
    puzzle: {
      getHref: (id: string) => `/app/puzzles/${id}`,
    },
    createPuzzle: {
      getHref: () => '/app/create-puzzle',
    },
    myPuzzles: {
      getHref: () => '/app/my-puzzles',
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
    newDiscussion: {
      getHref: () => '/app/discussions/new',
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
