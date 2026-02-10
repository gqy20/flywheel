"""Regression tests for issue #1883: Path traversal vulnerability via user-controlled db_path.

Issue: TodoStorage accepts arbitrary user-controlled paths without validation,
allowing path traversal attacks via '../' sequences or absolute paths outside
the working directory.

Attack vectors:
- '../../../etc/passwd' - read system files
- '/tmp/test.json' - write to arbitrary locations
- '../../sensitive.json' - access files outside project

These tests should FAIL before the fix and PASS after the fix.
"""

from __future__ import annotations

import pytest

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


class TestPathTraversalRejection:
    """Tests that malicious path traversal attempts are rejected."""

    def test_rejects_path_with_parent_traversal_sequences(self, tmp_path) -> None:
        """Issue #1883: Paths with '../' should be rejected."""
        # Change to temp directory to test relative paths
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
                TodoStorage("../../../etc/passwd")

            with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
                TodoStorage("../../sensitive.json")

            with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
                TodoStorage("../outside.json")
        finally:
            os.chdir(original_cwd)

    def test_rejects_absolute_path_outside_cwd(self, tmp_path) -> None:
        """Issue #1883: Absolute paths outside working directory should be rejected."""
        # These should all be rejected
        with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
            TodoStorage("/etc/passwd")

        with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
            TodoStorage("/tmp/test.json")

        with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
            TodoStorage("/var/log/app.json")

    def test_rejects_resolved_path_that_escapes_cwd(self, tmp_path) -> None:
        """Issue #1883: Even resolved paths that escape should be rejected."""
        import os

        # Create a nested directory structure
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)

        os.chdir(nested)

        try:
            # After resolution, this would escape to tmp_path's parent
            escape_path = "../../../escape.json"
            with pytest.raises(ValueError, match=r"(path|safe|traversal|escape|invalid)"):
                TodoStorage(escape_path)
        finally:
            os.chdir(tmp_path)

    def test_rejects_null_byte_injection(self) -> None:
        """Issue #1883: Paths with null bytes should be rejected."""
        with pytest.raises((ValueError, TypeError)):
            TodoStorage("test\x00.json")


class TestSafePathsAllowed:
    """Tests that legitimate paths are still accepted."""

    def test_default_path_works(self, tmp_path) -> None:
        """Issue #1883: Default '.todo.json' should always work."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            storage = TodoStorage()  # Uses default .todo.json
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)

    def test_simple_relative_path_in_cwd(self, tmp_path) -> None:
        """Issue #1883: Simple relative paths in CWD should work."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            storage = TodoStorage("mydb.json")
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)

    def test_nested_subdirectory_in_cwd(self, tmp_path) -> None:
        """Issue #1883: Nested paths within CWD should work."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            storage = TodoStorage("data/todos/todo.json")
            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)

    def test_absolute_path_within_cwd(self, tmp_path) -> None:
        """Issue #1883: Absolute paths that resolve to within CWD should work."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Create an absolute path that is within tmp_path (now the CWD)
            safe_absolute = tmp_path / "safe.json"
            storage = TodoStorage(str(safe_absolute))

            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)

    def test_nested_absolute_path_within_cwd(self, tmp_path) -> None:
        """Issue #1883: Nested absolute paths within CWD should work."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            nested = tmp_path / "subdir" / "nested" / "db.json"
            storage = TodoStorage(str(nested))

            storage.save([Todo(id=1, text="test")])
            loaded = storage.load()
            assert len(loaded) == 1
        finally:
            os.chdir(original_cwd)


class TestPathTraversalPreventsFileAccess:
    """Tests that path traversal cannot be used to access arbitrary files."""

    def test_cannot_read_system_file_via_traversal(self, tmp_path) -> None:
        """Issue #1883: Should not be able to read /etc/passwd via traversal."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            # Even if we create a malicious storage, load should fail
            with pytest.raises((ValueError, OSError)):
                storage = TodoStorage("../../../etc/passwd")
                storage.load()
        finally:
            os.chdir(original_cwd)

    def test_cannot_write_to_system_directory_via_traversal(self, tmp_path) -> None:
        """Issue #1883: Should not be able to write to /tmp via traversal."""
        import os
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
            with pytest.raises(ValueError):
                storage = TodoStorage("../../../tmp/malicious.json")
                storage.save([Todo(id=1, text="malicious")])
        finally:
            os.chdir(original_cwd)
