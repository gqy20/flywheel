"""Test for issue #1329 - Unicode spoofing chars not removed before shlex.quote().

Issue #1329: In the 'shell' context, although NFKC normalization is used,
zero-width characters and BIDI override characters are not explicitly removed
BEFORE calling shlex.quote(), which may pose potential terminal spoofing risks.

The FIX: Ensure that in 'shell' context processing logic, after NFKC normalization
and BEFORE shlex.quote(), ZERO_WIDTH_CHARS_PATTERN and BIDI_OVERRIDE_PATTERN
are explicitly filtered out.
"""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1329:
    """Test that shell context removes Unicode spoofing chars before quoting.

    The security concern is that Unicode spoofing characters like:
    - Zero-width characters (U+200B, U+200C, U+200D, U+2060, U+FEFF)
    - BIDI override characters (U+202A, U+202B, U+202C, U+202D, U+2066, U+2067, U+2068, U+2069)

    should be removed BEFORE shlex.quote() is called to prevent potential
    terminal spoofing attacks where these characters could be used to hide
    malicious commands or deceive users about what command will be executed.
    """

    def test_shell_context_removes_zero_width_chars(self):
        """Test that shell context removes zero-width characters before quoting.

        Zero-width characters can be used to hide malicious commands or create
        visual confusion in terminal output. They should be removed before
        the string is quoted for shell usage.
        """
        # Test with various zero-width characters
        test_cases = [
            # Zero-width space (U+200B)
            ("file\u200Bname.txt", "filename.txt"),
            # Zero-width non-joiner (U+200C)
            ("file\u200Cname.txt", "filename.txt"),
            # Zero-width joiner (U+200D)
            ("file\u200Dname.txt", "filename.txt"),
            # Word joiner (U+2060)
            ("file\u2060name.txt", "filename.txt"),
            # Zero-width no-break space (U+FEFF)
            ("file\uFEFFname.txt", "filename.txt"),
            # Multiple zero-width characters
            ("file\u200B\u200C\u200Dname.txt", "filename.txt"),
            # Zero-width chars with spaces
            ("file name\u200B.txt", "'file name.txt'"),
        ]

        for input_str, expected_clean in test_cases:
            result = sanitize_for_security_context(input_str, context="shell")

            # The result should be shlex.quote() of the cleaned string
            # (without zero-width characters)
            # We check that the result doesn't contain zero-width characters
            assert "\u200B" not in result, (
                f"Zero-width space U+200B should be removed from shell context output: {result!r}"
            )
            assert "\u200C" not in result, (
                f"Zero-width non-joiner U+200C should be removed from shell context output: {result!r}"
            )
            assert "\u200D" not in result, (
                f"Zero-width joiner U+200D should be removed from shell context output: {result!r}"
            )
            assert "\u2060" not in result, (
                f"Word joiner U+2060 should be removed from shell context output: {result!r}"
            )
            assert "\uFEFF" not in result, (
                f"Zero-width no-break space U+FEFF should be removed from shell context output: {result!r}"
            )

    def test_shell_context_removes_bidi_override_chars(self):
        """Test that shell context removes BIDI override characters before quoting.

        BIDI (bidirectional) override characters can be used to deceive users about
        the direction of text, potentially hiding malicious commands or making
        benign commands appear malicious. They should be removed before
        the string is quoted for shell usage.
        """
        # Test with various BIDI override characters
        test_cases = [
            # Left-to-right override (U+202A)
            ("file\u202Aname.txt", "filename.txt"),
            # Right-to-left override (U+202B)
            ("file\u202Bname.txt", "filename.txt"),
            # Pop directional formatting (U+202C)
            ("file\u202Cname.txt", "filename.txt"),
            # Left-to-right embedding (U+202D)
            ("file\u202Dname.txt", "filename.txt"),
            # Right-to-left embedding (U+202E)
            ("file\u202Ename.txt", "filename.txt"),
            # Left-to-right isolate (U+2066)
            ("file\u2066name.txt", "filename.txt"),
            # Right-to-left isolate (U+2067)
            ("file\u2067name.txt", "filename.txt"),
            # First strong isolate (U+2068)
            ("file\u2068name.txt", "filename.txt"),
            # Pop directional isolate (U+2069)
            ("file\u2069name.txt", "filename.txt"),
        ]

        for input_str, expected_clean in test_cases:
            result = sanitize_for_security_context(input_str, context="shell")

            # The result should not contain BIDI override characters
            assert "\u202A" not in result, (
                f"Left-to-right override U+202A should be removed from shell context output: {result!r}"
            )
            assert "\u202B" not in result, (
                f"Right-to-left override U+202B should be removed from shell context output: {result!r}"
            )
            assert "\u202C" not in result, (
                f"Pop directional formatting U+202C should be removed from shell context output: {result!r}"
            )
            assert "\u202D" not in result, (
                f"Left-to-right embedding U+202D should be removed from shell context output: {result!r}"
            )
            assert "\u202E" not in result, (
                f"Right-to-left embedding U+202E should be removed from shell context output: {result!r}"
            )
            assert "\u2066" not in result, (
                f"Left-to-right isolate U+2066 should be removed from shell context output: {result!r}"
            )
            assert "\u2067" not in result, (
                f"Right-to-left isolate U+2067 should be removed from shell context output: {result!r}"
            )
            assert "\u2068" not in result, (
                f"First strong isolate U+2068 should be removed from shell context output: {result!r}"
            )
            assert "\u2069" not in result, (
                f"Pop directional isolate U+2069 should be removed from shell context output: {result!r}"
            )

    def test_shell_context_combined_unicode_spoofing_chars(self):
        """Test that shell context removes combination of Unicode spoofing characters.

        Attackers might use combinations of zero-width and BIDI characters
        to create sophisticated spoofing attacks. All should be removed.
        """
        # Test with combinations of spoofing characters
        test_cases = [
            # Zero-width + BIDI
            ("file\u200B\u202Aname.txt", "filename.txt"),
            # Multiple of each type
            ("file\u200B\u200C\u202A\u202Bname\u2066\u2069.txt", "filename.txt"),
            # Interspersed with normal characters
            ("test\u200B\u202Afile\u2060name.txt", "testfilename.txt"),
        ]

        for input_str, expected_base in test_cases:
            result = sanitize_for_security_context(input_str, context="shell")

            # Check that none of the spoofing characters remain
            spoofing_chars = [
                "\u200B", "\u200C", "\u200D", "\u2060", "\uFEFF",  # Zero-width
                "\u202A", "\u202B", "\u202C", "\u202D", "\u202E",  # BIDI override
                "\u2066", "\u2067", "\u2068", "\u2069",  # BIDI isolate
            ]

            for char in spoofing_chars:
                assert char not in result, (
                    f"Unicode spoofing character {char!r} (U+{ord(char):04X}) "
                    f"should be removed from shell context output: {result!r}"
                )

    def test_general_context_also_removes_spoofing_chars(self):
        """Test that general context also removes Unicode spoofing characters.

        While this issue focuses on shell context, the fix should ensure
        that general context also removes these characters for consistency.
        """
        # Test with zero-width characters in general context
        input_str = "file\u200B\u202Aname\u2060.txt"
        result = sanitize_for_security_context(input_str, context="general")

        # General context should also remove spoofing characters
        assert "\u200B" not in result
        assert "\u202A" not in result
        assert "\u2060" not in result

    def test_url_context_also_removes_spoofing_chars(self):
        """Test that URL context removes Unicode spoofing characters.

        URL context should also remove these characters to prevent
        homograph attacks in URLs.
        """
        # Test with zero-width characters in URL context
        input_str = "http://example.com/\u200B\u202Apath\u2060"
        result = sanitize_for_security_context(input_str, context="url")

        # URL context should remove spoofing characters
        assert "\u200B" not in result
        assert "\u202A" not in result
        assert "\u2060" not in result

    def test_filename_context_also_removes_spoofing_chars(self):
        """Test that filename context removes Unicode spoofing characters.

        Filename context should also remove these characters to prevent
        spoofing in file system operations.
        """
        # Test with zero-width characters in filename context
        input_str = "\u200B\u202Afile\u2060name.txt"
        result = sanitize_for_security_context(input_str, context="filename")

        # Filename context should remove spoofing characters
        assert "\u200B" not in result
        assert "\u202A" not in result
        assert "\u2060" not in result
