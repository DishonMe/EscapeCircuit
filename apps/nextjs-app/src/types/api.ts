// EscapeCircuit API types

export type BaseEntity = {
  id: string;
  createdAt: number;
};

export type Entity<T> = {
  [K in keyof T]: T[K];
} & BaseEntity;

export type Meta = {
  page: number;
  total: number;
  totalPages: number;
};

export type User = Entity<{
  username: string;
  email: string;
  role: 'admin' | 'creator' | 'solver' | 'ADMIN' | 'USER' | 'GAME_MASTER' | 'PLAYER'; // Support both for safety
  bio: string;
  xp: number;
  level: number;
  /** Admin-set override for max published puzzles (null = use level-based default). */
  puzzle_limit_published: number | null;
  /** Admin-set override for max unpublished/draft puzzles (null = use level-based default). */
  puzzle_limit_unpublished: number | null;
  /** Effective published puzzle limit (level-based default or admin override). */
  effective_published_limit: number;
  /** Effective unpublished/draft puzzle limit (level-based default or admin override). */
  effective_unpublished_limit: number;
}>;

export type AuthResponse = {
  token: string;
  user: User;
};

export type Team = Entity<{
  name: string;
  description: string;
}>;

export type Discussion = Entity<{
  title: string;
  body: string;
  teamId: string;
  author: User;
  public: boolean;
}>;

export type Comment = Entity<{
  body: string;
  discussionId: string;
  author: User;
}>;

export type Puzzle = Entity<{
  title: string;
  name?: string; // Backend compat
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  timeLimit: number; // in seconds
  budgetLimit: number;
  budget?: number; // Backend compat
  inputs: string[];
  outputs: string[];
  creator: User;
  creatorComment?: string;

  filteredBasicComponents?: string[];
  defaultGateSet?: string[];
  allowArsenal?: boolean;
  specialComponents?: CircuitComponent[];
  rating: number;
  solvedCount: number;
  isPublic: boolean;
  solution?: CircuitSolution;
}>;

export type CircuitComponent = {
  id: string;
  type: string;
  cost: number;
  pins: number;
};

export type PlacedComponent = {
  id: string;
  componentId: string;
  x: number;
  y: number;
};

export type Wire = {
  id: string;
  from: { componentId: string; pinIndex: number; portId: string };
  to: { componentId: string; pinIndex: number; portId: string };
};

export type CircuitSolution = {
  placedComponents: PlacedComponent[];
  wires: Wire[];
  totalCost: number;
};

export type PuzzleAttempt = Entity<{
  puzzleId: string;
  playerId: string;
  startTime: number;
  endTime?: number;
  completed: boolean;
  score: number;
  timeSpent: number;
  solution?: CircuitSolution;
}>;
