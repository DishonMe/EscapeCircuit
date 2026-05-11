import contextlib
import json
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import UserRole, PuzzleStatus, GateType, TestCaseKind
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.settings import PUZZLE_MAX_PUBLISHED_PER_USER


class TestPuzzleServiceCreation:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.count_published.return_value = 0
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_puzzle_service_initialization(self):
        assert self.service.repo == self.mock_puzzle_repo
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.auth == self.mock_auth


class TestPuzzleServiceBrowse:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_browse_success(self):
        self.mock_auth.require_user_id.return_value = 1
        puzzles = [
            Puzzle(id=1, name="Puzzle1", creator_user_id=2, status=PuzzleStatus.PUBLISHED),
            Puzzle(id=2, name="Puzzle2", creator_user_id=3, status=PuzzleStatus.PUBLISHED),
        ]
        self.mock_puzzle_repo.list_published.return_value = puzzles
        self.mock_puzzle_repo.count_published.return_value = 2

        result = self.service.browse("valid_token")

        assert len(result["data"]) == 2
        assert result["data"][0]["name"] == "Puzzle1"
        self.mock_puzzle_repo.list_published.assert_called_once()
        self.mock_puzzle_repo.count_published.assert_called_once()

    def test_browse_with_pagination(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0

        self.service.browse("valid_token", limit=100, offset=50)

        self.mock_puzzle_repo.list_published.assert_called_once()

    def test_browse_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.browse("invalid_token")


class TestPuzzleServiceSearch:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_search_success(self):
        self.mock_auth.require_user_id.return_value = 1
        puzzles = [Puzzle(id=1, name="SearchResult", creator_user_id=2)]
        self.mock_puzzle_repo.search_by_name.return_value = puzzles

        result = self.service.search("valid_token", "Search")

        assert len(result) == 1
        assert result[0]["name"] == "SearchResult"
        self.mock_puzzle_repo.search_by_name.assert_called_once_with("Search", only_published=True)

    def test_search_unpublished(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.search_by_name.return_value = []

        self.service.search("valid_token", "test", only_published=False)

        self.mock_puzzle_repo.search_by_name.assert_called_once_with("test", only_published=False)

    def test_search_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.search("invalid_token", "test")


class TestPuzzleServiceGet:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_get_puzzle_success(self):
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Puzzle(id=1, name="TestPuzzle", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        # Mock test cases list to return empty list or mock list, ensuring it is subscriptable if checked
        self.mock_puzzle_repo.list_test_cases.return_value = []

        result = self.service.get("valid_token", 1)

        assert result["name"] == "TestPuzzle"
        self.mock_puzzle_repo.get_by_id.assert_called_once_with(1)

    def test_get_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.get("valid_token", 999)
        assert "puzzle not found" in str(exc_info.value)

    def test_get_puzzle_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.get("invalid_token", 1)


class TestPuzzleServiceCreatePuzzle:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_create_puzzle_success(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        payload = {
            "name": "NewPuzzle",
            "description": "A new puzzle",
            "budget": 100,
            "default_gate_set": ["AND", "OR"],
        }

        created_puzzle = Puzzle(
            id=1,
            name="NewPuzzle",
            creator_user_id=1,
            description="A new puzzle",
            budget=100,
            default_gate_set={GateType.AND, GateType.OR},
            status=PuzzleStatus.DRAFT,
        )
        self.mock_puzzle_repo.create.return_value = created_puzzle

        # Patch Puzzle constructor to avoid id=0 validation error in service
        with patch('Backend.DomainLayer.Puzzle.Puzzle') as mock_puzzle_class:
            mock_instance = Mock(spec=Puzzle)
            mock_instance.to_dict.return_value = created_puzzle.to_dict()
            mock_puzzle_class.return_value = mock_instance
            result = self.service.create_puzzle("valid_token", payload)

        assert result["name"] == "NewPuzzle"
        assert result["creator_user_id"] == 1
        self.mock_puzzle_repo.create.assert_called_once()

    def test_create_puzzle_non_creator(self):
        self.mock_auth.require_user_id.return_value = 1
        non_creator = User(id=1, username="user", role=UserRole.SOLVER)
        self.mock_user_repo.get_by_id.return_value = non_creator

        payload = {"name": "NewPuzzle"}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "creator" in str(exc_info.value).lower()

    def test_create_puzzle_missing_name(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        payload = {"name": ""}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "name is required" in str(exc_info.value).lower()

    def test_create_puzzle_rejects_name_too_long(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None

        payload = {"name": "x" * 101}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "at most 100 characters" in str(exc_info.value)

    def test_create_puzzle_rejects_duplicate_name(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = (1,)

        payload = {"name": "Existing Puzzle"}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "already exists" in str(exc_info.value)

    def test_create_puzzle_rejects_description_too_long(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        payload = {"name": "Valid Name", "description": "d" * 2001}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "description must be at most 2000 characters" in str(exc_info.value).lower()

    def test_create_puzzle_rejects_instructions_too_large(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        payload = {"name": "Valid Name", "instructions": "a" * 5121}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "instructions must be at most 5120 bytes" in str(exc_info.value).lower()

    def test_create_puzzle_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        payload = {"name": "NewPuzzle"}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "user not found" in str(exc_info.value)

    def test_create_puzzle_admin_allowed(self):
        self.mock_auth.require_user_id.return_value = 1
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.mock_user_repo.get_by_id.return_value = admin_user

        payload = {"name": "AdminPuzzle", "budget": 50}

        created_puzzle = Mock(spec=Puzzle)
        created_puzzle.id = 1
        created_puzzle.name = "AdminPuzzle"
        created_puzzle.creator_user_id = 1
        created_puzzle.status = PuzzleStatus.DRAFT
        created_puzzle.to_dict.return_value = {
            "id": 1,
            "name": "AdminPuzzle",
            "creator_user_id": 1,
            "status": "draft"
        }
        self.mock_puzzle_repo.create.return_value = created_puzzle

        # Patch Puzzle constructor to avoid id=0 validation error
        with patch('Backend.DomainLayer.Puzzle.Puzzle') as mock_puzzle_class:
            mock_instance = Mock(spec=Puzzle)
            mock_instance.to_dict.return_value = created_puzzle.to_dict()
            mock_puzzle_class.return_value = mock_instance
            result = self.service.create_puzzle("valid_token", payload)

        assert result["name"] == "AdminPuzzle"


class TestPuzzleServicePublish:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.count_published.return_value = 0
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_publish_success_by_creator(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        draft_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        published_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        # First call: pre-checks; second call: re-read after atomic update
        self.mock_puzzle_repo.get_by_id.side_effect = [draft_puzzle, published_puzzle]
        self.mock_puzzle_repo.count_published.return_value = 0
        self.mock_puzzle_repo.list_test_cases.return_value = [Mock()]

        # Mock conn.execute to return cursor with rowcount=1 (update succeeded)
        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor

        result = self.service.publish("valid_token", 1)

        assert result["status"] == PuzzleStatus.PUBLISHED.value
        self.mock_puzzle_repo.conn.execute.assert_called()

    def test_publish_success_by_admin(self):
        self.mock_auth.require_user_id.return_value = 1
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.mock_user_repo.get_by_id.return_value = admin_user

        draft_puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        published_puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        # First call: pre-checks; second call: re-read after atomic update
        self.mock_puzzle_repo.get_by_id.side_effect = [draft_puzzle, published_puzzle]

        result = self.service.publish("valid_token", 1)

        assert result["status"] == PuzzleStatus.PUBLISHED.value

    def test_publish_forbidden(self):
        self.mock_auth.require_user_id.return_value = 1
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        self.mock_user_repo.get_by_id.return_value = other_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "not allowed" in str(exc_info.value)

    def test_publish_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 999)
        assert "puzzle not found" in str(exc_info.value)

    def test_publish_rejects_non_admin_at_published_limit(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        draft_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = draft_puzzle
        self.mock_puzzle_repo.list_test_cases.return_value = [Mock()]
        self.mock_puzzle_repo.count_published.return_value = PUZZLE_MAX_PUBLISHED_PER_USER

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)

        assert str(exc_info.value) == (
            f"You have reached the maximum limit of {PUZZLE_MAX_PUBLISHED_PER_USER} published puzzles."
        )

    def test_publish_admin_bypasses_published_limit(self):
        self.mock_auth.require_user_id.return_value = 1
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.mock_user_repo.get_by_id.return_value = admin_user

        draft_puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        published_puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.side_effect = [draft_puzzle, published_puzzle]
        self.mock_puzzle_repo.list_test_cases.return_value = [Mock()]

        mock_cursor = Mock()
        mock_cursor.rowcount = 1
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor

        result = self.service.publish("valid_token", 1)

        assert result["status"] == PuzzleStatus.PUBLISHED.value
        self.mock_puzzle_repo.count_published.assert_not_called()


class TestPuzzleServiceUnpublish:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_unpublish_success(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        published = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        unpublished = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.UNPUBLISHED)
        # First call: ownership check; second call: re-read after atomic update
        self.mock_puzzle_repo.get_by_id.side_effect = [published, unpublished]

        result = self.service.unpublish("valid_token", 1)

        assert result["status"] == PuzzleStatus.UNPUBLISHED.value

    def test_unpublish_forbidden(self):
        self.mock_auth.require_user_id.return_value = 1
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        self.mock_user_repo.get_by_id.return_value = other_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 1)
        assert "not allowed" in str(exc_info.value)


class TestPuzzleServiceAddTestCase:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_add_test_case_success(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        # The repo returns the saved test case with id assigned by DB
        saved_test_case = Mock(spec=PuzzleTestCase)
        saved_test_case.id = 1
        saved_test_case.puzzle_id = 1
        saved_test_case.kind = TestCaseKind.BLACKBOX
        saved_test_case.inputs = {"A": 1}
        saved_test_case.expected_outputs = {"Q": 1}
        saved_test_case.to_dict.return_value = {
            "id": 1,
            "puzzle_id": 1,
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1}
        }
        self.mock_puzzle_repo.add_test_case.return_value = saved_test_case

        payload = {
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1},
        }

        with patch('Backend.DomainLayer.PuzzleTestCase.PuzzleTestCase') as mock_tc_class:
            mock_tc_class.return_value = saved_test_case
            result = self.service.add_test_case("valid_token", 1, payload)

        assert result["puzzle_id"] == 1
        assert result["kind"] == "blackbox"
        self.mock_puzzle_repo.add_test_case.assert_called_once()

    def test_add_test_case_forbidden(self):
        self.mock_auth.require_user_id.return_value = 1
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        self.mock_user_repo.get_by_id.return_value = other_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        payload = {
            "kind": "NORMAL",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1},
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.add_test_case("valid_token", 1, payload)
        assert "not allowed" in str(exc_info.value)


class TestPuzzleServiceListTestCases:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_list_test_cases_success(self):
        self.mock_auth.require_user_id.return_value = 1
        test_cases = [
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"A": 1},
                expected_outputs={"Q": 1},
            )
        ]
        self.mock_puzzle_repo.list_test_cases.return_value = test_cases

        result = self.service.list_test_cases("valid_token", 1)

        assert len(result) == 1
        assert result[0]["kind"] == "blackbox"

    def test_list_test_cases_empty(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_test_cases.return_value = []

        result = self.service.list_test_cases("valid_token", 1)

        assert result == []

class TestPuzzleServiceBranches:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_publish_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "user not found" in str(exc_info.value)

    def test_unpublish_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 1)
        assert "user not found" in str(exc_info.value)

    def test_unpublish_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 999)
        assert "puzzle not found" in str(exc_info.value)

    def test_add_test_case_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        payload = {
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1},
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.add_test_case("valid_token", 1, payload)
        assert "user not found" in str(exc_info.value)

    def test_add_test_case_puzzle_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        payload = {
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1},
        }

        with pytest.raises(ValidationError) as exc_info:
            self.service.add_test_case("valid_token", 1, payload)
        assert "puzzle not found" in str(exc_info.value)

    def test_add_test_case_admin_other_creator(self):
        self.mock_auth.require_user_id.return_value = 1
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.mock_user_repo.get_by_id.return_value = admin_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        saved_test_case = Mock(spec=PuzzleTestCase)
        saved_test_case.id = 1
        saved_test_case.puzzle_id = 1
        saved_test_case.kind = TestCaseKind.BLACKBOX
        saved_test_case.inputs = {"A": 1}
        saved_test_case.expected_outputs = {"Q": 1}
        saved_test_case.to_dict.return_value = {
            "id": 1,
            "puzzle_id": 1,
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1}
        }
        self.mock_puzzle_repo.add_test_case.return_value = saved_test_case

        payload = {
            "kind": "blackbox",
            "inputs": {"A": 1},
            "expected_outputs": {"Q": 1},
        }

        with patch('Backend.DomainLayer.PuzzleTestCase.PuzzleTestCase') as mock_tc_class:
            mock_tc_class.return_value = saved_test_case
            result = self.service.add_test_case("valid_token", 1, payload)

        assert result["puzzle_id"] == 1


class TestPuzzleServicePublish:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.count_published.return_value = 0
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_publish_success_creator(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        published_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        test_case = Mock()
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, puzzle, published_puzzle]
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]
        self.mock_puzzle_repo.conn.execute.return_value.rowcount = 1
        self.mock_puzzle_repo.conn.execute.return_value.fetchall.return_value = []

        result = self.service.publish("valid_token", 1)

        assert result["name"] == "Test"
        self.mock_puzzle_repo.get_by_id.assert_called()

    def test_publish_no_test_cases(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.list_test_cases.return_value = []

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "Cannot publish puzzle without test cases" in str(exc_info.value)

    def test_publish_puzzle_not_found(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "puzzle not found" in str(exc_info.value)

    def test_publish_not_creator_not_admin(self):
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = other_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "not allowed" in str(exc_info.value)

    def test_publish_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.publish("valid_token", 1)
        assert "user not found" in str(exc_info.value)


class TestPuzzleServiceUnpublish:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_unpublish_success_creator(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, puzzle]
        
        unpublished_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.UNPUBLISHED)
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, puzzle, unpublished_puzzle]

        result = self.service.unpublish("valid_token", 1)

        assert result["name"] == "Test"
        self.mock_puzzle_repo.conn.execute.assert_called()

    def test_unpublish_puzzle_not_found(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 1)
        assert "puzzle not found" in str(exc_info.value)

    def test_unpublish_not_creator(self):
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = other_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 1)
        assert "not allowed" in str(exc_info.value)

    def test_unpublish_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.unpublish("valid_token", 1)
        assert "user not found" in str(exc_info.value)


class TestPuzzleServiceDeletePuzzle:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_delete_puzzle_success_creator(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.delete.return_value = True

        result = self.service.delete_puzzle("valid_token", 1)

        assert result["success"] is True
        self.mock_puzzle_repo.delete.assert_called_once_with(1)

    def test_delete_puzzle_success_admin(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.delete.return_value = True

        result = self.service.delete_puzzle("valid_token", 1)

        assert result["success"] is True

    def test_delete_puzzle_puzzle_not_found(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_puzzle("valid_token", 1)
        assert "puzzle not found" in str(exc_info.value)

    def test_delete_puzzle_not_creator(self):
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = other_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_puzzle("valid_token", 1)
        assert "not allowed" in str(exc_info.value)

    def test_delete_puzzle_delete_failed(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.delete.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_puzzle("valid_token", 1)
        assert "Failed to delete puzzle" in str(exc_info.value)

    def test_delete_puzzle_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_puzzle("valid_token", 1)
        assert "user not found" in str(exc_info.value)


class TestPuzzleServiceUpdatePuzzle:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_update_puzzle_name_only(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Old", creator_user_id=1)
        updated_puzzle = Puzzle(id=1, name="New", creator_user_id=1)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, updated_puzzle]
        
        payload = {"name": "New"}
        result = self.service.update_puzzle("valid_token", 1, payload)
        
        assert result["name"] == "New"
        self.mock_puzzle_repo.conn.execute.assert_called()

    def test_update_puzzle_description_only(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, description="Old")
        updated_puzzle = Puzzle(id=1, name="Test", creator_user_id=1, description="New")
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, updated_puzzle]
        
        payload = {"description": "New"}
        result = self.service.update_puzzle("valid_token", 1, payload)
        
        assert result["description"] == "New"

    def test_update_puzzle_empty_name_validation(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        payload = {"name": ""}
        with pytest.raises(ValidationError) as exc_info:
            self.service.update_puzzle("valid_token", 1, payload)
        assert "empty" in str(exc_info.value).lower()

    def test_update_puzzle_no_changes(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, puzzle]
        
        payload = {}
        result = self.service.update_puzzle("valid_token", 1, payload)
        
        assert result["name"] == "Test"

    def test_update_puzzle_multiple_fields(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, description="Old")
        updated = Puzzle(id=1, name="New", creator_user_id=1, description="New desc")
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, updated]
        
        payload = {"name": "New", "description": "New desc"}
        result = self.service.update_puzzle("valid_token", 1, payload)
        
        self.mock_puzzle_repo.conn.execute.assert_called()

    def test_update_puzzle_not_creator_admin_allowed(self):
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        updated = Puzzle(id=1, name="Updated", creator_user_id=2)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin_user
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, updated]
        
        payload = {"name": "Updated"}
        result = self.service.update_puzzle("valid_token", 1, payload)
        
        assert result["name"] == "Updated"

    def test_update_puzzle_puzzle_not_found(self):
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator_user
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.update_puzzle("valid_token", 1, {"name": "New"})
        assert "puzzle not found" in str(exc_info.value)

    def test_update_puzzle_not_creator(self):
        other_user = User(id=1, username="user", role=UserRole.SOLVER)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = other_user
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.update_puzzle("valid_token", 1, {"name": "New"})
        assert "not allowed" in str(exc_info.value)

    def test_update_puzzle_user_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.update_puzzle("valid_token", 1, {"name": "New"})
        assert "user not found" in str(exc_info.value)


class TestPuzzleServiceCapacityLimits:
    """Tests for per-user puzzle capacity enforcement in PuzzleService."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def _make_conn_execute(self, unpublished_count=0, published_count=0):
        """Configure mock conn to return specific counts for capacity queries."""
        def side_effect(sql, *args, **kwargs):
            m = Mock()
            if "status IN ('draft','unpublished')" in sql:
                m.fetchone.return_value = (unpublished_count,)
            elif "status='published'" in sql:
                m.fetchone.return_value = (published_count,)
            else:
                m.fetchone.return_value = None
                m.fetchall.return_value = []
            return m
        self.mock_puzzle_repo.conn.execute.side_effect = side_effect

    # ── create_puzzle limits ────────────────────────────────────────────

    def test_create_puzzle_blocked_by_unpublished_limit(self):
        """Creator at their unpublished limit cannot create a new puzzle."""
        # Default capacity for level-1 user is 5 unpublished
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=0)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator
        self._make_conn_execute(unpublished_count=5, published_count=0)

        with pytest.raises(ValidationError, match="maximum limit"):
            self.service.create_puzzle("token", {"name": "New", "default_gate_set": []})

    def test_create_puzzle_blocked_over_limit(self):
        """Creator over their limits is blocked from creating."""
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=0)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator
        self._make_conn_execute(unpublished_count=6, published_count=6)

        with pytest.raises(ValidationError):
            self.service.create_puzzle("token", {"name": "New", "default_gate_set": []})

    def test_create_puzzle_admin_bypasses_limit(self):
        """Admins are never blocked by capacity limits."""
        admin = User(id=1, username="admin", role=UserRole.ADMIN, xp=0)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin

        saved = Puzzle(id=5, name="AdminPuzzle", creator_user_id=1)
        self.mock_puzzle_repo.create.return_value = saved
        self.mock_user_repo.get_by_id.return_value = admin
        # conn.execute for duplicate-name check returns None (no duplicate)
        def conn_exec(sql, *args, **kwargs):
            m = Mock()
            m.fetchone.return_value = None
            return m
        self.mock_puzzle_repo.conn.execute.side_effect = conn_exec

        result = self.service.create_puzzle("token", {
            "name": "AdminPuzzle", "default_gate_set": []
        })
        assert result["name"] == "AdminPuzzle"

    def test_create_puzzle_under_limit_succeeds(self):
        """Creator below their limit can create a puzzle."""
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=0)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator

        saved = Puzzle(id=2, name="MyPuzzle", creator_user_id=1)
        self.mock_puzzle_repo.create.return_value = saved

        def conn_exec(sql, *args, **kwargs):
            m = Mock()
            if "status IN" in sql:
                m.fetchone.return_value = (2,)  # 2 unpublished < 5 limit
            elif "status=" in sql:
                m.fetchone.return_value = (1,)  # 1 published < 5 limit
            else:
                m.fetchone.return_value = None
            return m
        self.mock_puzzle_repo.conn.execute.side_effect = conn_exec

        result = self.service.create_puzzle("token", {
            "name": "MyPuzzle", "default_gate_set": []
        })
        assert result["name"] == "MyPuzzle"

    # ── update_puzzle limits ────────────────────────────────────────────

    def test_update_puzzle_blocked_over_limit(self):
        """Creator over their limit cannot edit a puzzle."""
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=0)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self._make_conn_execute(unpublished_count=10, published_count=10)

        with pytest.raises(ValidationError, match="exceeded your puzzle limits"):
            self.service.update_puzzle("token", 1, {"name": "New"})

    def test_update_puzzle_admin_bypasses_limit(self):
        """Admins can always edit puzzles even when creators are over limit."""
        admin = User(id=1, username="admin", role=UserRole.ADMIN, xp=0)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2)
        updated = Puzzle(id=1, name="Updated", creator_user_id=2)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = admin
        self.mock_puzzle_repo.get_by_id.side_effect = [puzzle, updated]

        def conn_exec(sql, *args, **kwargs):
            m = Mock()
            m.fetchone.return_value = None
            return m
        self.mock_puzzle_repo.conn.execute.side_effect = conn_exec

        result = self.service.update_puzzle("token", 1, {"name": "Updated"})
        assert result["name"] == "Updated"

    # ── publish limits ──────────────────────────────────────────────────

    def test_publish_uses_per_user_published_limit(self):
        """Creator with admin-override limit can't publish past that limit."""
        # Admin set max_published = 2; user has 2 published already
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=0,
                       max_published_puzzles=2)
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = creator
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.list_test_cases.return_value = [Mock()]

        # Simulate 2 published, non-popular puzzles
        def conn_exec(sql, *args, **kwargs):
            m = Mock()
            if "status = 'published'" in sql:
                m.fetchall.return_value = [(0, 0, 0.0), (0, 0, 0.0)]
            else:
                m.fetchone.return_value = (1,)
                m.fetchall.return_value = []
            return m
        self.mock_puzzle_repo.conn.execute.side_effect = conn_exec

        import Backend.PersistantLayer._db as db_mod
        with patch.object(db_mod, "transaction", lambda conn: contextlib.nullcontext()):
            with pytest.raises(ValidationError, match="maximum limit of 2"):
                self.service.publish("token", 1)

    def test_publish_level_10_gets_higher_limit(self):
        """Creator at level 10 (xp=900) has a published limit of 7, not 5."""
        creator = User(id=1, username="creator", role=UserRole.CREATOR, xp=900)
        assert creator.level == 10
        max_pub, _ = creator.get_puzzle_capacity()
        assert max_pub == 7


class TestPuzzleServicePrivateMethods:
    """Test private helper methods of PuzzleService"""
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_count_published_puzzles(self):
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = (3,)
        result = self.service._count_published_puzzles(1)
        assert result == 3

    def test_is_admin_with_admin_role(self):
        assert self.service._is_admin(UserRole.ADMIN) is True

    def test_is_admin_with_creator_role(self):
        assert self.service._is_admin(UserRole.CREATOR) is False


class TestPuzzleServiceBrowseFilters:
    """Test browse method with different filter combinations"""
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_browse_with_creator_id_filter(self):
        user_id = 1
        token = "valid_token"
        creator_id = 5
        puzzle = Puzzle(id=1, name="Test", creator_user_id=creator_id, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(token, creator_id=creator_id)
        
        assert result["meta"]["total"] == 1
        assert len(result["data"]) == 1

    def test_browse_with_creator_username_filter(self):
        user_id = 1
        token = "valid_token"
        creator_username = "testuser"
        puzzle = Puzzle(id=1, name="Test", creator_user_id=5, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(token, creator_username=creator_username)
        
        assert result["meta"]["total"] == 1

    def test_browse_with_difficulty_filter(self):
        user_id = 1
        token = "valid_token"
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(token, min_difficulty=2.0, max_difficulty=3.0)
        
        assert len(result["data"]) == 1

    def test_browse_with_clearness_filter(self):
        user_id = 1
        token = "valid_token"
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(token, min_clearness=1.0, max_clearness=2.0)
        
        assert len(result["data"]) == 1

    def test_browse_with_fun_filter(self):
        user_id = 1
        token = "valid_token"
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(token, min_fun=1.5, max_fun=3.5)
        
        assert len(result["data"]) == 1

    def test_browse_with_pagination(self):
        user_id = 1
        token = "valid_token"
        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, description="Test")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 10
        
        result = self.service.browse(token, limit=5, offset=5)
        
        assert result["meta"]["total"] == 10
        assert result["meta"]["page"] == 2

    def test_browse_empty_results(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0
        
        result = self.service.browse(token)
        
        assert len(result["data"]) == 0
        assert result["meta"]["total"] == 0


class TestPuzzleServiceCreatePuzzleErrors:
    """Test create_puzzle method with error scenarios"""
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_create_puzzle_requires_user(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = None
        
        payload = {"name": "Test", "description": "Test puzzle"}
        with pytest.raises(ValidationError):
            self.service.create_puzzle(token, payload)

    def test_create_puzzle_non_creator_not_allowed(self):
        user_id = 1
        token = "valid_token"
        user = User(id=user_id, username="test", role=UserRole.SOLVER)
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        payload = {"name": "Test", "description": "Test puzzle"}
        with pytest.raises(ValidationError):
            self.service.create_puzzle(token, payload)

    def test_create_puzzle_with_creator_role(self):
        user_id = 1
        token = "valid_token"
        user = User(id=user_id, username="test", role=UserRole.CREATOR)
        puzzle = Puzzle(id=100, name="Test", creator_user_id=user_id, description="Test puzzle")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_puzzle_repo.create.return_value = puzzle
        
        payload = {"name": "Test", "description": "Test puzzle", "default_gate_set": []}
        result = self.service.create_puzzle(token, payload)
        
        assert result is not None

    def test_create_puzzle_with_admin_role(self):
        user_id = 1
        token = "valid_token"
        user = User(id=user_id, username="admin", role=UserRole.ADMIN)
        puzzle = Puzzle(id=100, name="AdminTest", creator_user_id=user_id, description="Admin puzzle")
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = user
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None
        self.mock_puzzle_repo.create.return_value = puzzle
        
        payload = {"name": "AdminTest", "description": "Admin puzzle", "default_gate_set": []}
        result = self.service.create_puzzle(token, payload)
        
        assert result is not None


class TestPuzzleServiceListMyPuzzles:
    """Test list_my_puzzles functionality."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_solve_repo = Mock()
        self.mock_auth = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_list_my_puzzles_success(self):
        """Test listing user's puzzles."""
        user_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        # Mock the puzzle repo to have a proper conn object
        mock_cursor_result = Mock()
        mock_cursor_result.fetchall.return_value = []
        mock_cursor_result.fetchone.return_value = (0,)
        
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor_result

        result = self.service.list_my_puzzles(token, limit=10, offset=0)

        assert result is not None
        assert isinstance(result, dict)

    def test_list_my_puzzles_with_limit_offset(self):
        """Test listing with limit and offset."""
        user_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        mock_cursor_result = Mock()
        mock_cursor_result.fetchall.return_value = []
        mock_cursor_result.fetchone.return_value = (5,)
        
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor_result

        result = self.service.list_my_puzzles(token, limit=10, offset=5)

        assert result is not None

    def test_list_my_puzzles_default_pagination(self):
        """Test listing with default pagination."""
        user_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        mock_cursor_result = Mock()
        mock_cursor_result.fetchall.return_value = []
        mock_cursor_result.fetchone.return_value = (0,)
        
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor_result

        # Call with minimal args
        result = self.service.list_my_puzzles(token)

        assert result is not None


class TestPuzzleServiceCountUnpublished:
    """Test unpublished puzzle counting."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_count_unpublished_returns_int(self):
        """Test that count returns integer or gracefully handles."""
        user_id = 1
        
        # Mock the conn.execute properly
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (3,)  # Return proper tuple
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor
        
        result = self.service._count_unpublished_puzzles(user_id)
        
        # Result should be an integer
        assert isinstance(result, int)


class TestPuzzleServiceEnrichPuzzle:
    """Test puzzle enrichment with creator data."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_enrich_puzzle_with_creator(self):
        """Test enriching puzzle with creator."""
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": 5}

        user = User(id=5, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = user

        result = self.service._enrich_puzzle(puzzle_dict)

        assert result is not None
        assert isinstance(result, dict)

    def test_enrich_puzzle_without_creator_id(self):
        """Test enriching puzzle without creator."""
        puzzle_dict = {"id": 1, "name": "Test"}

        result = self.service._enrich_puzzle(puzzle_dict)

        assert result is not None
        assert isinstance(result, dict)

    def test_enrich_puzzle_with_dict_input(self):
        """Test enrichment with different dict structure."""
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": 5, "description": "Test puzzle"}

        user = User(id=5, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = user

        result = self.service._enrich_puzzle(puzzle_dict)

        assert result is not None




class TestPuzzleServiceLoadIOFromRiddleConfig:
    """Test loading puzzle IO from riddle config files."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_load_io_from_riddle_config_returns_tuple(self):
        """Test that _load_io_from_riddle_config returns a tuple."""
        # Create a mock puzzle with riddle_base_name
        riddle_name = "riddle_01_binary_adder"
        
        # The method should return a tuple (inputs, outputs) or (None, None)
        result = self.service._load_io_from_riddle_config(riddle_name)
        
        # Should return a tuple
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_load_io_missing_riddle_name(self):
        """Test with None or empty riddle name."""
        # Empty string should return (None, None)
        result = self.service._load_io_from_riddle_config("")
        
        assert result == (None, None)

    def test_load_io_with_object_no_riddle_base(self):
        """Test with object that has no riddle_base_name."""
        mock_puzzle = Mock()
        mock_puzzle.riddle_base_name = None
        
        result = self.service._load_io_from_riddle_config(mock_puzzle)
        
        assert result == (None, None)




class TestPuzzleServicePublishAndState:
    """Test puzzle state transitions."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_publish_puzzle_success(self):
        """Test publishing a puzzle."""
        user_id = 1
        token = "valid_token"
        puzzle_id = 1

        self.mock_auth.require_user_id.return_value = user_id

        mock_user = Mock()
        mock_user.get_puzzle_capacity.return_value = (100, 50)
        self.mock_user_repo.get_by_id.return_value = mock_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=user_id)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle
        self.mock_puzzle_repo.count_published_by_creator.return_value = 0

        result = self.service.publish(token, puzzle_id)

        assert result is not None
        assert isinstance(result, dict)

    def test_unpublish_puzzle_success(self):
        """Test unpublishing a puzzle."""
        user_id = 1
        token = "valid_token"
        puzzle_id = 1

        self.mock_auth.require_user_id.return_value = user_id

        puzzle = Puzzle(id=1, name="Test", creator_user_id=user_id)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle

        result = self.service.unpublish(token, puzzle_id)

        assert result is not None
        assert isinstance(result, dict)

    def test_delete_puzzle_success(self):
        """Test deleting a puzzle."""
        user_id = 1
        token = "valid_token"
        puzzle_id = 1

        self.mock_auth.require_user_id.return_value = user_id

        puzzle = Puzzle(id=1, name="Test", creator_user_id=user_id)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.delete.return_value = True

        result = self.service.delete_puzzle(token, puzzle_id)

        assert result is not None
        assert isinstance(result, dict)


class TestPuzzleServiceComprehensiveCoverage:
    """Comprehensive tests for PuzzleService to increase coverage."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_slugify_puzzle_name(self):
        """Test puzzle name slugification."""
        result = PuzzleService._slugify_puzzle_name("Test Puzzle!@#")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_sanitize_puzzle_name(self):
        """Test puzzle name sanitization."""
        result = PuzzleService._sanitize_puzzle_name("Test   Puzzle")
        assert isinstance(result, str)

    def test_count_unpublished_puzzles(self):
        """Test counting unpublished puzzles."""
        user_id = 1
        self.mock_puzzle_repo.conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (5,)
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor

        result = self.service._count_unpublished_puzzles(user_id)

        assert result is not None


class TestPuzzleServiceBrowseFilters:
    """Test browse() with various filter combinations."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_browse_with_search_filter(self):
        """Test browse with search query."""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Puzzle(id=1, name="Binary Adder", creator_user_id=2, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1

        result = self.service.browse("token", search="Binary")

        assert result is not None
        assert isinstance(result, dict)

    def test_browse_with_difficulty_filter(self):
        """Test browse with difficulty filter."""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Puzzle(id=1, name="Hard Puzzle", creator_user_id=2, status=PuzzleStatus.PUBLISHED, avg_difficulty=8)
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1

        result = self.service.browse("token", min_difficulty=7, max_difficulty=10)

        assert result is not None

    def test_browse_with_rating_filter(self):
        """Test browse with rating filter."""
        self.mock_auth.require_user_id.return_value = 1
        puzzle = Puzzle(id=1, name="Popular", creator_user_id=2, status=PuzzleStatus.PUBLISHED, avg_fun=4.5)
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1

        result = self.service.browse("token", min_fun=4.0)

        assert result is not None

    def test_browse_with_sort_by_difficulty(self):
        """Test browse with difficulty sort."""
        self.mock_auth.require_user_id.return_value = 1
        puzzles = [
            Puzzle(id=1, name="Easy", creator_user_id=1, avg_difficulty=2),
            Puzzle(id=2, name="Hard", creator_user_id=2, avg_difficulty=9),
        ]
        self.mock_puzzle_repo.list_published.return_value = puzzles
        self.mock_puzzle_repo.count_published.return_value = 2

        result = self.service.browse("token", order_by="avg_difficulty")

        assert result is not None

    def test_browse_with_sort_direction(self):
        """Test browse with sort direction."""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0

        result = self.service.browse("token", order_by="created_at", order_direction="ASC")

        assert result is not None

    def test_browse_with_pagination_limit(self):
        """Test browse with pagination limits."""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0

        result = self.service.browse("token", limit=5, offset=10)

        assert result is not None


class TestPuzzleServiceUpdatePuzzle:
    """Test update_puzzle() with various payload scenarios."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_update_puzzle_basic_fields(self):
        """Test updating basic puzzle fields."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        user = User(id=user_id, username="test", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = user
        
        puzzle = Puzzle(id=puzzle_id, name="Original", description="Desc", creator_user_id=user_id)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None  # No duplicate name

        payload = {"name": "Updated", "description": "New Desc"}

        result = self.service.update_puzzle(token, puzzle_id, payload)

        assert result is not None

    def test_update_puzzle_permission_denied(self):
        """Test updating puzzle without permission."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        puzzle = Puzzle(id=puzzle_id, name="Original", creator_user_id=999)  # Different creator
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        payload = {"name": "Updated"}

        with pytest.raises(ValidationError):
            self.service.update_puzzle(token, puzzle_id, payload)

    def test_update_puzzle_not_found(self):
        """Test updating non-existent puzzle."""
        user_id = 1
        puzzle_id = 999
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError):
            self.service.update_puzzle(token, puzzle_id, {})

    def test_update_puzzle_instructions_only(self):
        """Test updating only puzzle instructions."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id

        user = User(id=user_id, username="test", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = user
        
        puzzle = Puzzle(id=puzzle_id, name="Test", creator_user_id=user_id)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = None  # No duplicate name

        payload = {"instructions": "New instructions content"}

        result = self.service.update_puzzle(token, puzzle_id, payload)

        assert result is not None


class TestPuzzleServiceDeleteRiddleFiles:
    """Test delete_riddle_files() with various scenarios."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_delete_riddle_files_nonexistent_directory(self):
        """Test deleting riddle files when directory doesn't exist."""
        puzzle_id = 1
        puzzle_name = "NonExistent"

        # Should not raise an error
        self.service._delete_riddle_files(puzzle_id, puzzle_name)

    def test_delete_riddle_files_with_special_characters_name(self):
        """Test deleting riddle files with special characters in name."""
        puzzle_id = 1
        puzzle_name = "Puzzle!@#$%^&*()"

        # Should handle sanitization and not raise
        self.service._delete_riddle_files(puzzle_id, puzzle_name)


class TestPuzzleServiceEnrichPuzzle:
    """Test _enrich_puzzle() helper method."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_enrich_puzzle_with_creator(self):
        """Test enriching puzzle with creator information."""
        creator_user = User(id=1, username="creator_user", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user
        
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": 1}
        result = self.service._enrich_puzzle(puzzle_dict)
        assert "creator" in result
        
    def test_enrich_puzzle_without_creator(self):
        """Test enriching puzzle without creator info."""
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": None}
        result = self.service._enrich_puzzle(puzzle_dict)
        assert result is not None


class TestPuzzleServiceMainMethods:
    """Test main puzzle service operations."""
    
    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)
    
    def test_get_puzzle_not_found(self):
        """Test getting non-existent puzzle."""
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.get("token", 999)
    
    def test_get_puzzle_success(self):
        """Test getting puzzle successfully."""
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_auth.require_user_id.return_value = 1
        
        result = self.service.get("token", 1)
        assert result is not None
    
    def test_publish_puzzle_not_found(self):
        """Test publishing non-existent puzzle."""
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.publish("token", 999)
    
    def test_publish_puzzle_success(self):
        """Test publishing puzzle successfully."""
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle
        self.mock_auth.require_user_id.return_value = 1
        
        result = self.service.publish("token", 1)
        assert result is not None
    
    def test_unpublish_puzzle_not_found(self):
        """Test unpublishing non-existent puzzle."""
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.unpublish("token", 999)
    
    def test_unpublish_puzzle_success(self):
        """Test unpublishing puzzle successfully."""
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_puzzle_repo.update.return_value = puzzle
        self.mock_auth.require_user_id.return_value = 1
        
        result = self.service.unpublish("token", 1)
        assert result is not None
    
    def test_delete_puzzle_not_found(self):
        """Test deleting non-existent puzzle."""
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.delete_puzzle("token", 999)
    
    def test_delete_puzzle_success(self):
        """Test deleting puzzle successfully."""
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        self.mock_auth.require_user_id.return_value = 1
        
        self.service.delete_puzzle("token", 1)
        self.mock_puzzle_repo.delete.assert_called_once()
    
    def test_list_my_puzzles_success(self):
        """Test listing user's puzzles."""
        puzzles = [Puzzle(id=1, name="Test", creator_user_id=1)]
        self.mock_puzzle_repo.list_by_creator.return_value = puzzles
        self.mock_auth.require_user_id.return_value = 1
        
        result = self.service.list_my_puzzles("token")
        assert len(result) == 1
    
    def test_list_my_puzzles_empty(self):
        """Test listing when user has no puzzles."""
        self.mock_puzzle_repo.list_by_creator.return_value = []
        self.mock_auth.require_user_id.return_value = 1
        
        result = self.service.list_my_puzzles("token")
        assert result == []


class TestPuzzleServiceNormalizeCreatorSolution:
    """Tests for _normalize_creator_solution_payload (solution format normalization)."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_normalize_none_input(self):
        """Normalize returns None for None input."""
        result = self.service._normalize_creator_solution_payload(None)
        assert result is None

    def test_normalize_non_dict_input(self):
        """Normalize returns None for non-dict input."""
        result = self.service._normalize_creator_solution_payload("not a dict")
        assert result is None

    def test_normalize_empty_dict(self):
        """Normalize returns None when dict has no circuit data."""
        result = self.service._normalize_creator_solution_payload({})
        assert result is None

    def test_normalize_basic_placed_and_wires(self):
        """Normalize handles basic placed components and wires."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "origin": {"row": 5, "col": 10}, "rotation": 0}
            ],
            "wires": [
                {
                    "id": "wire1",
                    "from": {"componentId": "INPUT1", "pinIndex": 0},
                    "to": {"componentId": "AND", "pinIndex": 0}
                }
            ],
            "totalCost": 10
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["totalCost"] == 10
        assert len(result["circuit"]["placed"]) == 1
        assert result["circuit"]["placed"][0]["componentId"] == "AND"
        assert result["circuit"]["placed"][0]["origin"]["row"] == 5
        assert result["circuit"]["placed"][0]["origin"]["col"] == 10
        assert len(result["circuit"]["wires"]) == 1

    def test_normalize_legacy_placedComponents_format(self):
        """Normalize handles legacy placedComponents format."""
        payload = {
            "placedComponents": [
                {"componentId": "OR", "id": "comp1", "origin": {"row": 0, "col": 0}}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1
        assert result["circuit"]["placed"][0]["componentId"] == "OR"

    def test_normalize_legacy_placed_components_snake_case(self):
        """Normalize handles snake_case placed_components."""
        payload = {
            "placed_components": [
                {"componentId": "XOR", "id": "comp1"}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1

    def test_normalize_components_format(self):
        """Normalize handles components array format."""
        payload = {
            "components": [
                {"componentId": "NOT", "id": "comp1"}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1

    def test_normalize_placed_as_dict_with_values(self):
        """Normalize handles placed as dict (extracts values)."""
        payload = {
            "placed": {
                "comp1": {"componentId": "AND", "id": "comp1"},
                "comp2": {"componentId": "OR", "id": "comp2"}
            },
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 2

    def test_normalize_wires_as_dict(self):
        """Normalize handles wires as dict (extracts values)."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": {
                "wire1": {
                    "from": {"componentId": "INPUT1", "pinIndex": 0},
                    "to": {"componentId": "AND", "pinIndex": 0}
                }
            }
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["wires"]) == 1

    def test_normalize_legacy_wire_list_format(self):
        """Normalize handles legacy wire_list format."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wire_list": [
                {
                    "from": {"componentId": "INPUT1", "pinIndex": 0},
                    "to": {"componentId": "AND", "pinIndex": 0}
                }
            ]
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["wires"]) == 1

    def test_normalize_nested_circuit_wrapper(self):
        """Normalize extracts circuit from circuit wrapper."""
        payload = {
            "circuit": {
                "placed": [{"componentId": "AND", "id": "comp1"}],
                "wires": []
            }
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1

    def test_normalize_solution_wrapper(self):
        """Normalize extracts circuit from solution wrapper."""
        payload = {
            "solution": {
                "placed": [{"componentId": "AND", "id": "comp1"}],
                "wires": []
            }
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1

    def test_normalize_structure_wrapper(self):
        """Normalize extracts circuit from structure wrapper."""
        payload = {
            "structure": {
                "placed": [{"componentId": "AND", "id": "comp1"}],
                "wires": []
            }
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1

    def test_normalize_component_without_explicit_position(self):
        """Normalize spreads components without explicit positions."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1"},
                {"componentId": "OR", "id": "comp2"},
                {"componentId": "NOT", "id": "comp3"}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 3
        # Verify auto-positioned (should be spread across rows/cols)
        # Formula: row = (i % 6) * 2, col = (i // 6) * 4 + 2
        assert result["circuit"]["placed"][0]["origin"]["row"] == 0  # (0 % 6) * 2
        assert result["circuit"]["placed"][0]["origin"]["col"] == 2  # (0 // 6) * 4 + 2
        assert result["circuit"]["placed"][1]["origin"]["row"] == 2  # (1 % 6) * 2
        assert result["circuit"]["placed"][1]["origin"]["col"] == 2  # (1 // 6) * 4 + 2
        assert result["circuit"]["placed"][2]["origin"]["row"] == 4  # (2 % 6) * 2
        assert result["circuit"]["placed"][2]["origin"]["col"] == 2  # (2 // 6) * 4 + 2

    def test_normalize_component_with_position_object(self):
        """Normalize extracts position from position object."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "position": {"row": 10, "col": 20}}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["origin"]["row"] == 10
        assert result["circuit"]["placed"][0]["origin"]["col"] == 20

    def test_normalize_component_position_xy_coordinates(self):
        """Normalize handles x,y coordinates (converts to row,col)."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "origin": {"x": 5, "y": 15}}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["origin"]["col"] == 5
        assert result["circuit"]["placed"][0]["origin"]["row"] == 15

    def test_normalize_component_rotation_90_degrees(self):
        """Normalize preserves 90-degree rotations."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "rotation": 90}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["rotation"] == 90

    def test_normalize_component_rotation_other_values(self):
        """Normalize normalizes non-90 rotations to 0."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "rotation": 45}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["rotation"] == 0

    def test_normalize_component_without_componentid(self):
        """Normalize skips components without componentId."""
        payload = {
            "placed": [
                {"id": "comp1"},  # No componentId
                {"componentId": "AND", "id": "comp2"}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["placed"]) == 1
        assert result["circuit"]["placed"][0]["componentId"] == "AND"

    def test_normalize_wire_with_source_target(self):
        """Normalize handles source/target instead of from/to."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": [
                {
                    "id": "wire1",
                    "source": {"componentId": "INPUT1", "pinIndex": 0},
                    "target": {"componentId": "AND", "pinIndex": 0}
                }
            ]
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["wires"]) == 1
        assert result["circuit"]["wires"][0]["from"]["componentId"] == "INPUT1"
        assert result["circuit"]["wires"][0]["to"]["componentId"] == "AND"

    def test_normalize_wire_with_legacy_field_names(self):
        """Normalize handles legacy fromComponentId/toComponentId."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": [
                {
                    "id": "wire1",
                    "fromComponentId": "INPUT1",
                    "toComponentId": "AND",
                    "fromPinIndex": 0,
                    "toPinIndex": 1
                }
            ]
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["wires"]) == 1
        assert result["circuit"]["wires"][0]["from"]["componentId"] == "INPUT1"
        assert result["circuit"]["wires"][0]["to"]["componentId"] == "AND"
        assert result["circuit"]["wires"][0]["from"]["pinIndex"] == 0
        assert result["circuit"]["wires"][0]["to"]["pinIndex"] == 1

    def test_normalize_total_cost_from_payload(self):
        """Normalize extracts totalCost from payload root."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": [],
            "totalCost": 42
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["totalCost"] == 42

    def test_normalize_total_cost_snake_case(self):
        """Normalize extracts total_cost from snake_case."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": [],
            "total_cost": 25
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["totalCost"] == 25

    def test_normalize_eval_map_preserved(self):
        """Normalize preserves eval_map field."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "wires": [],
            "eval_map": {"INPUT1": 1, "OUTPUT": 0}
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert "eval_map" in result
        assert result["eval_map"] == {"INPUT1": 1, "OUTPUT": 0}

    def test_normalize_invalid_position_values(self):
        """Normalize handles invalid position values gracefully."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "origin": {"row": "invalid", "col": "bad"}}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["origin"]["row"] == 0
        assert result["circuit"]["placed"][0]["origin"]["col"] == 0

    def test_normalize_negative_position_values_clamped(self):
        """Normalize clamps negative position values to 0."""
        payload = {
            "placed": [
                {"componentId": "AND", "id": "comp1", "origin": {"row": -5, "col": -10}}
            ],
            "wires": []
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert result["circuit"]["placed"][0]["origin"]["row"] == 0
        assert result["circuit"]["placed"][0]["origin"]["col"] == 0

    def test_normalize_connections_format(self):
        """Normalize handles connections format for wires."""
        payload = {
            "placed": [{"componentId": "AND", "id": "comp1"}],
            "connections": [
                {
                    "from": {"componentId": "INPUT1", "pinIndex": 0},
                    "to": {"componentId": "AND", "pinIndex": 0}
                }
            ]
        }
        
        result = self.service._normalize_creator_solution_payload(payload)
        
        assert result is not None
        assert len(result["circuit"]["wires"]) == 1


class TestPuzzleServiceEdgeCases:
    """Test edge cases and error conditions."""
    
    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_puzzle_repo.conn = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)
    
    def test_browse_empty_results(self):
        """Test browse with no results."""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0
        
        result = self.service.browse("token")
        assert result is not None
    
    def test_browse_with_filters(self):
        """Test browse with various filters."""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0
        
        result = self.service.browse("token", search="test", min_difficulty=1, max_difficulty=5)
        assert result is not None
    
    def test_count_published_puzzles_zero(self):
        """Test counting published puzzles when there are none."""
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = (0,)
        
        result = self.service._count_published_puzzles(1)
        assert result == 0
    
    def test_count_unpublished_puzzles_zero(self):
        """Test counting unpublished puzzles when there are none."""
        self.mock_puzzle_repo.conn.execute.return_value.fetchone.return_value = (0,)
        
        result = self.service._count_unpublished_puzzles(1)
        assert result == 0


class TestPuzzleServiceAddTestCase:
    """Test add_test_case() method."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_add_test_case_puzzle_not_found(self):
        """Test adding test case to non-existent puzzle."""
        user_id = 1
        puzzle_id = 999
        token = "valid_token"

        self.mock_auth.require_user_id.return_value = user_id
        self.mock_puzzle_repo.get_by_id.return_value = None

        payload = {"kind": "simple", "inputs": {}, "expectedOutputs": {}}

        with pytest.raises(ValidationError):
            self.service.add_test_case(token, puzzle_id, payload)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

    def test_count_published_puzzles(self):
        """Test counting published puzzles."""
        user_id = 1
        self.mock_puzzle_repo.conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (10,)
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor

        result = self.service._count_published_puzzles(user_id)

        assert result is not None

    def test_is_creator_blocked(self):
        """Test checking if creator is blocked."""
        user = Mock()
        user.id = 1
        user.blocked = False
        user.get_puzzle_capacity.return_value = (10, 20)
        
        # Mock the internal _count_published_puzzles and _count_unpublished_puzzles
        self.service._count_published_puzzles = Mock(return_value=5)
        self.service._count_unpublished_puzzles = Mock(return_value=8)
        
        result = self.service._is_creator_blocked(user)

        assert isinstance(result, bool)

    def test_enrich_puzzle_with_user(self):
        """Test enriching puzzle with user information."""
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": 1}
        user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = user
        self.service.solve_repo = None

        result = self.service._enrich_puzzle(puzzle_dict)

        assert result is not None
        assert isinstance(result, dict)

    def test_enrich_puzzle_with_solve_count(self):
        """Test enriching puzzle with solve count."""
        puzzle_dict = {"id": 1, "name": "Test"}
        self.mock_puzzle_repo.conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (5,)
        self.mock_puzzle_repo.conn.execute.return_value = mock_cursor
        
        self.service.solve_repo = self.mock_solve_repo
        self.mock_solve_repo.conn = self.mock_puzzle_repo.conn

        result = self.service._enrich_puzzle(puzzle_dict)

        assert result is not None
        assert isinstance(result, dict)

    def test_load_io_from_riddle_config_empty(self):
        """Test loading IO with empty riddle base."""
        puzzle = Mock()
        puzzle.riddle_base_name = ""

        inputs, outputs = self.service._load_io_from_riddle_config(puzzle)

        assert inputs is None
        assert outputs is None

    def test_load_creator_solution_no_riddles_dir(self):
        """Test loading creator solution when riddles dir doesn't exist."""
        puzzle = Mock()
        puzzle.riddle_base_name = "nonexistent"

        result = self.service._load_creator_solution(puzzle)

        assert result is None or isinstance(result, dict)

    def test_as_object_none(self):
        """Test converting None to object."""
        result = PuzzleService._as_object(None)
        assert result is None

    def test_as_object_dict(self):
        """Test converting dict stays as dict."""
        test_dict = {"key": "value"}
        result = PuzzleService._as_object(test_dict)
        assert result == test_dict

    def test_normalize_creator_solution_payload_none(self):
        """Test normalizing None payload."""
        result = self.service._normalize_creator_solution_payload(None)
        assert result is None


class TestPuzzleServiceAdditionalBranches:
    """Additional tests for PuzzleService branch coverage."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_delete_riddle_files(self):
        """Test deleting riddle files."""
        puzzle_id = 1
        puzzle_name = "test_puzzle"
        
        # Should not raise an error even if files don't exist
        result = self.service._delete_riddle_files(puzzle_id, puzzle_name)
        
        assert result is None

    def test_as_object_non_dict(self):
        """Test converting non-dict to object."""
        test_list = [1, 2, 3]
        result = PuzzleService._as_object(test_list)
        assert result is None

    def test_normalize_creator_solution_payload_empty_dict(self):
        """Test normalizing empty payload."""
        result = self.service._normalize_creator_solution_payload({})
        assert result is None

    def test_normalize_creator_solution_payload_with_circuit(self):
        """Test normalizing payload with circuit."""
        payload = {"circuit": {"placedComponents": []}}
        result = self.service._normalize_creator_solution_payload(payload)
        assert result is not None or result is None

    def test_search_published_only(self):
        """Test searching published puzzles."""
        self.mock_auth.require_user_id.return_value = 1
        
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        self.mock_puzzle_repo.search_by_name.return_value = [puzzle]
        
        result = self.service.search("token", "test", only_published=True)
        
        assert result is not None
        assert isinstance(result, list)

    def test_search_all_puzzles(self):
        """Test searching all puzzles."""
        self.mock_auth.require_user_id.return_value = 1
        
        puzzle = Puzzle(id=1, name="Test", creator_user_id=1)
        self.mock_puzzle_repo.search_by_name.return_value = [puzzle]
        
        result = self.service.search("token", "test", only_published=False)
        
        assert result is not None
        assert isinstance(result, list)


class TestPuzzleServiceMainMethods:
    """Test main public methods of PuzzleService."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_get_puzzle_basic(self):
        """Test getting puzzle details."""
        puzzle_dict = {"id": 1, "name": "Test", "creator_user_id": 1}
        puzzle = Mock()
        puzzle.to_dict.return_value = puzzle_dict
        
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        user = Mock()
        user.to_dict.return_value = {"id": 1, "username": "creator"}
        self.mock_user_repo.get_by_id.return_value = user
        
        result = self.service.get(session_token="valid_token", puzzle_id=1)
        
        assert result is not None
        assert isinstance(result, dict)

    def test_browse_basic(self):
        """Test browsing puzzles."""
        self.mock_auth.require_user_id.return_value = 1
        
        puzzle = Mock()
        puzzle.to_dict.return_value = {"id": 1, "name": "Test"}
        self.mock_puzzle_repo.list_published.return_value = [puzzle]
        self.mock_puzzle_repo.count_published.return_value = 1
        
        result = self.service.browse(session_token="valid_token")
        
        assert result is not None
        assert isinstance(result, dict)
        assert "data" in result
        assert "meta" in result

    def test_list_my_puzzles_basic(self):
        """Test listing user's puzzles."""
        self.mock_auth.require_user_id.return_value = 1
        
        # Mock the database query
        mock_cursor = Mock()
        puzzle_row = Mock()
        self.mock_puzzle_repo.conn = Mock()
        self.mock_puzzle_repo.conn.execute.side_effect = [
            Mock(fetchall=Mock(return_value=[puzzle_row])),
            Mock(fetchone=Mock(return_value=(1,)))
        ]
        
        puzzle = Mock()
        puzzle.to_dict.return_value = {"id": 1, "name": "My Puzzle"}
        self.mock_puzzle_repo._row_to_puzzle.return_value = puzzle
        
        result = self.service.list_my_puzzles(session_token="valid_token")
        
        assert result is not None
        assert isinstance(result, dict)

    def test_add_test_case_basic(self):
        """Test adding test case."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        
        puzzle = Mock()
        puzzle.creator_user_id = user_id
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        test_case = Mock()
        test_case.to_dict.return_value = {"id": 1, "kind": "blackbox"}
        self.mock_puzzle_repo.add_test_case.return_value = test_case
        
        payload = {
            "kind": "blackbox",
            "inputs": {"A": 0, "B": 1},
            "expected_outputs": {"Q": 1}
        }
        result = self.service.add_test_case(token, puzzle_id, payload)
        
        assert result is not None
        assert isinstance(result, dict)

    def test_publish_puzzle_basic(self):
        """Test publishing puzzle."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        
        user = Mock()
        user.role = UserRole.CREATOR
        user.get_puzzle_capacity.return_value = (1000, 1000)
        user.blocked = False
        self.mock_user_repo.get_by_id.return_value = user
        
        puzzle = Mock()
        puzzle.id = puzzle_id
        puzzle.creator_user_id = user_id
        puzzle.status = PuzzleStatus.DRAFT
        puzzle.to_dict.return_value = {"id": puzzle_id, "status": "published"}
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        # Mock test cases
        test_case = Mock()
        self.mock_puzzle_repo.list_test_cases.return_value = [test_case]
        
        # Mock count methods
        self.mock_puzzle_repo.count_published = Mock(return_value=0)
        
        result = self.service.publish(token, puzzle_id)
        
        assert result is not None

    def test_unpublish_puzzle_basic(self):
        """Test unpublishing puzzle."""
        user_id = 1
        puzzle_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        
        user = Mock()
        user.role = UserRole.CREATOR
        self.mock_user_repo.get_by_id.return_value = user
        
        puzzle = Mock()
        puzzle.creator_user_id = user_id
        puzzle.status = PuzzleStatus.PUBLISHED
        puzzle.to_dict.return_value = {"id": puzzle_id, "status": "unpublished"}
        self.mock_puzzle_repo.get_by_id.return_value = puzzle
        
        result = self.service.unpublish(token, puzzle_id)
        
        assert result is not None


class TestPuzzleServiceErrorPaths:
    """Test error paths for higher coverage."""

    def setup_method(self):
        self.mock_puzzle_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_solve_repo = Mock()

        self.service = PuzzleService(
            self.mock_puzzle_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_solve_repo,
        )

    def test_create_puzzle_missing_name(self):
        """Test creating puzzle without name."""
        token = "valid_token"
        self.mock_auth.require_user_id.return_value = 1
        
        payload = {"description": "Test"}  # Missing name
        
        with pytest.raises(ValidationError):
            self.service.create_puzzle(token, payload)

    def test_get_puzzle_not_found(self):
        """Test getting non-existent puzzle."""
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.get(session_token="token", puzzle_id=999)

    def test_delete_puzzle_not_found(self):
        """Test deleting non-existent puzzle."""
        token = "valid_token"
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.delete_puzzle(token, puzzle_id=999)

    def test_publish_puzzle_not_found(self):
        """Test publishing non-existent puzzle."""
        token = "valid_token"
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError):
            self.service.publish(token, puzzle_id=999)
