"""Tests to verify todo.py is complete and not truncated (Issue #1795).

This test verifies that the code reported in Issue #1795 is actually complete
and not truncated. The issue claimed that line 244 had incomplete code:
    raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_

This test confirms that the file is syntactically valid and the from_dict
method is complete with proper return statement.
"""


def test_todo_file_syntax_valid():
    """Verify that todo.py has valid Python syntax (Issue #1795)."""
    import ast
    import inspect

    from flywheel.todo import Todo

    # Parse the todo.py file to verify it's syntactically complete
    todo_path = inspect.getfile(Todo)
    with open(todo_path, 'r') as f:
        source_code = f.read()

    # Verify the file can be parsed as valid Python
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(
            f"todo.py has syntax errors at line {e.lineno}: {e.msg}\n"
            f"This confirms the file is truncated as reported in Issue #1795."
        )


def test_todo_from_dict_not_truncated():
    """Verify that from_dict method is complete and not truncated (Issue #1795)."""
    import inspect

    from flywheel.todo import Todo

    # Get the source code of the from_dict method
    from_dict_source = inspect.getsource(Todo.from_dict)

    # Verify the raise ValueError statement for due_date is complete
    # Issue #1795 claims this line was truncated at: raise ValueError(f"Invalid ISO 8601 date format for 'due_date': '{due_
    assert "raise ValueError(f\"Invalid ISO 8601 date format for 'due_date': '{due_date}'\")" in from_dict_source, (
        "from_dict method appears to be truncated. "
        "The raise ValueError statement for due_date validation is incomplete (Issue #1795)."
    )

    # Verify the from_dict method has a complete return statement
    assert 'return cls(**kwargs)' in from_dict_source, (
        "from_dict method is missing return statement. "
        "The method appears to be truncated (Issue #1795)."
    )

    # Verify the method ends with a return statement (not cut off mid-function)
    lines = from_dict_source.strip().split('\n')
    last_non_empty_line = None
    for line in reversed(lines):
        if line.strip():
            last_non_empty_line = line.strip()
            break

    assert last_non_empty_line == 'return cls(**kwargs)', (
        f"from_dict method should end with 'return cls(**kwargs)', "
        f"but ends with: {last_non_empty_line}. "
        f"Method may be truncated (Issue #1795)."
    )


def test_todo_from_dict_functionality():
    """Verify that from_dict creates complete Todo instances (Issue #1795)."""
    from flywheel.todo import Todo

    # Test creating a Todo from dict with all fields
    data = {
        "id": 1,
        "title": "Test Todo",
        "description": "Test Description",
        "status": "todo",
        "priority": "high",
        "due_date": "2026-01-15T10:30:00",
        "created_at": "2026-01-15T09:00:00",
        "completed_at": None,
        "tags": ["tag1", "tag2"]
    }

    todo = Todo.from_dict(data)

    # Verify all fields are correctly set
    assert todo.id == 1
    assert todo.title == "Test Todo"
    assert todo.description == "Test Description"
    assert todo.status.value == "todo"
    assert todo.priority.value == "high"
    assert todo.due_date == "2026-01-15T10:30:00"
    assert todo.created_at == "2026-01-15T09:00:00"
    assert todo.completed_at is None
    assert todo.tags == ["tag1", "tag2"]
