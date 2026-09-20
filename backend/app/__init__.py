"""Agricure backend package."""
import os
import sys

__version__ = "1.0.0"

# The ml/ inference package lives at the project root (sibling of backend/).
# Make it importable regardless of the working directory used to launch the app.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
