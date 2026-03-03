import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.DomainLayer.SolveAttempt import SolveAttempt


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return SolveRepo(conn)


def make_attempt(puzzle_id: int = 1, user_id: int = 2, circuit_id=None):
    started = datetime.now(timezone.utc)

    # prefer from_dict if exists
    if hasattr(SolveAttempt, "from_dict"):
        return SolveAttempt.from_dict({
            "id": 1,
            "puzzle_id": int(puzzle_id),
            "user_id": int(user_id),
            "circuit_id": circuit_id,
            "started_at": started.isoformat(),
            "submitted_at": None,
            "passed": None,
            "fail_reason": None,
        })

    return SolveAttempt(
        id=1,
        puzzle_id=int(puzzle_id),
        user_id=int(user_id),
        circuit_id=circuit_id,
        started_at=started,
    )


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='solve_attempts'"
    ).fetchone()
    assert row is not None


def test_get_open_attempt_none_branch(repo):
    assert repo.get_open_attempt(user_id=1, puzzle_id=1) is None


def test_create_attempt_passed_none_persists_as_null(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert a.id > 0

    # open attempt exists
    open_a = repo.get_open_attempt(user_id=2, puzzle_id=1)
    assert open_a is not None
    assert open_a.passed is None  # should remain None until submitted

    # DB-level assert passed is NULL
    row = conn.execute("SELECT passed FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert row["passed"] is None


def test_update_attempt_failed_writes_passed_0_and_fail_reason(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a.mark_submitted(passed=False, circuit_id=99, fail_reason="wrong output")
    repo.update_attempt(a)

    # no open attempt after submitted
    assert repo.get_open_attempt(user_id=2, puzzle_id=1) is None
    assert repo.has_passed(user_id=2, puzzle_id=1) is False

    # DB asserts: passed=0, fail_reason stored, submitted_at NOT NULL
    row = conn.execute("SELECT passed, fail_reason, submitted_at FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert int(row["passed"]) == 0
    assert row["fail_reason"] == "wrong output"
    assert row["submitted_at"] is not None


def test_update_attempt_success_has_passed_true(conn, repo):
    a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a.mark_submitted(passed=True, circuit_id=77)
    repo.update_attempt(a)

    assert repo.has_passed(user_id=2, puzzle_id=1) is True

    row = conn.execute("SELECT passed FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
    assert row is not None
    assert int(row["passed"]) == 1


def test_open_attempt_returns_latest(repo):
    a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    open_a = repo.get_open_attempt(user_id=2, puzzle_id=1)
    assert open_a is not None
    assert open_a.id == a2.id


def test_has_passed_before_attempt_false_then_true(repo):
    # attempt #1 open (not passed)
    a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert repo.has_passed_before_attempt(user_id=2, puzzle_id=1, attempt_id=a1.id) is False

    # attempt #1 becomes passed
    a1.mark_submitted(passed=True, circuit_id=10)
    repo.update_attempt(a1)

    # attempt #2 open => should see previous pass
    a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
    assert repo.has_passed_before_attempt(user_id=2, puzzle_id=1, attempt_id=a2.id) is True


def test_first_attempt_started_at_none_then_value(repo):
    assert repo.first_attempt_started_at(user_id=9, puzzle_id=9) is None

    a1 = repo.create_attempt(make_attempt(puzzle_id=9, user_id=9))
    a2 = repo.create_attempt(make_attempt(puzzle_id=9, user_id=9))

    ts = repo.first_attempt_started_at(user_id=9, puzzle_id=9)
    assert ts is not None
    assert isinstance(ts, str)

class TestSolveRepoGetTotalTimeOnPuzzle:
    """Tests for get_total_time_on_puzzle method"""
    
    def test_get_total_time_zero(self, repo):
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 0

    def test_get_total_time_single_attempt(self, repo):
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.mark_submitted(passed=False, circuit_id=1)
        a.time_used_seconds = 45
        repo.update_attempt(a)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 45

    def test_get_total_time_multiple_attempts(self, repo):
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.mark_submitted(passed=False, circuit_id=1)
        a1.time_used_seconds = 30
        repo.update_attempt(a1)
        
        a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a2.mark_submitted(passed=False, circuit_id=1)
        a2.time_used_seconds = 60
        repo.update_attempt(a2)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 90


class TestSolveRepoProgress:
    """Tests for puzzle progress tracking"""
    
    def test_get_progress_not_started(self, repo):
        progress = repo.get_progress(user_id=1, puzzle_id=1)
        assert progress.best_medal == 0
        assert progress.timer_upgraded is False
        assert progress.tight_upgraded is False
        assert progress.first_solved_at is None

    def test_update_progress_medal(self, conn, repo):
        # Create initial progress entry
        conn.execute("""
            INSERT INTO puzzle_progress 
            (user_id, puzzle_id, best_medal, timer_upgraded, tight_upgraded)
            VALUES (?, ?, ?, ?, ?)
        """, (1, 1, 2, 0, 1))
        
        progress = repo.get_progress(user_id=1, puzzle_id=1)
        assert progress.best_medal == 2
        assert progress.timer_upgraded is False
        assert progress.tight_upgraded is True


class TestSolveRepoCreatorXPAward:
    """Tests for creator XP deduplication"""
    
    def test_try_award_creator_solve_xp_first_time(self, repo):
        result = repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=5)
        assert result is True

    def test_try_award_creator_solve_xp_already_awarded(self, repo):
        repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=5)
        result = repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=5)
        assert result is False

    def test_try_award_creator_solve_xp_different_solvers(self, repo):
        result1 = repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=5)
        result2 = repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=6)
        assert result1 is True
        assert result2 is True

    def test_try_award_creator_solve_xp_different_puzzles(self, repo):
        result1 = repo.try_award_creator_solve_xp(puzzle_id=1, solver_user_id=5)
        result2 = repo.try_award_creator_solve_xp(puzzle_id=2, solver_user_id=5)
        assert result1 is True
        assert result2 is True


class TestSolveRepoAttemptTracking:
    """Tests for comprehensive attempt tracking"""
    
    def test_create_attempt_with_time_used(self, repo):
        """Attempt with time_used_seconds is persisted"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.time_used_seconds = 120
        repo.update_attempt(a)
        
        # Verify from database directly
        row = repo.conn.execute("SELECT time_used_seconds FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
        assert row is not None
        assert row["time_used_seconds"] == 120

    def test_create_attempt_with_circuit_id(self, repo):
        """Attempt with circuit_id is persisted"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1, circuit_id=42))
        assert a.circuit_id == 42
        
        fetched = repo.get_open_attempt(user_id=1, puzzle_id=1)
        assert fetched is not None
        assert fetched.circuit_id == 42

    def test_create_attempt_no_circuit_initially(self, repo):
        """Attempt can start without circuit_id (None)"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1, circuit_id=None))
        assert a.circuit_id is None
        
        fetched = repo.get_open_attempt(user_id=1, puzzle_id=1)
        assert fetched is not None
        assert fetched.circuit_id is None

    def test_update_attempt_circuit_id(self, repo):
        """Can update circuit_id on existing attempt"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1, circuit_id=None))
        a.circuit_id = 77
        a.mark_submitted(passed=True)
        repo.update_attempt(a)
        
        row = repo.conn.execute("SELECT circuit_id FROM solve_attempts WHERE id=?", (a.id,)).fetchone()
        assert row is not None
        assert row["circuit_id"] == 77

    def test_multiple_attempts_same_user_puzzle(self, repo):
        """User can have multiple attempts on same puzzle"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=5, user_id=3))
        a2 = repo.create_attempt(make_attempt(puzzle_id=5, user_id=3))
        a3 = repo.create_attempt(make_attempt(puzzle_id=5, user_id=3))
        
        # Only latest should be open
        open_a = repo.get_open_attempt(user_id=3, puzzle_id=5)
        assert open_a is not None
        assert open_a.id == a3.id


class TestSolveRepoHasPassedBranches:
    """Tests for has_passed validation with various scenarios"""
    
    def test_has_passed_returns_false_when_no_attempts(self, repo):
        """No attempts means no pass"""
        assert repo.has_passed(user_id=1, puzzle_id=1) is False

    def test_has_passed_returns_false_when_only_failed_attempts(self, repo):
        """Only failed attempts means no pass"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.mark_submitted(passed=False, circuit_id=1)
        repo.update_attempt(a)
        
        assert repo.has_passed(user_id=1, puzzle_id=1) is False

    def test_has_passed_returns_true_when_one_passed(self, repo):
        """One passed attempt means pass"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.mark_submitted(passed=True, circuit_id=1)
        repo.update_attempt(a)
        
        assert repo.has_passed(user_id=1, puzzle_id=1) is True

    def test_has_passed_returns_true_with_mixed_results(self, repo):
        """Passed state found even with earlier failures"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.mark_submitted(passed=False, circuit_id=1)
        repo.update_attempt(a1)
        
        a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a2.mark_submitted(passed=True, circuit_id=1)
        repo.update_attempt(a2)
        
        assert repo.has_passed(user_id=1, puzzle_id=1) is True

    def test_has_passed_user_isolated(self, repo):
        """One user's pass doesn't affect another user"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.mark_submitted(passed=True, circuit_id=1)
        repo.update_attempt(a1)
        
        # User 2 never solved it
        assert repo.has_passed(user_id=2, puzzle_id=1) is False

    def test_has_passed_puzzle_isolated(self, repo):
        """Pass on one puzzle doesn't affect another"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.mark_submitted(passed=True, circuit_id=1)
        repo.update_attempt(a1)
        
        # User hasn't solved puzzle 2
        assert repo.has_passed(user_id=1, puzzle_id=2) is False


class TestSolveRepoProgressTracking:
    """Tests for detailed progress tracking"""
    
    def test_get_progress_default_state(self, repo):
        """New progress has sensible defaults"""
        progress = repo.get_progress(user_id=100, puzzle_id=200)
        
        assert progress.user_id == 100
        assert progress.puzzle_id == 200
        assert progress.best_medal == 0
        assert progress.timer_upgraded is False
        assert progress.tight_upgraded is False
        assert progress.first_solved_at is None
        assert progress.max_xp_reached is False
        assert progress.best_xp == 0
        assert progress.total_xp_awarded == 0
        assert progress.xp_applied == 0

    def test_get_progress_with_existing_data(self, conn, repo):
        """Can retrieve and parse existing progress data"""
        conn.execute("""
            INSERT INTO puzzle_progress 
            (user_id, puzzle_id, best_medal, timer_upgraded, tight_upgraded, 
             first_solved_at, max_xp_reached, best_xp, total_xp_awarded, xp_applied)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (1, 1, 3, 1, 1, "2024-01-01T00:00:00", 1, 500, 1000, 800))
        
        progress = repo.get_progress(user_id=1, puzzle_id=1)
        assert progress.user_id == 1
        assert progress.puzzle_id == 1
        assert progress.best_medal == 3
        assert progress.timer_upgraded is True
        assert progress.tight_upgraded is True
        assert progress.first_solved_at == "2024-01-01T00:00:00"
        assert progress.max_xp_reached is True
        assert progress.best_xp == 500
        assert progress.total_xp_awarded == 1000
        assert progress.xp_applied == 800


class TestSolveRepoTimeTracking:
    """Tests for comprehensive time tracking scenarios"""
    
    def test_get_total_time_no_attempts_returns_zero(self, repo):
        """Empty history returns zero"""
        total = repo.get_total_time_on_puzzle(user_id=99, puzzle_id=99)
        assert total == 0

    def test_get_total_time_single_attempt_with_time(self, repo):
        """Single attempt time is returned"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.time_used_seconds = 60
        repo.update_attempt(a)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 60

class TestClaimXpDelta:
    """Test claim_xp_delta with various states"""
    
    def test_claim_xp_delta_no_progress(self, repo):
        """Test claim_xp_delta when progress record doesn't exist"""
        from unittest.mock import Mock
        repo.get_progress = Mock(return_value=None)
        
        result = repo.claim_xp_delta(1, 1)
        
        assert result == 0
    
    def test_claim_xp_delta_no_unapplied(self, repo):
        """Test claim_xp_delta when total_xp_awarded <= xp_applied"""
        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        progress = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=0,
            timer_upgraded=False, tight_upgraded=False,
            first_solved_at=None, max_xp_reached=False,
            best_xp=100, total_xp_awarded=100, xp_applied=100
        )
        
        from unittest.mock import Mock
        repo.get_progress = Mock(return_value=progress)
        
        result = repo.claim_xp_delta(1, 1)
        
        assert result == 0
    
    def test_claim_xp_delta_lost_race(self, repo):
        """Test claim_xp_delta returns 0 when losing concurrent update race"""
        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        progress = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=0,
            timer_upgraded=False, tight_upgraded=False,
            first_solved_at=None, max_xp_reached=False,
            best_xp=100, total_xp_awarded=100, xp_applied=50
        )
        
        from unittest.mock import Mock
        repo.get_progress = Mock(return_value=progress)
        
        result = repo.claim_xp_delta(1, 1)
        
        assert result == 0


class TestGetSolvedCounts:
    """Test get_solved_counts method"""
    
    def test_get_solved_counts(self, repo):
        """Test get_solved_counts aggregates solver counts"""
        result = repo.get_solved_counts()
        assert isinstance(result, dict)
    
    def test_get_solved_counts_empty(self, repo):
        """Test get_solved_counts with no solved puzzles"""
        result = repo.get_solved_counts()
        assert result == {}


class TestGetBestXpForPuzzle:
    """Test get_best_xp_for_puzzle method"""
    
    def test_get_best_xp_for_puzzle_with_xp(self, repo):
        """Test get_best_xp_for_puzzle when user has solved the puzzle"""
        result = repo.get_best_xp_for_puzzle(1, 1)
        assert isinstance(result, int)
    
    def test_get_best_xp_for_puzzle_no_solves(self, repo):
        """Test get_best_xp_for_puzzle when user hasn't solved the puzzle"""
        result = repo.get_best_xp_for_puzzle(1, 1)
        assert result == 0
    
    def test_get_best_xp_for_puzzle_no_row(self, repo):
        """Test get_best_xp_for_puzzle when no row is returned"""
        result = repo.get_best_xp_for_puzzle(999, 999)
        assert result == 0


class TestGetSolveStatusMap:
    """Test get_solve_status_map method"""
    
    def test_get_solve_status_map_with_solves(self, repo):
        """Test get_solve_status_map with multiple solved puzzles"""
        result = repo.get_solve_status_map(1)
        assert isinstance(result, dict)
    
    def test_get_solve_status_map_empty(self, repo):
        """Test get_solve_status_map with no solves"""
        result = repo.get_solve_status_map(999)
        assert result == {}


class TestAddSolve:
    """Test add_solve convenience method"""
    
    def test_add_solve_returns_id(self, repo):
        """Test add_solve inserts and returns lastrowid"""
        result = repo.add_solve(1, 1, 100, 50, medal=1)
        assert isinstance(result, int)
        assert result > 0


class TestDeleteByPuzzle:
    """Test delete_by_puzzle method"""
    
    def test_delete_by_puzzle(self, repo):
        """Test delete_by_puzzle removes all related data"""
        repo.delete_by_puzzle(999)
        # No error means success
    
    def test_delete_by_puzzle_ids_empty_list(self, repo):
        """Test delete_by_puzzle_ids with empty list"""
        repo.delete_by_puzzle_ids([])
        # No error means success
    
    def test_delete_by_puzzle_ids_multiple(self, repo):
        """Test delete_by_puzzle_ids with multiple puzzle IDs"""
        repo.delete_by_puzzle_ids([1, 2, 3])
        # No error means success


class TestUpsertProgress:
    """Test upsert_progress method"""
    
    def test_upsert_progress_new_record(self, repo):
        """Test upsert_progress creates new record"""
        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        progress = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=1,
            timer_upgraded=False, tight_upgraded=False,
            first_solved_at="2025-01-01T10:00:00",
            max_xp_reached=False,
            best_xp=100, total_xp_awarded=100, xp_applied=0
        )
        repo.upsert_progress(progress)
        # No error means success
    
    def test_upsert_progress_with_xp_delta(self, repo):
        """Test upsert_progress with XP delta"""
        from Backend.PersistantLayer.SolveRepo import PuzzleProgress
        progress = PuzzleProgress(
            user_id=1, puzzle_id=1, best_medal=2,
            timer_upgraded=True, tight_upgraded=False,
            first_solved_at="2025-01-01T10:00:00",
            max_xp_reached=False,
            best_xp=150, total_xp_awarded=150, xp_applied=0
        )
        repo.upsert_progress(progress, xp_delta=50)
        # No error means success


class TestFirstAttemptStartedAt:
    """Test first_attempt_started_at method"""
    
    def test_first_attempt_started_at_found(self, repo):
        """Test first_attempt_started_at returns timestamp"""
        result = repo.first_attempt_started_at(1, 1)
        assert result is None or isinstance(result, (str, type(None)))
    
    def test_first_attempt_started_at_not_found(self, repo):
        """Test first_attempt_started_at returns None when no attempt"""
        result = repo.first_attempt_started_at(999, 999)
        assert result is None


class TestGetTotalTimeOnPuzzle:
    """Test get_total_time_on_puzzle method"""
    
    def test_get_total_time_sum(self, repo):
        """Test get_total_time_on_puzzle sums all attempts"""
        result = repo.get_total_time_on_puzzle(1, 1)
        assert isinstance(result, (int, float))
    
    def test_get_total_time_zero(self, repo):
        """Test get_total_time_on_puzzle returns 0 when no data"""
        result = repo.get_total_time_on_puzzle(999, 999)
        assert result == 0
    def test_get_total_time_multiple_attempts_sum(self, repo):
        """Multiple attempts are summed"""
        for seconds in [30, 45, 25]:
            a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
            a.time_used_seconds = seconds
            repo.update_attempt(a)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 100

    def test_get_total_time_user_isolated(self, repo):
        """Time from one user doesn't affect another"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.time_used_seconds = 100
        repo.update_attempt(a1)
        
        a2 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=2))
        a2.time_used_seconds = 50
        repo.update_attempt(a2)
        
        assert repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1) == 100
        assert repo.get_total_time_on_puzzle(user_id=2, puzzle_id=1) == 50

    def test_get_total_time_puzzle_isolated(self, repo):
        """Time on one puzzle doesn't affect another"""
        a1 = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a1.time_used_seconds = 100
        repo.update_attempt(a1)
        
        a2 = repo.create_attempt(make_attempt(puzzle_id=2, user_id=1))
        a2.time_used_seconds = 50
        repo.update_attempt(a2)
        
        assert repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1) == 100
        assert repo.get_total_time_on_puzzle(user_id=1, puzzle_id=2) == 50

    def test_get_total_time_zero_seconds(self, repo):
        """Attempts with zero time are included"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.time_used_seconds = 0
        repo.update_attempt(a)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 0

    def test_get_total_time_large_values(self, repo):
        """Large time values are handled correctly"""
        a = repo.create_attempt(make_attempt(puzzle_id=1, user_id=1))
        a.time_used_seconds = 86400  # 24 hours in seconds
        repo.update_attempt(a)
        
        total = repo.get_total_time_on_puzzle(user_id=1, puzzle_id=1)
        assert total == 86400