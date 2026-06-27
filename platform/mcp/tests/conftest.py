import sys
import os

# Make the mcp package root importable when pytest runs from the tests/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
