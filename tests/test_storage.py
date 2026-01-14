"""Tests for Storage backend."""

import os
import tempfile

from flywheel.storage import Storage
from flywheel.todo import Status, Todo


def test_windows_acl_no_delete_permission():
    """Test that Windows ACL does not include DELETE permission (Issue #249)."""
    if os.name != 'nt':
        return  # Skip on non-Windows systems

    try:
        import win32security
        import win32con
    except ImportError:
        return  # Skip if pywin32 is not installed

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a storage instance which will apply Windows ACL
        storage = Storage(path=f"{tmpdir}/test.json")

        # Get the security descriptor of the directory
        security_descriptor = win32security.GetFileSecurity(
            tmpdir,
            win32security.DACL_SECURITY_INFORMATION
        )

        # Get the DACL
        dacl = security_descriptor.GetSecurityDescriptorDacl()

        if dacl is None:
            return  # No DACL, skip test

        # Check each ACE in the DACL
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            access_mask = ace[2]

            # Verify that DELETE permission is not granted
            # DELETE has the value 0x00010000
            assert (access_mask & win32con.DELETE) == 0, (
                f"DELETE permission found in ACE {i} with access mask {hex(access_mask)}. "
                "This violates the principle of least privilege (Issue #249)."
            )


def test_storage_add_and_get():
    """Test adding and retrieving todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todo = Todo(id=1, title="Test todo")
        storage.add(todo)

        retrieved = storage.get(1)
        assert retrieved is not None
        assert retrieved.title == "Test todo"
        assert retrieved.id == 1


def test_storage_list():
    """Test listing todos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="First", status=Status.TODO))
        storage.add(Todo(id=2, title="Second", status=Status.DONE))

        all_todos = storage.list()
        assert len(all_todos) == 2

        pending = storage.list(status="todo")
        assert len(pending) == 1
        assert pending[0].title == "First"


def test_storage_update():
    """Test updating a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        todo = Todo(id=1, title="Original", status=Status.TODO)
        storage.add(todo)

        todo.title = "Updated"
        todo.status = Status.DONE
        storage.update(todo)

        retrieved = storage.get(1)
        assert retrieved.title == "Updated"
        assert retrieved.status == Status.DONE


def test_storage_delete():
    """Test deleting a todo."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        storage.add(Todo(id=1, title="Test"))
        assert storage.get(1) is not None

        result = storage.delete(1)
        assert result is True

        assert storage.get(1) is None


def test_storage_get_next_id():
    """Test getting next available ID."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Storage(path=f"{tmpdir}/test.json")

        assert storage.get_next_id() == 1

        storage.add(Todo(id=1, title="First"))
        assert storage.get_next_id() == 2

        storage.add(Todo(id=2, title="Second"))
        assert storage.get_next_id() == 3


def test_storage_file_not_truncated():
    """Verify that storage.py is complete and not truncated (Issue #289)."""
    import ast
    import inspect

    # Parse the storage.py file to verify it's syntactically complete
    storage_path = inspect.getfile(Storage)
    with open(storage_path, 'r') as f:
        source_code = f.read()

    # Verify the file can be parsed as valid Python
    try:
        ast.parse(source_code)
    except SyntaxError as e:
        raise AssertionError(
            f"storage.py has syntax errors (file may be truncated): {e}"
        )

    # Verify the Storage class has all expected methods
    expected_methods = [
        '__init__',
        '_get_windows_lock_range',
        '_acquire_file_lock',
        '_release_file_lock',
        '_secure_directory',
        '_create_backup',
        '_cleanup',
        '_calculate_checksum',
        '_validate_storage_schema',
        '_load',
        '_save',
        '_save_with_todos',
        'add',
        'list',
        'get',
        'update',
        'delete',
        'get_next_id',
        'close',
    ]

    for method_name in expected_methods:
        assert hasattr(Storage, method_name), (
            f"Storage class is missing method '{method_name}'. "
            f"File may be truncated (Issue #289)."
        )

    # Verify the file has a reasonable length (not cut off mid-function)
    # The complete file should be around 876 lines
    line_count = len(source_code.split('\n'))
    assert line_count > 800, (
        f"storage.py appears to be truncated: only {line_count} lines. "
        f"Expected at least 800 lines (Issue #289)."
    )


def test_decorator_exception_handling_complete():
    """Verify that the decorator exception handling logic is complete (Issue #1025)."""
    import inspect

    # Get the source code of the _with_retry decorator
    storage_source = inspect.getsource(Storage._with_retry)

    # Verify that both async and sync wrappers have complete exception handling
    # Check for the presence of key exception handling components

    # 1. Verify async wrapper exists and has exception handling
    assert 'async def async_wrapper' in storage_source, (
        "Missing async_wrapper in decorator (Issue #1025)"
    )

    # 2. Verify sync wrapper exists and has exception handling
    assert 'def sync_wrapper' in storage_source, (
        "Missing sync_wrapper in decorator (Issue #1025)"
    )

    # 3. Verify both wrappers have complete exception handling blocks
    # Check for the try-except structure
    assert storage_source.count('try:') >= 2, (
        "Decorator should have try blocks for both async and sync wrappers (Issue #1025)"
    )

    assert storage_source.count('except Exception as e:') >= 2, (
        "Decorator should have exception handlers for both async and sync wrappers (Issue #1025)"
    )

    # 4. Verify the context handling logic is present in both wrappers
    assert storage_source.count('if context and not str(e).count(context) > 0:') >= 2, (
        "Missing context handling logic in decorator (Issue #1025)"
    )

    # 5. Verify add_note is used for Python 3.11+
    assert storage_source.count("if hasattr(e, 'add_note'):") >= 2, (
        "Missing add_note check for Python 3.11+ (Issue #1025)"
    )

    # 6. Verify fallback for older Python versions
    assert storage_source.count("if e.args:") >= 2, (
        "Missing fallback for older Python versions (Issue #1025)"
    )

    # 7. Verify the comment about appending context is complete
    assert '# Append context to the first argument' in storage_source, (
        "Missing or incomplete comment about context handling (Issue #1025)"
    )

    # 8. Verify both wrappers return the wrapper function
    assert 'return async_wrapper' in storage_source, (
        "Missing return statement for async_wrapper (Issue #1025)"
    )

    assert 'return sync_wrapper' in storage_source, (
        "Missing return statement for sync_wrapper (Issue #1025)"
    )


def test_async_lock_error_message_includes_both_thread_ids():
    """Verify that _AsyncCompatibleLock error message includes both thread IDs (Issue #1226)."""
    import asyncio
    import inspect
    import threading

    # Import the private _AsyncCompatibleLock class
    from flywheel.storage import _AsyncCompatibleLock

    # Get the source code of the __aenter__ method where the error is raised
    lock_source = inspect.getsource(_AsyncCompatibleLock.__aenter__)

    # Verify that the error message includes both thread IDs
    # The error message should contain:
    # 1. "Event loop thread ID:" followed by the event_loop_thread_id variable
    # 2. "current thread ID:" followed by the current_thread_id variable

    assert 'Event loop thread ID: {event_loop_thread_id}' in lock_source, (
        "Error message missing event loop thread ID (Issue #1226)"
    )

    assert 'current thread ID: {current_thread_id}' in lock_source, (
        "Error message missing current thread ID (Issue #1226)"
    )

    # Verify both variables are referenced in the f-string
    assert 'event_loop_thread_id' in lock_source, (
        "Error message should reference event_loop_thread_id variable (Issue #1226)"
    )

    assert 'current_thread_id' in lock_source, (
        "Error message should reference current_thread_id variable (Issue #1226)"
    )


def test_async_lock_sync_context_error_message_complete():
    """Verify that _AsyncCompatibleLock error message is properly terminated (Issue #1270)."""
    import inspect

    # Import the private _AsyncCompatibleLock class
    from flywheel.storage import _AsyncCompatibleLock

    # Get the source code of the __enter__ method where the error is raised
    lock_source = inspect.getsource(_AsyncCompatibleLock.__enter__)

    # Verify that the error message is complete and properly terminated
    # The error message should contain "instead" and be a complete sentence
    # Issue #1270 reported that the string was cut off at 'ins'
    assert "async with' instead" in lock_source, (
        "Error message should contain complete phrase 'async with' instead' (Issue #1270)"
    )

    # Verify the string is properly continued across lines
    assert "same event loop" in lock_source, (
        "Error message should mention 'same event loop' (Issue #1270)"
    )

    # Verify the message explains the consequence
    assert "potential deadlocks" in lock_source, (
        "Error message should explain potential deadlocks (Issue #1270)"
    )

    # Make sure we don't have the truncated version
    assert "async with' ins" not in lock_source or "async with' instead" in lock_source, (
        "Error message should not be truncated at 'ins' (Issue #1270)"
    )


def test_storage_context_no_mutation():
    """Verify that set_storage_context creates new dict instead of mutating (Issue #1634)."""
    import inspect

    # Get the source code of set_storage_context function
    from flywheel.storage import set_storage_context
    context_source = inspect.getsource(set_storage_context)

    # The current implementation has a race condition:
    # current_context = _storage_context.get({})
    # current_context.update(kwargs)
    # _storage_context.set(current_context)
    #
    # This mutates the original dict, which can cause race conditions in async contexts.
    # The safe approach is to create a new dict:
    # _storage_context.set({**_storage_context.get({}), **kwargs})

    # Check for the unsafe pattern: .update() followed by .set()
    has_update_pattern = (
        '.update(' in context_source and
        '_storage_context.set(current_context)' in context_source
    )

    # Check for the safe pattern: dictionary unpacking
    has_safe_pattern = (
        '{**' in context_source or
        'dict(' in context_source
    )

    # The test should fail if the unsafe pattern is present without safe pattern
    assert has_safe_pattern or not has_update_pattern, (
        "set_storage_context has race condition: it mutates the dictionary directly "
        "instead of creating a new one. Use: "
        "_storage_context.set({**_storage_context.get({}), **kwargs}) "
        "(Issue #1634)"
    )


def test_jsonformatter_has_make_serializable():
    """Test that JSONFormatter has _make_serializable method (Issue #1735 is false positive)."""
    import logging
    from flywheel.storage import JSONFormatter

    # Verify the method exists
    formatter = JSONFormatter()
    assert hasattr(formatter, '_make_serializable'), (
        "JSONFormatter should have _make_serializable method. "
        "Issue #1735 is a false positive - the method exists."
    )

    # Test that the method works correctly
    # Test with non-serializable object
    class CustomClass:
        def __str__(self):
            return "CustomClass instance"

    log_data = {
        'string': 'test',
        'number': 42,
        'custom': CustomClass(),
        'nested': {
            'lambda_func': lambda x: x,
            'list_with_custom': [1, CustomClass(), 'string']
        }
    }

    result = formatter._make_serializable(log_data)

    # Verify the result is JSON-serializable
    import json
    json_output = json.dumps(result)

    # Verify the conversion happened
    assert 'string' in result
    assert result['string'] == 'test'
    assert result['number'] == 42
    # Non-serializable objects should be converted to strings
    assert isinstance(result['custom'], str)
    assert 'CustomClass' in result['custom']
    # Nested structures should be processed
    assert 'nested' in result
    assert isinstance(result['nested'], dict)
    assert 'lambda_func' in result['nested']
    # Lambda should be converted to string
    assert isinstance(result['nested']['lambda_func'], str)


def test_jsonformatter_redact_sensitive_fields_has_return_value():
    """Test that _redact_sensitive_fields returns a value (Issue #1719).

    This test verifies that the _redact_sensitive_fields method correctly
    returns a dictionary with sensitive fields redacted, proving that
    Issue #1719 (which claimed the method was missing a return statement)
    is a false positive.
    """
    from flywheel.storage import JSONFormatter

    formatter = JSONFormatter()

    # Test basic sensitive field redaction
    log_data = {
        'message': 'Test log',
        'password': 'secret123',
        'api_key': 'key_abc',
        'normal_field': 'value'
    }

    result = formatter._redact_sensitive_fields(log_data)

    # Verify the method returns a dictionary
    assert isinstance(result, dict), "Method should return a dictionary"

    # Verify sensitive fields are redacted
    assert result['password'] == '***REDACTED***', "Password should be redacted"
    assert result['api_key'] == '***REDACTED***', "API key should be redacted"

    # Verify normal fields are preserved
    assert result['message'] == 'Test log', "Normal fields should be preserved"
    assert result['normal_field'] == 'value', "Normal fields should be preserved"

    # Test nested structure redaction
    nested_data = {
        'user': {
            'name': 'John',
            'password': 'nested_secret'
        },
        'tokens': ['token1', 'token2']
    }

    result = formatter._redact_sensitive_fields(nested_data)

    # Verify nested sensitive fields are redacted
    assert result['user']['password'] == '***REDACTED***', "Nested password should be redacted"
    assert result['user']['name'] == 'John', "Nested normal fields should be preserved"

    # Test case-insensitive matching
    case_data = {
        'Password': 'uppercase_secret',
        'API_KEY': 'uppercase_key',
        'PasSwOrD': 'mixed_case_secret'
    }

    result = formatter._redact_sensitive_fields(case_data)

    # Verify case-insensitive redaction works
    assert result['Password'] == '***REDACTED***', "Uppercase Password should be redacted"
    assert result['API_KEY'] == '***REDACTED***', "Uppercase API_KEY should be redacted"
    assert result['PasSwOrD'] == '***REDACTED***', "Mixed case PasSwOrD should be redacted"
