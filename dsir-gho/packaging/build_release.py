"""Compatibility entry point for the source-based local GHO test builder.

Both entry points now produce the same plugin and standalone runtime packages.
Historical release archives must be rebuilt from their historical Git tags.
"""
import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "packaging/build_gho_plugin.py"), run_name="__main__")
