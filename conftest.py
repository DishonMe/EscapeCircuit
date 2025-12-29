"""
Project-wide pytest configuration.
Adds src folder to Python path so imports work correctly.
"""

import sys
from pathlib import Path

# Add src directory to Python path so tests can import Backend modules
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
