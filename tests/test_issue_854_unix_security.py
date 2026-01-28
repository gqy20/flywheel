"""Test Unix degraded mode security enforcement (Issue #854).

This test verifies that when fcntl is not available on Unix systems
and strict mode is enabled, the system raises an error instead of
silently continuing in degraded mode.

This addresses the security concern that degraded mode can lead to
data corruption in concurrent scenarios.
"""

import os
import sys
import pytest
import tempfile


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason="Test only applies to Unix-like systems"
)
def test_strict_mode_prevents_degraded_operation():
    """Test that FLYWHEEL_STRICT_MODE environment variable prevents degraded mode.

    When FLYWHEEL_STRICT_MODE=1 is set and fcntl is not available,
    the system should raise an error instead of continuing in degraded mode.
    """
    import flywheel.storage

    # Only test if fcntl is not available (degraded mode)
    if flywheel.storage.fcntl is not None:
        pytest.skip("This test requires degraded mode (fcntl not available)")

    # Set strict mode environment variable
    original_strict_mode = os.environ.get('FLYWHEEL_STRICT_MODE')
    os.environ['FLYWHEEL_STRICT_MODE'] = '1'

    try:
        # Reload the module to pick up the environment variable
        import importlib
        importlib.reload(flywheel.storage)

        # Try to create a FileStorage instance
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # This should raise an error in strict mode when fcntl is not available
            with pytest.raises(RuntimeError) as exc_info:
                storage = flywheel.storage.FileStorage(temp_path)

            # Verify the error message mentions the security concern
            assert 'fcntl' in str(exc_info.value).lower() or 'degraded' in str(exc_info.value).lower()
            assert 'strict' in str(exc_info.value).lower() or 'security' in str(exc_info.value).lower()

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    finally:
        # Restore original environment
        if original_strict_mode is None:
            os.environ.pop('FLYWHEEL_STRICT_MODE', None)
        else:
            os.environ['FLYWHEEL_STRICT_MODE'] = original_strict_mode

        # Reload module to restore normal state
        import importlib
        importlib.reload(flywheel.storage)


@pytest.mark.skipif(
    sys.platform == 'win32',
    reason="Test only applies to Unix-like systems"
)
def test_strict_mode_allows_operation_with_fcntl():
    """Test that strict mode works fine when fcntl is available.

    When fcntl is available, strict mode should not prevent normal operation.
    """
    import flywheel.storage

    # Only test if fcntl is available
    try:
        import fcntl
    except ImportError:
        pytest.skip("This test requires fcntl to be available")

    # Set strict mode environment variable
    original_strict_mode = os.environ.get('FLYWHEEL_STRICT_MODE')
    os.environ['FLYWHEEL_STRICT_MODE'] = '1'

    try:
        # Reload the module to pick up the environment variable
        import importlib
        importlib.reload(flywheel.storage)

        # Create a FileStorage instance - should work fine with fcntl
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # This should NOT raise an error when fcntl is available
            storage = flywheel.storage.FileStorage(temp_path)
            assert storage is not None
            assert storage._path == temp_path

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    finally:
        # Restore original environment
        if original_strict_mode is None:
            os.environ.pop('FLYWHEEL_STRICT_MODE', None)
        else:
            os.environ['FLYWHEEL_STRICT_MODE'] = original_strict_mode

        # Reload module to restore normal state
        import importlib
        importlib.reload(flywheel.storage)


def test_degraded_mode_without_strict_mode():
    """Test that degraded mode works without strict mode (backward compatibility).

    When strict mode is not enabled, the system should allow degraded mode
    for backward compatibility (e.g., Cygwin users).
    """
    import flywheel.storage

    # Ensure strict mode is disabled
    original_strict_mode = os.environ.get('FLYWHEEL_STRICT_MODE')
    if 'FLYWHEEL_STRICT_MODE' in os.environ:
        del os.environ['FLYWHEEL_STRICT_MODE']

    try:
        # Reload the module
        import importlib
        importlib.reload(flywheel.storage)

        # Create a FileStorage instance - should work in degraded mode
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            # This should work regardless of fcntl availability
            storage = flywheel.storage.FileStorage(temp_path)
            assert storage is not None
            assert storage._path == temp_path

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            lock_path = temp_path + '.lock'
            if os.path.exists(lock_path):
                try:
                    os.rmdir(lock_path) if os.path.isdir(lock_path) else os.unlink(lock_path)
                except:
                    pass

    finally:
        # Restore original environment
        if original_strict_mode is not None:
            os.environ['FLYWHEEL_STRICT_MODE'] = original_strict_mode

        # Reload module to restore normal state
        import importlib
        importlib.reload(flywheel.storage)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
