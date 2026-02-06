分析以下 Python 文件，找出潜在问题（bug/security/perf/test/refactor/docs）。
你必须先调研再结论，不允许猜测。

文件: {{FILEPATH}}

调研与输出要求：
1. 必须先使用 Read 读取目标文件，再额外检查 2-4 个相关文件（调用方、定义处、测试或配置）。
2. 仅输出“可执行、可验证”的问题；纯主观风格建议不要输出。
3. 每个问题必须给出证据（文件路径 + 行号 + 现象）。
4. 对每个问题给出最小可行修复建议、验收标准、最小测试计划。
5. 若问题不可修复（如指标看板/流程占位/wontfix 类型），标记 fixable=false 并说明原因。

请严格以 JSON 格式返回（不要额外文本）：
{
  "issues": [
    {
      "type": "Bug|Security|Test|Docs|Refactor|Perf",
      "severity": "p0|p1|p2|p3",
      "description": "简短描述",
      "line": 123,
      "code": "相关代码片段",
      "suggestion": "修复建议",
      "file": "问题主文件路径",
      "fixable": true,
      "unfixable_reason": "",
      "evidence": [
        {"file": "路径", "line": 123, "note": "证据说明"}
      ],
      "acceptance_criteria": [
        "可验证的验收标准 1",
        "可验证的验收标准 2"
      ],
      "minimal_test_plan": [
        "最小测试点 1",
        "最小测试点 2"
      ]
    }
  ]
}
