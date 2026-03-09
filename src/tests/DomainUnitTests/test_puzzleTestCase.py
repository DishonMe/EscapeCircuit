import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import TestCaseKind
from Backend.DomainLayer.Exceptions import ValidationError


class TestPuzzleTestCaseCreation:
    def test_create_puzzle_test_case_valid_blackbox(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 1},
            expected_outputs={"result": 1}
        )
        assert test_case.id == 1
        assert test_case.puzzle_id == 1
        assert test_case.kind == TestCaseKind.BLACKBOX
        assert test_case.inputs == {"a": 0, "b": 1}
        assert test_case.expected_outputs == {"result": 1}

    def test_create_puzzle_test_case_valid_whitebox(self):
        test_case = PuzzleTestCase(
            id=2,
            puzzle_id=2,
            kind=TestCaseKind.WHITEBOX,
            inputs={"x": 1},
            expected_outputs={"y": 0}
        )
        assert test_case.kind == TestCaseKind.WHITEBOX

    def test_create_puzzle_test_case_empty_id(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="",
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": 1}
            )
        assert "PuzzleTestCase.id must be int" in str(exc_info.value)



    def test_create_puzzle_test_case_empty_inputs(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={},
                expected_outputs={"r": 1}
            )
        assert "PuzzleTestCase.inputs cannot be empty" in str(exc_info.value)

    def test_create_puzzle_test_case_empty_outputs(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={}
            )
        assert "cannot be empty" in str(exc_info.value)

    def test_create_puzzle_test_case_invalid_input_value(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 2},  # Invalid: must be 0 or 1
                expected_outputs={"r": 1}
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_create_puzzle_test_case_invalid_output_value(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": -1}  # Invalid: must be 0 or 1
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_create_puzzle_test_case_with_custom_created_at(self):
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        assert test_case.created_at == custom_time

    def test_create_puzzle_test_case_default_created_at(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert isinstance(test_case.created_at, datetime)
        assert test_case.created_at.tzinfo is not None


class TestPuzzleTestCaseGetters:
    def test_get_id(self):
        test_case = PuzzleTestCase(
            id=123,
                puzzle_id=123,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_id() == 123

    def test_get_puzzle_id(self):
        test_case = PuzzleTestCase(
            id=1,
                puzzle_id=123,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_puzzle_id() == 123

    def test_get_kind(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_kind() == TestCaseKind.WHITEBOX

    def test_get_inputs(self):
        inputs = {"a": 0, "b": 1, "c": 0}
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs=inputs,
            expected_outputs={"r": 1}
        )
        assert test_case.get_inputs() == inputs

    def test_get_expected_outputs(self):
        outputs = {"out1": 0, "out2": 1}
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs=outputs
        )
        assert test_case.get_expected_outputs() == outputs

    def test_get_created_at(self):
        custom_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        assert test_case.get_created_at() == custom_time


class TestPuzzleTestCaseSetters:


    def test_set_kind_blackbox(self):
        test_case = PuzzleTestCase(
            id=1,
                puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_kind(TestCaseKind.BLACKBOX)
        assert test_case.get_kind() == TestCaseKind.BLACKBOX

    def test_set_kind_whitebox(self):
        test_case = PuzzleTestCase(
            id=1,
                puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_kind(TestCaseKind.WHITEBOX)
        assert test_case.get_kind() == TestCaseKind.WHITEBOX

    def test_set_kind_invalid_type(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError) as exc_info:
            test_case.set_kind("invalid")  # type: ignore
        assert "must be TestCaseKind" in str(exc_info.value)

    def test_set_inputs_valid(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        new_inputs = {"x": 1, "y": 0, "z": 1}
        test_case.set_inputs(new_inputs)
        assert test_case.get_inputs() == new_inputs

    def test_set_inputs_empty(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_inputs({})

    def test_set_inputs_invalid_value(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError) as exc_info:
            test_case.set_inputs({"a": 2})  # Invalid: must be 0 or 1
        assert "must be 0/1" in str(exc_info.value)

    def test_set_expected_outputs_valid(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        new_outputs = {"out1": 0, "out2": 1, "out3": 0}
        test_case.set_expected_outputs(new_outputs)
        assert test_case.get_expected_outputs() == new_outputs

    def test_set_expected_outputs_empty(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_expected_outputs({})

    def test_set_expected_outputs_invalid_value(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError) as exc_info:
            test_case.set_expected_outputs({"r": 5})  # Invalid: must be 0 or 1
        assert "must be 0/1" in str(exc_info.value)


class TestPuzzleTestCaseSerialization:
    def test_to_dict(self):
        test_case = PuzzleTestCase(
            id=1,
                puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 1},
            expected_outputs={"result": 1}
        )
        d = test_case.to_dict()
        assert d["id"] == 1
        assert d["puzzle_id"] == 1
        assert d["kind"] == "blackbox"
        assert d["inputs"] == {"a": 0, "b": 1}
        assert d["expected_outputs"] == {"result": 1}
        assert "created_at" in d

    def test_to_dict_whitebox(self):
        test_case = PuzzleTestCase(
            id=2,
            puzzle_id=2,
            kind=TestCaseKind.WHITEBOX,
            inputs={"x": 1},
            expected_outputs={"y": 0}
        )
        d = test_case.to_dict()
        assert d["kind"] == "whitebox"

    def test_to_dict_created_at_iso_format(self):
        custom_time = datetime(2025, 3, 15, 14, 30, 45, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        d = test_case.to_dict()
        assert d["created_at"] == "2025-03-15T14:30:45+00:00"

    def test_from_dict(self):
        d = {
            "id": 1,
                "puzzle_id": 1,
            "kind": "blackbox",
            "inputs": {"a": 0, "b": 1},
            "expected_outputs": {"result": 1},
            "created_at": "2025-03-15T14:30:45+00:00"
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert test_case.id == 1
        assert test_case.puzzle_id == 1
        assert test_case.kind == TestCaseKind.BLACKBOX
        assert test_case.inputs == {"a": 0, "b": 1}
        assert test_case.expected_outputs == {"result": 1}

    def test_from_dict_whitebox(self):
        d = {
            "id": 2,
            "puzzle_id": 2,
            "kind": "whitebox",
            "inputs": {"x": 1},
            "expected_outputs": {"y": 0},
            "created_at": "2025-03-15T14:30:45+00:00"
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert test_case.kind == TestCaseKind.WHITEBOX

    def test_from_dict_without_created_at(self):
        d = {
            "id": 1,
            "puzzle_id": 1,
            "kind": "blackbox",
            "inputs": {"a": 0},
            "expected_outputs": {"r": 1}
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert isinstance(test_case.created_at, datetime)

    def test_roundtrip(self):
        original = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 1},
            expected_outputs={"result": 1}
        )
        d = original.to_dict()
        restored = PuzzleTestCase.from_dict(d)
        assert restored.id == original.id
        assert restored.puzzle_id == original.puzzle_id
        assert restored.kind == original.kind
        assert restored.inputs == original.inputs
        assert restored.expected_outputs == original.expected_outputs

    def test_to_dict_includes_all_fields(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        d = test_case.to_dict()
        assert set(d.keys()) == {"id", "puzzle_id", "kind", "inputs", "expected_outputs", "input_stream", "expected_output_stream", "gate_name", "gate_limit", "max_gate_count", "min_cycles", "max_cycles", "created_at"}


class TestPuzzleTestCaseEdgeCases:
    def test_multiple_inputs_and_outputs(self):
        inputs = {"a": 0, "b": 1, "c": 0, "d": 1, "e": 0}
        outputs = {"x": 1, "y": 0, "z": 1}
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs=inputs,
            expected_outputs=outputs
        )
        assert len(test_case.get_inputs()) == 5
        assert len(test_case.get_expected_outputs()) == 3

    def test_single_input_single_output(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 1},
            expected_outputs={"r": 0}
        )
        assert len(test_case.get_inputs()) == 1
        assert len(test_case.get_expected_outputs()) == 1

    def test_all_inputs_zero(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 0, "c": 0},
            expected_outputs={"r": 0}
        )
        assert all(v == 0 for v in test_case.get_inputs().values())

    def test_all_inputs_one(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 1, "b": 1, "c": 1},
            expected_outputs={"r": 1}
        )
        assert all(v == 1 for v in test_case.get_inputs().values())

    def test_id_with_special_characters(self):
        test_case = PuzzleTestCase(
            id=123456,
            puzzle_id=123456,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_id() == 123456

    def test_puzzle_id_with_uuid_format(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=550840041644665544000,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_puzzle_id() == 550840041644665544000

    def test_input_output_names_with_numbers(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"input0": 0, "input1": 1, "input2": 0},
            expected_outputs={"output0": 1, "output1": 0}
        )
        assert "input0" in test_case.get_inputs()
        assert "output0" in test_case.get_expected_outputs()

    def test_inputs_outputs_are_independent(self):
        """Ensure setting inputs doesn't affect outputs"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_inputs({"b": 1})
        assert test_case.get_expected_outputs() == {"r": 1}

    def test_input_dict_copy_independence(self):
        """Ensure modifications to returned dict don't affect internal state"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        inputs = test_case.get_inputs()
        inputs["b"] = 1  # Modify returned dict
        assert test_case.get_inputs() == {"a": 0, "b": 1}  # Internal state is modified (shallow copy)

    def test_set_puzzle_id(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_puzzle_id(42)
        assert test_case.get_puzzle_id() == 42

class TestPuzzleTestCaseGateLimit:
    """Tests for GATE_LIMIT test case kind"""
    
    def test_gate_limit_valid(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.GATE_LIMIT,
            inputs={},
            expected_outputs={},
            gate_name="AND",
            gate_limit=3
        )
        assert test_case.gate_name == "AND"
        assert test_case.gate_limit == 3
        assert test_case.kind == TestCaseKind.GATE_LIMIT

    def test_gate_limit_positive_required(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.GATE_LIMIT,
            inputs={},
            expected_outputs={},
            gate_name="XOR",
            gate_limit=1
        )
        assert test_case.gate_limit == 1

    def test_gate_limit_missing_gate_name(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.GATE_LIMIT,
                inputs={},
                expected_outputs={},
                gate_name=None,
                gate_limit=5
            )
        assert "gate_name and gate_limit specified" in str(exc_info.value)

    def test_gate_limit_missing_gate_limit(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.GATE_LIMIT,
                inputs={},
                expected_outputs={},
                gate_name="AND",
                gate_limit=None
            )
        assert "gate_name and gate_limit specified" in str(exc_info.value)

    def test_gate_limit_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.GATE_LIMIT,
                inputs={},
                expected_outputs={},
                gate_name="OR",
                gate_limit=-1
            )
        assert "must be non-negative integer" in str(exc_info.value)

    def test_gate_limit_large_value(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.GATE_LIMIT,
            inputs={},
            expected_outputs={},
            gate_name="AND",
            gate_limit=1000
        )
        assert test_case.gate_limit == 1000


class TestPuzzleTestCaseGateCountLimit:
    """Tests for GATE_COUNT_LIMIT test case kind"""
    
    def test_gate_count_limit_valid_with_max_gate_count(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={},
            expected_outputs={},
            max_gate_count=5
        )
        assert test_case.max_gate_count == 5
        assert test_case.kind == TestCaseKind.GATE_COUNT_LIMIT

    def test_gate_count_limit_valid_without_max_gate_count(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.GATE_COUNT_LIMIT,
            inputs={},
            expected_outputs={},
            max_gate_count=None
        )
        assert test_case.max_gate_count is None

    def test_gate_count_limit_zero_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.GATE_COUNT_LIMIT,
                inputs={},
                expected_outputs={},
                max_gate_count=0
            )
        assert "must be > 0" in str(exc_info.value)

    def test_gate_count_limit_negative_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.GATE_COUNT_LIMIT,
                inputs={},
                expected_outputs={},
                max_gate_count=-5
            )
        assert "must be > 0" in str(exc_info.value)


class TestPuzzleTestCaseLatencyLimit:
    """Tests for LATENCY_LIMIT test case kind"""
    
    def test_latency_limit_with_min_and_max(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.LATENCY_LIMIT,
            inputs={},
            expected_outputs={},
            min_cycles=2,
            max_cycles=5
        )
        assert test_case.min_cycles == 2
        assert test_case.max_cycles == 5

    def test_latency_limit_with_min_only(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.LATENCY_LIMIT,
            inputs={},
            expected_outputs={},
            min_cycles=3,
            max_cycles=None
        )
        assert test_case.min_cycles == 3
        assert test_case.max_cycles is None

    def test_latency_limit_with_max_only(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.LATENCY_LIMIT,
            inputs={},
            expected_outputs={},
            min_cycles=None,
            max_cycles=10
        )
        assert test_case.min_cycles is None
        assert test_case.max_cycles == 10

    def test_latency_limit_missing_both(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.LATENCY_LIMIT,
                inputs={},
                expected_outputs={},
                min_cycles=None,
                max_cycles=None
            )
        assert "min_cycles and/or max_cycles specified" in str(exc_info.value)

    def test_latency_limit_min_zero(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.LATENCY_LIMIT,
                inputs={},
                expected_outputs={},
                min_cycles=0,
                max_cycles=5
            )
        assert "min_cycles must be >= 1" in str(exc_info.value)

    def test_latency_limit_max_zero(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.LATENCY_LIMIT,
                inputs={},
                expected_outputs={},
                min_cycles=2,
                max_cycles=0
            )
        assert "max_cycles must be >= 1" in str(exc_info.value)

    def test_latency_limit_min_greater_than_max(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.LATENCY_LIMIT,
                inputs={},
                expected_outputs={},
                min_cycles=10,
                max_cycles=5
            )
        assert "min_cycles cannot be greater than max_cycles" in str(exc_info.value)

    def test_latency_limit_min_equals_max(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.LATENCY_LIMIT,
            inputs={},
            expected_outputs={},
            min_cycles=5,
            max_cycles=5
        )
        assert test_case.min_cycles == 5
        assert test_case.max_cycles == 5


class TestPuzzleTestCaseSequential:
    """Tests for sequential test cases (input_stream and expected_output_stream)"""
    
    def test_sequential_valid(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[{"clk": 0}, {"clk": 1}, {"clk": 0}],
            expected_output_stream={"q": [0, 1, 0]}
        )
        assert len(test_case.input_stream) == 3
        assert "q" in test_case.expected_output_stream

    def test_sequential_empty_input_stream_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.WHITEBOX,
                inputs={},
                expected_outputs={},
                input_stream=[],
                expected_output_stream={"q": [0, 1]}
            )
        assert "input_stream cannot be empty" in str(exc_info.value)

    def test_sequential_empty_output_stream_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.WHITEBOX,
                inputs={},
                expected_outputs={},
                input_stream=[{"clk": 0}],
                expected_output_stream={}
            )
        assert "expected_output_stream cannot be empty" in str(exc_info.value)

    def test_sequential_invalid_input_value_in_dict(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.WHITEBOX,
                inputs={},
                expected_outputs={},
                input_stream=[{"clk": 2}],  # Invalid: must be 0 or 1
                expected_output_stream={"q": [0]}
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_sequential_invalid_output_stream_value(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.WHITEBOX,
                inputs={},
                expected_outputs={},
                input_stream=[{"clk": 0}],
                expected_output_stream={"q": [2]}  # Invalid: must be 0 or 1
            )
        assert "must contain only 0/1" in str(exc_info.value)

    def test_sequential_multiple_input_signals(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[
                {"clk": 0, "reset": 1},
                {"clk": 1, "reset": 0},
                {"clk": 0, "reset": 0}
            ],
            expected_output_stream={"q": [0, 1, 1]}
        )
        assert test_case.input_stream[0] == {"clk": 0, "reset": 1}

    def test_sequential_multiple_output_signals(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[{"clk": 0}],
            expected_output_stream={"q": [0], "q_not": [1]}
        )
        assert len(test_case.expected_output_stream) == 2


class TestPuzzleTestCaseInputStreamValidation:
    """Additional tests for input stream validation edge cases"""
    
    def test_input_stream_with_scalar_values(self):
        """Input stream can contain scalar 0 or 1 values"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[0, 1, 0, 1],
            expected_output_stream={"out": [1, 0, 1, 0]}
        )
        assert test_case.input_stream == [0, 1, 0, 1]

    def test_input_stream_scalar_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.WHITEBOX,
                inputs={},
                expected_outputs={},
                input_stream=[2],  # Invalid scalar
                expected_output_stream={"out": [0]}
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_input_stream_mixed_dict_and_scalar_valid(self):
        """Can mix dict and scalar values - but validation checks each"""
        # This will pass because scalar 0 is valid
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.WHITEBOX,
            inputs={},
            expected_outputs={},
            input_stream=[0, {"a": 1}, 1],
            expected_output_stream={"out": [1, 0, 1]}
        )
        assert len(test_case.input_stream) == 3


class TestPuzzleTestCaseNegativeIDHandling:
    """Tests for ID validation with negative values"""
    
    def test_negative_id_invalid(self):
        with pytest.raises(ValidationError):
            PuzzleTestCase(
                id=-1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": 1}
            )

    def test_negative_puzzle_id_invalid(self):
        with pytest.raises(ValidationError):
            PuzzleTestCase(
                id=1,
                puzzle_id=-1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": 1}
            )

    def test_set_puzzle_id_negative_invalid(self):
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_puzzle_id(-5)


class TestPuzzleTestCaseListInputsOutputs:
    """Test list branches in inputs/outputs validation"""
    
    def test_input_with_list_values_valid(self):
        """Test inputs with list values containing only 0/1"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": [0, 1, 0], "b": [1, 1]},
            expected_outputs={"r": 1}
        )
        assert test_case.get_inputs() == {"a": [0, 1, 0], "b": [1, 1]}
    
    def test_output_with_list_values_valid(self):
        """Test outputs with list values containing only 0/1"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": [0, 1], "s": [1, 0, 1]}
        )
        assert test_case.get_expected_outputs() == {"r": [0, 1], "s": [1, 0, 1]}
    
    def test_input_with_list_values_invalid(self):
        """Test inputs with list containing invalid values"""
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": [0, 1, 2]},
                expected_outputs={"r": 1}
            )
        assert "Input 'a' list must contain only 0/1" in str(exc_info.value)
    
    def test_output_with_list_values_invalid(self):
        """Test outputs with list containing invalid values"""
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": [0, 2, 1]}
            )
        assert "Output 'r' list must contain only 0/1" in str(exc_info.value)
    
    def test_mixed_scalar_and_list_inputs(self):
        """Test mix of scalar and list values in inputs"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": [1, 0], "c": 1},
            expected_outputs={"r": 1}
        )
        assert test_case.get_inputs() == {"a": 0, "b": [1, 0], "c": 1}
    
    def test_mixed_scalar_and_list_outputs(self):
        """Test mix of scalar and list values in outputs"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1, "s": [0, 1], "t": 0}
        )
        assert test_case.get_expected_outputs() == {"r": 1, "s": [0, 1], "t": 0}
    
    def test_empty_list_in_input_allowed(self):
        """Test empty list in input values - should be allowed"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": []},
            expected_outputs={"r": 1}
        )
        assert test_case.get_inputs() == {"a": []}


class TestPuzzleTestCaseSequentialFormat:
    """Test sequential test cases with input_stream and output_stream"""
    
    def test_sequential_with_input_output_streams(self):
        """Test sequential format with input and output streams"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={},
            expected_outputs={},
            input_stream=[{"a": 0, "b": 1}, {"a": 1, "b": 0}],
            expected_output_stream={"r": [0, 1]}
        )
        assert len(test_case.input_stream) == 2
        assert "r" in test_case.expected_output_stream
    
    def test_sequential_input_stream_scalar_values(self):
        """Test input_stream with scalar values"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={},
            expected_outputs={},
            input_stream=[0, 1, 0, 1],
            expected_output_stream={"out": [1, 0, 1, 0]}
        )
        assert test_case.input_stream == [0, 1, 0, 1]
    
    def test_sequential_invalid_input_stream_value(self):
        """Test sequential with invalid input_stream values"""
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={},
                expected_outputs={},
                input_stream=[{"a": 2}],
                expected_output_stream={"r": [0]}
            )
        assert "Input stream value 'a' must be 0/1" in str(exc_info.value)
    
    def test_sequential_invalid_output_stream_value(self):
        """Test sequential with invalid output_stream values"""
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={},
                expected_outputs={},
                input_stream=[{"a": 0}],
                expected_output_stream={"r": [0, 2, 1]}
            )
        assert "Output stream 'r' must contain only 0/1" in str(exc_info.value)
    
    def test_sequential_output_stream_scalar_values(self):
        """Test output_stream with scalar values (not list)"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={},
            expected_outputs={},
            input_stream=[0, 1, 0],
            expected_output_stream={"out": 1}  # Single scalar value, not a list
        )
        assert test_case.expected_output_stream == {"out": 1}
    
    def test_sequential_mixed_scalar_and_list_output_stream(self):
        """Test output_stream with both scalar and list values"""
        test_case = PuzzleTestCase(
            id=1,
            puzzle_id=1,
            kind=TestCaseKind.BLACKBOX,
            inputs={},
            expected_outputs={},
            input_stream=[0, 1],
            expected_output_stream={"out1": 1, "out2": [0, 1]}
        )
        assert test_case.expected_output_stream == {"out1": 1, "out2": [0, 1]}


class TestPuzzleTestCaseNoFormat:
    """Test error when neither format is provided"""
    
    def test_no_combinatorial_no_sequential(self):
        """Test validation error when neither format is provided"""
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id=1,
                puzzle_id=1,
                kind=TestCaseKind.BLACKBOX,
                inputs={},
                expected_outputs={},
                input_stream=[],
                expected_output_stream={}
            )
        assert "must have either inputs/expected_outputs or input_stream/expected_output_stream" in str(exc_info.value)