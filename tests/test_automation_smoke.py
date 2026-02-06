"""Smoke tests for the current automation baseline."""

from pathlib import Path


def test_scripts_entrypoints_exist() -> None:
    for name in ["scan.py", "evaluate.py", "curate.py", "ci_failure_fix.py"]:
        assert (Path("scripts") / name).exists(), f"missing scripts/{name}"


def test_shared_modules_exist() -> None:
    for name in ["claude.py", "agent_sdk.py", "utils.py"]:
        assert (Path("scripts/shared") / name).exists(), f"missing scripts/shared/{name}"
