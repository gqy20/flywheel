"""Regression tests for issue #4915: Final database file should have 0o600 permissions.

Issue: After os.replace() in save(), the final database file may retain
permissions from a previously existing file instead of having the secure
0o600 (rw-------) permissions set on the temp file.

Security concern:
- If a database file existed with 0o644 (world-readable), after save()
  it should become 0o600 (owner-only)
- os.replace() on some systems preserves permissions of the destination
  file if it exists, rather than inheriting from source

This test FAILS before the fix and PASSES after the fix.
"""

from __future__ import annotations

import os
import stat

from flywheel.storage import TodoStorage
from flywheel.todo import Todo


def test_final_file_permissions_after_save_new_file(tmp_path) -> None:
    """Issue #4915: Final database file should have 0o600 after save (new file)."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Save creates new file
    storage.save([Todo(id=1, text="test")])

    # Final file should have 0o600 permissions
    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)
    assert file_mode == 0o600, (
        f"Final database file has incorrect permissions: {oct(file_mode)} "
        f"(expected 0o600). File: {db}"
    )


def test_final_file_permissions_after_save_overwrite(tmp_path, monkeypatch) -> None:
    """Issue #4915: Final database file should have 0o600 after save (overwrite).

    The key scenario: if a file existed with lax permissions (e.g., 0o644),
    after save() it should be corrected to 0o600.

    This test simulates a scenario where os.replace might not propagate
    permissions correctly by having a destination file with different permissions.
    """
    import os as os_module

    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # Create initial file with lax permissions (world-readable)
    db.write_text('[]', encoding="utf-8")
    os.chmod(db, 0o644)

    # Verify initial permissions are lax
    initial_stat = db.stat()
    initial_mode = stat.S_IMODE(initial_stat.st_mode)
    assert initial_mode == 0o644, f"Setup failed: expected 0o644, got {oct(initial_mode)}"

    # Simulate os.replace that doesn't propagate permissions (edge case)
    # by patching os.replace to preserve destination permissions
    original_replace = os_module.replace
    replace_calls = []

    def patched_replace(src, dst):
        replace_calls.append((src, dst))
        # Get the destination's current permissions
        if os.path.exists(dst):
            dst_mode = stat.S_IMODE(os.stat(dst).st_mode)
            # Do the actual replace
            result = original_replace(src, dst)
            # Restore the old permissions (simulating the bug)
            os.chmod(dst, dst_mode)
            return result
        return original_replace(src, dst)

    monkeypatch.setattr(os_module, "replace", patched_replace)

    try:
        # Save should fix permissions to 0o600 despite replace behavior
        storage.save([Todo(id=1, text="test")])
    finally:
        monkeypatch.setattr(os_module, "replace", original_replace)

    # Verify our patch simulated the problematic behavior
    assert len(replace_calls) > 0, "os.replace was not called"

    # Final file should STILL have 0o600 permissions (the fix ensures this)
    final_stat = db.stat()
    final_mode = stat.S_IMODE(final_stat.st_mode)
    assert final_mode == 0o600, (
        f"Final database file did not get secure permissions after save. "
        f"Initial: 0o644, Final: {oct(final_mode)} (expected 0o600). File: {db}"
    )


def test_final_file_permissions_multiple_saves(tmp_path) -> None:
    """Issue #4915: Permissions should stay 0o600 across multiple saves."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    # First save
    storage.save([Todo(id=1, text="first")])
    mode1 = stat.S_IMODE(db.stat().st_mode)
    assert mode1 == 0o600, f"After first save: expected 0o600, got {oct(mode1)}"

    # Second save
    storage.save([Todo(id=1, text="second"), Todo(id=2, text="added")])
    mode2 = stat.S_IMODE(db.stat().st_mode)
    assert mode2 == 0o600, f"After second save: expected 0o600, got {oct(mode2)}"

    # Third save
    storage.save([Todo(id=3, text="third")])
    mode3 = stat.S_IMODE(db.stat().st_mode)
    assert mode3 == 0o600, f"After third save: expected 0o600, got {oct(mode3)}"


def test_final_file_is_not_executable(tmp_path) -> None:
    """Issue #4915: Final database file should never have execute bits."""
    db = tmp_path / "todo.json"
    storage = TodoStorage(str(db))

    storage.save([Todo(id=1, text="test")])

    file_stat = db.stat()
    file_mode = stat.S_IMODE(file_stat.st_mode)

    # Verify no execute bits are set for anyone
    assert not (file_mode & stat.S_IXUSR), f"Owner execute bit set on {db}"
    assert not (file_mode & stat.S_IXGRP), f"Group execute bit set on {db}"
    assert not (file_mode & stat.S_IXOTH), f"Other execute bit set on {db}"
