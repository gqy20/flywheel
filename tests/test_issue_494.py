"""测试 Issue #494 - Windows 安全模块导入检查逻辑漏洞

测试目标：验证当 pywin32 未安装时，模块顶部不应直接导入 win32file，
而应在 __init__ 中提供清晰的错误信息。
"""

import os
import sys
import pytest
from unittest.mock import patch


class TestWindowsImportHandling:
    """测试 Windows 模块导入处理逻辑"""

    def test_windows_modules_imported_conditionally(self):
        """测试 Windows 模块应该有条件导入

        如果在非 Windows 平台，不应该导入 win32file 等模块。
        这个测试验证模块导入的条件性。
        """
        # 如果是 Windows 平台，跳过此测试
        if os.name == 'nt':
            pytest.skip("This test is for non-Windows platforms")

        # 在非 Windows 平台上，win32file 等模块不应该被导入
        # 如果被导入，说明导入逻辑有问题
        import flywheel.storage as storage_module

        # 检查模块中不应该有 win32file 相关的导入
        # 如果模块级别的导入是有条件的，非 Windows 平台不应该有这些模块
        assert not hasattr(storage_module, 'win32file'), \
            "win32file should not be imported on non-Windows platforms"

    def test_windows_import_error_handling(self):
        """测试 Windows 上 pywin32 缺失时的错误处理

        Issue #494: 如果 pywin32 未安装，__init__ 应该提供清晰的错误信息，
        而不是在模块顶部就因为导入 win32file 而崩溃。
        """
        # 只在 Windows 平台运行此测试
        if os.name != 'nt':
            pytest.skip("This test is for Windows platforms only")

        # 模拟 win32file 不存在的情况
        # 我们需要在导入模块之前模拟，所以需要重新加载模块
        import importlib

        # 保存原始的 import hook
        original_import = __builtins__.__import__

        def mock_import(name, *args, **kwargs):
            """模拟导入，当尝试导入 win32file 时抛出 ImportError"""
            if name in ['win32file', 'pywintypes', 'win32con', 'win32security', 'win32api']:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        try:
            # 临时替换 import hook
            with patch('builtins.__import__', side_effect=mock_import):
                # 尝试导入模块
                # 如果模块顶部有 win32file 的全局导入，这里会失败
                # 这是 Issue #494 的核心问题
                try:
                    # 需要先移除已加载的模块（如果存在）
                    if 'flywheel.storage' in sys.modules:
                        del sys.modules['flywheel.storage']

                    # 重新尝试导入
                    import flywheel.storage
                    # 如果导入成功，说明模块顶部的 win32file 导入是有条件的
                    # 这是正确的行为
                    assert True, "Module imported successfully with conditional imports"

                except ImportError as e:
                    # 如果在导入时就失败，说明模块顶部有 win32file 的全局导入
                    # 这是 Issue #494 描述的问题
                    pytest.fail(
                        f"Module-level import failed: {e}. "
                        f"This indicates win32file is imported at module level "
                        f"instead of being conditionally imported. "
                        f"Issue #494: Module should defer Windows imports to __init__ "
                        f"for proper error handling."
                    )
        finally:
            # 恢复原始的 import
            __builtins__.__import__ = original_import

    def test_storage_init_without_pywin32_windows(self):
        """测试在 Windows 上没有 pywin32 时创建 Storage 的错误信息

        Issue #494: 即使模块可以导入（使用条件导入），
        创建 Storage 实例时也应该提供清晰的错误信息。
        """
        # 只在 Windows 平台运行
        if os.name != 'nt':
            pytest.skip("This test is for Windows platforms only")

        # 模拟 pywin32 缺失
        with patch.dict('sys.modules', {
            'win32file': None,
            'pywintypes': None,
            'win32con': None,
            'win32security': None,
            'win32api': None,
        }):
            # 尝试创建 Storage 实例
            with pytest.raises(ImportError) as exc_info:
                from flywheel.storage import Storage
                Storage()

            # 验证错误信息包含有用的提示
            error_message = str(exc_info.value)
            assert 'pywin32' in error_message, \
                "Error message should mention pywin32"
            assert 'pip install' in error_message.lower(), \
                "Error message should include installation instructions"

    def test_storage_init_without_pywin32_non_windows(self):
        """测试在非 Windows 平台上不需要 pywin32

        在非 Windows 平台上，Storage 应该能够正常工作，
        不需要 pywin32。
        """
        # 只在非 Windows 平台运行
        if os.name == 'nt':
            pytest.skip("This test is for non-Windows platforms only")

        # 在非 Windows 平台上，Storage 应该能够正常创建
        from flywheel.storage import Storage
        import tempfile

        # 使用临时路径
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = os.path.join(tmpdir, 'todos.json')
            storage = Storage(storage_path)
            assert storage is not None
            storage.close()
