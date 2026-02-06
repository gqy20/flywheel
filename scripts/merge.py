"""Merge arbiter for candidate PRs via Claude Agent SDK."""

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


def build_prompt(issue_number: str, eligible_csv: str) -> str:
    return f"""
You are the dedicated merge arbiter for auto-fix candidates.
First, load and follow the local skill at `.claude/skills/flywheel-merge-arbiter/SKILL.md`.

Target issue: #{issue_number}
Eligible candidate PRs (CSV): {eligible_csv}

Required workflow:
1. Compare only the eligible candidates (all checks already green, non-draft, mergeable).
2. Score each candidate using this weighted rubric (0-10 each dimension):
   - Correctness and issue coverage (weight 0.45)
   - Regression risk (weight 0.30, lower risk means higher score)
   - Simplicity and maintainability (weight 0.15)
   - Test quality and verification evidence (weight 0.10)
3. Compute total score = weighted sum and rank all candidates.
4. Publish a machine-readable scorecard comment on the winner PR before merge, exactly:
   <!-- arbiter-scorecard -->
   {{"issue":<issue_number>,"winner_pr":<pr_number>,"scores":[{{"pr":<number>,"correctness":<0-10>,"risk":<0-10>,"maintainability":<0-10>,"tests":<0-10>,"total":<0-10>,"verdict":"winner|rejected","reason":"..."}}]}}
5. Merge exactly one winner to `master` using squash merge.
6. Comment and close non-winner candidate PRs with brief reasons and score deltas.
7. If no candidate is safe after deep review, do not merge and comment on issue #{issue_number}.

Constraints:
- Never merge more than one PR.
- Use GitHub CLI for PR/issue operations.
- Do not modify workflows or repository settings.
""".strip()


def main() -> int:
    issue_number = _required_env("ISSUE_NUMBER")
    eligible_csv = _required_env("ELIGIBLE_CSV")
    logger.info("Starting merge arbiter issue=%s eligible=%s", issue_number, eligible_csv)

    prompt = build_prompt(issue_number, eligible_csv)
    allowed_tools = ["Bash", "Read", "Glob", "Grep", "LS"]

    client = AgentSDKClient(model=os.environ.get("ANTHROPIC_MODEL", "").strip() or None)
    response = client.chat(
        prompt=prompt,
        max_turns=int(os.environ.get("CLAUDE_MAX_TURNS", "25")),
        allowed_tools=allowed_tools,
    )

    logger.info("Merge arbiter completed issue=%s response_chars=%s", issue_number, len(response))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        logger.exception("Merge arbiter failed: %s", exc)
        raise SystemExit(1) from exc
