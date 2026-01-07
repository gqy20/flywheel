"""Test for issue #960: Syntax error in logger.warning call

This test verifies that the storage.py module can be imported without syntax errors.
The bug was a missing closing parenthesis in a logger.warning call at line 217-219.
"""
import os
import sys

import pytest


def test_storage_module_imports_without_syntax_error():
    """Test that storage.py can be imported without syntax errors.

    Issue #960: There was a missing closing parenthesis in a logger.warning
    call at line 217-219 in src/flywheel/storage.py:
        logger.warning(
            f"Invalid FW_LOCK_STALE_SECONDS value: {env_value} "
            f"(must be positive, using default: {_STALE_LOCK_TIMEOUT_DEFAULT})"
    """
    # This should not raise SyntaxError
    try:
        import flywheel.storage
        assert True
    except SyntaxError as e:
        pytest.fail(f"SyntaxError when importing storage.py: {e}")


def test_get_stale_lock_timeout_with_invalid_value():
    """Test _get_stale_lock_timeout with invalid (non-positive) value.

    This tests the specific code path that had the syntax error.
    """
    import flywheel.storage

    # Set an invalid value (zero)
    os.environ['FW_LOCK_STALE_SECONDS'] = '0'

    # This should not raise SyntaxError
    try:
        timeout = flywheel.storage._get_stale_lock_timeout()
        assert timeout == 300  # Should return default
    except SyntaxError as e:
        pytest.fail(f"SyntaxError when calling _get_stale_lock_timeout: {e}")
    finally:
        # Clean up
        os.environ.pop('FW_LOCK_STALE_SECONDS', None)


def test_get_stale_lock_timeout_with_negative_value():
    """Test _get_stale_lock_timeout with negative value.

    This tests the specific code path that had the syntax error.
    """
    import flywheel.storage

    # Set an invalid value (negative)
    os.environ['FW_LOCK_STALE_SECONDS'] = '-100'

    # This should not raise SyntaxError
    try:
        timeout = flywheel.storage._get_stale_lock_timeout()
        assert timeout == 300  # Should return default
    except SyntaxError as e:
        pytest.fail(f"SyntaxError when calling _get_stale_lock_timeout: {e}")
    finally:
        # Clean up
        os.environ.pop('FW_LOCK_STALE_SECONDS', None)
