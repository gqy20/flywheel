"""测试 FileStorage 锁类型是否正确使用

Issue #661: FileStorage 是同步类，不应使用 asyncio.Lock
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from flywheel.storage import FileStorage
from flywheel.todo import Todo


class TestFileStorageLockType:
    """测试 FileStorage 使用正确的锁类型"""

    def test_filestorage_lock_is_threading_lock(self):
        """FileStorage 应该使用 threading.Lock，因为它是同步类"""
        storage = FileStorage()

        # 检查 _lock 是否是 threading.Lock 类型
        # 不应该是 asyncio.Lock
        assert isinstance(
            storage._lock, threading.Lock
        ), f"FileStorage._lock 应该是 threading.Lock，但实际是 {type(storage._lock)}"

    def test_filestorage_lock_not_asyncio_lock(self):
        """FileStorage 不应该使用 asyncio.Lock"""
        storage = FileStorage()

        # 确保 _lock 不是 asyncio.Lock
        import asyncio

        assert not isinstance(
            storage._lock, asyncio.Lock
        ), "FileStorage._lock 不应该是 asyncio.Lock，因为 FileStorage 是同步类"

    def test_filestorage_thread_safety(self):
        """测试 FileStorage 在多线程环境下的线程安全性

        如果使用 threading.Lock，多个线程可以安全地并发访问
        如果使用 asyncio.Lock（错误），在同步上下文中无法正常工作
        """
        storage = FileStorage()

        # 添加一个初始 todo
        todo = Todo(title="Initial Todo")
        storage.add(todo)

        results = []
        errors = []

        def add_todo(thread_id):
            """在多个线程中添加 todo"""
            try:
                for i in range(5):
                    todo = Todo(title=f"Thread-{thread_id}-Todo-{i}")
                    added = storage.add(todo)
                    results.append((thread_id, added.id))
                    time.sleep(0.001)  # 模拟一些处理时间
            except Exception as e:
                errors.append((thread_id, str(e)))

        # 使用多个线程并发添加 todos
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(add_todo, i) for i in range(5)]
            for future in futures:
                future.result()

        # 检查是否有错误
        assert len(errors) == 0, f"多线程访问时发生错误: {errors}"

        # 验证所有 todos 都被正确添加
        todos = storage.list()
        # 1 个初始 todo + 5 个线程 * 5 个 todos = 26 个 todos
        assert len(todos) == 26, f"期望 26 个 todos，实际 {len(todos)} 个"

        # 验证所有 ID 都是唯一的
        ids = [todo.id for todo in todos]
        assert len(ids) == len(set(ids)), "所有 todo ID 应该是唯一的"

    def test_filestorage_lock_context_manager(self):
        """测试锁可以作为上下文管理器使用"""
        storage = FileStorage()

        # threading.Lock 支持上下文管理器协议
        # 如果是 asyncio.Lock，在同步上下文中使用会有问题
        try:
            with storage._lock:
                # 在锁保护下执行操作
                todo = Todo(title="Test Todo")
                storage.add(todo)
            # 如果能正常执行，说明锁工作正常
            assert True
        except TypeError as e:
            pytest.fail(f"锁无法作为上下文管理器使用: {e}")
