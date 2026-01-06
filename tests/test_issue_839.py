"""Test for issue #839 - sanitize_string control character handling.

This test verifies that sanitize_string properly handles control characters
to prevent shell argument injection when the output is used in unquoted shell commands.

NOTE: Issue #849 updated this behavior to preserve spaces for display text integrity.
The security concern from #839 is addressed by removing control characters directly
without creating spaces, and relying on subprocess list arguments or shlex.quote()
for actual shell command execution.
"""

import pytest
from flywheel.cli import sanitize_string


def test_sanitize_string_handles_control_chars():
    """Test that sanitize_string removes control characters to prevent injection.

    Issue #839: If sanitize_string output is used in unquoted shell commands
    (like os.system), control characters could enable argument injection.

    This test ensures control characters are removed by default to make the
    function safer for shell command usage, even though subprocess list arguments
    or shlex.quote() should still be used for actual shell command execution.

    Updated for Issue #849: Spaces are now preserved for display text integrity.
    """
    # Test 1: Spaces in regular input should be preserved (Issue #849)
    assert sanitize_string("hello world") == "hello world"

    # Test 2: Control characters should be removed directly (no space added)
    assert sanitize_string("hello\x00world") == "helloworld"

    # Test 3: Multiple spaces should be preserved
    assert sanitize_string("hello  world") == "hello  world"

    # Test 4: Tabs and newlines should be removed directly (no space added)
    assert sanitize_string("hello\tworld") == "helloworld"
    assert sanitize_string("hello\nworld") == "helloworld"

    # Test 5: Leading/trailing spaces should be preserved (Issue #849)
    assert sanitize_string(" hello ") == " hello "

    # Test 6: Mixed control chars and spaces should be handled
    assert sanitize_string("hello\x00 \nworld") == "hello world"

    # Test 7: Control chars should be removed without creating spaces
    # This is the critical security test case
    assert sanitize_string("todo\x00extra") == "todoextra"
