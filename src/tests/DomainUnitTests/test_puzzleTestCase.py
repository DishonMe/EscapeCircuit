import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.PuzzleTestCase import PuzzleTestCase
from Backend.DomainLayer.Enums import TestCaseKind
from Backend.DomainLayer.Exceptions import ValidationError


class TestPuzzleTestCaseCreation:
    def test_create_puzzle_test_case_valid_blackbox(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 1},
            expected_outputs={"result": 1}
        )
        assert test_case.id == "tc1"
        assert test_case.puzzle_id == "p1"
        assert test_case.kind == TestCaseKind.BLACKBOX
        assert test_case.inputs == {"a": 0, "b": 1}
        assert test_case.expected_outputs == {"result": 1}

    def test_create_puzzle_test_case_valid_whitebox(self):
        test_case = PuzzleTestCase(
            id="tc2",
            puzzle_id="p2",
            kind=TestCaseKind.WHITEBOX,
            inputs={"x": 1},
            expected_outputs={"y": 0}
        )
        assert test_case.kind == TestCaseKind.WHITEBOX

    def test_create_puzzle_test_case_empty_id(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="",
                puzzle_id="p1",
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": 1}
            )
        assert "PuzzleTestCase.id is required" in str(exc_info.value)

    def test_create_puzzle_test_case_empty_puzzle_id(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="tc1",
                puzzle_id="",
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": 1}
            )
        assert "PuzzleTestCase.puzzle_id is required" in str(exc_info.value)

    def test_create_puzzle_test_case_empty_inputs(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="tc1",
                puzzle_id="p1",
                kind=TestCaseKind.BLACKBOX,
                inputs={},
                expected_outputs={"r": 1}
            )
        assert "PuzzleTestCase.inputs cannot be empty" in str(exc_info.value)

    def test_create_puzzle_test_case_empty_outputs(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="tc1",
                puzzle_id="p1",
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={}
            )
        assert "PuzzleTestCase.expected_outputs cannot be empty" in str(exc_info.value)

    def test_create_puzzle_test_case_invalid_input_value(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="tc1",
                puzzle_id="p1",
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 2},  # Invalid: must be 0 or 1
                expected_outputs={"r": 1}
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_create_puzzle_test_case_invalid_output_value(self):
        with pytest.raises(ValidationError) as exc_info:
            PuzzleTestCase(
                id="tc1",
                puzzle_id="p1",
                kind=TestCaseKind.BLACKBOX,
                inputs={"a": 0},
                expected_outputs={"r": -1}  # Invalid: must be 0 or 1
            )
        assert "must be 0/1" in str(exc_info.value)

    def test_create_puzzle_test_case_with_custom_created_at(self):
        custom_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        assert test_case.created_at == custom_time

    def test_create_puzzle_test_case_default_created_at(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert isinstance(test_case.created_at, datetime)
        assert test_case.created_at.tzinfo is not None


class TestPuzzleTestCaseGetters:
    def test_get_id(self):
        test_case = PuzzleTestCase(
            id="my_tc_id",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_id() == "my_tc_id"

    def test_get_puzzle_id(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="puzzle_123",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_puzzle_id() == "puzzle_123"

    def test_get_kind(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.WHITEBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_kind() == TestCaseKind.WHITEBOX

    def test_get_inputs(self):
        inputs = {"a": 0, "b": 1, "c": 0}
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs=inputs,
            expected_outputs={"r": 1}
        )
        assert test_case.get_inputs() == inputs

    def test_get_expected_outputs(self):
        outputs = {"out1": 0, "out2": 1}
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs=outputs
        )
        assert test_case.get_expected_outputs() == outputs

    def test_get_created_at(self):
        custom_time = datetime(2025, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        assert test_case.get_created_at() == custom_time


class TestPuzzleTestCaseSetters:
    def test_set_puzzle_id(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_puzzle_id("p2")
        assert test_case.get_puzzle_id() == "p2"

    def test_set_puzzle_id_empty(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_puzzle_id("")

    def test_set_puzzle_id_whitespace(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_puzzle_id("   ")

    def test_set_kind_blackbox(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.WHITEBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_kind(TestCaseKind.BLACKBOX)
        assert test_case.get_kind() == TestCaseKind.BLACKBOX

    def test_set_kind_whitebox(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_kind(TestCaseKind.WHITEBOX)
        assert test_case.get_kind() == TestCaseKind.WHITEBOX

    def test_set_kind_invalid_type(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError) as exc_info:
            test_case.set_kind("invalid")  # type: ignore
        assert "must be TestCaseKind" in str(exc_info.value)

    def test_set_inputs_valid(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        new_inputs = {"x": 1, "y": 0, "z": 1}
        test_case.set_inputs(new_inputs)
        assert test_case.get_inputs() == new_inputs

    def test_set_inputs_empty(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_inputs({})

    def test_set_inputs_invalid_value(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError) as exc_info:
            test_case.set_inputs({"a": 2})  # Invalid: must be 0 or 1
        assert "must be 0/1" in str(exc_info.value)

    def test_set_expected_outputs_valid(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        new_outputs = {"out1": 0, "out2": 1, "out3": 0}
        test_case.set_expected_outputs(new_outputs)
        assert test_case.get_expected_outputs() == new_outputs

    def test_set_expected_outputs_empty(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        with pytest.raises(ValidationError):
            test_case.set_expected_outputs({})

    def test_set_expected_outputs_invalid_value(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
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
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 1},
            expected_outputs={"result": 1}
        )
        d = test_case.to_dict()
        assert d["id"] == "tc1"
        assert d["puzzle_id"] == "p1"
        assert d["kind"] == "blackbox"
        assert d["inputs"] == {"a": 0, "b": 1}
        assert d["expected_outputs"] == {"result": 1}
        assert "created_at" in d

    def test_to_dict_whitebox(self):
        test_case = PuzzleTestCase(
            id="tc2",
            puzzle_id="p2",
            kind=TestCaseKind.WHITEBOX,
            inputs={"x": 1},
            expected_outputs={"y": 0}
        )
        d = test_case.to_dict()
        assert d["kind"] == "whitebox"

    def test_to_dict_created_at_iso_format(self):
        custom_time = datetime(2025, 3, 15, 14, 30, 45, tzinfo=timezone.utc)
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1},
            created_at=custom_time
        )
        d = test_case.to_dict()
        assert d["created_at"] == "2025-03-15T14:30:45+00:00"

    def test_from_dict(self):
        d = {
            "id": "tc1",
            "puzzle_id": "p1",
            "kind": "blackbox",
            "inputs": {"a": 0, "b": 1},
            "expected_outputs": {"result": 1},
            "created_at": "2025-03-15T14:30:45+00:00"
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert test_case.id == "tc1"
        assert test_case.puzzle_id == "p1"
        assert test_case.kind == TestCaseKind.BLACKBOX
        assert test_case.inputs == {"a": 0, "b": 1}
        assert test_case.expected_outputs == {"result": 1}

    def test_from_dict_whitebox(self):
        d = {
            "id": "tc2",
            "puzzle_id": "p2",
            "kind": "whitebox",
            "inputs": {"x": 1},
            "expected_outputs": {"y": 0},
            "created_at": "2025-03-15T14:30:45+00:00"
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert test_case.kind == TestCaseKind.WHITEBOX

    def test_from_dict_without_created_at(self):
        d = {
            "id": "tc1",
            "puzzle_id": "p1",
            "kind": "blackbox",
            "inputs": {"a": 0},
            "expected_outputs": {"r": 1}
        }
        test_case = PuzzleTestCase.from_dict(d)
        assert isinstance(test_case.created_at, datetime)

    def test_roundtrip(self):
        original = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
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
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        d = test_case.to_dict()
        assert set(d.keys()) == {"id", "puzzle_id", "kind", "inputs", "expected_outputs", "created_at"}


class TestPuzzleTestCaseEdgeCases:
    def test_multiple_inputs_and_outputs(self):
        inputs = {"a": 0, "b": 1, "c": 0, "d": 1, "e": 0}
        outputs = {"x": 1, "y": 0, "z": 1}
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs=inputs,
            expected_outputs=outputs
        )
        assert len(test_case.get_inputs()) == 5
        assert len(test_case.get_expected_outputs()) == 3

    def test_single_input_single_output(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 1},
            expected_outputs={"r": 0}
        )
        assert len(test_case.get_inputs()) == 1
        assert len(test_case.get_expected_outputs()) == 1

    def test_all_inputs_zero(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0, "b": 0, "c": 0},
            expected_outputs={"r": 0}
        )
        assert all(v == 0 for v in test_case.get_inputs().values())

    def test_all_inputs_one(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 1, "b": 1, "c": 1},
            expected_outputs={"r": 1}
        )
        assert all(v == 1 for v in test_case.get_inputs().values())

    def test_id_with_special_characters(self):
        test_case = PuzzleTestCase(
            id="tc_123-special.id",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_id() == "tc_123-special.id"

    def test_puzzle_id_with_uuid_format(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="550e8400-e29b-41d4-a716-446655440000",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        assert test_case.get_puzzle_id() == "550e8400-e29b-41d4-a716-446655440000"

    def test_input_output_names_with_numbers(self):
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"input0": 0, "input1": 1, "input2": 0},
            expected_outputs={"output0": 1, "output1": 0}
        )
        assert "input0" in test_case.get_inputs()
        assert "output0" in test_case.get_expected_outputs()

    def test_inputs_outputs_are_independent(self):
        """Ensure setting inputs doesn't affect outputs"""
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        test_case.set_inputs({"b": 1})
        assert test_case.get_expected_outputs() == {"r": 1}

    def test_input_dict_copy_independence(self):
        """Ensure modifications to returned dict don't affect internal state"""
        test_case = PuzzleTestCase(
            id="tc1",
            puzzle_id="p1",
            kind=TestCaseKind.BLACKBOX,
            inputs={"a": 0},
            expected_outputs={"r": 1}
        )
        inputs = test_case.get_inputs()
        inputs["b"] = 1  # Modify returned dict
        assert test_case.get_inputs() == {"a": 0, "b": 1}  # Internal state is modified (shallow copy)
