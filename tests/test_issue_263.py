"""Test Issue #263 - 数据完整性校验实现验证.

Issue #263 要求实现数据完整性校验，实际上该功能已经在 Issue #223 中完成。
本测试验证 Issue #263 的所有要求都已满足：
1. _load 方法中读取文件后计算校验和并与存储的元数据对比
2. _save 方法中计算并保存校验和
3. 校验失败时触发 _create_backup 并抛出异常
"""

import json
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import Storage
from flywheel.todo import Todo


class TestIssue263:
    """Verify Issue #263 requirements are met."""

    def test_load_verifies_checksum_with_metadata(self):
        """验证 _load 方法会计算校验和并与存储的元数据对比."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 创建存储并添加 todos
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            storage.add(Todo(id=2, title="Task 2", status="completed"))

            # 验证文件包含校验和
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data, "文件应包含 metadata 字段"
            assert "checksum" in data["metadata"], "metadata 应包含 checksum"

            # 验证 _load 能成功验证校验和
            storage2 = Storage(str(storage_path))
            todos = storage2.list()
            assert len(todos) == 2
            assert todos[0].title == "Task 1"
            assert todos[1].title == "Task 2"

    def test_save_calculates_and_stores_checksum(self):
        """验证 _save 方法会计算并保存校验和."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))
            todo = Todo(id=1, title="Test Task", status="pending")
            storage.add(todo)

            # 读取文件验证校验和已保存
            with storage_path.open('r') as f:
                data = json.load(f)

            assert "metadata" in data
            assert "checksum" in data["metadata"]
            assert len(data["metadata"]["checksum"]) > 0  # SHA256 哈希应该是64字符

    def test_checksum_mismatch_creates_backup_and_raises_error(self):
        """验证校验失败时会触发 _create_backup 并抛出异常."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 创建存储并保存数据
            storage = Storage(str(storage_path))
            storage.add(Todo(id=1, title="Original Task", status="pending"))
            storage.close()

            # 篡改文件内容（模拟数据损坏）
            with storage_path.open('r') as f:
                data = json.load(f)

            data["todos"][0]["title"] = "Tampered Task"

            with storage_path.open('w') as f:
                json.dump(data, f, indent=2)

            # 尝试加载 - 应该检测到校验和不匹配
            backup_path = storage_path.parent / (storage_path.name + ".backup")

            # 验证加载前备份文件不存在
            assert not backup_path.exists()

            # 加载应该抛出 RuntimeError 并创建备份
            with pytest.raises(RuntimeError) as exc_info:
                Storage(str(storage_path))

            error_msg = str(exc_info.value).lower()
            assert "checksum" in error_msg or "integrity" in error_msg

            # 验证备份文件已创建
            assert backup_path.exists(), "校验失败时应创建备份文件"

    def test_checksum_calculated_for_all_save_operations(self):
        """验证所有保存操作都会计算校验和."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            storage = Storage(str(storage_path))

            # 测试 add 操作
            storage.add(Todo(id=1, title="Task 1", status="pending"))
            with storage_path.open('r') as f:
                data = json.load(f)
            assert "checksum" in data["metadata"]

            # 测试 update 操作
            todo = storage.get(1)
            todo.status = "completed"
            storage.update(todo)
            with storage_path.open('r') as f:
                data = json.load(f)
            assert "checksum" in data["metadata"]

            # 测试 delete 操作
            storage.delete(1)
            with storage_path.open('r') as f:
                data = json.load(f)
            assert "checksum" in data["metadata"]

    def test_backward_compatibility_without_checksum(self):
        """验证向后兼容性 - 没有校验和的旧文件可以正常加载."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"

            # 创建旧格式文件（没有 metadata 和 checksum）
            old_data = [
                {"id": 1, "title": "Task 1", "status": "pending"},
                {"id": 2, "title": "Task 2", "status": "completed"}
            ]

            with storage_path.open('w') as f:
                json.dump(old_data, f, indent=2)

            # 应该能成功加载
            storage = Storage(str(storage_path))
            todos = storage.list()
            assert len(todos) == 2

            # 保存后应该包含校验和
            with storage_path.open('r') as f:
                data = json.load(f)
            assert "metadata" in data
            assert "checksum" in data["metadata"]

    def test_checksum_method_exists_and_works(self):
        """验证 _calculate_checksum 方法存在且正常工作."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "todos.json"
            storage = Storage(str(storage_path))

            todos = [
                Todo(id=1, title="Task 1", status="pending"),
                Todo(id=2, title="Task 2", status="completed")
            ]

            # 调用 _calculate_checksum 方法
            checksum = storage._calculate_checksum(todos)

            # 验证返回的是有效的 SHA256 哈希
            assert isinstance(checksum, str)
            assert len(checksum) == 64  # SHA256 哈希长度
            assert all(c in "0123456789abcdef" for c in checksum)

            # 相同的数据应该产生相同的校验和
            checksum2 = storage._calculate_checksum(todos)
            assert checksum == checksum2

            # 不同的数据应该产生不同的校验和
            todos2 = [Todo(id=1, title="Different Task", status="pending")]
            checksum3 = storage._calculate_checksum(todos2)
            assert checksum != checksum3
