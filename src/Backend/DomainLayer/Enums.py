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
    