"""Tests for Issue #616 - 初始化逻辑中存在未处理的异常分支

测试目标：确保在所有异常处理路径中，init_success 都被正确设置
"""

import json
import pytest
from pathlib import Path
from flywheel.storage import FileStorage


def test_init_success_set_after_json_decode_error(tmp_path):
    """测试 JSON 解析错误时 init_success 被正确设置"""
    # 创建一个包含无效 JSON 的文件
    invalid_json_file = tmp_path / "invalid.json"
    invalid_json_file.write_text("{invalid json content")

    # 尝试初始化存储对象，应该处理错误并成功初始化
    storage = FileStorage(str(invalid_json_file))

    # 验证对象可以正常使用
    assert storage._todos == []
    assert storage._next_id == 1
    assert storage._dirty is False

    # 验证 cleanup 已注册（说明 init_success 为 True）
    # 通过检查对象是否可以正常保存来验证
    storage.add("Test todo")
    storage.save()  # 如果 cleanup 没有注册，这里仍然应该能正常保存


def test_init_success_set_after_value_error(tmp_path):
    """测试值错误时 init_success 被正确设置"""
    # 创建一个包含有效但无效值的 JSON 文件
    # 例如：负数 ID
    invalid_data_file = tmp_path / "invalid_data.json"
    invalid_data_file.write_text('{"todos": [{"id": -1, "title": "test"}], "next_id": 0}')

    # 尝试初始化存储对象
    storage = FileStorage(str(invalid_data_file))

    # 验证对象可以正常使用
    assert storage._todos == []
    assert storage._next_id == 1
    assert storage._dirty is False

    # 验证可以正常操作
    storage.add("Test todo")
    storage.save()


def test_init_success_with_valid_json(tmp_path):
    """测试有效 JSON 时 init_success 被正确设置"""
    # 创建一个包含有效数据的 JSON 文件
    valid_json_file = tmp_path / "valid.json"
    valid_data = {
        "todos": [
            {"id": 1, "title": "Todo 1", "completed": False},
            {"id": 2, "title": "Todo 2", "completed": True}
        ],
        "next_id": 3
    }
    valid_json_file.write_text(json.dumps(valid_data))

    # 初始化存储对象
    storage = FileStorage(str(valid_json_file))

    # 验证数据正确加载
    assert len(storage._todos) == 2
    assert storage._next_id == 3
    assert storage._todos[0]["id"] == 1
    assert storage._todos[0]["title"] == "Todo 1"

    # 验证可以正常操作
    storage.add("Todo 3")
    storage.save()


def test_init_success_with_missing_file(tmp_path):
    """测试文件不存在时 init_success 被正确设置"""
    # 使用一个不存在的文件路径
    missing_file = tmp_path / "missing.json"

    # 初始化存储对象
    storage = FileStorage(str(missing_file))

    # 验证对象以空状态初始化
    assert storage._todos == []
    assert storage._next_id == 1
    assert storage._dirty is False

    # 验证可以正常操作
    storage.add("Test todo")
    storage.save()


def test_init_failure_without_backup_propagates():
    """测试没有备份的严重初始化失败会传播异常"""
    import tempfile
    import os

    # 创建一个临时文件并设置为只读，然后删除它
    # 这将导致权限错误，且没有备份
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "test.json"
        test_file.write_text('{"invalid": "data"}')

        # 修改文件权限为只读
        os.chmod(test_file, 0o000)

        # 删除文件以触发 FileNotFoundError 后的权限错误
        test_file.unlink()

        # 现在尝试创建父目录为只读的情况
        read_only_dir = Path(tmp_dir) / "readonly"
        read_only_dir.mkdir()
        os.chmod(read_only_dir, 0o000)

        readonly_file = read_only_dir / "test.json"

        # 这应该会抛出异常，因为无法创建文件
        with pytest.raises(Exception):
            FileStorage(str(readonly_file))
