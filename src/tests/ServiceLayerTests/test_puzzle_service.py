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
import json


class TestPuzzleServiceCreation:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
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
        self.mock_puzzle_repo.list_published.assert_called_once_with(limit=50, offset=0)
        self.mock_puzzle_repo.count_published.assert_called_once()

    def test_browse_with_pagination(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_puzzle_repo.list_published.return_value = []
        self.mock_puzzle_repo.count_published.return_value = 0

        self.service.browse("valid_token", limit=100, offset=50)

        self.mock_puzzle_repo.list_published.assert_called_once_with(limit=100, offset=50)

    def test_browse_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.browse("invalid_token")


class TestPuzzleServiceSearch:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
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
        assert "creator required" in str(exc_info.value)

    def test_create_puzzle_missing_name(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        payload = {"name": ""}

        with pytest.raises(ValidationError) as exc_info:
            self.service.create_puzzle("valid_token", payload)
        assert "name required" in str(exc_info.value)

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
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_publish_success_by_creator(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

        result = self.service.publish("valid_token", 1)

        assert result["status"] == PuzzleStatus.PUBLISHED.value
        self.mock_puzzle_repo.update.assert_called_once()

    def test_publish_success_by_admin(self):
        self.mock_auth.require_user_id.return_value = 1
        admin_user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.mock_user_repo.get_by_id.return_value = admin_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=2, status=PuzzleStatus.DRAFT)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

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


class TestPuzzleServiceUnpublish:
    def setup_method(self):
        self.mock_puzzle_repo = Mock(spec=PuzzleRepo)
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.service = PuzzleService(self.mock_puzzle_repo, self.mock_user_repo, self.mock_auth)

    def test_unpublish_success(self):
        self.mock_auth.require_user_id.return_value = 1
        creator_user = User(id=1, username="creator", role=UserRole.CREATOR)
        self.mock_user_repo.get_by_id.return_value = creator_user

        puzzle = Puzzle(id=1, name="Test", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        self.mock_puzzle_repo.get_by_id.return_value = puzzle

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