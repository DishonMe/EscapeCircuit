import sqlite3
import pytest
from datetime import datetime, timezone

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

    all_users = repo.list_all(limit=100, offset=0)
    assert len(all_users) == 5
    ids = [u.id for u in all_users]
    assert ids == sorted(ids)  # ORDER BY id ASC

    page = repo.list_all(limit=2, offset=1)
    assert len(page) == 2
    assert page[0].id == all_users[1].id
    assert page[1].id == all_users[2].id


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
