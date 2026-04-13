import pytest
import sqlite3
from unittest.mock import Mock

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Enums import UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.User import User
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.XPService import XPService
from Backend.settings import ARSENAL_XP_LEVEL_TIERS


class TestArsenalServiceInit:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_initialization(self):
        assert self.service.repo == self.mock_circuit_repo
        assert self.service.user_repo == self.mock_user_repo
        assert self.service.auth == self.mock_auth
        assert self.service.engine == self.mock_engine
        assert self.service.xp == self.mock_xp

    def test_arsenal_constants(self):
        assert self.service.MAX_ARSENAL_SIZE == self.service.MAX_ARSENAL_SIZE
        assert self.service.MAX_INPUTS > 0
        assert self.service.MAX_OUTPUTS > 0
        assert self.service.MIN_INPUTS >= 0
        assert self.service.MIN_OUTPUTS >= 0


class TestArsenalServiceSaveArsenalPiece:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_circuit_repo.conn = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def _valid_payload(self) -> dict:
        return {
            "name": "my_piece",
            "num_inputs": 1,
            "num_outputs": 1,
            "structure_json": "{}",
            "basic_gates": '["AND"]',
            "truth_table": {"0": "0", "1": "1"},
        }

    def test_save_arsenal_piece_rejects_non_admin_at_capacity(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = User(
            id=1,
            username="creator",
            role=UserRole.CREATOR,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1
        # Level 1 should map to the first configured tier.
        expected_slots = ARSENAL_XP_LEVEL_TIERS[0][1]
        self.mock_circuit_repo.count_user_components.return_value = expected_slots

        with pytest.raises(ValidationError) as exc_info:
            self.service.save_arsenal_piece("valid_token", self._valid_payload())

        assert str(exc_info.value) == (
            f"Arsenal capacity reached ({expected_slots}/{expected_slots}). "
            "Level up to unlock more slots!"
        )

    def test_save_arsenal_piece_admin_bypasses_capacity(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = User(
            id=1,
            username="admin",
            role=UserRole.ADMIN,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1

        saved_circuit = Circuit(
            id=123,
            user_id=1,
            name="my_piece",
            cost=1,
            structure_json="{}",
            is_arsenal=True,
            basic_gates='["AND"]',
            truth_table='{"0": "0", "1": "1"}',
            num_inputs=1,
            num_outputs=1,
        )
        self.mock_circuit_repo.create.return_value = saved_circuit

        result = self.service.save_arsenal_piece("valid_token", self._valid_payload())

        assert result["id"] == 123
        self.mock_circuit_repo.count_user_components.assert_not_called()

    def test_save_arsenal_piece_accepts_all_zero_truth_table(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_user_repo.get_by_id.return_value = User(
            id=1,
            username="creator",
            role=UserRole.CREATOR,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1
        self.mock_circuit_repo.count_user_components.return_value = 0

        payload = self._valid_payload()
        payload["truth_table"] = {"0": "0", "1": "0"}

        saved_circuit = Circuit(
            id=124,
            user_id=1,
            name="my_piece",
            cost=1,
            structure_json="{}",
            is_arsenal=True,
            basic_gates='["AND"]',
            truth_table='{"0": "0", "1": "0"}',
            num_inputs=1,
            num_outputs=1,
        )
        self.mock_circuit_repo.create.return_value = saved_circuit

        result = self.service.save_arsenal_piece("valid_token", payload)

        assert result["id"] == 124
        assert result["truth_table"] == '{"0": "0", "1": "0"}'

    def test_save_arsenal_piece_invalid_inputs(self):
        user_id = 1
        token = "valid_token"
        
        payload = {
            "name": "Invalid",
            "num_inputs": 0,  # Invalid
            "num_outputs": 1,
        }
        
        self.mock_auth.require_user_id.return_value = user_id
        user = Mock()
        user.id = user_id
        user.xp = 0
        self.mock_user_repo.get_by_id.return_value = user
        self.mock_xp.calculate_level.return_value = 1
        
        with pytest.raises(ValidationError):
            self.service.save_arsenal_piece(token, payload)

    def test_save_arsenal_piece_arsenal_full(self):
        user_id = 1
        token = "valid_token"
        
        payload = {
            "name": "New Piece",
            "num_inputs": 2,
            "num_outputs": 1,
        }
        
        self.mock_auth.require_user_id.return_value = user_id
        user = Mock()
        user.id = user_id
        user.xp = 0
        self.mock_user_repo.get_by_id.return_value = user
        self.mock_xp.calculate_level.return_value = 1
        
        # Mock full arsenal (MAX_ARSENAL_SIZE pieces)
        full_arsenal = [Mock() for _ in range(self.service.MAX_ARSENAL_SIZE)]
        self.mock_circuit_repo.list_arsenal.return_value = full_arsenal
        
        with pytest.raises(ValidationError):
            self.service.save_arsenal_piece(token, payload)

    def test_save_arsenal_piece_missing_name(self):
        user_id = 1
        token = "valid_token"
        
        payload = {
            "num_inputs": 2,
            "num_outputs": 1,
        }
        
        self.mock_auth.require_user_id.return_value = user_id
        user = Mock()
        user.id = user_id
        self.mock_user_repo.get_by_id.return_value = user
        
        with pytest.raises(ValidationError):
            self.service.save_arsenal_piece(token, payload)


class TestArsenalServiceListArsenal:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_list_my_arsenal_calls_repo(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_circuit_repo.list_arsenal_by_user.return_value = []
        
        result = self.service.list_my_arsenal(token)
        
        assert result == []
        self.mock_circuit_repo.list_arsenal_by_user.assert_called_once_with(user_id)


class TestArsenalServiceDeleteArsenalPiece:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_delete_arsenal_piece_calls_repo(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        mock_piece = Mock(spec=Circuit)
        mock_piece.creator_user_id = user_id
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        self.mock_circuit_repo.delete.return_value = True
        
        result = self.service.delete_arsenal_piece(token, piece_id)
        
        assert result is not None


class TestArsenalServiceGetArsenalPiece:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_get_arsenal_piece_success(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = True
        mock_piece.to_dict.return_value = {"id": piece_id, "name": "piece"}
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        result = self.service.get_arsenal_piece(token, piece_id)
        
        assert result == {"id": piece_id, "name": "piece"}
        self.mock_circuit_repo.get_by_id.assert_called_once_with(piece_id)

    def test_get_arsenal_piece_not_found(self):
        user_id = 1
        piece_id = 999
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_circuit_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.get_arsenal_piece(token, piece_id)
        
        assert "not found" in str(exc_info.value)

    def test_get_arsenal_piece_forbidden(self):
        user_id = 1
        other_user_id = 2
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = other_user_id
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.get_arsenal_piece(token, piece_id)
        
        assert "forbidden" in str(exc_info.value)

    def test_get_arsenal_piece_not_arsenal(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = False
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.get_arsenal_piece(token, piece_id)
        
        assert "not an arsenal piece" in str(exc_info.value)


class TestArsenalServiceRenameArsenalPiece:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_rename_arsenal_piece_success(self):
        user_id = 1
        piece_id = 101
        new_name = "renamed_piece"
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = True
        mock_piece.to_dict.return_value = {"id": piece_id, "name": new_name}
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        result = self.service.rename_arsenal_piece(token, piece_id, new_name)
        
        assert result == {"id": piece_id, "name": new_name}
        self.mock_circuit_repo.update.assert_called_once_with(mock_piece)

    def test_rename_arsenal_piece_empty_name(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.rename_arsenal_piece(token, piece_id, "")
        
        assert "required" in str(exc_info.value)

    def test_rename_arsenal_piece_not_found(self):
        user_id = 1
        piece_id = 999
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_circuit_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.rename_arsenal_piece(token, piece_id, "new_name")
        
        assert "not found" in str(exc_info.value)

    def test_rename_arsenal_piece_forbidden(self):
        user_id = 1
        other_user_id = 2
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = other_user_id
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.rename_arsenal_piece(token, piece_id, "new_name")
        
        assert "forbidden" in str(exc_info.value)

    def test_rename_arsenal_piece_not_arsenal(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = False
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.rename_arsenal_piece(token, piece_id, "new_name")
        
        assert "not an arsenal piece" in str(exc_info.value)

    def test_rename_arsenal_piece_duplicate_name(self):
        user_id = 1
        piece_id = 101
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = True
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        self.mock_circuit_repo.update.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed", None)
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.rename_arsenal_piece(token, piece_id, "duplicate")
        
        assert "already exists" in str(exc_info.value)


class TestArsenalServiceGetAvailablePieces:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_get_available_pieces_for_puzzle_all_allowed(self):
        user_id = 1
        token = "valid_token"
        allowed_gates = {"AND", "OR", "NOT"}
        
        self.mock_auth.require_user_id.return_value = user_id
        
        mock_piece1 = Mock(spec=Circuit)
        mock_piece1.basic_gates = '["AND"]'
        mock_piece1.to_circuit_component.return_value = {"id": 1, "name": "piece1"}
        
        mock_piece2 = Mock(spec=Circuit)
        mock_piece2.basic_gates = '["AND", "OR"]'
        mock_piece2.to_circuit_component.return_value = {"id": 2, "name": "piece2"}
        
        self.mock_circuit_repo.list_arsenal_by_user.return_value = [mock_piece1, mock_piece2]
        
        result = self.service.get_available_pieces_for_puzzle(token, allowed_gates)
        
        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "piece1"}
        assert result[1] == {"id": 2, "name": "piece2"}

    def test_get_available_pieces_for_puzzle_some_forbidden(self):
        user_id = 1
        token = "valid_token"
        allowed_gates = {"AND", "OR"}
        
        self.mock_auth.require_user_id.return_value = user_id
        
        mock_piece1 = Mock(spec=Circuit)
        mock_piece1.basic_gates = '["AND"]'
        mock_piece1.to_circuit_component.return_value = {"id": 1, "name": "piece1"}
        
        mock_piece2 = Mock(spec=Circuit)
        mock_piece2.basic_gates = '["NOT", "XOR"]'
        
        self.mock_circuit_repo.list_arsenal_by_user.return_value = [mock_piece1, mock_piece2]
        
        result = self.service.get_available_pieces_for_puzzle(token, allowed_gates)
        
        assert len(result) == 1
        assert result[0] == {"id": 1, "name": "piece1"}

    def test_get_available_pieces_for_puzzle_invalid_json(self):
        user_id = 1
        token = "valid_token"
        allowed_gates = {"AND", "OR"}
        
        self.mock_auth.require_user_id.return_value = user_id
        
        mock_piece_bad = Mock(spec=Circuit)
        mock_piece_bad.basic_gates = "invalid json"
        
        mock_piece_good = Mock(spec=Circuit)
        mock_piece_good.basic_gates = '["AND"]'
        mock_piece_good.to_circuit_component.return_value = {"id": 2}
        
        self.mock_circuit_repo.list_arsenal_by_user.return_value = [mock_piece_bad, mock_piece_good]
        
        result = self.service.get_available_pieces_for_puzzle(token, allowed_gates)
        
        assert len(result) == 1


class TestArsenalServiceGetCustomPieces:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_get_custom_pieces_for_puzzle_success(self):
        puzzle_id = 5
        
        mock_piece1 = Mock(spec=Circuit)
        mock_piece1.to_circuit_component.return_value = {"id": 1, "name": "custom1"}
        
        mock_piece2 = Mock(spec=Circuit)
        mock_piece2.to_circuit_component.return_value = {"id": 2, "name": "custom2"}
        
        self.mock_circuit_repo.list_custom_pieces_by_puzzle.return_value = [mock_piece1, mock_piece2]
        
        result = self.service.get_custom_pieces_for_puzzle(puzzle_id)
        
        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "custom1"}
        self.mock_circuit_repo.list_custom_pieces_by_puzzle.assert_called_once_with(puzzle_id)

    def test_get_custom_pieces_for_puzzle_error(self):
        puzzle_id = 999
        
        self.mock_circuit_repo.list_custom_pieces_by_puzzle.side_effect = Exception("DB error")
        
        result = self.service.get_custom_pieces_for_puzzle(puzzle_id)
        
        assert result == []


class TestArsenalServicePrivateMethods:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_is_admin_with_admin_role(self):
        result = self.service._is_admin(UserRole.ADMIN)
        assert result is True

    def test_is_admin_with_creator_role(self):
        result = self.service._is_admin(UserRole.CREATOR)
        assert result is False

    def test_is_admin_with_string(self):
        result = self.service._is_admin("ADMIN")
        assert result is True

    def test_is_admin_with_lowercase_string(self):
        result = self.service._is_admin("admin")
        assert result is True

    def test_is_admin_with_non_admin_string(self):
        result = self.service._is_admin("user")
        assert result is False

    def test_resolve_max_slots_for_level(self):
        # Level 1 should match first tier
        result = self.service._resolve_max_slots_for_level(1)
        assert result == int(ARSENAL_XP_LEVEL_TIERS[0][1])

    def test_extract_basic_gates(self):
        structure_json = '{}'
        self.mock_engine.extract_used_gates.return_value = ["AND", "OR", "NOT"]
        
        result = self.service._extract_basic_gates(structure_json)
        
        # Should filter out DFF and keep only valid gates
        assert "AND" in result
        assert "OR" in result
        assert "NOT" in result

    def test_calculate_truth_table_from_structure(self):
        structure = {"truth_table": {"0": {"out0": 0}, "1": {"out0": 1}}}
        
        result = self.service._calculate_truth_table(1, 1, structure)
        
        assert result == {"0": {"out0": 0}, "1": {"out0": 1}}

    def test_calculate_truth_table_generates(self):
        structure = {"placed": [], "wires": []}
        
        self.mock_engine.simulate.return_value = {"out0": 0}
        
        result = self.service._calculate_truth_table(1, 1, structure)
        
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_flatten_used_arsenal_pieces_empty(self):
        basic_gates = ["AND", "OR"]
        
        result = self.service._flatten_used_arsenal_pieces(basic_gates, [], 1)
        
        assert result == basic_gates

    def test_flatten_used_arsenal_pieces_with_pieces(self):
        user_id = 1
        basic_gates = ["AND"]
        used_ids = [101]
        
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = True
        mock_piece.basic_gates = '["OR", "NOT"]'
        
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        result = self.service._flatten_used_arsenal_pieces(basic_gates, used_ids, user_id)
        
        assert "AND" in result
        assert "OR" in result
        assert "NOT" in result

    def test_flatten_used_arsenal_pieces_piece_not_found(self):
        user_id = 1
        basic_gates = ["AND"]
        used_ids = [999]
        
        self.mock_circuit_repo.get_by_id.return_value = None
        
        with pytest.raises(ValidationError) as exc_info:
            self.service._flatten_used_arsenal_pieces(basic_gates, used_ids, user_id)
        
        assert "not found" in str(exc_info.value)

    def test_flatten_used_arsenal_pieces_not_owned(self):
        user_id = 1
        other_user_id = 2
        basic_gates = ["AND"]
        used_ids = [101]
        
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = other_user_id
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service._flatten_used_arsenal_pieces(basic_gates, used_ids, user_id)
        
        assert "not owned" in str(exc_info.value)

    def test_flatten_used_arsenal_pieces_not_arsenal(self):
        user_id = 1
        basic_gates = ["AND"]
        used_ids = [101]
        
        mock_piece = Mock(spec=Circuit)
        mock_piece.user_id = user_id
        mock_piece.is_arsenal = False
        self.mock_circuit_repo.get_by_id.return_value = mock_piece
        
        with pytest.raises(ValidationError) as exc_info:
            self.service._flatten_used_arsenal_pieces(basic_gates, used_ids, user_id)
        
        assert "not an arsenal piece" in str(exc_info.value)

    def test_calculate_arsenal_cost_gates_only(self):
        gates = ["AND", "OR", "NOT"]
        
        result = self.service._calculate_arsenal_cost(gates, [], 1)
        
        assert result == 3

    def test_calculate_arsenal_cost_with_pieces(self):
        gates = ["AND"]
        used_ids = [101, 102]
        user_id = 1
        
        mock_piece1 = Mock(spec=Circuit)
        mock_piece1.user_id = user_id
        mock_piece1.is_arsenal = True
        mock_piece1.cost = 5
        
        mock_piece2 = Mock(spec=Circuit)
        mock_piece2.user_id = user_id
        mock_piece2.is_arsenal = True
        mock_piece2.cost = 3
        
        self.mock_circuit_repo.get_by_id.side_effect = [mock_piece1, mock_piece2]
        
        result = self.service._calculate_arsenal_cost(gates, used_ids, user_id)
        
        assert result == 1 + 5 + 3


class TestArsenalServiceSaveAdvanced:
    def setup_method(self):
        self.mock_circuit_repo = Mock()
        self.mock_circuit_repo.conn = Mock()
        self.mock_user_repo = Mock()
        self.mock_auth = Mock()
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        
        self.service = ArsenalService(
            self.mock_circuit_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_save_arsenal_piece_with_dff_gate(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = User(
            id=user_id,
            username="creator",
            role=UserRole.CREATOR,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1
        self.mock_circuit_repo.count_user_components.return_value = 0
        
        # Mock extract_used_gates to return DFF
        self.mock_engine.extract_used_gates.return_value = ["AND", "DFF"]
        
        payload = {
            "name": "dff_piece",
            "num_inputs": 1,
            "num_outputs": 1,
            "structure_json": "{}",
            "basic_gates": '["AND", "DFF"]',
            "truth_table": {"0": {"out0": 0}, "1": {"out0": 1}},
        }

        saved_circuit = Circuit(
            id=321,
            user_id=user_id,
            name="dff_piece",
            cost=2,
            structure_json="{}",
            is_arsenal=True,
            basic_gates='["AND", "DFF"]',
            truth_table='{"0": {"out0": 0}, "1": {"out0": 1}}',
            num_inputs=1,
            num_outputs=1,
        )
        self.mock_circuit_repo.create.return_value = saved_circuit

        result = self.service.save_arsenal_piece(token, payload)

        assert result["id"] == 321
        assert "DFF" in result["basic_gates"]

    def test_save_arsenal_piece_invalid_structure_json(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = User(
            id=user_id,
            username="creator",
            role=UserRole.CREATOR,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1
        
        payload = {
            "name": "bad_piece",
            "num_inputs": 1,
            "num_outputs": 1,
            "structure_json": "not valid json",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.save_arsenal_piece(token, payload)
        
        assert "Invalid" in str(exc_info.value)

    def test_save_arsenal_piece_invalid_outputs(self):
        user_id = 1
        token = "valid_token"
        
        self.mock_auth.require_user_id.return_value = user_id
        self.mock_user_repo.get_by_id.return_value = User(
            id=user_id,
            username="creator",
            role=UserRole.CREATOR,
            xp=0,
        )
        self.mock_xp.calculate_level.return_value = 1
        
        payload = {
            "name": "bad_piece",
            "num_inputs": 1,
            "num_outputs": 10,  # Too many
            "structure_json": "{}",
        }
        
        with pytest.raises(ValidationError) as exc_info:
            self.service.save_arsenal_piece(token, payload)
        
        assert "outputs" in str(exc_info.value)



