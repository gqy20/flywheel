"""Generate one auto-fix candidate PR via Claude Agent SDK."""

from __future__ import annotations

import logging
import os

from shared.agent_sdk import AgentSDKClient

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def build_prompt(
    issue_number: str, issue_title: str, issue_url: str, candidate_id: str, run_id: str
) -> str:
    return f"""
You are candidate #{candidate_id} for fixing issue #{issue_number}.
First, load and follow the local skill at `.claude/skills/flywheel-candidate-fix/SKILL.md`.

Issue:
- Number: #{issue_number}
- Title: {issue_title}
- URL: {issue_url}

Required output:
1. Implement a focused fix using TDD:
   - Add or update a failing regression test first.
   - Implement minimal fix.
   - Run `uv run pytest ...` and `uv run ruff check ...` on changed scope.
2. Create a branch with EXACT name:
   `claude/issue-{issue_number}-candidate-{candidate_id}-{run_id}`
3. Commit using conventional commits and include issue number.
4. Create ONE PR to `master` with EXACT title prefix:
   `[AUTOFIX][ISSUE-{issue_number}][CANDIDATE-{candidate_id}]`
   followed by a short summary.
5. PR body must include:
   - Summary of change
   - Tests run
   - Risks/limitations
   - `Closes #{issue_number}`
6. Never push directly to master.
7. If blocked, comment on the issue with reason and add label `auto-fix-failed` if label exists.

Constraints:
- Keep diff small and reviewable.
- Do not modify workflows or secrets.
""".strip()


def main() -> int:
    issue_number = _required_env("ISSUE_NUMBER")
    issue_title = _required_env("ISSUE_TITLE")
    issue_url = _required_env("ISSUE_URL")
    candidate_id = _required_env("CANDIDATE_ID")
    run_id = _required_env("RUN_ID")

    branch_name = f"claude/issue-{issue_number}-candidate-{candidate_id}-{run_id}"
    logger.info(
        "Starting candidate generation issue=%s candidate=%s branch=%s",
        issue_number,
        candidate_id,
        branch_name,
    )

    prompt = build_prompt(issue_number, issue_title, issue_url, candidate_id, run_id)
    allowed_tools = [
        "Edit",
        "MultiEdit",
        "Write",
        "Read",
        "Glob",
        "Grep",
        "LS",
        "Bash(git *)",
        "Bash(gh *)",
        "Bash(uv run pytest *)",
        "Bash(uv run ruff *)",
    ]

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    response = client.chat(
        prompt=prompt,
        max_turns=int(os.environ.get("CLAUDE_MAX_TURNS", "20")),
        allowed_tools=allowed_tools,
    )

    logger.info(
        "Candidate generation completed issue=%s candidate=%s response_chars=%s",
        issue_number,
        candidate_id,
        len(response),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Auto-fix candidate generation failed: %s", exc)
        raise SystemExit(1) from exc
