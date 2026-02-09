"""Minimal flywheel package."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

__all__ = ["__version__"]

try:
    import tomli
except ModuleNotFoundError:
    tomli = None  # type: ignore[assignment]


def _get_version() -> str:
    """Get version from pyproject.toml or importlib.metadata.

    First tries to read from pyproject.toml for development installs.
    Falls back to importlib.metadata for installed packages.

    Returns:
        Version string.
    """
    # Try reading from pyproject.toml first (for development installs)
    try:
        if tomli is not None:
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    pyproject = tomli.load(f)
                return pyproject["project"]["version"]
    except Exception:
        pass  # Fall through to importlib.metadata

    # Fallback to importlib.metadata (for installed packages)
    try:
        return importlib.metadata.version("flywheel")
    except importlib.metadata.PackageNotFoundError:
        # Last resort fallback
        return "0.0.0-unknown"


__version__ = _get_version()
