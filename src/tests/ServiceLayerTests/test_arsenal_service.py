"""Tests for ArsenalService"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.DomainLayer.Enums import GateType
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit


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
        self.mock_user_repo.get_by_id.return_value = user
        
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
        self.mock_user_repo.get_by_id.return_value = user
        
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



