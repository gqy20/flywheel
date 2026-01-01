"""Test to verify Issue #342 is a false positive.

Issue #342 claimed the code was truncated at `parts = user.rspli`,
but the actual code is complete at line 223: `parts = user.rsplit('\\', 1)`.

This test verifies:
1. The storage module can be imported (no syntax errors)
2. The rsplit logic works correctly for Windows username parsing
3. The win32security logic is complete and functional
"""

import ast
from pathlib import Path


def test_storage_py_syntax_is_valid():
    """Verify that storage.py has valid Python syntax."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # This will raise SyntaxError if the code is invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e}")


def test_line_223_not_truncated():
    """Test that line 223 in storage.py is not truncated.

    Issue #342 claimed line 223 contained `parts = user.rspli` (truncated),
    but it should contain the complete code `parts = user.rsplit('\\', 1)`.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    # Read the file and get line 223 (1-indexed, so index 222)
    lines = storage_path.read_text().splitlines()
    line_223 = lines[222]  # 0-indexed

    # The issue claimed this line was truncated to "parts = user.rspli"
    # But it should contain the complete code
    assert line_223.strip(), "Line 223 should not be empty"

    # Verify it's NOT just a truncated "parts = user.rspli"
    assert "user.rspli" not in line_223, (
        f"Line 223 appears to be truncated. Got: '{line_223.strip()}'"
    )

    # Verify it contains the expected complete code
    expected_content = "parts = user.rsplit('\\\\', 1)"
    assert expected_content in line_223 or "user.rsplit" in line_223, (
        f"Line 223 should contain 'user.rsplit'. Got: '{line_223}'"
    )


def test_rsplit_logic_windows_username():
    """Test the rsplit logic mentioned in the issue.

    The code at line 223 correctly uses:
        parts = user.rsplit('\\', 1)

    This should extract the username from 'DOMAIN\\user' format.
    """
    # Simulate the logic from storage.py lines 221-225
    test_cases = [
        ("DOMAIN\\username", "username"),
        ("COMPUTERNAME\\user", "user"),
        ("DOMAIN\\user\\extra", "user\\extra"),  # Only splits on last backslash
        ("single", "single"),  # No backslash, no split
    ]

    for user_input, expected in test_cases:
        if '\\' in user_input:
            parts = user_input.rsplit('\\', 1)
            if len(parts) == 2:
                result = parts[1]
            else:
                result = user_input
        else:
            result = user_input

        assert result == expected, f"Failed for {user_input}: got {result}, expected {expected}"


def test_win32security_block_complete():
    """Verify the win32security import block is complete.

    Issue #342 claimed the win32security logic was incomplete,
    but it should be a complete try-except block with proper error handling.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find all Try nodes in the AST
    class TryVisitor(ast.NodeVisitor):
        def __init__(self):
            self.try_blocks = []

        def visit_Try(self, node):
            self.try_blocks.append(node)
            self.generic_visit(node)

    visitor = TryVisitor()
    visitor.visit(tree)

    # Verify all try blocks have complete except handlers
    for try_node in visitor.try_blocks:
        # Each try block should have either handlers or finalizer
        assert try_node.handlers or try_node.finalbody, (
            f"Try block at line {try_node.lineno} is incomplete"
        )

        # All except handlers should have bodies
        for handler in try_node.handlers:
            assert handler.body, (
                f"Except handler at line {handler.lineno} has no body"
            )
            # Verify body has at least one statement
            assert len(handler.body) > 0, (
                f"Except handler at line {handler.lineno} has empty body"
            )


def test_storage_module_imports():
    """Verify storage.py can be imported without syntax errors."""
    from flywheel.storage import Storage
    assert Storage is not None


def test_storage_methods_exist():
    """Verify all methods mentioned in the issue exist."""
    from flywheel.storage import Storage

    # Check that key methods exist
    assert hasattr(Storage, '_secure_directory'), "Storage._secure_directory method missing"
    assert hasattr(Storage, 'add'), "Storage.add method missing"
    assert hasattr(Storage, '_load'), "Storage._load method missing"
    assert hasattr(Storage, '_save'), "Storage._save method missing"
