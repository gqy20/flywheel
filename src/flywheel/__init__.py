"""Minimal flywheel package."""

from __future__ import annotations

from pathlib import Path

__all__ = ["__version__"]


def _get_version() -> str:
    """Read version from pyproject.toml to ensure single source of truth."""
    package_dir = Path(__file__).resolve().parent
    project_root = package_dir.parent.parent  # src/flywheel -> src -> project root
    pyproject_path = project_root / "pyproject.toml"

    if pyproject_path.exists():
        import tomllib

        with pyproject_path.open("rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]

    # Fallback for installed packages without pyproject.toml nearby
    return "0.1.0"


__version__ = _get_version()
