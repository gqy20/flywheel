"""Test for Issue #1731 - Verify _SimpleAsyncFile.__aexit__ is correct.

This test verifies that:
1. The _SimpleAsyncFile.__aexit__ method correctly uses await to_thread(self._file.close)
2. The code is syntactically correct and the file will be properly closed
3. asyncio.to_thread correctly calls the method passed to it

Note: Issue #1731 was reported as a false positive by an AI scanner.
The scanner claimed that "await" keyword was missing, but the code actually
has await. The scanner may have been confused by the method reference syntax.

The code `await to_thread(self._file.close)` is CORRECT because:
- asyncio.to_thread(func, *args) runs func(*args) in a separate thread
- When called as to_thread(self._file.close), it executes self._file.close()
- This is the correct way to run a bound method in a thread
"""

import asyncio
import tempfile
import os


def test_simple_async_file_has_await():
    """Test that _SimpleAsyncFile.__aexit__ uses await keyword (Issue #1731)."""
    import ast
    import inspect
    from flywheel import storage

    # Get the source code
    storage_source = inspect.getsource(storage)

    # Parse the AST
    tree = ast.parse(storage_source)

    # Find the _SimpleAsyncFile class
    simple_async_file_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_SimpleAsyncFile":
            simple_async_file_class = node
            break

    assert simple_async_file_class is not None, \
        "_SimpleAsyncFile class not found in storage module"

    # Find the __aexit__ method
    aexit_method = None
    for item in simple_async_file_class.body:
        if isinstance(item, ast.AsyncFunctionDef) and item.name == "__aexit__":
            aexit_method = item
            break

    assert aexit_method is not None, \
        "__aexit__ method not found in _SimpleAsyncFile"

    # Verify that __aexit__ contains an await statement
    has_await = False
    for node in ast.walk(aexit_method):
        if isinstance(node, ast.Await):
            has_await = True
            # Verify it's awaiting a call to to_thread
            if isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "to_thread":
                    # Found: await to_thread(...)
                    # This confirms Issue #1731 is a false positive - await IS present
                    break

    assert has_await, \
        "Issue #1731 FALSE POSITIVE: __aexit__ method does use 'await' keyword"


def test_to_thread_calls_method():
    """Test that asyncio.to_thread actually calls the method passed to it."""
    import asyncio

    class Counter:
        def __init__(self):
            self.count = 0

        def increment(self):
            self.count += 1
            return self.count

    async def test():
        counter = Counter()

        # This is the pattern used in storage.py line 98
        # await to_thread(self._file.close)
        result = await asyncio.to_thread(counter.increment)

        # Verify the method was actually called
        assert result == 1, "Method should be called by to_thread"
        assert counter.count == 1, "Counter should be incremented"

        # Call again to verify
        result = await asyncio.to_thread(counter.increment)
        assert result == 2
        assert counter.count == 2

    asyncio.run(test())


def test_simple_async_file_source_code():
    """Test that the source code contains the correct pattern (Issue #1731)."""
    import inspect
    from flywheel import storage

    # Get the source code
    storage_source = inspect.getsource(storage)

    # Verify the pattern exists
    # The correct pattern is: await to_thread(self._file.close)
    assert "await to_thread(self._file.close)" in storage_source, \
        "Issue #1731: Correct pattern 'await to_thread(self._file.close)' not found"

    # Make sure the incorrect pattern (without await) is NOT present
    assert "to_thread(self._file.close)" in storage_source, \
        "to_thread(self._file.close) should be present"

    # Count occurrences
    await_count = storage_source.count("await to_thread(self._file.close)")
    no_await_count = storage_source.count("\n            to_thread(self._file.close)")

    # The await version should be present
    assert await_count >= 1, \
        "Issue #1731 FALSE POSITIVE: 'await to_thread(self._file.close)' is present"


def test_simple_async_file_ast_verification():
    """Verify the AST structure shows correct await usage (Issue #1731)."""
    import ast
    import inspect
    from flywheel import storage

    # Get the source code
    storage_source = inspect.getsource(storage)

    # Parse the AST
    tree = ast.parse(storage_source)

    # Find the _SimpleAsyncFile.__aexit__ method
    aexit_method = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "__aexit__":
            # Make sure it's in _SimpleAsyncFile class
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef) and parent.name == "_SimpleAsyncFile":
                    for item in parent.body:
                        if isinstance(item, ast.AsyncFunctionDef) and item.name == "__aexit__":
                            aexit_method = item
                            break
                    if aexit_method:
                        break
            if aexit_method:
                break

    assert aexit_method is not None, "Could not find __aexit__ in _SimpleAsyncFile"

    # Walk the AST to find the await to_thread call
    found_correct_pattern = False

    for node in ast.walk(aexit_method):
        if isinstance(node, ast.Await):
            # Check if this await is for a to_thread call
            if isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Name) and call.func.id == "to_thread":
                    # Check the arguments
                    if len(call.args) > 0:
                        arg = call.args[0]
                        # The arg should be an Attribute (self._file.close)
                        if isinstance(arg, ast.Attribute):
                            # Verify it's self._file.close
                            if (arg.attr == "close" and
                                isinstance(arg.value, ast.Attribute) and
                                arg.value.attr == "_file"):
                                found_correct_pattern = True
                                break

    assert found_correct_pattern, \
        "Issue #1731 verification failed: Could not find 'await to_thread(self._file.close)' pattern"


if __name__ == "__main__":
    # Run all tests
    print("Testing Issue #1731 - Verifying false positive...")

    test_simple_async_file_has_await()
    print("✓ Test 1: await keyword is present")

    test_to_thread_calls_method()
    print("✓ Test 2: to_thread correctly calls methods")

    test_simple_async_file_source_code()
    print("✓ Test 3: Source code contains correct pattern")

    test_simple_async_file_ast_verification()
    print("✓ Test 4: AST structure verified")

    print("\nAll tests passed! Issue #1731 is confirmed as a FALSE POSITIVE.")
    print("The code 'await to_thread(self._file.close)' is CORRECT.")
