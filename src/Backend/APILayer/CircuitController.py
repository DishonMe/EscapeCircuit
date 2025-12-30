from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.CircuitService import CircuitService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")


class SaveCircuitReq(BaseModel):
    name: str
    cost: int = 0
    structure_json: str


def build_circuit_router(circuit_service: CircuitService) -> APIRouter:
    router = APIRouter(prefix="/circuits", tags=["circuits"])

    @router.get("")
    def list_my(token: str = Depends(oauth2_scheme)):
        try:
            return circuit_service.list_my_circuits(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.post("")
    def save(req: SaveCircuitReq, token: str = Depends(oauth2_scheme)):
        try:
            return circuit_service.save_circuit(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/{circuit_id}")
    def get_one(circuit_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return circuit_service.get_circuit(token, circuit_id)
        except ValidationError as e:
            code = 403 if "forbidden" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    @router.delete("/{circuit_id}")
    def delete(circuit_id: int, token: str = Depends(oauth2_scheme)):
        try:
            return circuit_service.delete_circuit(token, circuit_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return router
