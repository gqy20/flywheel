"""
测试 Issue #1506 - 验证 __enter__ 方法完整性

Issue #1506 报告称代码截断导致 `__enter__` 方法不完整。
这是一个误报（false positive），因为代码实际上是完整的。

测试验证：
1. __enter__ 方法包含完整的实现（不是截断的）
2. 方法包含所有必要的逻辑：锁获取、重试、返回语句
3. 方法可以正常工作

注意：此 issue 与 #1499 是相同的误报，测试已在
test_storage_enter_method_integrity_issue_1499.py 中实现。
本测试文件作为额外的验证，确认该问题已解决。
"""

import pytest
import inspect
from pathlib import Path

from flywheel.storage import FileStorage


class TestIssue1506:
    """测试 Issue #1506 - __enter__ 方法完整性（误报验证）"""

    def test_enter_method_is_complete(self):
        """验证 __enter__ 方法不是截断的，而是完整的实现"""
        storage = FileStorage()

        # 获取 __enter__ 方法的源代码
        source = inspect.getsource(storage.__enter__)

        # Issue #1506 声称代码在常量定义后就结束了
        # 我们验证代码实际上包含了完整的实现

        # 1. 验证常量存在
        assert 'MAX_RETRIES = 3' in source
        assert 'BASE_DELAY' in source
        assert 'MAX_DELAY' in source

        # 2. 验证有重试循环
        assert 'for attempt in range(MAX_RETRIES):' in source

        # 3. 验证有锁获取逻辑
        assert 'self._lock.acquire(timeout=' in source

        # 4. 验证有返回语句（这是 issue #1506 声称缺失的关键部分）
        assert 'return self' in source

        # 5. 验证有超时异常处理
        assert 'StorageTimeoutError' in source

        # 6. 验证方法有合理的长度（不是只有几行被截断的代码）
        lines = [line for line in source.split('\n') if line.strip()]
        assert len(lines) > 20, \
            f"__enter__ 方法应该有完整的实现（超过 20 行），实际只有 {len(lines)} 行"

    def test_enter_method_functional(self):
        """功能测试：验证 __enter__ 方法实际上可以工作"""
        storage = FileStorage()

        # 如果代码真的像 issue #1506 描述的那样被截断，
        # 这将导致 IndentationError 或 RuntimeError
        try:
            with storage as s:
                assert s is storage, "__enter__ 应该返回 self"
            # 如果能执行到这里，说明方法是完整的
        except (IndentationError, RuntimeError, SyntaxError) as e:
            pytest.fail(
                f"__enter__ 方法不完整或损坏（issue #1506 描述的问题）：{e}"
            )

    def test_enter_returns_self_not_none(self):
        """验证 __enter__ 返回 self 而不是 None（截断的代码会返回 None）"""
        storage = FileStorage()

        result = storage.__enter__()

        # 如果方法被截断，Python 会隐式返回 None
        assert result is storage, \
            f"__enter__ 应该返回 storage 实例，实际返回了 {type(result)}"
        assert result is not None, \
            "__enter__ 返回了 None（表明方法可能被截断或缺少 return 语句）"

        # 清理
        storage.__exit__(None, None, None)

    def test_issue_1506_is_false_positive(self):
        """明确验证 issue #1506 是误报"""
        storage = FileStorage()

        # 获取方法源代码
        source = inspect.getsource(storage.__enter__)

        # Issue #1506 声称代码看起来像这样：
        # ```python
        # def __enter__(self):
        #     import random
        #     import time
        #     MAX_RETRIES = 3
        #     BASE_DELAY = 0
        #     # （代码在这里结束）
        # ```

        # 我们验证这不是实际情况：
        issues_found = []

        if 'self._lock.acquire(' not in source:
            issues_found.append("缺少锁获取逻辑")
        if 'return self' not in source:
            issues_found.append("缺少返回语句")
        if 'StorageTimeoutError' not in source:
            issues_found.append("缺少超时处理")
        if 'for attempt in range' not in source:
            issues_found.append("缺少重试循环")

        if issues_found:
            pytest.fail(
                f"Issue #1506 似乎是真的（发现 {len(issues_found)} 个问题）："
                f"{', '.join(issues_found)}"
            )

        # 如果没有发现问题，issue #1506 确实是误报
        assert True, "Issue #1506 是误报，代码是完整的"
