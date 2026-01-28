"""Test to validate issue #320 - Code truncation verification.

This test verifies that the code in storage.py line 234 is NOT truncated
and contains complete, valid Python code.

Issue #320 claimed that line 234 contained only "# Bui" (truncated comment),
but this was a false positive from an AI scanner. The actual code contains
the complete comment "# Fallback: Use local computer for non-domain environments".
"""

import ast
from pathlib import Path


def test_line_234_not_truncated():
    """Test that line 234 in storage.py is not truncated."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    # Read the file and get line 234 (1-indexed, so index 233)
    lines = storage_path.read_text().splitlines()
    line_234 = lines[233]  # 0-indexed

    # The issue claimed this line was truncated to "# Bui"
    # But it should contain the complete comment
    assert line_234.strip(), "Line 234 should not be empty"

    # Verify it's NOT just a truncated "# Bui"
    assert line_234.strip() != "# Bui", (
        f"Line 234 appears to be truncated. Got: '{line_234.strip()}'"
    )

    # Verify it contains the expected complete comment
    expected_content = "Fallback: Use local computer for non-domain environments"
    assert expected_content in line_234, (
        f"Line 234 should contain '{expected_content}'. Got: '{line_234}'"
    )

    # Verify the file has valid Python syntax
    source_code = storage_path.read_text()
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e}")


def test_except_block_completeness():
    """Test that the except block starting at line 233 is complete."""
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
