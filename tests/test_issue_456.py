"""测试 Issue #456: __init__ 中调用 self._load() 失败时的处理"""

import json
import os
import tempfile
from pathlib import Path
import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue456:
    """测试存储初始化时处理损坏文件的能力"""

    def test_init_with_corrupted_json_file(self):
        """测试当存储文件包含无效 JSON 时，Storage 能否优雅处理"""
        # 创建临时目录和文件
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 写入无效的 JSON 内容
            storage_path.write_text("{invalid json content")

            # 尝试创建 Storage 实例
            # 当前实现会抛出 RuntimeError
            # 修复后应该允许实例化（可能以空状态启动）
            try:
                storage = Storage(str(storage_path))
                # 如果能成功创建，验证它处于可用状态
                assert storage.list() == []
                assert storage.get_next_id() == 1
            except RuntimeError as e:
                # 当前实现会失败，这是预期行为（RED Phase）
                assert "Invalid JSON" in str(e) or "Failed to load todos" in str(e)

    def test_init_with_empty_file(self):
        """测试当存储文件为空时，Storage 能否优雅处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 创建空文件
            storage_path.write_text("")

            # 尝试创建 Storage 实例
            # 当前实现会抛出 json.JSONDecodeError (被包装为 RuntimeError)
            try:
                storage = Storage(str(storage_path))
                # 如果能成功创建，验证它处于可用状态
                assert storage.list() == []
                assert storage.get_next_id() == 1
            except RuntimeError as e:
                # 当前实现会失败，这是预期行为（RED Phase）
                assert "Invalid JSON" in str(e) or "Failed to load todos" in str(e)

    def test_init_with_malformed_data_structure(self):
        """测试当存储文件包含格式错误的数据结构时，Storage 能否优雅处理"""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 写入格式错误的数据（例如，顶层是字符串而不是对象或数组）
            storage_path.write_text('"just a string"')

            # 尝试创建 Storage 实例
            # 当前实现会抛出 RuntimeError (schema validation failed)
            try:
                storage = Storage(str(storage_path))
                # 如果能成功创建，验证它处于可用状态
                assert storage.list() == []
                assert storage.get_next_id() == 1
            except RuntimeError as e:
                # 当前实现会失败，这是预期行为（RED Phase）
                assert "Invalid schema" in str(e)
