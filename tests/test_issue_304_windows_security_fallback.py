"""测试 Issue #304: Windows 安全设置回退机制安全性

这个测试确保当 Windows 平台上无法设置安全权限时，
系统会抛出异常而不是继续使用不安全的默认权限。
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestWindowsSecurityFallback(unittest.TestCase):
    """测试 Windows 安全设置回退机制。"""

    def setUp(self):
        """为每个测试创建临时目录。"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "todos.json"

    def tearDown(self):
        """清理临时目录。"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @unittest.skipUnless(os.name == 'nt', "Windows only test")
    def test_windows_security_failure_should_raise_error(self):
        """测试当 win32security 设置失败时应该抛出异常。"""
        # Mock win32security 模块存在但设置失败
        with patch('flywheel.storage.os.name', 'nt'):
            with patch.dict('sys.modules', {
                'win32security': MagicMock(),
                'win32con': MagicMock(),
                'win32api': MagicMock()
            }):
                # 让 SetFileSecurity 抛出异常
                import win32security
                win32security.SetFileSecurity.side_effect = Exception("Security setup failed")

                # 尝试创建 Storage，应该抛出异常
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息
                self.assertIn("Windows security", str(context.exception).lower())
                self.assertIn("failed", str(context.exception).lower())

    def test_windows_without_pywin32_should_raise_error(self):
        """测试当 Windows 上没有 pywin32 时应该抛出异常。"""
        # Mock Windows 平台但没有 win32security
        with patch('flywheel.storage.os.name', 'nt'):
            # 让导入 win32security 失败
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name.startswith('win32'):
                    raise ImportError("No module named 'win32security'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                # 尝试创建 Storage，应该抛出异常
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息
                self.assertIn("pywin32", str(context.exception).lower())
                self.assertIn("required", str(context.exception).lower())

    def test_unix_chmod_failure_should_raise_error(self):
        """测试 Unix 平台上 chmod 失败时应该抛出异常。"""
        # Mock Unix 平台但 chmod 失败
        with patch('flywheel.storage.os.name', 'posix'):
            with patch.object(Path, 'chmod', side_effect=OSError("Permission denied")):
                # 尝试创建 Storage，应该抛出异常
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息
                self.assertIn("directory permissions", str(context.exception).lower())
                self.assertIn("failed", str(context.exception).lower())


if __name__ == '__main__':
    unittest.main()
