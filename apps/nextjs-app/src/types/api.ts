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
  firstName: string;
  lastName: string;
  email: string;
  role: 'ADMIN' | 'USER' | 'GAME_MASTER' | 'PLAYER';
  bio: string;
}>;

export type AuthResponse = {
  jwt: string;
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
  description: string;
  difficulty: 'EASY' | 'MEDIUM' | 'HARD';
  timeLimit: number; // in seconds
  budgetLimit: number;
  tightBudgetLimit?: number;
  additionalConstraints?: string[] | string;
  inputs: string[];
  outputs: string[];
  creator: User;
  creatorComment?: string;
  filteredBasicComponents?: string[];
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
