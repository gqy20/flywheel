"""验证 Issue #1711 实际上不存在问题。

Issue #1711 声称代码在第 241 行被截断，但实际上文件是完整的。
这个测试验证：
1. from_dict 方法能正常工作
2. due_date 验证能正确触发
3. 所有代码路径都能正常执行
"""

import pytest
from flywheel.todo import Todo, Status, Priority


def test_from_dict_with_invalid_due_date():
    """测试无效的 due_date 格式能正确抛出异常（证明代码未被截断）"""
    data = {
        "id": 1,
        "title": "Test Todo",
        "due_date": "invalid-date-format"
    }

    with pytest.raises(ValueError) as exc_info:
        Todo.from_dict(data)

    # 验证错误消息是完整的（包含 due_date 的值）
    assert "Invalid ISO 8601 date format" in str(exc_info.value)
    assert "due_date" in str(exc_info.value)
    assert "invalid-date-format" in str(exc_info.value)


def test_from_dict_complete_method():
    """测试 from_dict 方法能完整执行并返回实例"""
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "todo",
        "priority": "high",
        "due_date": "2026-01-14T10:00:00",
        "tags": ["tag1", "tag2"]
    }

    todo = Todo.from_dict(data)

    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test Description"
    assert todo.status == Status.TODO
    assert todo.priority == Priority.HIGH
    assert todo.due_date == "2026-01-14T10:00:00"
    assert todo.tags == ["tag1", "tag2"]


def test_file_syntax_is_valid():
    """验证 Python 文件语法正确，没有被截断"""
    import py_compile
    import os

    # 编译文件会检查语法
    py_compile.compile("src/flywheel/todo.py", doraise=True)

    # 验证文件可以正常导入
    from flywheel import todo
    assert hasattr(todo, 'Todo')
    assert hasattr(todo, 'from_dict')


def test_all_date_validation_errors_complete():
    """测试所有日期验证的错误消息都是完整的"""
    test_cases = [
        ("due_date", "invalid-due"),
        ("created_at", "invalid-created"),
        ("completed_at", "invalid-completed")
    ]

    for field, invalid_value in test_cases:
        data = {
            "id": 1,
            "title": "Test Todo",
            field: invalid_value
        }

        with pytest.raises(ValueError) as exc_info:
            Todo.from_dict(data)

        error_msg = str(exc_info.value)
        # 验证错误消息包含完整的引号闭合
        assert error_msg.count("'") >= 2, f"Error message for {field} appears truncated"
        assert f"Invalid ISO 8601 date format for '{field}'" in error_msg
        assert f"'{invalid_value}'" in error_msg
