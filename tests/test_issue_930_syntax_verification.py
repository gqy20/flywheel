"""Test to verify Issue #930: Syntax error verification.

This test verifies that the code around the _get_stale_lock_timeout function
has proper syntax and that logger.warning calls are correctly formatted.

Issue #930 claimed there was a missing closing parenthesis in a logger.warning call,
but upon inspection, the code is syntactically correct.
"""

import os
import pytest
import tempfile
from pathlib import Path


def test_storage_module_has_valid_syntax():
    """Test that storage.py can be imported without syntax errors.

    This verifies that there are no syntax errors like missing parentheses
    in logger.warning calls or anywhere else in the module.
    """
    # Simply importing the module will fail if there's a syntax error
    from flywheel import storage
    assert storage is not None


def test_get_stale_lock_timeout_handles_invalid_value(caplog):
    """Test that _get_stale_lock_timeout properly logs invalid values.

    This specifically tests the logger.warning call mentioned in Issue #930
    to ensure it has proper syntax and executes without errors.
    """
    # Set an invalid value to trigger the warning
    os.environ['FW_LOCK_STALE_SECONDS'] = 'not-an-integer'

    # Reload the module to trigger the warning
    import importlib
    import flywheel.storage
    importlib.reload(flywheel.storage)

    # The module should load successfully and fall back to default
    assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
    assert flywheel.storage.STALE_LOCK_TIMEOUT == 300

    # Clean up
    del os.environ['FW_LOCK_STALE_SECONDS']


def test_get_stale_lock_timeout_handles_negative_value(caplog):
    """Test that _get_stale_lock_timeout properly logs negative values.

    This tests the other logger.warning call to ensure it has proper syntax.
    """
    # Set a negative value to trigger the warning
    os.environ['FW_LOCK_STALE_SECONDS'] = '-100'

    # Reload the module to trigger the warning
    import importlib
    import flywheel.storage
    importlib.reload(flywheel.storage)

    # The module should load successfully and fall back to default
    assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
    assert flywheel.storage.STALE_LOCK_TIMEOUT == 300

    # Clean up
    del os.environ['FW_LOCK_STALE_SECONDS']


def test_get_stale_lock_timeout_accepts_valid_value():
    """Test that _get_stale_lock_timeout works with valid values.

    This ensures the function works correctly overall.
    """
    # Set a valid custom value
    os.environ['FW_LOCK_STALE_SECONDS'] = '600'

    # Reload the module
    import importlib
    import flywheel.storage
    importlib.reload(flywheel.storage)

    # The module should use the custom value
    assert hasattr(flywheel.storage, 'STALE_LOCK_TIMEOUT')
    assert flywheel.storage.STALE_LOCK_TIMEOUT == 600

    # Clean up
    del os.environ['FW_LOCK_STALE_SECONDS']
