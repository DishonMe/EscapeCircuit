import sqlite3
import pytest

from Backend.PersistantLayer.AuditLogRepo import AuditLogRepo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return AuditLogRepo(conn)


class TestSchema:
    def test_table_created(self, conn, repo):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='admin_audit_log'"
        ).fetchone()
        assert row is not None

    def test_indexes_created(self, conn, repo):
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_audit%'"
        ).fetchall()
        names = {r["name"] for r in rows}
        assert "idx_audit_admin" in names
        assert "idx_audit_created" in names


class TestCreate:
    def test_create_basic(self, repo):
        log_id = repo.create(
            admin_user_id=1,
            action_type="assign_creator",
        )
        assert isinstance(log_id, int)
        assert log_id > 0

    def test_create_with_all_fields(self, repo):
        log_id = repo.create(
            admin_user_id=1,
            action_type="delete_puzzle",
            target_user_id=5,
            target_puzzle_id=10,
            details={"reason": "violation"},
        )
        assert log_id > 0

        entries = repo.list_all()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["admin_user_id"] == 1
        assert entry["action_type"] == "delete_puzzle"
        assert entry["target_user_id"] == 5
        assert entry["target_puzzle_id"] == 10
        assert entry["details"] == {"reason": "violation"}
        assert entry["created_at"] is not None

    def test_create_without_optional_fields(self, repo):
        log_id = repo.create(
            admin_user_id=1,
            action_type="remove_creator",
        )
        entries = repo.list_all()
        entry = entries[0]
        assert entry["target_user_id"] is None
        assert entry["target_puzzle_id"] is None
        assert entry["details"] == {}

    def test_create_multiple(self, repo):
        repo.create(admin_user_id=1, action_type="assign_creator")
        repo.create(admin_user_id=2, action_type="delete_puzzle")
        repo.create(admin_user_id=1, action_type="unpublish_puzzle")

        entries = repo.list_all()
        assert len(entries) == 3


class TestListAll:
    def test_empty_list(self, repo):
        entries = repo.list_all()
        assert entries == []

    def test_pagination(self, repo):
        for i in range(5):
            repo.create(admin_user_id=1, action_type=f"action_{i}")

        page1 = repo.list_all(limit=2, offset=0)
        assert len(page1) == 2

        page2 = repo.list_all(limit=2, offset=2)
        assert len(page2) == 2

        page3 = repo.list_all(limit=2, offset=4)
        assert len(page3) == 1

    def test_filter_by_action_type(self, repo):
        repo.create(admin_user_id=1, action_type="assign_creator")
        repo.create(admin_user_id=1, action_type="delete_puzzle")
        repo.create(admin_user_id=1, action_type="assign_creator")

        filtered = repo.list_all(action_type="assign_creator")
        assert len(filtered) == 2
        for entry in filtered:
            assert entry["action_type"] == "assign_creator"

    def test_filter_by_admin_user_id(self, repo):
        repo.create(admin_user_id=1, action_type="assign_creator")
        repo.create(admin_user_id=2, action_type="delete_puzzle")
        repo.create(admin_user_id=1, action_type="unpublish_puzzle")

        filtered = repo.list_all(admin_user_id=1)
        assert len(filtered) == 2
        for entry in filtered:
            assert entry["admin_user_id"] == 1

    def test_filter_by_both(self, repo):
        repo.create(admin_user_id=1, action_type="assign_creator")
        repo.create(admin_user_id=1, action_type="delete_puzzle")
        repo.create(admin_user_id=2, action_type="assign_creator")

        filtered = repo.list_all(action_type="assign_creator", admin_user_id=1)
        assert len(filtered) == 1
        assert filtered[0]["admin_user_id"] == 1
        assert filtered[0]["action_type"] == "assign_creator"

    def test_ordered_by_created_at_desc(self, repo):
        id1 = repo.create(admin_user_id=1, action_type="first")
        id2 = repo.create(admin_user_id=1, action_type="second")
        id3 = repo.create(admin_user_id=1, action_type="third")

        entries = repo.list_all()
        # Most recent first
        assert entries[0]["id"] == id3
        assert entries[1]["id"] == id2
        assert entries[2]["id"] == id1

    def test_details_json_parsed(self, repo):
        repo.create(
            admin_user_id=1,
            action_type="test",
            details={"key": "value", "nested": {"a": 1}},
        )
        entries = repo.list_all()
        assert entries[0]["details"] == {"key": "value", "nested": {"a": 1}}
