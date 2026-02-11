"""Tests for configurable JSON size limit via environment variable (Issue #2791).

These tests verify that:
1. Default behavior maintains 10MB limit when no env var is set
2. TODO_MAX_JSON_SIZE_MB env variable configures the limit
3. Invalid values fall back to default 10MB
4. Error messages show the configured limit value
"""

from __future__ import annotations

import json

import pytest

from flywheel.storage import TodoStorage


def test_default_limit_is_10mb_without_env_var(tmp_path, monkeypatch) -> None:
    """Default behavior: 10MB limit when TODO_MAX_JSON_SIZE_MB is not set."""
    db = tmp_path / "large.json"
    storage = TodoStorage(str(db))

    # Ensure env var is not set
    monkeypatch.delenv("TODO_MAX_JSON_SIZE_MB", raising=False)

    # Create a JSON file larger than 10MB (~11MB of data)
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Verify the file is actually larger than 10MB
    assert db.stat().st_size > 10 * 1024 * 1024

    # Should raise ValueError for oversized file with default 10MB limit
    with pytest.raises(ValueError, match=r"10MB"):
        storage.load()


def test_custom_limit_from_env_var_todo_max_json_size_mb(tmp_path, monkeypatch) -> None:
    """Custom limit from TODO_MAX_JSON_SIZE_MB environment variable."""
    db = tmp_path / "medium.json"
    storage = TodoStorage(str(db))

    # Set custom limit to 5MB
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "5")

    # Create a JSON file larger than 5MB but smaller than 10MB (~6MB of data)
    medium_payload = [
        {"id": i, "text": "x" * 80, "description": "y" * 80}
        for i in range(35000)
    ]
    db.write_text(json.dumps(medium_payload), encoding="utf-8")

    # Verify the file is larger than 5MB but smaller than 10MB
    assert db.stat().st_size > 5 * 1024 * 1024
    assert db.stat().st_size < 10 * 1024 * 1024

    # Should raise ValueError for oversized file with custom 5MB limit
    with pytest.raises(ValueError, match=r"5MB"):
        storage.load()


def test_invalid_env_var_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Invalid TODO_MAX_JSON_SIZE_MB falls back to default 10MB."""
    db = tmp_path / "invalid_limit.json"
    storage = TodoStorage(str(db))

    # Set invalid value
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "invalid")

    # Create a JSON file larger than 10MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Should still raise ValueError with default 10MB limit (fallback)
    with pytest.raises(ValueError, match=r"10MB"):
        storage.load()


def test_negative_env_var_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Negative TODO_MAX_JSON_SIZE_MB falls back to default 10MB."""
    db = tmp_path / "negative_limit.json"
    storage = TodoStorage(str(db))

    # Set negative value (invalid)
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "-5")

    # Create a JSON file larger than 10MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Should still raise ValueError with default 10MB limit (fallback)
    with pytest.raises(ValueError, match=r"10MB"):
        storage.load()


def test_zero_env_var_falls_back_to_default(tmp_path, monkeypatch) -> None:
    """Zero TODO_MAX_JSON_SIZE_MB falls back to default 10MB."""
    db = tmp_path / "zero_limit.json"
    storage = TodoStorage(str(db))

    # Set zero (invalid - must be positive)
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "0")

    # Create a JSON file larger than 10MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    # Should still raise ValueError with default 10MB limit (fallback)
    with pytest.raises(ValueError, match=r"10MB"):
        storage.load()


def test_custom_limit_allows_larger_files(tmp_path, monkeypatch) -> None:
    """Custom limit of 20MB should allow files between 10MB and 20MB."""
    db = tmp_path / "allowed_large.json"
    storage = TodoStorage(str(db))

    # Set custom limit to 20MB
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "20")

    # Create a JSON file larger than 10MB but smaller than 20MB (~11MB)
    medium_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(medium_payload), encoding="utf-8")

    # Verify the file is larger than default 10MB but smaller than 20MB
    assert db.stat().st_size > 10 * 1024 * 1024
    assert db.stat().st_size < 20 * 1024 * 1024

    # Should load successfully with 20MB limit
    loaded = storage.load()
    assert len(loaded) == 65000


def test_error_message_shows_configured_limit(tmp_path, monkeypatch) -> None:
    """Error message displays the actual configured limit value."""
    db = tmp_path / "error_msg.json"
    storage = TodoStorage(str(db))

    # Test with default limit
    monkeypatch.delenv("TODO_MAX_JSON_SIZE_MB", raising=False)
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(65000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()
    assert "10MB" in str(exc_info.value)


def test_error_message_shows_custom_limit(tmp_path, monkeypatch) -> None:
    """Error message displays custom limit when configured."""
    db = tmp_path / "custom_error_msg.json"
    storage = TodoStorage(str(db))

    # Set custom limit
    monkeypatch.setenv("TODO_MAX_JSON_SIZE_MB", "7")

    # Create a file larger than 7MB
    large_payload = [
        {"id": i, "text": "x" * 100, "description": "y" * 100, "metadata": "z" * 50}
        for i in range(45000)
    ]
    db.write_text(json.dumps(large_payload), encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        storage.load()
    assert "7MB" in str(exc_info.value)
