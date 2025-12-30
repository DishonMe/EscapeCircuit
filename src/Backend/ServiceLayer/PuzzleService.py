from typing import Dict, Any, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus

from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService


class PuzzleService:
    """
    All actions must call AuthService.
    """
    def __init__(self, puzzle_repo: PuzzleRepo, user_repo: UserRepo, auth_service: AuthService):
        self.repo = puzzle_repo
        self.user_repo = user_repo
        self.auth = auth_service

    def browse(self, session_token: str, limit: int = 50, offset: int = 0) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        puzzles = self.repo.list_published(limit=limit, offset=offset)
        return [p.to_dict() for p in puzzles]

    def search(self, session_token: str, q: str, only_published: bool = True) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        puzzles = self.repo.search_by_name(q, only_published=only_published)
        return [p.to_dict() for p in puzzles]

    def get(self, session_token: str, puzzle_id: int) -> dict:
        _ = self.auth.require_user_id(session_token)
        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")
        return p.to_dict()

    def create_puzzle(self, session_token: str, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        if user.role not in (UserRole.CREATOR, UserRole.ADMIN):
            raise ValidationError("creator required")

        from Backend.DomainLayer.Puzzle import Puzzle
        from Backend.DomainLayer.Enums import GateType

        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationError("name required")

        default_gate_set_raw = payload.get("default_gate_set", [])
        gate_set = {GateType(x) for x in default_gate_set_raw}

        p = Puzzle(
            id=0,
            name=name,
            creator_user_id=user_id,
            description=payload.get("description", "") or "",
            status=PuzzleStatus.DRAFT,
            budget=int(payload.get("budget", 0)),
            time_limit_seconds=payload.get("time_limit_seconds", None),
            default_gate_set=gate_set,
        )
        created = self.repo.create(p)
        return created.to_dict()

    def publish(self, session_token: str, puzzle_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        if user.role != UserRole.ADMIN and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        p.publish()
        self.repo.update(p)
        return p.to_dict()

    def unpublish(self, session_token: str, puzzle_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        if user.role != UserRole.ADMIN and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        p.unpublish()
        self.repo.update(p)
        return p.to_dict()

    def add_test_case(self, session_token: str, puzzle_id: int, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        if user.role != UserRole.ADMIN and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
        from Backend.DomainLayer.Enums import TestCaseKind

        tc = PuzzleTestCase(
            id=0,
            puzzle_id=puzzle_id,
            kind=TestCaseKind(payload.get("kind")),
            inputs=payload.get("inputs"),
            expected_outputs=payload.get("expected_outputs"),
        )
        saved = self.repo.add_test_case(tc)
        return saved.to_dict()

    def list_test_cases(self, session_token: str, puzzle_id: int) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        tcs = self.repo.list_test_cases(puzzle_id)
        return [tc.to_dict() for tc in tcs]
