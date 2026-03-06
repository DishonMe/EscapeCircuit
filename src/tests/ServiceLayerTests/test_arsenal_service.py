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


class TestArsenalServiceCapacity:
    def setup_method(self):
        self.mock_circuit_repo = Mock(spec=CircuitRepo)
        self.mock_circuit_repo.conn = Mock()
        self.mock_user_repo = Mock(spec=UserRepo)
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()
        self.mock_xp = Mock(spec=XPService)

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
