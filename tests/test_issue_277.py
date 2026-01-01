"""测试验证 Windows SACL 应用完整性 (issue #277)

这个测试确保 Windows SACL 设置被实际应用到目录，
而不仅仅是创建 SACL 对象。
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# 只有在 Windows 上运行此测试
@pytest.mark.skipif(os.name != 'nt', reason="Windows-only test")
def test_windows_sacl_is_applied():
    """测试 Windows SACL 被实际应用到目录。

    Issue #277: 代码创建了 SACL 但没有包含 SACL_SECURITY_INFORMATION 标志，
    导致 SACL 没有被实际应用到文件系统。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_flywheel"

        # Mock win32security 模块
        mock_security = MagicMock()
        mock_con = MagicMock()
        mock_api = MagicMock()

        # 设置常量
        mock_security.DACL_SECURITY_INFORMATION = 1
        mock_security.PROTECTED_DACL_SECURITY_INFORMATION = 2
        mock_security.OWNER_SECURITY_INFORMATION = 4
        mock_security.SACL_SECURITY_INFORMATION = 8

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
            assert len(set_file_security_calls) > 0, "SetFileSecurity 应该被调用"

            # 获取 security_info 参数
            security_info = set_file_security_calls[-1]

            # 关键断言：必须包含 SACL_SECURITY_INFORMATION
            # 这是 Issue #277 的核心问题 - SACL 被创建但没有被应用
            assert (security_info & mock_security.SACL_SECURITY_INFORMATION) != 0, \
                f"security_info 必须包含 SACL_SECURITY_INFORMATION 标志. " \
                f"当前 flags: {security_info} (二进制: {bin(security_info)}). " \
                f"Issue #277: SACL 被创建但没有应用到目录!"

        finally:
            for mod_name in original_modules:
                sys.modules[mod_name] = original_modules[mod_name]
            importlib.reload(storage)


@pytest.mark.skipif(os.name != 'nt', reason="Windows-only test")
def test_windows_sacl_is_created():
    """测试验证 SACL 对象确实被创建。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test_flywheel2"

        # Mock win32security 模块
        mock_security = MagicMock()
        mock_con = MagicMock()
        mock_api = MagicMock()

        mock_security.DACL_SECURITY_INFORMATION = 1
        mock_security.PROTECTED_DACL_SECURITY_INFORMATION = 2
        mock_security.OWNER_SECURITY_INFORMATION = 4
        mock_security.SACL_SECURITY_INFORMATION = 8

        mock_sid = MagicMock()
        mock_security.LookupAccountName.return_value = (mock_sid, None, None)

        # 创建不同的 ACL 对象用于 DACL 和 SACL
        dacl_mock = MagicMock()
        sacl_mock = MagicMock()
        mock_security.ACL.side_effect = [dacl_mock, sacl_mock]

        security_desc_mock = MagicMock()
        mock_security.SECURITY_DESCRIPTOR.return_value = security_desc_mock

        mock_api.GetUserName.return_value = "testuser"
        mock_api.GetComputerName.return_value = "TESTPC"
        mock_api.GetUserNameEx = MagicMock(side_effect=Exception("No domain"))

        set_file_security_calls = []
        sacl_calls = []

        def mock_set_file_security(path, security_info, security_descriptor):
            set_file_security_calls.append(security_info)

        def mock_set_security_descriptor_sacl(present, sacl, defaulted):
            sacl_calls.append({'present': present, 'sacl': sacl})

        mock_security.SetFileSecurity = mock_set_file_security
        mock_security.SetSecurityDescriptorOwner = MagicMock()
        mock_security.SetSecurityDescriptorDacl = MagicMock()
        mock_security.SetSecurityDescriptorSacl = mock_set_security_descriptor_sacl
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

            # 验证 ACL 被调用了两次 (一次 DACL，一次 SACL)
            assert mock_security.ACL.call_count == 2, \
                "ACL 应该被调用两次：一次创建 DACL，一次创建 SACL"

            # 验证 SetSecurityDescriptorSacl 被调用
            assert len(sacl_calls) > 0, "SetSecurityDescriptorSacl 应该被调用"

        finally:
            for mod_name in original_modules:
                sys.modules[mod_name] = original_modules[mod_name]
            importlib.reload(storage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
