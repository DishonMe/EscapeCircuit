from datetime import datetime, timezone
from uuid import uuid4

from typing import Dict, Any, Optional, Set
from .Exceptions import ValidationError
from .Enums import GateType

def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


def clamp_int(name: str, value: int, lo: int, hi: int) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be int")
    if value < lo or value > hi:
        raise ValidationError(f"{name} must be in [{lo}, {hi}]")
    return value

def ensure_non_empty(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} is required")
    return value

def ensure_non_negative_int(name: str, value: int) -> int:
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be int")
    if value <= 0:
        raise ValidationError(f"{name} cannot be negative")
    return value

def ensure_optional_positive_int(name: str, value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if not isinstance(value, int):
        raise ValidationError(f"{name} must be int or None")
    if value <= 0:
        raise ValidationError(f"{name} must be > 0 when set")
    return value

def ensure_bit_dict(name: str, d: Dict[str, int]) -> Dict[str, int]:
    if not isinstance(d, dict) or len(d) == 0:
        raise ValidationError(f"{name} cannot be empty")
    for k, v in d.items():
        if isinstance(v, list):
            if not all(x in (0, 1) for x in v):
                raise ValidationError(f"{name} '{k}' list must contain only 0/1")
        elif v not in (0, 1):
            raise ValidationError(f"{name} '{k}' must be 0/1")
    return d

def ensure_gate_set(name: str, s: Set[GateType]) -> Set[GateType]:
    if not isinstance(s, set):
        raise ValidationError(f"{name} must be a set")
    for g in s:
        if not isinstance(g, GateType):
            raise ValidationError(f"{name} must contain GateType items")
    return s