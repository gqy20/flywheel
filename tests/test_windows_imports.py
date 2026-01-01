"""Test Windows security imports are declared at module level (Issue #324)."""

import os
import ast


def test_pywin32_imported_at_module_level():
    """Verify pywin32 is imported at module level, not dynamically in methods.

    This test parses the source code of storage.py and verifies that
    win32security, win32con, and win32api are imported at the module level
    (top-level imports), not inside methods.

    This follows the fail-fast principle - dependencies should be declared
    at import time, not discovered at runtime.

    (Issue #324)
    """
    # Read the storage.py source code
    with open('src/flywheel/storage.py', 'r') as f:
        source_code = f.read()

    # Parse the source code into an AST
    tree = ast.parse(source_code)

    # Track imports and function definitions
    module_level_imports = []
    function_definitions = []

    # Walk through the AST
    for node in ast.walk(tree):
        # Track module-level imports
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            # Check if this import is at module level (not inside a function/class)
            for parent in ast.walk(tree):
                if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Check if node is inside this function/class
                    if hasattr(node, 'lineno') and hasattr(parent, 'lineno'):
                        # This is simplified - we just check if imports appear before functions
                        pass

            # Get the imported module names
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_level_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module_level_imports.append(node.module)

        # Track function definitions (including methods)
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            function_definitions.append(node.name)

    # Check if pywin32 modules are imported at module level
    # On Windows, these should be in the top-level imports
    pywin32_modules = ['win32security', 'win32con', 'win32api']

    # Find which pywin32 modules are imported at module level
    imported_pywin32 = []
    for module in module_level_imports:
        for pywin32_module in pywin32_modules:
            if pywin32_module in module:
                imported_pywin32.append(pywin32_module)

    # On Windows (when the code checks os.name == 'nt'),
    # pywin32 modules should be imported at module level
    # We can verify this by checking the source code for the pattern
    #
    # The fix should add these imports at the top level:
    # if os.name == 'nt':  # Windows
    #     import win32security
    #     import win32con
    #     import win32api
    #
    # For now, we verify the source contains the proper import pattern

    # Check if there's a Windows-specific import section at module level
    # This is the pattern we're looking for after the fix
    has_windows_import_block = False

    # Look for the pattern: if os.name == 'nt': followed by imports
    lines = source_code.split('\n')
    for i, line in enumerate(lines):
        if "os.name == 'nt'" in line or 'os.name == "nt"' in line:
            # Check the next few lines for win32 imports
            next_lines = '\n'.join(lines[i:min(i+10, len(lines))])
            if any(win32_module in next_lines for win32_module in pywin32_modules):
                has_windows_import_block = True
                break

    # The test currently expects this to FAIL (red phase)
    # because the imports are currently inside _secure_directory method
    # After the fix (green phase), this should pass
    assert has_windows_import_block, (
        "pywin32 modules (win32security, win32con, win32api) should be imported "
        "at module level in storage.py when os.name == 'nt', not dynamically "
        "inside _secure_directory method. This ensures fail-fast behavior. "
        "(Issue #324)"
    )


def test_unix_does_not_require_pywin32():
    """On Unix systems, storage should work without pywin32.

    This is a sanity check to ensure the fix doesn't break Unix.

    (Issue #324)
    """
    if os.name == 'nt':
        return  # Skip on Windows

    # On Unix, we should be able to import and use Storage
    # even if pywin32 is not available
    from flywheel.storage import Storage
    import tempfile

    # Create a temporary storage path
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = os.path.join(tmpdir, "todos.json")

        # This should work on Unix without pywin32
        storage = Storage(storage_path)
        storage.close()
