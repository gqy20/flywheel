"""Tests for Issue #105 - _save_with_todos 逻辑错误"""

import tempfile
import os
from pathlib import Path

from flywheel.storage import Storage
from flywheel.todo import Todo


def test_save_with_todos_saves_correct_data():
    """测试 _save_with_todos 保存的是正确的新数据，而不是旧数据"""
    # 创建临时存储文件
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # 添加一个 todo
        todo1 = Todo(id=1, title="Task 1", status="pending")
        storage.add(todo1)

        # 修改这个 todo 并更新
        todo1_updated = Todo(id=1, title="Task 1 Updated", status="completed")
        storage.update(todo1_updated)

        # 重新加载存储，验证保存的是更新后的数据
        storage_reloaded = Storage(str(storage_path))
        reloaded_todo = storage_reloaded.get(1)

        # 验证数据是更新后的数据
        assert reloaded_todo is not None
        assert reloaded_todo.title == "Task 1 Updated", f"Expected 'Task 1 Updated', got '{reloaded_todo.title}'"
        assert reloaded_todo.status == "completed", f"Expected 'completed', got '{reloaded_todo.status}'"


def test_save_with_todos_after_multiple_operations():
    """测试多次操作后 _save_with_todos 保存的是最新数据"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # 添加多个 todos
        storage.add(Todo(id=1, title="Task 1", status="pending"))
        storage.add(Todo(id=2, title="Task 2", status="pending"))
        storage.add(Todo(id=3, title="Task 3", status="pending"))

        # 删除中间的 todo
        storage.delete(2)

        # 重新加载验证
        storage_reloaded = Storage(str(storage_path))
        todos = storage_reloaded.list()

        # 应该只有 2 个 todos（ID 1 和 3）
        assert len(todos) == 2, f"Expected 2 todos, got {len(todos)}"
        assert storage_reloaded.get(1) is not None
        assert storage_reloaded.get(2) is None  # 已删除
        assert storage_reloaded.get(3) is not None


def test_save_with_todos_consistency():
    """测试 _save_with_todos 更新 self._todos 的一致性"""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "todos.json"
        storage = Storage(str(storage_path))

        # 添加 todo
        storage.add(Todo(id=1, title="Original", status="pending"))

        # 更新 todo
        updated = Todo(id=1, title="Updated", status="completed")
        storage.update(updated)

        # 检查内存中的状态是否正确
        assert storage._todos[0].title == "Updated"
        assert storage._todos[0].status == "completed"

        # 检查文件中的数据是否与内存一致
        import json
        data = json.loads(storage_path.read_text())
        assert data["todos"][0]["title"] == "Updated"
        assert data["todos"][0]["status"] == "completed"
