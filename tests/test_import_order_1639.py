"""Test that import statements are properly placed at the top of the file.

This test ensures that all import statements are at the top of the file,
not interleaved with code, which can cause confusion and potential issues.
(Issue #1639)
"""

import ast
import re
from pathlib import Path


def test_storage_py_imports_at_top():
    """Test that all imports in storage.py are at the top of the file.

    This ensures that:
    1. No import statements appear after code definitions
    2. All imports are properly grouped at the module level
    3. The file follows Python import conventions (PEP 8)

    Issue #1639: The import `from flywheel.todo import Todo` was placed
    after the _AiofilesPlaceholder class definition, which violates
    Python conventions and can cause confusion.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"

    with open(storage_path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    # Parse the file as AST
    tree = ast.parse(content)

    # Track the line number of the last import statement
    last_import_line = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Update the last import line
            if node.lineno > last_import_line:
                last_import_line = node.lineno

    # Find the first non-import, non-comment, non-docstring line
    # that represents actual code (class/function def or statement)
    first_code_line = None

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Skip comments
        if stripped.startswith("#"):
            continue

        # Skip string literals (docstrings)
        if stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # If we reach here, this is the first line of actual code
        # Check if it's an import or a code definition
        if stripped.startswith("import ") or stripped.startswith("from "):
            continue  # This is an import, keep going

        # This is the first actual code line
        first_code_line = i
        break

    # Assert that all imports come before any code
    # The last import should be before the first code statement
    assert last_import_line > 0, "No imports found in file"

    # Allow for some whitespace between imports and code
    # But check that no import appears after code has started
    for i, line in enumerate(lines[last_import_line:], start=last_import_line):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            continue

        # If we find an import after code has started, fail
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Check if there's any code (class/def) before this import
            for j in range(last_import_line, i):
                if any(lines[j].strip().startswith(k) for k in ["class ", "def ", "async def "]):
                    raise AssertionError(
                        f"Import statement found at line {i + 1} after code definition at line {j + 1}: "
                        f"'{stripped}'. All imports should be at the top of the file."
                    )

    # Specifically check that the Todo import is not after code
    todo_import_found = False
    todo_import_line = None
    code_before_todo_import = False

    for i, line in enumerate(lines, start=1):
        if "from flywheel.todo import Todo" in line:
            todo_import_found = True
            todo_import_line = i

            # Check if there's any code before this import
            for j in range(i):
                stripped = lines[j].strip()
                if stripped.startswith("class ") or stripped.startswith("def "):
                    code_before_todo_import = True
                    break

            break

    if todo_import_found and code_before_todo_import:
        raise AssertionError(
            f"The import 'from flywheel.todo import Todo' at line {todo_import_line} "
            f"appears after a code definition. All imports should be at the top of the file."
        )


def test_storage_py_no_runtime_import_errors():
    """Test that storage.py can be imported without runtime errors.

    This ensures that all imports are valid and don't cause NameError or ImportError.
    """
    # Try to import the module
    try:
        import flywheel.storage
    except (NameError, ImportError) as e:
        raise AssertionError(
            f"Failed to import flywheel.storage: {e}. "
            "This may be due to improperly placed import statements."
        ) from e
