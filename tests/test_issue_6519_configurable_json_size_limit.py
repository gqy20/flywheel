"""Tests for configurable JSON file size limit (Issue #6519).

These tests verify that:
1. Default limit remains 10MB for security
2. Limit can be overridden via environment variable FLYWHEEL_MAX_JSON_SIZE_MB
3. Invalid environment variable values are handled gracefully (fall back to default)
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage, _get_max_json_size_bytes


class TestConfigurableJsonSizeLimit:
    """Test suite for configurable JSON file size limit."""

    def test_default_limit_is_10mb(self) -> None:
        """Default limit should be 10MB when no env var is set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove the env var if it exists
            os.environ.pop("FLYWHEEL_MAX_JSON_SIZE_MB", None)
            limit = _get_max_json_size_bytes()
            assert limit == 10 * 1024 * 1024  # 10MB in bytes

    def test_limit_can_be_configured_via_env_var(self) -> None:
        """Limit can be overridden via FLYWHEEL_MAX_JSON_SIZE_MB environment variable."""
        # Test with 20MB
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "20"}):
            limit = _get_max_json_size_bytes()
            assert limit == 20 * 1024 * 1024  # 20MB in bytes

        # Test with 50MB
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "50"}):
            limit = _get_max_json_size_bytes()
            assert limit == 50 * 1024 * 1024  # 50MB in bytes

    def test_invalid_env_var_falls_back_to_default(self) -> None:
        """Invalid environment variable values fall back to default 10MB."""
        # Test with non-numeric value
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "invalid"}):
            limit = _get_max_json_size_bytes()
            assert limit == 10 * 1024 * 1024  # Falls back to default

        # Test with negative value
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "-5"}):
            limit = _get_max_json_size_bytes()
            assert limit == 10 * 1024 * 1024  # Falls back to default

        # Test with zero
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "0"}):
            limit = _get_max_json_size_bytes()
            assert limit == 10 * 1024 * 1024  # Falls back to default

        # Test with empty string
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": ""}):
            limit = _get_max_json_size_bytes()
            assert limit == 10 * 1024 * 1024  # Falls back to default

    def test_limit_is_enforced_when_loading_oversized_file(self, tmp_path: Path) -> None:
        """The configured limit is enforced when loading oversized files."""
        db = tmp_path / "large.json"
        storage = TodoStorage(str(db))

        # Create a file larger than 1MB (we use 1MB for faster testing)
        # 1.1MB of content
        large_content = '[{"id": 1, "text": "' + "x" * (1024 * 1024) + '"}]'
        db.write_text(large_content, encoding="utf-8")

        # With default limit (10MB), this should load fine
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("FLYWHEEL_MAX_JSON_SIZE_MB", None)
            # Should not raise - file is ~1MB, default limit is 10MB
            todos = storage.load()
            assert len(todos) == 1

        # With 0.5MB limit, this should raise
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "0.5"}):
            # Reload storage to pick up new limit
            storage2 = TodoStorage(str(db))
            with pytest.raises(ValueError, match=r"too large|limit"):
                storage2.load()

    def test_env_var_accepts_floating_point_values(self) -> None:
        """Environment variable accepts floating point values like 0.5 for 512KB."""
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "0.5"}):
            limit = _get_max_json_size_bytes()
            assert limit == int(0.5 * 1024 * 1024)  # 512KB in bytes

    def test_storage_load_uses_configured_limit(self, tmp_path: Path) -> None:
        """TodoStorage.load() uses the configured limit from environment variable."""
        db = tmp_path / "test.json"

        # Create a small valid file
        db.write_text('[{"id": 1, "text": "test"}]', encoding="utf-8")

        # With a very small limit (0.001MB = 1KB), even small files should work
        # if they're under the limit
        with patch.dict(os.environ, {"FLYWHEEL_MAX_JSON_SIZE_MB": "0.001"}):
            storage2 = TodoStorage(str(db))
            # File is ~30 bytes, limit is 1KB, should work
            todos = storage2.load()
            assert len(todos) == 1
