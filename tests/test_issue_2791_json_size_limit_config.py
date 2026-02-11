"""Tests for configurable JSON size limit via environment variable (Issue #2791).

These tests verify that:
1. Default behavior (no env var) maintains 10MB limit
2. TODO_MAX_JSON_SIZE_MB=5 changes limit to 5MB
3. Invalid env values fall back to default 10MB
4. Error messages display actual configured limit
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage


def test_default_json_size_limit_is_10mb() -> None:
    """Default behavior (no env var) should maintain 10MB limit."""
    # Default limit should be 10MB
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024


def test_default_size_limit_enforced_on_load(tmp_path, monkeypatch) -> None:
    """Without env var, loading 10MB+ file should fail with 10MB in error."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Remove env var if set
    monkeypatch.delenv("TODO_MAX_JSON_SIZE_MB", raising=False)

    # Create a file just over 10MB (using dummy data)
    large_data = [{"id": i, "text": "x" * 100} for i in range(110000)]  # ~11MB
    db.write_text(json.dumps(large_data), encoding="utf-8")

    with pytest.raises(ValueError, match=r"10MB|10\.0MB"):
        storage.load()


def test_custom_size_limit_5mb_via_env(tmp_path, monkeypatch) -> None:
    """TODO_MAX_JSON_SIZE_MB=5 should change limit to 5MB."""
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "5")

    # Reload the module to pick up the new env var
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    from flywheel.storage import _MAX_JSON_SIZE_BYTES, TodoStorage

    # Limit should now be 5MB
    assert _MAX_JSON_SIZE_BYTES == 5 * 1024 * 1024

    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file just over 5MB
    large_data = [{"id": i, "text": "x" * 100} for i in range(55000)]  # ~6MB
    db.write_text(json.dumps(large_data), encoding="utf-8")

    with pytest.raises(ValueError, match=r"5MB|5\.0MB"):
        storage.load()


def test_invalid_env_value_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Invalid TODO_MAX_JSON_SIZE_MB should fall back to default 10MB."""
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "invalid")

    # Reload the module to pick up the new env var
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    from flywheel.storage import _MAX_JSON_SIZE_BYTES

    # Should fall back to default 10MB
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024


def test_negative_env_value_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Negative TODO_MAX_JSON_SIZE_MB should fall back to default 10MB."""
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "-5")

    # Reload the module to pick up the new env var
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    from flywheel.storage import _MAX_JSON_SIZE_BYTES

    # Should fall back to default 10MB
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024


def test_zero_env_value_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Zero TODO_MAX_JSON_SIZE_MB should fall back to default 10MB."""
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "0")

    # Reload the module to pick up the new env var
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    from flywheel.storage import _MAX_JSON_SIZE_BYTES

    # Should fall back to default 10MB
    assert _MAX_JSON_SIZE_BYTES == 10 * 1024 * 1024


def test_error_message_shows_custom_limit(tmp_path, monkeypatch) -> None:
    """Error message should display the actual configured limit value."""
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "3")

    # Reload the module to pick up the new env var
    import importlib

    import flywheel.storage
    importlib.reload(flywheel.storage)

    from flywheel.storage import TodoStorage

    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Create a file over 3MB
    large_data = [{"id": i, "text": "x" * 100} for i in range(35000)]  # ~4MB
    db.write_text(json.dumps(large_data), encoding="utf-8")

    with pytest.raises(ValueError, match=r"3\.?MB"):
        storage.load()
