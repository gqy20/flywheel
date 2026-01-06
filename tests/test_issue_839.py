"""Test for issue #839 - sanitize_string should remove spaces to prevent argument injection.

This test verifies that sanitize_string removes spaces to prevent shell argument
injection when the output is used in unquoted shell commands.
"""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_removes_spaces():
    """Test that sanitize_string removes spaces to prevent argument injection.

    Issue #839: If sanitize_string output is used in unquoted shell commands
    (like os.system), spaces could enable argument injection. For example:
    - Input: "todo\x00extra"
    - Current: "todo extra" (spaces preserved - vulnerable!)
    - Expected: "todoextra" (spaces removed - safe!)

    This test ensures spaces are removed by default to make the function safer
    for shell command usage, even though subprocess list arguments or shlex.quote()
    should still be used for actual shell command execution.
    """
    # Test 1: Spaces in regular input should be removed
    assert sanitize_string("hello world") == "helloworld"

    # Test 2: Control characters should be replaced with spaces, then removed
    assert sanitize_string("hello\x00world") == "helloworld"

    # Test 3: Multiple spaces should be removed
    assert sanitize_string("hello  world") == "helloworld"

    # Test 4: Tabs and newlines should be replaced with spaces, then removed
    assert sanitize_string("hello\tworld") == "helloworld"
    assert sanitize_string("hello\nworld") == "helloworld"

    # Test 5: Leading/trailing spaces should be removed
    assert sanitize_string(" hello ") == "hello"

    # Test 6: Mixed control chars and spaces should be handled
    assert sanitize_string("hello\x00 \nworld") == "helloworld"

    # Test 7: Spaces from control char replacement should be removed
    # This is the critical security test case
    assert sanitize_string("todo\x00extra") == "todoextra"
