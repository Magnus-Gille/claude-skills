#!/usr/bin/env python3
"""Synthetic behavior tests for the bounded code-friction outbox."""

from __future__ import annotations

import copy
import concurrent.futures
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("code_friction", Path(__file__).with_name("code-friction.py"))
assert spec is not None and spec.loader is not None
friction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(friction)


STAMP = "2026-10-10T12:00:00Z"
REF = "ref:fixture-source"


def person(kind: str, ident: str, model: str | None) -> dict:
    return {
        "id": f"ref:{ident}",
        "kind": kind,
        "requested_model": model,
        "observed_model": model,
        "observed_effort": "high" if model else None,
    }


def capture() -> dict:
    return {
        "repo_owner": "Magnus-Gille",
        "repo_name": "synthetic-repo",
        "namespace": "projects/synthetic-repo",
        "classification": "internal",
        "task_id": "task-20261010",
        "task_class": "implementation",
        "attempt_id": "parent-attempt",
        "parent_attempt_id": None,
        "child_attempt_ids": ["child-attempt"],
        "observed_at": STAMP,
        "before_sha": "a" * 40,
        "after_sha": "b" * 40,
        "module_refs": ["ref:module-one"],
        "reporter": person("close", "close-runner", "gpt-6-sol"),
        "actual_worker": person("worker", "child-worker", None),
        "observations": [
            {
                "key": "hidden-consumer",
                "attempt_id": "child-attempt",
                "parent_attempt_id": "parent-attempt",
                "reporter": person("worker", "child-worker", "gpt-6-luna"),
                "actual_worker": person("worker", "child-worker", None),
                "observed_at": STAMP,
                "before_sha": "a" * 40,
                "after_sha": None,
                "dimension": "understand",
                "polarity": "negative",
                "cause": "code",
                "supporting_refs": [REF],
                "counter_refs": [],
                "summary": "A second known consumer had to be traced before the effect was clear.",
                "source_observation_ref": None,
            }
        ],
        "assessment": {
            "applicability": "applicable",
            "outcome": "completed",
            "completeness": "complete",
            "environment": "available",
            "observation_keys": ["hidden-consumer"],
            "ratings": [
                {"dimension": "locate", "value": "manageable", "reason": "grounded", "evidence_refs": [REF]},
                {"dimension": "understand", "value": "difficult", "reason": "grounded", "evidence_refs": [REF]},
                {"dimension": "verify", "value": "manageable", "reason": "grounded", "evidence_refs": [REF]},
            ],
        },
    }


class CodeFrictionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.outbox = Path(self.temp.name) / "state" / "outbox.json"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_positive_record_shapes_and_stable_ids_keep_reporter_separate(self) -> None:
        data = capture()
        records = friction.build_records(data)
        again = friction.build_records(copy.deepcopy(data))
        self.assertEqual(records, again)
        observation, assessment = records
        self.assertEqual(observation["actual_worker"]["observed_model"], None)
        self.assertEqual(observation["reporter"]["observed_model"], "gpt-6-luna")
        self.assertEqual(assessment["reporter"]["kind"], "close")
        self.assertEqual(assessment["observation_refs"], [observation["record_id"]])
        self.assertNotIn("transcript", json.dumps(records))

    def test_positive_observation_and_failed_work_are_supported(self) -> None:
        data = capture()
        data["observations"][0]["polarity"] = "positive"
        data["assessment"].update({"outcome": "failed", "completeness": "partial"})
        records = friction.build_records(data)
        self.assertEqual(records[0]["polarity"], "positive")
        self.assertEqual(records[-1]["outcome"], "failed")
        self.assertEqual(records[-1]["completeness"], "partial")

    def test_observation_cap_is_three_distinct_occurrences(self) -> None:
        data = capture()
        first = data["observations"][0]
        data["observations"] = [copy.deepcopy(first) for _ in range(3)]
        # Same attempt and key may only be repeated as an exact replay.
        self.assertEqual(len(friction.build_records(data)), 2)
        data["observations"].append({**copy.deepcopy(first), "key": "fourth"})
        with self.assertRaisesRegex(friction.EvidenceError, "at most three"):
            friction.build_records(data)

    def test_distinct_child_and_close_provenance_share_one_occurrence(self) -> None:
        data = capture()
        child = data["observations"][0]
        close_copy = copy.deepcopy(child)
        close_copy.update({
            "attempt_id": "parent-attempt",
            "parent_attempt_id": None,
            "reporter": data["reporter"],
            "actual_worker": data["actual_worker"],
            "source_observation_ref": friction._digest_id(
                data["repo_owner"], data["repo_name"], data["task_id"],
                "hidden-consumer", "child-attempt", "observation"),
        })
        data["observations"].append(close_copy)
        data["assessment"]["observation_keys"] = ["hidden-consumer"]
        records = friction.build_records(data)
        friction.prepare(data, self.outbox, STAMP)
        observations = [record for record in records if record["record_kind"] == "observation"]
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]["occurrence_id"], observations[1]["occurrence_id"])
        self.assertNotEqual(observations[0]["record_id"], observations[1]["record_id"])
        self.assertEqual(len(records[-1]["observation_refs"]), 1)

    def test_conflicting_repeated_occurrence_is_rejected(self) -> None:
        data = capture()
        other = copy.deepcopy(data["observations"][0])
        other.update({"attempt_id": "parent-attempt", "parent_attempt_id": None, "polarity": "positive"})
        data["observations"].append(other)
        with self.assertRaisesRegex(friction.EvidenceError, "conflicting"):
            friction.build_records(data)

    def test_parent_or_close_observation_needs_a_resolvable_source(self) -> None:
        data = capture()
        data["observations"][0]["reporter"] = person("close", "close-runner", "gpt-6-sol")
        with self.assertRaisesRegex(friction.EvidenceError, "reference their source"):
            friction.build_records(data)

    def test_unsaved_observation_cannot_be_used_as_assessment_or_parent_source(self) -> None:
        source_capture = capture()
        source_capture.pop("assessment")
        friction.prepare(source_capture, self.outbox, STAMP)
        source_id = friction.pending(self.outbox, STAMP)[0]["record_id"]
        friction.refuse(self.outbox, source_id, "access_denied")

        assessment_capture = copy.deepcopy(source_capture)
        assessment_capture["observations"] = []
        assessment_capture["assessment"] = copy.deepcopy(capture()["assessment"])
        assessment_capture["assessment"]["observation_keys"] = []
        assessment_capture["assessment"]["observation_refs"] = [source_id]
        with self.assertRaisesRegex(friction.EvidenceError, "pending or acknowledged"):
            friction.prepare(assessment_capture, self.outbox, STAMP)

        parent_capture = copy.deepcopy(source_capture)
        child = parent_capture["observations"][0]
        parent = copy.deepcopy(child)
        parent.update({"attempt_id": "parent-attempt", "parent_attempt_id": None,
                       "reporter": parent_capture["reporter"],
                       "actual_worker": parent_capture["actual_worker"],
                       "source_observation_ref": source_id})
        parent_capture["observations"] = [parent]
        with self.assertRaisesRegex(friction.EvidenceError, "pending or acknowledged"):
            friction.prepare(parent_capture, self.outbox, STAMP)

    def test_replaying_refused_source_does_not_overwrite_status_or_admit_dependent(self) -> None:
        source_capture = capture()
        source_capture.pop("assessment")
        friction.prepare(source_capture, self.outbox, STAMP)
        source_id = friction.pending(self.outbox, STAMP)[0]["record_id"]
        friction.refuse(self.outbox, source_id, "access_denied")
        friction.prepare(source_capture, self.outbox, STAMP)
        stored = next(entry for entry in friction._load(self.outbox)["entries"]
                      if entry["record_id"] == source_id)
        self.assertEqual(stored["status"], "unsaved")

        dependent = copy.deepcopy(source_capture)
        dependent["assessment"] = copy.deepcopy(capture()["assessment"])
        dependent["assessment"]["observation_keys"] = []
        dependent["assessment"]["observation_refs"] = [source_id]
        with self.assertRaisesRegex(friction.EvidenceError, "pending or acknowledged"):
            friction.prepare(dependent, self.outbox, STAMP)

    def test_refusing_pending_source_marks_pending_dependents_unsaved_transitively(self) -> None:
        data = capture()
        child = data["observations"][0]
        close_copy = copy.deepcopy(child)
        close_copy.update({
            "attempt_id": "parent-attempt", "parent_attempt_id": None,
            "reporter": data["reporter"], "actual_worker": data["actual_worker"],
            "source_observation_ref": friction._digest_id(
                data["repo_owner"], data["repo_name"], data["task_id"],
                "hidden-consumer", "child-attempt", "observation"),
        })
        data["observations"].append(close_copy)
        friction.prepare(data, self.outbox, STAMP)
        observation = next(item for item in friction.pending(self.outbox, STAMP)
                           if item["record_kind"] == "observation"
                           and item["request"]["record"]["attempt_id"] == "child-attempt")
        friction.refuse(self.outbox, observation["record_id"], "access_denied")

        self.assertEqual(friction.pending(self.outbox, STAMP), [])
        entries = friction._load(self.outbox)["entries"]
        dependent_records = [entry for entry in entries if entry["record_id"] != observation["record_id"]]
        self.assertTrue(dependent_records)
        self.assertTrue(all(entry["status"] == "unsaved" for entry in dependent_records))
        self.assertTrue(all(entry["refusal_reason"] == "access_denied" for entry in dependent_records))
        self.assertTrue(all(entry["dependency_reason"] == "source_refused" for entry in dependent_records))

    def test_unavailable_environment_only_makes_verify_not_assessable(self) -> None:
        data = capture()
        data["assessment"]["environment"] = "unavailable"
        data["assessment"]["ratings"][2] = {
            "dimension": "verify", "value": "not-assessable",
            "reason": "environment_unavailable", "evidence_refs": [],
        }
        ratings = friction.build_records(data)[-1]["ratings"]
        self.assertEqual([item["value"] for item in ratings], ["manageable", "difficult", "not-assessable"])

    def test_no_code_task_uses_explicit_not_applicable_ratings(self) -> None:
        data = capture()
        data["observations"] = []
        data["assessment"].update({"applicability": "not_applicable", "observation_keys": []})
        data["assessment"]["ratings"] = [
            {"dimension": name, "value": "not-assessable", "reason": "not_applicable", "evidence_refs": []}
            for name in ("locate", "understand", "verify")
        ]
        self.assertEqual(friction.build_records(data)[0]["applicability"], "not_applicable")
        data["assessment"]["ratings"][0]["value"] = "easy"
        with self.assertRaisesRegex(friction.EvidenceError, "not-applicable"):
            friction.build_records(data)

    def test_partial_or_aborted_work_cannot_claim_complete(self) -> None:
        data = capture()
        data["assessment"].update({"outcome": "partial", "completeness": "complete"})
        with self.assertRaisesRegex(friction.EvidenceError, "cannot claim a complete"):
            friction.build_records(data)
        data["assessment"].update({"outcome": "aborted", "completeness": "partial"})
        self.assertEqual(friction.build_records(data)[-1]["outcome"], "aborted")

    def test_raw_content_unknown_fields_and_private_locators_are_rejected(self) -> None:
        data = capture()
        data["transcript"] = "not accepted"
        with self.assertRaisesRegex(friction.EvidenceError, "unsupported fields"):
            friction.build_records(data)
        data = capture()
        data["observations"][0]["summary"] = "The issue was in /Users/person/private/file.ts"
        with self.assertRaisesRegex(friction.EvidenceError, "private locator"):
            friction.build_records(data)

    def test_punctuation_delimited_absolute_paths_are_rejected_but_relative_paths_are_allowed(self) -> None:
        for summary in (
            "The issue was in (/Users/synthetic/private/file.ts).",
            "The issue was in [/home/synthetic/private/file.ts].",
            'The issue was in "/private/tmp/example".',
            'The issue was in (C:\\Users\\synthetic\\private\\file.ts).',
        ):
            with self.subTest(summary=summary):
                data = capture()
                data["observations"][0]["summary"] = summary
                with self.assertRaisesRegex(friction.EvidenceError, "private locator"):
                    friction.build_records(data)
        data = capture()
        data["observations"][0]["summary"] = "The issue was in src/feature/module.ts."
        friction.build_records(data)

    def test_exact_replay_reuses_persisted_request_and_idempotency_key(self) -> None:
        data = capture()
        first = friction.prepare(data, self.outbox, STAMP)
        before = friction.pending(self.outbox, STAMP)
        second = friction.prepare(data, self.outbox, STAMP)
        after = friction.pending(self.outbox, STAMP)
        self.assertEqual(first["prepared"], 2)
        self.assertEqual(second["prepared"], 0)
        self.assertEqual(len(after), 2)
        self.assertEqual(before, after)
        self.assertEqual(before[0]["idempotency_key"], after[0]["idempotency_key"])
        self.assertEqual(self.outbox.stat().st_mode & 0o777, 0o600)

    def test_replay_cannot_change_bound_namespace_or_classification(self) -> None:
        data = capture()
        friction.prepare(data, self.outbox, STAMP)
        changed = copy.deepcopy(data)
        changed["namespace"] = "projects/another-repo"
        with self.assertRaisesRegex(friction.EvidenceError, "persisted namespace"):
            friction.prepare(changed, self.outbox, STAMP)
        changed = copy.deepcopy(data)
        changed["classification"] = "client-confidential"
        with self.assertRaisesRegex(friction.EvidenceError, "persisted classification"):
            friction.prepare(changed, self.outbox, STAMP)

    def test_ordinary_observation_replay_cannot_change_classification(self) -> None:
        data = capture()
        data.pop("assessment")
        friction.prepare(data, self.outbox, STAMP)
        changed = copy.deepcopy(data)
        changed["classification"] = "client-confidential"
        with self.assertRaisesRegex(friction.EvidenceError, "persisted classification"):
            friction.prepare(changed, self.outbox, STAMP)

    def test_partial_assessment_can_be_completed_only_as_explicit_correction(self) -> None:
        data = capture()
        data["assessment"].update({"outcome": "partial", "completeness": "partial"})
        friction.prepare(data, self.outbox, STAMP)
        assessment = next(item for item in friction.pending(self.outbox, STAMP)
                          if item["record_kind"] == "assessment")
        receipt = {
            "record_id": assessment["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        }
        friction.acknowledge(self.outbox, receipt)
        finalized = copy.deepcopy(data)
        finalized["assessment"].update({"outcome": "completed", "completeness": "complete",
                                        "correction_ref": "ref:final-assessment-evidence"})
        result = friction.prepare(finalized, self.outbox, STAMP)
        correction = next(item for item in friction.pending(self.outbox, STAMP)
                          if item["record_kind"] == "assessment")
        self.assertEqual(result["prepared"], 1)
        self.assertNotEqual(correction["record_id"], receipt["record_id"])
        self.assertEqual(correction["request"]["expected_updated_at"], receipt["updated_at"])
        corrected_record = correction["request"]["record"]
        self.assertEqual(corrected_record["supersedes_record_id"], receipt["record_id"])
        self.assertEqual(corrected_record["correction_ref"], "ref:final-assessment-evidence")
        self.assertEqual(corrected_record["observation_refs"], assessment["request"]["record"]["observation_refs"])
        before = friction.pending(self.outbox, STAMP)
        replay = friction.prepare(finalized, self.outbox, STAMP)
        self.assertEqual(replay["prepared"], 0)
        self.assertEqual(replay["replays"][0]["request"], correction["request"])
        self.assertEqual(before, friction.pending(self.outbox, STAMP))
        correction_receipt = {
            "record_id": correction["record_id"], "collected_at": "2026-10-10T12:00:01.123Z",
            "expires_at": "2027-04-10T12:00:01.789Z", "updated_at": "2026-10-10T12:00:01.456Z",
            "classification": "internal",
        }
        friction.acknowledge(self.outbox, correction_receipt)
        acknowledged_replay = friction.prepare(finalized, self.outbox, STAMP)
        self.assertEqual(acknowledged_replay["replays"][0]["receipt"], correction_receipt)

    def test_correction_classification_is_preserved_and_cannot_be_downgraded(self) -> None:
        data = capture()
        data["assessment"].update({"outcome": "partial", "completeness": "partial"})
        friction.prepare(data, self.outbox, STAMP)
        prior = next(item for item in friction.pending(self.outbox, STAMP)
                     if item["record_kind"] == "assessment")
        friction.acknowledge(self.outbox, {
            "record_id": prior["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        })

        raised = copy.deepcopy(data)
        raised["assessment"].update({"outcome": "completed", "completeness": "complete",
                                     "correction_ref": "ref:raised-classification"})
        raised["classification"] = "client-confidential"
        lower = copy.deepcopy(data)
        lower["assessment"].update({"outcome": "completed", "completeness": "complete",
                                    "correction_ref": "ref:lower-classification"})
        lower["classification"] = "public"
        with self.assertRaisesRegex(friction.EvidenceError, "cannot lower classification"):
            friction.prepare(lower, self.outbox, STAMP)

        friction.prepare(raised, self.outbox, STAMP)
        corrected = next(item for item in friction.pending(self.outbox, STAMP)
                         if item["record_kind"] == "assessment")
        self.assertEqual(corrected["request"]["classification"], "client-confidential")
        saved_request = copy.deepcopy(corrected["request"])
        self.assertEqual(friction.prepare(raised, self.outbox, STAMP)["prepared"], 0)
        self.assertEqual(friction.pending(self.outbox, STAMP)[-1]["request"], saved_request)

    def test_correction_without_classification_inherits_and_same_level_is_preserved(self) -> None:
        for selected in (None, "internal"):
            with self.subTest(selected=selected):
                outbox = Path(self.temp.name) / f"classification-{selected or 'absent'}" / "outbox.json"
                data = capture()
                data["assessment"].update({"outcome": "partial", "completeness": "partial"})
                friction.prepare(data, outbox, STAMP)
                prior = next(item for item in friction.pending(outbox, STAMP)
                             if item["record_kind"] == "assessment")
                friction.acknowledge(outbox, {
                    "record_id": prior["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
                    "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
                    "classification": "internal",
                })
                corrected = copy.deepcopy(data)
                corrected["assessment"].update({"outcome": "completed", "completeness": "complete",
                                                "correction_ref": f"ref:inherit-{selected or 'absent'}"})
                if selected is None:
                    corrected.pop("classification")
                else:
                    corrected["classification"] = selected
                friction.prepare(corrected, outbox, STAMP)
                request = next(item["request"] for item in friction.pending(outbox, STAMP)
                               if item["record_kind"] == "assessment")
                self.assertEqual(request["classification"], "internal")

    def test_changed_assessment_waits_for_uncertain_predecessor(self) -> None:
        data = capture()
        friction.prepare(data, self.outbox, STAMP)
        changed = copy.deepcopy(data)
        changed["assessment"]["correction_ref"] = "ref:correction-evidence"
        changed["assessment"]["ratings"][1]["value"] = "manageable"
        with self.assertRaisesRegex(friction.EvidenceError, "resolve the uncertain"):
            friction.prepare(changed, self.outbox, STAMP)

    def test_close_can_reference_prior_acknowledged_observation_without_recreating_it(self) -> None:
        data = capture()
        friction.prepare(data, self.outbox, STAMP)
        observation = next(item for item in friction.pending(self.outbox, STAMP)
                           if item["record_kind"] == "observation")
        receipt = {
            "record_id": observation["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        }
        friction.acknowledge(self.outbox, receipt)
        prior_assessment = next(item for item in friction.pending(self.outbox, STAMP)
                                if item["record_kind"] == "assessment")
        friction.acknowledge(self.outbox, {
            "record_id": prior_assessment["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        })
        close = copy.deepcopy(data)
        close["observations"] = []
        close["assessment"]["observation_keys"] = []
        close["assessment"]["observation_refs"] = [observation["record_id"]]
        # The terminal assessment is still the original exact replay; a changed
        # assessment needs its own explicit correction evidence.
        close["assessment"]["correction_ref"] = "ref:close-correction"
        close["assessment"]["outcome"] = "partial"
        close["assessment"]["completeness"] = "partial"
        result = friction.prepare(close, self.outbox, STAMP)
        self.assertEqual(result["prepared"], 1)
        assessment = next(item for item in friction.pending(self.outbox, STAMP)
                          if item["record_kind"] == "assessment")
        self.assertEqual(assessment["request"]["record"]["observation_refs"], [observation["record_id"]])
        self.assertEqual(len([item for item in friction._load(self.outbox)["entries"]
                              if item["record_kind"] == "observation"]), 1)

    def test_pending_read_does_not_create_an_assessment(self) -> None:
        data = capture()
        data.pop("assessment")
        friction.prepare(data, self.outbox, STAMP)
        records = [entry["request"]["record"] for entry in friction.pending(self.outbox, STAMP)]
        self.assertEqual([record["record_kind"] for record in records], ["observation"])

    def test_ack_retains_server_expiry_and_erases_payload(self) -> None:
        friction.prepare(capture(), self.outbox, STAMP)
        item = friction.pending(self.outbox, STAMP)[0]
        receipt = {
            "record_id": item["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        }
        friction.acknowledge(self.outbox, receipt)
        stored = friction._load(self.outbox)["entries"][0]
        self.assertEqual(stored["receipt"], receipt)
        self.assertNotIn("request", stored)
        self.assertEqual(item["request"], {
            "action": "append", "namespace": "projects/synthetic-repo",
            "idempotency_key": item["idempotency_key"],
            "record": item["request"]["record"], "classification": "internal",
        })
        friction.acknowledge(self.outbox, receipt)
        with self.assertRaisesRegex(friction.EvidenceError, "conflicts"):
            friction.acknowledge(self.outbox, {**receipt, "expires_at": "2027-01-01T00:00:00Z"})

    def test_terminal_refusal_is_not_retried_and_stays_unsaved(self) -> None:
        friction.prepare(capture(), self.outbox, STAMP)
        item = friction.pending(self.outbox, STAMP)[0]
        friction.refuse(self.outbox, item["record_id"], "classification_denied")
        with self.assertRaisesRegex(friction.EvidenceError, "pending or acknowledged"):
            friction.prepare(capture(), self.outbox, STAMP)
        pending = friction.pending(self.outbox, STAMP)
        self.assertNotIn(item["record_id"], {entry["record_id"] for entry in pending})
        record = next(x for x in friction._load(self.outbox)["entries"] if x["record_id"] == item["record_id"])
        self.assertEqual(record["status"], "unsaved")
        self.assertEqual(record["refusal_reason"], "classification_denied")

    def test_access_denied_is_terminal_and_does_not_loop(self) -> None:
        friction.prepare(capture(), self.outbox, STAMP)
        source = next(item for item in friction.pending(self.outbox, STAMP)
                      if item["record_kind"] == "observation")
        friction.refuse(self.outbox, source["record_id"], "access_denied")
        self.assertEqual(friction.pending(self.outbox, STAMP), [])

    def test_unsaved_payload_expires_after_thirty_days(self) -> None:
        data = capture()
        data["observed_at"] = "2026-09-01T00:00:00Z"
        for observation in data["observations"]:
            observation["observed_at"] = data["observed_at"]
        friction.prepare(data, self.outbox, "2026-09-01T00:00:00Z")
        self.assertEqual(friction.expire(self.outbox, STAMP), 2)
        self.assertEqual(friction.pending(self.outbox, STAMP), [])
        self.assertTrue(all("request" not in item and item["status"] == "expired"
                            for item in friction._load(self.outbox)["entries"]))

    def test_day31_exact_acknowledged_replay_returns_receipts_but_changes_and_expiry_fail(self) -> None:
        initial = capture()
        initial["observed_at"] = "2026-09-01T12:00:00Z"
        for observation in initial["observations"]:
            observation["observed_at"] = initial["observed_at"]
        day_zero = "2026-09-02T12:00:00Z"
        day_31 = "2026-10-02T12:00:00Z"
        friction.prepare(initial, self.outbox, day_zero)
        records = friction.pending(self.outbox, day_zero)
        for offset, item in enumerate(records):
            friction.acknowledge(self.outbox, {
                "record_id": item["record_id"], "collected_at": "2026-09-02T12:00:00.123Z",
                "expires_at": "2027-03-02T12:00:00.789Z",
                "updated_at": f"2026-09-02T12:00:0{offset}.456Z", "classification": "internal",
            })
        replay = friction.prepare(initial, self.outbox, day_31)
        self.assertEqual(replay["prepared"], 0)
        self.assertEqual({item["status"] for item in replay["replays"]}, {"acknowledged"})
        self.assertTrue(all("receipt" in item for item in replay["replays"]))
        self.assertEqual(friction.pending(self.outbox, day_31), [])

        altered_observation = copy.deepcopy(initial)
        altered_observation["observations"][0]["summary"] = "A changed summary is new evidence."
        with self.assertRaisesRegex(friction.EvidenceError, "older than 30 days"):
            friction.prepare(altered_observation, self.outbox, day_31)
        altered_assessment = copy.deepcopy(initial)
        altered_assessment["assessment"]["correction_ref"] = "ref:late-correction"
        altered_assessment["assessment"]["ratings"][1]["value"] = "manageable"
        with self.assertRaisesRegex(friction.EvidenceError, "older than 30 days"):
            friction.prepare(altered_assessment, self.outbox, day_31)

        expired_outbox = Path(self.temp.name) / "expired" / "outbox.json"
        friction.prepare(initial, expired_outbox, day_zero)
        for item in friction.pending(expired_outbox, day_zero):
            friction.acknowledge(expired_outbox, {
                "record_id": item["record_id"], "collected_at": "2026-09-02T12:00:00.123Z",
                "expires_at": day_31, "updated_at": "2026-09-02T12:00:00.456Z",
                "classification": "internal",
            })
        with self.assertRaisesRegex(friction.EvidenceError, "older than 30 days"):
            friction.prepare(initial, expired_outbox, day_31)
        self.assertEqual(friction._load(expired_outbox)["entries"], [])

    def test_acknowledged_metadata_is_erased_at_server_expiry(self) -> None:
        data = capture()
        data.pop("assessment")
        data["observations"] = data["observations"][:1]
        friction.prepare(data, self.outbox, STAMP)
        item = friction.pending(self.outbox, STAMP)[0]
        receipt = {
            "record_id": item["record_id"], "collected_at": "2026-10-10T12:00:00.123Z",
            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": "2026-10-10T12:00:00.456Z",
            "classification": "internal",
        }
        friction.acknowledge(self.outbox, receipt)
        self.assertEqual(friction.expire(self.outbox, "2027-04-10T12:00:00.788Z"), 0)
        self.assertEqual(friction.expire(self.outbox, "2027-04-10T12:00:00.789Z"), 1)
        self.assertEqual(friction._load(self.outbox)["entries"], [])

    def test_concurrent_child_prepares_do_not_drop_records_or_exceed_budget(self) -> None:
        inputs = []
        for index in range(4):
            data = capture()
            data.pop("assessment")
            data["observations"][0]["key"] = f"friction-{index}"
            path = Path(self.temp.name) / f"capture-{index}.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            inputs.append(path)
        script = Path(__file__).with_name("code-friction.py")
        def run(path: Path) -> subprocess.CompletedProcess:
            return subprocess.run([sys.executable, str(script), "prepare", str(path), str(self.outbox)],
                                  capture_output=True, text=True, check=False)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(run, inputs))
        self.assertEqual(sorted(result.returncode for result in results), [0, 0, 0, 2],
                         [result.stderr for result in results])
        self.assertEqual(len(friction.pending(self.outbox, STAMP)), 3)
        self.assertEqual(self.outbox.with_name(self.outbox.name + ".lock").stat().st_mode & 0o777, 0o600)

    def test_global_entry_limit_rejects_new_evidence_without_eviction(self) -> None:
        state = {"version": "1.0", "entries": []}
        receipt_time = "2026-10-10T12:00:00.123Z"
        for index in range(friction.MAX_OUTBOX_ENTRIES):
            record_id = f"ref:record-{index}"
            state["entries"].append({
                "record_id": record_id, "record_kind": "observation",
                "idempotency_key": str(uuid.uuid4()), "captured_at": STAMP,
                "status": "acknowledged", "task_identity": ["Magnus-Gille", "old-repo", "old-task"],
                "occurrence_id": None, "observed_at": STAMP,
                "worker_fingerprint": "0" * 64, "attempt_id": "attempt",
                "namespace": "projects/old-repo", "payload_fingerprint": "1" * 64,
                "supersedes_record_id": None, "assessment_fingerprint": None, "correction_ref": None,
                "receipt": {"record_id": record_id, "collected_at": receipt_time,
                            "expires_at": "2027-04-10T12:00:00.789Z", "updated_at": receipt_time,
                            "classification": "internal"},
            })
        friction._save(self.outbox, state)
        with self.assertRaisesRegex(friction.EvidenceError, "capacity reached \(1024 entries\)"):
            friction.prepare(capture(), self.outbox, STAMP)
        self.assertEqual(len(friction._load(self.outbox)["entries"]), friction.MAX_OUTBOX_ENTRIES)

    def test_oversized_outbox_is_rejected_before_json_read_or_persist(self) -> None:
        self.outbox.parent.mkdir(mode=0o700, parents=True)
        self.outbox.write_bytes(b"{" + b" " * friction.MAX_OUTBOX_BYTES)
        self.outbox.chmod(0o600)
        with self.assertRaisesRegex(friction.EvidenceError, "4 MiB read limit"):
            friction.pending(self.outbox, STAMP)
        self.assertEqual(self.outbox.stat().st_size, friction.MAX_OUTBOX_BYTES + 1)

        new_path = Path(self.temp.name) / "save" / "outbox.json"
        huge_state = {"version": "1.0", "entries": [], "padding": "x" * friction.MAX_OUTBOX_BYTES}
        with self.assertRaisesRegex(friction.EvidenceError, "capacity reached \(4 MiB\)"):
            friction._save(new_path, huge_state)
        self.assertFalse(new_path.exists())

    def test_stale_and_future_evidence_cannot_be_prepared(self) -> None:
        data = capture()
        with self.assertRaisesRegex(friction.EvidenceError, "future evidence"):
            friction.prepare(data, self.outbox, "2026-10-09T00:00:00Z")
        data["observed_at"] = "2026-09-01T00:00:00Z"
        for observation in data["observations"]:
            observation["observed_at"] = data["observed_at"]
        with self.assertRaisesRegex(friction.EvidenceError, "older than 30 days"):
            friction.prepare(data, self.outbox, STAMP)

    def test_persistence_failure_blocks_preparation_and_submission(self) -> None:
        with patch.object(friction, "_save", side_effect=friction.EvidenceError("synthetic disk error")):
            with self.assertRaises(friction.EvidenceError):
                friction.prepare(capture(), self.outbox, STAMP)
        self.assertEqual(friction.pending(self.outbox, STAMP), [])


if __name__ == "__main__":
    unittest.main()
