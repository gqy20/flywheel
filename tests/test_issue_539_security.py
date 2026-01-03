"""
测试 Issue #539: Windows 降级模式已移除

确保在没有 pywin32 时，系统始终拒绝运行，不再允许任何形式的降级模式。
"""
import os
import sys
import pytest
from unittest.mock import patch
import importlib


class TestWindowsDegradedModeRemoved:
    """测试 Windows 降级模式已完全移除"""

    def test_import_fails_without_pywin32(self):
        """测试：没有 pywin32 时导入应该失败"""
        # 模拟 pywin32 不可用
        with patch.dict('sys.modules', {
            'win32security': None,
            'win32con': None,
            'win32api': None,
            'win32file': None,
            'pywintypes': None
        }):
            # 重新导入模块应抛出 ImportError
            with pytest.raises(ImportError) as exc_info:
                # 清除已导入的模块
                if 'flywheel.storage' in sys.modules:
                    del sys.modules['flywheel.storage']
                import flywheel.storage

            # 验证错误消息包含 pywin32
            assert 'pywin32' in str(exc_info.value).lower()

    def test_no_env_var_bypass(self, monkeypatch):
        """测试：即使设置了 FLYWHEEL_DEBUG，也无法绕过检查"""
        # 尝试设置调试环境变量（应该无效）
        monkeypatch.setenv('FLYWHEEL_DEBUG', '1')

        # 模拟 pywin32 不可用
        with patch.dict('sys.modules', {
            'win32security': None,
            'win32con': None,
            'win32api': None,
            'win32file': None,
            'pywintypes': None
        }):
            # 仍然应该抛出 ImportError
            with pytest.raises(ImportError) as exc_info:
                if 'flywheel.storage' in sys.modules:
                    del sys.modules['flywheel.storage']
                import flywheel.storage

            # 验证错误消息
            error_msg = str(exc_info.value).lower()
            assert 'pywin32' in error_msg
            # 确保错误消息中提到了安全性
            assert 'secure' in error_msg or 'locking' in error_msg

    def test_all_env_values_fail(self, monkeypatch):
        """测试：任何环境变量值都无法启用降级模式"""
        # 尝试各种可能的环境变量值
        test_values = ['1', 'true', 'yes', 'TRUE', 'YES']

        for value in test_values:
            monkeypatch.setenv('FLYWHEEL_DEBUG', value)

            with patch.dict('sys.modules', {
                'win32security': None,
                'win32con': None,
                'win32api': None,
                'win32file': None,
                'pywintypes': None
            }):
                # 应该抛出 ImportError
                with pytest.raises(ImportError):
                    if 'flywheel.storage' in sys.modules:
                        del sys.modules['flywheel.storage']
                    import flywheel.storage
