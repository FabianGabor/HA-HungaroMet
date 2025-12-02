"""Pytest configuration for the HungaroMet integration tests."""

import sys
from pathlib import Path

# Add the project root to the Python path so imports work correctly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
