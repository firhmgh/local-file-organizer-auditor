#!/usr/bin/env python
"""
Runner script for local-file-organizer-auditor
"""
import sys
from pathlib import Path

# Ensure local package is importable
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from local_organizer.cli import main

if __name__ == "__main__":
    main()
