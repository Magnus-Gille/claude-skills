#!/usr/bin/env python3
"""Focused offline tests for check_ci.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check_ci.py")
HEAD = "0123456789abcdef0123456789abcdef01234567"


def receipt(*checks: dict[str, object], head: str = HEAD) -> dict[str, object]:
    return {"headRefOid": head, "statusCheckRollup": list(checks)}


def check_run(name: str = "build", *, status: str = "COMPLETED", conclusion: object = "SUCCESS") -> dict[str, object]:
    return {
        "__typename": "CheckRun",
        "name": name,
        "status": status,
        "conclusion": conclusion,
    }


def status_context(context: str = "lint", *, state: str = "SUCCESS") -> dict[str, object]:
    return {"__typename": "StatusContext", "context": context, "state": state}


class CheckCiCliTests(unittest.TestCase):
    def run_cli(
        self,
        value: object,
        *required: str,
        expected_head: str = HEAD,
        use_stdin: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = Path(directory) / "receipt.json"
            receipt_path.write_text(
                value if isinstance(value, str) else json.dumps(value),
                encoding="utf-8",
            )
            argument = "-" if use_stdin else str(receipt_path)
            return subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    argument,
                    "--expected-head",
                    expected_head,
                    *sum((["--required", name] for name in required), []),
                ],
                input=receipt_path.read_text(encoding="utf-8") if use_stdin else None,
                text=True,
                capture_output=True,
                check=False,
            )

    def assert_blocked(self, value: object, *required: str, **kwargs: object) -> None:
        result = self.run_cli(value, *required, **kwargs)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertTrue(result.stderr.startswith("BLOCKED:"), result.stderr)

    def test_valid_check_run_and_status_context_emit_short_json_pass(self) -> None:
        result = self.run_cli(receipt(check_run(), status_context()), "build", "lint")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        payload = json.loads(result.stdout)
        self.assertEqual(payload, {"status": "PASS", "head": HEAD, "checknames": ["build", "lint"]})

    def test_stdin_receipt_is_supported(self) -> None:
        result = self.run_cli(receipt(check_run()), "build", use_stdin=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help_is_available(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--expected-head", result.stdout)
        self.assertIn("--required", result.stdout)

    def test_required_names_must_be_nonempty_and_unique(self) -> None:
        value = receipt(check_run())
        self.assert_blocked(value, "")
        self.assert_blocked(value, "build", "build")

    def test_expected_head_must_be_exact_lowercase_sha(self) -> None:
        value = receipt(check_run())
        for expected in ("", "a" * 39, "A" * 40, "g" * 40):
            self.assert_blocked(value, "build", expected_head=expected)

    def test_receipt_head_must_match_expected_and_be_well_formed(self) -> None:
        self.assert_blocked(receipt(check_run(), head="f" * 39), "build")
        self.assert_blocked(receipt(check_run(), head="A" * 40), "build")
        self.assert_blocked(receipt(check_run(), head="f" * 40), "build", expected_head=HEAD)

    def test_rollup_must_be_nonempty_list(self) -> None:
        for rollup in (None, [], {}, "pending"):
            self.assert_blocked({"headRefOid": HEAD, "statusCheckRollup": rollup}, "build")
        self.assert_blocked({"headRefOid": HEAD}, "build")

    def test_check_run_requires_completed_success(self) -> None:
        self.assert_blocked(receipt(check_run(status="IN_PROGRESS")), "build")
        self.assert_blocked(receipt(check_run(status="PENDING", conclusion="SUCCESS")), "build")
        for conclusion in (None, "FAILURE", "NEUTRAL", "SKIPPED"):
            self.assert_blocked(receipt(check_run(conclusion=conclusion)), "build")

    def test_status_context_requires_success(self) -> None:
        for state in ("PENDING", "ERROR", "FAILURE", "EXPECTED"):
            self.assert_blocked(receipt(status_context(state=state)), "lint")

    def test_required_checks_must_occur_exactly_once(self) -> None:
        self.assert_blocked(receipt(check_run("other")), "build")
        self.assert_blocked(receipt(check_run("build"), check_run("build")), "build")
        self.assert_blocked(receipt(check_run("build"), status_context("build")), "build")

    def test_malformed_rollup_entries_and_json_are_blocked(self) -> None:
        self.assert_blocked(receipt({}), "build")
        self.assert_blocked(receipt({"__typename": "Unknown", "name": "build"}), "build")
        self.assert_blocked(receipt({"__typename": "CheckRun", "name": "build"}), "build")
        self.assert_blocked("{not-json", "build")

    def test_failure_does_not_echo_receipt_content(self) -> None:
        secret = "do-not-echo-this-receipt-value"
        result = self.run_cli(
            {"headRefOid": HEAD, "statusCheckRollup": [{"__typename": "Bad", "secret": secret}]},
            "build",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stderr)


if __name__ == "__main__":
    unittest.main()
