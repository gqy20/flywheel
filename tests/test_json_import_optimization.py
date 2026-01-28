"""Test to verify json module is not re-imported in hot paths.

This test checks that the json module is imported at the module level
and not re-imported inside methods that are called frequently (like logging format).
"""

import ast
import pytest


def test_no_redundant_json_import_in_format_method():
    """Verify that json is not imported inside the format method.

    The json module should be imported at the top of the file (line 12)
    and should not be re-imported inside the format method of the
    JSONFormatter class, as this is a hot path in logging operations.
    """
    storage_file = "src/flywheel/storage.py"

    with open(storage_file, "r") as f:
        source = f.read()

    tree = ast.parse(source)

    # Find the JSONFormatter class
    json_formatter_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "JSONFormatter":
            json_formatter_class = node
            break

    assert json_formatter_class is not None, "JSONFormatter class not found"

    # Find the format method
    format_method = None
    for item in json_formatter_class.body:
        if isinstance(item, ast.FunctionDef) and item.name == "format":
            format_method = item
            break

    assert format_method is not None, "format method not found in JSONFormatter"

    # Check for any import statements inside the format method
    has_json_import = False
    import_line = None

    for node in ast.walk(format_method):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "json":
                    has_json_import = True
                    import_line = node.lineno
                    break

    # Get the actual line number from the source file
    if has_json_import and import_line:
        # Find the actual line number in the source file by counting
        # We need to find where the method starts in the actual source
        lines = source.split('\n')
        method_start_line = None
        for i, line in enumerate(lines, 1):
            if 'def format(self, record):' in line:
                method_start_line = i
                break

        if method_start_line:
            # The import line is relative to the method start
            actual_line = method_start_line + (import_line - format_method.lineno)

    assert not has_json_import, (
        f"The 'json' module should not be imported inside the format method. "
        f"It is already imported at the module level (line 12). "
        f"Re-importing inside a hot path (logging) adds unnecessary overhead. "
        f"Please remove the 'import json' statement from the format method."
    )
