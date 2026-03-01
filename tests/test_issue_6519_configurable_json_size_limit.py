"""Tests for configurable JSON file size limit (Issue #6519).

These tests verify that:
1. Default limit remains 10MB for security
2. Limit can be overridden via environment variable FLYWHEEL_MAX_JSON_SIZE_MB
3. Invalid environment variable values fall back to default
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage


def test_default_limit_is_10mb(tmp_path) -> None:
    """Default limit of 10MB should be enforced for security."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a JSON file larger than 10MB (~11MB of data)
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > 10 * 1024 * 1024

    # Should raise ValueError for oversized file
    with pytest.raises(ValueError, match=r"too large|10MB"):
        storage.load()


def test_limit_can_be_configured_via_environment_variable(tmp_path) -> None:
    """Limit can be configured via FLYWHEEL_MAX_JSON_SIZE_MB environment variable."""
    db = tmp_path / "configurable.json"

    # Set environment variable to allow 30MB
    with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "30"}):
        # Re-import to pick up new environment variable
        import importlib

        import flywheel.storage as storage_module

        importlib.reload(storage_module)

        storage = storage_module.TodoStorage(str(db))

        # Create a JSON file larger than 10MB but smaller than 30MB (~15MB)
        large_payload = [
            {"id": i, "text": "x" * 100, "description": "y" * 100}
            for i in range(55000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Verify the file is between 10MB and 30MB
        file_size = db.stat().st_size
        assert file_size > 10 * 1024 * 1024
        assert file_size < 30 * 1024 * 1024

        # Should NOT raise because we configured 30MB limit
        loaded = storage.load()
        assert len(loaded) == 55000


def test_invalid_environment_variable_falls_back_to_default(tmp_path) -> None:
    """Invalid environment variable values should fall back to default 10MB."""
    db = tmp_path / "invalid_env.json"

    # Set invalid environment variable
    with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "not-a-number"}):
        # Re-import to pick up new environment variable
        import importlib

        import flywheel.storage as storage_module

        importlib.reload(storage_module)

        storage = storage_module.TodoStorage(str(db))

        # Create a JSON file larger than 10MB
        large_payload = [
            {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
            for i in range(65000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Should raise because invalid env var falls back to default 10MB
        with pytest.raises(ValueError, match=r"too large|10MB"):
            storage.load()


def test_negative_environment_variable_falls_back_to_default(tmp_path) -> None:
    """Negative environment variable values should fall back to default 10MB."""
    db = tmp_path / "negative_env.json"

    # Set negative environment variable
    with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "-5"}):
        # Re-import to pick up new environment variable
        import importlib

        import flywheel.storage as storage_module

        importlib.reload(storage_module)

        storage = storage_module.TodoStorage(str(db))

        # Create a JSON file larger than 10MB
        large_payload = [
            {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
            for i in range(65000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Should raise because negative env var falls back to default 10MB
        with pytest.raises(ValueError, match=r"too large|10MB"):
            storage.load()


def test_zero_environment_variable_falls_back_to_default(tmp_path) -> None:
    """Zero environment variable value should fall back to default 10MB."""
    db = tmp_path / "zero_env.json"

    # Set zero environment variable
    with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "0"}):
        # Re-import to pick up new environment variable
        import importlib

        import flywheel.storage as storage_module

        importlib.reload(storage_module)

        storage = storage_module.TodoStorage(str(db))

        # Create a JSON file larger than 10MB
        large_payload = [
            {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
            for i in range(65000)
        ]
        db.write_text(json.dumps(large_payload), encoding="utf-8")

        # Should raise because zero env var falls back to default 10MB
        with pytest.raises(ValueError, match=r"too large|10MB"):
            storage.load()
