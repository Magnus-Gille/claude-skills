#!/usr/bin/env python3
"""Render the canonical /close report from a small JSON record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


LIST_FIELDS = (
    "completed",
    "verification",
    "persistence",
    "deployment",
    "cleanup",
    "blockers",
    "warnings",
    "pending",
)
REPOSITORY_FIELDS = ("name", "branch", "working_tree", "remote", "disposition")


def fail(message: str) -> None:
    print(f"render-report: {message}", file=sys.stderr)
    raise SystemExit(2)


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def require_text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not compact(value):
        fail(f"{field} must be a non-empty string")
    return compact(value)


def text_list(data: dict[str, Any], field: str) -> list[str]:
    value = data.get(field, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        fail(f"{field} must be an array of strings")
    return [compact(item) for item in value if compact(item)]


def repositories(data: dict[str, Any]) -> list[dict[str, str]]:
    value = data.get("repositories", [])
    if not isinstance(value, list):
        fail("repositories must be an array")
    result: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            fail(f"repositories[{index}] must be an object")
        row: dict[str, str] = {}
        for field in REPOSITORY_FIELDS:
            raw = item.get(field)
            if not isinstance(raw, str) or not compact(raw):
                fail(f"repositories[{index}].{field} must be a non-empty string")
            row[field] = compact(raw)
        result.append(row)
    return sorted(result, key=lambda row: (row["name"].casefold(), row["branch"].casefold()))


def table_cell(value: str) -> str:
    return value.replace("|", "\\|")


def bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- None."]


def render(data: dict[str, Any]) -> str:
    mode = require_text(data, "mode").lower()
    if mode not in {"full", "quick"}:
        fail("mode must be full or quick")
    closed_at = require_text(data, "closed_at")
    scope = text_list(data, "scope")
    if not scope:
        fail("scope must contain at least one item")

    lists = {field: text_list(data, field) for field in LIST_FIELDS}
    repos = repositories(data)

    if lists["blockers"]:
        outcome = "NOT READY"
    elif lists["warnings"] or lists["pending"]:
        outcome = "READY WITH NOTES"
    else:
        outcome = "READY"

    lines = [
        "# Session Close Report",
        "",
        f"**Status:** {outcome}",
        f"**Closed:** {closed_at}",
        f"**Mode:** {mode}",
        f"**Scope:** {', '.join(sorted(scope, key=str.casefold))}",
        "",
        "## Completed",
        "",
        *bullets(lists["completed"]),
        "",
        "## Repository state",
        "",
        "| Repository | Branch | Working tree | Remote / PR | Disposition |",
        "|---|---|---|---|---|",
    ]
    if repos:
        for repo in repos:
            lines.append(
                "| "
                + " | ".join(table_cell(repo[field]) for field in REPOSITORY_FIELDS)
                + " |"
            )
    else:
        lines.append("| None | - | - | - | - |")

    lines.extend(["", "## Verification", "", *bullets(lists["verification"])])
    lines.extend(["", "## Persistence", "", *bullets(lists["persistence"])])
    lines.extend(["", "## Deployment", "", *bullets(lists["deployment"])])
    lines.extend(["", "## Cleanup", "", *bullets(lists["cleanup"])])
    lines.extend(["", "## Risks and limitations", ""])
    risks = [f"[BLOCKER] {item}" for item in lists["blockers"]]
    risks.extend(f"[WARNING] {item}" for item in lists["warnings"])
    lines.extend(bullets(risks))
    lines.extend(["", "## Pending / next actions", ""])
    if lists["pending"]:
        lines.extend(f"{index}. {item}" for index, item in enumerate(lists["pending"], start=1))
    else:
        lines.append("- None.")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON file path, or - for stdin")
    args = parser.parse_args()
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        fail(str(error))
    if not isinstance(data, dict):
        fail("top-level JSON value must be an object")
    sys.stdout.write(render(data))


if __name__ == "__main__":
    main()
