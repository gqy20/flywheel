"""测试批量操作接口 (Issue #658)."""

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestBatchOperations:
    """测试批量添加和更新功能."""

    def test_add_batch_method_exists(self):
        """测试 add_batch 方法是否存在."""
        storage = FileStorage(":memory:")
        # 测试方法存在
        assert hasattr(storage, 'add_batch')

    def test_add_batch_single_todo(self):
        """测试批量添加单个 Todo."""
        storage = FileStorage(":memory:")
        todos = [Todo(title="Task 1")]
        result = storage.add_batch(todos)
        assert len(result) == 1
        assert result[0].title == "Task 1"
        assert result[0].id is not None

    def test_add_batch_multiple_todos(self):
        """测试批量添加多个 Todos."""
        storage = FileStorage(":memory:")
        todos = [
            Todo(title="Task 1"),
            Todo(title="Task 2"),
            Todo(title="Task 3")
        ]
        result = storage.add_batch(todos)
        assert len(result) == 3
        assert result[0].title == "Task 1"
        assert result[1].title == "Task 2"
        assert result[2].title == "Task 3"
        # 验证 IDs 连续
        assert result[0].id + 1 == result[1].id
        assert result[1].id + 1 == result[2].id

    def test_add_batch_with_existing_ids(self):
        """测试批量添加带指定 ID 的 Todos."""
        storage = FileStorage(":memory:")
        todos = [
            Todo(id=10, title="Task 1"),
            Todo(id=20, title="Task 2")
        ]
        result = storage.add_batch(todos)
        assert len(result) == 2
        assert result[0].id == 10
        assert result[1].id == 20

    def test_add_batch_empty_list(self):
        """测试批量添加空列表."""
        storage = FileStorage(":memory:")
        result = storage.add_batch([])
        assert result == []

    def test_update_batch_method_exists(self):
        """测试 update_batch 方法是否存在."""
        storage = FileStorage(":memory:")
        assert hasattr(storage, 'update_batch')

    def test_update_batch_existing_todos(self):
        """测试批量更新存在的 Todos."""
        storage = FileStorage(":memory:")
        # 先添加几个 todos
        todos = [
            Todo(title="Task 1"),
            Todo(title="Task 2"),
            Todo(title="Task 3")
        ]
        added = storage.add_batch(todos)

        # 批量更新状态
        updated_todos = [
            Todo(id=added[0].id, title="Updated Task 1", status="completed"),
            Todo(id=added[1].id, title="Updated Task 2", status="completed"),
            Todo(id=added[2].id, title="Updated Task 3", status="pending")
        ]
        result = storage.update_batch(updated_todos)

        assert len(result) == 3
        assert result[0].title == "Updated Task 1"
        assert result[0].status == "completed"
        assert result[1].title == "Updated Task 2"
        assert result[1].status == "completed"
        assert result[2].title == "Updated Task 3"
        assert result[2].status == "pending"

    def test_update_batch_partial_nonexistent(self):
        """测试批量更新包含不存在的 Todos."""
        storage = FileStorage(":memory:")
        # 添加一个 todo
        todos = [Todo(title="Task 1")]
        added = storage.add_batch(todos)

        # 尝试更新存在的和不存在的
        updated_todos = [
            Todo(id=added[0].id, title="Updated Task 1"),
            Todo(id=9999, title="Non-existent")
        ]
        result = storage.update_batch(updated_todos)

        # 应该只返回成功更新的
        assert len(result) == 1
        assert result[0].id == added[0].id
        assert result[0].title == "Updated Task 1"

    def test_update_batch_empty_list(self):
        """测试批量更新空列表."""
        storage = FileStorage(":memory:")
        result = storage.update_batch([])
        assert result == []

    def test_batch_performance(self):
        """测试批量操作的性能优势."""
        import tempfile
        import os

        # 创建临时文件用于测试
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_perf.json")

            # 测试单个添加
            storage1 = FileStorage(file_path)
            import time
            start = time.perf_counter()
            for i in range(100):
                storage1.add(Todo(title=f"Task {i}"))
            single_time = time.perf_counter() - start

            # 测试批量添加
            storage2 = FileStorage(file_path)
            start = time.perf_counter()
            todos = [Todo(title=f"Task {i}") for i in range(100)]
            storage2.add_batch(todos)
            batch_time = time.perf_counter() - start

            # 批量操作应该更快（至少不慢于单个操作）
            # 允许一定的误差，但批量操作应该有性能优势
            assert batch_time <= single_time * 1.5, f"批量操作 ({batch_time:.4f}s) 应该比单个操作 ({single_time:.4f}s) 更快或相当"
