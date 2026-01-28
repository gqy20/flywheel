"""Tests to verify msvcrt is NOT used for Windows locking (Issue #425).

Issue #425 reported that Windows file locking used advisory locks (msvcrt.locking),
which do not enforce mutual exclusion. This test verifies that the codebase
now uses mandatory locking (win32file.LockFileEx) instead.

This test confirms:
1. msvcrt.locking is NOT imported or used in storage.py
2. win32file.LockFileEx IS used for mandatory locking
"""

import os
import ast
import pytest
from pathlib import Path


class TestIssue425NoMsvcrt:
    """Verify that msvcrt is NOT used for Windows file locking."""

    def test_storage_py_does_not_import_msvcrt(self):
        """Test that storage.py does not import msvcrt module."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Parse the AST to find all imports
        tree = ast.parse(content)

        # Check all import statements
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "msvcrt", (
                        "storage.py should NOT import msvcrt. "
                        "msvcrt.locking provides advisory locks which do not enforce "
                        "mutual exclusion. Use win32file.LockFileEx for mandatory locking."
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("msvcrt"), (
                        "storage.py should NOT import from msvcrt module. "
                        "msvcrt.locking provides advisory locks which do not enforce "
                        "mutual exclusion. Use win32file.LockFileEx for mandatory locking."
                    )

    def test_storage_py_does_not_use_msvcrt_locking(self):
        """Test that storage.py does not reference msvcrt.locking anywhere."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Check for any reference to msvcrt
        assert "msvcrt" not in content.lower(), (
            "storage.py should NOT reference msvcrt anywhere. "
            "msvcrt.locking provides advisory locks which do not enforce "
            "mutual exclusion. The code should use win32file.LockFileEx "
            "for mandatory locking instead."
        )

    def test_windows_uses_win32file_lockfileex(self):
        """Test that Windows code path uses win32file.LockFileEx."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Verify that win32file.LockFileEx is used for mandatory locking
        assert "win32file.LockFileEx" in content, (
            "storage.py should use win32file.LockFileEx for Windows file locking. "
            "LockFileEx provides MANDATORY locking which enforces mutual exclusion "
            "on all processes, preventing concurrent writes."
        )

    def test_windows_imports_pywin32_modules(self):
        """Test that Windows imports pywin32 modules for mandatory locking."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Parse the AST
        tree = ast.parse(content)

        # Check for Windows-specific imports
        found_pywin32_imports = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in ["win32file", "win32con", "pywintypes"]:
                        found_pywin32_imports = True
                        break

        assert found_pywin32_imports, (
            "storage.py should import pywin32 modules (win32file, win32con, pywintypes) "
            "for Windows mandatory locking. These modules provide LockFileEx which "
            "enforces mutual exclusion at the OS level."
        )

    def test_mandatory_locking_comment_present(self):
        """Test that mandatory locking is documented in comments."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Verify documentation mentions mandatory locking
        assert "MANDATORY LOCKING" in content or "mandatory locking" in content.lower(), (
            "storage.py should document that Windows uses mandatory locking. "
            "This is important for users to understand that file locks are "
            "enforced at the OS level, not just advisory."
        )

    def test_mandatory_locking_blocks_all_processes_comment(self):
        """Test that comments explain mandatory locking blocks all processes."""
        # Read the storage.py file
        storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
        with open(storage_path, 'r') as f:
            content = f.read()

        # Verify documentation mentions that mandatory locks enforce mutual exclusion
        assert "enforce mutual exclusion" in content.lower() or "blocks ALL processes" in content or (
            "enforces mutual exclusion on ALL processes" in content
        ), (
            "storage.py should document that mandatory locking enforces mutual "
            "exclusion on ALL processes, including malicious or unaware ones. "
            "This is the key advantage over advisory locks."
        )
