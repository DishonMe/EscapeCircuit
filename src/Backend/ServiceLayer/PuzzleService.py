from typing import Dict, Any, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus

from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.DomainLayer.Utils import utcnow


class PuzzleService:
    """
    All actions must call AuthService.
    """
    def __init__(self, puzzle_repo: PuzzleRepo, user_repo: UserRepo, auth_service: AuthService, solve_repo: SolveRepo | None = None):
        self.repo = puzzle_repo
        self.user_repo = user_repo
        self.auth = auth_service
        self.solve_repo = solve_repo

    def _enrich_puzzle(self, p_dict: dict) -> dict:
        # Helper to attach creator object
        creator_id = p_dict.get("creator_user_id")
        if creator_id is not None:
            user = self.user_repo.get_by_id(int(creator_id))
            if user:
                p_dict["creator"] = user.to_dict()
        return p_dict

    def browse(self, session_token: str, limit: int = 50, offset: int = 0) -> dict:
        _ = self.auth.require_user_id(session_token)
        puzzles = self.repo.list_published(limit=limit, offset=offset)
        
        # Count total published for pagination
        total = self.repo.count_published()
        
        # Avoid division by zero if limit is 0 (should not happen via API validation usually)
        limit = max(1, limit)
        
        total_pages = (total + limit - 1) // limit # Ceiling division
        
        return {
            "data": [self._enrich_puzzle(p.to_dict()) for p in puzzles],
            "meta": {
                "page": (offset // limit) + 1,
                "total": total,
                "totalPages": total_pages
            }
        }

    def search(self, session_token: str, q: str, only_published: bool = True) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        puzzles = self.repo.search_by_name(q, only_published=only_published)
        return [self._enrich_puzzle(p.to_dict()) for p in puzzles]

    def get(self, session_token: str, puzzle_id: int) -> dict:
        _ = self.auth.require_user_id(session_token)
        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")
        
        d = self._enrich_puzzle(p.to_dict())
        
        # Populate inputs/outputs from test cases if not present
        # This is needed because Puzzle model doesn't store them, but Frontend needs them.
        tcs = self.repo.list_test_cases(puzzle_id)
        if tcs:
            # Assume all test cases have same inputs/outputs keys. Take the first one.
            first_tc = tcs[0]
            d["inputs"] = list(first_tc.inputs.keys())
            d["outputs"] = list(first_tc.expected_outputs.keys())
        
        return d

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
        return self._enrich_puzzle(created.to_dict())

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

        # Publish preconditions (ADD/ARD):
        # 1) at least one test case
        if not self.repo.list_test_cases(puzzle_id):
            raise ValidationError("cannot publish without test cases")

        # 2) creator must have solved (self-solve). If SolveRepo isn't wired yet,
        #    we skip this check to avoid breaking dependency injection.
        if self.solve_repo is not None and user.role != UserRole.ADMIN:
            if not self.solve_repo.has_passed(user_id, puzzle_id):
                raise ValidationError("creator must solve the puzzle before publishing")

        # treat created_at as upload datetime
        p.created_at = utcnow()

        p.publish()
        self.repo.update(p)
        return self._enrich_puzzle(p.to_dict())

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
        return self._enrich_puzzle(p.to_dict())

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
