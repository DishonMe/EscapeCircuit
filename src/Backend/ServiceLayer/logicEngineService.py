import json
from typing import Dict, Any, Set

from Backend.DomainLayer.Circuit import Circuit
from Backend.DomainLayer.Exceptions import ValidationError


class logicEngineService:
    """
    Minimal evaluator + helpers for:
    - cost calculation
    - gate validation
    - essential conditions (has entry for each official input)
    """

    # ---------- existing evaluate ----------
    def evaluate(self, circuit: Circuit, inputs: Dict[str, int]) -> Dict[str, int]:
        data = self._load(circuit.structure_json)
        
        # Check if this is a simulation-ready circuit (from frontend solution)
        # It will have 'wires' and 'placedComponents' (or 'components')
        if "wires" in data and ("placedComponents" in data or "components" in data):
            arsenal_pieces = data.get("_arsenal_pieces", {})
            return self.simulate(data, inputs, arsenal_pieces)
            
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':')) 

        if isinstance(data.get("eval_map"), dict):
            if key not in data["eval_map"]:
                raise ValidationError("no eval_map entry for inputs")
            out = data["eval_map"][key]
            if not isinstance(out, dict):
                raise ValidationError("eval_map output must be dict")
            return {str(k): int(v) for k, v in out.items()}

        if isinstance(data.get("truth_table"), dict):
            tt = data["truth_table"]
            if key not in tt:
                raise ValidationError("truth_table missing entry")
            out = tt[key]
            if not isinstance(out, dict):
                raise ValidationError("truth_table output must be dict")
            return {str(k): int(v) for k, v in out.items()}

        # Sequential circuit support (Mealy machine)
        if isinstance(data.get("mealy_map"), dict) and data.get("type") == "sequential_riddle":
            mealy_map = data["mealy_map"]
            if key not in mealy_map:
                raise ValidationError(f"no mealy_map entry for inputs and state: {key}")
            transition = mealy_map[key]
            if not isinstance(transition, dict):
                raise ValidationError("mealy_map transition must be dict")
            
            # Return both outputs and next state values
            result = {}
            for k, v in transition.items():
                result[str(k)] = int(v)
            return result

        raise ValidationError("logic engine format not supported")

    # ---------- Simulation Logic ----------
    def simulate(self, data: Dict[str, Any], inputs: Dict[str, int], arsenal_pieces: Dict[str, Any] = None) -> Dict[str, int]:
        """
        Simulates combinatorial circuit.
        data: parsed JSON containing 'placedComponents' and 'wires'.
        inputs: dict {"A": 0, "B": 1...}
        arsenal_pieces: dict mapping placed component ID -> arsenal piece metadata
        """
        if arsenal_pieces is None:
            arsenal_pieces = {}
        # 1. Build Graph
        # Nodes are (componentId, portId) -> value (0/1/None)
        # But wires connect (componentId, pinIndex)??
        # Frontend wire: from: {componentId, pinIndex, portId}, to: ...
        
        placed = data.get("placedComponents", [])
        if not placed:
            placed = data.get("components", []) # fallback
            
        wires = data.get("wires", [])
        
        # Map component ID to Type
        # Frontend placed component has { compId, componentId (type usually or reference to catalog) }
        # Re-check Frontend types:
        # PlacedComponent = { id: string, componentId: string ... }
        # The 'componentId' in PlacedComponent is the TYPE ID (e.g. "AND", "OR") unless it's a special component.
        # We assume standard gates have IDs "AND", "OR", etc.
        
        comp_types = {} 
        for p in placed:
            comp_types[p["id"]] = p["componentId"]
            
        # State: map of "ComponentID:PortID" or "ComponentID:PinIndex" -> Value
        # Using string keys for simplicity
        # IO components are tricky: "IO:IN:A" -> we treat "A" as the input.
        # Wait, PuzzleWorkstation wires use "IO:IN:A", "IO:OUT:S" as componentIds.
        
        signals = {} # Key: WireID or NetID -> Value. 
        # Actually easier to map (CompId, PinIdx) -> NetID.
        
        # Netlist construction
        # Disjoint Set Union or similar to merge connected pins into Nets
        parent = {}
        
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i])
            return parent[i]
            
        def union(i, j):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j
                
        # Initialize pins from wires
        pins = set()
        
        # Helper to get unique pin key
        def get_pin_key(endpoint):
            # endpoint has componentId and pinIndex (or portId)
            # We use componentId and pinIndex as primary key if available
            c = endpoint.get("componentId")
            idx = endpoint.get("pinIndex", 0)
            return f"{c}#{idx}"
            
        for w in wires:
             u = get_pin_key(w["from"])
             v = get_pin_key(w["to"])
             if u not in parent: parent[u] = u
             if v not in parent: parent[v] = v
             union(u, v)
             pins.add(u)
             pins.add(v)
             
        # Also need to track pins of components that might NOT be wired? No, they don't matter.
        
        # Simulation State: NetID -> Value (0 or 1, None if unknown)
        net_values = {}
        
        # 2. Iterate (Relaxation)
        # Combinatorial logic: multiple passes until stable.
        # Limit iterations to avoid infinite loops (oscillations)
        MAX_ITER = 50 
        
        # Pre-set Inputs
        # Inputs are typically represented as components like "IO:IN:A"
        # Or wires connected to them.
        for input_name, val in inputs.items():
            # In PuzzleWorkstation, inputs are "IO:IN:A". Port 0 usually.
            comp_id = f"IO:IN:{input_name}"
            pk = f"{comp_id}#0"
            if pk in parent:
                root = find(pk)
                net_values[root] = val

        # Pre-set State (DFF Outputs)
        for p in placed:
            cid = p["id"]
            ctype = comp_types.get(cid, "")
            if ctype == "DFF":
                # Check if we have a current state value for this DFF
                # Pin 1 = Q (Output). We set it using the value from 'inputs' (the state history)
                val = inputs.get(cid, 0)
                pk = f"{cid}#1"
                if pk in parent:
                    root = find(pk)
                    net_values[root] = val
                
        # Iteration
        for _ in range(MAX_ITER):
            changed = False
            
            # Evaluate every component
            for p in placed:
                cid = p["id"]
                ctype = comp_types.get(cid, "")
                
                # Get input values
                # We need to know which pin is input/output.
                # Hardcoded gate definitions for now (matching Workstation hardcoded logic approx)
                # AND/OR/XOR/NAND: pins 0,1 are IN. pin 3 (or 2) is OUT.
                # Wait, Workstation logic:
                # 3-pin gates (AND, OR, ...): IN0(0), IN1(1), OUT0(3?) NO.
                # puzzle-workstation.tsx hardcoded:
                # AND: Ports at row0/col0, row1/col0 -> Pins 0, 1?
                # Actually we need exact Pin Index mapping.
                # Frontend uiCatalog construction (Line 142):
                # AND: ports[0]=IN0, ports[1]=IN1, ports[2]=OUT0.
                # So Pins 0, 1 are Inputs. Pin 2 is Output.
                # NOT: ports[0]=IN0, ports[1]=OUT0.
                
                # Determine gate behavior
                inputs_vals = []
                out_pin_idx = -1
                
                if ctype in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR"):
                    # 2 inputs, 1 output (index 2)
                    p0 = find(f"{cid}#0") if f"{cid}#0" in parent else None
                    p1 = find(f"{cid}#1") if f"{cid}#1" in parent else None
                    out_pin_idx = 2
                    
                    v0 = net_values.get(p0)
                    v1 = net_values.get(p1)
                    inputs_vals = [v0, v1]
                    
                elif ctype in ("NOT", "DELAY", "BUF"):
                    # 1 input, 1 output (index 1)
                    p0 = find(f"{cid}#0") if f"{cid}#0" in parent else None
                    out_pin_idx = 1
                    
                    v0 = net_values.get(p0)
                    inputs_vals = [v0]
                elif cid in arsenal_pieces:
                    # Check if this is an arsenal piece
                    arsenal_info = arsenal_pieces[cid]
                    truth_table_str = arsenal_info.get("truth_table", "{}")
                    num_inputs = arsenal_info.get("num_inputs", 0)
                    num_outputs = arsenal_info.get("num_outputs", 0)
                    
                    try:
                        truth_table = json.loads(truth_table_str) if isinstance(truth_table_str, str) else truth_table_str
                        
                        # Build input key for the truth table
                        # Truth table keys are binary strings like "00", "01", "10", "11"
                        input_bits = []
                        for i in range(num_inputs):
                            pk = find(f"{cid}#{i}") if f"{cid}#{i}" in parent else None
                            val = net_values.get(pk)
                            if val is None:
                                break
                            input_bits.append(str(int(val)))
                        
                        if len(input_bits) == num_inputs:
                            # Look up in truth table using binary string key
                            key = "".join(input_bits)  # e.g. "0011" for inputs 0,0,1,1
                            if key in truth_table:
                                outputs = truth_table[key]
                                # Set all output pins based on the truth table
                                if isinstance(outputs, dict):
                                    for out_idx in range(num_outputs):
                                        out_key = f"out{out_idx}"
                                        if out_key in outputs:
                                            new_out = outputs[out_key]
                                            pk_out = f"{cid}#{num_inputs + out_idx}"
                                            if pk_out in parent:
                                                root = find(pk_out)
                                                if net_values.get(root) != new_out:
                                                    net_values[root] = new_out
                                                    changed = True
                    except Exception as e:
                        # If truth table evaluation fails, skip this component
                        pass
                    # Skip to next component (don't compute gate)
                    continue
                else:
                    # Unknown or IO -> skip
                    continue
                    
                # Compute Logic
                new_out = self._compute_gate(ctype, inputs_vals)
                
                # Update Output Net
                if new_out is not None and out_pin_idx != -1:
                    pk_out = f"{cid}#{out_pin_idx}"
                    if pk_out in parent:
                        root = find(pk_out)
                        if net_values.get(root) != new_out:
                            if net_values.get(root) is not None and net_values.get(root) != new_out:
                                # Contention (Short circuit) or oscillation
                                # For simulation, last writer wins or keep iterating. A strict engine might error.
                                pass 
                            net_values[root] = new_out
                            changed = True
            
            if not changed:
                break
                
        # 3. Read Outputs
        # Outputs are components "IO:OUT:S". Port 0.
        results = {}
        # We need to know expected output names. 
        # But we only return mapped outputs.
        # Find all keys in parent that start with IO:OUT
        
        # We scan all pins or just construct from known outputs if we had them.
        # We can scan the parent keys.
        
        # Or better: The test case inputs has keys, expected outputs has keys.
        # We should try to read all "IO:OUT:*" signals.
        
        possible_roots = set(parent.keys())
        for pk in possible_roots:
            if pk.startswith("IO:OUT:"):
                # format: IO:OUT:Name#0
                parts = pk.split("#")[0].split(":")
                if len(parts) == 3:
                     name = parts[2]
                     root = find(pk)
                     val = net_values.get(root, 0) # Default to 0 if floating?
                     # Floating outputs usually 0 or X. Let's say 0 for safety.
                     results[name] = val if val is not None else 0

        # 4. Capture Next State (DFF Inputs)
        for p in placed:
            cid = p["id"]
            ctype = comp_types.get(cid, "")
            if ctype == "DFF":
                # Pin 0 = D (Input)
                pk_in = f"{cid}#0"
                d_val = 0
                if pk_in in parent:
                    root = find(pk_in)
                    v = net_values.get(root)
                    if v is not None:
                        d_val = v
                
                results[f"{cid}_next"] = d_val
                     
        return results

    def _compute_gate(self, gtype: str, inputs: list) -> int | None:
        # None if any input is None (unknown/floating)
        if any(v is None for v in inputs):
            return None
            
        a = inputs[0]
        b = inputs[1] if len(inputs) > 1 else 0
        
        if gtype == "AND": return 1 if (a and b) else 0
        if gtype == "OR":  return 1 if (a or b) else 0
        if gtype == "XOR": return 1 if (a != b) else 0
        if gtype == "NAND": return 0 if (a and b) else 1
        if gtype == "NOR": return 0 if (a or b) else 1
        if gtype == "XNOR": return 0 if (a != b) else 1
        if gtype == "NOT": return 1 if (not a) else 0
        if gtype == "DELAY": return a
        if gtype == "BUF": return a
        
        return None

    # ---------- NEW helpers used by services ----------
    def _load(self, structure_json: str) -> Dict[str, Any]:
        try:
            data = json.loads(structure_json)
        except Exception:
            raise ValidationError("invalid circuit json")
        if not isinstance(data, dict):
            raise ValidationError("invalid circuit json")
        return data

    def extract_used_gates(self, structure_json: str) -> Set[str]:
        """
        Flexible extraction to support multiple frontend schemas.
        Supported shapes (any of them):
        - {"used_gates": ["AND","NOT"]}
        - {"gates_counts": {"AND":3,"NOT":2}}
        - {"components":[{"type":"AND"}, ...]}
        """
        data = self._load(structure_json)

        if isinstance(data.get("used_gates"), list):
            return {str(x) for x in data["used_gates"]}

        if isinstance(data.get("gates_counts"), dict):
            return {str(k) for k in data["gates_counts"].keys()}

        if isinstance(data.get("components"), list):
            out = set()
            for c in data["components"]:
                if isinstance(c, dict) and "type" in c:
                    out.add(str(c["type"]))
            return out

        # fallback: no info
        return set()

    def extract_gate_counts(self, structure_json: str) -> dict:
        """
        Extract actual gate counts from circuit structure.
        Returns dict like {"AND": 3, "OR": 2, "NOT": 1}
        
        Supported shapes:
        - {"gates_counts": {"AND":3,"NOT":2}}
        - {"components":[{"type":"AND"}, {"type":"AND"}, ...]}
        - {"placedComponents":[{"componentId":"AND"}, ...]}
        """
        data = self._load(structure_json)
        counts = {}
        
        # Priority 1: Direct gates_counts field
        if isinstance(data.get("gates_counts"), dict):
            for gate_name, count in data["gates_counts"].items():
                counts[str(gate_name)] = int(count)
            return counts
        
        # Priority 2: Count from components array
        if isinstance(data.get("components"), list):
            for c in data["components"]:
                if isinstance(c, dict) and "type" in c:
                    gate_type = str(c["type"])
                    counts[gate_type] = counts.get(gate_type, 0) + 1
            return counts
        
        # Priority 3: Count from placedComponents (user circuit)
        if isinstance(data.get("placedComponents"), list):
            for c in data["placedComponents"]:
                if isinstance(c, dict):
                    gate_type = c.get("componentId") or c.get("type")
                    if gate_type:
                        gate_type = str(gate_type)
                        counts[gate_type] = counts.get(gate_type, 0) + 1
            return counts
        
        # fallback: empty counts
        return {}

    def compute_cost(self, structure_json: str) -> int:
        """
        ARD: cost = sum of basic gate counts + nested circuit full cost. :contentReference[oaicite:3]{index=3}
        We support:
        - gates_counts dict => sum(counts)
        - components list => len(components)
        - explicit cost/value fields if exist
        - optional nested_costs list => add them
        """
        data = self._load(structure_json)

        # explicit override if frontend already computed it safely
        for k in ("cost", "value", "computed_cost"):
            if k in data:
                try:
                    return int(data[k])
                except Exception:
                    pass

        total = 0

        if isinstance(data.get("gates_counts"), dict):
            for _, v in data["gates_counts"].items():
                try:
                    total += int(v)
                except Exception:
                    raise ValidationError("invalid gates_counts")

        elif isinstance(data.get("components"), list):
            total += len(data["components"])

        # nested circuits cost (if frontend provides)
        if isinstance(data.get("nested_costs"), list):
            for x in data["nested_costs"]:
                try:
                    total += int(x)
                except Exception:
                    raise ValidationError("invalid nested_costs")

        return int(total)

    def validate_gate_usage(self, structure_json: str, allowed_basic: Set[str]) -> None:
        used = self.extract_used_gates(structure_json)
        if not used:
            # allow empty for now (some puzzles may have 0 inputs)
            return
        illegal = used - set(allowed_basic)
        if illegal:
            raise ValidationError(f"illegal gates: {sorted(illegal)}")

    def has_entry_for_inputs(self, circuit: Circuit, inputs: Dict[str, int]) -> bool:
        data = self._load(circuit.structure_json)
        key = json.dumps(inputs, sort_keys=True, separators=(',', ':'))

        if isinstance(data.get("eval_map"), dict):
            return key in data["eval_map"]
        if isinstance(data.get("truth_table"), dict):
            return key in data["truth_table"]
        return False
