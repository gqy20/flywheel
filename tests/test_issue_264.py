"""测试验证 Windows 安全代码完整性 (issue #264)

这个测试确保 Windows ACL 设置中包含 OWNER_SECURITY_INFORMATION。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# 只有在 Windows 上运行此测试
@pytest.mark.skipif(os.name != 'nt', reason="Windows-only test")
def test_windows_security_includes_owner_info():
    """测试 Windows 安全设置包含 OWNER_SECURITY_INFORMATION 标志。"""
    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_flywheel"

        # Mock win32security 模块来捕获 SetFileSecurity 调用
        mock_security = MagicMock()
        mock_con = MagicMock()

        # 创建模拟对象
        mock_security.DACL_SECURITY_INFORMATION = 1
        mock_security.PROTECTED_DACL_SECURITY_INFORMATION = 2
        mock_security.OWNER_SECURITY_INFORMATION = 4

        # 模拟 LookupAccountName 返回值
        mock_sid = MagicMock()
        mock_security.LookupAccountName.return_value = (mock_sid, None, None)
        mock_security.ACL.return_value = MagicMock()
        mock_security.SECURITY_DESCRIPTOR.return_value = MagicMock()

        # 模拟 SetFileSecurity 方法来捕获调用
        set_file_security_calls = []
        original_set_file_security = None

        def mock_set_file_security(path, security_info, security_descriptor):
            """捕获 SetFileSecurity 调用的参数"""
            set_file_security_calls.append({
                'path': path,
                'security_info': security_info,
                'security_descriptor': security_descriptor
            })

        mock_security.SetFileSecurity = mock_set_file_security
        mock_security.SetSecurityDescriptorOwner = MagicMock()
        mock_security.SetSecurityDescriptorDacl = MagicMock()
        mock_security.SetSecurityDescriptorSacl = MagicMock()
        mock_security.SetSecurityDescriptorControl = MagicMock()

        # Mock win32api
        mock_api = MagicMock()
        mock_api.GetUserName.return_value = "testuser"
        mock_api.GetComputerName.return_value = "TESTPC"

        try:
            mock_api.GetUserNameEx.side_effect = Exception("No domain")
        except:
            mock_api.GetUserNameEx = MagicMock(side_effect=Exception("No domain"))

        # 准备 mock 模块
        mock_modules = {
            'win32security': mock_security,
            'win32con': mock_con,
            'win32api': mock_api
        }

        # 导入 Storage 并使用 mock
        from flywheel import storage

        # 保存原始模块（如果已导入）
        original_modules = {}
        for mod_name in mock_modules:
            if mod_name in sys.modules:
                original_modules[mod_name] = sys.modules[mod_name]

        try:
            # 注入 mock 模块
            for mod_name, mod_obj in mock_modules.items():
                sys.modules[mod_name] = mod_obj

            # 重新导入 storage 以使用 mock
            import importlib
            importlib.reload(storage)

            # 创建 Storage 实例，这会触发 _secure_directory
            # 覆盖默认路径以使用我们的测试目录
            s = storage.Storage(str(test_dir / "todos.json"))

            # 验证 SetFileSecurity 是否被调用
            assert len(set_file_security_calls) > 0, "SetFileSecurity 应该被调用至少一次"

            # 获取最后一次调用（应该是对我们测试目录的调用）
            last_call = set_file_security_calls[-1]

            # 验证 security_info 包含 OWNER_SECURITY_INFORMATION
            security_info = last_call['security_info']

            # 检查是否包含所有必需的标志
            assert (security_info & mock_security.OWNER_SECURITY_INFORMATION) != 0, \
                "security_info 必须包含 OWNER_SECURITY_INFORMATION 标志"
            assert (security_info & mock_security.DACL_SECURITY_INFORMATION) != 0, \
                "security_info 必须包含 DACL_SECURITY_INFORMATION 标志"
            assert (security_info & mock_security.PROTECTED_DACL_SECURITY_INFORMATION) != 0, \
                "security_info 必须包含 PROTECTED_DACL_SECURITY_INFORMATION 标志"

        finally:
            # 恢复原始模块
            for mod_name in original_modules:
                sys.modules[mod_name] = original_modules[mod_name]
            importlib.reload(storage)


@pytest.mark.skipif(os.name != 'nt', reason="Windows-only test")
def test_windows_security_owner_flag_set():
    """测试验证 SetSecurityDescriptorOwner 被调用且 OWNER_SECURITY_INFORMATION 被设置。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_flywheel2"

        # Mock win32security 模块
        mock_security = MagicMock()
        mock_con = MagicMock()
        mock_api = MagicMock()

        # 设置常量
        mock_security.DACL_SECURITY_INFORMATION = 1
        mock_security.PROTECTED_DACL_SECURITY_INFORMATION = 2
        mock_security.OWNER_SECURITY_INFORMATION = 4

        mock_sid = MagicMock()
        mock_security.LookupAccountName.return_value = (mock_sid, None, None)
        mock_security.ACL.return_value = MagicMock()
        security_desc_mock = MagicMock()
        mock_security.SECURITY_DESCRIPTOR.return_value = security_desc_mock

        mock_api.GetUserName.return_value = "testuser"
        mock_api.GetComputerName.return_value = "TESTPC"
        mock_api.GetUserNameEx = MagicMock(side_effect=Exception("No domain"))

        # 追踪调用
        set_file_security_calls = []

        def mock_set_file_security(path, security_info, security_descriptor):
            set_file_security_calls.append(security_info)

        mock_security.SetFileSecurity = mock_set_file_security
        mock_security.SetSecurityDescriptorOwner = MagicMock()
        mock_security.SetSecurityDescriptorDacl = MagicMock()
        mock_security.SetSecurityDescriptorSacl = MagicMock()
        mock_security.SetSecurityDescriptorControl = MagicMock()

        mock_modules = {
            'win32security': mock_security,
            'win32con': mock_con,
            'win32api': mock_api
        }

        from flywheel import storage
        import importlib

        original_modules = {}
        for mod_name in mock_modules:
            if mod_name in sys.modules:
                original_modules[mod_name] = sys.modules[mod_name]

        try:
            for mod_name, mod_obj in mock_modules.items():
                sys.modules[mod_name] = mod_obj

            importlib.reload(storage)
            s = storage.Storage(str(test_dir / "todos.json"))

            # 验证调用了 SetFileSecurity
            assert len(set_file_security_calls) > 0

            # 获取 security_info 参数
            security_info = set_file_security_calls[-1]

            # 关键断言：必须包含 OWNER_SECURITY_INFORMATION
            expected_flags = (
                mock_security.DACL_SECURITY_INFORMATION |
                mock_security.PROTECTED_DACL_SECURITY_INFORMATION |
                mock_security.OWNER_SECURITY_INFORMATION
            )

            assert security_info == expected_flags, \
                f"security_info 应该包含 OWNER_SECURITY_INFORMATION. " \
                f"预期: {expected_flags} (二进制: {bin(expected_flags)}), " \
                f"实际: {security_info} (二进制: {bin(security_info)})"

        finally:
            for mod_name in original_modules:
                sys.modules[mod_name] = original_modules[mod_name]
            importlib.reload(storage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
