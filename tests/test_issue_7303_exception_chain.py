"""Regression test for issue #7303: save() exception handling should preserve exception chain.

This test verifies that when save() catches and re-raises OSError, it preserves
the original exception as __cause__ for better debugging (using raise ... from e).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_save_preserves_oserror_exception_chain(tmp_path) -> None:
    """Test that save() preserves the original OSError as __cause__ when re-raising.

    Regression test for issue #7303:
    When os.replace() or other OS operations fail, the exception should preserve
    the original exception chain using 'raise ... from e' pattern.
    """
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial valid data
    original_todos = [Todo(id=1, text="original")]
    storage.save(original_todos)

    # Simulate os.replace failure
    def failing_replace(*args, **kwargs):
        raise OSError("Simulated rename failure")

    with (
        patch("flywheel.storage.os.replace", failing_replace),
        pytest.raises(OSError, match="Simulated rename failure") as exc_info,
    ):
        storage.save([Todo(id=2, text="new")])

    # The key assertion: exception should have __cause__ set (exception chain preserved)
    assert exc_info.value.__cause__ is not None, (
        "OSError should have __cause__ set to preserve exception chain. "
        "Use 'raise ... from e' to preserve the original exception context."
    )
    assert isinstance(exc_info.value.__cause__, OSError)
    assert "Simulated rename failure" in str(exc_info.value.__cause__)


def test_save_preserves_exception_chain_on_fdopen_write_failure(tmp_path) -> None:
    """Test that save() preserves exception chain when writing via fdopen fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate fdopen write failure
    def failing_fdopen(*args, **kwargs):
        # Return a file-like object that fails on write
        class FailingFile:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def write(self, content):
                raise OSError("Simulated write failure")

        return FailingFile()

    with (
        patch("flywheel.storage.os.fdopen", failing_fdopen),
        pytest.raises(OSError, match="Simulated write failure") as exc_info,
    ):
        storage.save([Todo(id=1, text="test")])

    # Exception should have __cause__ set
    assert exc_info.value.__cause__ is not None, (
        "OSError should have __cause__ set to preserve exception chain."
    )


def test_save_preserves_exception_chain_on_fchmod_failure(tmp_path) -> None:
    """Test that save() preserves exception chain when os.fchmod fails."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Simulate fchmod failure
    def failing_fchmod(*args, **kwargs):
        raise OSError("Simulated fchmod failure")

    with (
        patch("flywheel.storage.os.fchmod", failing_fchmod),
        pytest.raises(OSError, match="Simulated fchmod failure") as exc_info,
    ):
        storage.save([Todo(id=1, text="test")])

    # Exception should have __cause__ set
    assert exc_info.value.__cause__ is not None, (
        "OSError should have __cause__ set to preserve exception chain."
    )
