"""Performance tests for _sanitize_text function (Issue #5254).

This test ensures that _sanitize_text can handle large text inputs efficiently.
Target: Process 1MB text in < 100ms.
"""

import time

import pytest

from flywheel.formatter import _sanitize_text


class TestSanitizeTextPerformance:
    """Test that _sanitize_text performs well on large inputs."""

    @pytest.mark.performance
    def test_sanitize_text_1mb_performance(self) -> None:
        """Processing 1MB text should take less than 100ms."""
        # Create 1MB of text (regular ASCII characters)
        text = "a" * (1024 * 1024)  # 1MB

        start = time.perf_counter()
        result = _sanitize_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify correctness: result should be same as input since no control chars
        assert result == text
        # Verify performance: must be under 100ms
        assert elapsed_ms < 100, f"Processing 1MB took {elapsed_ms:.1f}ms (target: <100ms)"

    @pytest.mark.performance
    def test_sanitize_text_1mb_with_control_chars_performance(self) -> None:
        """Processing 1MB text with scattered control chars should be fast."""
        # Create text with control characters scattered throughout
        # Every 1000th character is a control char (0x01)
        # Use efficient string construction with multiplication
        segment = "\x01" + "a" * 999  # 1000 chars: 1 control + 999 normal
        text = segment * 1024  # 1MB total

        start = time.perf_counter()
        result = _sanitize_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify some control chars were escaped
        assert r"\x01" in result
        # Verify performance: must be under 100ms
        assert elapsed_ms < 100, f"Processing 1MB with control chars took {elapsed_ms:.1f}ms (target: <100ms)"

    @pytest.mark.performance
    def test_sanitize_text_100kb_baseline(self) -> None:
        """Smaller text (100KB) should be very fast."""
        text = "a" * (100 * 1024)  # 100KB

        start = time.perf_counter()
        result = _sanitize_text(text)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert result == text
        # 100KB should be much faster - under 10ms
        assert elapsed_ms < 10, f"Processing 100KB took {elapsed_ms:.1f}ms (target: <10ms)"
