import os
import sys

# The root entry script setu.py shadows the `setu` package when pytest runs
# with the project root on sys.path; keep src/ ahead of it.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
