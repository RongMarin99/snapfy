"""
Resolves bundled asset paths for both dev (repo root) and a PyInstaller-frozen exe (_MEIPASS).
"""

import sys
from pathlib import Path


def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent
    return str(base_dir / relative_path)
