"""Coverage tests for ArsenalService — focused on _normalize_visual_style branches,
_resolve_max_slots_for_level tiers, _is_admin, _is_stateful_structure,
_calculate_truth_table fast paths, _flatten_used_arsenal_pieces validation,
_calculate_arsenal_cost validation, and helpers used by puzzle resolution."""

import json
import pytest
from unittest.mock import Mock, patch

from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.DomainLayer.Enums import UserRole, GateType
from Backend.DomainLayer.Exceptions import ValidationError


def _make_service():
    repo = Mock()
    user_repo = Mock()
    auth = Mock()
    engine = Mock()
    xp = Mock()
    return ArsenalService(repo, user_repo, auth, engine, xp), repo, user_repo, auth, engine, xp


# ---------------------------------------------------------------------------
# _normalize_visual_style — extensive branch coverage
# ---------------------------------------------------------------------------

class TestNormalizeVisualStyle:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_none_returns_empty(self):
        assert self.svc._normalize_visual_style(None) == {}

    def test_non_dict_rejected(self):
        with pytest.raises(ValidationError, match="must be an object"):
            self.svc._normalize_visual_style("not-a-dict")

    def test_preset_valid_returns_legacy_dict(self):
        result = self.svc._normalize_visual_style({"preset": "clean-lab"})
        assert result["borderStyle"] == "solid"

    def test_preset_invalid_string(self):
        with pytest.raises(ValidationError, match="preset is invalid"):
            self.svc._normalize_visual_style({"preset": "nope"})

    def test_preset_invalid_type(self):
        with pytest.raises(ValidationError, match="preset is invalid"):
            self.svc._normalize_visual_style({"preset": 42})

    def test_accent_color_invalid(self):
        with pytest.raises(ValidationError, match="accentColor"):
            self.svc._normalize_visual_style({"accentColor": "blue"})

    def test_accent_color_short_hex_valid(self):
        result = self.svc._normalize_visual_style({"accentColor": "#abc"})
        assert result["accentColor"] == "#abc"

    def test_accent_color_long_hex_valid(self):
        result = self.svc._normalize_visual_style({"accent_color": "#abcdef"})
        assert result["accentColor"] == "#abcdef"

    def test_roundness_bool_rejected(self):
        with pytest.raises(ValidationError, match="roundness"):
            self.svc._normalize_visual_style({"roundness": True})

    def test_roundness_string_rejected(self):
        with pytest.raises(ValidationError, match="roundness"):
            self.svc._normalize_visual_style({"roundness": "five"})

    def test_roundness_out_of_range(self):
        with pytest.raises(ValidationError, match="between"):
            self.svc._normalize_visual_style({"roundness": 99})
        with pytest.raises(ValidationError, match="between"):
            self.svc._normalize_visual_style({"roundness": -5})

    def test_roundness_valid_int(self):
        result = self.svc._normalize_visual_style({"roundness": 7})
        assert result["roundness"] == 7

    def test_roundness_valid_float_rounded(self):
        result = self.svc._normalize_visual_style({"corner_radius": 3.6})
        assert result["roundness"] == 4

    def test_legacy_corner_style_sharp(self):
        result = self.svc._normalize_visual_style({"cornerStyle": "sharp"})
        assert result["roundness"] == 0

    def test_legacy_corner_style_capsule(self):
        result = self.svc._normalize_visual_style({"corner_style": "capsule"})
        assert result["roundness"] == 10

    def test_legacy_corner_invalid_type(self):
        with pytest.raises(ValidationError, match="cornerStyle"):
            self.svc._normalize_visual_style({"cornerStyle": 12})

    def test_legacy_corner_unknown(self):
        with pytest.raises(ValidationError, match="cornerStyle"):
            self.svc._normalize_visual_style({"cornerStyle": "bevelled"})

    def test_border_chip_translates(self):
        result = self.svc._normalize_visual_style({"borderStyle": "chip"})
        assert result["edgeAddon"] == "chip-legs"
        assert result["borderStyle"] == "double"

    def test_border_invalid_type(self):
        with pytest.raises(ValidationError, match="borderStyle"):
            self.svc._normalize_visual_style({"borderStyle": 42})

    def test_border_unknown(self):
        with pytest.raises(ValidationError, match="borderStyle"):
            self.svc._normalize_visual_style({"border_style": "dashed"})

    def test_border_valid(self):
        result = self.svc._normalize_visual_style({"borderStyle": "etched"})
        assert result["borderStyle"] == "etched"

    def test_edge_addon_chip_translates(self):
        result = self.svc._normalize_visual_style({"edgeAddon": "chip"})
        assert result["edgeAddon"] == "chip-legs"

    def test_edge_addon_invalid(self):
        with pytest.raises(ValidationError, match="edgeAddon"):
            self.svc._normalize_visual_style({"edge_addon": "wings"})

    def test_edge_addon_invalid_type(self):
        with pytest.raises(ValidationError, match="edgeAddon"):
            self.svc._normalize_visual_style({"edgeAddon": 99})

    def test_surface_invalid_type(self):
        with pytest.raises(ValidationError, match="surfaceStyle"):
            self.svc._normalize_visual_style({"surfaceStyle": 0})

    def test_surface_invalid_value(self):
        with pytest.raises(ValidationError, match="surfaceStyle"):
            self.svc._normalize_visual_style({"surface_style": "wood"})

    def test_surface_valid(self):
        result = self.svc._normalize_visual_style({"surfaceStyle": "matte"})
        assert result["surfaceStyle"] == "matte"


# ---------------------------------------------------------------------------
# _resolve_max_slots_for_level — tier walks
# ---------------------------------------------------------------------------

class TestResolveMaxSlotsForLevel:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_low_level(self):
        # Level 1 should fall in lowest tier
        slots = self.svc._resolve_max_slots_for_level(1)
        assert slots >= 0

    def test_very_high_level_returns_max(self):
        # Level 999 should return the ARSENAL_XP_MAX_SLOTS
        from Backend.ServiceLayer.ArsenalService import ARSENAL_XP_MAX_SLOTS
        assert self.svc._resolve_max_slots_for_level(999) == int(ARSENAL_XP_MAX_SLOTS)


# ---------------------------------------------------------------------------
# _is_admin
# ---------------------------------------------------------------------------

class TestIsAdmin:
    def test_admin_enum(self):
        assert ArsenalService._is_admin(UserRole.ADMIN) is True

    def test_creator_enum(self):
        assert ArsenalService._is_admin(UserRole.CREATOR) is False

    def test_admin_string_normalized(self):
        assert ArsenalService._is_admin("  ADMIN ") is True

    def test_non_admin_string(self):
        assert ArsenalService._is_admin("solver") is False


# ---------------------------------------------------------------------------
# _is_stateful_structure
# ---------------------------------------------------------------------------

class TestIsStatefulStructure:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_non_dict(self):
        assert self.svc._is_stateful_structure("not-a-dict") is False

    def test_state_ports_list_non_empty(self):
        assert self.svc._is_stateful_structure({"state": ["q"]}) is True

    def test_state_ports_empty(self):
        assert self.svc._is_stateful_structure({"state": []}) is False

    def test_dff_in_placed_components(self):
        assert self.svc._is_stateful_structure(
            {"placedComponents": [{"componentId": "DFF"}]}
        ) is True

    def test_no_dff(self):
        assert self.svc._is_stateful_structure(
            {"placedComponents": [{"componentId": "AND"}]}
        ) is False

    def test_placed_not_a_list(self):
        assert self.svc._is_stateful_structure({"placedComponents": "x"}) is False

    def test_uses_components_key(self):
        assert self.svc._is_stateful_structure(
            {"components": [{"componentId": "DFF"}]}
        ) is True

    def test_uses_placed_key(self):
        assert self.svc._is_stateful_structure(
            {"placed": [{"componentId": "DFF"}]}
        ) is True


# ---------------------------------------------------------------------------
# _calculate_truth_table — fast paths
# ---------------------------------------------------------------------------

class TestCalculateTruthTable:
    def setup_method(self):
        self.svc, *_ = _make_service()

    def test_stateful_returns_empty(self):
        result = self.svc._calculate_truth_table(2, 1, {"state": ["q"]})
        assert result == {}

    def test_uses_existing_truth_table(self):
        tt = {"00": {"out0": 0}, "01": {"out0": 1}}
        result = self.svc._calculate_truth_table(2, 1, {"truth_table": tt})
        assert result == tt

    def test_uses_eval_map_fallback(self):
        em = {"00": {"out0": 1}}
        result = self.svc._calculate_truth_table(2, 1, {"eval_map": em})
        assert result == em

    def test_simulates_when_no_table(self):
        self.svc.engine.simulate.return_value = {"out0": 1}
        result = self.svc._calculate_truth_table(1, 1, {"placed": [], "wires": []})
        assert result == {"0": {"out0": 1}, "1": {"out0": 1}}

    def test_simulation_exception_uses_zero_row(self):
        self.svc.engine.simulate.side_effect = Exception("sim")
        result = self.svc._calculate_truth_table(1, 1, {})
        assert result["0"] == {"out0": 0}

    def test_outer_exception_returns_empty(self):
        # The outer try wraps the 2**num_inputs computation as well, so a
        # malicious num_inputs that errors should short-circuit cleanly.
        # We'll patch range to raise.
        with patch("builtins.range", side_effect=Exception("boom")):
            result = self.svc._calculate_truth_table(1, 1, {})
        assert result == {}


# ---------------------------------------------------------------------------
# _flatten_used_arsenal_pieces — error branches
# ---------------------------------------------------------------------------

class TestFlattenUsedArsenalPieces:
    def setup_method(self):
        self.svc, self.repo, *_ = _make_service()

    def test_empty_list_returns_input(self):
        assert self.svc._flatten_used_arsenal_pieces(["AND"], [], 1) == ["AND"]

    def test_piece_not_found(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            self.svc._flatten_used_arsenal_pieces([], [99], 1)

    def test_piece_not_owned(self):
        piece = Mock(user_id=999, is_arsenal=True)
        self.repo.get_by_id.return_value = piece
        with pytest.raises(ValidationError, match="not owned"):
            self.svc._flatten_used_arsenal_pieces([], [1], 1)

    def test_piece_not_arsenal(self):
        piece = Mock(user_id=1, is_arsenal=False)
        self.repo.get_by_id.return_value = piece
        with pytest.raises(ValidationError, match="not an arsenal piece"):
            self.svc._flatten_used_arsenal_pieces([], [1], 1)

    def test_flattens_successfully(self):
        piece = Mock(user_id=1, is_arsenal=True, basic_gates=json.dumps(["OR", "NOT"]))
        self.repo.get_by_id.return_value = piece
        result = self.svc._flatten_used_arsenal_pieces(["AND"], [1], 1)
        assert set(result) == {"AND", "OR", "NOT"}

    def test_invalid_basic_gates_json(self):
        piece = Mock(user_id=1, is_arsenal=True, basic_gates="{bad-json")
        self.repo.get_by_id.return_value = piece
        with pytest.raises(ValidationError, match="Invalid basic_gates"):
            self.svc._flatten_used_arsenal_pieces([], [1], 1)


# ---------------------------------------------------------------------------
# _calculate_arsenal_cost
# ---------------------------------------------------------------------------

class TestCalculateArsenalCost:
    def setup_method(self):
        self.svc, self.repo, *_ = _make_service()

    def test_only_basic_gates(self):
        assert self.svc._calculate_arsenal_cost(["AND", "OR", "NOT"]) == 3

    def test_with_used_pieces_added(self):
        piece = Mock(user_id=1, is_arsenal=True, cost=5)
        self.repo.get_by_id.return_value = piece
        assert self.svc._calculate_arsenal_cost(["AND"], used_arsenal_ids=[1], user_id=1) == 6

    def test_piece_not_found(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            self.svc._calculate_arsenal_cost(["AND"], used_arsenal_ids=[99], user_id=1)

    def test_piece_not_owned(self):
        piece = Mock(user_id=2, is_arsenal=True, cost=3)
        self.repo.get_by_id.return_value = piece
        with pytest.raises(ValidationError, match="not owned"):
            self.svc._calculate_arsenal_cost([], used_arsenal_ids=[1], user_id=1)

    def test_piece_not_arsenal(self):
        piece = Mock(user_id=1, is_arsenal=False, cost=3)
        self.repo.get_by_id.return_value = piece
        with pytest.raises(ValidationError, match="not an arsenal piece"):
            self.svc._calculate_arsenal_cost([], used_arsenal_ids=[1], user_id=1)


# ---------------------------------------------------------------------------
# get_custom_pieces_for_puzzle / get_arsenal_pieces_by_ids / get_user_arsenal_filtered_by_gates
# ---------------------------------------------------------------------------

class TestGetCustomPieces:
    def test_get_custom_pieces_normal(self):
        svc, repo, *_ = _make_service()
        piece1 = Mock()
        piece1.to_circuit_component.return_value = {"id": "c1"}
        repo.list_custom_pieces_by_puzzle.return_value = [piece1]
        result = svc.get_custom_pieces_for_puzzle(1)
        assert result == [{"id": "c1"}]

    def test_get_custom_pieces_empty(self):
        svc, repo, *_ = _make_service()
        repo.list_custom_pieces_by_puzzle.return_value = []
        assert svc.get_custom_pieces_for_puzzle(1) == []

    def test_get_custom_pieces_exception(self):
        svc, repo, *_ = _make_service()
        repo.list_custom_pieces_by_puzzle.side_effect = Exception("db")
        # Should not raise; returns []
        assert svc.get_custom_pieces_for_puzzle(1) == []


class TestGetArsenalPiecesByIds:
    def test_empty_list_returns_empty(self):
        svc, *_ = _make_service()
        assert svc.get_arsenal_pieces_by_ids([]) == []

    def test_some_pieces(self):
        svc, repo, *_ = _make_service()
        piece = Mock(is_arsenal=True)
        piece.to_circuit_component.return_value = {"id": "p1"}
        repo.get_by_id.return_value = piece
        result = svc.get_arsenal_pieces_by_ids([1])
        assert result == [{"id": "p1"}]

    def test_skips_non_arsenal(self):
        svc, repo, *_ = _make_service()
        piece = Mock(is_arsenal=False)
        repo.get_by_id.return_value = piece
        assert svc.get_arsenal_pieces_by_ids([1]) == []

    def test_skips_on_inner_exception(self):
        svc, repo, *_ = _make_service()
        repo.get_by_id.side_effect = Exception("db")
        assert svc.get_arsenal_pieces_by_ids([1]) == []

    def test_outer_exception(self):
        svc, *_ = _make_service()
        # Passing a non-iterable triggers the outer except path
        assert svc.get_arsenal_pieces_by_ids(None) == []


class TestGetUserArsenalFiltered:
    def test_no_user_id(self):
        svc, *_ = _make_service()
        assert svc.get_user_arsenal_filtered_by_gates(0, {"AND"}) == []

    def test_filters_by_allowed_gates(self):
        svc, repo, *_ = _make_service()
        ok_piece = Mock(basic_gates=json.dumps(["AND"]))
        ok_piece.to_circuit_component.return_value = {"id": "ok"}
        blocked_piece = Mock(basic_gates=json.dumps(["DFF"]))
        blocked_piece.to_circuit_component.return_value = {"id": "no"}
        repo.list_arsenal_by_user.return_value = [ok_piece, blocked_piece]
        result = svc.get_user_arsenal_filtered_by_gates(1, {"AND", "OR"})
        assert result == [{"id": "ok"}]

    def test_skip_invalid_json(self):
        svc, repo, *_ = _make_service()
        bad_piece = Mock(basic_gates="{not-json")
        bad_piece.to_circuit_component.return_value = {"id": "bad"}
        repo.list_arsenal_by_user.return_value = [bad_piece]
        assert svc.get_user_arsenal_filtered_by_gates(1, {"AND"}) == []

    def test_outer_exception(self):
        svc, repo, *_ = _make_service()
        repo.list_arsenal_by_user.side_effect = Exception("db")
        assert svc.get_user_arsenal_filtered_by_gates(1, {"AND"}) == []


# ---------------------------------------------------------------------------
# delete_arsenal_piece — not found
# ---------------------------------------------------------------------------

class TestDeleteArsenalPiece:
    def test_delete_success(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        repo.delete.return_value = True
        assert svc.delete_arsenal_piece("tok", 5) == {"ok": True}

    def test_delete_not_found(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        repo.delete.return_value = False
        with pytest.raises(ValidationError, match="not found"):
            svc.delete_arsenal_piece("tok", 5)


# ---------------------------------------------------------------------------
# update_arsenal_piece — edge branches
# ---------------------------------------------------------------------------

class TestUpdateArsenalPieceBranches:
    def setup_method(self):
        self.svc, self.repo, _, self.auth, *_ = _make_service()
        self.auth.require_user_id.return_value = 1

    def _piece(self, **kwargs):
        defaults = {
            "user_id": 1,
            "is_arsenal": True,
            "structure_json": json.dumps({}),
            "name": "old",
        }
        defaults.update(kwargs)
        piece = Mock(**defaults)
        piece.to_dict.return_value = {"id": "1", "name": defaults["name"]}
        return piece

    def test_update_empty_name_rejected(self):
        with pytest.raises(ValidationError, match="new name is required"):
            self.svc.update_arsenal_piece("tok", 1, new_name="   ")

    def test_update_no_changes_rejected(self):
        self.repo.get_by_id.return_value = self._piece()
        with pytest.raises(ValidationError, match="no updates"):
            self.svc.update_arsenal_piece("tok", 1)

    def test_update_piece_not_found(self):
        self.repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            self.svc.update_arsenal_piece("tok", 1, new_name="new")

    def test_update_forbidden(self):
        self.repo.get_by_id.return_value = self._piece(user_id=999)
        with pytest.raises(ValidationError, match="forbidden"):
            self.svc.update_arsenal_piece("tok", 1, new_name="new")

    def test_update_not_arsenal_piece(self):
        self.repo.get_by_id.return_value = self._piece(is_arsenal=False)
        with pytest.raises(ValidationError, match="not an arsenal piece"):
            self.svc.update_arsenal_piece("tok", 1, new_name="new")

    def test_update_name_only(self):
        self.repo.get_by_id.return_value = self._piece()
        result = self.svc.update_arsenal_piece("tok", 1, new_name="new")
        assert result is not None

    def test_update_visual_style_clears_when_empty(self):
        # Pre-set visualStyle, then update with {} → it should be removed
        piece = self._piece(structure_json=json.dumps({"visualStyle": {"old": True}}))
        self.repo.get_by_id.return_value = piece
        self.svc.update_arsenal_piece("tok", 1, visual_style={})
        # Verify structure_json no longer has visualStyle
        final = json.loads(piece.structure_json)
        assert "visualStyle" not in final

    def test_update_visual_style_invalid_structure_json(self):
        piece = self._piece(structure_json="not-json")
        self.repo.get_by_id.return_value = piece
        # Should not raise — structure defaults to {}
        self.svc.update_arsenal_piece("tok", 1, visual_style={"accentColor": "#abc"})

    def test_update_visual_style_non_dict_structure(self):
        piece = self._piece(structure_json=json.dumps([1, 2, 3]))
        self.repo.get_by_id.return_value = piece
        self.svc.update_arsenal_piece("tok", 1, visual_style={"accentColor": "#abc"})

    def test_update_integrity_error_translated(self):
        import sqlite3
        self.repo.get_by_id.return_value = self._piece()
        self.repo.update.side_effect = sqlite3.IntegrityError("dup")
        with pytest.raises(ValidationError, match="already exists"):
            self.svc.update_arsenal_piece("tok", 1, new_name="dup")


# ---------------------------------------------------------------------------
# get_arsenal_piece + list_my_arsenal
# ---------------------------------------------------------------------------

class TestGetArsenalPiece:
    def test_get_not_found(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        repo.get_by_id.return_value = None
        with pytest.raises(ValidationError, match="not found"):
            svc.get_arsenal_piece("tok", 1)

    def test_get_forbidden(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        repo.get_by_id.return_value = Mock(user_id=999, is_arsenal=True)
        with pytest.raises(ValidationError, match="forbidden"):
            svc.get_arsenal_piece("tok", 1)

    def test_get_not_arsenal(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        repo.get_by_id.return_value = Mock(user_id=1, is_arsenal=False)
        with pytest.raises(ValidationError, match="not an arsenal piece"):
            svc.get_arsenal_piece("tok", 1)

    def test_get_success(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        piece = Mock(user_id=1, is_arsenal=True)
        piece.to_dict.return_value = {"id": "1"}
        repo.get_by_id.return_value = piece
        assert svc.get_arsenal_piece("tok", 1) == {"id": "1"}


# ---------------------------------------------------------------------------
# get_available_pieces_for_puzzle
# ---------------------------------------------------------------------------

class TestGetAvailablePiecesForPuzzle:
    def test_filters_to_allowed(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        ok = Mock(basic_gates=json.dumps(["AND"]))
        ok.to_circuit_component.return_value = {"id": "ok"}
        blocked = Mock(basic_gates=json.dumps(["DFF"]))
        blocked.to_circuit_component.return_value = {"id": "no"}
        repo.list_arsenal_by_user.return_value = [ok, blocked]
        result = svc.get_available_pieces_for_puzzle("tok", {"AND"})
        assert result == [{"id": "ok"}]

    def test_skip_invalid_json(self):
        svc, repo, _, auth, *_ = _make_service()
        auth.require_user_id.return_value = 1
        bad = Mock(basic_gates="{not-json")
        bad.to_circuit_component.return_value = {"id": "bad"}
        repo.list_arsenal_by_user.return_value = [bad]
        assert svc.get_available_pieces_for_puzzle("tok", {"AND"}) == []
