#!/usr/bin/env python3
"""Validate a captured ``gh pr view --json`` CI rollup receipt offline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")


class ReceiptError(ValueError):
    """A receipt or command-line value cannot establish a passing gate."""


class ArgumentParser(argparse.ArgumentParser):
    """Keep invalid CLI invocations on the same actionable BLOCKED channel."""

    def error(self, message: str) -> None:
        raise ReceiptError(f"invalid arguments: {message}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = ArgumentParser(
        description="Check a captured gh pr view CI receipt without network access.",
    )
    parser.add_argument(
        "receipt",
        help="JSON receipt path, or - to read the receipt from stdin",
    )
    parser.add_argument(
        "--expected-head",
        metavar="FULL40LOWERHEX",
        help="expected 40-character lowercase commit SHA",
    )
    parser.add_argument(
        "--required",
        action="append",
        metavar="NAME",
        help="required check name or status context (repeatable)",
    )
    return parser.parse_args(argv)


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA_PATTERN.fullmatch(value) is None:
        raise ReceiptError(f"{label} must be exactly 40 lowercase hexadecimal characters")
    return value


def _validate_required(required: Any) -> list[str]:
    if not isinstance(required, list) or not required:
        raise ReceiptError("at least one --required check name is required")
    if any(not isinstance(name, str) or not name for name in required):
        raise ReceiptError("--required names must be non-empty strings")
    if len(set(required)) != len(required):
        raise ReceiptError("--required names must be unique")
    return required


def validate_receipt(receipt: Any, expected_head: Any, required: Any) -> dict[str, Any]:
    """Return the compact PASS payload or raise ReceiptError."""

    expected = _require_sha(expected_head, "expected head")
    required_names = _validate_required(required)

    if not isinstance(receipt, dict):
        raise ReceiptError("receipt must be a JSON object")
    head = _require_sha(receipt.get("headRefOid"), "receipt head")
    if head != expected:
        raise ReceiptError("receipt head does not match expected head")

    rollup = receipt.get("statusCheckRollup")
    if not isinstance(rollup, list) or not rollup:
        raise ReceiptError("statusCheckRollup must be a non-empty array")

    matches: dict[str, int] = {name: 0 for name in required_names}
    for item in rollup:
        if not isinstance(item, dict):
            raise ReceiptError("statusCheckRollup contains a malformed entry")
        typename = item.get("__typename")
        if typename == "CheckRun":
            name = item.get("name")
            if not isinstance(name, str) or not name:
                raise ReceiptError("CheckRun name is missing or malformed")
            status = item.get("status")
            conclusion = item.get("conclusion")
            if not isinstance(status, str) or not isinstance(conclusion, str):
                raise ReceiptError("CheckRun status or conclusion is malformed")
            passed = status == "COMPLETED" and conclusion == "SUCCESS"
            if name in matches and not passed:
                raise ReceiptError("a required CheckRun is pending or unsuccessful")
        elif typename == "StatusContext":
            name = item.get("context")
            if not isinstance(name, str) or not name:
                raise ReceiptError("StatusContext context is missing or malformed")
            state = item.get("state")
            if not isinstance(state, str):
                raise ReceiptError("StatusContext state is malformed")
            if name in matches and state != "SUCCESS":
                raise ReceiptError("a required StatusContext is not successful")
        else:
            raise ReceiptError("statusCheckRollup contains an unsupported entry type")

        if name in matches:
            matches[name] += 1

    if any(count != 1 for count in matches.values()):
        raise ReceiptError("each required check name must occur exactly once")

    return {"status": "PASS", "head": head, "checknames": required_names}


def _read_receipt(source: str) -> Any:
    try:
        raw = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise ReceiptError("could not read receipt") from None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        raise ReceiptError("receipt is not valid JSON") from None


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if args.expected_head is None:
            raise ReceiptError("--expected-head is required")
        if args.required is None:
            raise ReceiptError("at least one --required check name is required")
        result = validate_receipt(_read_receipt(args.receipt), args.expected_head, args.required)
    except ReceiptError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, separators=(",", ":"), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
