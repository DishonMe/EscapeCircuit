from typing import TYPE_CHECKING

from .Enums import PuzzleDifficulty

if TYPE_CHECKING:
    from .Puzzle import Puzzle


DEFAULT_CLUE_PENALTY_BY_DIFFICULTY = {
    PuzzleDifficulty.EASY: 15,
    PuzzleDifficulty.MEDIUM: 30,
    PuzzleDifficulty.HARD: 60,
}

FALLBACK_CLUE_PENALTY_SECONDS = 30


def resolve_clue_penalty(puzzle: "Puzzle") -> int:
    override = getattr(puzzle, "clue_penalty_seconds", None)
    if override is not None and override > 0:
        return int(override)
    difficulty = getattr(puzzle, "difficulty", None)
    if difficulty in DEFAULT_CLUE_PENALTY_BY_DIFFICULTY:
        return DEFAULT_CLUE_PENALTY_BY_DIFFICULTY[difficulty]
    return FALLBACK_CLUE_PENALTY_SECONDS
