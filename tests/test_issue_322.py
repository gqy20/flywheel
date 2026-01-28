"""Test to validate issue #322 - Windows security code truncation verification.

This test verifies that the code in storage.py line 227 is NOT truncated
and contains complete, valid Python code.

Issue #322 claimed that line 227 contained truncated code (ending with 'Bui'),
but this is a false positive from an AI scanner. The actual code contains
the complete domain extraction logic.
"""

import ast
from pathlib import Path


def test_line_227_not_truncated():
    """Test that line 227 in storage.py is not truncated."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    # Read the file and get line 227 (1-indexed, so index 226)
    lines = storage_path.read_text().splitlines()
    line_227 = lines[226]  # 0-indexed

    # The issue claimed this line was truncated
    # But it should contain the complete domain extraction logic
    assert line_227.strip(), "Line 227 should not be empty"

    # Verify it's NOT a truncated line
    assert line_227.strip() != "Bui", (
        f"Line 227 appears to be truncated. Got: '{line_227.strip()}'"
    )

    # Verify it contains the expected domain extraction code
    expected_content = "dc_parts"
    assert expected_content in line_227, (
        f"Line 227 should contain '{expected_content}'. Got: '{line_227}'"
    )

    # Verify it contains the complete list comprehension
    assert "startswith('DC=')" in line_227, (
        f"Line 227 should contain complete domain extraction logic. Got: '{line_227}'"
    )


def test_domain_extraction_logic_completeness():
    """Test that the domain extraction logic is complete and syntactically valid."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Verify the file has valid Python syntax
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"storage.py has syntax error at line {e.lineno}: {e}")

    # Verify line 227 is part of a complete code block
    lines = source_code.splitlines()
    line_227 = lines[226]

    # The line should be a complete list comprehension
    assert "dc_parts = [" in line_227, (
        f"Line 227 should contain dc_parts assignment. Got: '{line_227}'"
    )
    assert line_227.strip().endswith("]"), (
        f"Line 227 should be a complete list comprehension ending with ']'. Got: '{line_227}'"
    )


def test_try_block_completeness_around_line_227():
    """Test that the try block containing line 227 is complete."""
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
