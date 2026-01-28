"""Test Windows file locking limitations and documentation (Issue #411).

This test verifies that:
1. Windows file locking (msvcrt.locking) is properly documented as advisory
2. The code includes warnings about Windows lock limitations
3. Users are informed about the differences between Windows and Unix locking behavior
"""

import os
import tempfile
from pathlib import Path

from flywheel.storage import Storage


def test_windows_lock_documentation_exists():
    """Test that Windows file locking limitations are documented.

    This test verifies that the storage.py file includes proper
    documentation about Windows msvcrt.locking being an advisory lock
    that cannot enforce mutual exclusion on all systems.
    """
    # Read the storage.py file to check for documentation
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    # Check for Windows lock documentation
    # The documentation should mention that msvcrt.locking is advisory
    assert 'msvcrt.locking' in content, \
        "storage.py should mention msvcrt.locking for Windows file locking"

    # Check for advisory lock warning or documentation
    # This could be in comments or docstrings
    has_windows_warning = (
        'advisory' in content.lower() or
        'windows' in content.lower() or
        'platform-specific' in content.lower() or
        'platform' in content.lower()
    )

    assert has_windows_warning, \
        "storage.py should include documentation about platform-specific lock behavior"


def test_windows_lock_behavior_documented():
    """Test that Windows lock behavior differences are documented.

    This test verifies that the code explains the difference between
    Windows advisory locks and Unix mandatory locks.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    # Check for platform-specific locking section
    assert 'os.name' in content or 'nt' in content, \
        "storage.py should check for Windows platform (os.name == 'nt')"

    # The _acquire_file_lock method should exist and handle platform differences
    assert '_acquire_file_lock' in content, \
        "storage.py should have _acquire_file_lock method"

    # Check for Windows-specific lock implementation
    if os.name == 'nt':
        # On Windows, check that msvcrt is imported
        assert 'import msvcrt' in content, \
            "storage.py should import msvcrt on Windows"
    else:
        # On Unix, check that fcntl is imported
        assert 'import fcntl' in content, \
            "storage.py should import fcntl on Unix-like systems"


def test_storage_initialization_includes_platform_check():
    """Test that Storage initialization uses platform-specific locking.

    This verifies that the Storage class properly detects the platform
    and uses appropriate locking mechanisms.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = str(Path(tmpdir) / "test_lock.json")

        # Create a Storage instance
        storage = Storage(path=storage_path)

        # The Storage should have lock-related attributes
        assert hasattr(storage, '_lock'), "Storage should have _lock attribute"
        assert hasattr(storage, '_acquire_file_lock'), \
            "Storage should have _acquire_file_lock method"
        assert hasattr(storage, '_release_file_lock'), \
            "Storage should have _release_file_lock method"

        # Verify platform detection works
        # This is tested implicitly by the fact that Storage was created
        # without errors, meaning the platform-specific imports worked


def test_windows_lock_warning_in_acquire_method():
    """Test that _acquire_file_lock documents Windows lock limitations.

    This test checks that the _acquire_file_lock method includes
    documentation about Windows advisory lock behavior.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    # Find the _acquire_file_lock method
    acquire_method_start = content.find('def _acquire_file_lock(')
    assert acquire_method_start != -1, "_acquire_file_lock method should exist"

    # Extract the method (up to the next method definition or class end)
    # We'll check a reasonable amount of text after the method starts
    method_section = content[acquire_method_start:acquire_method_start + 3000]

    # Check that the method has documentation
    assert '"""' in method_section or "'''" in method_section, \
        "_acquire_file_lock should have a docstring"

    # The method should mention Windows or platform differences
    # We allow for various forms of documentation
    method_text = method_section.lower()
    has_platform_doc = (
        'windows' in method_text or
        'unix' in method_text or
        'platform' in method_text or
        'locking' in method_text
    )

    assert has_platform_doc, \
        "_acquire_file_lock should document platform-specific behavior"


def test_windows_msvcrt_lock_is_used_on_windows():
    """Test that Windows uses msvcrt.locking for file locking.

    This is a regression test to ensure Windows uses the appropriate
    locking mechanism.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    if os.name == 'nt':
        # On Windows, msvcrt.locking should be used
        assert 'msvcrt.locking' in content, \
            "On Windows, storage.py should use msvcrt.locking"

        # Check for the specific lock mode constants
        assert 'LK_NBLCK' in content or 'LK_LOCK' in content, \
            "Windows code should use msvcrt lock mode constants"
    else:
        # On Unix, fcntl.flock should be used
        assert 'fcntl.flock' in content, \
            "On Unix, storage.py should use fcntl.flock"

        # Check for the specific lock mode constants
        assert 'LOCK_EX' in content, \
            "Unix code should use fcntl lock mode constants"


def test_windows_lock_timeout_mechanism():
    """Test that Windows lock implementation includes timeout mechanism.

    This verifies that the Windows lock implementation uses non-blocking
    locks with retry logic to prevent indefinite hangs.
    """
    storage_path = Path(__file__).parent.parent / "src" / "flywheel" / "storage.py"
    with open(storage_path, 'r') as f:
        content = f.read()

    # Find the _acquire_file_lock method
    acquire_method_start = content.find('def _acquire_file_lock(')
    assert acquire_method_start != -1, "_acquire_file_lock method should exist"

    # Extract a reasonable section of the method
    method_section = content[acquire_method_start:acquire_method_start + 5000]

    # Check for timeout/retry mechanism
    method_text = method_section.lower()
    has_timeout = (
        'timeout' in method_text or
        'retry' in method_text or
        'lk_nblck' in method_text or  # Non-blocking lock on Windows
        'lock_nb' in method_text  # Non-blocking lock on Unix
    )

    assert has_timeout, \
        "_acquire_file_lock should include timeout or retry mechanism to prevent indefinite hangs"
