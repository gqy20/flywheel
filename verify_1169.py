#!/usr/bin/env python3
"""验证 issue #1169 的 format 上下文转义功能是否已实现"""

from src.flywheel.cli import sanitize_for_security_context

# 测试用例
test_cases = [
    ("{", "{{", "单个左花括号"),
    ("}", "}}", "单个右花括号"),
    ("%", "%%", "单个百分号"),
    ("\\", "\\\\", "单个反斜杠"),
    ("Use {var}", "Use {{var}}", "花括号在文本中"),
    ("50%", "50%%", "百分号在文本中"),
    ("C:\\Users", "C:\\\\Users", "反斜杠在路径中"),
    ("Use {var} for 100%\\n", "Use {{var}} for 100%%\\\\n", "组合测试"),
]

print("验证 issue #1169 - format 上下文转义功能")
print("=" * 60)

all_passed = True
for input_str, expected, description in test_cases:
    result = sanitize_for_security_context(input_str, context="format")
    passed = result == expected
    all_passed = all_passed and passed

    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"{status}: {description}")
    if not passed:
        print(f"  输入: {repr(input_str)}")
        print(f"  期望: {repr(expected)}")
        print(f"  实际: {repr(result)}")

print("=" * 60)
if all_passed:
    print("✓ 所有测试通过！issue #1169 已经被修复（可能在 issue #1119 中）")
else:
    print("✗ 部分测试失败！issue #1169 确实需要修复")

exit(0 if all_passed else 1)
