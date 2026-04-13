from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Union, List, Optional

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.ServiceLayer.ArsenalService import ArsenalService
from Backend.ServiceLayer.SolvingService import SolvingService
from Backend.APILayer.auth_utils import verify_token


class SaveArsenalPieceReq(BaseModel):
    name: str
    num_inputs: int
    num_outputs: int
    structure_json: str
    description: str = ""  # CRITICAL: Description field was being silently dropped by Pydantic!
    basic_gates: str = ""  # Optional, calculated by service if not provided
    truth_table: dict = {}
    used_arsenal_pieces: List[int] = []  # IDs of other arsenal pieces used as components


class RenameArsenalPieceReq(BaseModel):
    new_name: str


class SimulateReq(BaseModel):
    solution: Dict[str, Any]
    inputs: Union[Dict[str, int], List[Dict[str, int]], Dict[str, List[int]]]
    isSequence: Optional[bool] = None


def build_arsenal_router(arsenal_service: ArsenalService, solving_service: SolvingService) -> APIRouter:
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

    @router.post("/simulate")
    def simulate(req: SimulateReq, token: str = Depends(verify_token)):
        """Simulate an arsenal piece with given inputs (no puzzle required)"""
        try:
            # Determine if it's a sequence simulation
            is_sequence = req.isSequence if req.isSequence is not None else (
                isinstance(req.inputs, dict) and 
                any(isinstance(v, list) for v in req.inputs.values())
            )
            # Use puzzle_id=0 as a placeholder since this is for an arsenal piece, not a puzzle
            return solving_service.simulate_solution(token, 0, req.solution, req.inputs, is_sequence=is_sequence)
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router
