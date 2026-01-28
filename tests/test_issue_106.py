"""测试 Issue #106 - 旧格式数据加载时 next_id 计算逻辑异常处理"""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage


def test_old_format_with_invalid_item_should_not_crash():
    """测试旧格式数据中包含无效项时，应该能够优雅处理并继续加载有效数据"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 写入旧格式数据，包含一个无效项（缺少必需字段）
        old_data_with_invalid_item = [
            {"id": 1, "title": "Valid Todo 1", "status": "pending"},
            {"id": 2, "title": "Valid Todo 2", "status": "completed"},
            {"id": 3, "status": "pending"},  # 无效项：缺少 title 字段
            {"invalid": "data"},  # 无效项：不是合法的 todo 结构
        ]

        storage_path.write_text(json.dumps(old_data_with_invalid_item))

        # 创建 Storage 时不应该抛出异常
        storage = Storage(str(storage_path))

        # 验证有效的 todo 被正确加载
        todos = storage.list()
        assert len(todos) == 2

        # 验证 next_id 被正确计算（应该是最大 ID + 1 = 4）
        assert storage.get_next_id() == 4


def test_old_format_with_empty_list():
    """测试旧格式数据为空列表时，应该正确初始化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 写入空的旧格式数据
        storage_path.write_text(json.dumps([]))

        # 创建 Storage 时不应该抛出异常
        storage = Storage(str(storage_path))

        # 验证初始状态
        todos = storage.list()
        assert len(todos) == 0
        assert storage.get_next_id() == 1


def test_old_format_with_all_invalid_items():
    """测试旧格式数据中所有项都无效时，应该优雅处理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 写入全部是无效项的数据
        all_invalid_data = [
            {"id": 1, "status": "pending"},  # 缺少 title
            {"title": "No ID"},  # 缺少 id
            {"invalid": "structure"},
        ]

        storage_path.write_text(json.dumps(all_invalid_data))

        # 创建 Storage 时不应该抛出异常
        storage = Storage(str(storage_path))

        # 验证初始状态（没有有效的 todo）
        todos = storage.list()
        assert len(todos) == 0
        assert storage.get_next_id() == 1


def test_old_format_with_valid_items_only():
    """测试旧格式数据中所有项都有效时，应该正确计算 next_id"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"

        # 写入全部有效的旧格式数据
        valid_data = [
            {"id": 1, "title": "Todo 1", "status": "pending"},
            {"id": 5, "title": "Todo 5", "status": "completed"},
            {"id": 3, "title": "Todo 3", "status": "pending"},
        ]

        storage_path.write_text(json.dumps(valid_data))

        # 创建 Storage
        storage = Storage(str(storage_path))

        # 验证所有 todo 被正确加载
        todos = storage.list()
        assert len(todos) == 3

        # 验证 next_id 被正确计算（应该是最大 ID 5 + 1 = 6）
        assert storage.get_next_id() == 6
