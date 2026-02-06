"""Claude client wrapper backed by claude-agent-sdk."""

import logging
import os
import time
from pathlib import Path
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
        self.prompt_dir = Path(__file__).resolve().parent.parent / "prompts"

    def _load_prompt(self, filename: str, filepath: str) -> str:
        template_path = self.prompt_dir / filename
        return template_path.read_text(encoding="utf-8").replace("{{FILEPATH}}", filepath)

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
                return cast(
                    str,
                    self.sdk_client.chat(
                        payload,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        allowed_tools=self.readonly_tools,
                    ),
                )
            except Exception as e:
                if attempt >= self.max_retries - 1:
                    raise
                logger.warning("Agent SDK call failed (attempt %s): %s", attempt + 1, e)
                time.sleep(2**attempt)
        raise RuntimeError("Max retries exceeded")

    def analyze_code(self, filepath: str) -> list[dict]:
        prompt = self._load_prompt("analyze_code.md", filepath)

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
        prompt = self._load_prompt("analyze_opportunities.md", filepath)

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
