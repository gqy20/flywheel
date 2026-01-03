"""
测试 Issue #539: Windows 降级模式安全加固

确保在没有 pywin32 时，只有在显式配置文件配置的情况下才能启用降级模式，
而不能通过环境变量绕过。
"""
import os
import sys
import pytest
from unittest.mock import patch
import importlib


class TestWindowsDegradedModeSecurity:
    """测试 Windows 降级模式的安全性"""

    def test_degraded_mode_rejected_without_debug_env(self, monkeypatch):
        """测试：在没有 FLYWHEEL_DEBUG 环境变量时，降级模式应被拒绝"""
        # 确保环境变量未设置
        monkeypatch.delenv('FLYWHEEL_DEBUG', raising=False)

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

            # 验证错误消息
            assert 'pywin32' in str(exc_info.value).lower()

    def test_degraded_mode_rejected_with_false_debug_env(self, monkeypatch):
        """测试：FLYWHEEL_DEBUG 设置为 false 时，降级模式应被拒绝"""
        # 设置环境变量为 false
        monkeypatch.setenv('FLYWHEEL_DEBUG', '0')

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
                if 'flywheel.storage' in sys.modules:
                    del sys.modules['flywheel.storage']
                import flywheel.storage

            assert 'pywin32' in str(exc_info.value).lower()

    def test_env_var_bypass_prevention(self, monkeypatch):
        """测试：防止通过环境变量绕过安全检查"""
        # 尝试各种可能的环境变量值
        test_values = ['', 'false', 'no', '0', 'off', 'disable']

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
