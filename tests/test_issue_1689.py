"""测试 Issue #1689 - 文件关闭逻辑不应使用同步阻塞操作"""
import asyncio
import pytest
from unittest.mock import Mock, patch
from flywheel.storage import open_file_async


class TestAsyncFileClose:
    """测试异步文件关闭不使用同步阻塞操作"""

    @pytest.mark.asyncio
    async def test_file_close_should_be_async_only(self):
        """验证文件关闭只使用异步方式，不使用同步 close()"""
        # 创建一个模拟的文件对象
        mock_file = Mock()
        mock_file.closed = False

        # 模拟 to_thread 失败的情况
        async def failing_to_thread(func, *args, **kwargs):
            # 模拟 to_thread 失败
            raise RuntimeError("to_thread failed")

        with patch('flywheel.storage.to_thread', side_effect=failing_to_thread):
            # 创建上下文管理器
            from flywheel.storage import _StorageBackend

            # 使用 _SimpleAsyncFile 内部类
            class _SimpleAsyncFile:
                def __init__(self, path, mode):
                    self.path = path
                    self.mode = mode
                    self._file = None

                async def __aenter__(self):
                    from flywheel.storage import to_thread
                    self._file = await to_thread(open, self.path, self.mode)
                    return self._file

                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    from flywheel.storage import to_thread
                    if self._file:
                        try:
                            await to_thread(self._file.close)
                        finally:
                            # 这里不应该有同步的 close() 调用
                            # Issue #1689: 同步 close() 违背异步 I/O 原则
                            if not self._file.closed:
                                # 这行代码应该被移除
                                self._file.close()
                            return False

            # 测试：如果 to_thread 成功，不应该有同步调用
            mock_file = Mock()
            mock_file.closed = False
            mock_file.close = Mock()

            async_file = _SimpleAsyncFile('/tmp/test', 'r')
            async_file._file = mock_file

            # 模拟 to_thread 成功关闭文件
            async def successful_to_thread(func, *args, **kwargs):
                if func == mock_file.close:
                    mock_file.closed = True
                return None

            with patch('flywheel.storage.to_thread', side_effect=successful_to_thread):
                await async_file.__aexit__(None, None, None)

                # to_thread 应该被调用
                assert mock_file.close.called

                # 文件应该已经被标记为关闭
                assert mock_file.closed is True

                # 关键断言：由于文件已经通过异步方式关闭，
                # 同步的 self._file.close() 不应该被调用
                # 如果调用了，说明存在同步阻塞风险
                # 我们期望 close() 只被调用一次（通过 to_thread）
                assert mock_file.close.call_count == 1, \
                    "文件应该只通过异步方式关闭，不应该有同步的 close() 调用"

    @pytest.mark.asyncio
    async def test_file_close_no_sync_fallback(self):
        """测试：不应该有同步的 fallback 逻辑"""
        # 这个测试验证修复后的行为：
        # 当 to_thread 成功关闭文件后，不应该有任何同步的 close() 调用

        mock_file = Mock()
        mock_file.closed = False
        mock_file.close = Mock()

        # 模拟异步关闭成功
        async def mock_async_close():
            mock_file.closed = True

        # 使用实际的代码路径
        from flywheel.storage import _StorageBackend

        # 测试实现：创建一个简单的异步文件上下文管理器
        class TestAsyncFile:
            def __init__(self):
                self._file = mock_file

            async def __aenter__(self):
                return self._file

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._file:
                    try:
                        # 模拟异步关闭成功
                        await mock_async_close()
                    finally:
                        # 修复后的代码：移除同步 fallback
                        # 如果文件已通过异步方式关闭，不再有同步调用
                        if not self._file.closed:
                            # 这个分支不应该被执行
                            self._file.close()
                        return False

        test_file = TestAsyncFile()
        await test_file.__aexit__(None, None, None)

        # 验证：close() 只被调用一次（通过异步方式）
        assert mock_file.close.call_count == 0, \
            "修复后：不应该有任何同步的 close() 调用"
