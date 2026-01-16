import pytest
import json
from Backend.ServiceLayer.logicEngineService import logicEngineService
from Backend.DomainLayer.Circuit import Circuit

class TestLogicEngineSimulation:
    def setup_method(self):
        self.service = logicEngineService()

    def test_simulate_simple_and_gate(self):
        structure = {
            "placedComponents": [
                {"id": "IO:IN:A", "componentId": "IO:IN:A"},
                {"id": "IO:IN:B", "componentId": "IO:IN:B"},
                {"id": "c3", "componentId": "AND"},
                {"id": "IO:OUT:Out", "componentId": "IO:OUT:Out"}
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0}, "to": {"componentId": "c3", "pinIndex": 0}},
                {"from": {"componentId": "IO:IN:B", "pinIndex": 0}, "to": {"componentId": "c3", "pinIndex": 1}},
                {"from": {"componentId": "c3", "pinIndex": 2}, "to": {"componentId": "IO:OUT:Out", "pinIndex": 0}}
            ]
        }
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        
        result = self.service.evaluate(circuit, {"A": 0, "B": 0})
        assert result["Out"] == 0
        
        result = self.service.evaluate(circuit, {"A": 0, "B": 1})
        assert result["Out"] == 0
        
        result = self.service.evaluate(circuit, {"A": 1, "B": 1})
        assert result["Out"] == 1

    def test_simulate_not_gate(self):
        structure = {
            "placedComponents": [
                {"id": "IO:IN:A", "componentId": "IO:IN:A"},
                {"id": "c2", "componentId": "NOT"},
                {"id": "IO:OUT:Out", "componentId": "IO:OUT:Out"}
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0}, "to": {"componentId": "c2", "pinIndex": 0}},
                {"from": {"componentId": "c2", "pinIndex": 1}, "to": {"componentId": "IO:OUT:Out", "pinIndex": 0}}
            ]
        }
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        
        assert self.service.evaluate(circuit, {"A": 0})["Out"] == 1
        assert self.service.evaluate(circuit, {"A": 1})["Out"] == 0

    def test_simulate_dff_next_state(self):
        structure = {
            "placedComponents": [
                {"id": "IO:IN:In", "componentId": "IO:IN:In"},
                {"id": "dff1", "componentId": "DFF"},
                {"id": "IO:OUT:Out", "componentId": "IO:OUT:Out"}
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:In", "pinIndex": 0}, "to": {"componentId": "dff1", "pinIndex": 0}}, 
                {"from": {"componentId": "dff1", "pinIndex": 1}, "to": {"componentId": "IO:OUT:Out", "pinIndex": 0}}
            ]
        }
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        
        result = self.service.evaluate(circuit, {"In": 1, "dff1": 0})
        assert result["Out"] == 0
        assert result["dff1_next"] == 1
        
        result = self.service.evaluate(circuit, {"In": 0, "dff1": 1})
        assert result["Out"] == 1
        assert result["dff1_next"] == 0

    def test_simulate_disconnected_components(self):
        structure = {
            "placedComponents": [
                {"id": "c1", "componentId": "AND"}
            ],
            "wires": []
        }
        # cost=0 added to constructor call
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        self.service.evaluate(circuit, {})

    def test_simulate_unknown_gate_type(self):
        structure = {
            "placedComponents": [
                {"id": "c1", "componentId": "UNKNOWN"}
            ],
            "wires": []
        }
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        assert self.service.evaluate(circuit, {}) == {}

    def test_extract_used_gates(self):
        assert self.service.extract_used_gates(json.dumps({"used_gates": ["AND"]})) == {"AND"}
        assert self.service.extract_used_gates(json.dumps({"gates_counts": {"NOT": 5}})) == {"NOT"}
        assert self.service.extract_used_gates(json.dumps({"components": [{"type": "XOR"}]})) == {"XOR"}
        assert self.service.extract_used_gates(json.dumps({})) == set()

    def test_validate_gate_usage(self):
        with pytest.raises(Exception) as exc:
            self.service.validate_gate_usage(json.dumps({"used_gates": ["BAD"]}), {"AND"})
        assert "illegal gates" in str(exc.value)

    def test_compute_cost(self):
        assert self.service.compute_cost(json.dumps({"cost": 100})) == 100
        assert self.service.compute_cost(json.dumps({"gates_counts": {"AND": 2}})) == 2
        assert self.service.compute_cost(json.dumps({"components": [{}, {}]})) == 2
        assert self.service.compute_cost(json.dumps({"nested_costs": [10, 20]})) == 30

    def test_simulation_convergence(self):
        structure = {
            "placedComponents": [
                {"id": "IO:IN:A", "componentId": "IO:IN:A"},
                {"id": "b1", "componentId": "BUF"},
                {"id": "b2", "componentId": "BUF"},
                {"id": "IO:OUT:Out", "componentId": "IO:OUT:Out"}
            ],
            "wires": [
                {"from": {"componentId": "IO:IN:A", "pinIndex": 0}, "to": {"componentId": "b1", "pinIndex": 0}},
                {"from": {"componentId": "b1", "pinIndex": 1}, "to": {"componentId": "b2", "pinIndex": 0}},
                {"from": {"componentId": "b2", "pinIndex": 1}, "to": {"componentId": "IO:OUT:Out", "pinIndex": 0}}
            ]
        }
        circuit = Circuit(id=1, user_id=1, name="Test", structure_json=json.dumps(structure), cost=0)
        assert self.service.evaluate(circuit, {"A": 1})["Out"] == 1
