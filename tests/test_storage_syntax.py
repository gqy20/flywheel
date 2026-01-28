"""Test that storage.py has valid Python syntax.

This test ensures that all except statements have proper colons and the file
can be parsed without syntax errors.
"""

import ast
from pathlib import Path


def test_storage_syntax_is_valid():
    """Test that storage.py has valid Python syntax."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    assert storage_path.exists(), "storage.py file not found"

    source_code = storage_path.read_text()

    # This will raise SyntaxError if there's a syntax error
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(f"Syntax error in storage.py: {e}")


def test_except_statements_have_colons():
    """Test that all 'except' statements in storage.py have colons."""
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    source_code = storage_path.read_text()

    # Parse the source code
    tree = ast.parse(source_code)

    # Find all except handlers
    class ExceptVisitor(ast.NodeVisitor):
        def __init__(self):
            self.except_handlers = []

        def visit_ExceptHandler(self, node):
            self.except_handlers.append(node)
            self.generic_visit(node)

    visitor = ExceptVisitor()
    visitor.visit(tree)

    # All except handlers should be valid (AST parsing ensures this)
    # If we got here, all except statements are syntactically valid
    assert len(visitor.except_handlers) > 0, "No except handlers found in storage.py"


def test_can_import_storage():
    """Test that storage module can be imported without syntax errors."""
    try:
        from flywheel.storage import Storage
        assert Storage is not None
    except SyntaxError as e:
        raise AssertionError(f"Failed to import storage module due to syntax error: {e}")
