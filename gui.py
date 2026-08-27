"""
Main GUI entrypoint for Local File Organizer & Auditor (Windows Edition).
Run with: python gui.py
"""
import sys
from pathlib import Path

# Ensure local_organizer module is accessible
root_dir = Path(__file__).parent.resolve()
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from local_organizer.gui import launch_gui

if __name__ == "__main__":
    launch_gui()
