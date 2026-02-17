from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.APILayer.auth_utils import verify_token


class SaveArsenalPieceReq(BaseModel):
    name: str
    num_inputs: int
    num_outputs: int
    structure_json: str
    basic_gates: str = ""  # Optional, calculated by service if not provided
    truth_table: dict = {}


class RenameArsenalPieceReq(BaseModel):
    new_name: str


def build_arsenal_router(arsenal_service: ArsenalService) -> APIRouter:
    router = APIRouter(prefix="/arsenal", tags=["arsenal"])

    @router.post("")
    def save_piece(req: SaveArsenalPieceReq, token: str = Depends(verify_token)):
        """Save a new arsenal piece"""
        try:
            return arsenal_service.save_arsenal_piece(token, req.model_dump())
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("")
    def list_pieces(token: str = Depends(verify_token)):
        """List all arsenal pieces for the current user"""
        try:
            return arsenal_service.list_my_arsenal(token)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    @router.get("/{piece_id}")
    def get_piece(piece_id: int, token: str = Depends(verify_token)):
        """Get details of a specific arsenal piece"""
        try:
            return arsenal_service.get_arsenal_piece(token, piece_id)
        except ValidationError as e:
            code = 403 if "forbidden" in str(e).lower() else 404
            raise HTTPException(status_code=code, detail=str(e))

    @router.put("/{piece_id}")
    def rename_piece(piece_id: int, req: RenameArsenalPieceReq, token: str = Depends(verify_token)):
        """Rename an arsenal piece"""
        try:
            return arsenal_service.rename_arsenal_piece(token, piece_id, req.new_name)
        except ValidationError as e:
            code = 403 if "forbidden" in str(e).lower() else 400
            raise HTTPException(status_code=code, detail=str(e))

    @router.delete("/{piece_id}")
    def delete_piece(piece_id: int, token: str = Depends(verify_token)):
        """Delete an arsenal piece"""
        try:
            return arsenal_service.delete_arsenal_piece(token, piece_id)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @router.get("/puzzle/{puzzle_id}/available")
    def get_available_for_puzzle(puzzle_id: str, allowed_gates: str = "", token: str = Depends(verify_token)):
        """Get arsenal pieces available for a puzzle.
        
        Query params:
        - allowed_gates: comma-separated list of gate types allowed in the puzzle
        """
        try:
            gates_set = set(allowed_gates.split(",")) if allowed_gates else set()
            return arsenal_service.get_available_pieces_for_puzzle(token, gates_set)
        except ValidationError as e:
            raise HTTPException(status_code=401, detail=str(e))

    return router
