"""Test for issue #1369 - NFKC normalization safety with shlex.quote().

Issue #1369: In 'shell' context, although shlex.quote is used, the code logic
(based on use_nfkc) performs NFKC normalization first. If input contains maliciously
constructed Unicode characters, the normalized result might still contain characters
processed by shlex.quote. We need to ensure normalization doesn't compromise the
safety of quoting.

The fix validates that the combination of NFKC normalization followed by
shlex.quote() is safe and doesn't introduce injection vulnerabilities.
"""

import subprocess
import shlex
import unicodedata
import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1369:
    """Test that NFKC normalization + shlex.quote() is safe for shell context.

    The concern is that NFKC normalization could transform characters in ways
    that might affect shell safety. These tests validate that:
    1. NFKC normalization doesn't introduce dangerous transformations
    2. The combination of NFKC + shlex.quote() is safe
    3. Fullwidth/malicious characters are properly handled
    """

    def test_nfkc_normalization_with_shlex_quote_is_safe(self):
        """Test that NFKC normalization followed by shlex.quote() is safe.

        This test verifies that the order of operations (NFKC first, then quote)
        doesn't introduce vulnerabilities.
        """
        test_cases = [
            # Normal strings
            "normal_file.txt",
            "file with spaces.txt",
            "file'with'quotes.txt",

            # Fullwidth characters that NFKC normalizes
            "ｆｉｌｅ．ｔｘｔ",  # Fullwidth "file.txt"
            "ｈｔｔｐ：／／ｅｘａｍｐｌｅ．ｃｏｍ",  # Fullwidth URL

            # Dangerous characters (should be quoted)
            "file;name.txt",
            "file|pipe.txt",
            "file&amp.txt",
            "file`backtick`.txt",
            "file$dollar.txt",
            "file(paren).txt",
        ]

        for input_str in test_cases:
            # Get the result from our function
            result = sanitize_for_security_context(input_str, context="shell")

            # Manually apply NFKC + shlex.quote() to verify the order is safe
            normalized = unicodedata.normalize('NFKC', input_str)
            expected = shlex.quote(normalized)

            assert result == expected, (
                f"For input '{input_str}', expected '{expected}' "
                f"(NFKC then quote) but got '{result}'. "
                f"The order of NFKC normalization and shlex.quote() matters."
            )

    def test_fullwidth_characters_are_normalized_before_quoting(self):
        """Test that fullwidth characters are normalized to ASCII before quoting.

        Fullwidth characters are a homograph attack vector. NFKC normalization
        converts them to ASCII equivalents, making them safe for shell usage.
        """
        # Fullwidth characters that normalize to ASCII
        fullwidth_test_cases = [
            ("ｆｉｌｅ．ｔｘｔ", "file.txt"),
            ("ａｂｃ；ｄｅｆ", "abc;def"),  # Fullwidth semicolon
            ("ｔｅｓｔ｜ｐｉｐｅ", "test|pipe"),  # Fullwidth pipe
            ("ｔｅｓｔ＄ｄｏｌｌａｒ", "test$dollar"),  # Fullwidth dollar
        ]

        for fullwidth_input, expected_normalized in fullwidth_test_cases:
            result = sanitize_for_security_context(fullwidth_input, context="shell")

            # The result should be the quoted version of the NFKC-normalized string
            expected = shlex.quote(expected_normalized)

            assert result == expected, (
                f"Fullwidth input '{fullwidth_input}' should be NFKC-normalized "
                f"to '{expected_normalized}' and then quoted to '{expected}', "
                f"but got '{result}'"
            )

    def test_malicious_unicode_combinations_are_safe(self):
        """Test that malicious Unicode combinations are handled safely.

        This includes:
        - Characters that might normalize to dangerous sequences
        - Compatibility characters that could bypass filters
        - Characters that normalize to shell metacharacters
        """
        malicious_cases = [
            # Fullwidth versions of dangerous characters
            "；",  # Fullwidth semicolon (U+FF1B)
            "｜",  # Fullwidth pipe (U+FF5C)
            "＄",  # Fullwidth dollar (U+FF04)
            "＇",  # Fullwidth single quote (U+FF07)
            "＂",  # Fullwidth double quote (U+FF02)

            # Compatibility characters
            "ﬁ",  # Latin small ligature fi -> "fi"
            "²",  # Superscript two -> "2"
            "™",  # Trademark sign -> "TM"

            # Combined with normal text
            "fileｓｐａｃｅｓ.txt",
            "ｄａｎｇｅｒｏｕｓ；ｃｈａｒｓ",
        ]

        for malicious_input in malicious_cases:
            result = sanitize_for_security_context(malicious_input, context="shell")

            # Verify the result is properly quoted
            # After NFKC normalization and quoting, it should be safe for shell
            normalized = unicodedata.normalize('NFKC', malicious_input)
            expected = shlex.quote(normalized)

            assert result == expected, (
                f"Malicious input '{malicious_input}' should be safely "
                f"normalized and quoted to '{expected}', but got '{result}'"
            )

    def test_shell_output_is_actually_safe_in_subprocess(self):
        """Test that sanitized output is actually safe when used in shell commands.

        This is a runtime test that verifies the sanitized string can be
        safely used in shell commands without injection.
        """
        test_inputs = [
            "normal_file.txt",
            "ｆｉｌｅ．ｔｘｔ",  # Fullwidth
            "file;with;semicolons.txt",
            "file`whoami`.txt",
            "file\nwith\nnewlines.txt",
        ]

        for input_str in test_inputs:
            sanitized = sanitize_for_security_context(input_str, context="shell")

            # Test that it's safe in an actual shell command
            cmd = f"echo {sanitized}"
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True
            )

            # Check that the command succeeded (exit code 0)
            assert result.returncode == 0, (
                f"Command with sanitized input failed: {cmd}"
            )

            # The output should be the NFKC-normalized version of input
            # (because control chars and Unicode spoofing chars are removed)
            normalized_input = unicodedata.normalize('NFKC', input_str)
            # Remove control characters, zero-width chars, and BIDI override chars
            import re
            control_chars = re.compile(r'[\x00-\x1F\x7F]')
            zero_width = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
            bidi = re.compile(r'[\u202A-\u202E\u2066-\u2069]')

            cleaned_input = control_chars.sub('', normalized_input)
            cleaned_input = zero_width.sub('', cleaned_input)
            cleaned_input = bidi.sub('', cleaned_input)

            expected_output = cleaned_input

            assert result.stdout.strip() == expected_output, (
                f"For input '{input_str}', shell output should be "
                f"'{expected_output}' but got '{result.stdout.strip()}'. "
                f"This indicates the sanitization is not safe."
            )

    def test_nfkc_does_not_introduce_shell_metacharacters(self):
        """Test that NFKC normalization doesn't introduce unexpected shell metacharacters.

        This addresses the core concern: that NFKC normalization might transform
        safe characters into dangerous ones.
        """
        # Characters that should NOT normalize to shell metacharacters
        safe_inputs = [
            " Café ",  # Normalizes to " Cafe " (accent removed, but safe)
            " naïve ",  # Normalizes to " naive " (diaeresis removed, but safe)
            " ﬁxture ",  # Normalizes to " fixture " (ligature expanded, but safe)
            " ²³ ",  # Normalizes to " 23 " (superscripts to digits, but safe)
        ]

        for safe_input in safe_inputs:
            # Get NFKC-normalized version
            normalized = unicodedata.normalize('NFKC', safe_input)

            # Check that normalization doesn't introduce dangerous shell metacharacters
            # (except for the fact that fullwidth dangerous chars normalize to ASCII dangerous chars)
            # The key is that after normalization, shlex.quote() makes it safe
            result = sanitize_for_security_context(safe_input, context="shell")

            # The result should be properly quoted
            expected = shlex.quote(normalized)
            assert result == expected, (
                f"Safe input '{safe_input}' normalized to '{normalized}' "
                f"should be quoted to '{expected}', but got '{result}'"
            )

    def test_order_of_operations_is_correct(self):
        """Test that the order (normalize -> remove dangerous -> quote) is correct.

        This test explicitly verifies that:
        1. NFKC normalization happens first (converts fullwidth to ASCII)
        2. Control/spoofing characters are removed
        3. shlex.quote() is applied last
        """
        input_with_everything = "ｆｉｌｅ\x00ｗｉｔｈ\u200Bｓｔｕｆｆ；ｄａｎｇｅｒｏｕｓ"

        # Apply the transformations manually in the correct order
        step1_normalized = unicodedata.normalize('NFKC', input_with_everything)
        # Now remove control chars, zero-width, BIDI
        import re
        control = re.compile(r'[\x00-\x1F\x7F]')
        zero = re.compile(r'[\u200B-\u200D\u2060\uFEFF]')
        bidi = re.compile(r'[\u202A-\u202E\u2066-\u2069]')

        step2_cleaned = control.sub('', step1_normalized)
        step2_cleaned = zero.sub('', step2_cleaned)
        step2_cleaned = bidi.sub('', step2_cleaned)

        step3_quoted = shlex.quote(step2_cleaned)

        # Now get the result from our function
        result = sanitize_for_security_context(input_with_everything, context="shell")

        assert result == step3_quoted, (
            f"The order of operations should be: "
            f"NFKC normalize -> remove dangerous chars -> quote. "
            f"Expected '{step3_quoted}' but got '{result}'"
        )
