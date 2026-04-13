import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from Backend.ServiceLayer.CircuitService import CircuitService
from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService


class TestCircuitServiceCreation:
    def setup_method(self):
        self.mock_repo = Mock(spec=CircuitRepo)
        self.mock_repo.list_by_user.return_value = []
        # Mock conn for SQL COUNT(*) capacity check
        mock_count_cursor = Mock()
        mock_count_cursor.fetchone.return_value = (0,)
        self.mock_repo.conn = Mock()
        self.mock_repo.conn.execute.return_value = mock_count_cursor
        self.mock_user_repo = Mock()  # UserRepo
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()  # Fix: add missing mock_engine
        self.mock_xp = Mock()
        self.mock_xp.calculate_level.return_value = 1
        self.service = CircuitService(
            self.mock_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_circuit_service_initialization(self):
        assert self.service.repo == self.mock_repo
        assert self.service.auth == self.mock_auth


class TestCircuitServiceSaveCircuit:
    def setup_method(self):
        self.mock_repo = Mock(spec=CircuitRepo)
        self.mock_repo.list_by_user.return_value = []
        # Mock conn for SQL COUNT(*) capacity check
        mock_count_cursor = Mock()
        mock_count_cursor.fetchone.return_value = (0,)
        self.mock_repo.conn = Mock()
        self.mock_repo.conn.execute.return_value = mock_count_cursor  # Always return a real list for list_by_user
        self.mock_user_repo = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()
        self.mock_engine.compute_cost.return_value = 0  # Ensure compute_cost returns int
        self.mock_xp = Mock()
        self.mock_xp.calculate_level.return_value = 1
        self.service = CircuitService(
            self.mock_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )
    def test_save_circuit_success(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": ["AND"]})
        payload = {
            "name": "TestCircuit",
            "cost": 10,
            "structure_json": structure_json,
        }

        saved_circuit = Circuit(
            id=1,
            user_id=1,
            name="TestCircuit",
            cost=10,
            structure_json=structure_json,
        )
        self.mock_repo.create.return_value = saved_circuit

        # Mock user object with xp attribute for arsenal limit logic
        mock_user = Mock()
        mock_user.xp = 0
        self.mock_user_repo.get_by_id.return_value = mock_user
        # Ensure list_by_user returns a real list of Circuit objects
        self.mock_repo.list_by_user.return_value = [saved_circuit]
        # Ensure get_arsenal_limit returns an int
        self.mock_xp.get_arsenal_limit.return_value = 5

        result = self.service.save_circuit("valid_token", payload)

        assert result["id"] == 1
        assert result["name"] == "TestCircuit"
        assert result["cost"] == 10
        self.mock_auth.require_user_id.assert_called_once_with("valid_token")
        self.mock_repo.create.assert_called_once()

    def test_save_circuit_with_defaults(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": []})
        payload = {
            "name": "DefaultCircuit",
            "structure_json": structure_json,
        }

        saved_circuit = Circuit(
            id=1,
            user_id=1,
            name="DefaultCircuit",
            cost=0,
            structure_json=structure_json,
        )
        self.mock_repo.create.return_value = saved_circuit
        # Mock user object with xp attribute for arsenal limit logic
        mock_user = Mock()
        mock_user.xp = 0
        self.mock_user_repo.get_by_id.return_value = mock_user
        # Ensure list_by_user returns a real list of Circuit objects
        self.mock_repo.list_by_user.return_value = [saved_circuit]
        # Ensure get_arsenal_limit returns an int
        self.mock_xp.get_arsenal_limit.return_value = 5

        result = self.service.save_circuit("valid_token", payload)
        assert result["id"] == 1

    def test_save_circuit_success(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": ["AND"]})
        payload = {
            "name": "TestCircuit",
            "cost": 10,
            "structure_json": structure_json,
        }

        saved_circuit = Circuit(
            id=1,
            user_id=1,
            name="TestCircuit",
            cost=10,
            structure_json=structure_json,
        )
        self.mock_repo.create.return_value = saved_circuit

        # Mock user object with xp attribute for arsenal limit logic
        mock_user = Mock()
        mock_user.xp = 0
        self.mock_user_repo.get_by_id.return_value = mock_user
        # Ensure list_by_user returns a real list of Circuit objects
        self.mock_repo.list_by_user.return_value = [saved_circuit]
        # Ensure get_arsenal_limit returns an int
        self.mock_xp.get_arsenal_limit.return_value = 5

        result = self.service.save_circuit("valid_token", payload)

        assert result["id"] == 1
        assert result["name"] == "TestCircuit"
        assert result["cost"] == 10
        self.mock_auth.require_user_id.assert_called_once_with("valid_token")
        self.mock_repo.create.assert_called_once()

    def test_save_circuit_with_defaults(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": []})
        payload = {
            "name": "DefaultCircuit",
            "structure_json": structure_json,
        }

        saved_circuit = Circuit(
            id=1,
            user_id=1,
            name="DefaultCircuit",
            cost=0,
            structure_json=structure_json,
        )
        self.mock_repo.create.return_value = saved_circuit
        # Mock user object with xp attribute for arsenal limit logic
        mock_user = Mock()
        mock_user.xp = 0
        self.mock_user_repo.get_by_id.return_value = mock_user
        # Ensure list_by_user returns a real list of Circuit objects
        self.mock_repo.list_by_user.return_value = [saved_circuit]
        # Ensure get_arsenal_limit returns an int
        self.mock_xp.get_arsenal_limit.return_value = 5

        result = self.service.save_circuit("valid_token", payload)
        assert result["id"] == 1

    def test_save_circuit_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")
        payload = {"name": "Test", "cost": 10, "structure_json": json.dumps({})}

        with pytest.raises(ValidationError):
            self.service.save_circuit("invalid_token", payload)


class TestCircuitServiceListMyCircuits:
    def setup_method(self):
        self.mock_repo = Mock(spec=CircuitRepo)
        self.mock_repo.list_by_user.return_value = []
        # Mock conn for SQL COUNT(*) capacity check
        mock_count_cursor = Mock()
        mock_count_cursor.fetchone.return_value = (0,)
        self.mock_repo.conn = Mock()
        self.mock_repo.conn.execute.return_value = mock_count_cursor
        self.mock_user_repo = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        self.mock_xp.calculate_level.return_value = 1
        self.service = CircuitService(
            self.mock_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_list_my_circuits_success(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": []})
        circuits = [
            Circuit(id=1, user_id=1, name="Circuit1", cost=10, structure_json=structure_json),
            Circuit(id=2, user_id=1, name="Circuit2", cost=20, structure_json=structure_json),
        ]
        self.mock_repo.list_by_user.return_value = circuits

        result = self.service.list_my_circuits("valid_token")

        assert len(result) == 2
        assert result[0]["name"] == "Circuit1"
        assert result[1]["name"] == "Circuit2"
        self.mock_auth.require_user_id.assert_called_once_with("valid_token")
        self.mock_repo.list_by_user.assert_called_once_with(1)

    def test_list_my_circuits_empty(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_repo.list_by_user.return_value = []

        result = self.service.list_my_circuits("valid_token")

        assert result == []

    def test_list_my_circuits_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.list_my_circuits("invalid_token")


class TestCircuitServiceGetCircuit:
    def setup_method(self):
        self.mock_repo = Mock(spec=CircuitRepo)
        self.mock_repo.list_by_user.return_value = []
        # Mock conn for SQL COUNT(*) capacity check
        mock_count_cursor = Mock()
        mock_count_cursor.fetchone.return_value = (0,)
        self.mock_repo.conn = Mock()
        self.mock_repo.conn.execute.return_value = mock_count_cursor
        self.mock_user_repo = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        self.mock_xp.calculate_level.return_value = 1
        self.service = CircuitService(
            self.mock_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_get_circuit_success(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": []})
        circuit = Circuit(
            id=1, user_id=1, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_repo.get_by_id.return_value = circuit

        result = self.service.get_circuit("valid_token", 1)

        assert result["id"] == 1
        assert result["name"] == "TestCircuit"
        self.mock_repo.get_by_id.assert_called_once_with(1)

    def test_get_circuit_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError) as exc_info:
            self.service.get_circuit("valid_token", 999)
        assert "not found" in str(exc_info.value).lower()

    def test_get_circuit_forbidden(self):
        self.mock_auth.require_user_id.return_value = 1
        structure_json = json.dumps({"gates": []})
        circuit = Circuit(
            id=1, user_id=2, name="TestCircuit", cost=10, structure_json=structure_json
        )
        self.mock_repo.get_by_id.return_value = circuit

        with pytest.raises(ValidationError) as exc_info:
            self.service.get_circuit("valid_token", 1)
        assert "permission" in str(exc_info.value).lower()

    def test_get_circuit_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.get_circuit("invalid_token", 1)


class TestCircuitServiceDeleteCircuit:
    def setup_method(self):
        self.mock_repo = Mock(spec=CircuitRepo)
        self.mock_repo.list_by_user.return_value = []
        # Mock conn for SQL COUNT(*) capacity check
        mock_count_cursor = Mock()
        mock_count_cursor.fetchone.return_value = (0,)
        self.mock_repo.conn = Mock()
        self.mock_repo.conn.execute.return_value = mock_count_cursor
        self.mock_user_repo = Mock()
        self.mock_auth = Mock(spec=AuthService)
        self.mock_engine = Mock()
        self.mock_xp = Mock()
        self.mock_xp.calculate_level.return_value = 1
        self.service = CircuitService(
            self.mock_repo,
            self.mock_user_repo,
            self.mock_auth,
            self.mock_engine,
            self.mock_xp,
        )

    def test_delete_circuit_success(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_repo.delete.return_value = True

        result = self.service.delete_circuit("valid_token", 1)

        assert result["ok"] is True
        self.mock_repo.delete.assert_called_once_with(1, 1)

    def test_delete_circuit_not_found(self):
        self.mock_auth.require_user_id.return_value = 1
        self.mock_repo.delete.return_value = False

        with pytest.raises(ValidationError) as exc_info:
            self.service.delete_circuit("valid_token", 999)
        assert "not found" in str(exc_info.value).lower()

    def test_delete_circuit_unauthorized(self):
        self.mock_auth.require_user_id.side_effect = ValidationError("unauthorized")

        with pytest.raises(ValidationError):
            self.service.delete_circuit("invalid_token", 1)
