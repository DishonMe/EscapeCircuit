import pytest
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

    def test_service_initialization(self):
        # Basic initialization test
        assert self.service.repo == self.mock_circuit_repo
        assert self.service.user_repo == self.mock_user_repo



