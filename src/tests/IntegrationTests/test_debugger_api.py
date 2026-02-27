"""Integration tests for the Debugger API (/debugger endpoints).

These endpoints are publicly accessible (no auth required).
"""
import json


class TestSimulateCircuit:
    def test_simulate_empty_circuit(self, client):
        resp = client.post("/debugger/simulate-circuit", json={
            "inputs": {"A": 1},
            "placed": [],
            "wires": [],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "outputs" in body

    def test_simulate_no_auth_required(self, client):
        """Debugger endpoints should work without a token."""
        resp = client.post("/debugger/simulate-circuit", json={
            "inputs": {"A": 0},
            "placed": [],
            "wires": [],
        })
        # Should not return 401
        assert resp.status_code != 401


class TestSimulateSequence:
    def test_simulate_empty_sequence(self, client):
        resp = client.post("/debugger/simulate-sequence", json={
            "input_stream": [{"A": 1}, {"A": 0}],
            "placed": [],
            "wires": [],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "cycle_outputs" in body
        assert "cycle_0" in body["cycle_outputs"]
        assert "cycle_1" in body["cycle_outputs"]

    def test_simulate_sequence_no_auth(self, client):
        resp = client.post("/debugger/simulate-sequence", json={
            "input_stream": [{"A": 0}],
            "placed": [],
            "wires": [],
        })
        assert resp.status_code != 401
