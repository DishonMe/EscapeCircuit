from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit
from Backend.ServiceLayer.logicEngineService import logicEngineService


class SimulateCircuitReq(BaseModel):
    inputs: Dict[str, int]
    placed: List[Dict[str, Any]]
    wires: List[Dict[str, Any]]


def build_debugger_router(logic_engine: logicEngineService) -> APIRouter:
    router = APIRouter(prefix="/debugger", tags=["debugger"])

    @router.post("/simulate-circuit")
    def simulate_circuit(req: SimulateCircuitReq):
        """
        Simulate a circuit with given inputs and return the outputs.
        Used by puzzle creators to validate their solution before saving.
        """
        try:
            # Convert placed/wires to structure_json format expected by logicEngineService
            # The service expects "placedComponents" and "wires"
            structure_json = json.dumps({
                "placedComponents": req.placed,  # Use "placedComponents" which simulate() expects
                "wires": req.wires,
            })
            
            # Create a temporary Circuit object for evaluation
            temp_circuit = Circuit(
                id=0,  # Temporary ID for simulation
                user_id=0,  # Temporary user ID
                name="temp-sim",
                cost=0,
                structure_json=structure_json,
                is_arsenal=False,
            )
            
            # Call logic engine to simulate the circuit
            outputs = logic_engine.evaluate(temp_circuit, req.inputs)
            
            return {"outputs": outputs}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    return router
