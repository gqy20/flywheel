"""
测试用例：Windows 降级模式下的文件锁原子性和死锁防护 (Issue #886)

这个测试验证在 Windows 降级模式（没有 pywin32）下，文件锁机制是否：
1. 原子性：使用文件锁(.lock)时，创建操作是原子的
2. 死锁防护：能正确检测和清理过期的锁文件
3. 并发安全：多个进程/线程竞争时只有一个能获得锁
4. PID 检测：能通过 PID 检测进程是否存活
"""
import os
import sys
import time
import tempfile
import multiprocessing
from pathlib import Path
import pytest

# 添加 src 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from flywheel.storage import FileStorage


class TestWindowsDegradedModeLocking:
    """测试 Windows 降级模式下的文件锁机制"""

    def test_fallback_lock_creates_lock_file(self):
        """测试降级模式是否创建 .lock 文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.json"

            # 创建 FileStorage 实例
            storage = FileStorage(str(test_file))

            # 尝试获取文件锁
            with open(test_file, 'w') as f:
                storage._acquire_file_lock(f)

                # 检查是否创建了 .lock 文件
                lock_file = Path(str(test_file) + ".lock")
                assert lock_file.exists(), "降级模式应该创建 .lock 文件"

                # 验证锁文件内容包含 PID 和时间戳
                with open(lock_file, 'r') as lock_f:
                    content = lock_f.read()
                    assert "pid=" in content, "锁文件应包含 PID"
                    assert "locked_at=" in content, "锁文件应包含锁定时间"

                storage._release_file_lock(f)

            # 验证锁文件被释放
            assert not lock_file.exists(), "释放锁后应删除 .lock 文件"

    def test_fallback_lock_prevents_concurrent_access(self):
        """测试降级模式是否能防止并发访问"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_concurrent.json"

            storage1 = FileStorage(str(test_file), lock_timeout=2.0)
            storage2 = FileStorage(str(test_file), lock_timeout=2.0)

            lock_acquired = [False, False]

            def process1():
                with open(test_file, 'w') as f:
                    storage1._acquire_file_lock(f)
                    lock_acquired[0] = True
                    time.sleep(0.5)  # 持有锁 0.5 秒
                    storage1._release_file_lock(f)

            def process2():
                time.sleep(0.1)  # 稍晚启动
                with open(test_file, 'w') as f:
                    try:
                        storage2._acquire_file_lock(f)
                        lock_acquired[1] = True
                        storage2._release_file_lock(f)
                    except RuntimeError as e:
                        # 预期可能会超时
                        if "timed out" in str(e):
                            lock_acquired[1] = False
                        else:
                            raise

            # 使用进程模拟并发
            p1 = multiprocessing.Process(target=process1)
            p2 = multiprocessing.Process(target=process2)

            p1.start()
            p2.start()

            p1.join()
            p2.join()

            # 至少有一个进程成功获取锁
            assert lock_acquired[0] or lock_acquired[1], "至少应有一个进程成功获取锁"

    def test_fallback_lock_stale_detection_by_pid(self):
        """测试降级模式是否能通过 PID 检测过期锁"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_stale.json"

            # 手动创建一个伪造的锁文件，使用不存在的 PID
            lock_file = Path(str(test_file) + ".lock")
            fake_pid = 99999  # 假设这个 PID 不存在

            with open(lock_file, 'w') as f:
                f.write(f"pid={fake_pid}\n")
                f.write(f"locked_at={time.time()}\n")

            # 创建新的 FileStorage 实例，应该能检测到过期锁
            storage = FileStorage(str(test_file), lock_timeout=2.0)

            start_time = time.time()
            with open(test_file, 'w') as f:
                # 应该能够获取锁（因为伪造的进程不存在）
                storage._acquire_file_lock(f)
                elapsed = time.time() - start_time
                storage._release_file_lock(f)

            # 应该快速获取锁，不会等待超时
            assert elapsed < 1.0, f"使用不存在的 PID 应该快速获取锁，实际耗时 {elapsed:.2f}s"

    def test_fallback_lock_stale_detection_by_time(self):
        """测试降级模式是否能通过时间检测过期锁（无 PID 信息）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_time_stale.json"

            # 手动创建一个没有 PID 信息的过期锁文件
            lock_file = Path(str(test_file) + ".lock")
            old_time = time.time() - 400  # 400 秒前（超过 300 秒阈值）

            with open(lock_file, 'w') as f:
                # 只写时间，不写 PID
                f.write(f"locked_at={old_time}\n")

            # 创建新的 FileStorage 实例，应该能检测到过期锁
            storage = FileStorage(str(test_file), lock_timeout=2.0)

            start_time = time.time()
            with open(test_file, 'w') as f:
                # 应该能够获取锁（因为锁已过期）
                storage._acquire_file_lock(f)
                elapsed = time.time() - start_time
                storage._release_file_lock(f)

            # 应该快速获取锁
            assert elapsed < 1.0, f"过期的锁应该被快速清理，实际耗时 {elapsed:.2f}s"

    def test_fallback_lock_timeout(self):
        """测试降级模式下的超时机制"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_timeout.json"

            storage1 = FileStorage(str(test_file), lock_timeout=1.0)
            storage2 = FileStorage(str(test_file), lock_timeout=1.0)

            def hold_lock():
                with open(test_file, 'w') as f:
                    storage1._acquire_file_lock(f)
                    time.sleep(2.0)  # 持有锁超过 storage2 的超时时间
                    storage1._release_file_lock(f)

            # 启动第一个进程持有锁
            p1 = multiprocessing.Process(target=hold_lock)
            p1.start()

            time.sleep(0.1)  # 等待第一个进程获取锁

            # 第二个进程尝试获取锁，应该超时
            with pytest.raises(RuntimeError, match="timed out"):
                with open(test_file, 'w') as f:
                    storage2._acquire_file_lock(f)

            p1.join()

    def test_fallback_lock_toctou_race_condition(self):
        """测试降级模式下删除过期锁时的 TOCTOU 竞态条件 (Issue #886)

        这个测试验证在检测和删除过期锁文件时是否存在竞态条件：
        - 多个进程同时检测到锁过期
        - 多个进程同时尝试删除锁文件
        - 应该只有一个进程能成功获取锁
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_race.json"

            # 手动创建一个使用不存在 PID 的过期锁文件
            lock_file = Path(str(test_file) + ".lock")
            fake_pid = 99999  # 假设这个 PID 不存在

            with open(lock_file, 'w') as f:
                f.write(f"pid={fake_pid}\n")
                f.write(f"locked_at={time.time()}\n")

            results = []

            def try_acquire_lock(process_id):
                """多个进程尝试同时获取锁"""
                storage = FileStorage(str(test_file), lock_timeout=2.0)
                try:
                    with open(test_file, 'w') as f:
                        storage._acquire_file_lock(f)
                        # 成功获取锁
                        results.append(process_id)
                        time.sleep(0.2)  # 持有锁一小段时间
                        storage._release_file_lock(f)
                except Exception as e:
                    # 获取锁失败
                    results.append(f"Process {process_id} failed: {e}")

            # 启动多个进程同时尝试获取同一个过期锁
            processes = []
            for i in range(3):
                p = multiprocessing.Process(target=try_acquire_lock, args=(i,))
                processes.append(p)
                p.start()

            # 等待所有进程完成
            for p in processes:
                p.join()

            # 分析结果：应该只有一个进程成功获取锁
            # 如果存在竞态条件，可能有多个进程都认为获取了锁
            successful_processes = [r for r in results if isinstance(r, int)]

            # 验证原子性：只有一个进程应该成功获取锁
            assert len(successful_processes) == 1, (
                f"原子性 violation: 预期只有 1 个进程获取锁，"
                f"但有 {len(successful_processes)} 个进程成功: {successful_processes}. "
                "这表明存在 TOCTOU 竞态条件。"
            )
