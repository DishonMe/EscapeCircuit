#!/usr/bin/env python
"""
Run code coverage for the EscapeCircuit backend.
This script generates both terminal and HTML coverage reports.
"""

import subprocess
import sys
from pathlib import Path

def run_coverage():
    """Run coverage analysis on the backend code."""
    
    project_root = Path(__file__).parent
    backend_dir = project_root / "src" / "Backend"
    tests_dir = project_root / "src" / "tests"
    
    print("=" * 60)
    print("EscapeCircuit Code Coverage Analysis")
    print("=" * 60)
    print("Backend directory: Backend code")
    print("Tests directory: Tests")
    print()
    
    try:
        # Run tests with coverage
        print("Running tests with coverage (including branch coverage)...")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "coverage",
                "run",
                "--branch",
                "-m",
                "pytest",
                "tests/DomainUnitTests",
                "tests/ServiceLayerTests",
                "-v",
            ],
            cwd=project_root / "src",
            capture_output=False,
        )
        
        if result.returncode != 0:
            print("\nWarning: Some tests failed or coverage module not found.")
            print("Make sure pytest and coverage are installed:")
            print("  pip install pytest coverage")
            return False
        
        print("\n" + "=" * 60)
        print("Coverage Report")
        print("=" * 60)
        
        # Generate terminal report
        subprocess.run(
            [sys.executable, "-m", "coverage", "report", "--include=Backend/*"],
            cwd=project_root / "src",
        )
        
        # Generate HTML report
        print("\nGenerating HTML report...")
        subprocess.run(
            [sys.executable, "-m", "coverage", "html", "--include=Backend/*"],
            cwd=project_root / "src",
        )
        
        print("\n" + "=" * 60)
        print("* Coverage analysis complete!")
        print("=" * 60)
        print("HTML report: htmlcov/index.html")
        print("\nTo view the HTML report, open htmlcov/index.html in your browser.")
        
        return True
        
    except FileNotFoundError:
        print("\n❌ Error: coverage module not found")
        print("Install it with: pip install coverage pytest")
        return False

if __name__ == "__main__":
    success = run_coverage()
    sys.exit(0 if success else 1)
