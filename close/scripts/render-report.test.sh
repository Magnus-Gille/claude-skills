#!/usr/bin/env bash

set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/close-report-test.XXXXXX")"
trap 'rm -rf "$TEMP_ROOT"' EXIT

cat >"$TEMP_ROOT/input.json" <<'JSON'
{
  "mode": "full",
  "closed_at": "2026-07-19 12:00 CEST",
  "scope": ["zeta", "alpha"],
  "completed": ["Implemented the requested change."],
  "repositories": [
    {
      "name": "zeta",
      "branch": "feature/report",
      "working_tree": "clean",
      "remote": "PR #2 open",
      "disposition": "awaiting review"
    },
    {
      "name": "alpha",
      "branch": "main",
      "working_tree": "clean",
      "remote": "origin/main synchronized",
      "disposition": "complete"
    }
  ],
  "verification": ["Tests passed."],
  "persistence": ["STATUS.md updated."],
  "deployment": ["Not changed."],
  "cleanup": [],
  "blockers": [],
  "warnings": ["PR #2 remains open."],
  "pending": ["Review PR #2."]
}
JSON

cat >"$TEMP_ROOT/expected.md" <<'MARKDOWN'
# Session Close Report

**Status:** READY WITH NOTES
**Closed:** 2026-07-19 12:00 CEST
**Mode:** full
**Scope:** alpha, zeta

## Completed

- Implemented the requested change.

## Repository state

| Repository | Branch | Working tree | Remote / PR | Disposition |
|---|---|---|---|---|
| alpha | main | clean | origin/main synchronized | complete |
| zeta | feature/report | clean | PR #2 open | awaiting review |

## Verification

- Tests passed.

## Persistence

- STATUS.md updated.

## Deployment

- Not changed.

## Cleanup

- None.

## Risks and limitations

- [WARNING] PR #2 remains open.

## Pending / next actions

1. Review PR #2.
MARKDOWN

python3 "$SCRIPT_DIR/render-report.py" "$TEMP_ROOT/input.json" >"$TEMP_ROOT/actual.md"
diff -u "$TEMP_ROOT/expected.md" "$TEMP_ROOT/actual.md"

python3 - "$SCRIPT_DIR/render-report.py" <<'PY'
import importlib.util
import sys

path = sys.argv[1]
spec = importlib.util.spec_from_file_location("close_report", path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)

base = {
    "mode": "quick",
    "closed_at": "2026-07-19 12:00 CEST",
    "scope": ["repo"],
    "repositories": [],
}
assert "**Status:** READY" in module.render(base)
base["pending"] = ["Do one thing."]
assert "**Status:** READY WITH NOTES" in module.render(base)
base["blockers"] = ["User decision required."]
assert "**Status:** NOT READY" in module.render(base)
PY

printf 'ok - canonical close report rendering\n'
