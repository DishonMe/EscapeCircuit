import pytest

from Backend.DomainLayer.Enums import (
    UserRole,
    PuzzleStatus,
    PuzzleDifficulty,
    Medal,
    TestCaseKind,
    AuditActionType,
    GateType,
    ThreadCategory,
    ReactionType,
)


class TestUserRole:
    def test_values(self):
        assert UserRole.SOLVER.value == "solver"
        assert UserRole.CREATOR.value == "creator"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.PENDING_CREATOR.value == "pending_creator"

    def test_from_string(self):
        assert UserRole("solver") == UserRole.SOLVER
        assert UserRole("admin") == UserRole.ADMIN

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            UserRole("invalid_role")

    def test_is_str_subclass(self):
        assert isinstance(UserRole.SOLVER, str)
        assert UserRole.SOLVER == "solver"


class TestPuzzleStatus:
    def test_values(self):
        assert PuzzleStatus.DRAFT.value == "draft"
        assert PuzzleStatus.PUBLISHED.value == "published"
        assert PuzzleStatus.UNPUBLISHED.value == "unpublished"

    def test_from_string(self):
        assert PuzzleStatus("draft") == PuzzleStatus.DRAFT

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            PuzzleStatus("archived")


class TestPuzzleDifficulty:
    def test_values(self):
        assert PuzzleDifficulty.EASY.value == "EASY"
        assert PuzzleDifficulty.MEDIUM.value == "MEDIUM"
        assert PuzzleDifficulty.HARD.value == "HARD"

    def test_from_string(self):
        assert PuzzleDifficulty("HARD") == PuzzleDifficulty.HARD

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            PuzzleDifficulty("IMPOSSIBLE")


class TestMedal:
    def test_values(self):
        assert Medal.NONE.value == 0
        assert Medal.BRONZE.value == 1
        assert Medal.SILVER.value == 2
        assert Medal.GOLD.value == 3

    def test_from_int(self):
        assert Medal(0) == Medal.NONE
        assert Medal(3) == Medal.GOLD

    def test_ordering(self):
        assert Medal.NONE < Medal.BRONZE < Medal.SILVER < Medal.GOLD

    def test_is_int_subclass(self):
        assert isinstance(Medal.GOLD, int)
        assert Medal.GOLD == 3


class TestTestCaseKind:
    def test_all_values(self):
        assert TestCaseKind.BLACKBOX.value == "blackbox"
        assert TestCaseKind.WHITEBOX.value == "whitebox"
        assert TestCaseKind.STREAM.value == "stream"
        assert TestCaseKind.GATE_LIMIT.value == "gate_limit"
        assert TestCaseKind.GATE_COUNT_LIMIT.value == "gate_count_limit"
        assert TestCaseKind.LATENCY_LIMIT.value == "latency_limit"

    def test_from_string(self):
        assert TestCaseKind("stream") == TestCaseKind.STREAM

    def test_member_count(self):
        assert len(TestCaseKind) == 6


class TestAuditActionType:
    def test_all_values(self):
        assert AuditActionType.ASSIGN_CREATOR.value == "assign_creator"
        assert AuditActionType.REMOVE_CREATOR.value == "remove_creator"
        assert AuditActionType.DELETE_PUZZLE.value == "delete_puzzle"
        assert AuditActionType.UNPUBLISH_PUZZLE.value == "unpublish_puzzle"

    def test_from_string(self):
        assert AuditActionType("delete_puzzle") == AuditActionType.DELETE_PUZZLE


class TestGateType:
    def test_basic_gates(self):
        assert GateType.AND.value == "AND"
        assert GateType.OR.value == "OR"
        assert GateType.NOT.value == "NOT"
        assert GateType.XOR.value == "XOR"
        assert GateType.NAND.value == "NAND"
        assert GateType.NOR.value == "NOR"
        assert GateType.XNOR.value == "XNOR"

    def test_special_gates(self):
        assert GateType.DFF.value == "DFF"

    def test_member_count(self):
        assert len(GateType) == 8

    def test_from_string(self):
        assert GateType("AND") == GateType.AND
        assert GateType("DFF") == GateType.DFF


class TestThreadCategory:
    def test_all_values(self):
        assert ThreadCategory.GENERAL.value == "general"
        assert ThreadCategory.PUZZLE_HELP.value == "puzzle_help"
        assert ThreadCategory.PUZZLE_TIPS.value == "puzzle_tips"
        assert ThreadCategory.SOLUTIONS.value == "solutions"
        assert ThreadCategory.BUG_REPORT.value == "bug_report"
        assert ThreadCategory.FEATURE_REQUEST.value == "feature_request"
        assert ThreadCategory.SHOWCASE.value == "showcase"

    def test_member_count(self):
        assert len(ThreadCategory) == 7

    def test_from_string(self):
        assert ThreadCategory("bug_report") == ThreadCategory.BUG_REPORT


class TestReactionType:
    def test_all_values(self):
        assert ReactionType.INSIGHTFUL.value == "insightful"
        assert ReactionType.HELPFUL.value == "helpful"
        assert ReactionType.GENIUS.value == "genius"
        assert ReactionType.SPOT_ON.value == "spot_on"
        assert ReactionType.THINKING.value == "thinking"

    def test_member_count(self):
        assert len(ReactionType) == 5

    def test_from_string(self):
        assert ReactionType("genius") == ReactionType.GENIUS
