"""验证测试 - issue #164 为误报

此测试验证 src/flywheel/storage.py 文件完整性：
- _save_with_todos 方法完整
- finally 块正确闭合
- 文件语法正确
"""

import ast
import pytest
from pathlib import Path


def test_storage_file_syntax_valid():
    """验证 storage.py 文件语法正确"""
    storage_path = Path("src/flywheel/storage.py")
    assert storage_path.exists(), "storage.py 文件存在"

    # 尝试解析文件 - 如果语法错误会抛出 SyntaxError
    source = storage_path.read_text(encoding='utf-8')
    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"storage.py 存在语法错误: {e}")


def test_save_with_todos_method_complete():
    """验证 _save_with_todos 方法完整"""
    storage_path = Path("src/flywheel/storage.py")
    source = storage_path.read_text(encoding='utf-8')

    # 验证方法定义存在
    assert "def _save_with_todos(self, todos: list[Todo]) -> None:" in source

    # 验证关键代码段存在
    required_snippets = [
        "try:",                              # try 块
        "except OSError as e:",              # OSError 处理
        "if e.errno == errno.EINTR:",        # EINTR 检查
        "continue",                          # continue 语句
        "# Re-raise other OSErrors",         # 注释
        "raise",                             # raise 语句
        "os.fsync(fd)",                      # fsync 调用
        "os.close(fd)",                      # close 调用
        "fd = -1",                           # 标记关闭
        "Path(temp_path).replace(self.path)",  # 原子替换
        "except Exception:",                 # 异常处理
        "finally:",                          # finally 块
        "if fd != -1:",                      # fd 检查
        "os.close(fd)",                      # finally 中的关闭
    ]

    for snippet in required_snippets:
        assert snippet in source, f"缺少关键代码: {snippet}"


def test_finally_block_properly_closed():
    """验证 finally 块正确闭合"""
    storage_path = Path("src/flywheel/storage.py")
    source = storage_path.read_text(encoding='utf-8')

    # 解析 AST
    tree = ast.parse(source)

    # 找到 Storage 类
    storage_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Storage":
            storage_class = node
            break

    assert storage_class is not None, "找到 Storage 类"

    # 找到 _save_with_todos 方法
    save_method = None
    for item in storage_class.body:
        if isinstance(item, ast.FunctionDef) and item.name == "_save_with_todos":
            save_method = item
            break

    assert save_method is not None, "找到 _save_with_todos 方法"

    # 验证方法有 try-except-finally 结构
    has_try = False
    has_finally = False

    for node in ast.walk(save_method):
        if isinstance(node, ast.Try):
            has_try = True
            if node.finalbody:  # finally 块
                has_finally = True
            break

    assert has_try, "_save_with_todos 方法包含 try 块"
    assert has_finally, "_save_with_todos 方法的 try 块有 finally 分支"


def test_file_lines_count():
    """验证文件行数符合预期（非截断）"""
    storage_path = Path("src/flywheel/storage.py")
    source = storage_path.read_text(encoding='utf-8')
    lines = source.split('\n')

    # 文件应该至少有 300 行（实际有 390 行）
    assert len(lines) >= 300, f"文件行数过少，可能被截断: {len(lines)} 行"

    # 最后一行不应该是不完整的代码
    last_line = lines[-1].strip()
    # 文件应该以空行或完整的代码结束，不应该是截断的语句
    if last_line:
        # 检查最后几行是否包含不完整的代码
        assert not last_line.endswith(','), "最后一行是不完整的元组/列表"
        assert not last_line.endswith('('), "最后一行是不完整的函数调用"


def test_specific_line_244():
    """验证 issue 提到的第 244 行完整"""
    storage_path = Path("src/flywheel/storage.py")
    source = storage_path.read_text(encoding='utf-8')
    lines = source.split('\n')

    # 第 244 行（索引 243）
    if len(lines) > 244:
        line_244 = lines[243].strip()
        # 应该是 "continue" 或类似的完整语句
        assert line_244 in ["continue", "continue # 注释..."] or line_244.startswith(
            "continue"
        ), f"第 244 行不是完整的 continue 语句: '{line_244}'"
