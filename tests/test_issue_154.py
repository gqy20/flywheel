"""Test to verify issue #154 - code is NOT truncated.

This test verifies that the _save_with_todos method in storage.py
is complete and has all the required logic:
- os.write exception handling
- File closing
- os.fsync call
- Atomic replace operation
- finally block for file descriptor cleanup
"""

import ast
import tempfile
from pathlib import Path


def test_save_with_todos_method_is_complete():
    """Test that _save_with_todos method is complete and not truncated.

    This is a regression test for issue #154 which claimed the code was
    truncated at line 234 with incomplete error handling.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find the _save_with_todos method
    class MethodFinder(ast.NodeVisitor):
        def __init__(self):
            self.methods = {}

        def visit_FunctionDef(self, node):
            self.methods[node.name] = node
            self.generic_visit(node)

    finder = MethodFinder()
    finder.visit(tree)

    assert "_save_with_todos" in finder.methods, "_save_with_todos method not found"

    # Verify the method body has statements (not truncated)
    method_node = finder.methods["_save_with_todos"]
    assert len(method_node.body) > 10, "_save_with_todos appears to be truncated"

    # Verify key components exist in the source code
    assert "os.fsync(fd)" in source_code, "Missing os.fsync call"
    assert "os.close(fd)" in source_code, "Missing os.close call"
    assert "Path(temp_path).replace(self.path)" in source_code, "Missing atomic replace"
    assert "finally:" in source_code, "Missing finally block"
    assert "# Re-raise other OSErrors" in source_code or "Re-raise other OSErr" in source_code, \
        "Missing OSEerror re-raise comment"

    # Verify the method signature matches expected
    assert method_node.lineno > 190, "Method start line seems incorrect"


def test_save_with_todos_can_be_called():
    """Test that _save_with_todos method can actually be executed.

    This ensures the method is syntactically correct and runnable.
    """
    from flywheel.storage import Storage
    from flywheel.todo import Todo

    # Create a temporary storage
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # Add a todo
        todo = Todo(title="Test todo for issue #154")
        storage.add(todo)

        # Verify it was saved
        assert storage_path.exists(), "Todo file was not created"

        # Verify we can load it back
        storage2 = Storage(str(storage_path))
        loaded = storage2.get(todo.id)
        assert loaded is not None, "Todo was not saved correctly"
        assert loaded.title == "Test todo for issue #154"


def test_os_write_exception_handling_present():
    """Test that os.write exception handling logic is present in _save_with_todos."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Look for the exception handling pattern
    required_patterns = [
        "except OSError as e:",  # Exception handler
        "errno.EINTR",  # EINTR handling
        "raise",  # Re-raise logic
        "os.write(fd,",  # os.write call
    ]

    for pattern in required_patterns:
        assert pattern in source_code, f"Missing required pattern: {pattern}"


def test_finally_block_closes_fd():
    """Test that finally block properly closes file descriptor."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Look for the finally block pattern
    assert "finally:" in source_code, "Missing finally block"
    assert "if fd != -1:" in source_code, "Missing fd check in finally"
    assert "os.close(fd)" in source_code, "Missing os.close in finally block"
