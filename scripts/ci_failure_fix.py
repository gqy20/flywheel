"""Generate CI failure fix candidate PR via Claude Agent SDK."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from shared.agent_sdk import AgentSDKClient
from shared.utils import run_gh_command

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CiFixContext:
    pr_number: str
    head_branch: str
    target_run_id: str
    target_run_url: str
    failure_summary: str
    run_id: str

    @property
    def fix_branch(self) -> str:
        return f"claude/ci-fix-pr-{self.pr_number}-{self.run_id}"


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _build_prompt(context: CiFixContext) -> str:
    return f"""
You are fixing a failed CI run for PR #{context.pr_number}.
First, load and follow the local skill at `.claude/skills/flywheel-ci-failure-autofix/SKILL.md`.

Context:
- PR: #{context.pr_number}
- Original branch: {context.head_branch}
- CI run ID: {context.target_run_id}
- CI run URL: {context.target_run_url}
- Failed jobs:
{context.failure_summary}

Required behavior:
1. Diagnose likely root cause from failed jobs/check context.
2. Implement minimal fix and run targeted verification (`uv run pytest ...`, `uv run ruff check ...`).
3. Create and use branch: `{context.fix_branch}`.
4. Open one PR to `master` with title prefix:
   `[AUTOFIX][CI-FAIL][PR-{context.pr_number}]`
5. PR body must include cause analysis, fix summary, tests run, and risks.
6. Do not push to `master` directly.

Constraints:
- Keep diff minimal and focused to failing checks.
- Do not modify workflows or repository secrets/settings.
""".strip()


def _find_open_pr_for_branch(branch_name: str) -> tuple[str, str] | None:
    result = run_gh_command(
        ["pr", "list", "--head", branch_name, "--state", "open", "--json", "number,url"],
        check=False,
    )
    if result.returncode != 0:
        logger.error(
            "Failed to query PR for branch=%s stderr=%s", branch_name, result.stderr.strip()
        )
        return None

    try:
        import json

        data = json.loads(result.stdout or "[]")
    except Exception:
        logger.error("Failed to parse gh pr list output for branch=%s", branch_name)
        return None

    if not data:
        return None
    pr = data[0]
    return str(pr.get("number", "")), str(pr.get("url", ""))


def main() -> int:
    context = CiFixContext(
        pr_number=_required_env("TARGET_PR_NUMBER"),
        head_branch=_required_env("TARGET_HEAD_BRANCH"),
        target_run_id=_required_env("TARGET_RUN_ID"),
        target_run_url=_required_env("TARGET_RUN_URL"),
        failure_summary=os.environ.get("FAILURE_SUMMARY", "").strip()
        or "No failed jobs summary provided.",
        run_id=_required_env("RUN_ID"),
    )
    max_turns = int(os.environ.get("CLAUDE_MAX_TURNS", "20"))

    logger.info(
        "Starting CI failure fix generation pr=%s source_branch=%s fix_branch=%s run_id=%s",
        context.pr_number,
        context.head_branch,
        context.fix_branch,
        context.run_id,
    )

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    allowed_tools = ["Bash", "Edit", "MultiEdit", "Write", "Read", "Glob", "Grep", "LS", "Skill"]
    prompt = _build_prompt(context)
    response = client.chat(prompt=prompt, max_turns=max_turns, allowed_tools=allowed_tools)
    logger.info("CI failure fix SDK response_chars=%s", len(response))

    pr_ref = _find_open_pr_for_branch(context.fix_branch)
    if not pr_ref:
        raise RuntimeError(
            f"SDK run completed without creating expected open PR for branch `{context.fix_branch}`"
        )

    pr_number, pr_url = pr_ref
    logger.info(
        "CI failure fix produced PR source_pr=%s new_pr=%s new_pr_url=%s",
        context.pr_number,
        pr_number,
        pr_url,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("CI failure auto-fix failed: %s", exc)
        raise SystemExit(1) from exc
