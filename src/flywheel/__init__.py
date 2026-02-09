"""Minimal flywheel package."""

from __future__ import annotations

import importlib.metadata

__all__ = ["__version__"]

__version__: str = importlib.metadata.version("flywheel")
