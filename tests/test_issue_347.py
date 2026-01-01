"""Tests for Issue #347 - Verify this is a false positive.

Issue #347 claimed that storage.py was truncated at line 223 with
`parts = user.rspli`, but this is incorrect. The actual code is
`parts = user.rsplit('\\', 1)` which is syntactically correct.

This test verifies that:
1. The storage.py file is complete and not truncated
2. The code at line 223 uses the correct rsplit() method
3. The Storage class works correctly

Related: Issue #347 (FALSE POSITIVE)
"""

import pytest
from pathlib import Path


def test_storage_file_is_complete():
    """Test that storage.py is not truncated (Issue #347 false positive).

    Issue #347 incorrectly claimed that line 223 contained `parts = user.rspli`
    which would be a syntax error. The actual code is:
        parts = user.rsplit('\\', 1)

    This test verifies that:
    1. The storage module can be imported (would fail if syntax error existed)
    2. The Storage class has all expected methods
    3. Basic storage operations work correctly

    Related: Issue #347 - FALSE POSITIVE
    """
    # Import should work if file is complete
    # This would fail with SyntaxError if line 223 was actually `parts = user.rspli`
    from flywheel.storage import Storage

    # Verify the Storage class has all expected methods
    assert hasattr(Storage, 'add')
    assert hasattr(Storage, 'delete')
    assert hasattr(Storage, 'update')
    assert hasattr(Storage, 'get')
    assert hasattr(Storage, 'list')
    assert hasattr(Storage, '_load')
    assert hasattr(Storage, '_save')
    assert hasattr(Storage, '_secure_directory')


def test_windows_username_code_is_correct():
    """Verify the code at line 223 uses rsplit correctly.

    This test directly inspects the source code to verify that
    line 223 contains the correct `rsplit` method call, not the
    truncated `rspli` that was incorrectly reported in Issue #347.

    Related: Issue #347 - FALSE POSITIVE
    """
    # Read the actual source code
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        lines = f.readlines()

    # Line 223 (0-indexed as 222) should contain rsplit, not rspli
    line_223 = lines[222].strip()

    # Verify the line contains the correct code
    assert 'rsplit' in line_223, f"Line 223 should contain 'rsplit', got: {line_223}"
    assert 'rspli' not in line_223, f"Line 223 should NOT contain 'rspli', got: {line_223}"

    # Verify the expected pattern
    assert "parts = user.rsplit('\\\\', 1)" in line_223, \
        f"Line 223 should be 'parts = user.rsplit('\\\\', 1)', got: {line_223}"


def test_storage_basic_operations():
    """Test that Storage basic operations work correctly.

    If line 223 was actually truncated as claimed in Issue #347,
    the module would fail to import and this test would not run.

    Related: Issue #347 - FALSE POSITIVE
    """
    from flywheel.storage import Storage
    from flywheel.todo import Todo
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "test_todos.json"
        storage = Storage(str(storage_path))

        # Verify storage is working correctly
        assert storage is not None
        assert storage.list() == []

        # Add a todo and verify it works
        todo = Todo(title="Test todo")
        storage.add(todo)

        # Verify the todo was added
        todos = storage.list()
        assert len(todos) == 1
        assert todos[0].title == "Test todo"
