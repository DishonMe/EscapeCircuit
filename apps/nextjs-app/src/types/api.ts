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
  role: 'admin' | 'creator' | 'solver' | 'pending_creator' | 'ADMIN' | 'USER' | 'GAME_MASTER' | 'PLAYER'; // Support both for safety
  bio: string;
  xp: number;
  level: number;
}>;

export type AuthResponse = {
  token: string;
  user: User;
};

export type Team = Entity<{
  name: string;
  description: string;
}>;

export type ThreadCategory =
  | 'general'
  | 'puzzle_help'
  | 'puzzle_tips'
  | 'solutions'
  | 'bug_report'
  | 'feature_request'
  | 'showcase';

export type Discussion = Entity<{
  title: string;
  body: string;
  author: User;
  author_id: number;
  puzzle_id: number | null;
  category: ThreadCategory;
  is_pinned: boolean;
  is_locked: boolean;
  view_count: number;
  reply_count: number;
  upvotes: number;
  accepted_reply_id: number | null;
  updated_at: string;
  engagement?: DiscussionEngagement;
}>;

export type Reply = Entity<{
  discussion_id: number;
  parent_reply_id: number | null;
  author: User;
  author_id: number;
  body: string;
  upvotes: number;
  downvotes: number;
  is_accepted: boolean;
  updated_at: string;
  children?: Reply[];
  engagement?: ReplyEngagement;
}>;

export type ReactionType =
  | 'insightful'
  | 'helpful'
  | 'genius'
  | 'spot_on'
  | 'thinking';

export type ReactionCount = {
  type: ReactionType;
  count: number;
};

export type DiscussionEngagement = {
  upvotes: number;
  downvotes: number;
  user_vote: number | null;
  reactions: ReactionCount[];
  user_reactions: ReactionType[];
  is_following: boolean;
  is_bookmarked: boolean;
};

export type ReplyEngagement = {
  upvotes: number;
  downvotes: number;
  user_vote: number | null;
  reactions: ReactionCount[];
  user_reactions: ReactionType[];
};

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

  // Solve tracking (injected per-user by browse endpoint)
  is_solved?: boolean;
  can_rate?: boolean;
  best_time?: number | null;
  total_xp?: number;
  best_medal?: number; // 0=none, 1=bronze, 2=silver, 3=gold

  // Difficulty ratings (injected by backend)
  avg_difficulty?: number;

  // Rating metrics (injected by browse/get endpoints)
  rating_metrics?: RatingMetrics;
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

// --- Rating System Types ---

export type RatingMetrics = {
  puzzle_id: number;
  count: number;
  avg_difficulty: number | null;
  weighted_difficulty: number;
  avg_fun: number | null;
  avg_clearness: number | null;
  experienced: {
    count: number;
    avg_difficulty: number | null;
    avg_fun: number | null;
    avg_clearness: number | null;
  };
};

export type RatingEntry = {
  id: number;
  puzzle_id: number;
  user_id: number;
  difficulty: number;
  fun: number;
  clearness: number;
  created_at: string;
  is_experienced_at_rating: boolean;
};

export type PuzzleRatingsResponse = {
  metrics: RatingMetrics;
  my_rating: RatingEntry | null;
};

// --- Admin Panel Types ---

export type AuditLogEntry = {
  id: number;
  admin_user_id: number;
  action_type: string;
  target_user_id: number | null;
  target_puzzle_id: number | null;
  details: Record<string, any>;
  created_at: string;
};

export type Report = {
  id: number;
  reporter_id: number;
  reporter_username?: string;
  target_type: 'discussion' | 'reply';
  target_id: number;
  target_author_id?: number;
  target_author_username?: string;
  discussion_id?: number;
  reason: string;
  details: string;
  status: 'pending' | 'reviewed' | 'dismissed';
  created_at: string;
};

export type AdminPuzzle = Puzzle & {
  flags: string[]; // 'low_fun', 'low_clearness', 'unrated'
  status: 'draft' | 'published' | 'unpublished';
  rating_count?: number;
};
