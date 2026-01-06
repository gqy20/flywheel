"""
Test for Issue #874: Windows 降级模式下的锁文件清理逻辑未实现

这个测试验证在进程异常终止时，锁文件能够被正确清理。
根据 issue 描述，注释声称锁文件会在进程终止时自动清理，
但 Python 文件对象通常不会在异常崩溃时触发 __del__ 进行清理。

测试策略：
1. 模拟进程创建锁文件后异常崩溃（不调用 close()）
2. 验证新进程能够检测并清理过期的锁文件
3. 验证基于 PID 的锁文件检测机制
"""

import os
import sys
import time
import subprocess
import tempfile
import pytest
from pathlib import Path

# 添加 src 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import FileStorage
from flywheel.entities import Todo


def test_lock_file_cleanup_on_stale_lock():
    """测试过期锁文件能够被检测和清理。

    这个测试模拟以下场景：
    1. 进程 A 创建了一个锁文件
    2. 进程 A 崩溃（没有调用 close()）
    3. 进程 B 尝试获取锁，应该能检测到过期锁并清理
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.json.lock"
        data_file = Path(tmpdir) / "test.json"

        # 创建一个过期的锁文件（模拟崩溃的进程）
        # 设置一个较旧的时间戳（超过 stale_threshold）
        stale_time = time.time() - 400  # 400秒前，超过300秒的阈值
        lock_file.write_text(f"pid=99999\nlocked_at={stale_time}\n")

        # 验证锁文件存在
        assert lock_file.exists(), "锁文件应该存在"

        # 尝试创建 FileStorage 实例
        # 这应该能够检测到过期锁并清理
        storage = FileStorage(
            path=str(data_file),
            compression=False,
            backup_count=0,
            enable_cache=False,
            lock_timeout=10.0,
            lock_retry_interval=0.05
        )

        try:
            # 添加一个 todo 来触发文件操作
            storage.add(Todo(title="Test todo"))

            # 验证操作成功完成（说明锁被正确获取和释放）
            todos = storage.list_all()
            assert len(todos) == 1
            assert todos[0].title == "Test todo"

        finally:
            storage.close()


def test_lock_file_cleanup_on_abnormal_termination():
    """测试进程异常终止后锁文件能够被新进程清理。

    这个测试使用子进程模拟异常终止场景：
    1. 子进程创建锁文件并崩溃（不调用 close）
    2. 父进程创建新的 FileStorage 实例
    3. 验证新进程能够成功获取锁
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_crash.json"
        lock_file = Path(tmpdir) / "test_crash.json.lock"

        # 子进程代码：创建锁文件但不关闭
        child_code = f'''
import sys
import time
sys.path.insert(0, '{os.path.join(os.path.dirname(__file__), '..', 'src')}')

from flywheel.storage import FileStorage
from flywheel.entities import Todo

# 创建 FileStorage 实例（会获取锁）
storage = FileStorage(
    path="{str(data_file)}",
    compression=False,
    backup_count=0,
    enable_cache=False,
    lock_timeout=10.0
)

# 添加一个 todo
storage.add(Todo(title="Crash test"))

# 模拟崩溃：不调用 close()，直接退出
# 这应该导致锁文件不被清理（如果没有正确实现）
# 注意：我们使用 os._exit() 来跳过正常的清理逻辑
import os
import gc
# 删除引用但不调用 close
del storage
gc.collect()
# 使用 _exit 跳过 atexit 处理器
os._exit(0)
'''

        # 运行子进程
        result = subprocess.run(
            [sys.executable, '-c', child_code],
            capture_output=True,
            text=True,
            timeout=10
        )

        # 等待一下确保子进程完全退出
        time.sleep(0.5)

        # 验证数据文件被创建
        assert data_file.exists(), "数据文件应该被创建"

        # 验证锁文件可能存在（取决于 __del__ 是否被调用）
        # 注意：这个测试的关键是验证即使锁文件存在，
        # 新进程也能基于 PID 或时间戳判断并清理它

        # 现在尝试创建新的 FileStorage 实例
        # 如果实现了正确的过期锁检测，这应该能够成功
        storage2 = FileStorage(
            path=str(data_file),
            compression=False,
            backup_count=0,
            enable_cache=False,
            lock_timeout=10.0
        )

        try:
            # 尝试添加另一个 todo
            storage2.add(Todo(title="Recovery test"))

            # 验证操作成功
            todos = storage2.list_all()
            assert len(todos) >= 1, "应该能够读取到数据"

        finally:
            storage2.close()


def test_lock_file_pid_validation():
    """测试基于 PID 的锁文件验证。

    验证锁文件包含正确的 PID 信息，
    并且能够用于检测进程是否还存在。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_pid.json"
        lock_file = Path(tmpdir) / "test_pid.json.lock"

        storage = FileStorage(
            path=str(data_file),
            compression=False,
            backup_count=0,
            enable_cache=False,
            lock_timeout=10.0
        )

        try:
            # 触发文件操作以获取锁
            storage.add(Todo(title="PID test"))

            # 验证锁文件被创建
            assert lock_file.exists(), "锁文件应该被创建"

            # 读取锁文件内容
            lock_content = lock_file.read_text()
            assert "pid=" in lock_content, "锁文件应该包含 PID"
            assert "locked_at=" in lock_content, "锁文件应该包含锁定时间"

            # 验证 PID 是当前进程的 PID
            current_pid = os.getpid()
            assert f"pid={current_pid}" in lock_content, "PID 应该匹配"

        finally:
            storage.close()

            # 验证锁文件被清理
            assert not lock_file.exists(), "锁文件应该被清理"


def test_lock_file_cleanup_with_context_manager():
    """测试使用上下文管理器时锁文件能被正确清理。

    这是推荐的用法，应该始终能正确清理锁文件。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_context.json"
        lock_file = Path(tmpdir) / "test_context.json.lock"

        # 使用上下文管理器
        with FileStorage(
            path=str(data_file),
            compression=False,
            backup_count=0,
            enable_cache=False,
            lock_timeout=10.0
        ) as storage:
            storage.add(Todo(title="Context manager test"))

        # 验证锁文件被清理
        assert not lock_file.exists(), "上下文管理器退出后锁文件应该被清理"


def test_concurrent_lock_access():
    """测试并发访问时锁文件机制的正确性。

    验证同一时间只有一个进程能够持有锁。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        data_file = Path(tmpdir) / "test_concurrent.json"

        # 创建第一个 storage 实例并获取锁
        storage1 = FileStorage(
            path=str(data_file),
            compression=False,
            backup_count=0,
            enable_cache=False,
            lock_timeout=2.0,
            lock_retry_interval=0.1
        )

        try:
            storage1.add(Todo(title="First"))

            # 尝试创建第二个实例，应该等待或超时
            # 因为第一个实例持有锁
            storage2_started = time.time()

            # 这应该等待直到超时（因为我们不会释放 storage1 的锁）
            with pytest.raises(RuntimeError, match="timed out"):
                storage2 = FileStorage(
                    path=str(data_file),
                    compression=False,
                    backup_count=0,
                    enable_cache=False,
                    lock_timeout=1.0,
                    lock_retry_interval=0.1
                )
                storage2.add(Todo(title="Second"))

            # 验证确实等待了
            elapsed = time.time() - storage2_started
            assert elapsed >= 0.9, f"应该等待至少 0.9 秒，实际等待了 {elapsed:.2f} 秒"

        finally:
            storage1.close()


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
