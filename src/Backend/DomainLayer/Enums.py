from enum import Enum

class UserRole(str, Enum):
    SOLVER = "solver"
    CREATOR = "creator"
    ADMIN = "admin"


class PuzzleStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    UNPUBLISHED = "unpublished"


class TestCaseKind(str, Enum):
    BLACKBOX = "blackbox"
    WHITEBOX = "whitebox"


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
    