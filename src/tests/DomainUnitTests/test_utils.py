import pytest
from datetime import datetime, timezone

from Backend.DomainLayer.Utils import (
    utcnow,
    new_id,
    clamp_int,
    ensure_non_empty,
    ensure_non_negative_int,
    ensure_optional_positive_int,
    ensure_bit_dict,
    ensure_gate_set
)
from Backend.DomainLayer.Enums import GateType
from Backend.DomainLayer.Exceptions import ValidationError


class TestUtcnow:
    def test_utcnow_returns_datetime(self):
        result = utcnow()
        assert isinstance(result, datetime)

    def test_utcnow_has_timezone(self):
        result = utcnow()
        assert result.tzinfo is not None

    def test_utcnow_is_utc(self):
        result = utcnow()
        assert result.tzinfo == timezone.utc

    def test_utcnow_recent_time(self):
        """Verify utcnow returns current time (within reasonable margin)"""
        before = datetime.now(timezone.utc)
        result = utcnow()
        after = datetime.now(timezone.utc)
        assert before <= result <= after


class TestNewId:
    def test_new_id_returns_string(self):
        result = new_id()
        assert isinstance(result, str)

    def test_new_id_not_empty(self):
        result = new_id()
        assert len(result) > 0

    def test_new_id_uuid_format(self):
        """Verify new_id returns UUID format"""
        result = new_id()
        # UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        parts = result.split('-')
        assert len(parts) == 5

    def test_new_id_uniqueness(self):
        """Verify each call returns unique ID"""
        id1 = new_id()
        id2 = new_id()
        id3 = new_id()
        assert id1 != id2
        assert id2 != id3
        assert id1 != id3

    def test_new_id_multiple_calls_all_strings(self):
        """Verify multiple IDs are all strings"""
        ids = [new_id() for _ in range(10)]
        assert all(isinstance(id_, str) for id_ in ids)


class TestClampInt:
    def test_clamp_int_valid_in_range_lower(self):
        result = clamp_int("test", 5, 0, 10)
        assert result == 5

    def test_clamp_int_valid_in_range_upper(self):
        result = clamp_int("test", 10, 0, 10)
        assert result == 10

    def test_clamp_int_valid_in_range_middle(self):
        result = clamp_int("test", 5, 0, 10)
        assert result == 5

    def test_clamp_int_valid_at_lower_bound(self):
        result = clamp_int("test", 0, 0, 10)
        assert result == 0

    def test_clamp_int_valid_at_upper_bound(self):
        result = clamp_int("test", 10, 0, 10)
        assert result == 10

    def test_clamp_int_below_range(self):
        with pytest.raises(ValidationError) as exc_info:
            clamp_int("test", -1, 0, 10)
        assert "must be in [0, 10]" in str(exc_info.value)

    def test_clamp_int_above_range(self):
        with pytest.raises(ValidationError) as exc_info:
            clamp_int("test", 11, 0, 10)
        assert "must be in [0, 10]" in str(exc_info.value)

    def test_clamp_int_non_integer(self):
        with pytest.raises(ValidationError) as exc_info:
            clamp_int("test", "5", 0, 10)  # type: ignore
        assert "must be int" in str(exc_info.value)

    def test_clamp_int_float(self):
        with pytest.raises(ValidationError) as exc_info:
            clamp_int("test", 5.5, 0, 10)  # type: ignore
        assert "must be int" in str(exc_info.value)

    def test_clamp_int_negative_bounds(self):
        result = clamp_int("test", -5, -10, 0)
        assert result == -5

    def test_clamp_int_large_numbers(self):
        result = clamp_int("test", 500, 0, 1000)
        assert result == 500

    def test_clamp_int_single_value_range(self):
        result = clamp_int("test", 5, 5, 5)
        assert result == 5

    def test_clamp_int_single_value_range_invalid(self):
        with pytest.raises(ValidationError):
            clamp_int("test", 6, 5, 5)

    def test_clamp_int_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            clamp_int("myCustomValue", 15, 0, 10)
        assert "myCustomValue" in str(exc_info.value)


class TestEnsureNonEmpty:
    def test_ensure_non_empty_valid(self):
        result = ensure_non_empty("test", "hello")
        assert result == "hello"

    def test_ensure_non_empty_empty_string(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("test", "")
        assert "test is required" in str(exc_info.value)

    def test_ensure_non_empty_whitespace_only(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("test", "   ")
        assert "test is required" in str(exc_info.value)

    def test_ensure_non_empty_tabs_and_newlines(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("test", "\t\n\r")
        assert "test is required" in str(exc_info.value)

    def test_ensure_non_empty_single_char(self):
        result = ensure_non_empty("test", "a")
        assert result == "a"

    def test_ensure_non_empty_with_spaces(self):
        result = ensure_non_empty("test", "hello world")
        assert result == "hello world"

    def test_ensure_non_empty_non_string(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("test", 123)  # type: ignore
        assert "test is required" in str(exc_info.value)

    def test_ensure_non_empty_none(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("test", None)  # type: ignore
        assert "test is required" in str(exc_info.value)

    def test_ensure_non_empty_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_empty("Circuit.name", "")
        assert "Circuit.name is required" in str(exc_info.value)


class TestEnsureNonNegativeInt:
    def test_ensure_non_negative_int_zero(self):
        # Zero is rejected (validation uses value <= 0)
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", 0)
        assert "cannot be negative" in str(exc_info.value)

    def test_ensure_non_negative_int_positive(self):
        result = ensure_non_negative_int("test", 10)
        assert result == 10

    def test_ensure_non_negative_int_large_positive(self):
        result = ensure_non_negative_int("test", 1000000)
        assert result == 1000000

    def test_ensure_non_negative_int_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", -1)
        assert "test cannot be negative" in str(exc_info.value)

    def test_ensure_non_negative_int_large_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", -1000000)
        assert "test cannot be negative" in str(exc_info.value)

    def test_ensure_non_negative_int_non_integer(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", "5")  # type: ignore
        assert "test must be int" in str(exc_info.value)

    def test_ensure_non_negative_int_float(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", 5.5)  # type: ignore
        assert "test must be int" in str(exc_info.value)

    def test_ensure_non_negative_int_none(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("test", None)  # type: ignore
        assert "test must be int" in str(exc_info.value)

    def test_ensure_non_negative_int_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_non_negative_int("Circuit.cost", -5)
        assert "Circuit.cost cannot be negative" in str(exc_info.value)


class TestEnsureOptionalPositiveInt:
    def test_ensure_optional_positive_int_valid_positive(self):
        result = ensure_optional_positive_int("test", 10)
        assert result == 10

    def test_ensure_optional_positive_int_large_positive(self):
        result = ensure_optional_positive_int("test", 1000000)
        assert result == 1000000

    def test_ensure_optional_positive_int_none(self):
        result = ensure_optional_positive_int("test", None)
        assert result is None

    def test_ensure_optional_positive_int_zero(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_optional_positive_int("test", 0)
        assert "must be > 0 when set" in str(exc_info.value)

    def test_ensure_optional_positive_int_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_optional_positive_int("test", -1)
        assert "must be > 0 when set" in str(exc_info.value)

    def test_ensure_optional_positive_int_non_integer(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_optional_positive_int("test", "5")  # type: ignore
        assert "test must be int or None" in str(exc_info.value)

    def test_ensure_optional_positive_int_float(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_optional_positive_int("test", 5.5)  # type: ignore
        assert "test must be int or None" in str(exc_info.value)

    def test_ensure_optional_positive_int_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_optional_positive_int("timeout", -10)
        assert "timeout must be > 0 when set" in str(exc_info.value)


class TestEnsureBitDict:
    def test_ensure_bit_dict_valid(self):
        d = {"a": 0, "b": 1}
        result = ensure_bit_dict("test", d)
        assert result == d

    def test_ensure_bit_dict_single_entry(self):
        d = {"x": 0}
        result = ensure_bit_dict("test", d)
        assert result == d

    def test_ensure_bit_dict_all_zeros(self):
        d = {"a": 0, "b": 0, "c": 0}
        result = ensure_bit_dict("test", d)
        assert result == d

    def test_ensure_bit_dict_all_ones(self):
        d = {"x": 1, "y": 1, "z": 1}
        result = ensure_bit_dict("test", d)
        assert result == d

    def test_ensure_bit_dict_empty(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", {})
        assert "test cannot be empty" in str(exc_info.value)

    def test_ensure_bit_dict_invalid_value_two(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", {"a": 2})
        assert "test 'a' must be 0/1" in str(exc_info.value)

    def test_ensure_bit_dict_invalid_value_negative(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", {"a": -1})
        assert "test 'a' must be 0/1" in str(exc_info.value)

    def test_ensure_bit_dict_non_dict(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", [1, 0, 1])  # type: ignore
        assert "test cannot be empty" in str(exc_info.value)

    def test_ensure_bit_dict_none(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", None)  # type: ignore
        assert "test cannot be empty" in str(exc_info.value)

    def test_ensure_bit_dict_string_values(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("test", {"a": "0"})  # type: ignore
        assert "test 'a' must be 0/1" in str(exc_info.value)

    def test_ensure_bit_dict_many_entries(self):
        d = {f"key{i}": i % 2 for i in range(100)}
        result = ensure_bit_dict("test", d)
        assert result == d

    def test_ensure_bit_dict_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_bit_dict("PuzzleTestCase.inputs", {"a": 2})
        assert "PuzzleTestCase.inputs 'a' must be 0/1" in str(exc_info.value)


class TestEnsureGateSet:
    def test_ensure_gate_set_valid_single_gate(self):
        s = {GateType.AND}
        result = ensure_gate_set("test", s)
        assert result == s

    def test_ensure_gate_set_valid_multiple_gates(self):
        s = {GateType.AND, GateType.OR, GateType.NOT}
        result = ensure_gate_set("test", s)
        assert result == s

    def test_ensure_gate_set_all_basic_gates(self):
        s = {GateType.AND, GateType.OR, GateType.NOT, GateType.XOR, GateType.NAND, GateType.NOR, GateType.XNOR}
        result = ensure_gate_set("test", s)
        assert result == s

    def test_ensure_gate_set_with_dff(self):
        s = {GateType.AND, GateType.DFF}
        result = ensure_gate_set("test", s)
        assert result == s

    def test_ensure_gate_set_non_set(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", [GateType.AND, GateType.OR])  # type: ignore
        assert "test must be a set" in str(exc_info.value)

    def test_ensure_gate_set_none(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", None)  # type: ignore
        assert "test must be a set" in str(exc_info.value)

    def test_ensure_gate_set_dict(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", {GateType.AND: 1})  # type: ignore
        assert "test must be a set" in str(exc_info.value)

    def test_ensure_gate_set_string_values(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", {"AND", "OR"})  # type: ignore
        assert "test must contain GateType items" in str(exc_info.value)

    def test_ensure_gate_set_integer_values(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", {1, 2, 3})  # type: ignore
        assert "test must contain GateType items" in str(exc_info.value)

    def test_ensure_gate_set_mixed_types(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("test", {GateType.AND, "OR"})  # type: ignore
        assert "test must contain GateType items" in str(exc_info.value)

    def test_ensure_gate_set_empty_set(self):
        # Empty set is allowed as long as it's a set
        result = ensure_gate_set("test", set())
        assert result == set()

    def test_ensure_gate_set_descriptive_name(self):
        with pytest.raises(ValidationError) as exc_info:
            ensure_gate_set("Circuit.gates", ["AND"])  # type: ignore
        assert "Circuit.gates must be a set" in str(exc_info.value)

class TestUtilsFunctionBranches:
    """Test conditional branches in utility validation functions"""
    
    def test_ensure_non_empty_empty_string(self):
        """Test ensure_non_empty with empty string"""
        with pytest.raises(ValidationError):
            ensure_non_empty("test", "")
    
    def test_ensure_non_empty_whitespace_only(self):
        """Test ensure_non_empty with whitespace-only string"""
        with pytest.raises(ValidationError):
            ensure_non_empty("test", "   ")
    
    def test_ensure_non_empty_valid(self):
        """Test ensure_non_empty with valid string"""
        result = ensure_non_empty("test", "valid")
        assert result == "valid"
    
    def test_clamp_int_not_int_type(self):
        """Test clamp_int with non-int type"""
        with pytest.raises(ValidationError):
            clamp_int("test", "3", 1, 5)
    
    def test_clamp_int_below_range(self):
        """Test clamp_int with value below range"""
        with pytest.raises(ValidationError):
            clamp_int("test", 0, 1, 5)
    
    def test_clamp_int_above_range(self):
        """Test clamp_int with value above range"""
        with pytest.raises(ValidationError):
            clamp_int("test", 6, 1, 5)
    
    def test_clamp_int_valid(self):
        """Test clamp_int with valid value"""
        result = clamp_int("test", 3, 1, 5)
        assert result == 3
    
    def test_ensure_optional_positive_int_none(self):
        """Test ensure_optional_positive_int with None"""
        result = ensure_optional_positive_int("test", None)
        assert result is None
    
    def test_ensure_optional_positive_int_positive(self):
        """Test ensure_optional_positive_int with positive int"""
        result = ensure_optional_positive_int("test", 5)
        assert result == 5
    
    def test_ensure_optional_positive_int_zero(self):
        """Test ensure_optional_positive_int with zero"""
        with pytest.raises(ValidationError):
            ensure_optional_positive_int("test", 0)
    
    def test_ensure_optional_positive_int_negative(self):
        """Test ensure_optional_positive_int with negative"""
        with pytest.raises(ValidationError):
            ensure_optional_positive_int("test", -5)
    
    def test_ensure_optional_positive_int_not_int(self):
        """Test ensure_optional_positive_int with non-int"""
        with pytest.raises(ValidationError):
            ensure_optional_positive_int("test", "5")