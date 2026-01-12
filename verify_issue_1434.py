#!/usr/bin/env python3
"""验证 Issue #1434 - 检查上下文管理器方法是否完整存在"""

import inspect
from flywheel.storage import FileStorage


def verify_methods():
    """验证所有方法都存在且完整"""
    storage = FileStorage()
    lock = storage._lock

    print("验证 Issue #1434")
    print("=" * 60)

    # 检查 __exit__ 方法
    print("\n1. 检查 __exit__ 方法:")
    assert hasattr(lock, "__exit__"), "❌ __exit__ 方法不存在"
    print("   ✓ __exit__ 方法存在")

    assert callable(lock.__exit__), "❌ __exit__ 不可调用"
    print("   ✓ __exit__ 方法可调用")

    assert lock.__exit__.__doc__, "❌ __exit__ 没有文档字符串"
    print("   ✓ __exit__ 有文档字符串")

    doc_lines = lock.__exit__.__doc__.strip().split('\n')
    assert len(doc_lines) > 5, "❌ __exit__ 文档字符串太短（可能被截断）"
    print(f"   ✓ __exit__ 文档字符串完整（{len(doc_lines)} 行）")

    # 检查 __aenter__ 方法
    print("\n2. 检查 __aenter__ 方法:")
    assert hasattr(lock, "__aenter__"), "❌ __aenter__ 方法不存在"
    print("   ✓ __aenter__ 方法存在")

    assert callable(lock.__aenter__), "❌ __aenter__ 不可调用"
    print("   ✓ __aenter__ 方法可调用")

    assert inspect.iscoroutinefunction(lock.__aenter__), "❌ __aenter__ 不是协程函数"
    print("   ✓ __aenter__ 是协程函数")

    assert lock.__aenter__.__doc__, "❌ __aenter__ 没有文档字符串"
    print("   ✓ __aenter__ 有文档字符串")

    # 检查 __aexit__ 方法
    print("\n3. 检查 __aexit__ 方法:")
    assert hasattr(lock, "__aexit__"), "❌ __aexit__ 方法不存在"
    print("   ✓ __aexit__ 方法存在")

    assert callable(lock.__aexit__), "❌ __aexit__ 不可调用"
    print("   ✓ __aexit__ 方法可调用")

    assert inspect.iscoroutinefunction(lock.__aexit__), "❌ __aexit__ 不是协程函数"
    print("   ✓ __aexit__ 是协程函数")

    assert lock.__aexit__.__doc__, "❌ __aexit__ 没有文档字符串"
    print("   ✓ __aexit__ 有文档字符串")

    # 检查源代码
    print("\n4. 检查方法实现:")
    exit_source = inspect.getsource(lock.__exit__)
    assert "return False" in exit_source, "❌ __exit__ 实现不完整"
    print("   ✓ __exit__ 实现完整（包含 return 语句）")

    aexit_source = inspect.getsource(lock.__aexit__)
    assert "return False" in aexit_source, "❌ __aexit__ 实现不完整"
    print("   ✓ __aexit__ 实现完整（包含 return 语句）")

    # 测试同步上下文管理器
    print("\n5. 测试同步上下文管理器:")
    try:
        with lock:
            pass
        print("   ✓ 同步上下文管理器工作正常")
    except Exception as e:
        print(f"   ❌ 同步上下文管理器失败: {e}")
        raise

    print("\n" + "=" * 60)
    print("✅ 所有检查通过！Issue #1434 是误报。")
    print("   所有方法都完整存在且可以正常工作。")


if __name__ == "__main__":
    verify_methods()
