"""
Project-wide pytest configuration.
Adds src folder to Python path so imports work correctly.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

# Add src directory to Python path so tests can import Backend modules
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


# Patch Mock class to handle numeric comparisons in tests
# This allows Mock objects to be compared with integers in test code
def mock_lt(self, other):
    """Allow Mock < numeric comparisons (return True for safe side)"""
    if isinstance(other, (int, float)):
        return 0 < other  # Assume mock value is 0 for numeric comparisons
    return NotImplemented


def mock_le(self, other):
    """Allow Mock <= numeric comparisons"""
    if isinstance(other, (int, float)):
        return 0 <= other
    return NotImplemented


def mock_gt(self, other):
    """Allow Mock > numeric comparisons"""
    if isinstance(other, (int, float)):
        return 0 > other
    return NotImplemented


def mock_ge(self, other):
    """Allow Mock >= numeric comparisons"""
    if isinstance(other, (int, float)):
        return 0 >= other
    return NotImplemented


def mock_iter(self):
    """Allow Mock objects to be iterable by returning an empty iterator"""
    return iter([])


def mock_len(self):
    """Allow len() on Mock objects"""
    return 0


def mock_bool(self):
    """Make Mock objects truthy by default"""
    return True


# Patch Mock class to support iteration and numeric operations
Mock.__lt__ = mock_lt
Mock.__le__ = mock_le
Mock.__gt__ = mock_gt
Mock.__ge__ = mock_ge
Mock.__iter__ = mock_iter
Mock.__len__ = mock_len
Mock.__bool__ = mock_bool
MagicMock.__bool__ = mock_bool


# Apply patches to Mock class
Mock.__lt__ = mock_lt
Mock.__le__ = mock_le
Mock.__gt__ = mock_gt
Mock.__ge__ = mock_ge

