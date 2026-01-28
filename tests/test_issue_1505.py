"""
测试 Issue #1505 - 验证 Python 字符串切片是安全的

Issue #1505 声称在 cli.py 第 160-161 行的切片可能会为多字节字符
创建无效的 UTF-8 序列。这是一个对 Python 3 字符串工作原理的误解。

**这是一个误报（false positive）** - 不需要修改代码。

核心事实：
1. Python 3 字符串是 Unicode 码点序列，不是字节序列
2. len(s) 返回码点数（字符数），不是字节数
3. s[:n] 按码点切片，不是按字节
4. Python 字符串切片不可能创建无效的 UTF-8 序列

建议的修复方案（.encode('utf-8', 'ignore').decode('utf-8')）是错误的：
- 它操作字节，但我们处理的是 Unicode 字符串
- 它会不必要地丢失字符
- 后续的 Unicode 规范化（NFKC/NFC）已经处理了边界情况

示例：
- 表情符号 😀 在 Python 中是 1 个码点，但在 UTF-8 中是 4 字节
- len("😀" * 100) = 100（码点），不是 400（字节）
- "😀" * 100[:50] = 50 个表情符号（50 个码点），安全且有效
- 切片发生在规范化之前，这是正确的做法

本测试验证当前实现已经是安全且正确的。
"""

import pytest
from flywheel.cli import sanitize_for_security_context


class TestIssue1505FalsePositive:
    """测试 Issue #1505 - 验证这是误报，Python 字符串切片是安全的

    所有这些测试都应该通过当前实现，证明 issue #1505 的担忧是没有根据的。
    """

    def test_emoji_slicing_preserves_valid_unicode(self):
        """测试带表情符号（4字节 UTF-8）的字符串切片后仍然有效

        表情符号如 😀 在 UTF-8 中是 4 字节，但在 Python 字符串中是 1 个码点。
        按码点切片是安全的，不会创建无效序列。
        """
        # 创建一个超过限制的表情符号字符串
        # 每个表情符号是 1 个码点，但在 UTF-8 中是 4 字节
        emoji_string = "😀" * 100  # 100 个表情符号 = 100 个码点 = 400 字节

        # 这应该在不创建无效 UTF-8 的情况下截断
        result = sanitize_for_security_context(emoji_string, max_length=50, context="general")

        # 结果应该是有效的 UTF-8
        result.encode('utf-8')  # 如果无效会抛出 UnicodeError

        # 长度应该最多为 max_length（规范化和控制字符移除后）
        # 注意：由于控制字符移除或其他处理，可能更短
        assert len(result) <= 50

    def test_mixed_multi_byte_characters(self):
        """Test slicing with mixed multi-byte characters (Chinese, emoji, accents)."""
        # Mix of different multi-byte characters:
        # - Chinese: 中 (3 bytes UTF-8, 1 code point)
        # - Emoji: 🎉 (4 bytes UTF-8, 1 code point)
        # - Accented: é (2 bytes UTF-8, 1 code point)
        mixed = "中文测试🎉🎊éàü" * 20  # Repeat to exceed limits

        result = sanitize_for_security_context(mixed, max_length=30, context="general")

        # Should be valid UTF-8
        result.encode('utf-8')

        # Length should be within bounds
        assert len(result) <= 30

    def test_pre_normalization_truncation_with_nfkc(self):
        """Test that pre-normalization truncation is safe when followed by NFKC.

        The concern in issue #1505 is that truncating before NFKC normalization
        could create invalid sequences. This test verifies that:
        1. Python slicing is safe (operates on code points)
        2. Subsequent NFKC normalization handles any edge cases
        3. The result is always valid Unicode
        """
        # Characters that expand during NFKC normalization
        # ﬁ (U+FB01) → fi (2 code points)
        # ² (U+00B2) → 2 (1 code point)
        ligature_string = "ﬁ" * 50  # 50 ligatures

        result = sanitize_for_security_context(ligature_string, max_length=20, context="url")

        # Should be valid UTF-8
        result.encode('utf-8')

        # After NFKC normalization, ﬁ becomes fi (2 characters)
        # So the result should contain 'f' and 'i' characters
        assert all(c in 'fi' for c in result)

    def test_slicing_at_various_positions(self):
        """Test slicing at various positions to ensure no invalid sequences."""
        test_strings = [
            "a" * 100 + "😀" * 100,  # ASCII then emoji
            "😀" * 100 + "a" * 100,  # Emoji then ASCII
            "中" * 100,  # All Chinese
            "éàü" * 100,  # All accented
        ]

        for test_string in test_strings:
            result = sanitize_for_security_context(test_string, max_length=50, context="general")

            # Should always be valid UTF-8
            result.encode('utf-8')

            # Should be truncation-safe
            assert len(result) <= 50

    def test_empty_and_short_strings(self):
        """Test edge cases with empty and short strings."""
        assert sanitize_for_security_context("", max_length=10, context="general") == ""
        assert sanitize_for_security_context("a", max_length=10, context="general") == "a"
        assert sanitize_for_security_context("😀", max_length=10, context="general") == "😀"

    def test_exact_boundary_slicing(self):
        """Test slicing at exact boundary conditions."""
        # Test at exactly 2x max_length (the pre-normalization threshold)
        s = "a" * 200  # Exactly 200 characters
        result = sanitize_for_security_context(s, max_length=100, context="general")

        # Should be valid
        result.encode('utf-8')
        assert len(result) <= 100

        # Test at 2x max_length + 1 (should trigger pre-normalization truncation)
        s = "a" * 201  # Just over 2x max_length
        result = sanitize_for_security_context(s, max_length=100, context="general")

        # Should be valid
        result.encode('utf-8')
        assert len(result) <= 100

    def test_python_string_slicing_is_by_code_points_not_bytes(self):
        """Demonstrate that Python slicing operates on code points, not bytes.

        This is the core reason why issue #1505 is a false positive.
        """
        # Emoji is 4 bytes in UTF-8 but 1 code point in Python
        emoji = "😀"

        # Verify byte length vs character length
        assert len(emoji.encode('utf-8')) == 4  # 4 bytes in UTF-8
        assert len(emoji) == 1  # 1 code point in Python

        # Create a string of 100 emojis
        emoji_string = emoji * 100

        # Python sees this as 100 characters (code points), not 400 bytes
        assert len(emoji_string) == 100

        # Slice by code points (this is what line 161 does: s[:effective_max_length * 2])
        sliced = emoji_string[:50]

        # Result is 50 characters, NOT 50 bytes
        assert len(sliced) == 50

        # Sliced string is still valid UTF-8
        sliced.encode('utf-8')  # Would raise if invalid

        # This demonstrates that the concern in issue #1505 is unfounded:
        # - We're slicing by code points (characters), not bytes
        # - Python guarantees the result is valid Unicode
        # - No invalid UTF-8 sequences can be created

    def test_pre_normalization_truncation_demonstration(self):
        """Demonstrate the pre-normalization truncation at line 160-161.

        This test shows exactly what happens at the code that issue #1505 is concerned about.
        """
        # Simulate the scenario at line 160-161 in cli.py
        # max_length = 100, so effective_max_length * 2 = 200

        max_length = 100
        s = "😀" * 150  # 150 emojis = 150 code points

        # This is what line 160-161 does:
        if len(s) > max_length * 2:
            s = s[:max_length * 2]

        # In this case, len(s) = 150, which is NOT > 200, so no truncation happens

        # But even if it did, the slicing would be safe:
        s_long = "😀" * 250  # 250 emojis
        if len(s_long) > max_length * 2:
            s_long = s_long[:max_length * 2]

        # After slicing: 200 emojis (200 code points)
        assert len(s_long) == 200

        # Still valid UTF-8 (no invalid sequences possible)
        s_long.encode('utf-8')  # Would raise if invalid

        # This proves the concern in issue #1505 is unfounded

    def test_issue_1505_is_false_positive(self):
        """明确验证 issue #1505 是误报

        此测试直接针对 issue #1505 的核心担忧：
        声称：s[:effective_max_length * 2] 可能会创建无效的 UTF-8 序列
        事实：Python 字符串切片按码点操作，不可能创建无效序列
        """
        # Issue #1505 担心的场景：多字节字符被截断
        # 创建一个包含大量多字节字符的字符串
        test_cases = [
            ("😀" * 250, "表情符号（4字节 UTF-8）"),
            ("中" * 250, "中文字符（3字节 UTF-8）"),
            ("éàü" * 250, "带重音的拉丁字符（2字节 UTF-8）"),
            ("a" * 150 + "😀" * 100, "混合 ASCII 和表情符号"),
        ]

        max_length = 100

        for test_string, description in test_cases:
            # 执行 Issue #1505 担心的操作：预规范化截断
            if len(test_string) > max_length * 2:
                truncated = test_string[:max_length * 2]

                # 验证 1：结果是有效的 Unicode 字符串
                try:
                    truncated.encode('utf-8')
                except UnicodeError as e:
                    pytest.fail(
                        f"{description}：预规范化截断创建了无效 UTF-8！"
                        f"这证实 issue #1505 是真的。错误：{e}"
                    )

                # 验证 2：长度符合预期
                assert len(truncated) == max_length * 2, \
                    f"{description}：截断后的长度应该是 {max_length * 2}"

            # 验证 3：完整的 sanitize_for_security_context 函数工作正常
            result = sanitize_for_security_context(
                test_string,
                max_length=max_length,
                context="general"
            )

            # 结果应该是有效的 UTF-8
            try:
                result.encode('utf-8')
            except UnicodeError as e:
                pytest.fail(
                    f"{description}：sanitize_for_security_context 创建了无效 UTF-8！"
                    f"这证实 issue #1505 是真的。错误：{e}"
                )

            # 长度应该在限制内
            assert len(result) <= max_length, \
                f"{description}：结果长度 {len(result)} 超过了 max_length {max_length}"

        # 如果所有测试都通过，issue #1505 确实是误报
        assert True, "Issue #1505 是误报，Python 字符串切片是安全的"
