from enum import Enum


class UserRole(str, Enum):
    SOLVER = "solver"
    CREATOR = "creator"
    ADMIN = "admin"
    PENDING_CREATOR = "pending_creator"


class PuzzleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


class PuzzleDifficulty(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class Medal(int, Enum):
    NONE = 0
    BRONZE = 1
    SILVER = 2
    GOLD = 3


class TestCaseKind(str, Enum):
    BLACKBOX = "blackbox"
    WHITEBOX = "whitebox"
    STREAM = "stream"  # Sequential/stream test cases for circuits with state
    GATE_LIMIT = "gate_limit"  # Per-gate usage limits (e.g., max 3 ANDs)
    GATE_COUNT_LIMIT = "gate_count_limit"  # Total gate count limit (e.g., max 10 gates total)
    LATENCY_LIMIT = "latency_limit"  # Sequential circuit cycle limits (e.g., min 2, max 5 cycles)


class AuditActionType(str, Enum):
    ASSIGN_CREATOR = "assign_creator"
    REMOVE_CREATOR = "remove_creator"
    DELETE_PUZZLE = "delete_puzzle"
    UNPUBLISH_PUZZLE = "unpublish_puzzle"


class GateType(str, Enum):
    # Add/remove as needed
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    NAND = "NAND"
    NOR = "NOR"
    XNOR = "XNOR"

    # Special gate types - flip flop
    DFF = "DFF"


class ThreadCategory(str, Enum):
    GENERAL = "general"
    PUZZLE_HELP = "puzzle_help"
    PUZZLE_TIPS = "puzzle_tips"
    SOLUTIONS = "solutions"
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    SHOWCASE = "showcase"


class ReactionType(str, Enum):
    INSIGHTFUL = "insightful"
    HELPFUL = "helpful"
    GENIUS = "genius"
    SPOT_ON = "spot_on"
    THINKING = "thinking"
