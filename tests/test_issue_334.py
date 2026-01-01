"""测试 Issue #334: Windows 安全设置失败时可能缺少回退机制（误报验证）

这个测试验证 issue #334 是一个误报。当前实现是正确的：
- 当 Windows 安全设置失败时，程序应该抛出异常而不是回退到不安全的配置
- 这遵循"安全优先"原则，符合 Issue #304 的设计决策
- 添加回退机制会降低安全性，因此不应该实现
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from flywheel.storage import Storage


class TestIssue334FalsePositive(unittest.TestCase):
    """验证 Issue #334 是误报 - 当前实现是正确的安全设计。"""

    def setUp(self):
        """为每个测试创建临时目录。"""
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = Path(self.temp_dir) / "todos.json"

    def tearDown(self):
        """清理临时目录。"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_windows_getusername_failure_should_raise_error_not_fallback(self):
        """验证 win32api.GetUserName() 失败时抛出异常，不回退到环境变量。"""
        # Mock Windows 平台
        with patch('flywheel.storage.os.name', 'nt'):
            # Mock pywin32 模块存在
            mock_win32api = MagicMock()
            mock_win32security = MagicMock()
            mock_win32con = MagicMock()

            # GetUserName() 失败
            mock_win32api.GetUserName.side_effect = Exception("GetUserName failed")

            with patch.dict('sys.modules', {
                'win32security': mock_win32security,
                'win32con': mock_win32con,
                'win32api': mock_win32api
            }):
                # 应该抛出异常，不回退到环境变量（安全修复 Issue #329）
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息明确指出问题
                error_msg = str(context.exception).lower()
                self.assertIn("cannot set windows security", error_msg)
                self.assertIn("getusername", error_msg)
                # 验证没有提到环境变量回退
                self.assertNotIn("environment variable", error_msg)

    def test_windows_acl_failure_should_raise_error_not_fallback(self):
        """验证 Windows ACL 设置失败时抛出异常，不回退到不安全配置。"""
        # Mock Windows 平台
        with patch('flywheel.storage.os.name', 'nt'):
            # Mock pywin32 模块
            mock_win32api = MagicMock()
            mock_win32security = MagicMock()
            mock_win32con = MagicMock()

            # 让所有 API 调用成功，但 SetFileSecurity 失败
            mock_win32api.GetUserName.return_value = "testuser"
            mock_win32api.GetUserNameEx.return_value = "CN=testuser,DC=example,DC=com"
            mock_win32api.GetComputerName.return_value = "COMPUTER"

            mock_sid = MagicMock()
            mock_win32security.LookupAccountName.return_value = (mock_sid, None, None)
            mock_win32security.SetFileSecurity.side_effect = Exception("ACL setup failed")

            with patch.dict('sys.modules', {
                'win32security': mock_win32security,
                'win32con': mock_win32con,
                'win32api': mock_win32api
            }):
                # 应该抛出异常，不回退到宽松权限（Issue #304 设计决策）
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息
                error_msg = str(context.exception).lower()
                self.assertIn("failed to set windows acls", error_msg)
                self.assertIn("cannot continue", error_msg)

    def test_windows_missing_pywin32_should_raise_error_not_fallback(self):
        """验证缺少 pywin32 时抛出异常，不回退到不安全配置。"""
        # Mock Windows 平台但没有 pywin32
        with patch('flywheel.storage.os.name', 'nt'):
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name.startswith('win32'):
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)

            with patch('builtins.__import__', side_effect=mock_import):
                # 应该抛出异常，不回退到 chmod（Issue #304 设计决策）
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息提供清晰的安装指引
                error_msg = str(context.exception).lower()
                self.assertIn("pywin32 is required", error_msg)
                self.assertIn("install pywin32", error_msg)

    def test_security_first_principle_maintained(self):
        """验证"安全优先"原则得到维护。"""
        # 这个测试确保代码遵循安全优先原则：
        # 如果无法建立安全配置，程序应该拒绝运行而不是回退到不安全状态

        # Mock Windows 平台
        with patch('flywheel.storage.os.name', 'nt'):
            # Mock pywin32 但让关键操作失败
            mock_win32api = MagicMock()
            mock_win32security = MagicMock()
            mock_win32con = MagicMock()

            # 模拟各种失败场景
            failure_scenarios = [
                # GetUserName 失败
                {
                    'GetUserName': {'side_effect': Exception("Failed")},
                    'expected_error': 'getusername'
                },
                # SetFileSecurity 失败
                {
                    'GetUserName': {'return_value': "user"},
                    'GetUserNameEx': {'return_value': "CN=user,DC=local"},
                    'GetComputerName': {'return_value': "PC"},
                    'SetFileSecurity': {'side_effect': Exception("Failed")},
                    'expected_error': 'failed to set windows acls'
                },
            ]

            for scenario in failure_scenarios:
                # 重置 mocks
                mock_win32api.reset_mock()
                mock_win32security.reset_mock()

                # 配置当前场景的失败
                for method, config in scenario.items():
                    if method == 'expected_error':
                        continue
                    if hasattr(mock_win32api, method):
                        getattr(mock_win32api, method).configure(**config)
                    elif hasattr(mock_win32security, method):
                        getattr(mock_win32security, method).configure(**config)

                with patch.dict('sys.modules', {
                    'win32security': mock_win32security,
                    'win32con': mock_win32con,
                    'win32api': mock_win32api
                }):
                    # 所有失败场景都应该抛出异常
                    with self.assertRaises(RuntimeError) as context:
                        Storage(path=str(self.storage_path))

                    # 验证没有创建不安全的存储
                    self.assertFalse(self.storage_path.exists())

    def test_unix_chmod_failure_should_raise_error_not_fallback(self):
        """验证 Unix chmod 失败时抛出异常，不回退到宽松权限。"""
        # Mock Unix 平台但 chmod 失败
        with patch('flywheel.storage.os.name', 'posix'):
            with patch.object(Path, 'chmod', side_effect=OSError("Permission denied")):
                # 应该抛出异常，不回退到宽松权限
                with self.assertRaises(RuntimeError) as context:
                    Storage(path=str(self.storage_path))

                # 验证错误消息
                error_msg = str(context.exception).lower()
                self.assertIn("directory permissions", error_msg)
                self.assertIn("cannot continue", error_msg)


if __name__ == '__main__':
    unittest.main()
