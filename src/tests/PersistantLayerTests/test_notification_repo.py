import sqlite3
import pytest

from Backend.PersistantLayer.NotificationRepo import NotificationRepo


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return NotificationRepo(conn)


class TestSchema:
    def test_table_created(self, conn, repo):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='creator_notifications'"
        ).fetchone()
        assert row is not None

    def test_index_created(self, conn, repo):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_notif_user_unread'"
        ).fetchone()
        assert row is not None


class TestCreate:
    def test_create_basic(self, repo):
        nid = repo.create(user_id=1, notif_type="solve", message="Someone solved your puzzle")
        assert isinstance(nid, int)
        assert nid > 0

    def test_create_with_all_fields(self, repo):
        nid = repo.create(
            user_id=1,
            notif_type="rating",
            message="Your puzzle was rated",
            xp_amount=50,
            puzzle_name="Adder",
            actor_username="alice",
        )
        assert nid > 0

        entries = repo.get_all(user_id=1)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["type"] == "rating"
        assert entry["message"] == "Your puzzle was rated"
        assert entry["xp_amount"] == 50
        assert entry["puzzle_name"] == "Adder"
        assert entry["actor_username"] == "alice"

    def test_create_defaults(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg")
        entries = repo.get_all(user_id=1)
        entry = entries[0]
        assert entry["xp_amount"] == 0
        assert entry["puzzle_name"] == ""
        assert entry["actor_username"] == ""


class TestGetUnread:
    def test_empty(self, repo):
        assert repo.get_unread(user_id=1) == []

    def test_returns_only_unread(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        repo.create(user_id=1, notif_type="rating", message="msg2")

        unread = repo.get_unread(user_id=1)
        assert len(unread) == 2

        repo.mark_all_read(user_id=1)
        unread = repo.get_unread(user_id=1)
        assert len(unread) == 0

    def test_filter_by_type(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        repo.create(user_id=1, notif_type="rating", message="msg2")
        repo.create(user_id=1, notif_type="solve", message="msg3")

        filtered = repo.get_unread(user_id=1, notif_type="solve")
        assert len(filtered) == 2

    def test_filter_by_puzzle_name(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1", puzzle_name="Adder")
        repo.create(user_id=1, notif_type="solve", message="m2", puzzle_name="XOR Gate")
        repo.create(user_id=1, notif_type="solve", message="m3", puzzle_name="Half Adder")

        filtered = repo.get_unread(user_id=1, puzzle_name="Adder")
        assert len(filtered) == 2  # "Adder" and "Half Adder" match LIKE %Adder%

    def test_filter_by_actor_username(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1", actor_username="alice")
        repo.create(user_id=1, notif_type="solve", message="m2", actor_username="bob")

        filtered = repo.get_unread(user_id=1, actor_username="alice")
        assert len(filtered) == 1
        assert filtered[0]["actor_username"] == "alice"

    def test_limit_and_offset(self, repo):
        for i in range(5):
            repo.create(user_id=1, notif_type="solve", message=f"msg{i}")

        page1 = repo.get_unread(user_id=1, limit=2, offset=0)
        assert len(page1) == 2

        page2 = repo.get_unread(user_id=1, limit=2, offset=2)
        assert len(page2) == 2

        page3 = repo.get_unread(user_id=1, limit=2, offset=4)
        assert len(page3) == 1

    def test_order_by_xp(self, repo):
        repo.create(user_id=1, notif_type="solve", message="low", xp_amount=10)
        repo.create(user_id=1, notif_type="solve", message="high", xp_amount=100)
        repo.create(user_id=1, notif_type="solve", message="mid", xp_amount=50)

        results = repo.get_unread(user_id=1, order_by="xp_amount", order_direction="DESC")
        assert results[0]["xp_amount"] == 100
        assert results[1]["xp_amount"] == 50
        assert results[2]["xp_amount"] == 10

    def test_user_isolation(self, repo):
        repo.create(user_id=1, notif_type="solve", message="for user 1")
        repo.create(user_id=2, notif_type="solve", message="for user 2")

        assert len(repo.get_unread(user_id=1)) == 1
        assert len(repo.get_unread(user_id=2)) == 1

    def test_filter_by_date_from(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        all_notifs = repo.get_unread(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        filtered = repo.get_unread(user_id=1, date_from=created_at)
        assert len(filtered) == 1
        assert filtered[0]["message"] == "msg1"

    def test_filter_by_date_to(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        all_notifs = repo.get_unread(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        filtered = repo.get_unread(user_id=1, date_to=created_at)
        assert len(filtered) == 1
        assert filtered[0]["message"] == "msg1"

    def test_filter_by_date_range(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        all_notifs = repo.get_unread(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        filtered = repo.get_unread(user_id=1, date_from=created_at, date_to=created_at)
        assert len(filtered) == 1


class TestGetAll:
    def test_includes_read_and_unread(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        repo.create(user_id=1, notif_type="rating", message="msg2")
        repo.mark_all_read(user_id=1)
        repo.create(user_id=1, notif_type="solve", message="msg3")

        all_notifs = repo.get_all(user_id=1)
        assert len(all_notifs) == 3

        unread = repo.get_unread(user_id=1)
        assert len(unread) == 1

    def test_filter_by_type(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=1, notif_type="rating", message="m2")

        filtered = repo.get_all(user_id=1, notif_type="rating")
        assert len(filtered) == 1
        assert filtered[0]["type"] == "rating"

    def test_limit_and_offset(self, repo):
        for i in range(5):
            repo.create(user_id=1, notif_type="solve", message=f"msg{i}")

        page = repo.get_all(user_id=1, limit=3)
        assert len(page) == 3

    def test_order_by_xp(self, repo):
        repo.create(user_id=1, notif_type="solve", message="low", xp_amount=10)
        repo.create(user_id=1, notif_type="solve", message="high", xp_amount=100)

        results = repo.get_all(user_id=1, order_by="xp_amount", order_direction="ASC")
        assert results[0]["xp_amount"] == 10
        assert results[1]["xp_amount"] == 100

    def test_filter_by_date_from(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        all_notifs = repo.get_all(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        filtered = repo.get_all(user_id=1, date_from=created_at)
        assert len(filtered) == 1
        assert filtered[0]["message"] == "msg1"

    def test_filter_by_date_to(self, repo):
        repo.create(user_id=1, notif_type="solve", message="msg1")
        all_notifs = repo.get_all(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        filtered = repo.get_all(user_id=1, date_to=created_at)
        assert len(filtered) == 1

    def test_filter_by_actor_username(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1", actor_username="alice")
        repo.create(user_id=1, notif_type="solve", message="m2", actor_username="bob")

        filtered = repo.get_all(user_id=1, actor_username="alice")
        assert len(filtered) == 1
        assert filtered[0]["actor_username"] == "alice"


class TestCountNotifications:
    def test_count_all(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=1, notif_type="rating", message="m2")
        repo.create(user_id=2, notif_type="solve", message="m3")

        assert repo.count_notifications(user_id=1) == 2
        assert repo.count_notifications(user_id=2) == 1

    def test_count_unread_only(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=1, notif_type="solve", message="m2")
        repo.mark_all_read(user_id=1)
        repo.create(user_id=1, notif_type="solve", message="m3")

        assert repo.count_notifications(user_id=1, only_unread=True) == 1
        assert repo.count_notifications(user_id=1, only_unread=False) == 3

    def test_count_by_type(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=1, notif_type="rating", message="m2")
        repo.create(user_id=1, notif_type="solve", message="m3")

        assert repo.count_notifications(user_id=1, notif_type="solve") == 2
        assert repo.count_notifications(user_id=1, notif_type="rating") == 1

    def test_count_by_puzzle_name(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1", puzzle_name="Adder")
        repo.create(user_id=1, notif_type="solve", message="m2", puzzle_name="XOR")

        assert repo.count_notifications(user_id=1, puzzle_name="Adder") == 1

    def test_count_empty(self, repo):
        assert repo.count_notifications(user_id=999) == 0

    def test_count_by_date_from(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        all_notifs = repo.get_all(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        count = repo.count_notifications(user_id=1, date_from=created_at)
        assert count == 1

    def test_count_by_date_to(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        all_notifs = repo.get_all(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        count = repo.count_notifications(user_id=1, date_to=created_at)
        assert count == 1

    def test_count_by_date_range(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        all_notifs = repo.get_all(user_id=1)
        created_at = all_notifs[0]["created_at"]
        
        count = repo.count_notifications(user_id=1, date_from=created_at, date_to=created_at)
        assert count == 1


class TestMarkAllRead:
    def test_marks_all_unread_as_read(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=1, notif_type="rating", message="m2")
        repo.create(user_id=1, notif_type="solve", message="m3")

        count = repo.mark_all_read(user_id=1)
        assert count == 3

        assert len(repo.get_unread(user_id=1)) == 0

    def test_mark_all_read_idempotent(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")

        repo.mark_all_read(user_id=1)
        count = repo.mark_all_read(user_id=1)
        assert count == 0

    def test_mark_read_user_isolated(self, repo):
        repo.create(user_id=1, notif_type="solve", message="m1")
        repo.create(user_id=2, notif_type="solve", message="m2")

        repo.mark_all_read(user_id=1)
        assert len(repo.get_unread(user_id=1)) == 0
        assert len(repo.get_unread(user_id=2)) == 1

    def test_mark_read_no_notifications(self, repo):
        count = repo.mark_all_read(user_id=999)
        assert count == 0
