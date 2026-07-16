#!/usr/bin/env python3
"""Entry point: python setu.py --src hi --tgt en --text "..." """

import os
import sys

# This file shadows the `setu` package when run as a script; put src/ ahead of
# it so the package resolves whether or not it's pip-installed.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from setu.cli import main

if __name__ == "__main__":
    sys.exit(main())
