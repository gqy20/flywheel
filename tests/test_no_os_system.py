"""Test to ensure no unsafe os.system usage exists in cli.py

This test addresses Issue #844 - ensuring that unsafe shell command execution
via os.system is not present in the codebase.
"""

import ast
import os
from pathlib import Path


def test_no_os_system_in_cli():
    """Ensure cli.py does not contain unsafe os.system calls.

    This test checks that the cli.py module does not use os.system(),
    which is unsafe for executing shell commands with user input.

    The os.system function is vulnerable to shell injection attacks when
    used with untrusted input. The codebase should use subprocess.run()
    with list arguments instead.

    Addresses Issue #844.
    """
    cli_path = Path(__file__).parent.parent / "src" / "flywheel" / "cli.py"

    # Read the source code
    with open(cli_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # Check for os.system in the source
    if 'os.system' in source_code:
        # Parse the AST to find the exact location
        tree = ast.parse(source_code)

        class OsSystemVisitor(ast.NodeVisitor):
            def __init__(self):
                self.found = False
                self.locations = []

            def visit_Call(self, node):
                # Check if this is an os.system call
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Name) and
                        node.func.value.id == 'os' and
                        node.func.attr == 'system'):
                        self.found = True
                        self.locations.append(
                            f"line {node.lineno}, col {node.col_offset}"
                        )
                self.generic_visit(node)

        visitor = OsSystemVisitor()
        visitor.visit(tree)

        assert not visitor.found, (
            f"Unsafe os.system() call found in cli.py at {visitor.locations}. "
            "Use subprocess.run() with list arguments instead. "
            "See Issue #844."
        )

    # If we get here, no os.system calls were found
    assert True
