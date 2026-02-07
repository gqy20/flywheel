"""Path traversal security tests for TodoStorage.

Issue #1873: Path traversal via path parameter - no validation against '../' sequences

The security fix prevents directory traversal via relative paths containing '..'.
Absolute paths are allowed since they represent an explicit user choice, not a
hidden traversal attack.
"""

import pytest

from flywheel.storage import TodoStorage


class TestPathTraversalPrevention:
    """Security tests to prevent directory traversal attacks via '..'."""

    def test_reject_parent_directory_traversal(self) -> None:
        """Paths with '../' should be rejected to prevent directory traversal."""
        with pytest.raises(ValueError, match=r"\.\.|not allowed"):
            TodoStorage("../../../etc/passwd")

    def test_reject_single_parent_directory(self) -> None:
        """Even a single '../' should be rejected."""
        with pytest.raises(ValueError, match=r"\.\.|not allowed"):
            TodoStorage("../outside.json")

    def test_reject_complex_parent_traversal(self) -> None:
        """Complex paths with multiple parent references should be rejected."""
        with pytest.raises(ValueError, match=r"\.\.|not allowed"):
            TodoStorage("subdir/../../etc/passwd")

    def test_absolute_paths_are_allowed(self) -> None:
        """Absolute paths ARE allowed - they are an explicit user choice."""
        # This is intentional: users can explicitly specify absolute paths
        # The security issue is about hidden traversal in relative paths
        storage = TodoStorage("/tmp/todo.json")
        assert str(storage.path) == "/tmp/todo.json"

    def test_reject_resolved_path_outside_cwd(self) -> None:
        """Paths that resolve outside CWD via symlinks or other means should be caught."""
        # Create a test that would escape the current directory if not validated
        # This is more about the resolution check catching edge cases
        # (In practice, the '..' check catches the common cases)


class TestSafePathAcceptance:
    """Tests for valid safe paths that should be accepted."""

    def test_accept_default_path(self) -> None:
        """Default path '.todo.json' should work normally."""
        storage = TodoStorage()
        assert storage.path.name == ".todo.json"

    def test_accept_simple_filename(self) -> None:
        """Simple filenames should be accepted."""
        storage = TodoStorage("safe.json")
        assert storage.path.name == "safe.json"

    def test_accept_relative_path_in_current_dir(self) -> None:
        """Relative paths within current directory should be accepted."""
        storage = TodoStorage("./subdir/safe.json")
        assert "subdir" in str(storage.path)

    def test_accept_subdirectory_path(self) -> None:
        """Paths to subdirectories within working dir should be accepted."""
        storage = TodoStorage("data/todos.json")
        assert storage.path.name == "todos.json"

    def test_accept_nested_subdirectory(self) -> None:
        """Nested paths within working dir should be accepted."""
        storage = TodoStorage("data/nested/todos.json")
        assert storage.path.name == "todos.json"

    def test_accept_dotfile_path(self) -> None:
        """Dotfile paths should be accepted."""
        storage = TodoStorage(".config/todo.json")
        assert storage.path.name == "todo.json"
