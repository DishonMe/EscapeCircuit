import json
import sqlite3
from typing import Any, Dict, List, Set

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Enums import GateType, UserRole
from Backend.DomainLayer.Exceptions import ValidationError
from Backend.settings import (
    ARSENAL_DEFAULT_MAX_SIZE,
    ARSENAL_MAX_INPUTS,
    ARSENAL_MAX_OUTPUTS,
    ARSENAL_MIN_INPUTS,
    ARSENAL_MIN_OUTPUTS,
    ARSENAL_XP_LEVEL_TIERS,
    ARSENAL_XP_MAX_SLOTS,
)
from Backend.PersistantLayer._db import transaction
from Backend.PersistantLayer.CircuitRepo import CircuitRepo
from Backend.PersistantLayer.UserRepo import UserRepo
from Backend.ServiceLayer.AuthService import AuthService
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.ServiceLayer.XPService import XPService


class ArsenalService:
    """Arsenal (special custom circuits) management.
    
    Handles:
    - Creating custom circuit pieces (with input/output selection)
    - Calculating basic gates and truth tables
    - Managing arsenal inventory (max 10 per user initially)
    - Filtering available pieces for puzzles based on allowed gates
    - Cascading gate resolution (if arsenal piece uses another arsenal piece, flatten to basic gates)
    """

    MAX_ARSENAL_SIZE = ARSENAL_DEFAULT_MAX_SIZE
    MAX_INPUTS = ARSENAL_MAX_INPUTS
    MAX_OUTPUTS = ARSENAL_MAX_OUTPUTS
    MIN_INPUTS = ARSENAL_MIN_INPUTS
    MIN_OUTPUTS = ARSENAL_MIN_OUTPUTS

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

    def save_arsenal_piece(self, session_token: str, payload: Dict[str, Any]) -> dict:
        """Save a new custom circuit piece to arsenal.
        
        Payload should contain:
        - name: str (unique per user)
        - num_inputs: int (1-5)
        - num_outputs: int (1-3)
        - structure_json: str (the actual circuit from workstation)
        - truth_table: dict (pre-calculated by client or calculated here)
        """
        user_id = self.auth.require_user_id(session_token)
        
        # Validate name
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationError("Arsenal piece name is required. Please provide a name for your custom component.")
        
        # Validate user exists
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise ValidationError("Your user account could not be found. Please log in again.")
        is_admin = self._is_admin(user.role)
        user_level = self.xp.calculate_level(user.xp)
        max_slots = self._resolve_max_slots_for_level(user_level)

        # Validate structure_json
        structure_json = payload.get("structure_json") or ""
        if not isinstance(structure_json, str) or not structure_json.strip():
            raise ValidationError("Circuit structure (JSON) is required. Please provide a valid circuit structure.")

        try:
            structure = json.loads(structure_json)
        except (json.JSONDecodeError, ValueError):
            raise ValidationError("Invalid circuit structure. Please ensure you provide valid JSON that represents your circuit.")

        # Validate inputs and outputs
        num_inputs = payload.get("num_inputs", 0)
        num_outputs = payload.get("num_outputs", 0)

        if not isinstance(num_inputs, int) or num_inputs < self.MIN_INPUTS or num_inputs > self.MAX_INPUTS:
            raise ValidationError(f"Number of inputs must be between {self.MIN_INPUTS} and {self.MAX_INPUTS}. Adjust your circuit accordingly.")
        if not isinstance(num_outputs, int) or num_outputs < self.MIN_OUTPUTS or num_outputs > self.MAX_OUTPUTS:
            raise ValidationError(f"Number of outputs must be between {self.MIN_OUTPUTS} and {self.MAX_OUTPUTS}. Adjust your circuit accordingly.")

        # Extract and validate gates used by this arsenal piece
        # Use provided basic_gates if available, otherwise extract from structure
        basic_gates_str = payload.get("basic_gates", "")
        used_arsenal_piece_ids = payload.get("used_arsenal_pieces", [])
        
        if basic_gates_str and isinstance(basic_gates_str, str):
            try:
                basic_gates = json.loads(basic_gates_str)
                if not isinstance(basic_gates, list):
                    basic_gates = []
            except (json.JSONDecodeError, ValueError):
                basic_gates = []
            # Frontend sends direct basic gates (not including arsenal piece gates yet)
        else:
            basic_gates = self._extract_basic_gates(structure_json)

        # Calculate cost BEFORE flattening (direct gates + piece costs)
        cost = self._calculate_arsenal_cost(basic_gates, used_arsenal_piece_ids, user_id)
        
        # Now flatten basic gates with arsenal pieces for final storage
        basic_gates = self._flatten_used_arsenal_pieces(basic_gates, used_arsenal_piece_ids, user_id)

        # Get or calculate truth table
        truth_table = payload.get("truth_table")
        if truth_table is None or (isinstance(truth_table, dict) and len(truth_table) == 0):
            truth_table = self._calculate_truth_table(num_inputs, num_outputs, structure)

        if not isinstance(truth_table, dict):
            raise ValidationError("truth_table must be a dictionary")

        # Extract description from payload before creating Circuit
        description = (payload.get("description") or "").strip()

        # Create and save circuit
        arsenal_piece = Circuit(
            id=0,
            user_id=int(user_id),
            name=name,
            cost=int(cost),
            structure_json=structure_json,
            is_arsenal=True,
            basic_gates=json.dumps(basic_gates),
            truth_table=json.dumps(truth_table),
            num_inputs=num_inputs,
            num_outputs=num_outputs,
            description=description,
        )

        # Wrap capacity check + insert in IMMEDIATE transaction to prevent TOCTOU
        try:
            with transaction(self.repo.conn):
                if not is_admin:
                    current_count = self.repo.count_user_components(user_id)
                    if current_count >= max_slots:
                        raise ValidationError(
                            f"Arsenal capacity reached ({current_count}/{max_slots}). Level up to unlock more slots!"
                        )
                saved = self.repo.create(arsenal_piece, commit=False)
        except sqlite3.IntegrityError:
            # UNIQUE(user_id, name) constraint violated
            raise ValidationError("arsenal piece name already exists for this user")

        return saved.to_dict()

    def list_my_arsenal(self, session_token: str) -> List[dict]:
        """List all arsenal pieces for the current user"""
        user_id = self.auth.require_user_id(session_token)
        pieces = self.repo.list_arsenal_by_user(user_id)
        return [p.to_dict() for p in pieces]

    def get_arsenal_piece(self, session_token: str, piece_id: int) -> dict:
        """Get detailed info about an arsenal piece"""
        user_id = self.auth.require_user_id(session_token)
        piece = self.repo.get_by_id(piece_id)
        if not piece:
            raise ValidationError("arsenal piece not found")
        if piece.user_id != user_id:
            raise ValidationError("forbidden")
        if not piece.is_arsenal:
            raise ValidationError("not an arsenal piece")
        return piece.to_dict()

    def rename_arsenal_piece(self, session_token: str, piece_id: int, new_name: str) -> dict:
        """Rename an arsenal piece (must be unique per user)"""
        user_id = self.auth.require_user_id(session_token)
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValidationError("new name is required")
        
        piece = self.repo.get_by_id(piece_id)
        if not piece:
            raise ValidationError("arsenal piece not found")
        if piece.user_id != user_id:
            raise ValidationError("forbidden")
        if not piece.is_arsenal:
            raise ValidationError("not an arsenal piece")
        
        piece.name = new_name
        try:
            self.repo.update(piece)
        except sqlite3.IntegrityError:
            raise ValidationError("arsenal piece name already exists for this user")
        
        return piece.to_dict()

    def delete_arsenal_piece(self, session_token: str, piece_id: int) -> dict:
        """Delete an arsenal piece"""
        user_id = self.auth.require_user_id(session_token)
        ok = self.repo.delete(piece_id, user_id)
        if not ok:
            raise ValidationError("arsenal piece not found or not owned by user")
        return {"ok": True}

    def get_available_pieces_for_puzzle(
        self, session_token: str, allowed_gates: Set[str]
    ) -> List[dict]:
        """Get arsenal pieces available for a puzzle.
        
        A piece is available if ALL its basic gates are allowed in the puzzle.
        Handles cascading: if a piece uses another piece from the arsenal,
        the final gates list should only contain basic gates.
        """
        user_id = self.auth.require_user_id(session_token)
        arsenal = self.repo.list_arsenal_by_user(user_id)
        
        available = []
        for piece in arsenal:
            try:
                # Get the basic gates for this piece
                # If it uses other arsenal pieces, they should already be flattened
                gates = json.loads(piece.basic_gates) if piece.basic_gates else []
                gates_set = set(gates)
                
                # Check if all gates are allowed
                if gates_set.issubset(allowed_gates):
                    available.append(piece.to_circuit_component())
            except (json.JSONDecodeError, ValueError):
                # Skip pieces with invalid JSON
                continue
        
        return available

    def get_custom_pieces_for_puzzle(self, puzzle_id: int) -> List[dict]:
        """Get custom pieces created for a specific puzzle.
        
        Custom pieces are stored with puzzle_id set and is_arsenal=true.
        They are unique to the puzzle and available to all solvers.
        Always available regardless of allow_arsenal setting.
        """
        try:
            pieces = self.repo.list_custom_pieces_by_puzzle(puzzle_id)
            result = [piece.to_circuit_component() for piece in pieces]
            if result:
                print(f"✅ Custom pieces for puzzle {puzzle_id}: found {len(result)} pieces")
            return result
        except Exception as e:
            print(f"❌ ERROR getting custom pieces for puzzle {puzzle_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_arsenal_pieces_by_ids(self, piece_ids: List[int]) -> List[dict]:
        """Fetch specific Arsenal pieces by their IDs.
        
        This is used when a puzzle specifies which arsenal pieces are allowed.
        Returns the full component definitions for those pieces.
        
        Args:
            piece_ids: List of Arsenal piece IDs to fetch
            
        Returns:
            List of CircuitComponent dicts for the requested pieces
        """
        try:
            if not piece_ids:
                return []
            
            components = []
            for piece_id in piece_ids:
                try:
                    # Fetch the circuit piece by ID
                    piece = self.repo.get_by_id(piece_id)
                    if piece and piece.is_arsenal:
                        component = piece.to_circuit_component()
                        components.append(component)
                except Exception as e:
                    continue
            
            return components
        except Exception as e:
            return []

    def get_user_arsenal_filtered_by_gates(self, user_id: int, allowed_gates: Set[str]) -> List[dict]:
        """Get all arsenal pieces for a user, filtered by allowed gates.
        
        Used when a puzzle allows arsenal but doesn't specify which pieces.
        Returns only pieces whose basic gates are all in the allowed set.
        
        Args:
            user_id: Creator's user ID
            allowed_gates: Set of allowed gate types
            
        Returns:
            List of CircuitComponent dicts that use only allowed gates
        """
        try:
            if not user_id:
                return []
            
            arsenal = self.repo.list_arsenal_by_user(user_id)
            available = []
            
            for piece in arsenal:
                try:
                    # Parse the basic gates for this piece
                    gates = json.loads(piece.basic_gates) if piece.basic_gates else []
                    gates_set = set(gates)
                    
                    # Include this piece only if ALL its gates are allowed
                    if gates_set.issubset(allowed_gates):
                        available.append(piece.to_circuit_component())
                except (json.JSONDecodeError, ValueError):
                    # Skip pieces with invalid JSON
                    continue
            
            return available
        except Exception as e:
            return []

    def _resolve_max_slots_for_level(self, user_level: int) -> int:
        for max_level_inclusive, slot_count in ARSENAL_XP_LEVEL_TIERS:
            if user_level <= int(max_level_inclusive):
                return int(slot_count)
        return int(ARSENAL_XP_MAX_SLOTS)

    @staticmethod
    def _is_admin(role: Any) -> bool:
        if isinstance(role, UserRole):
            return role == UserRole.ADMIN
        return str(role).strip().lower() == UserRole.ADMIN.value

    def _extract_basic_gates(self, structure_json: str) -> List[str]:
        """Extract basic gates used in the circuit structure"""
        used = self.engine.extract_used_gates(structure_json)
        # Keep only known built-in gate values, including DFF.
        basic_gate_values = {g.value for g in GateType}
        basic = [g for g in used if g in basic_gate_values]
        return basic

    def _calculate_truth_table(
        self, num_inputs: int, num_outputs: int, structure: dict
    ) -> dict:
        """Calculate truth table by simulating the circuit for each input combination.
        
        Uses the logic engine to evaluate the circuit for all possible input combinations.
        """
        # Check if structure already has truth_table
        if "truth_table" in structure:
            return structure["truth_table"]
        
        # Check for eval_map (alternative format)
        if "eval_map" in structure:
            return structure["eval_map"]
        
        # Generate truth table by simulating the circuit
        truth_table = {}
        
        try:
            num_combinations = 2 ** num_inputs
            
            # Transform structure to match engine's expected format
            # Engine expects 'placedComponents' not 'placed'
            sim_data = {
                'placedComponents': structure.get('placed', []),
                'wires': structure.get('wires', []),
                'num_inputs': num_inputs,
                'num_outputs': num_outputs,
            }
            
            for combo_idx in range(num_combinations):
                # Convert index to binary input string
                # e.g., for 2 inputs: "00", "01", "10", "11"
                input_key = format(combo_idx, f'0{num_inputs}b')
                
                # Create inputs dict: {in0: 0, in1: 1, ...}
                inputs = {f'in{i}': int(input_key[i]) for i in range(num_inputs)}
                
                try:
                    # Simulate the circuit with these inputs
                    outputs = self.engine.simulate(sim_data, inputs)
                    
                    # Ensure outputs are in the expected format {out0: 0, out1: 1, ...}
                    formatted_outputs = {}
                    for i in range(num_outputs):
                        out_key = f'out{i}'
                        formatted_outputs[out_key] = int(outputs.get(out_key, 0))
                    
                    truth_table[input_key] = formatted_outputs
                except Exception as e:
                    # If simulation fails for this input combo, use zeros
                    truth_table[input_key] = {f'out{i}': 0 for i in range(num_outputs)}
            
            return truth_table if truth_table else {}
        except Exception as e:
            # If anything goes wrong, return empty
            return {}



    def _flatten_used_arsenal_pieces(
        self, basic_gates: List[str], used_arsenal_ids: List[int], user_id: int
    ) -> List[str]:
        """Flatten gates from used arsenal pieces into the basic gates list.
        
        When an arsenal piece uses another arsenal piece, we add all of the used piece's
        basic gates to the final basic_gates list (flattened, not nested).
        
        Args:
            basic_gates: Current list of basic gates
            used_arsenal_ids: List of arsenal piece IDs to use as components
            user_id: Current user ID (to validate ownership)
            
        Returns:
            Flattened list of basic gates including gates from used pieces
        """
        if not used_arsenal_ids:
            return basic_gates
        
        flattened = basic_gates.copy() if basic_gates else []
        
        for piece_id in used_arsenal_ids:
            # Retrieve the used arsenal piece
            piece = self.repo.get_by_id(piece_id)
            if not piece:
                raise ValidationError(f"Arsenal piece with ID {piece_id} not found")
            if piece.user_id != user_id:
                raise ValidationError(f"Arsenal piece with ID {piece_id} is not owned by you")
            if not piece.is_arsenal:
                raise ValidationError(f"Piece with ID {piece_id} is not an arsenal piece")
            
            # Extract and add its basic gates (flattened)
            try:
                piece_gates = json.loads(piece.basic_gates) if piece.basic_gates else []
                if isinstance(piece_gates, list):
                    flattened.extend(piece_gates)
            except (json.JSONDecodeError, ValueError):
                raise ValidationError(f"Invalid basic_gates format in arsenal piece {piece_id}")
        
        return flattened

    def _calculate_arsenal_cost(
        self, gates: List[str], used_arsenal_ids: List[int] = None, user_id: int = None
    ) -> int:
        """Calculate cost as sum of gate counts and used piece costs.
        
        Basic gates cost 1 each.
        Used arsenal pieces cost their computed cost (not 1).
        """
        # Count basic gates
        cost = len(gates)
        
        # Add cost of used arsenal pieces
        if used_arsenal_ids and user_id is not None:
            for piece_id in used_arsenal_ids:
                piece = self.repo.get_by_id(piece_id)
                if not piece:
                    raise ValidationError(f"Arsenal piece with ID {piece_id} not found")
                if piece.user_id != user_id:
                    raise ValidationError(f"Arsenal piece with ID {piece_id} is not owned by you")
                if not piece.is_arsenal:
                    raise ValidationError(f"Piece with ID {piece_id} is not an arsenal piece")
                
                # Add the cost of the used piece instead of 1
                cost += piece.cost
        
        return cost

