"""Claude client wrapper backed by claude-agent-sdk."""

import logging
import os
import time
from typing import Any, cast

from shared.agent_sdk import AgentSDKClient

logger = logging.getLogger(__name__)

# 模型配置
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "glm-4.7")
FAST_MODEL = os.getenv("ANTHROPIC_FAST_MODEL", "glm-4.7")

# 优先级映射
PRIORITY_MAP = {
    "[Security]": 100,  # p0
    "[Bug]": 75,  # p1
    "[Perf]": 50,  # p1/p2
    "[Test]": 30,  # p2
    "[Refactor]": 20,  # p2
    "[Docs]": 10,  # p3
}

PRIORITY_LABELS = {
    (80, 1000): "p0",
    (50, 79): "p1",
    (30, 49): "p2",
    (0, 29): "p3",
}


class ClaudeClient:
    """Claude wrapper with retry logic using Agent SDK only."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        _ = api_key  # compatibility
        self.model = model
        self.max_retries = 3
        self.sdk_client = AgentSDKClient(model=model)
        self.readonly_tools = ["Read", "Grep", "Glob", "LS"]

    def _calculate_priority(self, title: str) -> str:
        """Calculate priority from issue title."""
        for prefix, score in PRIORITY_MAP.items():
            if prefix in title:
                for (min_score, max_score), label in PRIORITY_LABELS.items():
                    if min_score <= score <= max_score:
                        return label
        return "p2"

    def chat(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        system_prompt: str | None = None,
    ) -> str:
        payload = prompt if not system_prompt else f"{system_prompt}\n\n{prompt}"
        for attempt in range(self.max_retries):
            try:
                return self.sdk_client.chat(
                    payload,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    allowed_tools=self.readonly_tools,
                )
            except Exception as e:
                if attempt >= self.max_retries - 1:
                    raise
                logger.warning("Agent SDK call failed (attempt %s): %s", attempt + 1, e)
                time.sleep(2**attempt)
        raise RuntimeError("Max retries exceeded")

    def analyze_code(self, filepath: str) -> list[dict]:
        prompt = f"""
分析以下 Python 文件，找出潜在问题。
请先使用 Read 工具读取该文件内容，不要猜测。

文件: {filepath}

请以 JSON 格式返回：
{{
    "issues": [
        {{
            "type": "Bug|Security|Test|Docs|Refactor|Perf",
            "severity": "p0|p1|p2|p3",
            "description": "简短描述",
            "line": 行号 (int),
            "code": "相关代码片段",
            "suggestion": "修复建议"
        }}
    ]
}}
"""

        response = self.chat(prompt, temperature=0.1)

        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                result = cast(dict[str, Any], json.loads(json_match.group()))
                return cast(list[dict], result.get("issues", []))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {response[:200]}")
                return []

        return []

    def analyze_opportunities(self, filepath: str) -> list[dict]:
        prompt = f"""
分析以下 Python 文件，发现功能增强和改进机会。
请先使用 Read 工具读取该文件内容，不要猜测。

文件: {filepath}

请思考这个文件可以如何改进，包括：
1. 缺少的常用功能（如日志、配置、缓存）
2. 用户体验改进（如进度条、彩色输出、交互模式）
3. 架构扩展性（如插件系统、钩子、抽象层）
4. 开发体验改进（如 debug 模式、错误提示、文档）

注意：
- 只建议**小的、可实现的改进**（不是大规模重构）
- 优先考虑对用户或开发者有实际价值的功能
- 避免过于抽象或理论化的建议

请以 JSON 格式返回：
{{
    "issues": [
        {{
            "type": "Feature|Enhancement",
            "description": "简短描述要添加的功能",
            "file": "文件路径（从filepath推断）",
            "value": "这个功能的价值（为什么有用）",
            "suggestion": "实现建议"
        }}
    ]
}}
"""

        response = self.chat(prompt, temperature=0.3)

        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                result = cast(dict[str, Any], json.loads(json_match.group()))
                opportunities = cast(list[dict], result.get("issues", []))
                for opp in opportunities:
                    if not opp.get("file"):
                        opp["file"] = filepath
                return opportunities
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {response[:200]}")
                return []

        return []

    def generate_fix(self, issue: dict, file_content: str) -> dict:
        prompt = f"""
修复以下问题：

{issue["description"]}

文件: {issue.get("file", "unknown")}
行号: {issue.get("line", "unknown")}

当前代码：
```python
{issue.get("code", file_content[:2000])}
```

修复建议：
{issue.get("suggestion", "N/A")}

请提供修复后的完整代码（只返回修复的部分，不要返回整个文件）。
以 JSON 格式返回：
{{
    "fixed_code": "修复后的代码",
    "start_line": 起始行号,
    "end_line": 结束行号,
    "confidence": 置信度 (0-100)
}}
"""

        response = self.chat(prompt, temperature=0.2)

        import json
        import re

        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return cast(dict[str, Any], json.loads(json_match.group()))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from response: {response[:200]}")

        return {"fixed_code": "", "confidence": 0}

    def generate_test(self, code: str, function_name: str) -> str:
        prompt = f"""
为以下代码生成单元测试：

```python
{code}
```

函数名: {function_name}

使用 pytest，生成完整的测试类。
确保测试覆盖率（正常情况、边界情况、异常情况）。
"""

        return self.chat(prompt, temperature=0.2)

    def estimate_tokens(self, text: str) -> int:
        return len(text) // 4
