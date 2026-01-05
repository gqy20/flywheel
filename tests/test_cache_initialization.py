"""测试缓存初始化功能 (Issue #742).

这个测试验证缓存应该在 _load 后立即可用，而不是等到第一次访问时才重建。
"""

import os
import tempfile
from pathlib import Path

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


def test_cache_initialized_after_load():
    """测试缓存应该在 _load 后立即初始化.

    当启用缓存时，_load 方法应该在加载数据后立即更新缓存，
    这样第一次 get() 操作就能从缓存中命中，而不需要重建缓存。

    Issue #742: 实现内存缓存层
    """
    # 创建临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # 创建带有初始数据的存储
        storage1 = FileStorage(
            path=str(test_file),
            enable_cache=True
        )

        # 添加一些 todos
        todo1 = storage1.add(Todo(title="Task 1", description="Description 1"))
        todo2 = storage1.add(Todo(title="Task 2", description="Description 2"))
        todo3 = storage1.add(Todo(title="Task 3", description="Description 3"))

        # 确保数据已写入磁盘
        assert storage1._cache_enabled is True
        assert storage1._cache is not None
        assert len(storage1._cache) == 3

        # 创建新的存储实例，模拟应用重启
        # 这将触发 _load_sync() 方法
        storage2 = FileStorage(
            path=str(test_file),
            enable_cache=True
        )

        # 验证缓存是否已初始化
        # 如果缓存在 _load 后立即初始化，缓存应该包含数据
        # 如果没有，缓存将为空或需要重建

        # 检查缓存状态 - 应该已经从磁盘加载数据
        assert storage2._cache_enabled is True
        assert storage2._cache is not None

        # 关键断言：缓存应该在 _load 后就包含数据
        # 而不是等到第一次访问时才重建
        # 如果缓存未初始化，这个断言会失败
        assert len(storage2._cache) == 3, (
            "缓存应该在 _load 后立即包含数据，而不是等到第一次访问时才重建。"
        )

        # 验证缓存内容正确
        assert storage2._cache[1].title == "Task 1"
        assert storage2._cache[2].title == "Task 2"
        assert storage2._cache[3].title == "Task 3"

        # 验证 get() 操作使用缓存（应该命中缓存，不需要重建）
        # 如果缓存未初始化，第一次 get 会触发缓存重建
        # 我们可以通过检查 _cache_dirty 标志来验证

        # 在第一次访问前，_cache_dirty 应该为 False（因为缓存已经在 _load 中初始化）
        assert storage2._cache_dirty is False, (
            "缓存应该在 _load 后就标记为干净，不需要重建"
        )

        # 第一次 get 操作应该直接命中缓存，不需要重建
        result = storage2.get(1)
        assert result is not None
        assert result.title == "Task 1"


def test_cache_disabled_does_not_initialize():
    """测试禁用缓存时不应该初始化缓存."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        # 创建带有初始数据的存储
        storage1 = FileStorage(
            path=str(test_file),
            enable_cache=False
        )

        # 添加一些 todos
        storage1.add(Todo(title="Task 1"))
        storage1.add(Todo(title="Task 2"))

        # 创建新的存储实例
        storage2 = FileStorage(
            path=str(test_file),
            enable_cache=False
        )

        # 验证缓存未启用
        assert storage2._cache_enabled is False

        # 验证 get() 操作仍然工作（使用线性搜索）
        result = storage2.get(1)
        assert result is not None
        assert result.title == "Task 1"


def test_cache_write_through_on_add():
    """测试 add 操作应该立即更新缓存（write-through）."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        storage = FileStorage(
            path=str(test_file),
            enable_cache=True
        )

        # 添加一个 todo
        todo = storage.add(Todo(title="New Task"))

        # 验证缓存已更新（write-through）
        assert todo.id is not None
        assert todo.id in storage._cache
        assert storage._cache[todo.id].title == "New Task"

        # 验证 _cache_dirty 为 False（因为已经更新了缓存）
        assert storage._cache_dirty is False


def test_cache_invalidation_on_update():
    """测试 update 操作应该正确更新缓存."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        storage = FileStorage(
            path=str(test_file),
            enable_cache=True
        )

        # 添加一个 todo
        todo = storage.add(Todo(title="Original Title"))

        # 更新 todo
        updated = storage.update(
            todo.id,
            title="Updated Title"
        )

        # 验证缓存已更新
        assert storage._cache[todo.id].title == "Updated Title"
        assert storage._cache_dirty is False


def test_cache_invalidation_on_delete():
    """测试 delete 操作应该从缓存中移除项目."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "todos.json"

        storage = FileStorage(
            path=str(test_file),
            enable_cache=True
        )

        # 添加一个 todo
        todo = storage.add(Todo(title="To Delete"))

        # 验证缓存中有这个项目
        assert todo.id in storage._cache

        # 删除 todo
        storage.delete(todo.id)

        # 验证缓存中已移除
        assert todo.id not in storage._cache
        assert storage._cache_dirty is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
