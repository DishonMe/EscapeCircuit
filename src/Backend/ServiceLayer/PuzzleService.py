import sqlite3
from typing import Dict, Any, List, Set
import pathlib
import os
import shutil
import re
import json

from Backend import settings
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus, GateType

from Backend.PersistantLayer._db import transaction
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.DomainLayer.Utils import utcnow


class PuzzleService:
    """
    All actions must call AuthService.
    """
    def __init__(self, puzzle_repo: PuzzleRepo, user_repo: UserRepo, auth_service: AuthService, solve_repo: SolveRepo | None = None, arsenal_service = None):
        self.repo = puzzle_repo
        self.user_repo = user_repo
        self.auth = auth_service
        self.solve_repo = solve_repo
        self.arsenal_service = arsenal_service

    @staticmethod
    def _slugify_puzzle_name(name: str) -> str:
        sanitized = re.sub(r'[^\w\s-]', '', name or '')
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        return sanitized.lower().strip('_')

    @staticmethod
    def _sanitize_puzzle_name(name: str) -> str:
        """Sanitize puzzle name for use in directory/file names (matches creation logic).
        Convert spaces to underscores, convert to lowercase, and strip illegal characters."""
        sanitized = re.sub(r'[^\w\s-]', '', name or '')
        sanitized = re.sub(r'[\s-]+', '_', sanitized)
        return sanitized.lower()

    def _delete_riddle_files(self, puzzle_id: int, puzzle_name: str) -> None:
        """Delete riddle directory for a puzzle using puzzle_id and name.
        This uses the same naming convention as creation: riddle_{puzzle_id}_{sanitized_name}"""
        try:
            # Get riddles directory path
            current_file = pathlib.Path(__file__).resolve()
            root_dir = current_file.parent.parent.parent.parent
            riddles_dir = root_dir / 'riddles'
            
            if not riddles_dir.exists():
                print(f"[DELETE] Riddles directory not found: {riddles_dir}")
                return
            
            # Reconstruct directory name using the same logic as creation
            sanitized_name = self._sanitize_puzzle_name(puzzle_name)
            riddle_dir_name = f'riddle_{puzzle_id}_{sanitized_name}'
            riddle_dir_path = riddles_dir / riddle_dir_name
            
            # Delete the directory if it exists
            if riddle_dir_path.exists():
                try:
                    shutil.rmtree(riddle_dir_path)
                    print(f"✓ Successfully deleted puzzle directory: {riddle_dir_path}")
                except Exception as e:
                    print(f"⚠ Error deleting directory {riddle_dir_path}: {e}")
            else:
                print(f"[DELETE] Directory not found: {riddle_dir_path}")
                # Try legacy search as fallback
                puzzle_slug = self._slugify_puzzle_name(puzzle_name)
                for item in riddles_dir.iterdir():
                    if item.is_dir() and re.match(rf'riddle_\d+_{re.escape(puzzle_slug)}', item.name.lower()):
                        try:
                            shutil.rmtree(item)
                            print(f"[DELETE] Removed legacy puzzle directory: {item.name}")
                            return
                        except Exception as e:
                            print(f"[WARNING] Failed to delete legacy directory {item.name}: {e}")
        except Exception as e:
            print(f"[WARNING] Error during riddle cleanup: {e}")

    def _enrich_puzzle(self, p_dict: dict) -> dict:
        # Helper to attach creator object
        creator_id = p_dict.get("creator_user_id")
        if creator_id is not None:
            user = self.user_repo.get_by_id(int(creator_id))
            if user:
                p_dict["creator"] = user.to_dict()
        
        # Count actual solves (including creator's solves)
        puzzle_id = p_dict.get("id")
        if puzzle_id is not None and self.solve_repo:
            try:
                # Count distinct users who have passed this puzzle
                count = self.solve_repo.conn.execute(
                    "SELECT COUNT(DISTINCT user_id) as cnt FROM solve_attempts WHERE puzzle_id = ? AND passed = 1",
                    (int(puzzle_id),)
                ).fetchone()
                if count:
                    p_dict["solvedCount"] = count[0]
            except Exception:
                pass
        
        return p_dict

    def browse(
        self,
        session_token: str,
        limit: int = settings.BROWSE_PUZZLES_DEFAULT_LIMIT,
        offset: int = 0,
        search: str = None,
        creator_id: int = None,
        creator_username: str = None,
        creator_experience_level: str = None,
        min_difficulty: float = None,
        max_difficulty: float = None,
        only_experienced_difficulty: bool = False,
        min_clearness: float = None,
        max_clearness: float = None,
        only_experienced_clearness: bool = False,
        min_fun: float = None,
        max_fun: float = None,
        only_experienced_fun: bool = False,
        date_from: str = None,
        date_to: str = None,
        order_by: str = "created_at",
        order_direction: str = "DESC",
        order_only_experienced: bool = False
    ) -> dict:
        _ = self.auth.require_user_id(session_token)
        puzzles = self.repo.list_published(
            limit=limit,
            offset=offset,
            search=search,
            creator_id=creator_id,
            creator_username=creator_username,
            creator_experience_level=creator_experience_level,
            min_difficulty=min_difficulty,
            max_difficulty=max_difficulty,
            only_experienced_difficulty=only_experienced_difficulty,
            min_clearness=min_clearness,
            max_clearness=max_clearness,
            only_experienced_clearness=only_experienced_clearness,
            min_fun=min_fun,
            max_fun=max_fun,
            only_experienced_fun=only_experienced_fun,
            date_from=date_from,
            date_to=date_to,
            order_by=order_by,
            order_direction=order_direction,
            order_only_experienced=order_only_experienced
        )
        
        # Count total with same filters for pagination
        total = self.repo.count_published(
            search=search,
            creator_id=creator_id,
            creator_username=creator_username,
            creator_experience_level=creator_experience_level,
            min_difficulty=min_difficulty,
            max_difficulty=max_difficulty,
            only_experienced_difficulty=only_experienced_difficulty,
            min_clearness=min_clearness,
            max_clearness=max_clearness,
            only_experienced_clearness=only_experienced_clearness,
            min_fun=min_fun,
            max_fun=max_fun,
            only_experienced_fun=only_experienced_fun,
            date_from=date_from,
            date_to=date_to
        )
        
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

    def list_my_puzzles(
        self,
        session_token: str,
        limit: int = settings.LIST_MY_PUZZLES_DEFAULT_LIMIT,
        offset: int = 0,
        search: str = None,
        order_by: str = "created_at",
        order_direction: str = "DESC"
    ) -> dict:
        user_id = self.auth.require_user_id(session_token)
        
        # Get all puzzles created by the user (both published and unpublished)
        where_clauses = ["creator_user_id=?"]
        params = [user_id]
        
        if search:
            where_clauses.append("name LIKE ?")
            params.append(f"%{search}%")
        
        where_clause = " AND ".join(where_clauses)
        
        # Query for puzzles
        puzzles = self.repo.conn.execute(f"""
            SELECT * FROM puzzles 
            WHERE {where_clause}
            ORDER BY {order_by} {order_direction}
            LIMIT ? OFFSET ?
        """, params + [limit, offset]).fetchall()
        
        puzzles = [self.repo._row_to_puzzle(row) for row in puzzles]
        
        # Count total
        total = self.repo.conn.execute(f"""
            SELECT COUNT(*) FROM puzzles WHERE {where_clause}
        """, params).fetchone()[0]
        
        limit = max(1, limit)
        total_pages = (total + limit - 1) // limit
        
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
        user_id = self.auth.require_user_id(session_token)
        print(f"DEBUG: PuzzleService.get fetching id={puzzle_id}")
        p = self.repo.get_by_id(puzzle_id)
        if not p:
            print(f"DEBUG: PuzzleService.get id={puzzle_id} NOT FOUND in repo")
            raise ValidationError("puzzle not found")
        
        d = self._enrich_puzzle(p.to_dict())
        
        # Add gate limits (allowed gates that player can use)
        # Get all available gates and filter to only those in default_gate_set
        from Backend.DomainLayer.Enums import GateType
        all_gates = {g.value for g in GateType}
        allowed_gates = {g.value for g in p.default_gate_set}
        blocked_gates = sorted(list(all_gates - allowed_gates))
        d["filteredBasicComponents"] = blocked_gates if blocked_gates else []
        
        # Add gate-specific limits from test cases
        # Format: { "gate_name": limit_value_or_null }
        gate_limits = {}
        try:
            tcs = self.repo.list_test_cases(puzzle_id)
            for tc in tcs:
                if tc.gate_name and tc.gate_name in allowed_gates:
                    if tc.gate_name not in gate_limits:
                        # Store the limit (None means unlimited)
                        gate_limits[tc.gate_name] = tc.gate_limit
            
            # Ensure all allowed gates are in the dict
            for gate in allowed_gates:
                if gate not in gate_limits:
                    gate_limits[gate] = None
        except Exception:
            # If something fails, just set all allowed gates as unlimited
            gate_limits = {gate: None for gate in allowed_gates}
        
        d["gateLimits"] = gate_limits
        
        # Add times saved count
        if puzzle_id is not None and self.solve_repo:
            try:
                saved_count = self.solve_repo.conn.execute(
                    "SELECT COUNT(*) as cnt FROM saved_puzzles WHERE puzzle_id = ?",
                    (int(puzzle_id),)
                ).fetchone()
                if saved_count:
                    d["timesSaved"] = saved_count[0]
            except Exception:
                d["timesSaved"] = 0
        else:
            d["timesSaved"] = 0
        
        # Add medal distribution (count of users who earned each medal level)
        if puzzle_id is not None and self.solve_repo:
            try:
                medal_dist = self.solve_repo.conn.execute(
                    """SELECT best_medal, COUNT(*) as cnt FROM puzzle_progress 
                       WHERE puzzle_id = ? GROUP BY best_medal""",
                    (int(puzzle_id),)
                ).fetchall()
                medal_counts = {"none": 0, "bronze": 0, "silver": 0, "gold": 0}
                for medal_level, count in medal_dist:
                    if medal_level == 0:
                        medal_counts["none"] = count
                    elif medal_level == 1:
                        medal_counts["bronze"] = count
                    elif medal_level == 2:
                        medal_counts["silver"] = count
                    elif medal_level == 3:
                        medal_counts["gold"] = count
                d["medalDistribution"] = medal_counts
            except Exception:
                d["medalDistribution"] = {"none": 0, "bronze": 0, "silver": 0, "gold": 0}
        else:
            d["medalDistribution"] = {"none": 0, "bronze": 0, "silver": 0, "gold": 0}
        
        # Populate inputs/outputs from test cases if not present
        # This is needed because Puzzle model doesn't store them, but Frontend needs them.
        tcs = self.repo.list_test_cases(puzzle_id)
        if tcs:
            # Return all test cases as array for frontend display
            test_cases_data = []
            for tc in tcs:
                # Extract actual data - don't default to empty dict if data exists
                inputs = tc.inputs if tc.inputs else {}
                outputs = tc.expected_outputs if tc.expected_outputs else {}
                
                # For stream test cases, use the stream data
                if hasattr(tc, 'input_stream') and tc.input_stream:
                    inputs = tc.input_stream
                if hasattr(tc, 'expected_output_stream') and tc.expected_output_stream:
                    outputs = tc.expected_output_stream
                
                tc_obj = {
                    "inputs": inputs,
                    "outputs": outputs,
                }
                test_cases_data.append(tc_obj)
            
            d["test_cases"] = test_cases_data if test_cases_data else []
            
            # For backward compatibility, also extract input/output array from first test case
            first_tc = tcs[0]
            if first_tc.inputs:
                d["inputs"] = list(first_tc.inputs.keys()) if first_tc.inputs else []
            elif first_tc.input_stream and isinstance(first_tc.input_stream, list) and len(first_tc.input_stream) > 0:
                # For stream test cases, get input names from first frame.
                first_input = first_tc.input_stream[0]
                if isinstance(first_input, dict):
                    d["inputs"] = list(first_input.keys())
                elif isinstance(first_input, (str, int)):
                    d["inputs"] = [str(first_input)]
                else:
                    d["inputs"] = [str(first_input)]
            
            if first_tc.expected_outputs:
                d["outputs"] = list(first_tc.expected_outputs.keys()) if first_tc.expected_outputs else []
            elif first_tc.expected_output_stream:
                if isinstance(first_tc.expected_output_stream, dict):
                    # For stream outputs, dict keys are output names.
                    d["outputs"] = list(first_tc.expected_output_stream.keys()) if first_tc.expected_output_stream else []
                elif isinstance(first_tc.expected_output_stream, (str, int)):
                    d["outputs"] = [str(first_tc.expected_output_stream)]
                else:
                    d["outputs"] = [str(first_tc.expected_output_stream)]
        
        # Add custom pieces and split arsenal into two buckets:
        # 1) creator-shared (explicit allowed IDs) and 2) solver personal arsenal.
        custom_components: List[dict] = []
        shared_arsenal_components: List[dict] = []
        solver_arsenal_components: List[dict] = []

        def _dedupe_components(components: List[dict]) -> List[dict]:
            deduped: List[dict] = []
            seen: Set[str] = set()
            for component in components or []:
                component_id = component.get("id") if isinstance(component, dict) else None
                if component_id is not None:
                    key = str(component_id)
                else:
                    key = json.dumps(component, sort_keys=True, default=str)
                if key in seen:
                    continue
                seen.add(key)
                deduped.append(component)
            return deduped

        try:
            if self.arsenal_service:
                # Custom pieces are always puzzle-specific and always available.
                custom_components = self.arsenal_service.get_custom_pieces_for_puzzle(puzzle_id)

                # Creator-shared arsenal components are always fetched from selected IDs,
                # even when solver personal arsenal is disallowed.
                allowed_ids = getattr(p, "allowed_arsenal_component_ids", None) or []
                if allowed_ids:
                    shared_arsenal_components = self.arsenal_service.get_arsenal_pieces_by_ids(allowed_ids)

                # Solver personal arsenal is controlled by allow_arsenal.
                if user_id and getattr(p, "allow_arsenal", True):
                    allowed_gates_set = {g.value for g in p.default_gate_set} if p.default_gate_set else set()
                    solver_arsenal_components = self.arsenal_service.get_user_arsenal_filtered_by_gates(
                        user_id, allowed_gates_set
                    )

            shared_arsenal_components = _dedupe_components(shared_arsenal_components)
            solver_arsenal_components = _dedupe_components(solver_arsenal_components)
            merged_arsenal_components = _dedupe_components(
                shared_arsenal_components + solver_arsenal_components
            )

            # Backward-compatible merged list + new split lists.
            d["specialComponents"] = custom_components + merged_arsenal_components
            d["customComponents"] = custom_components
            d["arsenalComponents"] = merged_arsenal_components
            d["sharedArsenalComponents"] = shared_arsenal_components
            d["solverArsenalComponents"] = solver_arsenal_components

        except Exception:
            # Graceful fallback if component resolution fails.
            d["specialComponents"] = custom_components if custom_components else []
            d["customComponents"] = custom_components
            d["arsenalComponents"] = _dedupe_components(shared_arsenal_components + solver_arsenal_components)
            d["sharedArsenalComponents"] = _dedupe_components(shared_arsenal_components)
            d["solverArsenalComponents"] = _dedupe_components(solver_arsenal_components)
        
        return d

    def create_puzzle(self, session_token: str, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")
        if user.role not in (UserRole.CREATOR, UserRole.ADMIN):
            raise ValidationError("Only creators and admins can create puzzles. Contact an admin to upgrade your account to creator.")

        # Non-admin creators: check unpublished capacity and blocked state
        if not self._is_admin(user.role):
            _, max_unpublished = user.get_puzzle_capacity()
            current_unpublished = self._count_unpublished_puzzles(user_id)
            if current_unpublished >= max_unpublished:
                raise ValidationError(
                    f"You have reached the maximum limit of {max_unpublished} unpublished puzzles. "
                    "Delete or publish existing puzzles to create a new one."
                )
            if self._is_creator_blocked(user):
                raise ValidationError(
                    "You have exceeded your puzzle limits. Please remove puzzles until "
                    "you are within your allowed amounts before creating new ones."
                )

        from Backend.DomainLayer.Puzzle import Puzzle
        from Backend.DomainLayer.Enums import GateType, PuzzleDifficulty

        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationError("Puzzle name is required. Please provide a meaningful name for your puzzle.")
        if len(name) > settings.PUZZLE_NAME_MAX_LENGTH:
            raise ValidationError(
                f"Puzzle name must be at most {settings.PUZZLE_NAME_MAX_LENGTH} characters."
            )

        description = (payload.get("description", "") or "")
        if len(description) > settings.PUZZLE_DESCRIPTION_MAX_LENGTH:
            raise ValidationError(
                f"Puzzle description must be at most {settings.PUZZLE_DESCRIPTION_MAX_LENGTH} characters."
            )

        instructions = (payload.get("instructions", "") or "")
        if len(instructions.encode("utf-8")) > settings.PUZZLE_INSTRUCTIONS_MAX_BYTES:
            raise ValidationError(
                f"Puzzle instructions must be at most {settings.PUZZLE_INSTRUCTIONS_MAX_BYTES} bytes."
            )

        existing = self.repo.conn.execute(
            "SELECT 1 FROM puzzles WHERE LOWER(name) = LOWER(?) LIMIT 1",
            (name,),
        ).fetchone()
        if existing:
            raise ValidationError("Puzzle name already exists. Please choose a unique name.")

        default_gate_set_raw = payload.get("default_gate_set", [])
        gate_set = {GateType(x) for x in default_gate_set_raw}

        raw_diff = payload.get("difficulty", "EASY")
        try:
            difficulty = PuzzleDifficulty(raw_diff)
        except (ValueError, KeyError):
            difficulty = PuzzleDifficulty.EASY

        raw_creator_budget = payload.get("creator_budget")
        creator_budget = int(raw_creator_budget) if raw_creator_budget is not None else None
        allowed_arsenal_ids = payload.get("allowed_arsenal_component_ids")
        display_modes = payload.get("arsenal_component_display_modes")
        p = Puzzle(
            id=0,
            name=name,
            creator_user_id=user_id,
            description=description,
            status=PuzzleStatus.DRAFT,
            budget=int(payload.get("budget", 0)),
            creator_budget=creator_budget,
            time_limit_seconds=payload.get("time_limit_seconds", None),
            default_gate_set=gate_set,
            difficulty=difficulty,
            allow_arsenal=payload.get("allow_arsenal", True),
            allowed_arsenal_component_ids=allowed_arsenal_ids,
            arsenal_component_display_modes=display_modes,
        )
        p.instructions = instructions or None
        try:
            created = self.repo.create(p)
        except sqlite3.IntegrityError:
            raise ValidationError("Puzzle name already exists. Please choose a unique name.")
        self.repo.conn.commit()
        
        return self._enrich_puzzle(created.to_dict())

    def publish(self, session_token: str, puzzle_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        is_admin = self._is_admin(user.role)

        if not is_admin and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        # Publish preconditions (ADD/ARD):
        # 1) at least one test case
        if not self.repo.list_test_cases(puzzle_id):
            raise ValidationError("Cannot publish puzzle without test cases. Add at least one test case that demonstrates the solution.")

        # 2) creator must have solved (self-solve) — but only on first publish from DRAFT.
        #    If re-publishing from UNPUBLISHED status, skip this check since it was solved before.
        #    If SolveRepo isn't wired yet, we skip this check to avoid breaking dependency injection.
        if self.solve_repo is not None and not is_admin:
            # Only enforce solve requirement if transitioning from DRAFT
            if p.status == PuzzleStatus.DRAFT:
                if not self.solve_repo.has_passed(user_id, puzzle_id):
                    raise ValidationError("You must solve this puzzle yourself before publishing it. This ensures the puzzle is actually solvable.")

        # Atomic publish with per-user limit check inside IMMEDIATE transaction
        now_iso = utcnow().isoformat()
        with transaction(self.repo.conn):
            if not is_admin:
                # Use per-user published capacity
                max_published, _ = user.get_puzzle_capacity()

                published_rows = self.repo.conn.execute(
                    """
                    SELECT is_hall_of_fame, rating_count, avg_fun
                    FROM puzzles
                    WHERE creator_user_id = ? AND status = 'published'
                    """,
                    (int(user_id),),
                ).fetchall()

                current_count = 0
                for row in published_rows:
                    is_hall_of_fame = bool(int(row[0] or 0))
                    rating_count = int(row[1] or 0)
                    avg_fun = float(row[2] or 0.0)
                    is_popular = is_hall_of_fame or (rating_count >= 20 and avg_fun > 3.5)
                    if not is_popular:
                        current_count += 1

                target_is_popular = bool(getattr(p, "is_hall_of_fame", False)) or (
                    int(getattr(p, "rating_count", 0) or 0) >= 20
                    and float(getattr(p, "avg_fun", 0.0) or 0.0) > 3.5
                )

                if (
                    p.status != PuzzleStatus.PUBLISHED
                    and current_count >= max_published
                    and not target_is_popular
                ):
                    raise ValidationError(
                        f"You have reached the maximum limit of {max_published} published puzzles."
                    )

            cur = self.repo.conn.execute(
                "UPDATE puzzles SET status = 'published', created_at = ? WHERE id = ? AND status != 'published'",
                (now_iso, int(puzzle_id)),
            )
            if cur.rowcount == 0:
                raise ValidationError("Puzzle is already published or could not be updated.")

        # Re-read for return value
        p = self.repo.get_by_id(puzzle_id)
        return self._enrich_puzzle(p.to_dict())

    @staticmethod
    def _is_admin(role: Any) -> bool:
        if isinstance(role, UserRole):
            return role == UserRole.ADMIN
        return str(role).strip().lower() == UserRole.ADMIN.value

    def _count_unpublished_puzzles(self, creator_user_id: int) -> int:
        """Count DRAFT + UNPUBLISHED puzzles for a creator."""
        row = self.repo.conn.execute(
            "SELECT COUNT(*) FROM puzzles WHERE creator_user_id=? AND status IN ('draft','unpublished')",
            (int(creator_user_id),),
        ).fetchone()
        return row[0] if row else 0

    def _count_published_puzzles(self, creator_user_id: int) -> int:
        """Count PUBLISHED puzzles for a creator."""
        row = self.repo.conn.execute(
            "SELECT COUNT(*) FROM puzzles WHERE creator_user_id=? AND status='published'",
            (int(creator_user_id),),
        ).fetchone()
        return row[0] if row else 0

    def _is_creator_blocked(self, user) -> bool:
        """Return True if a creator is over their published or unpublished limit."""
        max_published, max_unpublished = user.get_puzzle_capacity()
        if self._count_published_puzzles(user.id) > max_published:
            return True
        if self._count_unpublished_puzzles(user.id) > max_unpublished:
            return True
        return False

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

        # Targeted SQL — only change status, don't clobber rating aggregates or other fields
        self.repo.conn.execute(
            "UPDATE puzzles SET status = 'unpublished' WHERE id = ? AND status = 'published'",
            (int(puzzle_id),),
        )
        self.repo.conn.commit()

        p = self.repo.get_by_id(puzzle_id)
        return self._enrich_puzzle(p.to_dict())

    def delete_puzzle(self, session_token: str, puzzle_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        if user.role != UserRole.ADMIN and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        puzzle_name = p.name
        deleted = self.repo.delete(puzzle_id)
        
        # Track user deletion to prevent re-import by insert_riddles
        self.repo.track_user_deletion(puzzle_name)
        self.repo.conn.commit()
        
        # Delete riddle files from riddles directory (using puzzle_id for accurate path reconstruction)
        self._delete_riddle_files(puzzle_id, puzzle_name)
        
        if not deleted:
            raise ValidationError("Failed to delete puzzle")
        return {"success": True, "message": "Puzzle deleted successfully"}

    def update_puzzle(self, session_token: str, puzzle_id: int, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("user not found")

        p = self.repo.get_by_id(puzzle_id)
        if not p:
            raise ValidationError("puzzle not found")

        if user.role != UserRole.ADMIN and p.creator_user_id != user_id:
            raise ValidationError("not allowed")

        # Non-admin creators: block editing when over their limits
        if not self._is_admin(user.role) and self._is_creator_blocked(user):
            raise ValidationError(
                "You have exceeded your puzzle limits. Please remove puzzles until "
                "you are within your allowed amounts before editing."
            )

        # Build targeted SQL update — only write the fields actually being changed
        # to avoid clobbering concurrent rating recalculations or status changes
        set_clauses = []
        params = []

        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationError("Puzzle name cannot be empty")
            if len(name) > settings.PUZZLE_NAME_MAX_LENGTH:
                raise ValidationError(
                    f"Puzzle name must be at most {settings.PUZZLE_NAME_MAX_LENGTH} characters."
                )
            existing = self.repo.conn.execute(
                "SELECT 1 FROM puzzles WHERE LOWER(name) = LOWER(?) AND id != ? LIMIT 1",
                (name, int(puzzle_id)),
            ).fetchone()
            if existing:
                raise ValidationError("Puzzle name already exists. Please choose a unique name.")
            set_clauses.append("name = ?")
            params.append(name)

        if "description" in payload:
            description = payload.get("description", "") or ""
            if len(description) > settings.PUZZLE_DESCRIPTION_MAX_LENGTH:
                raise ValidationError(
                    f"Puzzle description must be at most {settings.PUZZLE_DESCRIPTION_MAX_LENGTH} characters."
                )
            set_clauses.append("description = ?")
            params.append(description)

        if "instructions" in payload:
            instructions = payload.get("instructions", "") or ""
            if len(instructions.encode("utf-8")) > settings.PUZZLE_INSTRUCTIONS_MAX_BYTES:
                raise ValidationError(
                    f"Puzzle instructions must be at most {settings.PUZZLE_INSTRUCTIONS_MAX_BYTES} bytes."
                )
            set_clauses.append("instructions = ?")
            params.append(instructions)

        if "creator_comment" in payload:
            creator_comment = payload.get("creator_comment")
            # Allow None to clear the comment
            if creator_comment is not None and isinstance(creator_comment, str):
                creator_comment = creator_comment.strip() or None
                if creator_comment and len(creator_comment) > settings.PUZZLE_CREATOR_COMMENT_MAX_LENGTH:
                    raise ValidationError(
                        f"Creator comment must be at most {settings.PUZZLE_CREATOR_COMMENT_MAX_LENGTH} characters."
                    )
            set_clauses.append("creator_comment = ?")
            params.append(creator_comment)

        if "allow_arsenal" in payload:
            allow_arsenal = payload.get("allow_arsenal")
            if not isinstance(allow_arsenal, bool):
                raise ValidationError("allow_arsenal must be a boolean")
            set_clauses.append("allow_arsenal = ?")
            params.append(1 if allow_arsenal else 0)
        
        if "arsenal_component_display_modes" in payload:
            display_modes = payload.get("arsenal_component_display_modes")
            set_clauses.append("arsenal_component_display_modes = ?")
            params.append(json.dumps(display_modes) if display_modes else None)

        if set_clauses:
            params.append(int(puzzle_id))
            self.repo.conn.execute(
                f"UPDATE puzzles SET {', '.join(set_clauses)} WHERE id = ?",
                params,
            )
            self.repo.conn.commit()

        p = self.repo.get_by_id(puzzle_id)
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
        self.repo.conn.commit()
        return saved.to_dict()

    def list_test_cases(self, session_token: str, puzzle_id: int) -> List[dict]:
        _ = self.auth.require_user_id(session_token)
        tcs = self.repo.list_test_cases(puzzle_id)
        return [tc.to_dict() for tc in tcs]
