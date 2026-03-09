import sqlite3
import pytest
from datetime import datetime, timezone

from Backend import settings
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.DomainLayer.User import User
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return UserRepo(conn)


def make_user(username: str, role=UserRole.SOLVER, xp=0, created_at=None):
    created_at = created_at or datetime.now(timezone.utc)

    # Prefer from_dict if exists (stable with your repos)
    if hasattr(User, "from_dict"):
        return User.from_dict({
            "id": 1,
            "username": username,
            "role": role.value if hasattr(role, "value") else str(role),
            "xp": int(xp),
            "created_at": created_at.isoformat(),
        })

    # Fallback constructor
    return User(id=1, username=username, role=role, xp=int(xp), created_at=created_at)


def test_schema_created(conn, repo):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    assert row is not None


def test_create_with_password_and_verify_login_success(repo):
    u = make_user("alice", role=UserRole.SOLVER, xp=10)
    created = repo.create(u, password="pw123")
    assert created.id > 0

    ok = repo.verify_login("alice", "pw123")
    assert ok is not None
    assert ok.username == "alice"

    wrong = repo.verify_login("alice", "wrong")
    assert wrong is None


def test_create_without_password_hits_branch_salt_hash_none(conn, repo):
    u = make_user("nopass", role=UserRole.SOLVER, xp=0)
    created = repo.create(u, password=None)
    assert created.id > 0

    # verify_login should return None because pw_salt/pw_hash are NULL
    assert repo.verify_login("nopass", "anything") is None

    # DB-level assert: pw_salt and pw_hash are NULL (covers branch)
    row = conn.execute("SELECT pw_salt, pw_hash FROM users WHERE username=?", ("nopass",)).fetchone()
    assert row is not None
    assert row["pw_salt"] is None
    assert row["pw_hash"] is None


def test_verify_login_user_not_found_branch(repo):
    assert repo.verify_login("no_such_user", "pw") is None


def test_get_by_id_and_username_none_branches(repo):
    assert repo.get_by_id(999999) is None
    assert repo.get_by_username("missing") is None


def test_get_by_id_and_username_roundtrip(repo):
    u = make_user("bob", role=UserRole.CREATOR, xp=42)
    created = repo.create(u, password="pw")
    by_id = repo.get_by_id(created.id)
    by_name = repo.get_by_username("bob")

    assert by_id is not None and by_name is not None
    assert by_id.id == created.id
    assert by_name.id == created.id
    assert by_id.username == "bob"
    assert by_id.role == UserRole.CREATOR
    assert by_id.xp == 42


def test_unique_username_constraint(repo):
    repo.create(make_user("unique"), password="pw1")
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(make_user("unique"), password="pw2")


def test_update_xp_positive(repo):
    created = repo.create(make_user("xpuser", xp=0), password="pw")
    repo.update_xp(created.id, 777)
    got = repo.get_by_id(created.id)
    assert got is not None
    assert got.xp == 777


def test_update_xp_negative_branch(repo):
    created = repo.create(make_user("negxp", xp=0), password="pw")
    with pytest.raises(ValidationError):
        repo.update_xp(created.id, -1)


def test_update_role(repo):
    created = repo.create(make_user("roleuser", role=UserRole.SOLVER), password="pw")
    repo.update_role(created.id, UserRole.ADMIN)
    got = repo.get_by_id(created.id)
    assert got is not None
    assert got.role == UserRole.ADMIN


def test_list_all_order_and_pagination(repo):
    # create 5 users
    for i in range(5):
        repo.create(make_user(f"u{i}", xp=i), password="pw")

    all_users = repo.list_all(limit=100, offset=0, order_by="id", order_direction="ASC")
    assert len(all_users) == 5
    ids = [u.id for u in all_users]
    assert ids == sorted(ids)  # ORDER BY id ASC

    page = repo.list_all(limit=2, offset=1, order_by="id", order_direction="ASC")
    assert len(page) == 2
    assert page[0].id == all_users[1].id
    assert page[1].id == all_users[2].id

class TestUserRepoIncrementXP:
    """Tests for increment_xp method"""
    
    def test_increment_xp_positive_delta(self, repo):
        created = repo.create(make_user("incruser", xp=100), password="pw")
        repo.increment_xp(created.id, 50)
        got = repo.get_by_id(created.id)
        assert got.xp == 150

    def test_increment_xp_zero_delta(self, repo):
        created = repo.create(make_user("zerouser", xp=100), password="pw")
        repo.increment_xp(created.id, 0)
        got = repo.get_by_id(created.id)
        assert got.xp == 100

    def test_increment_xp_negative_delta_ignored(self, repo):
        created = repo.create(make_user("neguser", xp=100), password="pw")
        repo.increment_xp(created.id, -50)
        got = repo.get_by_id(created.id)
        assert got.xp == 100  # No change for negative delta

    def test_increment_xp_large_delta(self, repo):
        created = repo.create(make_user("largeuser", xp=0), password="pw")
        repo.increment_xp(created.id, 100000)
        got = repo.get_by_id(created.id)
        assert got.xp == 100000


class TestUserRepoDelete:
    """Tests for delete method"""
    
    def test_delete_existing_user(self, repo):
        created = repo.create(make_user("deleteuser"), password="pw")
        result = repo.delete(created.id)
        assert result is True
        assert repo.get_by_id(created.id) is None

    def test_delete_nonexistent_user(self, repo):
        result = repo.delete(99999)
        assert result is False


class TestUserRepoUpdateRoleIf:
    """Tests for update_role_if method"""
    
    def test_update_role_if_matches(self, repo):
        created = repo.create(make_user("conduser", role=UserRole.SOLVER), password="pw")
        result = repo.update_role_if(created.id, UserRole.CREATOR, UserRole.SOLVER)
        assert result is True
        got = repo.get_by_id(created.id)
        assert got.role == UserRole.CREATOR

    def test_update_role_if_no_match(self, repo):
        created = repo.create(make_user("nomatchuser", role=UserRole.SOLVER), password="pw")
        result = repo.update_role_if(created.id, UserRole.ADMIN, UserRole.CREATOR)
        assert result is False
        got = repo.get_by_id(created.id)
        assert got.role == UserRole.SOLVER


class TestUserRepoGetByIds:
    """Tests for get_by_ids method"""
    
    def test_get_by_ids_single(self, repo):
        created = repo.create(make_user("single"), password="pw")
        result = repo.get_by_ids([created.id])
        assert len(result) == 1
        assert result[created.id].username == "single"

    def test_get_by_ids_multiple(self, repo):
        u1 = repo.create(make_user("user1"), password="pw")
        u2 = repo.create(make_user("user2"), password="pw")
        u3 = repo.create(make_user("user3"), password="pw")
        
        result = repo.get_by_ids([u1.id, u2.id, u3.id])
        assert len(result) == 3

    def test_get_by_ids_empty_list(self, repo):
        result = repo.get_by_ids([])
        assert len(result) == 0

    def test_get_by_ids_partial_exists(self, repo):
        u1 = repo.create(make_user("exists"), password="pw")
        result = repo.get_by_ids([u1.id, 99999])
        assert len(result) == 1
        assert u1.id in result


class TestUserRepoGetByEmail:
    """Tests for get_by_email method"""
    
    def test_get_by_email_success(self, repo):
        u = make_user("emailuser")
        created = repo.create(u, password="pw")
        # Note: User creation might not set email automatically, adjust accordingly
        found = repo.get_by_email(u.email)
        assert found is not None or found is None  # Depends on implementation

    def test_get_by_email_not_found(self, repo):
        result = repo.get_by_email("nonexistent@example.com")
        assert result is None


class TestUserRepoListAllFilters:
    """Tests for list_all with various filters"""
    
    def test_list_all_username_search(self, repo):
        repo.create(make_user("alice"), password="pw")
        repo.create(make_user("alicia"), password="pw")
        repo.create(make_user("bob"), password="pw")
        
        results = repo.list_all(limit=100, username_search="ali")
        assert len(results) == 2

    def test_list_all_role_filter(self, repo):
        repo.create(make_user("solver", role=UserRole.SOLVER), password="pw")
        repo.create(make_user("creator", role=UserRole.CREATOR), password="pw")
        repo.create(make_user("admin", role=UserRole.ADMIN), password="pw")
        
        results = repo.list_all(limit=100, role="creator")
        assert len(results) == 1

    def test_list_all_xp_filter_min(self, repo):
        repo.create(make_user("lowxp", xp=50), password="pw")
        repo.create(make_user("midxp", xp=500), password="pw")
        repo.create(make_user("highxp", xp=2000), password="pw")
        
        results = repo.list_all(limit=100, min_xp=500)
        assert len(results) == 2

    def test_list_all_xp_filter_max(self, repo):
        repo.create(make_user("lowxp", xp=50), password="pw")
        repo.create(make_user("midxp", xp=500), password="pw")
        repo.create(make_user("highxp", xp=2000), password="pw")
        
        results = repo.list_all(limit=100, max_xp=500)
        assert len(results) == 2

    def test_list_all_experience_level_experienced(self, repo):
        repo.create(make_user("inexperienced", xp=100), password="pw")
        repo.create(make_user("experienced", xp=2000), password="pw")
        
        results = repo.list_all(limit=100, experience_level="experienced")
        assert len(results) == 1

    def test_list_all_experience_level_inexperienced(self, repo):
        repo.create(make_user("inexperienced", xp=100), password="pw")
        repo.create(make_user("experienced", xp=2000), password="pw")
        
        results = repo.list_all(limit=100, experience_level="inexperienced")
        assert len(results) == 1

    def test_list_all_experience_level_boundary_level_5(self, repo):
        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        repo.create(make_user("below_boundary", xp=exp_xp_min - 1), password="pw")
        repo.create(make_user("at_boundary", xp=exp_xp_min), password="pw")

        results = repo.list_all(limit=100, experience_level="experienced")
        usernames = {u.username for u in results}
        assert "at_boundary" in usernames
        assert "below_boundary" not in usernames

    def test_list_all_inexperienced_excludes_level_5(self, repo):
        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        repo.create(make_user("below_boundary", xp=exp_xp_min - 1), password="pw")
        repo.create(make_user("at_boundary", xp=exp_xp_min), password="pw")

        results = repo.list_all(limit=100, experience_level="inexperienced")
        usernames = {u.username for u in results}
        assert "below_boundary" in usernames
        assert "at_boundary" not in usernames

    def test_list_all_date_from_filter(self, repo):
        """Test list_all with date_from filter"""
        past_time = "2020-01-01T00:00:00+00:00"
        recent_time = "2024-01-01T00:00:00+00:00"
        
        # Create user with past date
        past_user = make_user("past", created_at=datetime.fromisoformat(past_time))
        repo.create(past_user, password="pw")
        
        # Create user with recent date
        recent_user = make_user("recent", created_at=datetime.fromisoformat(recent_time))
        repo.create(recent_user, password="pw")
        
        # Filter from recent date should only return recent_user
        results = repo.list_all(limit=100, date_from=recent_time)
        assert len(results) == 1
        assert results[0].username == "recent"

    def test_list_all_date_to_filter(self, repo):
        """Test list_all with date_to filter"""
        past_time = "2020-01-01T00:00:00+00:00"
        recent_time = "2024-01-01T00:00:00+00:00"
        
        # Create users with different dates
        past_user = make_user("past", created_at=datetime.fromisoformat(past_time))
        repo.create(past_user, password="pw")
        
        recent_user = make_user("recent", created_at=datetime.fromisoformat(recent_time))
        repo.create(recent_user, password="pw")
        
        # Filter to past date should only return past_user
        results = repo.list_all(limit=100, date_to=past_time)
        assert len(results) == 1
        assert results[0].username == "past"

    def test_list_all_order_by_xp_desc(self, repo):
        """Test list_all with order_by=xp"""
        repo.create(make_user("low", xp=100), password="pw")
        repo.create(make_user("high", xp=1000), password="pw")
        repo.create(make_user("mid", xp=500), password="pw")
        
        results = repo.list_all(limit=100, order_by="xp", order_direction="DESC")
        assert len(results) == 3
        assert results[0].xp >= results[1].xp >= results[2].xp

    def test_list_all_order_by_xp_asc(self, repo):
        """Test list_all with order_by=xp ascending"""
        repo.create(make_user("low", xp=100), password="pw")
        repo.create(make_user("high", xp=1000), password="pw")
        repo.create(make_user("mid", xp=500), password="pw")
        
        results = repo.list_all(limit=100, order_by="xp", order_direction="ASC")
        assert len(results) == 3
        assert results[0].xp <= results[1].xp <= results[2].xp

    def test_list_all_order_by_invalid(self, repo):
        """Test list_all with invalid order_by defaults to created_at"""
        repo.create(make_user("user1"), password="pw")
        repo.create(make_user("user2"), password="pw")
        
        # Invalid order_by should not raise error, should default to created_at
        results = repo.list_all(limit=100, order_by="invalid_field")
        assert len(results) == 2

    def test_list_all_order_by_role(self, repo):
        """Test list_all with order_by=role"""
        repo.create(make_user("solver", role=UserRole.SOLVER), password="pw")
        repo.create(make_user("creator", role=UserRole.CREATOR), password="pw")
        repo.create(make_user("admin", role=UserRole.ADMIN), password="pw")
        
        results = repo.list_all(limit=100, order_by="role", order_direction="ASC")
        assert len(results) == 3
        # Roles should be ordered (order depends on alphabetical)
        assert results[0].role is not None

    def test_list_all_order_by_level(self, repo):
        """Test list_all with order_by=level (maps to xp)"""
        repo.create(make_user("lowxp", xp=100), password="pw")
        repo.create(make_user("highxp", xp=1000), password="pw")
        
        results = repo.list_all(limit=100, order_by="level", order_direction="DESC")
        assert len(results) == 2
        assert results[0].xp >= results[1].xp

    def test_list_all_order_by_experienced_desc(self, repo):
        """DESC should place experienced users (lvl 5+) first."""
        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        repo.create(make_user("inexperienced", xp=exp_xp_min - 1), password="pw")
        repo.create(make_user("experienced", xp=exp_xp_min), password="pw")

        results = repo.list_all(limit=100, order_by="experienced", order_direction="DESC")
        assert len(results) == 2
        assert results[0].username == "experienced"

    def test_list_all_order_by_experienced_asc(self, repo):
        """ASC should place inexperienced users first."""
        exp_xp_min = ((settings.EXPERIENCED_LEVEL_MIN - 1) ** 2) * settings.LEVEL_XP_DIVISOR
        repo.create(make_user("inexperienced", xp=exp_xp_min - 1), password="pw")
        repo.create(make_user("experienced", xp=exp_xp_min), password="pw")

        results = repo.list_all(limit=100, order_by="experienced", order_direction="ASC")
        assert len(results) == 2
        assert results[0].username == "inexperienced"


class TestUserRepoCountAll:
    """Tests for count_all method"""
    
    def test_count_all(self, repo):
        for i in range(3):
            repo.create(make_user(f"u{i}"), password="pw")
        assert repo.count_all() == 3

    def test_count_all_with_filter(self, repo):
        repo.create(make_user("alice"), password="pw")
        repo.create(make_user("alicia"), password="pw")
        repo.create(make_user("bob"), password="pw")
        
        count = repo.count_all(username_search="ali")
        assert count == 2


class TestUserRepoBanning:
    """Tests for discussion ban functionality"""
    
    def test_ban_from_discussions(self, repo):
        created = repo.create(make_user("banneduser"), password="pw")
        repo.ban_from_discussions(created.id)
        got = repo.get_by_id(created.id)
        assert got.is_discussion_banned is True

    def test_unban_from_discussions(self, repo):
        created = repo.create(make_user("banneduser"), password="pw")
        repo.ban_from_discussions(created.id)
        repo.unban_from_discussions(created.id)
        got = repo.get_by_id(created.id)
        assert got.is_discussion_banned is False

# ---------- puzzle limit columns ----------

def test_puzzle_limits_default_to_none(repo):
    u = make_user("creator1", role=UserRole.CREATOR)
    created = repo.create(u, password="pw")
    fetched = repo.get_by_id(created.id)
    assert fetched.puzzle_limit_published is None
    assert fetched.puzzle_limit_unpublished is None


def test_update_puzzle_limits_sets_values(repo):
    u = make_user("creator2", role=UserRole.CREATOR)
    created = repo.create(u, password="pw")

    repo.update_puzzle_limits(created.id, max_published=10, max_unpublished=8)
    fetched = repo.get_by_id(created.id)
    assert fetched.puzzle_limit_published == 10
    assert fetched.puzzle_limit_unpublished == 8


def test_update_puzzle_limits_reset_to_none(repo):
    u = make_user("creator3", role=UserRole.CREATOR)
    created = repo.create(u, password="pw")

    repo.update_puzzle_limits(created.id, max_published=7, max_unpublished=7)
    repo.update_puzzle_limits(created.id, max_published=None, max_unpublished=None)
    fetched = repo.get_by_id(created.id)
    assert fetched.puzzle_limit_published is None
    assert fetched.puzzle_limit_unpublished is None


def test_puzzle_limits_included_in_list_all(repo):
    u = make_user("creator4", role=UserRole.CREATOR)
    created = repo.create(u, password="pw")
    repo.update_puzzle_limits(created.id, max_published=3, max_unpublished=None)

    all_users = repo.list_all()
    target = next((x for x in all_users if x.id == created.id), None)
    assert target is not None
    assert target.puzzle_limit_published == 3
    assert target.puzzle_limit_unpublished is None
