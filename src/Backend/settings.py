"""
EscapeCircuit — centralised configuration / constants.

Every magic number that controls business rules, performance tuning, or
UI defaults lives here.  Import directly from this module:

    from Backend.settings import XP_SOLVE_EASY, PUZZLE_MAX_PUBLISHED_PER_USER

This file has **no imports from the rest of the Backend** so it can be
safely imported by any layer without creating circular dependencies.
"""

# ── Database ──────────────────────────────────────────────────────────────────
# sqlite3.connect(timeout=) — seconds to wait for the connection object itself
DB_CONNECTION_TIMEOUT_S: float = 30.0

# PRAGMA busy_timeout (milliseconds) — how long a write waits for the WAL lock
DB_BUSY_TIMEOUT_MS: int = 30_000

# ── Contention-monitoring middleware ──────────────────────────────────────────
# Request wall-clock time (seconds) at which we escalate log severity
CONTENTION_WARN_THRESHOLD_S: float = 3.0   # WARNING — probable write-lock stall
CONTENTION_INFO_THRESHOLD_S: float = 1.0   # INFO    — elevated latency

# ── XP — solve rewards ────────────────────────────────────────────────────────
XP_SOLVE_EASY: int = 50
XP_SOLVE_MEDIUM: int = 100
XP_SOLVE_HARD: int = 200

XP_MEDAL_BONUS_NONE: int = 0
XP_MEDAL_BONUS_BRONZE: int = 0
XP_MEDAL_BONUS_SILVER: int = 25
XP_MEDAL_BONUS_GOLD: int = 50

# XP awarded to a puzzle's creator each time someone else solves it
XP_SOLVE_REWARD_CREATOR: int = 10

# XP awarded when a rating is submitted (first time per puzzle+user only)
XP_RATING_RATER: int = 5     # to the user who rated
XP_RATING_CREATOR: int = 1   # to the puzzle creator

# ── Level formula ─────────────────────────────────────────────────────────────
# level = floor(sqrt(xp / LEVEL_XP_DIVISOR)) + 1
LEVEL_XP_DIVISOR: int = 100

# Minimum level to be considered an "experienced" rater
EXPERIENCED_LEVEL_MIN: int = 5

# ── Difficulty tier — numeric rating → PuzzleDifficulty enum ─────────────────
DIFFICULTY_HARD_THRESHOLD: float = 7.0    # avg_difficulty >= this → HARD
DIFFICULTY_MEDIUM_THRESHOLD: float = 4.0  # avg_difficulty >= this → MEDIUM (else EASY)

# ── Arsenal — XP-gated slot capacity ─────────────────────────────────────────
# Each tuple: (max_level_inclusive, slot_count).  Evaluated in order.
ARSENAL_XP_LEVEL_TIERS: list = [
    (2,  5),
    (4,  10),
    (6,  20),
    (8,  35),
]
ARSENAL_XP_MAX_SLOTS: int = 50   # capacity when level > 8

# ── Arsenal piece constraints ─────────────────────────────────────────────────
# Hard cap used by ArsenalService before XP-based tiers apply
ARSENAL_DEFAULT_MAX_SIZE: int = 10
ARSENAL_MAX_INPUTS: int = 5
ARSENAL_MAX_OUTPUTS: int = 3
ARSENAL_MIN_INPUTS: int = 1
ARSENAL_MIN_OUTPUTS: int = 1

# ── Puzzle custom pieces constraints ───────────────────────────────────────────
# Limits for custom pieces created by puzzle creators for specific puzzles
PUZZLE_CUSTOM_PIECES_MAX_COUNT: int = 10  # Max custom pieces per puzzle
PUZZLE_CUSTOM_PIECES_MAX_INPUTS: int = 5
PUZZLE_CUSTOM_PIECES_MAX_OUTPUTS: int = 3
PUZZLE_CUSTOM_PIECES_MIN_INPUTS: int = 1
PUZZLE_CUSTOM_PIECES_MIN_OUTPUTS: int = 1

# ── Puzzle publishing ─────────────────────────────────────────────────────────
PUZZLE_MAX_PUBLISHED_PER_USER: int = 10  # Legacy — kept for reference; per-user limits now used

# ── Puzzle capacity for creators ──────────────────────────────────────────────
# Base capacity for all creators regardless of level
PUZZLE_BASE_PUBLISHED_PER_CREATOR: int = 5
PUZZLE_BASE_UNPUBLISHED_PER_CREATOR: int = 5
# From this level onward, capacity increases by PUZZLE_CAPACITY_LEVEL_INCREMENT per level
PUZZLE_CAPACITY_LEVEL_START: int = 10
# Capacity stops increasing after this level
PUZZLE_CAPACITY_LEVEL_END: int = 15
# Amount added to capacity per qualifying level
PUZZLE_CAPACITY_LEVEL_INCREMENT: int = 2
PUZZLE_NAME_MAX_LENGTH: int = 100
PUZZLE_DESCRIPTION_MAX_LENGTH: int = 2000
PUZZLE_INSTRUCTIONS_MAX_BYTES: int = 5 * 1024
PUZZLE_CREATOR_COMMENT_MAX_LENGTH: int = 1000

# ── Puzzle board defaults ──────────────────────────────────────────────────────
PUZZLE_DEFAULT_BOARD_ROWS: int = 15
PUZZLE_DEFAULT_BOARD_COLS: int = 30
# ── Rating system ─────────────────────────────────────────────────────────────
# Minimum puzzle-attempt time (seconds) to unlock rating without having solved
RATING_MIN_ATTEMPT_SECONDS: int = 300  # 300 seconds = 5 minutes

# Number of *user* ratings (excluding creator) that shifts the weighting model
RATING_USER_COUNT_THRESHOLD: int = 10

# Difficulty blend weights (creator_weight, users_weight)
RATING_DIFF_WEIGHT_FEW_RATINGS: tuple = (0.8, 0.2)   # < RATING_USER_COUNT_THRESHOLD
RATING_DIFF_WEIGHT_MANY_RATINGS: tuple = (0.4, 0.6)  # >= RATING_USER_COUNT_THRESHOLD

# Numeric equivalents for the creator's categorical difficulty label
RATING_DIFFICULTY_MAP: dict = {"EASY": 1, "MEDIUM": 3, "HARD": 5}

# ── Forum / Discussion XP ─────────────────────────────────────────────────────
XP_DISCUSSION_CREATE: int = 5    # author creates a discussion thread
XP_DISCUSSION_UPVOTE: int = 3    # discussion author receives an upvote
XP_DISCUSSION_REACTION: int = 1  # discussion author receives a reaction

XP_REPLY_CREATE: int = 2         # user posts a reply
XP_REPLY_ACCEPTED: int = 25      # reply is marked as the accepted solution
XP_ACCEPT_SOLUTION: int = 5      # discussion author accepts a solution
XP_REPLY_UPVOTE: int = 3         # reply author receives an upvote
XP_REPLY_REACTION: int = 1       # reply author receives a reaction

# ── Moderation ────────────────────────────────────────────────────────────────
# avg_fun / avg_clearness below these values → "low_fun" / "low_clearness" flag
MODERATION_LOW_FUN_THRESHOLD: float = 2.0
MODERATION_LOW_CLEARNESS_THRESHOLD: float = 2.0

# Accepted values for user-submitted report reasons
MODERATION_VALID_REPORT_REASONS: frozenset = frozenset(
    {"spam", "harassment", "off_topic", "inappropriate", "other"}
)

# ── Pagination defaults ────────────────────────────────────────────────────────
BROWSE_PUZZLES_DEFAULT_LIMIT: int = 50
LIST_MY_PUZZLES_DEFAULT_LIMIT: int = 50
LIST_USERS_DEFAULT_LIMIT: int = 50
LIST_DISCUSSIONS_DEFAULT_LIMIT: int = 20

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS: list = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
