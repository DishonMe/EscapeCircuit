from typing import Dict, Any, List

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.ServiceLayer.AuthService import AuthService


class CircuitService:
    def __init__(self, circuit_repo: CircuitRepo, auth_service: AuthService):
        self.repo = circuit_repo
        self.auth = auth_service

    def save_circuit(self, session_token: str, payload: Dict[str, Any]) -> dict:
        user_id = self.auth.require_user_id(session_token)
        # repo will create domain only on reads; for create we pass a domain circuit:
        from Backend.DomainLayer.Circuit import Circuit

        c = Circuit(
            id=0,
            user_id=user_id,
            name=payload.get("name", ""),
            cost=int(payload.get("cost", 0)),
            structure_json=payload.get("structure_json", ""),
        )
        saved = self.repo.create(c)
        return saved.to_dict()

    def list_my_circuits(self, session_token: str) -> List[dict]:
        user_id = self.auth.require_user_id(session_token)
        circuits = self.repo.list_by_user(user_id)
        return [c.to_dict() for c in circuits]

    def get_circuit(self, session_token: str, circuit_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        c = self.repo.get_by_id(circuit_id)
        if not c:
            raise ValidationError("circuit not found")
        if c.user_id != user_id:
            raise ValidationError("forbidden")
        return c.to_dict()

    def delete_circuit(self, session_token: str, circuit_id: int) -> dict:
        user_id = self.auth.require_user_id(session_token)
        ok = self.repo.delete(circuit_id, user_id)
        if not ok:
            raise ValidationError("circuit not found or not owned by user")
        return {"ok": True}
