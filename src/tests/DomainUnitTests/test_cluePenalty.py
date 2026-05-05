import pytest
from Backend.DomainLayer.CluePenalty import (
    resolve_clue_penalty,
    DEFAULT_CLUE_PENALTY_BY_DIFFICULTY,
    FALLBACK_CLUE_PENALTY_SECONDS,
)
from Backend.DomainLayer.Enums import PuzzleDifficulty
from Backend.DomainLayer.Puzzle import Puzzle


class TestResolveCluepenalty:
    """Test the resolve_clue_penalty function for all branches."""

    def test_override_penalty_positive_value(self):
        """Override is set and positive - should use override."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            clue_penalty_seconds=50
        )
        result = resolve_clue_penalty(puzzle)
        assert result == 50

    def test_override_penalty_zero_value(self):
        """Override is 0 - should fall through to difficulty lookup."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            clue_penalty_seconds=0,
            difficulty=PuzzleDifficulty.EASY
        )
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.EASY]

    def test_override_penalty_negative_value(self):
        """Override is negative - should fall through to difficulty lookup."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            clue_penalty_seconds=-10,
            difficulty=PuzzleDifficulty.MEDIUM
        )
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.MEDIUM]

    def test_override_none_easy_difficulty(self):
        """No override, easy difficulty - should use default easy penalty."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            difficulty=PuzzleDifficulty.EASY
        )
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.EASY]
        assert result == 15

    def test_override_none_medium_difficulty(self):
        """No override, medium difficulty - should use default medium penalty."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            difficulty=PuzzleDifficulty.MEDIUM
        )
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.MEDIUM]
        assert result == 30

    def test_override_none_hard_difficulty(self):
        """No override, hard difficulty - should use default hard penalty."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            difficulty=PuzzleDifficulty.HARD
        )
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.HARD]
        assert result == 60

    def test_override_none_unknown_difficulty(self):
        """No override, unknown difficulty - should use fallback."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1,
            difficulty=None
        )
        result = resolve_clue_penalty(puzzle)
        assert result == FALLBACK_CLUE_PENALTY_SECONDS
        assert result == 30

    def test_override_none_no_difficulty_set(self):
        """Override not set and difficulty attribute missing - uses default EASY (15), not fallback."""
        puzzle = Puzzle(
            id=1,
            name="Test",
            creator_user_id=1
        )
        # Puzzle defaults to EASY difficulty, so should use DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[EASY]
        result = resolve_clue_penalty(puzzle)
        assert result == DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[PuzzleDifficulty.EASY]
        assert result == 15
