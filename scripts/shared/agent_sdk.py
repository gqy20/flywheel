"""Claude Agent SDK wrapper for script automation."""

from __future__ import annotations

import logging
import os
from typing import Any, cast

import anyio
from claude_agent_sdk import ClaudeAgentOptions, TextBlock, query

logger = logging.getLogger(__name__)


class AgentSDKClient:
    """Small wrapper around claude-agent-sdk query API."""

    def __init__(self, model: str | None = None):
        token = os.environ.get("ANTHROPIC_AUTH_TOKEN", "").strip()
        if not token:
            raise ValueError("ANTHROPIC_AUTH_TOKEN environment variable is required")

        self.model = model or os.environ.get("ANTHROPIC_MODEL", "")
        self.base_url = os.environ.get("ANTHROPIC_BASE_URL", "").strip()
        self.token = token
        self.max_turns_default = int(os.environ.get("CLAUDE_MAX_TURNS", "25"))

    def _build_env(self) -> dict[str, str]:
        env: dict[str, str] = {
            # Keep user-requested variable name as source-of-truth.
            "ANTHROPIC_AUTH_TOKEN": self.token,
            # Some SDK/provider adapters read API_TOKEN; provide both.
            "ANTHROPIC_API_TOKEN": self.token,
        }
        if self.base_url:
            env["ANTHROPIC_BASE_URL"] = self.base_url
        if self.model:
            env["ANTHROPIC_MODEL"] = self.model
        return env

    async def _chat_async(
        self,
        prompt: str,
        max_turns: int,
        temperature: float,
        allowed_tools: list[str] | None,
    ) -> str:
        extra_args: dict[str, Any] = {"max-turns": str(max_turns)}
        if self.model:
            extra_args["model"] = self.model

        options = ClaudeAgentOptions(
            system_prompt={"type": "preset", "preset": "claude_code"},
            setting_sources=["user", "project"],
            cwd=os.getcwd(),
            env=self._build_env(),
            extra_args=extra_args,
            permission_mode="bypassPermissions",
            allowed_tools=allowed_tools or [],
        )

        chunks: list[str] = []
        async for message in query(prompt=prompt, options=options):
            if getattr(message, "type", None) == "assistant":
                msg = getattr(message, "message", None)
                if msg is None:
                    continue
                for block in getattr(msg, "content", []) or []:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
            elif getattr(message, "type", None) == "result":
                # bubble up explicit error result to caller for better diagnostics
                if getattr(message, "is_error", False):
                    result_text = getattr(message, "result", "")
                    raise RuntimeError(result_text or "Claude Agent SDK returned error")

        return "".join(chunks).strip()

    def chat(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        max_turns: int | None = None,
        allowed_tools: list[str] | None = None,
    ) -> str:
        """Chat via Claude Agent SDK.

        max_tokens is accepted for interface compatibility.
        """
        _ = max_tokens
        _ = temperature
        turns = max_turns if max_turns is not None else self.max_turns_default
        return cast(
            str,
            anyio.run(self._chat_async, prompt, turns, temperature, allowed_tools),
        )
