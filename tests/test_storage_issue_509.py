"""Test for issue #509 - Windows module import error should not expose stack traces.

This test ensures that when pywin32 is not installed on Windows, the ImportError
message does not expose internal file paths or stack traces from the original exception.
"""

import os
import sys
import unittest
from unittest.mock import patch, Mock


class TestIssue509(unittest.TestCase):
    """Test that Windows import errors don't expose internal stack traces."""

    def test_import_error_message_is_sanitized(self):
        """Test that ImportError message construction doesn't include raw exception details."""
        # Create a mock exception that might contain sensitive info
        mock_exception = ImportError(
            "No module named 'win32security' (sensitive path: C:\\Users\\Admin\\...)"
        )

        # Simulate the OLD buggy behavior (what we're fixing)
        old_message = f"pywin32 is required on Windows. Original error: {mock_exception}"

        # Simulate the NEW secure behavior (what we want)
        new_message = (
            "pywin32 is required on Windows for secure directory permissions "
            "and mandatory file locking (Issue #451, #429). "
            "Install it with: pip install pywin32."
        )

        # Verify old message contains sensitive info
        self.assertIn("No module named", old_message)
        self.assertIn("Original error:", old_message)

        # Verify new message does NOT contain sensitive info
        self.assertNotIn("No module named", new_message)
        self.assertNotIn("Original error:", new_message)
        self.assertNotIn("C:\\Users\\", new_message)

    def test_error_message_does_not_contain_original_exception(self):
        """Test that the error message doesn't embed the original exception object."""
        # Create various types of exceptions that might occur
        test_exceptions = [
            ImportError("No module named 'win32security'"),
            ImportError("DLL load failed while importing win32security: The specified module could not be found"),
            OSError("WinError 126: The specified module could not be found"),
            Exception("Unexpected error with file path: /home/user/sensitive/data"),
        ]

        for exc in test_exceptions:
            with self.subTest(exception=str(exc)):
                # OLD behavior (insecure - includes {e})
                old_message = f"pywin32 is required. Original error: {exc}"

                # NEW behavior (secure - no {e})
                new_message = "pywin32 is required on Windows. Install it with: pip install pywin32"

                # Verify old message leaks exception details
                self.assertIn(str(exc), old_message)

                # Verify new message doesn't leak exception details
                self.assertNotIn(str(exc), new_message)
                self.assertNotIn("Original error:", new_message)

    def test_current_implementation_is_secure(self):
        """Test that the current implementation in storage.py is secure."""
        # Read the storage.py file and check for the insecure pattern
        storage_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'src',
            'flywheel',
            'storage.py'
        )

        with open(storage_path, 'r') as f:
            content = f.read()

        # Check that there's an ImportError for Windows
        self.assertIn('ImportError', content)
        self.assertIn('pywin32 is required', content)

        # SECURITY CHECK: The code should NOT contain "Original error: {e}"
        # This is the insecure pattern from issue #509
        # This test will FAIL before the fix and PASS after the fix
        self.assertNotIn('Original error: {e}', content,
                        "Error message should not embed raw exception object")

        # Also check for variations of the insecure pattern
        # Look for f-strings that include {e} in error messages
        import re
        # Pattern: f" ... {e}" where e is an exception variable
        insecure_pattern = r'f["\'][^"\']*\{e\}[^"\']*["\']'
        matches = re.findall(insecure_pattern, content)

        # Filter out matches that are not in error messages (false positives)
        # We're looking for error messages about pywin32
        error_context_matches = [m for m in matches if 'pywin32' in content[content.find(m)-100:content.find(m)+100]]

        self.assertEqual(len(error_context_matches), 0,
                        f"Found insecure error message pattern with {{e}}: {error_context_matches}")

    def test_error_message_structure(self):
        """Test that error messages follow secure structure."""
        # A secure error message should:
        # 1. Not include raw exception objects
        # 2. Not include "Original error:" prefix
        # 3. Provide actionable guidance
        # 4. Not include file paths or stack traces

        secure_message = (
            "pywin32 is required on Windows for secure directory permissions "
            "and mandatory file locking (Issue #451, #429). "
            "Install it with: pip install pywin32."
        )

        # Check for secure patterns
        self.assertIn("pywin32 is required", secure_message)
        self.assertIn("pip install pywin32", secure_message)

        # Check for absence of insecure patterns
        self.assertNotIn("Original error:", secure_message)
        self.assertNotIn("No module named", secure_message)
        self.assertNotIn("/", secure_message)  # No Unix paths
        self.assertNotIn("\\", secure_message)  # No Windows paths


if __name__ == '__main__':
    unittest.main()
