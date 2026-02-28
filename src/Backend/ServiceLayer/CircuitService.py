import sqlite3
from typing import Any, Dict, List

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Enums import GateType
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer._db import transaction
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.ServiceLayer.XPService import XPService


class CircuitService:
    """Circuit (arsenal) management.

    Requirements implemented here:
    - Every call authenticates via AuthService.
    - Server-side cost calculation (ignore client-provided cost).
    - Enforce that saved circuits use only basic gates (no action gate / unknown gates).
    - Enforce arsenal capacity based on user's level/xp.
    """

    def __init__(
        self,
        circuit_repo: CircuitRepo,
        user_repo: UserRepo,
        auth_service: AuthService,
        engine: logicEngineService,
        xp_service: XPService,
    ):
        self.repo = circuit_repo
        self.user_repo = user_repo
        self.auth = auth_service
        self.engine = engine
        self.xp = xp_service

    def save_circuit(self, session_token: str, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)

        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationError("Circuit name is required. Please provide a name for your circuit.")

        structure_json = payload.get("structure_json") or ""
        if not isinstance(structure_json, str) or not structure_json.strip():
            raise ValidationError("Circuit structure (JSON) is required. Please provide a valid circuit structure.")

        # Enforce arsenal limit based on XP/level using SQL COUNT to prevent TOCTOU bypass.
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("Your user account could not be found. Please log in again.")
        limit = self.xp.get_arsenal_limit(user.xp)

        # Validate gate usage & compute cost server-side.
        allowed_basic = {g.value for g in GateType}
        self.engine.validate_gate_usage(structure_json, allowed_basic=allowed_basic)
        cost = self.engine.compute_cost(structure_json)

        c = Circuit(
            id=0,
            user_id=int(user_id),
            name=name,
            cost=int(cost),
            structure_json=structure_json,
        )

        # Wrap capacity check + insert in IMMEDIATE transaction to prevent TOCTOU
        try:
            with transaction(self.repo.conn):
                count_row = self.repo.conn.execute(
                    "SELECT COUNT(*) FROM circuits WHERE user_id = ?", (int(user_id),)
                ).fetchone()
                current_count = count_row[0] if count_row else 0
                if current_count >= limit:
                    raise ValidationError(f"You have reached the maximum number of arsenal pieces ({limit}). You can create more by earning XP or manage existing pieces.")
                saved = self.repo.create(c, commit=False)
        except sqlite3.IntegrityError:
            # UNIQUE(user_id, name)
            raise ValidationError("A circuit with this name already exists. Please choose a different name or delete the existing one.")

        return saved.to_dict()

    def list_my_circuits(self, session_token: str) -> List[dict]:
        user_id = self.auth.require_user_id(session_token)
        circuits = self.repo.list_by_user(user_id)
        return [c.to_dict() for c in circuits]

    def get_circuit(self, session_token: str, circuit_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        c = self.repo.get_by_id(circuit_id)
        if not c:
            raise ValidationError("Circuit not found. It may have been deleted.")
        if c.user_id != user_id:
            raise ValidationError("You do not have permission to access this circuit.")
        return c.to_dict()

    def delete_circuit(self, session_token: str, circuit_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        ok = self.repo.delete(circuit_id, user_id)
        if not ok:
            raise ValidationError("Circuit not found or you do not own this circuit. Please verify the circuit ID and try again.")
        return {"ok": True}
