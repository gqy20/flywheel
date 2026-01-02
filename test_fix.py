#!/usr/bin/env python
"""验证 Issue #456 修复"""

import sys
import tempfile
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_corrupted_json():
    """测试损坏的 JSON 文件"""
    print("测试 1: 损坏的 JSON 文件")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        # 写入无效的 JSON
        storage_path.write_text("{invalid json content")

        try:
            storage = Storage(str(storage_path))
            print(f"✓ Storage 创建成功")
            print(f"  - Todos: {storage.list()}")
            print(f"  - Next ID: {storage.get_next_id()}")

            # 验证可以添加新 todo
            todo = storage.add(Todo(title="Test task"))
            print(f"  - 添加 todo 成功: ID={todo.id}")
            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False


def test_empty_file():
    """测试空文件"""
    print("\n测试 2: 空文件")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        # 创建空文件
        storage_path.write_text("")

        try:
            storage = Storage(str(storage_path))
            print(f"✓ Storage 创建成功")
            print(f"  - Todos: {storage.list()}")
            print(f"  - Next ID: {storage.get_next_id()}")

            # 验证可以添加新 todo
            todo = storage.add(Todo(title="Test task"))
            print(f"  - 添加 todo 成功: ID={todo.id}")
            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False


def test_malformed_schema():
    """测试格式错误的数据结构"""
    print("\n测试 3: 格式错误的数据结构")
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        # 写入格式错误的数据（顶层是字符串）
        storage_path.write_text('"just a string"')

        try:
            storage = Storage(str(storage_path))
            print(f"✓ Storage 创建成功")
            print(f"  - Todos: {storage.list()}")
            print(f"  - Next ID: {storage.get_next_id()}")

            # 验证可以添加新 todo
            todo = storage.add(Todo(title="Test task"))
            print(f"  - 添加 todo 成功: ID={todo.id}")
            return True
        except Exception as e:
            print(f"✗ 失败: {e}")
            return False


if __name__ == "__main__":
    print("=" * 60)
    print("Issue #456 修复验证")
    print("=" * 60)

    results = []
    results.append(test_corrupted_json())
    results.append(test_empty_file())
    results.append(test_malformed_schema())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有测试通过!")
        sys.exit(0)
    else:
        print("✗ 部分测试失败")
        sys.exit(1)
