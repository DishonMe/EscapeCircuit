from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Union
import json

from Backend.DomainLayer.Exceptions import ValidationError
from Backend.DomainLayer.Circuit import Circuit
from Backend.ServiceLayer.logicEngineService import logicEngineService


class SimulateCircuitReq(BaseModel):
    inputs: Dict[str, int]
    placed: List[Dict[str, Any]]
    wires: List[Dict[str, Any]]
    custom_pieces: List[Dict[str, Any]] = []


class SimulateSequenceReq(BaseModel):
    input_stream: List[Dict[str, int]]
    placed: List[Dict[str, Any]]
    wires: List[Dict[str, Any]]
    custom_pieces: List[Dict[str, Any]] = []


def build_debugger_router(logic_engine: logicEngineService) -> APIRouter:
    router = APIRouter(prefix="/debugger", tags=["debugger"])

    @router.post("/simulate-circuit")
    def simulate_circuit(req: SimulateCircuitReq):
        """
        Simulate a circuit with given inputs and return the outputs.
        Used by puzzle creators to validate their solution before saving.
        """
        try:
            print(f"[DEBUGGER_SIM] === SIMULATE CIRCUIT ===")
            print(f"[DEBUGGER_SIM] Inputs: {req.inputs}")
            print(f"[DEBUGGER_SIM] Placed components: {len(req.placed)}")
            print(f"[DEBUGGER_SIM] Wires: {len(req.wires)}")
            print(f"[DEBUGGER_SIM] Custom pieces received: {len(req.custom_pieces)}")
            for i, piece in enumerate(req.custom_pieces):
                print(f"[DEBUGGER_SIM]   Piece {i}: name={piece.get('name')}, num_inputs={piece.get('num_inputs')}, num_outputs={piece.get('num_outputs')}")
                print(f"[DEBUGGER_SIM]   Piece {i} truth_table: {piece.get('truth_table')}")
            
            # Convert custom pieces to arsenal format for the logic engine
            arsenal_pieces = {}
            for piece in req.custom_pieces:
                piece_name = piece.get('name', '')
                if piece_name:
                    truth_table = piece.get('truth_table', {})
                    print(f"[DEBUGGER_SIM] Converting piece '{piece_name}' to arsenal format")
                    print(f"[DEBUGGER_SIM]   truth_table (before dump): {truth_table}")
                    arsenal_pieces[piece_name] = {
                        "truth_table": json.dumps(truth_table),
                        "num_inputs": piece.get('num_inputs', 0),
                        "num_outputs": piece.get('num_outputs', 0),
                    }
                    print(f"[DEBUGGER_SIM]   arsenalified: {arsenal_pieces[piece_name]}")
            print(f"[DEBUGGER_SIM] Final arsenal_pieces keys: {list(arsenal_pieces.keys())}")
            
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
            
            # Call logic engine to simulate the circuit, passing custom pieces as arsenal
            outputs = logic_engine.evaluate(temp_circuit, req.inputs, data={"_arsenal_pieces": arsenal_pieces})
            print(f"[DEBUGGER_SIM] Simulation outputs: {outputs}")
            
            return {"outputs": outputs}
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

    @router.post("/simulate-sequence")
    def simulate_sequence(req: SimulateSequenceReq):
        """
        Simulate a sequential circuit with a stream of inputs.
        Returns outputs for each cycle, preserving state through DFFs.
        Used by puzzle creators to validate sequential circuits.
        """
        try:
            print(f"[DEBUGGER] === SIMULATE SEQUENCE ===")
            print(f"[DEBUGGER] Input stream length: {len(req.input_stream)}")
            print(f"[DEBUGGER] Input stream: {req.input_stream}")
            print(f"[DEBUGGER] Placed components: {len(req.placed)}")
            print(f"[DEBUGGER] Wires: {len(req.wires)}")
            print(f"[DEBUGGER] Custom pieces: {len(req.custom_pieces)}")
            
            # Convert custom pieces to arsenal format for the logic engine
            arsenal_pieces = {}
            for piece in req.custom_pieces:
                piece_name = piece.get('name', '')
                if piece_name:
                    arsenal_pieces[piece_name] = {
                        "truth_table": json.dumps(piece.get('truth_table', {})),
                        "num_inputs": piece.get('num_inputs', 0),
                        "num_outputs": piece.get('num_outputs', 0),
                    }
            
            structure_json = json.dumps({
                "placedComponents": req.placed,
                "wires": req.wires,
            })
            
            # Create a temporary Circuit object
            temp_circuit = Circuit(
                id=0,
                user_id=0,
                name="temp-seq-sim",
                cost=0,
                structure_json=structure_json,
                is_arsenal=False,
            )
            
            # Extract DFF component IDs from circuit structure
            structure = json.loads(structure_json)
            dff_ids = []
            placed_components = structure.get("placedComponents", [])
            for comp in placed_components:
                if comp.get("componentId") == "DFF" or comp.get("type") == "DFF":
                    dff_ids.append(comp["id"])
            
            print(f"[DEBUGGER] DFF IDs found: {dff_ids}")
            
            # Simulate the sequence, maintaining state across cycles
            current_state = {str(did): 0 for did in dff_ids}
            cycle_outputs = {f"cycle_{i}": {} for i in range(len(req.input_stream))}
            
            for cycle_idx, cycle_input in enumerate(req.input_stream):
                print(f"[DEBUGGER] Cycle {cycle_idx}: input={cycle_input}, state={current_state}")
                
                # Merge current cycle inputs with DFF state
                full_inputs = cycle_input.copy()
                full_inputs.update(current_state)
                
                print(f"[DEBUGGER]   Full inputs for eval: {full_inputs}")
                
                # Simulate this cycle, passing custom pieces as arsenal
                outputs = logic_engine.evaluate(temp_circuit, full_inputs, data={"_arsenal_pieces": arsenal_pieces})
                
                # Filter outputs: exclude DFF _next values (internal state), keep only puzzle outputs
                filtered_outputs = {k: v for k, v in outputs.items() if not k.endswith('_next')}
                cycle_outputs[f"cycle_{cycle_idx}"] = filtered_outputs
                
                print(f"[DEBUGGER]   Raw cycle outputs: {outputs}")
                print(f"[DEBUGGER]   Filtered outputs (for eval_map): {filtered_outputs}")
                
                # Update state for next cycle (extract DFF next values)
                for did in dff_ids:
                    next_val = outputs.get(f"{did}_next")
                    current_state[str(did)] = next_val if next_val is not None else 0
                    print(f"[DEBUGGER]   DFF {did}_next = {next_val} -> state[{did}] = {current_state[str(did)]}")
            
            print(f"[DEBUGGER] Final cycle_outputs: {cycle_outputs}")
            return {"cycle_outputs": cycle_outputs}
        except ValidationError as e:
            print(f"[DEBUGGER] ValidationError: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            print(f"[DEBUGGER] Exception: {str(e)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Sequence simulation failed: {str(e)}")

    return router
