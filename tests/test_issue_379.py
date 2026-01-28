"""Test Unix directory permissions不受 umask 影响 (Issue #379).

在 Unix 系统上，mkdir 的 mode 参数会受到 umask 的影响。
即使设置 mode=0o700，如果 umask 是 022，实际权限可能是 755。

这个测试验证在创建目录后，显式调用 os.chmod 确保权限为 0o700。

Ref: Issue #379
"""

import os
import tempfile
import stat
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_unix_directory_permissions_ignore_umask():
    """Test that directory permissions are set to 0o700 regardless of umask.

    On Unix systems, mkdir(mode=0o700) is affected by umask.
    For example, with umask=022, the actual permissions become 0o755.

    This test ensures that after mkdir, we explicitly call os.chmod
    to guarantee 0o700 permissions.

    Ref: Issue #379
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set a permissive umask (0o022)
        # This would normally cause mkdir(mode=0o700) to create 0o755 directories
        old_umask = os.umask(0o022)

        try:
            # Create storage in a subdirectory to trigger mkdir
            storage_path = Path(tmpdir) / "subdir" / "todos.json"

            # This will create parent directories
            # WITHOUT the fix: parent directories might have 0o755 due to umask
            # WITH the fix: _secure_directory should ensure 0o700
            storage = Storage(str(storage_path))

            # Check all parent directories have 0o700 permissions
            parent = storage_path.parent
            while parent != Path(tmpdir).parent:
                if parent.exists():
                    parent_stat = parent.stat()
                    parent_mode = stat.S_IMODE(parent_stat.st_mode)

                    # Verify the directory has exactly 0o700 permissions
                    # (rwx------ - owner only, no group/other permissions)
                    assert parent_mode == 0o700, (
                        f"Directory {parent} should have 0o700 permissions, "
                        f"but has {oct(parent_mode)}. "
                        f"This indicates umask affected mkdir and chmod was not called."
                    )

                parent = parent.parent

        finally:
            # Restore original umask
            os.umask(old_umask)


def test_unix_mkdir_with_permissive_umask():
    """Demonstrate the issue: mkdir mode parameter is affected by umask.

    This test shows the behavior BEFORE the fix:
    - mkdir(mode=0o700) with umask=0o022 creates directories with 0o755

    Ref: Issue #379
    """
    if os.name == 'nt':  # Skip on Windows
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        # Set a permissive umask
        old_umask = os.umask(0o022)

        try:
            test_dir = Path(tmpdir) / "test_dir"

            # Create directory with mode=0o700
            test_dir.mkdir(mode=0o700)

            # Check actual permissions
            test_stat = test_dir.stat()
            test_mode = stat.S_IMODE(test_stat.st_mode)

            # WITHOUT chmod: permissions will be 0o755 due to umask
            # This demonstrates the bug
            assert test_mode == 0o755, (
                f"Expected mkdir with umask 0o022 to create 0o755, got {oct(test_mode)}"
            )

            # NOW apply chmod to fix it
            test_dir.chmod(0o700)

            # Verify permissions are now correct
            test_stat_after = test_dir.stat()
            test_mode_after = stat.S_IMODE(test_stat_after.st_mode)

            assert test_mode_after == 0o700, (
                f"After chmod, expected 0o700, got {oct(test_mode_after)}"
            )

        finally:
            os.umask(old_umask)
