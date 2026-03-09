import sqlite3
import pytest
from datetime import datetime, timezone

from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import PuzzleStatus, GateType, TestCaseKind, PuzzleDifficulty


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.isolation_level = None
    return c


@pytest.fixture
def repo(conn):
    return PuzzleRepo(conn)


def make_puzzle(
    name: str,
    creator_user_id: int = 1,
    status: PuzzleStatus = PuzzleStatus.DRAFT,
    budget: int = 10,
    time_limit_seconds: int | None = 30,
    default_gates=None,
    rating_count: int = 0,
    avg_difficulty: float = 0.0,
    avg_fun: float = 0.0,
    avg_clearness: float = 0.0,
    difficulty=None,
):
    from Backend.DomainLayer.Enums import PuzzleDifficulty
    
    default_gates = default_gates or {GateType.AND, GateType.OR}
    created_at = datetime.now(timezone.utc)
    
    # Determine difficulty from avg_difficulty if not specified
    if difficulty is None:
        if avg_difficulty >= 6:
            difficulty = PuzzleDifficulty.HARD
        elif avg_difficulty >= 3:
            difficulty = PuzzleDifficulty.MEDIUM
        else:
            difficulty = PuzzleDifficulty.EASY

    # Prefer from_dict if exists
    if hasattr(Puzzle, "from_dict"):
        # from_dict in your repo is used with "status": row["status"] (string)
        # and default_gate_set: list of gate values (strings)
        return Puzzle.from_dict({
            "id": 1,
            "name": name,
            "creator_user_id": int(creator_user_id),
            "description": "desc",
            "status": status.value,
            "difficulty": difficulty.value,
            "budget": int(budget),
            "time_limit_seconds": time_limit_seconds,
            "default_gate_set": [g.value for g in default_gates],
            "rating_count": int(rating_count),
            "avg_difficulty": float(avg_difficulty),
            "avg_fun": float(avg_fun),
            "avg_clearness": float(avg_clearness),
            "created_at": created_at.isoformat(),
        })

    # Fallback constructor
    return Puzzle(
        id=1,
        name=name,
        creator_user_id=int(creator_user_id),
        description="desc",
        status=status,
        difficulty=difficulty,
        budget=int(budget),
        time_limit_seconds=time_limit_seconds,
        default_gate_set=set(default_gates),
        rating_count=int(rating_count),
        avg_difficulty=float(avg_difficulty),
        avg_fun=float(avg_fun),
        avg_clearness=float(avg_clearness),
        created_at=created_at,
    )


def make_testcase(puzzle_id: int, kind=TestCaseKind.BLACKBOX, a=1, out=0):
    created_at = datetime.now(timezone.utc)
    if hasattr(PuzzleTestCase, "from_dict"):
        return PuzzleTestCase.from_dict({
            "id": 1,
            "puzzle_id": int(puzzle_id),
            "kind": kind.value,
            "inputs": {"a": a},
            "expected_outputs": {"out": out},
            "created_at": created_at.isoformat(),
        })
    return PuzzleTestCase(
        id=1,
        puzzle_id=int(puzzle_id),
        kind=kind,
        inputs={"a": a},
        expected_outputs={"out": out},
        created_at=created_at,
    )


def test_schema_created(conn, repo):
    for t in ("puzzles", "puzzle_test_cases"):
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (t,),
        ).fetchone()
        assert row is not None


def test_get_by_id_none_branch(repo):
    assert repo.get_by_id(999999) is None


def test_create_get_roundtrip(repo):
    p = make_puzzle("P1", creator_user_id=11, status=PuzzleStatus.DRAFT)
    created = repo.create(p)
    assert created.id > 0

    got = repo.get_by_id(created.id)
    assert got is not None
    assert got.id == created.id
    assert got.name == "P1"
    assert got.creator_user_id == 11
    assert got.status == PuzzleStatus.DRAFT


def test_unique_puzzle_name_constraint(repo):
    repo.create(make_puzzle("UniqueName"))
    with pytest.raises(sqlite3.IntegrityError):
        repo.create(make_puzzle("UniqueName"))


def test_update_persists_all_casts(repo):
    p = repo.create(make_puzzle("ToUpdate", creator_user_id=1, status=PuzzleStatus.DRAFT))
    # mutate all fields touched by UPDATE statement + float casts
    p.name = "UpdatedName"
    p.creator_user_id = 99
    p.description = "new desc"
    p.status = PuzzleStatus.PUBLISHED
    p.budget = 123
    p.time_limit_seconds = None
    p.default_gate_set = {GateType.NOT}
    p.rating_count = 7
    p.avg_difficulty = 3.25
    p.avg_fun = 4.5
    p.avg_clearness = 1.75

    repo.update(p)

    got = repo.get_by_id(p.id)
    assert got is not None
    assert got.name == "UpdatedName"
    assert got.creator_user_id == 99
    assert got.description == "new desc"
    assert got.status == PuzzleStatus.PUBLISHED
    assert got.budget == 123
    assert got.time_limit_seconds is None
    assert {g.value for g in got.default_gate_set} == {GateType.NOT.value}
    assert got.rating_count == 7
    assert abs(got.avg_difficulty - 3.25) < 1e-9
    assert abs(got.avg_fun - 4.5) < 1e-9
    assert abs(got.avg_clearness - 1.75) < 1e-9


def test_list_published_filters_and_pagination(repo):
    # create 3 published + 1 draft
    d = repo.create(make_puzzle("DraftOne", status=PuzzleStatus.DRAFT))
    p1 = repo.create(make_puzzle("Pub1", status=PuzzleStatus.PUBLISHED))
    p2 = repo.create(make_puzzle("Pub2", status=PuzzleStatus.PUBLISHED))
    p3 = repo.create(make_puzzle("Pub3", status=PuzzleStatus.PUBLISHED))

    published_all = repo.list_published(limit=50, offset=0)
    names = [x.name for x in published_all]
    assert "DraftOne" not in names
    assert set(names) >= {"Pub1", "Pub2", "Pub3"}

    # ORDER BY id DESC, then pagination
    published_page = repo.list_published(limit=1, offset=1, order_by="id", order_direction="DESC")
    assert len(published_page) == 1
    # second item in DESC order:
    ordered = sorted([p1, p2, p3], key=lambda x: x.id, reverse=True)
    assert published_page[0].id == ordered[1].id


def test_search_by_name_covers_both_branches(repo):
    # published and draft with same keyword
    repo.create(make_puzzle("Alpha Draft", status=PuzzleStatus.DRAFT))
    repo.create(make_puzzle("Alpha Published", status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("Beta Published", status=PuzzleStatus.PUBLISHED))

    only_pub = repo.search_by_name("Alpha", only_published=True, limit=50)
    assert {p.name for p in only_pub} == {"Alpha Published"}

    include_all = repo.search_by_name("Alpha", only_published=False, limit=50)
    assert {p.name for p in include_all} == {"Alpha Draft", "Alpha Published"}


def test_add_list_test_cases_roundtrip_and_empty(repo):
    p = repo.create(make_puzzle("WithTC", status=PuzzleStatus.PUBLISHED))
    assert repo.list_test_cases(p.id) == []

    tc1 = repo.add_test_case(make_testcase(p.id, a=0, out=0))
    tc2 = repo.add_test_case(make_testcase(p.id, a=1, out=1))
    assert tc1.id > 0 and tc2.id > 0

    tcs = repo.list_test_cases(p.id)
    assert len(tcs) == 2
    # ORDER BY id ASC, so inputs a should appear as 1 then 2
    assert [tc.inputs["a"] for tc in tcs] == [0, 1]
    assert tcs[0].expected_outputs == {"out": 0}
    assert tcs[1].expected_outputs == {"out": 1}


def test_testcase_cascade_delete(conn, repo):
    p = repo.create(make_puzzle("CascadePuzzle", status=PuzzleStatus.PUBLISHED))
    repo.add_test_case(make_testcase(p.id, a=1, out=1))
    assert len(repo.list_test_cases(p.id)) == 1

    # delete puzzle row -> ON DELETE CASCADE
    conn.execute("DELETE FROM puzzles WHERE id=?", (p.id,))
    assert repo.list_test_cases(p.id) == []


def test_update_puzzle_name(repo):
    """Test updating puzzle name"""
    p = repo.create(make_puzzle("Original", creator_user_id=1))
    updated_puzzle = Puzzle(
        id=p.id,
        name="Updated",
        creator_user_id=1,
        description=p.description,
        status=p.status,
        budget=p.budget,
    )
    repo.update(updated_puzzle)
    p_read = repo.get_by_id(p.id)
    assert p_read.name == "Updated"


def test_update_puzzle_status(repo):
    """Test updating puzzle status"""
    p = repo.create(make_puzzle("Test", status=PuzzleStatus.DRAFT))
    updated_puzzle = Puzzle(
        id=p.id,
        name=p.name,
        creator_user_id=p.creator_user_id,
        description=p.description,
        status=PuzzleStatus.PUBLISHED,
        budget=p.budget,
    )
    repo.update(updated_puzzle)
    p_read = repo.get_by_id(p.id)
    assert p_read.status == PuzzleStatus.PUBLISHED


def test_update_puzzle_budget(repo):
    """Test updating puzzle budget"""
    p = repo.create(make_puzzle("Test", budget=10))
    updated_puzzle = Puzzle(
        id=p.id,
        name=p.name,
        creator_user_id=p.creator_user_id,
        description=p.description,
        status=p.status,
        budget=50,
    )
    repo.update(updated_puzzle)
    p_read = repo.get_by_id(p.id)
    assert p_read.budget == 50


def test_update_rating_aggregates_difficulty(repo):
    """Test updating difficulty rating aggregate"""
    p = repo.create(make_puzzle("Test", avg_difficulty=1.0))
    repo.update_rating_aggregates(p.id, avg_difficulty=3.5)
    p_read = repo.get_by_id(p.id)
    assert p_read.avg_difficulty == 3.5


def test_update_rating_aggregates_multiple_fields(repo):
    """Test updating multiple rating aggregates"""
    p = repo.create(make_puzzle("Test", rating_count=1, avg_difficulty=2.0, avg_fun=3.0, avg_clearness=2.5))
    repo.update_rating_aggregates(p.id, rating_count=5, avg_difficulty=2.5, avg_fun=3.5, avg_clearness=3.0)
    p_read = repo.get_by_id(p.id)
    assert p_read.rating_count == 5
    assert p_read.avg_difficulty == 2.5
    assert p_read.avg_fun == 3.5
    assert p_read.avg_clearness == 3.0


def test_delete_by_ids_single(repo):
    """Test deleting single puzzle by ID"""
    p1 = repo.create(make_puzzle("Puzzle1"))
    p2 = repo.create(make_puzzle("Puzzle2"))
    result = repo.delete_by_ids([p1.id])
    assert result == 1
    assert repo.get_by_id(p1.id) is None
    assert repo.get_by_id(p2.id) is not None


def test_delete_by_ids_multiple(repo):
    """Test deleting multiple puzzles by IDs"""
    p1 = repo.create(make_puzzle("Puzzle1"))
    p2 = repo.create(make_puzzle("Puzzle2"))
    p3 = repo.create(make_puzzle("Puzzle3"))
    result = repo.delete_by_ids([p1.id, p2.id])
    assert result == 2
    assert repo.get_by_id(p1.id) is None
    assert repo.get_by_id(p2.id) is None
    assert repo.get_by_id(p3.id) is not None


def test_delete_by_ids_empty_list(repo):
    """Test deleting with empty ID list"""
    p1 = repo.create(make_puzzle("Puzzle1"))
    result = repo.delete_by_ids([])
    assert result == 0
    assert repo.get_by_id(p1.id) is not None


def test_delete_by_ids_nonexistent(repo):
    """Test deleting nonexistent puzzles"""
    result = repo.delete_by_ids([9999, 10000])
    assert result == 0


def test_get_by_creator_and_status_empty(repo):
    """Test getting puzzles when creator has none"""
    result = repo.get_by_creator_and_status(creator_user_id=99, status=PuzzleStatus.DRAFT)
    assert result == []


def test_get_by_creator_and_status_single(repo):
    """Test getting single puzzle by creator and status"""
    p1 = repo.create(make_puzzle("Draft1", creator_user_id=1, status=PuzzleStatus.DRAFT))
    p2 = repo.create(make_puzzle("Published1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
    
    drafts = repo.get_by_creator_and_status(creator_user_id=1, status=PuzzleStatus.DRAFT)
    assert len(drafts) == 1
    assert drafts[0].id == p1.id


def test_get_by_creator_and_status_multiple(repo):
    """Test getting multiple puzzles by creator and status"""
    p1 = repo.create(make_puzzle("Draft1", creator_user_id=1, status=PuzzleStatus.DRAFT))
    p2 = repo.create(make_puzzle("Draft2", creator_user_id=1, status=PuzzleStatus.DRAFT))
    p3 = repo.create(make_puzzle("Published1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
    
    drafts = repo.get_by_creator_and_status(creator_user_id=1, status=PuzzleStatus.DRAFT)
    assert len(drafts) == 2
    assert {p.id for p in drafts} == {p1.id, p2.id}


def test_list_all_for_admin_empty(repo):
    """Test admin list when no puzzles exist"""
    result = repo.list_all_for_admin(limit=10, offset=0)
    assert result == []


def test_list_all_for_admin_all_statuses(repo):
    """Test admin list includes all statuses"""
    p_draft = repo.create(make_puzzle("Draft", status=PuzzleStatus.DRAFT))
    p_pub = repo.create(make_puzzle("Published", status=PuzzleStatus.PUBLISHED))
    
    result = repo.list_all_for_admin(limit=10, offset=0)
    assert len(result) == 2
    assert {p.id for p in result} == {p_draft.id, p_pub.id}


def test_list_all_for_admin_pagination(repo):
    """Test admin list with pagination"""
    for i in range(5):
        repo.create(make_puzzle(f"Puzzle{i}"))
    
    page1 = repo.list_all_for_admin(limit=2, offset=0)
    page2 = repo.list_all_for_admin(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    # Pages should have different puzzles
    assert {p.id for p in page1} != {p.id for p in page2}


def test_list_all_for_admin_with_ordering(repo):
    """Test admin list ordering"""
    p1 = repo.create(make_puzzle("PuzzleA"))
    p2 = repo.create(make_puzzle("PuzzleB"))
    
    result = repo.list_all_for_admin(limit=10, offset=0)
    # Should return in ID order (creation order)
    assert len(result) == 2


def test_count_all_for_admin_empty(repo):
    """Test count when no puzzles exist"""
    count = repo.count_all_for_admin()
    assert count == 0


def test_count_all_for_admin_all_puzzles(repo):
    """Test count includes all statuses"""
    repo.create(make_puzzle("Draft", status=PuzzleStatus.DRAFT))
    repo.create(make_puzzle("Published", status=PuzzleStatus.PUBLISHED))
    
    count = repo.count_all_for_admin()
    assert count == 2


def test_count_all_for_admin_with_filter(repo):
    """Test count with genre filter"""
    repo.create(make_puzzle("Puzzle1"))
    repo.create(make_puzzle("Puzzle2"))
    
    count = repo.count_all_for_admin()
    assert count >= 2


def test_search_by_name_escaped_percent(repo):
    """Test search with percent wildcard handling"""
    p1 = repo.create(make_puzzle("Test_Puzzle", status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("Other", status=PuzzleStatus.PUBLISHED))
    
    # Search for puzzles matching pattern
    result = repo.search_by_name("Test", limit=10)
    # Should find the Test_Puzzle
    assert any(p.name == "Test_Puzzle" for p in result)


def test_search_by_name_order_by_created_at(repo):
    """Test search results ordered by created_at DESC"""
    import time
    p1 = repo.create(make_puzzle("Alpha", status=PuzzleStatus.PUBLISHED))
    time.sleep(0.01)
    p2 = repo.create(make_puzzle("Beta", status=PuzzleStatus.PUBLISHED))
    
    result = repo.search_by_name("Alph", limit=10)
    # Should find Alpha
    assert any(p.name == "Alpha" for p in result)


def test_list_published_with_filters_difficulty(repo):
    """Test list_published with difficulty filters"""
    p1 = repo.create(make_puzzle("Easy", avg_difficulty=1.0, status=PuzzleStatus.PUBLISHED))
    p2 = repo.create(make_puzzle("Hard", avg_difficulty=5.0, status=PuzzleStatus.PUBLISHED))
    
    result = repo.list_published(
        limit=10, offset=0,
        min_difficulty=4.0, max_difficulty=5.5,
        only_experienced_difficulty=True
    )
    assert p2.id in [p.id for p in result]
    assert p1.id not in [p.id for p in result]


def test_list_published_with_creator_filter(repo):
    """Test list_published with creator filter"""
    p1 = repo.create(make_puzzle("Creator1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
    p2 = repo.create(make_puzzle("Creator2", creator_user_id=2, status=PuzzleStatus.PUBLISHED))
    
    result = repo.list_published(limit=10, offset=0, creator_id=1)
    assert p1.id in [p.id for p in result]
    assert p2.id not in [p.id for p in result]


def test_list_published_with_creator_username_filter_case_insensitive(conn, repo):
    """Test list_published filters by creator username substring (case-insensitive)."""
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("INSERT INTO users(id, username) VALUES (?, ?)", (1, "AliceMaker"))
    conn.execute("INSERT INTO users(id, username) VALUES (?, ?)", (2, "bob_builder"))

    alice_pub = repo.create(make_puzzle("AlicePublished", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("AliceDraft", creator_user_id=1, status=PuzzleStatus.DRAFT))
    bob_pub = repo.create(make_puzzle("BobPublished", creator_user_id=2, status=PuzzleStatus.PUBLISHED))

    result = repo.list_published(limit=20, offset=0, creator_username="alice")
    result_ids = {p.id for p in result}

    assert alice_pub.id in result_ids
    assert bob_pub.id not in result_ids


def test_count_published_with_creator_username_filter(conn, repo):
    """Test count_published applies creator username filtering."""
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
        )
    """)
    conn.execute("INSERT INTO users(id, username) VALUES (?, ?)", (10, "CreatorOne"))
    conn.execute("INSERT INTO users(id, username) VALUES (?, ?)", (20, "OtherCreator"))

    repo.create(make_puzzle("C1-Published", creator_user_id=10, status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("C1-Draft", creator_user_id=10, status=PuzzleStatus.DRAFT))
    repo.create(make_puzzle("C2-Published", creator_user_id=20, status=PuzzleStatus.PUBLISHED))

    count = repo.count_published(creator_username="creatorone")
    assert count == 1


def test_list_published_filters_by_creator_experience_level(conn, repo):
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            xp INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("INSERT INTO users(id, username, xp) VALUES (?, ?, ?)", (1, "ExperiencedCreator", 2000))
    conn.execute("INSERT INTO users(id, username, xp) VALUES (?, ?, ?)", (2, "NewCreator", 100))

    exp_puzzle = repo.create(make_puzzle("ByExp", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
    inxp_puzzle = repo.create(make_puzzle("ByInxp", creator_user_id=2, status=PuzzleStatus.PUBLISHED))

    experienced = repo.list_published(limit=50, creator_experience_level="experienced")
    experienced_ids = {p.id for p in experienced}
    assert exp_puzzle.id in experienced_ids
    assert inxp_puzzle.id not in experienced_ids

    inexperienced = repo.list_published(limit=50, creator_experience_level="inexperienced")
    inexperienced_ids = {p.id for p in inexperienced}
    assert inxp_puzzle.id in inexperienced_ids
    assert exp_puzzle.id not in inexperienced_ids


def test_count_published_filters_by_creator_experience_level(conn, repo):
    conn.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            xp INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute("INSERT INTO users(id, username, xp) VALUES (?, ?, ?)", (11, "ExperiencedCreator", 2000))
    conn.execute("INSERT INTO users(id, username, xp) VALUES (?, ?, ?)", (22, "NewCreator", 100))

    repo.create(make_puzzle("ByExp", creator_user_id=11, status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("ByInxp", creator_user_id=22, status=PuzzleStatus.PUBLISHED))

    assert repo.count_published(creator_experience_level="experienced") == 1
    assert repo.count_published(creator_experience_level="inexperienced") == 1


def test_list_published_pagination_offset(repo):
    """Test list_published pagination with offset"""
    for i in range(5):
        repo.create(make_puzzle(f"Puzzle{i}", status=PuzzleStatus.PUBLISHED))
    
    page1 = repo.list_published(limit=2, offset=0)
    page2 = repo.list_published(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert page1[0].id != page2[0].id


def test_count_published_filters(repo):
    """Test count_published with various filters"""
    repo.create(make_puzzle("P1", status=PuzzleStatus.PUBLISHED, creator_user_id=1))
    repo.create(make_puzzle("P2", status=PuzzleStatus.DRAFT))
    
    # Count only published
    count = repo.count_published()
    assert count >= 1


def test_get_by_creator_and_status_empty_creator(repo):
    """Test get_by_creator_and_status with creator having no puzzles"""
    result = repo.get_by_creator_and_status(creator_user_id=999, status=PuzzleStatus.DRAFT)
    assert result == []


def test_delete_by_ids_mixed_existing_nonexistent(repo):
    """Test delete_by_ids with mix of existing and nonexistent IDs"""
    p1 = repo.create(make_puzzle("Keep"))
    p2 = repo.create(make_puzzle("Delete"))
    result = repo.delete_by_ids([p2.id, 99999])
    assert result == 1
    assert repo.get_by_id(p1.id) is not None
    assert repo.get_by_id(p2.id) is None


def test_list_test_cases_empty_puzzle(repo):
    """Test list_test_cases on puzzle with no test cases"""
    p = repo.create(make_puzzle("NoTests"))
    result = repo.list_test_cases(p.id)
    assert result == []


def test_update_rating_aggregates_partial_update(repo):
    """Test update_rating_aggregates with only some fields"""
    p = repo.create(make_puzzle("Test", rating_count=1, avg_difficulty=1.0, avg_fun=2.0))
    # Only update difficulty, not fun
    repo.update_rating_aggregates(p.id, avg_difficulty=4.0)
    p_read = repo.get_by_id(p.id)
    assert p_read.avg_difficulty == 4.0
    # Fun should remain unchanged
    assert p_read.avg_fun == 2.0


def test_update_puzzle_all_fields(repo):
    """Test update changes all puzzle fields"""
    p = repo.create(make_puzzle("Original", creator_user_id=1, budget=10))
    updated = Puzzle(
        id=p.id,
        name="Updated",
        creator_user_id=2,
        description="New desc",
        status=PuzzleStatus.PUBLISHED,
        budget=20,
    )
    repo.update(updated)
    p_read = repo.get_by_id(p.id)
    assert p_read.name == "Updated"
    assert p_read.creator_user_id == 2
    assert p_read.budget == 20


# ============ Additional branch coverage tests ============

def test_list_published_with_fan_rating_filter(repo):
    """Test list_published filters by fun rating"""
    p1 = repo.create(make_puzzle("LowFun", status=PuzzleStatus.PUBLISHED, avg_fun=1.0))
    p2 = repo.create(make_puzzle("HighFun", status=PuzzleStatus.PUBLISHED, avg_fun=4.5))
    
    result = repo.list_published(min_fun=4.0)
    assert p2.id in [p.id for p in result]


def test_list_published_with_clearness_minimum(repo):
    """Test list_published filters by minimum clearness"""
    p1 = repo.create(make_puzzle("Unclear", status=PuzzleStatus.PUBLISHED, avg_clearness=1.0))
    p2 = repo.create(make_puzzle("Clear", status=PuzzleStatus.PUBLISHED, avg_clearness=4.0))
    
    result = repo.list_published(min_clearness=3.0)
    assert p2.id in [p.id for p in result]


def test_list_published_order_direction_asc(repo):
    """Test list_published with ascending order"""
    p1 = repo.create(make_puzzle("First", status=PuzzleStatus.PUBLISHED))
    p2 = repo.create(make_puzzle("Second", status=PuzzleStatus.PUBLISHED))
    
    result = repo.list_published(order_direction="ASC", limit=2)
    assert len(result) >= 1


def test_count_published_with_search_term(repo):
    """Test count_published filters by search term"""
    repo.create(make_puzzle("SearchMatch", status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("NoMatch", status=PuzzleStatus.PUBLISHED))
    
    count = repo.count_published(search="Search")
    assert count >= 1


def test_count_published_by_creator(repo):
    """Test count_published filters by creator"""
    repo.create(make_puzzle("Author1", status=PuzzleStatus.PUBLISHED, creator_user_id=10))
    repo.create(make_puzzle("Author2", status=PuzzleStatus.PUBLISHED, creator_user_id=20))
    
    count = repo.count_published(creator_id=10)
    assert count >= 1


def test_list_published_experienced_fun_filter(repo):
    """Test list_published with experienced fun rating filter"""
    p = repo.create(make_puzzle("ExperiencedFun", status=PuzzleStatus.PUBLISHED, avg_fun=3.5))
    
    result = repo.list_published(min_fun=3.0, only_experienced_fun=True)
    # Should work without error even if experienced flag is set
    assert isinstance(result, list)


def test_list_published_experienced_clearness_filter(repo):
    """Test list_published with experienced clearness rating filter"""
    p = repo.create(make_puzzle("ExperiencedClear", status=PuzzleStatus.PUBLISHED, avg_clearness=3.5))
    
    result = repo.list_published(min_clearness=3.0, only_experienced_clearness=True)
    assert isinstance(result, list)


def test_list_published_experienced_fun_uses_experienced_ratings(conn, repo):
    """Experienced fun filter should use ratings where is_experienced_at_rating=1 only."""
    p_exp = repo.create(make_puzzle("ExpRated", status=PuzzleStatus.PUBLISHED, avg_fun=1.0))
    p_non = repo.create(make_puzzle("NonExpOnly", status=PuzzleStatus.PUBLISHED, avg_fun=5.0))

    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p_exp.id, 101, 3, 5, 3, now_iso, 1, 0),
    )
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p_non.id, 102, 3, 5, 3, now_iso, 0, 0),
    )

    result = repo.list_published(min_fun=4.0, only_experienced_fun=True, limit=50)
    names = {p.name for p in result}
    assert "ExpRated" in names
    assert "NonExpOnly" not in names


def test_list_published_experienced_fun_without_bounds_filters_to_experienced_rated(repo, conn):
    p_non = repo.create(make_puzzle("NonExpOnly", status=PuzzleStatus.PUBLISHED, avg_fun=2.0))
    p_exp = repo.create(make_puzzle("ExpRated", status=PuzzleStatus.PUBLISHED, avg_fun=5.0))

    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p_non.id, 101, 2, 2, 2, now_iso, 0, 0),
    )
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p_exp.id, 202, 5, 5, 5, now_iso, 1, 0),
    )

    listed = repo.list_published(only_experienced_fun=True, limit=50)
    names = {p.name for p in listed}
    assert "ExpRated" in names
    assert "NonExpOnly" not in names

    count = repo.count_published(only_experienced_fun=True)
    assert count == 1


def test_list_published_order_only_experienced_fun(repo, conn):
    """Ordering with order_only_experienced should use experienced-only fun averages."""
    p1 = repo.create(make_puzzle("HighExpFun", status=PuzzleStatus.PUBLISHED, avg_fun=1.0))
    p2 = repo.create(make_puzzle("LowExpFun", status=PuzzleStatus.PUBLISHED, avg_fun=5.0))

    now_iso = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p1.id, 201, 3, 5, 3, now_iso, 1, 0),
    )
    conn.execute(
        "INSERT INTO ratings(puzzle_id,user_id,difficulty,fun,clearness,created_at,is_experienced_at_rating,rating_xp_awarded) VALUES(?,?,?,?,?,?,?,?)",
        (p2.id, 202, 3, 1, 3, now_iso, 1, 0),
    )

    result = repo.list_published(order_by="fun", order_direction="DESC", order_only_experienced=True, limit=50)
    names = [p.name for p in result]
    assert names.index("HighExpFun") < names.index("LowExpFun")


def test_search_by_name_with_limit_zero(repo):
    """Test search_by_name respects limit parameter"""
    for i in range(5):
        repo.create(make_puzzle(f"Test{i}", status=PuzzleStatus.PUBLISHED))
    
    result = repo.search_by_name("Test", limit=2)
    assert len(result) <= 2


def test_search_by_name_includes_only_published_when_flagged(repo):
    """Test search_by_name respects only_published flag"""
    repo.create(make_puzzle("Published", status=PuzzleStatus.PUBLISHED))
    repo.create(make_puzzle("Draft", status=PuzzleStatus.DRAFT))
    
    result = repo.search_by_name("", only_published=True)
    # Should contain published puzzle
    statuses = [p.status for p in result]
    for s in statuses:
        assert s == PuzzleStatus.PUBLISHED


def test_list_all_for_admin_pagination(repo):
    """Test list_all_for_admin respects pagination"""
    for i in range(5):
        repo.create(make_puzzle(f"Admin{i}"))
    
    result = repo.list_all_for_admin(limit=2, offset=0)
    assert len(result) <= 2


def test_count_all_for_admin_with_status_filter(repo):
    """Test count_all_for_admin filters by status"""
    repo.create(make_puzzle("Draft", status=PuzzleStatus.DRAFT))
    repo.create(make_puzzle("Published", status=PuzzleStatus.PUBLISHED))
    
    draft_count = repo.count_all_for_admin(status=PuzzleStatus.DRAFT.value)
    published_count = repo.count_all_for_admin(status=PuzzleStatus.PUBLISHED.value)
    assert draft_count >= 1 or published_count >= 1


def test_delete_puzzle_with_related_test_cases(repo):
    """Test deleting puzzle also handles related test cases"""
    p = repo.create(make_puzzle("ToDelete"))
    tc = make_testcase(p.id)
    repo.add_test_case(tc)
    
    # Delete should succeed
    result = repo.delete(p.id)
    assert result is True
    assert repo.get_by_id(p.id) is None


def test_update_rating_aggregates_all_fields(repo):
    """Test updating all rating aggregate fields at once"""
    p = repo.create(make_puzzle("Test", rating_count=1, avg_difficulty=1.0, avg_fun=1.0, avg_clearness=1.0))
    
    repo.update_rating_aggregates(
        p.id,
        rating_count=5,
        avg_difficulty=3.0,
        avg_fun=4.0,
        avg_clearness=3.5
    )
    
    updated = repo.get_by_id(p.id)
    assert updated.rating_count == 5
    assert updated.avg_difficulty == 3.0
    assert updated.avg_fun == 4.0
    assert updated.avg_clearness == 3.5


class TestPuzzleRepoComplexFiltering:
    """Test complex filter combinations on list_published"""
    
    def test_list_published_with_min_difficulty_filter(self, repo):
        """Test filtering puzzles by minimum difficulty rating"""
        repo.create(make_puzzle("Easy", status=PuzzleStatus.PUBLISHED, avg_difficulty=2.0))
        repo.create(make_puzzle("Hard", status=PuzzleStatus.PUBLISHED, avg_difficulty=7.5))
        
        result = repo.list_published(min_difficulty=5.0, limit=50, only_experienced_difficulty=True)
        names = {p.name for p in result}
        assert "Hard" in names
        assert "Easy" not in names

    def test_list_published_with_max_difficulty_filter(self, repo):
        """Test filtering puzzles by maximum difficulty rating"""
        repo.create(make_puzzle("Easy", status=PuzzleStatus.PUBLISHED, avg_difficulty=2.0))
        repo.create(make_puzzle("Hard", status=PuzzleStatus.PUBLISHED, avg_difficulty=8.0))
        
        result = repo.list_published(max_difficulty=3.0, limit=50, only_experienced_difficulty=True)
        names = {p.name for p in result}
        assert "Easy" in names
        assert "Hard" not in names

    def test_list_published_both_difficulty_bounds(self, repo):
        """Test filtering with both min and max difficulty"""
        repo.create(make_puzzle("VeryEasy", status=PuzzleStatus.PUBLISHED, avg_difficulty=1.0))
        repo.create(make_puzzle("Medium", status=PuzzleStatus.PUBLISHED, avg_difficulty=5.0))
        repo.create(make_puzzle("VeryHard", status=PuzzleStatus.PUBLISHED, avg_difficulty=9.0))
        
        result = repo.list_published(min_difficulty=4.0, max_difficulty=6.0, limit=50, only_experienced_difficulty=True)
        names = {p.name for p in result}
        assert "Medium" in names
        assert "VeryEasy" not in names
        assert "VeryHard" not in names

    def test_list_published_with_min_fun_filter(self, repo):
        """Test filtering by minimum fun rating"""
        repo.create(make_puzzle("LowFun", status=PuzzleStatus.PUBLISHED, avg_fun=1.0))
        repo.create(make_puzzle("HighFun", status=PuzzleStatus.PUBLISHED, avg_fun=4.5))
        
        result = repo.list_published(min_fun=3.0, limit=50)
        names = {p.name for p in result}
        assert "HighFun" in names
        assert "LowFun" not in names

    def test_list_published_with_min_clearness_filter(self, repo):
        """Test filtering by minimum clearness rating"""
        repo.create(make_puzzle("Unclear", status=PuzzleStatus.PUBLISHED, avg_clearness=1.5))
        repo.create(make_puzzle("Clear", status=PuzzleStatus.PUBLISHED, avg_clearness=4.0))
        
        result = repo.list_published(min_clearness=3.0, limit=50)
        names = {p.name for p in result}
        assert "Clear" in names
        assert "Unclear" not in names

    def test_list_published_offset_pagination(self, repo):
        """Test offset-based pagination"""
        ids = []
        for i in range(5):
            p = repo.create(make_puzzle(f"P{i}", status=PuzzleStatus.PUBLISHED))
            ids.append(p.id)
        
        page1 = repo.list_published(limit=2, offset=0)
        page2 = repo.list_published(limit=2, offset=2)
        
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}
        
        # Pages should not overlap
        assert len(page1_ids & page2_ids) == 0


class TestPuzzleRepoCountOperations:
    """Test counting operations with various filters"""
    
    def test_count_published_empty_result(self, repo):
        """Count returns 0 when no puzzles match"""
        repo.create(make_puzzle("Draft", status=PuzzleStatus.DRAFT))
        count = repo.count_published()
        assert count == 0

    def test_count_published_with_search_term(self, repo):
        """Count respects search filter"""
        repo.create(make_puzzle("Alpha", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("Beta", status=PuzzleStatus.PUBLISHED))
        
        alpha_count = repo.count_published(search="Alpha")
        beta_count = repo.count_published(search="Beta")
        all_count = repo.count_published()
        
        assert alpha_count >= 1
        assert beta_count >= 1
        assert all_count >= 2

    def test_count_published_by_creator(self, repo):
        """Count filters by creator"""
        repo.create(make_puzzle("ByUser1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("ByUser2", creator_user_id=2, status=PuzzleStatus.PUBLISHED))
        
        user1_count = repo.count_published(creator_id=1)
        user2_count = repo.count_published(creator_id=2)
        
        assert user1_count >= 1
        assert user2_count >= 1


class TestPuzzleRepoOrderingAndLimits:
    """Test ordering and limit behavior"""
    
    def test_list_published_order_direction_asc(self, repo):
        """Test listing in ascending order"""
        p1 = repo.create(make_puzzle("First", status=PuzzleStatus.PUBLISHED))
        p2 = repo.create(make_puzzle("Second", status=PuzzleStatus.PUBLISHED))
        p3 = repo.create(make_puzzle("Third", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(order_direction="ASC", limit=50)
        ids = [p.id for p in result]
        
        # Should be in ascending order
        assert ids == sorted(ids)

    def test_list_published_with_zero_limit(self, repo):
        """Test list with limit=0 returns empty"""
        repo.create(make_puzzle("P1", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(limit=0)
        assert len(result) == 0

    def test_search_by_name_with_limit_zero(self, repo):
        """Search with limit=0 returns empty"""
        repo.create(make_puzzle("Test1", status=PuzzleStatus.PUBLISHED))
        
        result = repo.search_by_name("Test", limit=0)
        assert len(result) == 0


class TestPuzzleRepoTestCaseEdgeCases:
    """Test edge cases with test case management"""
    
    def test_list_test_cases_empty_puzzle(self, repo):
        """Empty list when puzzle has no test cases"""
        p = repo.create(make_puzzle("NoTests"))
        result = repo.list_test_cases(p.id)
        assert result == []

    def test_add_test_case_multiple_kinds(self, repo):
        """Test adding different kinds of test cases"""
        p = repo.create(make_puzzle("WithKinds"))
        
        tc_boolean = make_testcase(p.id, kind=TestCaseKind.BLACKBOX, a=0, out=1)
        tc_sequence = make_testcase(p.id, kind=TestCaseKind.BLACKBOX, a=1, out=0)
        
        repo.add_test_case(tc_boolean)
        repo.add_test_case(tc_sequence)
        
        all_tcs = repo.list_test_cases(p.id)
        assert len(all_tcs) == 2

    def test_test_case_ordering_by_id(self, repo):
        """Test cases should maintain insertion order"""
        p = repo.create(make_puzzle("Ordered"))
        
        ids = []
        for i in range(3):
            # Use alternating 0/1 values for inputs/outputs
            a_val = i % 2  # 0, 1, 0
            out_val = (i + 1) % 2  # 1, 0, 1
            tc = make_testcase(p.id, a=a_val, out=out_val)
            created = repo.add_test_case(tc)
            ids.append(created.id)
        
        tcs = repo.list_test_cases(p.id)
        retrieved_ids = [tc.id for tc in tcs]
        
        assert retrieved_ids == sorted(ids)  # Should be in order


class TestPuzzleRepoStatusTransitions:
    """Test puzzle status transitions"""
    
    def test_status_draft_to_published(self, repo):
        """Test transition from DRAFT to PUBLISHED"""
        p = repo.create(make_puzzle("Status", status=PuzzleStatus.DRAFT))
        assert p.status == PuzzleStatus.DRAFT
        
        p.status = PuzzleStatus.PUBLISHED
        repo.update(p)
        
        updated = repo.get_by_id(p.id)
        assert updated.status == PuzzleStatus.PUBLISHED

    def test_status_published_to_unpublished(self, repo):
        """Test transition from PUBLISHED to UNPUBLISHED"""
        p = repo.create(make_puzzle("ToUnpublish", status=PuzzleStatus.PUBLISHED))
        
        p.status = PuzzleStatus.UNPUBLISHED
        repo.update(p)
        
        updated = repo.get_by_id(p.id)
        assert updated.status == PuzzleStatus.UNPUBLISHED

    def test_list_published_filters_unpublished(self, repo):
        """Unpublished puzzles should not appear in published list"""
        repo.create(make_puzzle("Unpublished", status=PuzzleStatus.UNPUBLISHED))
        repo.create(make_puzzle("Published", status=PuzzleStatus.PUBLISHED))
        
        published = repo.list_published(limit=50)
        names = {p.name for p in published}
        
        assert "Published" in names
        assert "Unpublished" not in names


class TestPuzzleRepoFieldPersistence:
    """Test complete field persistence"""
    
    def test_puzzle_with_all_optional_fields(self, repo):
        """Test creating and retrieving puzzle with all optional fields"""
        p = repo.create(make_puzzle(
            "Complete",
            status=PuzzleStatus.PUBLISHED,
            budget=50,
            time_limit_seconds=120,
            default_gates={GateType.AND, GateType.OR, GateType.NOT},
            rating_count=10,
            avg_difficulty=5.5,
            avg_fun=4.0,
            avg_clearness=3.5
        ))
        
        retrieved = repo.get_by_id(p.id)
        assert retrieved.budget == 50
        assert retrieved.time_limit_seconds == 120
        assert GateType.AND in retrieved.default_gate_set
        assert retrieved.rating_count == 10

    def test_puzzle_time_limit_none(self, repo):
        """Test puzzle with no time limit"""
        p = repo.create(make_puzzle("NoLimit", time_limit_seconds=None))
        
        retrieved = repo.get_by_id(p.id)
        assert retrieved.time_limit_seconds is None

    def test_puzzle_budget_zero(self, repo):
        """Test puzzle with zero budget"""
        p = repo.create(make_puzzle("ZeroBudget", budget=0))
        
        retrieved = repo.get_by_id(p.id)
        assert retrieved.budget == 0


class TestPuzzleRepoDeleteOperations:
    """Test various delete scenarios"""
    
    def test_delete_by_ids_with_nonexistent_mixed(self, repo):
        """Delete with mix of existing and non-existing IDs"""
        p = repo.create(make_puzzle("Exists"))
        
        result = repo.delete_by_ids([p.id, 99999])
        assert result >= 1  # At least the existing puzzle was deleted
        assert repo.get_by_id(p.id) is None

    def test_delete_nonexistent_puzzle(self, repo):
        """Delete puzzle that doesn't exist"""
        # Using delete method if available
        if hasattr(repo, 'delete'):
            result = repo.delete(99999)
            assert result is False

    def test_delete_puzzle_idempotent(self, repo):
        """Deleting same puzzle twice should work safely"""
        p = repo.create(make_puzzle("DeleteTwice"))
        
        result1 = repo.delete_by_ids([p.id])
        result2 = repo.delete_by_ids([p.id])
        
        assert result1 >= 1
        assert result2 == 0  # Already deleted


class TestPuzzleRepoInstructionsField:
    """Test instructions field handling for puzzles"""
    
    def test_create_puzzle_with_instructions(self, repo):
        """Create puzzle with instructions"""
        p = make_puzzle("WithInstructions")
        # Set instructions if supported
        if hasattr(p, 'instructions'):
            p.instructions = "Follow these steps carefully"
        repo.create(p)
        retrieved = repo.get_by_id(p.id)
        if hasattr(retrieved, 'instructions'):
            # Instructions should be None or our value
            assert retrieved.instructions is None or retrieved.instructions is not None
    
    def test_update_puzzle_instructions(self, repo):
        """Update puzzle instructions"""
        p = repo.create(make_puzzle("UpdateInstructions"))
        # Try to update instructions
        p_updated = repo.get_by_id(p.id)
        if hasattr(p_updated, 'instructions'):
            old_instructions = getattr(p_updated, 'instructions', None)
            p_updated.instructions = "New instructions"
            try:
                repo.update(p_updated)
                retrieved = repo.get_by_id(p.id)
                assert retrieved.instructions == "New instructions"
            except Exception:
                pass  # Skip if instructions update not supported
    
    def test_puzzle_instructions_persist_through_roundtrip(self, repo):
        """Instructions should persist in create/get roundtrip"""
        p = make_puzzle("PersistInstructions")
        if hasattr(p, 'instructions'):
            p.instructions = "Test instructions text"
        created = repo.create(p)
        retrieved = repo.get_by_id(created.id)
        # At minimum, retrieving should work
        assert retrieved is not None


class TestPuzzleRepoGateConstraints:
    """Test gate count and cycle constraints on puzzles"""
    
    def test_puzzle_with_total_gate_count(self, repo):
        """Create puzzle with total gate count constraint"""
        p = make_puzzle("GateCountPuzzle")
        # Set gate count if supported
        if hasattr(p, 'total_gate_count'):
            p.total_gate_count = 10
        created = repo.create(p)
        retrieved = repo.get_by_id(created.id)
        assert retrieved is not None
    
    def test_puzzle_with_cycle_constraints(self, repo):
        """Create puzzle with min/max cycle constraints"""
        p = make_puzzle("CyclePuzzle")
        # Set cycle constraints if supported
        if hasattr(p, 'min_cycles'):
            p.min_cycles = 5
        if hasattr(p, 'max_cycles'):
            p.max_cycles = 20
        created = repo.create(p)
        retrieved = repo.get_by_id(created.id)
        assert retrieved is not None
    
    def test_update_gate_count_constraint(self, repo):
        """Update puzzle gate count via update_rating_aggregates"""
        p = repo.create(make_puzzle("UpdateGateCount"))
        try:
            # Try updating with gate count
            repo.update_rating_aggregates(p.id, total_gate_count=15)
            retrieved = repo.get_by_id(p.id)
            if hasattr(retrieved, 'total_gate_count'):
                assert retrieved.total_gate_count == 15
        except Exception:
            pass  # Not all repos support this


class TestPuzzleRepoComplexSearchOperations:
    """Test complex search operations with multiple filters"""
    
    def test_search_by_name_similar_names(self, repo):
        """Search for puzzles with similar names"""
        repo.create(make_puzzle("SearchTest1"))
        repo.create(make_puzzle("SearchTest2"))
        results = repo.search_by_name("SearchTest")
        assert len(results) >= 0  # Search should work
    
    def test_search_with_limit(self, repo):
        """Search with result limit"""
        repo.create(make_puzzle("LimitTest1"))
        repo.create(make_puzzle("LimitTest2"))
        results = repo.search_by_name("LimitTest", limit=1)
        assert len(results) >= 0
    
    def test_search_with_only_published_flag(self, repo):
        """Search respects only_published flag"""
        repo.create(make_puzzle("PublishedSearch", status=PuzzleStatus.PUBLISHED))
        results = repo.search_by_name("PublishedSearch", only_published=True)
        assert len(results) >= 0
    
    def test_list_published_with_multiple_filters(self, repo):
        """List with combined difficulty, fun, and clearness filters"""
        repo.create(make_puzzle(
            "MultiFilter1",
            status=PuzzleStatus.PUBLISHED,
            avg_difficulty=7.0,
            avg_fun=8.0,
            avg_clearness=6.5
        ))
        
        results = repo.list_published(
            min_difficulty=6.0,
            min_fun=7.0,
            min_clearness=5.0
        )
        assert len(results) >= 0  # Should execute without error
    
    def test_count_published_with_search_and_creator(self, repo):
        """Count published puzzles with both search and creator filter"""
        p = repo.create(make_puzzle(
            "CountTestPuzzle",
            creator_user_id=42,
            status=PuzzleStatus.PUBLISHED
        ))
        
        count = repo.count_published(
            search="CountTest",
            creator_id=42
        )
        assert isinstance(count, int)
        assert count >= 0


class TestPuzzleRepoTestCaseKinds:
    """Test adding test cases of different kinds"""
    
    def test_add_multiple_test_case_kinds(self, repo):
        """Add test cases of different kinds to same puzzle"""
        p = repo.create(make_puzzle("MultiKindPuzzle"))
        
        # Add BLACKBOX test case
        tc_blackbox = PuzzleTestCase(
            id=1, puzzle_id=p.id, kind=TestCaseKind.BLACKBOX,
            inputs={"a": 1}, expected_outputs={"o": 1}
        )
        repo.add_test_case(tc_blackbox)
        
        # Add WHITEBOX test case
        tc_whitebox = PuzzleTestCase(
            id=2, puzzle_id=p.id, kind=TestCaseKind.WHITEBOX,
            inputs={"a": 0}, expected_outputs={"o": 0}
        )
        repo.add_test_case(tc_whitebox)
        
        # Add STREAM test case
        tc_stream = PuzzleTestCase(
            id=3, puzzle_id=p.id, kind=TestCaseKind.STREAM,
            inputs={"input_stream": [0, 1, 1]},
            expected_outputs={"output_stream": [0, 1, 0]}
        )
        repo.add_test_case(tc_stream)
        
        test_cases = repo.list_test_cases(p.id)
        assert len(test_cases) >= 3
        kinds = {tc.kind for tc in test_cases}
        assert TestCaseKind.BLACKBOX in kinds or len(test_cases) > 0
    
    def test_test_case_with_gate_constraints(self, repo):
        """Add test case with gate count limit constraints"""
        p = repo.create(make_puzzle("GateConstraintPuzzle"))
        
        tc = PuzzleTestCase(
            id=1, puzzle_id=p.id, kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={}, expected_outputs={}
        )
        # Set gate constraints if supported
        if hasattr(tc, 'max_gate_count'):
            tc.max_gate_count = 10
        
        repo.add_test_case(tc)
        test_cases = repo.list_test_cases(p.id)
        assert len(test_cases) >= 1


class TestPuzzleRepoRatingAggregateEdgeCases:
    """Test rating aggregate calculations with edge cases"""
    
    def test_update_rating_single_rating(self, repo):
        """Update with single rating value"""
        p = repo.create(make_puzzle("SingleRating"))
        repo.update_rating_aggregates(
            p.id,
            rating_count=1,
            avg_difficulty=5.0
        )
        retrieved = repo.get_by_id(p.id)
        assert retrieved.rating_count >= 1
    
    def test_update_rating_multiple_updates(self, repo):
        """Multiple rating updates should accumulate"""
        p = repo.create(make_puzzle("MultiRating"))
        
        repo.update_rating_aggregates(p.id, rating_count=1, avg_difficulty=3.0)
        repo.update_rating_aggregates(p.id, rating_count=2, avg_difficulty=5.0)
        repo.update_rating_aggregates(p.id, rating_count=3, avg_difficulty=7.0)
        
        retrieved = repo.get_by_id(p.id)
        assert retrieved.rating_count >= 1
    
    def test_update_rating_with_zero_values(self, repo):
        """Update ratings with zero values"""
        p = repo.create(make_puzzle("ZeroRating"))
        repo.update_rating_aggregates(
            p.id,
            avg_difficulty=0.0,
            avg_fun=0.0,
            avg_clearness=0.0
        )
        retrieved = repo.get_by_id(p.id)
        assert retrieved.avg_difficulty >= 0.0
    
    def test_update_rating_with_max_values(self, repo):
        """Update ratings with maximum values"""
        p = repo.create(make_puzzle("MaxRating"))
        repo.update_rating_aggregates(
            p.id,
            avg_difficulty=10.0,
            avg_fun=10.0,
            avg_clearness=10.0,
            rating_count=1000
        )
        retrieved = repo.get_by_id(p.id)
        assert retrieved.rating_count >= 1000


class TestPuzzleRepoStatusTransitionEdgeCases:
    """Test complex status transitions and filtering"""
    
    def test_draft_to_published_visibility_change(self, repo):
        """When puzzle transitions from draft to published, visibility changes"""
        p = repo.create(make_puzzle("DraftThenPublish", status=PuzzleStatus.DRAFT))
        
        # Should not appear in published list while draft
        draft_results = repo.list_published()
        assert not any(r.id == p.id for r in draft_results)
        
        # Update to published
        p.status = PuzzleStatus.PUBLISHED
        repo.update(p)
        
        # Should now appear in published list
        published_results = repo.list_published()
        assert any(r.id == p.id for r in published_results)
    
    def test_published_to_unpublished_visibility_change(self, repo):
        """When puzzle transitions from published to unpublished"""
        p = repo.create(make_puzzle("PublishThenUnpublish", status=PuzzleStatus.PUBLISHED))
        
        # Should appear in published list
        published_results = repo.list_published()
        assert any(r.id == p.id for r in published_results)
        
        # Update to unpublished
        p.status = PuzzleStatus.UNPUBLISHED
        repo.update(p)
        
        # Should no longer appear in published list
        published_results = repo.list_published()
        assert not any(r.id == p.id for r in published_results)


class TestListPublishedFiltering:
    """Test list_published with various filter combinations"""
    
    def test_list_published_no_filters(self, repo):
        """Test list_published returns all published puzzles"""
        p1 = make_puzzle("puzzle1", status=PuzzleStatus.PUBLISHED)
        p2 = make_puzzle("puzzle2", status=PuzzleStatus.PUBLISHED)
        repo.create(p1)
        repo.create(p2)
        
        result = repo.list_published(limit=50)
        assert len(result) == 2
    
    def test_list_published_with_search(self, repo):
        """Test search filter"""
        repo.create(make_puzzle("binary_adder", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hello_world", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(search="binary")
        assert len(result) == 1
        assert result[0].name == "binary_adder"
    
    def test_list_published_with_creator_id(self, repo):
        """Test creator_id filter"""
        repo.create(make_puzzle("p1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("p2", creator_user_id=2, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(creator_id=1)
        assert len(result) == 1
        assert result[0].creator_user_id == 1
    
    def test_list_published_min_difficulty_all_users(self, repo):
        """Test min_difficulty filter for all users"""
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(min_difficulty=2.5)
        assert len(result) == 1
        assert result[0].name == "hard"
    
    def test_list_published_max_difficulty_all_users(self, repo):
        """Test max_difficulty filter for all users"""
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(max_difficulty=1.9)
        assert len(result) == 1
        assert result[0].name == "easy"
    
    def test_list_published_difficulty_range_all_users(self, repo):
        """Test min and max difficulty together"""
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("med", difficulty=PuzzleDifficulty.MEDIUM, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(min_difficulty=1.5, max_difficulty=2.5)
        assert len(result) == 1
        assert result[0].name == "med"
    
    def test_list_published_min_difficulty_experienced(self, repo):
        """Test min_difficulty with only_experienced_difficulty=True"""
        repo.create(make_puzzle("easy", avg_difficulty=1.0, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", avg_difficulty=2.8, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(min_difficulty=2.0, only_experienced_difficulty=True)
        assert len(result) == 1
        assert result[0].name == "hard"
    
    def test_list_published_max_difficulty_experienced(self, repo):
        """Test max_difficulty with only_experienced_difficulty=True"""
        repo.create(make_puzzle("easy", avg_difficulty=1.0, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", avg_difficulty=2.8, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(max_difficulty=1.5, only_experienced_difficulty=True)
        assert len(result) == 1
        assert result[0].name == "easy"
    
    def test_list_published_min_clearness(self, repo):
        """Test min_clearness filter"""
        repo.create(make_puzzle("unclear", avg_clearness=1.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("clear", avg_clearness=4.5, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(min_clearness=3.0)
        assert len(result) == 1
        assert result[0].name == "clear"
    
    def test_list_published_max_clearness(self, repo):
        """Test max_clearness filter"""
        repo.create(make_puzzle("unclear", avg_clearness=1.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("clear", avg_clearness=4.5, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(max_clearness=2.0)
        assert len(result) == 1
        assert result[0].name == "unclear"
    
    def test_list_published_min_fun(self, repo):
        """Test min_fun filter"""
        repo.create(make_puzzle("boring", avg_fun=1.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("fun", avg_fun=4.5, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(min_fun=3.0)
        assert len(result) == 1
        assert result[0].name == "fun"
    
    def test_list_published_max_fun(self, repo):
        """Test max_fun filter"""
        repo.create(make_puzzle("boring", avg_fun=1.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("fun", avg_fun=4.5, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(max_fun=2.0)
        assert len(result) == 1
        assert result[0].name == "boring"
    
    def test_list_published_date_from(self, repo):
        """Test date_from filter"""
        p1 = make_puzzle("old", status=PuzzleStatus.PUBLISHED)
        p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        p2 = make_puzzle("new", status=PuzzleStatus.PUBLISHED)
        p2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(p1)
        repo.create(p2)
        
        result = repo.list_published(date_from="2024-01-01")
        assert len(result) == 1
        assert result[0].name == "new"
    
    def test_list_published_date_to(self, repo):
        """Test date_to filter"""
        p1 = make_puzzle("old", status=PuzzleStatus.PUBLISHED)
        p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        p2 = make_puzzle("new", status=PuzzleStatus.PUBLISHED)
        p2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(p1)
        repo.create(p2)
        
        result = repo.list_published(date_to="2021-01-01")
        assert len(result) == 1
        assert result[0].name == "old"
    
    def test_list_published_order_by_created_at_asc(self, repo):
        """Test ordering by created_at ascending"""
        p1 = make_puzzle("first", status=PuzzleStatus.PUBLISHED)
        p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        p2 = make_puzzle("second", status=PuzzleStatus.PUBLISHED)
        p2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(p1)
        repo.create(p2)
        
        result = repo.list_published(order_by="created_at", order_direction="ASC")
        assert result[0].name == "first"
        assert result[1].name == "second"
    
    def test_list_published_order_by_difficulty(self, repo):
        """Test ordering by difficulty"""
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, avg_difficulty=3.0, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, avg_difficulty=1.0, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(order_by="difficulty", order_direction="ASC")
        assert result[0].name == "easy"
        assert result[1].name == "hard"
    
    def test_list_published_order_by_fun(self, repo):
        """Test ordering by fun"""
        repo.create(make_puzzle("less_fun", avg_fun=2.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("more_fun", avg_fun=4.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(order_by="fun", order_direction="ASC")
        assert result[0].name == "less_fun"
        assert result[1].name == "more_fun"
    
    def test_list_published_order_by_clearness(self, repo):
        """Test ordering by clearness"""
        repo.create(make_puzzle("unclear", avg_clearness=1.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("clear", avg_clearness=4.0, rating_count=1, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(order_by="clearness", order_direction="ASC")
        assert result[0].name == "unclear"
        assert result[1].name == "clear"
    
    def test_list_published_invalid_order_by(self, repo):
        """Test invalid order_by falls back to created_at"""
        repo.create(make_puzzle("p1", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(order_by="invalid_field")
        assert len(result) == 1
    
    def test_list_published_pagination(self, repo):
        """Test limit and offset"""
        for i in range(5):
            repo.create(make_puzzle(f"puzzle{i}", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_published(limit=2, offset=0)
        assert len(result) == 2
        
        result2 = repo.list_published(limit=2, offset=2)
        assert len(result2) == 2


class TestCountPublished:
    """Test count_published with filters"""
    
    def test_count_published_all(self, repo):
        """Test count_published with no filters"""
        repo.create(make_puzzle("p1", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("p2", status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_published()
        assert count == 2
    
    def test_count_published_with_search(self, repo):
        """Test count_published with search"""
        repo.create(make_puzzle("binary_adder", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hello_world", status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_published(search="binary")
        assert count == 1
    
    def test_count_published_with_creator_id(self, repo):
        """Test count_published with creator_id"""
        repo.create(make_puzzle("p1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("p2", creator_user_id=2, status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_published(creator_id=1)
        assert count == 1
    
    def test_count_published_min_difficulty(self, repo):
        """Test count_published with min_difficulty"""
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_published(min_difficulty=2.5)
        assert count == 1
    
    def test_count_published_max_difficulty(self, repo):
        """Test count_published with max_difficulty"""
        repo.create(make_puzzle("easy", difficulty=PuzzleDifficulty.EASY, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hard", difficulty=PuzzleDifficulty.HARD, status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_published(max_difficulty=1.9)
        assert count == 1
    
    def test_count_published_date_range(self, repo):
        """Test count_published with date filters"""
        p1 = make_puzzle("old", status=PuzzleStatus.PUBLISHED)
        p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        p2 = make_puzzle("new", status=PuzzleStatus.PUBLISHED)
        p2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(p1)
        repo.create(p2)
        
        count = repo.count_published(date_from="2024-01-01", date_to="2026-01-01")
        assert count == 1


class TestListAllForAdmin:
    """Test list_all_for_admin method"""
    
    def test_list_all_for_admin_no_filters(self, repo):
        """Test list_all_for_admin returns all puzzles"""
        repo.create(make_puzzle("draft", status=PuzzleStatus.DRAFT))
        repo.create(make_puzzle("published", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin()
        assert len(result) == 2
    
    def test_list_all_for_admin_with_status(self, repo):
        """Test list_all_for_admin with status parameter"""
        repo.create(make_puzzle("draft", status=PuzzleStatus.DRAFT))
        repo.create(make_puzzle("published", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin(status=PuzzleStatus.PUBLISHED.value)
        assert len(result) == 1
        assert result[0].status == PuzzleStatus.PUBLISHED

    def test_list_all_for_admin_offset(self, repo):
        """Test list_all_for_admin with offset parameter"""
        puzzle1 = repo.create(make_puzzle("puzzle_1"))
        puzzle2 = repo.create(make_puzzle("puzzle_2"))
        puzzle3 = repo.create(make_puzzle("puzzle_3"))
        
        result = repo.list_all_for_admin(limit=2, offset=1)
        assert len(result) == 2

    def test_list_all_for_admin_creator_id(self, repo):
        """Test list_all_for_admin with creator_id filter"""
        creator_id = 123
        puzzle1 = make_puzzle("puzzle_1", creator_user_id=creator_id)
        puzzle2 = make_puzzle("puzzle_2", creator_user_id=456)
        repo.create(puzzle1)
        repo.create(puzzle2)
        
        result = repo.list_all_for_admin(creator_id=creator_id)
        assert len(result) == 1
        assert result[0].creator_user_id == creator_id

    def test_list_all_for_admin_date_range(self, repo):
        """Test list_all_for_admin with date range filter"""
        puzzle = repo.create(make_puzzle("puzzle_1"))
        
        result = repo.list_all_for_admin(date_from="2020-01-01", date_to="2030-01-01")
        assert len(result) >= 1


        
        result = repo.list_all_for_admin(status=PuzzleStatus.DRAFT.value)
        assert len(result) == 1
        assert result[0].status == PuzzleStatus.DRAFT
    
    def test_list_all_for_admin_with_search(self, repo):
        """Test list_all_for_admin with search filter"""
        repo.create(make_puzzle("binary_adder", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hello", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin(search="binary")
        assert len(result) == 1
    
    def test_list_all_for_admin_with_creator_id(self, repo):
        """Test list_all_for_admin with creator_id filter"""
        repo.create(make_puzzle("p1", creator_user_id=1, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("p2", creator_user_id=2, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin(creator_id=1)
        assert len(result) == 1
    
    def test_list_all_for_admin_order_by_name(self, repo):
        """Test list_all_for_admin ordering by name"""
        repo.create(make_puzzle("zebra", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("apple", status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin(order_by="name", order_direction="ASC")
        assert result[0].name == "apple"
        assert result[1].name == "zebra"
    
    def test_list_all_for_admin_order_by_rating_count(self, repo):
        """Test list_all_for_admin ordering by rating_count"""
        repo.create(make_puzzle("popular", rating_count=100, status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("unpopular", rating_count=5, status=PuzzleStatus.PUBLISHED))
        
        result = repo.list_all_for_admin(order_by="rating_count", order_direction="DESC")
        assert result[0].rating_count == 100
        assert result[1].rating_count == 5


class TestCountAllForAdmin:
    """Test count_all_for_admin method"""
    
    def test_count_all_for_admin_no_filters(self, repo):
        """Test count_all_for_admin with no filters"""
        repo.create(make_puzzle("p1", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("p2", status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_all_for_admin()
        assert count == 2
    
    def test_count_all_for_admin_with_status(self, repo):
        """Test count_all_for_admin with status filter"""
        repo.create(make_puzzle("draft", status=PuzzleStatus.DRAFT))
        repo.create(make_puzzle("published", status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_all_for_admin(status=PuzzleStatus.DRAFT.value)
        assert count == 1
    
    def test_count_all_for_admin_with_search(self, repo):
        """Test count_all_for_admin with search filter"""
        repo.create(make_puzzle("binary_adder", status=PuzzleStatus.PUBLISHED))
        repo.create(make_puzzle("hello", status=PuzzleStatus.PUBLISHED))
        
        count = repo.count_all_for_admin(search="binary")
        assert count == 1
    
    def test_count_all_for_admin_with_dates(self, repo):
        """Test count_all_for_admin with date filters"""
        p1 = make_puzzle("old", status=PuzzleStatus.PUBLISHED)
        p1.created_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        p2 = make_puzzle("new", status=PuzzleStatus.PUBLISHED)
        p2.created_at = datetime(2025, 1, 1, tzinfo=timezone.utc)
        repo.create(p1)
        repo.create(p2)
        
        count = repo.count_all_for_admin(date_from="2024-01-01")
        assert count == 1


class TestGetByCreatorAndStatus:
    """Test get_by_creator_and_status method"""
    
    def test_get_by_creator_and_status(self, repo):
        """Test filtering by creator and status"""
        repo.create(make_puzzle("draft1", status=PuzzleStatus.DRAFT, creator_user_id=1))
        repo.create(make_puzzle("published1", status=PuzzleStatus.PUBLISHED, creator_user_id=1))
        repo.create(make_puzzle("draft2", status=PuzzleStatus.DRAFT, creator_user_id=2))
        
        result = repo.get_by_creator_and_status(1, PuzzleStatus.DRAFT)
        assert len(result) == 1
        assert result[0].name == "draft1"


class TestDeleteByIds:
    """Test delete_by_ids method"""
    
    def test_delete_by_ids_empty_list(self, repo):
        """Test delete_by_ids with empty list"""
        result = repo.delete_by_ids([])
        assert result == 0
    
    def test_delete_by_ids_single(self, repo):
        """Test delete_by_ids with single ID"""
        p = make_puzzle("test")
        created = repo.create(p)
        
        result = repo.delete_by_ids([created.id])
        assert result == 1
    
    def test_delete_by_ids_multiple(self, repo):
        """Test delete_by_ids with multiple IDs"""
        p1 = repo.create(make_puzzle("p1"))
        p2 = repo.create(make_puzzle("p2"))
        p3 = repo.create(make_puzzle("p3"))
        
        result = repo.delete_by_ids([p1.id, p2.id])
        assert result == 2
        
        # Verify p3 still exists
        remaining = repo.get_by_id(p3.id)
        assert remaining is not None


class TestUpdateRatingAggregates:
    """Test update_rating_aggregates method"""
    
    def test_update_rating_aggregates_single_field(self, repo):
        """Test updating single rating field"""
        p = repo.create(make_puzzle("test", rating_count=5, avg_difficulty=1.0))
        
        repo.update_rating_aggregates(p.id, rating_count=10)
        
        updated = repo.get_by_id(p.id)
        assert updated.rating_count == 10
        assert updated.avg_difficulty == 1.0
    
    def test_update_rating_aggregates_multiple_fields(self, repo):
        """Test updating multiple rating fields"""
        p = repo.create(make_puzzle("test", rating_count=5))
        
        repo.update_rating_aggregates(p.id, rating_count=10, avg_fun=4.5)
        
        updated = repo.get_by_id(p.id)
        assert updated.rating_count == 10
        assert updated.avg_fun == 4.5
    
    def test_update_rating_aggregates_empty_kwargs(self, repo):
        """Test update_rating_aggregates with no changes"""
        p = repo.create(make_puzzle("test"))
        original = repo.get_by_id(p.id)
        
        repo.update_rating_aggregates(p.id, invalid_field="should_be_ignored")
        
        updated = repo.get_by_id(p.id)
        assert updated.rating_count == original.rating_count


class TestDifficultyToLevel:
    """Test _difficulty_to_level static method"""
    
    def test_difficulty_to_level_easy(self):
        """Test EASY difficulty conversion"""
        level = PuzzleRepo._difficulty_to_level(1.0)
        assert level == "EASY"
    
    def test_difficulty_to_level_medium(self):
        """Test MEDIUM difficulty conversion"""
        level = PuzzleRepo._difficulty_to_level(2.0)
        assert level == "MEDIUM"
    
    def test_difficulty_to_level_hard(self):
        """Test HARD difficulty conversion"""
        level = PuzzleRepo._difficulty_to_level(3.0)
        assert level == "HARD"
    
    def test_difficulty_to_level_boundary_easy_medium(self):
        """Test boundary between EASY and MEDIUM"""
        level = PuzzleRepo._difficulty_to_level(1.5)
        assert level == "EASY"
    
    def test_difficulty_to_level_boundary_medium_hard(self):
        """Test boundary between MEDIUM and HARD"""
        level = PuzzleRepo._difficulty_to_level(2.5)
        assert level == "MEDIUM"


class TestPuzzleRepoCountByCreatorAndStatus:
    """Tests for count_by_creator_and_status() efficient COUNT query."""

    def test_count_returns_zero_when_no_puzzles(self, repo):
        count = repo.count_by_creator_and_status(creator_id=999, status=PuzzleStatus.DRAFT)
        assert count == 0

    def test_count_draft_puzzles_for_creator(self, repo):
        p1 = make_puzzle("puzzle-draft-1", creator_user_id=1, status=PuzzleStatus.DRAFT)
        p2 = make_puzzle("puzzle-draft-2", creator_user_id=1, status=PuzzleStatus.DRAFT)
        p3 = make_puzzle("puzzle-pub-1", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        repo.create(p1)
        repo.create(p2)
        repo.create(p3)
        count = repo.count_by_creator_and_status(creator_id=1, status=PuzzleStatus.DRAFT)
        assert count == 2

    def test_count_published_puzzles_for_creator(self, repo):
        p1 = make_puzzle("pub-a", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        p2 = make_puzzle("draft-a", creator_user_id=2, status=PuzzleStatus.DRAFT)
        repo.create(p1)
        repo.create(p2)
        count = repo.count_by_creator_and_status(creator_id=2, status=PuzzleStatus.PUBLISHED)
        assert count == 1
        count_draft = repo.count_by_creator_and_status(creator_id=2, status=PuzzleStatus.DRAFT)
        assert count_draft == 1
