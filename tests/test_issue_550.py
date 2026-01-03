"""测试 Issue #550: Windows 模块导入逻辑与 _is_degraded_mode 函数存在逻辑冲突

问题描述：
在 Windows 上，当 pywin32 导入失败时，代码会抛出 ImportError。
这导致 _is_degraded_mode() 函数永远不会被调用（因为程序已经崩溃），
使得降级模式检查逻辑完全无效。

修复方案：
移除 raise 语句，允许程序在 pywin32 缺失时进入降级模式继续运行。
"""

import os
import sys
import ast


def test_windows_import_logic_consistency():
    """
    测试 Windows 导入逻辑与 _is_degraded_mode 函数的一致性。

    通过静态分析验证：
    1. 如果代码中有 _is_degraded_mode() 的调用
    2. 那么 Windows 导入失败时不应该直接 raise ImportError
    3. 而是应该允许变量保持 None，使降级模式检查能够工作
    """
    # 读取源代码
    storage_path = os.path.join(
        os.path.dirname(__file__),
        '..',
        'src',
        'flywheel',
        'storage.py'
    )

    with open(storage_path, 'r', encoding='utf-8') as f:
        source_code = f.read()

    # 解析 AST
    tree = ast.parse(source_code)

    # 查找 Windows 导入的 try/except 块
    has_windows_import = False
    has_raise_in_import = False
    has_degraded_mode_check = False

    for node in ast.walk(tree):
        # 检查是否有 Windows 导入块
        if isinstance(node, ast.Try):
            # 检查 try 块中是否导入 win32file
            for handler in node.handlers:
                if isinstance(handler.type, ast.Name) and handler.type.id == 'ImportError':
                    # 检查 except 块是否有 raise
                    for stmt in handler.body:
                        if isinstance(stmt, ast.Raise):
                            has_raise_in_import = True
                            # 检查 raise 的消息是否与 pywin32 相关
                            if hasattr(stmt.exc, 'func') and hasattr(stmt.exc.func, 'id'):
                                if stmt.exc.func.id == 'ImportError':
                                    has_windows_import = True

        # 检查是否有 _is_degraded_mode 函数
        if isinstance(node, ast.FunctionDef) and node.name == '_is_degraded_mode':
            has_degraded_mode_check = True

    # 逻辑矛盾检查：
    # 如果存在 _is_degraded_mode 函数，说明设计上支持降级模式
    # 但是如果在导入失败时 raise ImportError，那么程序无法运行到调用 _is_degraded_mode
    # 这是一个逻辑矛盾
    if has_degraded_mode_check and has_raise_in_import:
        # 这是 Issue #550 描述的问题
        # 如果要支持降级模式，就不应该在导入失败时 raise
        # 这里我们记录问题，但在修复前测试会失败
        print(
            "\n⚠️  发现逻辑矛盾："
            "\n  - 代码中定义了 _is_degraded_mode() 函数，说明设计上支持降级模式"
            "\n  - 但在 Windows 导入 pywin32 失败时，代码会 raise ImportError"
            "\n  - 这导致 _is_degraded_mode() 永远无法被调用（程序已崩溃）"
            "\n  - 使得降级模式检查逻辑完全无效"
            "\n\n  修复建议：移除 raise 语句，允许程序在 pywin32 缺失时进入降级模式"
        )
        # 在修复前，这个测试会失败
        # 修复后，应该移除 raise，或者在失败时不抛出异常
        assert False, (
            "Issue #550: Windows 导入逻辑与 _is_degraded_mode 存在逻辑冲突。"
            "如果支持降级模式，导入失败时不应该 raise ImportError。"
        )


def test_degraded_mode_function_exists():
    """验证 _is_degraded_mode 函数存在且有正确的逻辑"""
    from flywheel.storage import _is_degraded_mode

    # 在非 Windows 系统上，应该返回 False
    if os.name != 'nt':
        assert _is_degraded_mode() is False, \
            "在非 Windows 系统上，_is_degraded_mode() 应该返回 False"

    # 验证函数可以正常调用（不抛出异常）
    try:
        result = _is_degraded_mode()
        assert isinstance(result, bool), \
            "_is_degraded_mode() 应该返回布尔值"
    except Exception as e:
        assert False, f"_is_degraded_mode() 调用失败: {e}"


if __name__ == '__main__':
    # 直接运行测试
    test_windows_import_logic_consistency()
    test_degraded_mode_function_exists()
    print("✅ 所有测试通过")
