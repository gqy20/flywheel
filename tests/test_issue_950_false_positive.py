"""Test for Issue #950 - Verify it's a false positive.

Issue #950 claimed there was a missing closing parenthesis in a logger.warning call
at line 236 in src/flywheel/storage.py. However, upon inspection:

1. Line 236 is actually a comment: "# Reference to module-level logger..."
2. The actual logger.warning calls at lines 217-219 and 224-227 are properly formatted
3. All logger.warning calls in the file have correct syntax with closing parentheses

This test verifies that the code is syntactically correct and that Issue #950
is a false positive from an AI scanner (similar to issues #935 and #940).
"""

import ast
import pytest
from pathlib import Path


def test_storage_py_syntax_is_valid_issue_950():
    """Verify that storage.py has valid Python syntax (Issue #950)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # Parse the source code - this will raise SyntaxError if invalid
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        pytest.fail(f"Issue #950 - storage.py has syntax error: {e}")


def test_line_236_is_comment_issue_950():
    """Verify that line 236 is a comment, not a logger.warning call (Issue #950)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # Line 236 (0-indexed as 235)
    line_236 = lines[235].strip()

    # Verify it's a comment
    assert line_236.startswith("#"), \
        f"Issue #950 - Line 236 should be a comment, but is: {line_236}"
    assert "logger" in line_236.lower(), \
        f"Issue #950 - Line 236 comment should mention logger"


def test_logger_warning_calls_around_line_236_issue_950():
    """Verify that logger.warning calls near line 236 are properly formatted (Issue #950)."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find and verify all logger.warning calls
    logger_warning_count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "logger" and
                    node.func.attr == "warning"):
                    logger_warning_count += 1
                    # If we can parse it, the syntax is valid (no missing parentheses)

    # Verify we found logger.warning calls
    assert logger_warning_count > 0, "Should find logger.warning calls in storage.py"

    # The fact that we could parse the AST proves no missing parentheses


def test_specific_logger_warning_lines_issue_950():
    """Verify the specific logger.warning calls mentioned in Issue #950."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        lines = f.readlines()

    # Check lines 217-219 (first logger.warning in _get_stale_lock_timeout)
    line_217 = lines[216].strip()
    assert "logger.warning(" in line_217, \
        f"Issue #950 - Line 217 should contain logger.warning(: {line_217}"

    line_219 = lines[218].strip()
    assert ")" in line_219, \
        f"Issue #950 - Line 219 should have closing parenthesis: {line_219}"

    # Check lines 224-227 (second logger.warning in _get_stale_lock_timeout)
    line_224 = lines[223].strip()
    assert "logger.warning(" in line_224, \
        f"Issue #950 - Line 224 should contain logger.warning(: {line_224}"

    line_227 = lines[226].strip()
    assert ")" in line_227, \
        f"Issue #950 - Line 227 should have closing parenthesis: {line_227}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
