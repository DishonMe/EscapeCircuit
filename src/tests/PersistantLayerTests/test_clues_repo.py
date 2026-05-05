import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.CluesRepo import CluesRepo, CluesExhausted


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return CluesRepo(conn)


class TestCluesRepoSchema:
    """Test CluesRepo schema creation"""
    
    def test_schema_created(self, conn, repo):
        """Test clue_requests table is created"""
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='clue_requests'"
        ).fetchone()
        assert row is not None

    def test_index_created(self, conn, repo):
        """Test unique index on request_id is created"""
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_clue_requests_request_id'"
        ).fetchone()
        assert row is not None


class TestCountForAttempt:
    """Test count_for_attempt method"""
    
    def test_count_for_attempt_empty(self, repo):
        """Test count returns 0 when no clues requested"""
        count = repo.count_for_attempt(attempt_id=1)
        assert count == 0

    def test_count_for_attempt_single(self, repo):
        """Test count returns 1 after one clue"""
        repo.record_next_clue(1, 1, 1, 5, 3)
        count = repo.count_for_attempt(attempt_id=1)
        assert count == 1

    def test_count_for_attempt_multiple(self, repo):
        """Test count returns correct number after multiple clues"""
        repo.record_next_clue(1, 1, 1, 5, 5)
        repo.record_next_clue(1, 1, 1, 5, 5)
        repo.record_next_clue(1, 1, 1, 5, 5)
        count = repo.count_for_attempt(attempt_id=1)
        assert count == 3

    def test_count_for_attempt_isolated(self, repo):
        """Test count is isolated by attempt_id"""
        repo.record_next_clue(1, 1, 1, 5, 5)
        repo.record_next_clue(1, 1, 1, 5, 5)
        repo.record_next_clue(2, 1, 1, 5, 5)
        
        count_attempt1 = repo.count_for_attempt(attempt_id=1)
        count_attempt2 = repo.count_for_attempt(attempt_id=2)
        
        assert count_attempt1 == 2
        assert count_attempt2 == 1


class TestTotalPenaltyForAttempt:
    """Test total_penalty_for_attempt method"""
    
    def test_total_penalty_empty(self, repo):
        """Test penalty is 0 when no clues requested"""
        penalty = repo.total_penalty_for_attempt(attempt_id=1)
        assert penalty == 0

    def test_total_penalty_single(self, repo):
        """Test penalty sums correctly for single clue"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        penalty = repo.total_penalty_for_attempt(attempt_id=1)
        assert penalty == 10

    def test_total_penalty_multiple(self, repo):
        """Test penalty sums correctly for multiple clues"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        repo.record_next_clue(1, 1, 1, 20, 5)
        repo.record_next_clue(1, 1, 1, 15, 5)
        penalty = repo.total_penalty_for_attempt(attempt_id=1)
        assert penalty == 45

    def test_total_penalty_isolated(self, repo):
        """Test penalty is isolated by attempt_id"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        repo.record_next_clue(1, 1, 1, 20, 5)
        repo.record_next_clue(2, 1, 1, 100, 5)
        
        penalty1 = repo.total_penalty_for_attempt(attempt_id=1)
        penalty2 = repo.total_penalty_for_attempt(attempt_id=2)
        
        assert penalty1 == 30
        assert penalty2 == 100


class TestListForAttempt:
    """Test list_for_attempt method"""
    
    def test_list_for_attempt_empty(self, repo):
        """Test list returns empty when no clues"""
        clues = repo.list_for_attempt(attempt_id=1)
        assert clues == []

    def test_list_for_attempt_single(self, repo):
        """Test list returns single clue"""
        result = repo.record_next_clue(1, 1, 1, 10, 5)
        clues = repo.list_for_attempt(attempt_id=1)
        
        assert len(clues) == 1
        assert clues[0]["clue_index"] == 0
        assert clues[0]["penalty_seconds"] == 10

    def test_list_for_attempt_multiple_ordered(self, repo):
        """Test list returns clues in order by index"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        repo.record_next_clue(1, 1, 1, 20, 5)
        repo.record_next_clue(1, 1, 1, 30, 5)
        
        clues = repo.list_for_attempt(attempt_id=1)
        
        assert len(clues) == 3
        assert clues[0]["clue_index"] == 0
        assert clues[1]["clue_index"] == 1
        assert clues[2]["clue_index"] == 2

    def test_list_for_attempt_with_request_id(self, repo):
        """Test list includes request_id"""
        repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        clues = repo.list_for_attempt(attempt_id=1)
        
        assert len(clues) == 1
        assert clues[0]["request_id"] == "req-123"

    def test_list_for_attempt_isolated(self, repo):
        """Test list is isolated by attempt_id"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        repo.record_next_clue(2, 1, 1, 20, 5)
        
        clues1 = repo.list_for_attempt(attempt_id=1)
        clues2 = repo.list_for_attempt(attempt_id=2)
        
        assert len(clues1) == 1
        assert len(clues2) == 1
        assert clues1[0]["penalty_seconds"] == 10
        assert clues2[0]["penalty_seconds"] == 20


class TestFindByRequestId:
    """Test find_by_request_id method"""
    
    def test_find_by_request_id_not_found(self, repo):
        """Test returns None when request_id doesn't exist"""
        result = repo.find_by_request_id(attempt_id=1, request_id="not-found")
        assert result is None

    def test_find_by_request_id_empty_request_id(self, repo):
        """Test returns None when request_id is empty"""
        result = repo.find_by_request_id(attempt_id=1, request_id="")
        assert result is None

    def test_find_by_request_id_found(self, repo):
        """Test finds clue by request_id"""
        repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        result = repo.find_by_request_id(attempt_id=1, request_id="req-123")
        
        assert result is not None
        assert result["clue_index"] == 0
        assert result["penalty_seconds"] == 10
        assert result["request_id"] == "req-123"

    def test_find_by_request_id_isolated_by_attempt(self, repo):
        """Test find is isolated by attempt_id"""
        repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        repo.record_next_clue(2, 1, 1, 20, 5, request_id="req-123")
        
        result1 = repo.find_by_request_id(attempt_id=1, request_id="req-123")
        result2 = repo.find_by_request_id(attempt_id=2, request_id="req-123")
        
        assert result1 is not None and result1["penalty_seconds"] == 10
        assert result2 is not None and result2["penalty_seconds"] == 20

    def test_find_by_request_id_without_request_id(self, repo):
        """Test find only works for clues with request_id"""
        repo.record_next_clue(1, 1, 1, 10, 5, request_id=None)
        result = repo.find_by_request_id(attempt_id=1, request_id="any-id")
        assert result is None


class TestRecordNextClue:
    """Test record_next_clue method"""
    
    def test_record_next_clue_first(self, repo):
        """Test first clue gets index 0"""
        result = repo.record_next_clue(1, 1, 1, 10, 3)
        
        assert result["clue_index"] == 0
        assert result["penalty_seconds"] == 10
        assert result["replayed"] is False

    def test_record_next_clue_sequential(self, repo):
        """Test clues get sequential indices"""
        result1 = repo.record_next_clue(1, 1, 1, 10, 5)
        result2 = repo.record_next_clue(1, 1, 1, 20, 5)
        result3 = repo.record_next_clue(1, 1, 1, 30, 5)
        
        assert result1["clue_index"] == 0
        assert result2["clue_index"] == 1
        assert result3["clue_index"] == 2

    def test_record_next_clue_exhausted(self, repo):
        """Test raises CluesExhausted when all clues consumed"""
        repo.record_next_clue(1, 1, 1, 10, 2)
        repo.record_next_clue(1, 1, 1, 20, 2)
        
        with pytest.raises(CluesExhausted):
            repo.record_next_clue(1, 1, 1, 30, 2)

    def test_record_next_clue_with_request_id(self, repo):
        """Test recording clue with request_id"""
        result = repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        
        assert result["clue_index"] == 0
        assert result["replayed"] is False
        
        # Verify it was stored
        found = repo.find_by_request_id(1, "req-123")
        assert found is not None
        assert found["request_id"] == "req-123"

    def test_record_next_clue_idempotency_same_request_id(self, repo):
        """Test same request_id replays without consuming new clue"""
        result1 = repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        result2 = repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        
        assert result1["clue_index"] == 0
        assert result1["replayed"] is False
        
        assert result2["clue_index"] == 0
        assert result2["replayed"] is True
        
        # Count should be 1, not 2
        count = repo.count_for_attempt(1)
        assert count == 1

    def test_record_next_clue_different_request_ids(self, repo):
        """Test different request_ids consume separate clues"""
        result1 = repo.record_next_clue(1, 1, 1, 10, 5, request_id="req-123")
        result2 = repo.record_next_clue(1, 1, 1, 20, 5, request_id="req-456")
        
        assert result1["clue_index"] == 0
        assert result2["clue_index"] == 1
        assert result1["replayed"] is False
        assert result2["replayed"] is False

    def test_record_next_clue_isolated_by_attempt(self, repo):
        """Test clues are isolated by attempt_id"""
        result1 = repo.record_next_clue(1, 1, 1, 10, 5)
        result2 = repo.record_next_clue(2, 1, 1, 20, 5)
        
        assert result1["clue_index"] == 0
        assert result2["clue_index"] == 0
        
        count1 = repo.count_for_attempt(1)
        count2 = repo.count_for_attempt(2)
        assert count1 == 1
        assert count2 == 1

    def test_record_next_clue_stores_user_and_puzzle(self, repo, conn):
        """Test user_id and puzzle_id are stored"""
        repo.record_next_clue(1, 5, 99, 10, 5)
        
        row = conn.execute(
            "SELECT user_id, puzzle_id FROM clue_requests WHERE attempt_id=1"
        ).fetchone()
        
        assert int(row["user_id"]) == 5
        assert int(row["puzzle_id"]) == 99

    def test_record_next_clue_stores_timestamp(self, repo, conn):
        """Test requested_at timestamp is stored"""
        repo.record_next_clue(1, 1, 1, 10, 5)
        
        row = conn.execute(
            "SELECT requested_at FROM clue_requests WHERE attempt_id=1"
        ).fetchone()
        
        assert row["requested_at"] is not None
        # Verify it's ISO format
        assert "T" in row["requested_at"]


class TestCluesRepoIntegration:
    """Integration tests combining multiple operations"""
    
    def test_full_clue_lifecycle(self, repo):
        """Test complete flow: record, count, list, find"""
        # Record multiple clues
        repo.record_next_clue(1, 1, 1, 5, 10, request_id="req-1")
        repo.record_next_clue(1, 1, 1, 10, 10, request_id="req-2")
        repo.record_next_clue(1, 1, 1, 15, 10)
        
        # Verify count
        count = repo.count_for_attempt(1)
        assert count == 3
        
        # Verify total penalty
        penalty = repo.total_penalty_for_attempt(1)
        assert penalty == 30
        
        # Verify list
        clues = repo.list_for_attempt(1)
        assert len(clues) == 3
        
        # Verify find
        found = repo.find_by_request_id(1, "req-1")
        assert found is not None
        assert found["clue_index"] == 0

    def test_multiple_attempts_independence(self, repo):
        """Test multiple attempts don't interfere"""
        for attempt_id in [1, 2, 3]:
            for i in range(5):
                repo.record_next_clue(attempt_id, 1, 1, 10 * (i + 1), 5)
        
        # Each attempt should have 5 clues
        for attempt_id in [1, 2, 3]:
            count = repo.count_for_attempt(attempt_id)
            assert count == 5

    def test_exhaustion_per_attempt(self, repo):
        """Test exhaustion is per-attempt"""
        # Exhaust attempt 1
        repo.record_next_clue(1, 1, 1, 10, 2)
        repo.record_next_clue(1, 1, 1, 20, 2)
        
        with pytest.raises(CluesExhausted):
            repo.record_next_clue(1, 1, 1, 30, 2)
        
        # Attempt 2 should still work
        result = repo.record_next_clue(2, 1, 1, 10, 3)
        assert result["clue_index"] == 0
