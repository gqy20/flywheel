"""测试用例：验证 _AsyncCompatibleLock 正确清理事件循环资源

Issue #1185: Event loop resource leak in _AsyncCompatibleLock
"""
import asyncio
import gc
import weakref

import pytest

from flywheel.storage import _AsyncCompatibleLock


def test_event_loop_cleanup_on_deletion():
    """测试 _AsyncCompatibleLock 在删除时正确清理事件循环

    当锁从同步上下文创建并使用后，应该正确关闭事件循环以避免资源泄漏。
    """
    # 创建锁的弱引用以便跟踪其生命周期
    lock = _AsyncCompatibleLock()

    # 从同步上下文使用锁（这会创建新的事件循环）
    with lock:
        pass

    # 获取事件循环引用以便后续验证
    event_loop = lock._event_loop

    # 验证事件循环存在
    assert event_loop is not None
    assert not event_loop.is_closed()

    # 删除锁对象
    del lock
    gc.collect()  # 强制垃圾回收

    # 验证事件循环已被关闭
    # 注意：如果 __del__ 方法正确实现了清理，这应该通过
    assert event_loop.is_closed(), "Event loop should be closed after lock is deleted"


def test_multiple_locks_cleanup():
    """测试多个锁实例都能正确清理各自的事件循环

    如果创建多个锁实例，每个都应该在删除时清理自己的事件循环。
    """
    loops = []

    # 创建多个锁实例
    for _ in range(3):
        lock = _AsyncCompatibleLock()
        with lock:
            pass
        loops.append(lock._event_loop)

    # 验证所有事件循环都未关闭
    for loop in loops:
        assert not loop.is_closed()

    # 删除所有锁（但保留事件循环引用）
    del lock
    gc.collect()

    # 验证所有事件循环都已被关闭
    for i, loop in enumerate(loops):
        assert loop.is_closed(), f"Event loop {i} should be closed"


def test_close_method():
    """测试 close 方法能正确清理事件循环

    应该提供一个显式的 close 方法来清理资源。
    """
    lock = _AsyncCompatibleLock()

    # 从同步上下文使用锁
    with lock:
        pass

    # 获取事件循环引用
    event_loop = lock._event_loop
    assert event_loop is not None
    assert not event_loop.is_closed()

    # 调用 close 方法
    if hasattr(lock, 'close'):
        lock.close()
        assert event_loop.is_closed(), "Event loop should be closed after calling close()"
    else:
        pytest.fail("_AsyncCompatibleLock should have a close() method")


def test_reused_lock_does_not_leak():
    """测试重复使用同一个锁不会泄漏事件循环

    如果锁被重复使用，应该重用同一个事件循环而不是创建新的。
    """
    lock = _AsyncCompatibleLock()

    # 第一次使用
    with lock:
        pass

    first_loop = lock._event_loop

    # 第二次使用
    with lock:
        pass

    second_loop = lock._event_loop

    # 应该是同一个事件循环
    assert first_loop is second_loop, "Should reuse the same event loop"

    # 清理
    del lock
    gc.collect()

    # 事件循环应该被关闭
    assert first_loop.is_closed()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
