#!/usr/bin/env python3
"""Regression checks for user-visible ship-it boundaries and retired runners."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SHIP_IT = ROOT / "ship-it" / "SKILL.md"
BATCH = ROOT / "ship-it" / "references" / "batch.md"
RELEASE = ROOT / "ship-it" / "references" / "release-gates.md"
WORKFLOW = ROOT / ".github" / "workflows" / "ship-it.yml"
RUNNERS = sorted((ROOT / "ticket-fleet" / "scripts").glob("*.sh"))


class DeliveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ship_it = SHIP_IT.read_text(encoding="utf-8")
        cls.batch = BATCH.read_text(encoding="utf-8")
        cls.release = RELEASE.read_text(encoding="utf-8")
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def assert_contains_prose(self, text: str, fragment: str) -> None:
        normalized_text = " ".join(text.replace("`", "").split())
        normalized_fragment = " ".join(fragment.replace("`", "").split())
        self.assertIn(normalized_fragment, normalized_text)

    def test_normal_repairs_preserve_mandate_but_refresh_evidence(self) -> None:
        self.assertIn("A new commit invalidates affected evidence, not the mandate", self.ship_it)
        self.assertIn("rerun affected checks and review the changed scope", self.ship_it)
        self.assertIn("A rebase or new SHA invalidates", self.batch)
        self.assertIn("not authorization", self.batch)

    def test_task_dependencies_are_isolated_and_production_gates_are_separate(self) -> None:
        self.assert_contains_prose(self.ship_it, "meet the full credential-free isolation requirements in global AGENTS.md")
        self.assert_contains_prose(self.batch, "meet the full credential-free isolation requirements in global AGENTS.md")
        self.assertIn("a disposable directory alone is not isolation", self.ship_it)
        self.assertIn("a disposable directory alone\n  is not isolation", self.batch)
        self.assertIn("A production-only prerequisite does not prevent local implementation\nor PR preparation", self.batch)

    def test_unknown_external_outcomes_reconcile_before_retry(self) -> None:
        self.assertIn("reconcile provider state and receipts", self.ship_it)
        self.assert_contains_prose(
            self.ship_it,
            "Do not repeat publication, merge, or deployment merely because a response was lost",
        )
        self.assertIn("Reconcile provider receipts and immutable\nrevision identity first", self.batch)

    def test_pr_endpoint_stops_before_merge(self) -> None:
        self.assertIn("A PR endpoint remains a PR even when all\n   checks pass", self.ship_it)
        self.assertIn("does not authorize or imply merging them", self.batch)

    def test_explicit_workflow_invocation_covers_required_pr_publication(self) -> None:
        compatibility = (ROOT / "ticket-fleet" / "SKILL.md").read_text(encoding="utf-8")
        self.assert_contains_prose(
            self.ship_it,
            "An explicit user request naming the task, owning repository, and endpoint",
        )
        self.assert_contains_prose(self.ship_it, "Automatic skill selection does not create or expand")
        self.assert_contains_prose(compatibility, "is the user's request to prepare and publish PRs")
        self.assert_contains_prose(compatibility, "If the repository or target is unclear, clarify it before publication")

    def test_no_progress_pauses_for_diagnosis_not_automatic_reapproval(self) -> None:
        self.assertIn("pause that branch and report\nthe diagnosis and smallest missing decision or capability", self.ship_it)
        self.assertIn("not automatically a new owner-approval request", self.ship_it)
        self.assertIn("resume within\nthe mandate when new evidence supports a bounded hypothesis", self.ship_it)

    def test_automatic_rollout_preparation_precedes_trigger_and_runs_once(self) -> None:
        self.assertIn("complete step 7's production preparation\n   before publishing", self.ship_it)
        self.assertIn("complete step 7's production preparation before merging", self.ship_it)
        self.assertIn("Verify a successful automatic rollout once; do not run a second manual\n   deployment", self.ship_it)

    def test_scope_escalation_holds_only_dependent_work(self) -> None:
        self.assertIn("Safe\n   independent work may continue", self.ship_it)
        self.assertIn("A blocked dependency holds only downstream\nwork that requires it", self.batch)

    def test_review_and_required_checks_cannot_be_weakened(self) -> None:
        self.assertIn("does not satisfy an independent review requirement", self.ship_it)
        self.assertIn("never weaken, bypass, or\n   infer success", self.ship_it)
        self.assertIn("rerun the repository's required checks and\nindependent review", self.batch)
        self.assertIn("current integration context", self.release)
        self.assertIn("native runtime or UI evidence", self.ship_it)

    def test_ci_runs_both_suites_for_ship_it_and_legacy_runner_changes(self) -> None:
        self.assertEqual(self.workflow.count('"ticket-fleet/**"'), 2)
        self.assertIn("python3 ship-it/scripts/test_check_ci.py", self.workflow)
        self.assertIn("python3 ship-it/scripts/test_delivery_contract.py", self.workflow)
        self.assertIn("actions/checkout@11d5960a326750d5838078e36cf38b85af677262", self.workflow)
        self.assertIn("actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065", self.workflow)

    def test_retired_runner_scripts_fail_closed_without_dispatch(self) -> None:
        expected = {
            "continue-ticket-broker.sh",
            "continue-ticket-m5.sh",
            "continue-ticket.sh",
            "run-ticket-broker.sh",
            "run-ticket-m5.sh",
            "run-ticket.sh",
        }
        self.assertEqual({path.name for path in RUNNERS}, expected)

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            marker = temp / "dispatched"
            fake = temp / "fake-command"
            fake.write_text(f"#!/bin/sh\n: > '{marker}'\n", encoding="utf-8")
            fake.chmod(0o755)
            for tool in ("claude", "git", "gh"):
                (temp / tool).symlink_to(fake)
            environment = os.environ.copy()
            environment["PATH"] = str(temp)

            for script in RUNNERS:
                with self.subTest(script=script.name):
                    result = subprocess.run(
                        ["/bin/sh", str(script), "unused", "arguments"],
                        text=True,
                        capture_output=True,
                        env=environment,
                        check=False,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("runners are retired", result.stderr)
                    self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
