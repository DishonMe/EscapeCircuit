"""Targeted coverage tests for PuzzleService — focuses on under-covered branches,
edge cases, and error paths in static-like helpers and the rich `get`/`update`
flows. Adds branch coverage rather than statement-only coverage."""

import json
import pathlib
import sqlite3
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch, MagicMock

import pytest

from Backend.ServiceLayer.PuzzleService import PuzzleService
from Backend.DomainLayer.Puzzle import Puzzle
from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import (
    UserRole,
    PuzzleStatus,
    GateType,
    TestCaseKind,
    PuzzleDifficulty,
)
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User
from Backend.PersistantLayer.PuzzleRepo import PuzzleRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.PersistantLayer.SolveRepo import SolveRepo
from Backend.ServiceLayer.AuthService import AuthService


def _make_service(arsenal_service=None, with_solve=True):
    mock_puzzle_repo = Mock(spec=PuzzleRepo)
    mock_puzzle_repo.conn = Mock()
    mock_user_repo = Mock(spec=UserRepo)
    mock_auth = Mock(spec=AuthService)
    mock_solve_repo = None
    if with_solve:
        mock_solve_repo = Mock(spec=SolveRepo)
        mock_solve_repo.conn = Mock()
    svc = PuzzleService(
        mock_puzzle_repo,
        mock_user_repo,
        mock_auth,
        solve_repo=mock_solve_repo,
        arsenal_service=arsenal_service,
    )
    return svc, mock_puzzle_repo, mock_user_repo, mock_auth, mock_solve_repo


# ---------------------------------------------------------------------------
# Static helpers — _slugify_puzzle_name, _sanitize_puzzle_name, _as_object
# ---------------------------------------------------------------------------

class TestStaticHelpers:
    def test_slugify_strips_special_chars(self):
        assert PuzzleService._slugify_puzzle_name("Hello, World!") == "hello_world"

    def test_slugify_collapses_spaces_and_hyphens(self):
        assert PuzzleService._slugify_puzzle_name("foo  bar--baz") == "foo_bar_baz"

    def test_slugify_strips_leading_trailing_underscores(self):
        assert PuzzleService._slugify_puzzle_name("--foo--") == "foo"

    def test_slugify_handles_none(self):
        assert PuzzleService._slugify_puzzle_name(None) == ""

    def test_sanitize_preserves_internal_underscores(self):
        assert PuzzleService._sanitize_puzzle_name("My Puzzle") == "my_puzzle"

    def test_as_object_from_dict(self):
        d = {"a": 1}
        assert PuzzleService._as_object(d) is d

    def test_as_object_from_json_string(self):
        assert PuzzleService._as_object('{"a": 1}') == {"a": 1}

    def test_as_object_invalid_json(self):
        assert PuzzleService._as_object("not-json") is None

    def test_as_object_json_non_dict(self):
        # Valid JSON but not a dict
        assert PuzzleService._as_object("[1, 2, 3]") is None

    def test_as_object_other_types(self):
        assert PuzzleService._as_object(42) is None
        assert PuzzleService._as_object(None) is None


# ---------------------------------------------------------------------------
# _is_admin — branch coverage on UserRole vs string
# ---------------------------------------------------------------------------

class TestIsAdmin:
    def test_is_admin_enum(self):
        assert PuzzleService._is_admin(UserRole.ADMIN) is True

    def test_is_admin_enum_non_admin(self):
        assert PuzzleService._is_admin(UserRole.CREATOR) is False

    def test_is_admin_string(self):
        assert PuzzleService._is_admin("admin") is True
        assert PuzzleService._is_admin("  ADMIN  ") is True

    def test_is_admin_string_non_admin(self):
        assert PuzzleService._is_admin("creator") is False


# ---------------------------------------------------------------------------
# _normalize_creator_solution_payload — many branches
# ---------------------------------------------------------------------------

class TestNormalizeCreatorSolution:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_non_dict_payload_returns_none(self):
        assert self.svc._normalize_creator_solution_payload(None) is None
        assert self.svc._normalize_creator_solution_payload("string") is None
        assert self.svc._normalize_creator_solution_payload([1, 2]) is None

    def test_empty_dict_returns_none(self):
        # No components / wires anywhere → normalized is None
        assert self.svc._normalize_creator_solution_payload({}) is None

    def test_circuit_nested(self):
        payload = {
            "circuit": {
                "placed": [
                    {"componentId": "AND", "origin": {"row": 1, "col": 2}, "id": "g1"}
                ],
                "wires": [
                    {
                        "id": "w1",
                        "from": {"componentId": "g1", "pinIndex": 0},
                        "to": {"componentId": "OUT", "pinIndex": 0},
                    }
                ],
                "totalCost": 5,
            }
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized is not None
        assert normalized["totalCost"] == 5
        assert len(normalized["circuit"]["placed"]) == 1
        assert normalized["circuit"]["placed"][0]["origin"] == {"row": 1, "col": 2}
        assert len(normalized["circuit"]["wires"]) == 1

    def test_placed_components_field_used(self):
        payload = {
            "placedComponents": [{"type": "OR", "row": 3, "col": 4}],
            "connections": [
                {"source": {"componentId": "g1"}, "target": {"componentId": "g2"}}
            ],
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized is not None
        assert normalized["circuit"]["placed"][0]["componentId"] == "OR"
        assert normalized["circuit"]["placed"][0]["origin"]["row"] == 3
        assert len(normalized["circuit"]["wires"]) == 1

    def test_placed_as_dict_values(self):
        payload = {
            "placed": {"a": {"gateType": "AND", "x": 0, "y": 0}, "b": {"name": "OR"}},
            "wires": {"w1": {"from": {"id": "a"}, "to": {"id": "b"}}},
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized is not None
        # Both placed components present
        assert len(normalized["circuit"]["placed"]) == 2

    def test_components_without_position_get_spread(self):
        payload = {
            "components": [
                {"componentId": "AND"},
                {"componentId": "OR"},
            ]
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized is not None
        # When no explicit position, indices are spread deterministically
        assert normalized["circuit"]["placed"][0]["origin"] != {"row": 0, "col": 0} or \
               normalized["circuit"]["placed"][1]["origin"] != {"row": 0, "col": 0}

    def test_components_with_invalid_position_default_to_zero(self):
        payload = {
            "components": [
                {"componentId": "AND", "row": "not-a-number", "col": "bad"}
            ]
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        # Should not raise — gracefully falls back
        assert normalized is not None
        assert normalized["circuit"]["placed"][0]["origin"] == {"row": 0, "col": 0}

    def test_negative_position_clamped(self):
        payload = {
            "components": [{"componentId": "AND", "row": -5, "col": -10}]
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["circuit"]["placed"][0]["origin"] == {"row": 0, "col": 0}

    def test_rotation_90_preserved(self):
        payload = {"components": [{"componentId": "AND", "row": 0, "col": 0, "rotation": 90}]}
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["circuit"]["placed"][0]["rotation"] == 90

    def test_rotation_invalid_defaults_zero(self):
        payload = {"components": [{"componentId": "AND", "row": 0, "col": 0, "rotation": "spin"}]}
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["circuit"]["placed"][0]["rotation"] == 0

    def test_component_without_id_skipped(self):
        payload = {"components": [{"row": 0, "col": 0}, {"componentId": "AND", "row": 1, "col": 1}]}
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert len(normalized["circuit"]["placed"]) == 1

    def test_non_object_component_skipped(self):
        payload = {"components": ["not-an-object", {"componentId": "AND", "row": 0, "col": 0}]}
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert len(normalized["circuit"]["placed"]) == 1

    def test_wire_without_ids_skipped(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "wires": [
                {"from": {}, "to": {}},
                {"from": {"componentId": "a"}, "to": {"componentId": "b"}},
            ],
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert len(normalized["circuit"]["wires"]) == 1

    def test_non_object_wire_skipped(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "wires": ["bad", {"from": {"id": "a"}, "to": {"id": "b"}}],
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert len(normalized["circuit"]["wires"]) == 1

    def test_wire_pin_invalid_defaults_zero(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "wires": [
                {
                    "from": {"id": "a", "pinIndex": "x"},
                    "to": {"id": "b", "pinIndex": "y"},
                }
            ],
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["circuit"]["wires"][0]["from"]["pinIndex"] == 0
        assert normalized["circuit"]["wires"][0]["to"]["pinIndex"] == 0

    def test_total_cost_invalid_defaults_zero(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "totalCost": "abc",
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["totalCost"] == 0

    def test_total_cost_from_circuit_total_cost_snake(self):
        payload = {
            "circuit": {
                "placed": [{"componentId": "AND", "row": 0, "col": 0}],
                "total_cost": 42,
            }
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized["totalCost"] == 42

    def test_eval_map_propagated_if_dict(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "eval_map": {"a": "b"},
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert normalized.get("eval_map") == {"a": "b"}

    def test_eval_map_non_dict_omitted(self):
        payload = {
            "components": [{"componentId": "AND", "row": 0, "col": 0}],
            "eval_map": "not-a-dict",
        }
        normalized = self.svc._normalize_creator_solution_payload(payload)
        assert "eval_map" not in normalized


# ---------------------------------------------------------------------------
# _load_io_from_riddle_config and _load_creator_solution — filesystem access
# ---------------------------------------------------------------------------

class TestLoadFromRiddleFiles:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_load_io_blank_base_name(self):
        puzzle = SimpleNamespace(riddle_base_name="")
        assert self.svc._load_io_from_riddle_config(puzzle) == (None, None)

    def test_load_io_none_base_name(self):
        puzzle = SimpleNamespace(riddle_base_name=None)
        assert self.svc._load_io_from_riddle_config(puzzle) == (None, None)

    def test_load_io_missing_file_returns_nones(self):
        puzzle = SimpleNamespace(riddle_base_name="does_not_exist_123")
        result = self.svc._load_io_from_riddle_config(puzzle)
        assert result == (None, None)

    def test_load_io_from_real_riddle_file(self, tmp_path, monkeypatch):
        # Set up a fake riddles dir
        riddle_name = "rb_test"
        riddle_dir = tmp_path / "riddles" / riddle_name
        riddle_dir.mkdir(parents=True)
        config = {"puzzle": {"inputs": ["A", "B"], "outputs": ["S", "C"]}}
        (riddle_dir / f"{riddle_name}_config.json").write_text(json.dumps(config))

        # Patch __file__ so root_dir computes to tmp_path
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=riddle_name)
            inputs, outputs = self.svc._load_io_from_riddle_config(puzzle)
        assert inputs == ["A", "B"]
        assert outputs == ["S", "C"]

    def test_load_io_with_bad_json(self, tmp_path):
        riddle_name = "rb_bad"
        riddle_dir = tmp_path / "riddles" / riddle_name
        riddle_dir.mkdir(parents=True)
        (riddle_dir / f"{riddle_name}_config.json").write_text("not-json")

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=riddle_name)
            result = self.svc._load_io_from_riddle_config(puzzle)
        # Should not raise — returns (None, None) on parse failure
        assert result == (None, None)

    def test_load_creator_solution_no_dir(self, tmp_path):
        # Point to a path with no "riddles" dir
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            assert self.svc._load_creator_solution(SimpleNamespace(riddle_base_name="x")) is None

    def test_load_creator_solution_primary_path_present(self, tmp_path):
        riddle_name = "rb_primary"
        riddles_root = tmp_path / "riddles"
        riddle_dir = riddles_root / riddle_name
        riddle_dir.mkdir(parents=True)
        payload = {"placed": [{"componentId": "AND", "row": 0, "col": 0}]}
        (riddle_dir / f"{riddle_name}_sample_solution.json").write_text(json.dumps(payload))

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=riddle_name, id=1, name="Foo")
            result = self.svc._load_creator_solution(puzzle)
        assert result == payload

    def test_load_creator_solution_legacy_flat(self, tmp_path):
        riddle_name = "rb_flat"
        riddles_root = tmp_path / "riddles"
        riddles_root.mkdir()
        payload = {"placed": [{"componentId": "AND", "row": 0, "col": 0}]}
        (riddles_root / f"{riddle_name}_sample_solution.json").write_text(json.dumps(payload))

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=riddle_name, id=1, name="X")
            result = self.svc._load_creator_solution(puzzle)
        assert result == payload

    def test_load_creator_solution_id_pattern(self, tmp_path):
        # No riddle_base_name; uses id + slug fallback
        riddles_root = tmp_path / "riddles"
        name = "My Puzzle"
        slug = "my_puzzle"
        base_name = f"riddle_5_{slug}"
        (riddles_root / base_name).mkdir(parents=True)
        payload = {"placed": [{"componentId": "AND", "row": 0, "col": 0}]}
        (riddles_root / base_name / f"{base_name}_sample_solution.json").write_text(
            json.dumps(payload)
        )

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=None, id=5, name=name)
            result = self.svc._load_creator_solution(puzzle)
        assert result == payload

    def test_load_creator_solution_bad_payload_skipped(self, tmp_path):
        riddle_name = "rb_bad"
        riddles_root = tmp_path / "riddles"
        riddle_dir = riddles_root / riddle_name
        riddle_dir.mkdir(parents=True)
        (riddle_dir / f"{riddle_name}_sample_solution.json").write_text("not-json")

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            puzzle = SimpleNamespace(riddle_base_name=riddle_name, id=1, name="A")
            assert self.svc._load_creator_solution(puzzle) is None


# ---------------------------------------------------------------------------
# _delete_riddle_files
# ---------------------------------------------------------------------------

class TestDeleteRiddleFiles:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_delete_no_riddles_dir(self, tmp_path):
        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            # No exception — just returns
            self.svc._delete_riddle_files(1, "foo")

    def test_delete_existing_dir(self, tmp_path):
        riddles_root = tmp_path / "riddles"
        target = riddles_root / "riddle_5_my_puzzle"
        target.mkdir(parents=True)
        (target / "stuff.txt").write_text("x")

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            self.svc._delete_riddle_files(5, "My Puzzle")
        assert not target.exists()

    def test_delete_legacy_pattern_fallback(self, tmp_path):
        riddles_root = tmp_path / "riddles"
        # Different id, but slug matches → caught by legacy regex
        legacy = riddles_root / "riddle_99_my_puzzle"
        legacy.mkdir(parents=True)

        fake_file = tmp_path / "src" / "Backend" / "ServiceLayer" / "PuzzleService.py"
        fake_file.parent.mkdir(parents=True)
        fake_file.write_text("")
        with patch.object(pathlib.Path, "resolve", lambda self: fake_file):
            # id=5 won't match exactly, but legacy pattern finds it
            self.svc._delete_riddle_files(5, "My Puzzle")
        assert not legacy.exists()


# ---------------------------------------------------------------------------
# list_my_puzzles
# ---------------------------------------------------------------------------

class TestListMyPuzzles:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, self.solve_repo = _make_service()

    def test_list_basic(self):
        self.auth.require_user_id.return_value = 7
        puzzle = Puzzle(id=1, name="P", creator_user_id=7)
        self.repo._row_to_puzzle.return_value = puzzle
        # mock cursor chains
        rows = [("row1",)]
        execute_mock = self.repo.conn.execute
        # fetchall for puzzles, fetchone for count
        execute_mock.side_effect = [
            Mock(fetchall=lambda: rows),
            Mock(fetchone=lambda: (1,)),
        ]
        self.user_repo.get_by_id.return_value = None  # for _enrich_puzzle

        result = self.svc.list_my_puzzles("tok")
        assert result["meta"]["total"] == 1
        assert result["meta"]["page"] == 1
        assert result["meta"]["totalPages"] == 1
        assert len(result["data"]) == 1

    def test_list_with_search(self):
        self.auth.require_user_id.return_value = 7
        puzzle = Puzzle(id=2, name="A", creator_user_id=7)
        self.repo._row_to_puzzle.return_value = puzzle
        execute_mock = self.repo.conn.execute
        execute_mock.side_effect = [
            Mock(fetchall=lambda: [("r",)]),
            Mock(fetchone=lambda: (1,)),
        ]
        self.user_repo.get_by_id.return_value = None

        result = self.svc.list_my_puzzles("tok", search="adder")
        # Verify search was applied (LIKE clause)
        first_call_args = execute_mock.call_args_list[0]
        assert "LIKE" in first_call_args[0][0]
        # search param appended to params list
        assert "%adder%" in first_call_args[0][1]

    def test_list_unauthorized(self):
        self.auth.require_user_id.side_effect = ValidationError("nope")
        with pytest.raises(ValidationError):
            self.svc.list_my_puzzles("bad")


# ---------------------------------------------------------------------------
# get — owner/admin paths, gate_limits, medal distribution, arsenal
# ---------------------------------------------------------------------------

class TestGetExtended:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, self.solve_repo = _make_service()
        self.user = User(id=1, username="u", role=UserRole.CREATOR)
        self.puzzle = Puzzle(
            id=10,
            name="P",
            creator_user_id=1,
            default_gate_set={GateType.AND, GateType.OR},
            allow_arsenal=True,
            allowed_arsenal_component_ids=[],
        )
        self.auth.require_user_id.return_value = 1
        self.user_repo.get_by_id.return_value = self.user
        self.repo.get_by_id.return_value = self.puzzle

    def _stub_solve_repo_counts(self):
        # Set up the solve_repo.conn.execute to return chained mocks
        # 4 calls: solvedCount, timesSaved, medalDistribution, (plus enrich for puzzles list)
        cnt_call = Mock()
        cnt_call.fetchone.return_value = (3,)
        saved_call = Mock()
        saved_call.fetchone.return_value = (5,)
        medal_call = Mock()
        medal_call.fetchall.return_value = [(0, 1), (1, 2), (2, 3), (3, 4)]
        self.solve_repo.conn.execute.side_effect = [cnt_call, saved_call, medal_call]

    def test_get_as_owner_loads_creator_solution(self, tmp_path):
        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert "creator_solution" in d
        assert d["creator_solution"] is None
        assert d["creator_solution_meta"]["available"] is False

    def test_get_as_owner_with_solution_loaded(self):
        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        raw_payload = {"placed": [{"componentId": "AND", "row": 0, "col": 0}]}
        with patch.object(self.svc, "_load_creator_solution", return_value=raw_payload):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert d["creator_solution"] is not None
        assert d["creator_solution_meta"]["available"] is True
        assert d["creator_solution_meta"]["raw_found"] is True

    def test_get_non_owner_no_creator_solution(self):
        # Different user, not admin
        other_user = User(id=99, username="other", role=UserRole.SOLVER)
        self.user_repo.get_by_id.return_value = other_user
        self.auth.require_user_id.return_value = 99
        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
            d = self.svc.get("tok", 10)
        assert "creator_solution" not in d

    def test_get_not_found_raises(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            self.svc.get("tok", 10)

    def test_get_with_gate_limits_from_test_cases(self):
        tc = PuzzleTestCase(
            id=1, puzzle_id=10,
            kind=TestCaseKind.GATE_LIMIT,
            inputs={}, expected_outputs={},
            gate_name="AND", gate_limit=2,
        )
        self.repo.list_test_cases.return_value = [tc]
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert d["gateLimits"]["AND"] == 2
        # OR was in allowed but no limit set
        assert d["gateLimits"]["OR"] is None

    def test_get_gate_limits_exception_falls_back(self):
        self.repo.list_test_cases.side_effect = [Exception("boom"), []]
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        # All allowed gates set to None
        assert d["gateLimits"] == {"AND": None, "OR": None}

    def test_get_inputs_outputs_from_test_cases(self):
        tc = PuzzleTestCase(
            id=1, puzzle_id=10,
            kind=TestCaseKind.WHITEBOX,
            inputs={"A": 0, "B": 1},
            expected_outputs={"Y": 1},
        )
        self.repo.list_test_cases.return_value = [tc]
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert set(d["inputs"]) == {"A", "B"}
        assert d["outputs"] == ["Y"]
        assert len(d["test_cases"]) == 1

    def test_get_inputs_outputs_from_streams(self):
        tc = PuzzleTestCase(
            id=1, puzzle_id=10,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[{"A": 0, "B": 1}, {"A": 1, "B": 0}],
            expected_output_stream={"Y": [1, 0]},
        )
        self.repo.list_test_cases.return_value = [tc]
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        # Inputs derived from first input_stream dict
        assert set(d["inputs"]) == {"A", "B"}
        # Outputs derived from expected_output_stream dict keys
        assert d["outputs"] == ["Y"]

    def test_get_io_fallback_from_config(self):
        # No test cases — falls back to riddle config inputs/outputs
        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(["X"], ["Y"])):
                d = self.svc.get("tok", 10)
        assert d["inputs"] == ["X"]
        assert d["outputs"] == ["Y"]

    def test_get_with_arsenal_service(self):
        arsenal = Mock()
        arsenal.get_custom_pieces_for_puzzle.return_value = [{"id": "c1"}]
        arsenal.get_arsenal_pieces_by_ids.return_value = [{"id": "a1"}]
        arsenal.get_user_arsenal_filtered_by_gates.return_value = [{"id": "u1"}]
        self.svc.arsenal_service = arsenal
        self.puzzle.allowed_arsenal_component_ids = ["a1"]

        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert any(c["id"] == "c1" for c in d["customComponents"])
        assert any(c["id"] == "a1" for c in d["sharedArsenalComponents"])
        assert any(c["id"] == "u1" for c in d["solverArsenalComponents"])

    def test_get_with_arsenal_exception(self):
        arsenal = Mock()
        arsenal.get_custom_pieces_for_puzzle.side_effect = Exception("oops")
        self.svc.arsenal_service = arsenal
        self.repo.list_test_cases.return_value = []
        self._stub_solve_repo_counts()
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        # Fallback path returns empty lists
        assert d["specialComponents"] == []

    def test_get_solve_repo_failures_default_to_empty(self):
        self.repo.list_test_cases.return_value = []
        # Both timesSaved and medalDistribution raise
        bad = Mock()
        bad.fetchone.side_effect = Exception("db")
        bad.fetchall.side_effect = Exception("db")
        # solvedCount fails inside _enrich_puzzle (Exception caught)
        # but timesSaved and medalDistribution need separate executes
        self.solve_repo.conn.execute.side_effect = [bad, bad, bad]
        with patch.object(self.svc, "_load_creator_solution", return_value=None):
            with patch.object(self.svc, "_load_io_from_riddle_config", return_value=(None, None)):
                d = self.svc.get("tok", 10)
        assert d["timesSaved"] == 0
        assert d["medalDistribution"] == {"none": 0, "bronze": 0, "silver": 0, "gold": 0}


# ---------------------------------------------------------------------------
# _enrich_puzzle — covers solvedCount path
# ---------------------------------------------------------------------------

class TestEnrichPuzzle:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, self.solve_repo = _make_service()

    def test_enrich_attaches_creator(self):
        user = User(id=5, username="creator")
        self.user_repo.get_by_id.return_value = user
        d = {"creator_user_id": 5, "id": None}
        result = self.svc._enrich_puzzle(d)
        assert "creator" in result
        assert result["creator"]["username"] == "creator"

    def test_enrich_no_creator(self):
        self.user_repo.get_by_id.return_value = None
        d = {"creator_user_id": 999, "id": None}
        result = self.svc._enrich_puzzle(d)
        assert "creator" not in result

    def test_enrich_no_creator_id(self):
        d = {"id": 1}
        # solve_repo will be hit because id is present
        self.solve_repo.conn.execute.return_value.fetchone.return_value = (7,)
        result = self.svc._enrich_puzzle(d)
        assert result["solvedCount"] == 7

    def test_enrich_solved_count_exception_swallowed(self):
        d = {"id": 1}
        self.solve_repo.conn.execute.side_effect = Exception("boom")
        # Should not raise
        result = self.svc._enrich_puzzle(d)
        assert "solvedCount" not in result


# ---------------------------------------------------------------------------
# create_puzzle — uncovered branches
# ---------------------------------------------------------------------------

class TestCreatePuzzleBranches:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, _ = _make_service()
        self.repo.count_published.return_value = 0

    def test_create_difficulty_invalid_defaults_easy(self):
        # Admin path skips capacity / blocked-creator checks → simpler mocking
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.user_repo.get_by_id.return_value = user
        # Duplicate-name check returns None (no existing puzzle)
        self.repo.conn.execute.return_value.fetchone.return_value = None

        created = Puzzle(id=42, name="X", creator_user_id=1, difficulty=PuzzleDifficulty.EASY)
        self.repo.create.return_value = created
        payload = {"name": "X", "difficulty": "INVALID_DIFFICULTY"}
        result = self.svc.create_puzzle("tok", payload)
        # Should not raise even with invalid difficulty
        assert result["id"] == "42"

    def test_create_integrity_error_translated(self):
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="admin", role=UserRole.ADMIN)
        self.user_repo.get_by_id.return_value = user
        self.repo.conn.execute.return_value.fetchone.return_value = None
        self.repo.create.side_effect = sqlite3.IntegrityError("dup")
        with pytest.raises(ValidationError, match="already exists"):
            self.svc.create_puzzle("tok", {"name": "Y"})

    def test_create_blocked_creator(self):
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="u", role=UserRole.CREATOR)
        self.user_repo.get_by_id.return_value = user
        max_pub, max_unpub = user.get_puzzle_capacity()
        # Flow: _count_unpublished (must be < max_unpub), then _is_creator_blocked
        # checks published > max_pub (TRUE → blocked).
        execute = self.repo.conn.execute
        execute.return_value.fetchone.side_effect = [
            (0,),                # _count_unpublished_puzzles (capacity check)
            (max_pub + 5,),      # _count_published_puzzles inside _is_creator_blocked
        ]
        with pytest.raises(ValidationError, match="exceeded your puzzle limits"):
            self.svc.create_puzzle("tok", {"name": "Z"})


# ---------------------------------------------------------------------------
# publish — uncovered branches (already published rowcount=0, solve check)
# ---------------------------------------------------------------------------

class TestPublishBranches:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, self.solve_repo = _make_service()
        self.repo.count_published.return_value = 0

    def test_publish_requires_self_solve(self):
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="u", role=UserRole.CREATOR)
        self.user_repo.get_by_id.return_value = user
        puzzle = Puzzle(id=10, name="P", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.repo.get_by_id.return_value = puzzle
        self.repo.list_test_cases.return_value = [Mock()]
        self.solve_repo.has_passed.return_value = False
        with pytest.raises(ValidationError, match="must solve"):
            self.svc.publish("tok", 10)

    def test_publish_unpublished_status_skips_solve_check(self):
        # Re-publishing from UNPUBLISHED → no solve check, only limits
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="u", role=UserRole.CREATOR)
        self.user_repo.get_by_id.return_value = user
        puzzle = Puzzle(id=10, name="P", creator_user_id=1, status=PuzzleStatus.UNPUBLISHED)
        published = Puzzle(id=10, name="P", creator_user_id=1, status=PuzzleStatus.PUBLISHED)
        self.repo.get_by_id.side_effect = [puzzle, published]
        self.repo.list_test_cases.return_value = [Mock()]

        # transaction() issues BEGIN, then SELECT, UPDATE, COMMIT.
        # Use a single configured cursor with sensible defaults.
        cursor = Mock()
        cursor.rowcount = 1
        cursor.fetchall.return_value = []  # no other published puzzles
        self.repo.conn.execute.return_value = cursor

        result = self.svc.publish("tok", 10)
        assert result["id"] == "10"
        self.solve_repo.has_passed.assert_not_called()

    def test_publish_update_rowcount_zero(self):
        self.auth.require_user_id.return_value = 1
        user = User(id=1, username="u", role=UserRole.ADMIN)
        self.user_repo.get_by_id.return_value = user
        puzzle = Puzzle(id=10, name="P", creator_user_id=1, status=PuzzleStatus.DRAFT)
        self.repo.get_by_id.return_value = puzzle
        self.repo.list_test_cases.return_value = [Mock()]
        upd = Mock()
        upd.rowcount = 0
        self.repo.conn.execute.return_value = upd
        with pytest.raises(ValidationError, match="already published"):
            self.svc.publish("tok", 10)


# ---------------------------------------------------------------------------
# update_puzzle — uncovered field branches
# ---------------------------------------------------------------------------

class TestUpdatePuzzleBranches:
    def setup_method(self):
        self.svc, self.repo, self.user_repo, self.auth, _ = _make_service()
        self.auth.require_user_id.return_value = 1
        self.user = User(id=1, username="u", role=UserRole.ADMIN)
        self.user_repo.get_by_id.return_value = self.user
        self.puzzle = Puzzle(id=10, name="P", creator_user_id=1)
        self.repo.get_by_id.return_value = self.puzzle

    def test_update_name_too_long_rejected(self):
        with pytest.raises(ValidationError, match="at most"):
            self.svc.update_puzzle("tok", 10, {"name": "x" * 10_000})

    def test_update_name_duplicate_rejected(self):
        self.repo.conn.execute.return_value.fetchone.return_value = (1,)
        with pytest.raises(ValidationError, match="already exists"):
            self.svc.update_puzzle("tok", 10, {"name": "duplicate"})

    def test_update_description_too_long(self):
        with pytest.raises(ValidationError, match="at most"):
            self.svc.update_puzzle("tok", 10, {"description": "x" * 100_000})

    def test_update_instructions_too_large(self):
        # build a string that exceeds the byte limit
        from Backend import settings
        too_big = "x" * (settings.PUZZLE_INSTRUCTIONS_MAX_BYTES + 1)
        with pytest.raises(ValidationError, match="at most"):
            self.svc.update_puzzle("tok", 10, {"instructions": too_big})

    def test_update_creator_comment_too_long(self):
        from Backend import settings
        too_big = "x" * (settings.PUZZLE_CREATOR_COMMENT_MAX_LENGTH + 1)
        with pytest.raises(ValidationError, match="at most"):
            self.svc.update_puzzle("tok", 10, {"creator_comment": too_big})

    def test_update_creator_comment_none_clears(self):
        # Setting to None should pass through without raising
        self.repo.conn.execute.return_value.fetchone.return_value = None
        self.svc.update_puzzle("tok", 10, {"creator_comment": None})

    def test_update_creator_comment_whitespace_becomes_none(self):
        self.repo.conn.execute.return_value.fetchone.return_value = None
        self.svc.update_puzzle("tok", 10, {"creator_comment": "   "})

    def test_update_allow_arsenal_non_bool_rejected(self):
        with pytest.raises(ValidationError, match="must be a boolean"):
            self.svc.update_puzzle("tok", 10, {"allow_arsenal": "yes"})

    def test_update_allow_arsenal_true(self):
        self.svc.update_puzzle("tok", 10, {"allow_arsenal": True})
        # No exception → success path covered

    def test_update_display_modes_json_serialized(self):
        self.svc.update_puzzle("tok", 10, {"arsenal_component_display_modes": {"a": "icon"}})

    def test_update_display_modes_falsy_becomes_null(self):
        self.svc.update_puzzle("tok", 10, {"arsenal_component_display_modes": None})

    def test_update_creator_blocked(self):
        # Non-admin creator over their limits
        self.user.role = UserRole.CREATOR
        # _is_creator_blocked → published > max
        max_pub, _ = self.user.get_puzzle_capacity()
        ex = self.repo.conn.execute
        ex.return_value.fetchone.side_effect = [
            (max_pub + 5,),  # _count_published
        ]
        with pytest.raises(ValidationError, match="exceeded"):
            self.svc.update_puzzle("tok", 10, {"name": "newname"})
