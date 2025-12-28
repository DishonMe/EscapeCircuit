import sys
from pathlib import Path

# Add the Backend directory to the Python path so imports work correctly
backend_dir = Path(__file__).parent.parent.parent / "Backend"
sys.path.insert(0, str(backend_dir))
