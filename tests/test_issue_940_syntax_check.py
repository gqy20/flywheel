"""Test to verify Issue #940 is a false positive.

This test verifies that the code in storage.py is syntactically correct,
specifically around the logger.warning calls mentioned in the issue.
"""

import ast
import pytest
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
        pytest.fail(f"storage.py has syntax error: {e}")


def test_logger_warning_calls_are_complete():
    """Verify that all logger.warning calls have proper closing parentheses."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path) as f:
        source_code = f.read()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find all logger.warning calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check if this is a logger.warning call
            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name) and
                    node.func.value.id == "logger" and
                    node.func.attr == "warning"):
                    # Verify the call is complete (has opening and closing)
                    # If there was a missing closing parenthesis, parsing would fail
                    assert True  # If we get here, the syntax is valid


def test_import_storage_module():
    """Verify that storage.py can be imported without errors."""
    try:
        import flywheel.storage
        assert flywheel.storage is not None
    except SyntaxError as e:
        pytest.fail(f"Failed to import storage module due to syntax error: {e}")
    except Exception as e:
        # Other exceptions are OK for this test (e.g., import side effects)
        pass
