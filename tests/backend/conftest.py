import sys
import os

# Add backend/ to sys.path so tests can import services, models, core, etc.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
