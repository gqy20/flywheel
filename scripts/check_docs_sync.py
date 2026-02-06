"""Generate and verify documentation synchronized with workflow inputs."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, cast

import yaml  # type: ignore[import-untyped]

WORKFLOWS_DIR = Path(".github/workflows")
OUTPUT_PATH = Path("docs/generated/workflow-inputs.md")


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return data
    return {}


def _extract_dispatch_inputs(path: Path) -> dict[str, dict[str, Any]]:
    data = _load_yaml(path)
    on_section = data.get("on")
    if on_section is None:
        on_section = cast(dict[Any, Any], data).get(True, {})
    if not isinstance(on_section, dict):
        return {}

    workflow_dispatch = on_section.get("workflow_dispatch", {})
    if not isinstance(workflow_dispatch, dict):
        return {}

    raw_inputs = workflow_dispatch.get("inputs", {})
    if not isinstance(raw_inputs, dict):
        return {}

    result: dict[str, dict[str, Any]] = {}
    for name, payload in sorted(raw_inputs.items()):
        if isinstance(payload, dict):
            result[name] = payload
        else:
            result[name] = {}
    return result


def build_markdown() -> str:
    lines: list[str] = []
    lines.append("# Workflow Inputs Reference")
    lines.append("")
    lines.append("This file is auto-generated from `.github/workflows/*.yml`.")
    lines.append(
        "Run `uv run python scripts/check_docs_sync.py --generate` after workflow changes."
    )
    lines.append("")

    workflow_files = sorted(WORKFLOWS_DIR.glob("*.yml"))
    for path in workflow_files:
        inputs = _extract_dispatch_inputs(path)
        if not inputs:
            continue

        lines.append(f"## `{path.name}`")
        lines.append("")
        lines.append("| Input | Required | Default | Type | Description |")
        lines.append("|---|---|---|---|---|")

        for key, payload in inputs.items():
            required = str(payload.get("required", False)).lower()
            default = payload.get("default", "")
            input_type = payload.get("type", "string")
            desc = str(payload.get("description", "")).replace("|", "\\|")
            default_text = str(default).replace("|", "\\|")
            lines.append(f"| `{key}` | `{required}` | `{default_text}` | `{input_type}` | {desc} |")

        lines.append("")

    return "\n".join(lines).strip() + "\n"


def generate() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_markdown(), encoding="utf-8")
    print(f"generated: {OUTPUT_PATH}")
    return 0


def check() -> int:
    if not OUTPUT_PATH.exists():
        print(f"missing generated doc: {OUTPUT_PATH}")
        print("run: uv run python scripts/check_docs_sync.py --generate")
        return 1

    actual = OUTPUT_PATH.read_text(encoding="utf-8")
    expected = build_markdown()
    if actual != expected:
        print(f"out-of-sync: {OUTPUT_PATH}")
        print("run: uv run python scripts/check_docs_sync.py --generate")
        return 1

    print("docs sync check passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true", help="Generate workflow input reference")
    group.add_argument(
        "--check", action="store_true", help="Check workflow input reference is synced"
    )
    args = parser.parse_args()

    if args.generate:
        return generate()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
