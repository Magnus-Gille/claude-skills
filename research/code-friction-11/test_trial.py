#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("code_friction_trial", ROOT / "trial.py")
TRIAL = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(TRIAL)


def packet():
    return TRIAL.load_packet(ROOT / "packet")


def evaluation(scenario_id, *, evaluator_id="evaluator-a", evaluation_id=None, status="completed", applicability="applicable", env_status="available", env_class="code"):
    if evaluation_id is None:
        evaluation_id = f"{evaluator_id}-{scenario_id}"
    scenario = next(item for item in packet()["scenarios"] if item["id"] == scenario_id)
    anchors = [anchor["id"] for anchor in scenario["anchors"]]
    qa = scenario["kind"] == "qa"
    if qa:
        applicability = "not_applicable"
        status = "qa_only"
        env_class = "not_applicable"
        ratings = {dimension: {"rating": "not-assessable", "friction_class": "not_applicable", "reason": "No implementation change is requested."} for dimension in TRIAL.DIMENSIONS}
    else:
        ratings = {dimension: {"rating": "manageable", "friction_class": "code", "reason": "Synthetic evidence supports a bounded assessment."} for dimension in TRIAL.DIMENSIONS}
    return {
        "schema_version": "code-friction-11.eval.v1",
        "evaluation_id": evaluation_id,
        "evaluator_id": evaluator_id,
        "scenario_id": scenario_id,
        "requested_model": "Luna High",
        "requested_effort": "high",
        "observed_model": "unknown",
        "observed_effort": "unknown",
        "elapsed_seconds": "unknown",
        "input_tokens": "unknown",
        "output_tokens": "unknown",
        "task_status": status,
        "completion_claim": status in ("completed", "planned", "qa_only"),
        "applicability": applicability,
        "environment": {"status": env_status, "friction_class": env_class, "notes": "Synthetic test fixture."},
        "ratings": ratings,
        "observations": [{
            "observation_id": f"{evaluation_id}-obs",
            "occurrence_id": f"{scenario_id}:occ-1",
            "polarity": "positive",
            "dimension": "locate",
            "claim": "The supplied source identifies the relevant location.",
            "evidence_refs": [anchors[0]],
            "source": {"kind": "direct", "attempt_id": "attempt-1", "parent_observation_id": None},
        }],
    }


class TrialTests(unittest.TestCase):
    def test_packet_is_valid_and_freeze_is_deterministic(self):
        data = packet()
        self.assertEqual(len(data["scenarios"]), 8)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "frozen.json"
            TRIAL.freeze(ROOT / "packet", output)
            frozen = json.loads(output.read_text())
            self.assertEqual(len(frozen["files"]), 3)
            self.assertTrue(all(len(item["sha256"]) == 64 for item in frozen["files"]))

    def test_partial_task_cannot_claim_completion(self):
        item = evaluation("S5-failed-aborted", status="partial")
        item["completion_claim"] = True
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.validate_evaluation(item, packet())

    def test_unavailable_environment_requires_not_assessable_verification(self):
        item = evaluation("S4-unavailable-test-env", env_status="unavailable", env_class="environment")
        item["ratings"]["verify"]["rating"] = "manageable"
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.validate_evaluation(item, packet())

    def test_qa_requires_explicit_not_applicable(self):
        item = evaluation("S6-qa")
        item["applicability"] = "applicable"
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.validate_evaluation(item, packet())

    def test_observation_limit_and_anchor_validation(self):
        item = evaluation("S1-straightforward")
        item["observations"] *= 4
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.validate_evaluation(item, packet())
        item = evaluation("S1-straightforward")
        item["observations"][0]["evidence_refs"] = ["hidden-anchor"]
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.validate_evaluation(item, packet())

    def test_one_observation_may_cite_more_than_three_anchors(self):
        item = evaluation("S2-scattered")
        item["observations"][0]["evidence_refs"] = [
            anchor["id"]
            for anchor in next(s for s in packet()["scenarios"] if s["id"] == "S2-scattered")["anchors"]
        ]
        TRIAL.validate_evaluation(item, packet())

    def test_load_evaluations_accepts_json_arrays(self):
        first = evaluation("S1-straightforward", evaluator_id="array-a")
        second = evaluation("S1-straightforward", evaluator_id="array-b")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluations.json"
            path.write_text(json.dumps([first, second]), encoding="utf-8")
            loaded = TRIAL.load_evaluations([path])
        self.assertEqual([item["evaluator_id"] for item in loaded], ["array-a", "array-b"])

    def test_parent_child_and_close_retry_count_once(self):
        evaluations = []
        for scenario in packet()["scenarios"]:
            evaluations.extend([
                evaluation(scenario["id"], evaluator_id="evaluator-a"),
                evaluation(scenario["id"], evaluator_id="evaluator-b"),
            ])
        first = next(item for item in evaluations if item["scenario_id"] == "S5-failed-aborted" and item["evaluator_id"] == "evaluator-a")
        second = next(item for item in evaluations if item["scenario_id"] == "S5-failed-aborted" and item["evaluator_id"] == "evaluator-b")
        first["observations"][0]["occurrence_id"] = "queue-cleanup"
        second["observations"][0]["occurrence_id"] = "queue-cleanup"
        first["observations"][0]["source"] = {"kind": "child", "attempt_id": "child-attempt", "parent_observation_id": "parent-obs"}
        second["observations"][0]["source"] = {"kind": "close_retry", "attempt_id": "close-attempt-2", "parent_observation_id": None}
        report = TRIAL.aggregate(evaluations, packet())
        dedup = report["deduplicated_observations"]
        self.assertEqual(dedup["unique_occurrences"], len(packet()["scenarios"]))
        occurrence = next(item for item in dedup["occurrences"] if item["occurrence_id"] == "queue-cleanup")
        self.assertEqual(occurrence["count"], 2)
        self.assertEqual(set(occurrence["source_kinds"]), {"child", "close_retry"})

    def test_aggregate_requires_two_distinct_evaluators(self):
        first = evaluation("S1-straightforward", evaluator_id="same")
        second = evaluation("S1-straightforward", evaluator_id="same", evaluation_id="second")
        with self.assertRaises(TRIAL.ValidationError):
            TRIAL.aggregate([first, second], packet())


if __name__ == "__main__":
    unittest.main()

