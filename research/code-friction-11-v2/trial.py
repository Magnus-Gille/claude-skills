#!/usr/bin/env python3
"""Validate and aggregate the code-friction-11 research fixtures.

This is intentionally dependency-free and research-only. It validates the
shape and provenance of evaluator records; it does not decide whether a
rating or evidence claim is substantively correct.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path
from typing import Any


DIMENSIONS = ("locate", "understand", "verify")
RATINGS = ("easy", "manageable", "difficult", "not-assessable")
FRICTION = ("code", "environment", "mixed", "not_applicable")
APPLICABILITY = ("applicable", "not_applicable")
TASK_STATUS = ("planned", "completed", "partial", "failed", "aborted", "qa_only")
OBSERVATION_KINDS = ("direct", "child", "parent", "close_retry")
POLARITIES = ("positive", "negative")


class ValidationError(ValueError):
    """Raised when a fixture cannot be safely aggregated."""


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read JSON {path}: {exc}") from exc


def _require(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping:
        raise ValidationError(f"{context}: missing {key}")
    return mapping[key]


def _string(value: Any, field: str, *, allow_unknown: bool = False) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field}: expected non-empty string")
    if value == "unknown" and not allow_unknown:
        raise ValidationError(f"{field}: unknown is not allowed here")
    return value


def _telemetry(value: Any, field: str, *, numeric: bool = False) -> Any:
    if value == "unknown":
        return value
    if numeric:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise ValidationError(f"{field}: expected non-negative number or unknown")
        return value
    return _string(value, field, allow_unknown=True)


def load_packet(packet_dir: Path) -> dict[str, Any]:
    packet_dir = packet_dir.resolve()
    manifest = read_json(packet_dir / "manifest.json")
    files = _require(manifest, "files", "packet manifest")
    if not isinstance(files, list) or not files:
        raise ValidationError("packet manifest: files must be a non-empty list")
    for relative in files:
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            raise ValidationError(f"packet manifest: unsafe file path {relative!r}")
        if not (packet_dir / relative).is_file():
            raise ValidationError(f"packet manifest: missing file {relative}")
    scenarios = read_json(packet_dir / "scenarios.json")
    validate_packet(scenarios)
    return scenarios


def validate_packet(packet: dict[str, Any]) -> None:
    if _require(packet, "packet_version", "packet") != "code-friction-11.scenarios.v2":
        raise ValidationError("packet: unsupported packet_version")
    scenarios = _require(packet, "scenarios", "packet")
    if not isinstance(scenarios, list) or not scenarios:
        raise ValidationError("packet: scenarios must be a non-empty list")
    ids: set[str] = set()
    anchors: dict[str, set[str]] = {}
    pairs: dict[str, list[str]] = {}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise ValidationError("packet: each scenario must be an object")
        sid = _string(_require(scenario, "id", "scenario"), "scenario.id")
        if sid in ids:
            raise ValidationError(f"packet: duplicate scenario id {sid}")
        ids.add(sid)
        _string(_require(scenario, "task", sid), f"{sid}.task")
        files = _require(scenario, "files", sid)
        if not isinstance(files, list) or not files:
            raise ValidationError(f"{sid}: files must be a non-empty list")
        seen_paths: set[str] = set()
        for item in files:
            path = _string(_require(item, "path", sid), f"{sid}.file.path")
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValidationError(f"{sid}: unsafe synthetic path {path}")
            if path in seen_paths:
                raise ValidationError(f"{sid}: duplicate synthetic path {path}")
            seen_paths.add(path)
            _string(_require(item, "content", sid), f"{sid}.{path}.content")
        scenario_anchors = _require(scenario, "anchors", sid)
        if not isinstance(scenario_anchors, list) or not scenario_anchors:
            raise ValidationError(f"{sid}: anchors must be a non-empty list")
        anchor_ids: set[str] = set()
        for anchor in scenario_anchors:
            aid = _string(_require(anchor, "id", sid), f"{sid}.anchor.id")
            if aid in anchor_ids:
                raise ValidationError(f"{sid}: duplicate anchor id {aid}")
            anchor_ids.add(aid)
            path = _string(_require(anchor, "path", sid), f"{sid}.anchor.path")
            if path not in seen_paths:
                raise ValidationError(f"{sid}: anchor {aid} names unknown path {path}")
        anchors[sid] = anchor_ids
        pair_id = scenario.get("pair_id")
        if pair_id is not None:
            pairs.setdefault(_string(pair_id, f"{sid}.pair_id"), []).append(sid)
        env = _require(scenario, "environment", sid)
        if _require(env, "status", f"{sid}.environment") not in ("available", "unavailable", "partial", "unknown"):
            raise ValidationError(f"{sid}: invalid environment status")
    for pair_id, members in pairs.items():
        if len(members) != 2:
            raise ValidationError(f"pair {pair_id}: expected exactly two scenarios, got {members}")


def _validate_rating(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise ValidationError(f"{field}: expected object")
    rating = _string(_require(value, "rating", field), f"{field}.rating")
    if rating not in RATINGS:
        raise ValidationError(f"{field}.rating: invalid value {rating}")
    friction = _string(_require(value, "friction_class", field), f"{field}.friction_class")
    if friction not in FRICTION:
        raise ValidationError(f"{field}.friction_class: invalid value {friction}")
    _string(_require(value, "reason", field), f"{field}.reason")
    return {"rating": rating, "friction_class": friction}


def validate_evaluation(evaluation: dict[str, Any], packet: dict[str, Any]) -> None:
    if not isinstance(evaluation, dict):
        raise ValidationError("evaluation: expected object")
    sid = _string(_require(evaluation, "scenario_id", "evaluation"), "evaluation.scenario_id")
    scenarios = {item["id"]: item for item in packet["scenarios"]}
    if sid not in scenarios:
        raise ValidationError(f"evaluation: unknown scenario {sid}")
    for field in ("schema_version", "evaluation_id", "evaluator_id"):
        _string(_require(evaluation, field, "evaluation"), f"evaluation.{field}")
    if evaluation["schema_version"] != "code-friction-11.eval.v1":
        raise ValidationError("evaluation.schema_version: unsupported version")
    for field in ("requested_model", "requested_effort", "observed_model", "observed_effort"):
        _telemetry(_require(evaluation, field, "evaluation"), f"evaluation.{field}")
    for field in ("elapsed_seconds", "input_tokens", "output_tokens"):
        _telemetry(evaluation.get(field, "unknown"), f"evaluation.{field}", numeric=True)
    status = _string(_require(evaluation, "task_status", "evaluation"), "evaluation.task_status")
    if status not in TASK_STATUS:
        raise ValidationError(f"evaluation.task_status: invalid value {status}")
    completion = _require(evaluation, "completion_claim", "evaluation")
    if not isinstance(completion, bool):
        raise ValidationError("evaluation.completion_claim: expected boolean")
    if status in ("partial", "failed", "aborted") and completion:
        raise ValidationError("evaluation: incomplete task cannot claim completion")
    applicability = _string(_require(evaluation, "applicability", "evaluation"), "evaluation.applicability")
    if applicability not in APPLICABILITY:
        raise ValidationError(f"evaluation.applicability: invalid value {applicability}")
    environment = _require(evaluation, "environment", "evaluation")
    env_status = _string(_require(environment, "status", "evaluation.environment"), "evaluation.environment.status")
    if env_status not in ("available", "unavailable", "partial", "unknown"):
        raise ValidationError("evaluation.environment.status: invalid value")
    env_class = _string(_require(environment, "friction_class", "evaluation.environment"), "evaluation.environment.friction_class")
    if env_class not in FRICTION:
        raise ValidationError("evaluation.environment.friction_class: invalid value")
    _string(_require(environment, "notes", "evaluation.environment"), "evaluation.environment.notes")
    ratings = _require(evaluation, "ratings", "evaluation")
    if not isinstance(ratings, dict) or set(ratings) != set(DIMENSIONS):
        raise ValidationError("evaluation.ratings: must contain locate, understand, verify only")
    for dimension in DIMENSIONS:
        _validate_rating(ratings[dimension], f"evaluation.ratings.{dimension}")
    observations = _require(evaluation, "observations", "evaluation")
    if not isinstance(observations, list) or len(observations) > 3:
        raise ValidationError("evaluation.observations: expected a list of at most three")
    anchor_ids = {
        anchor["id"]
        for item in packet["scenarios"]
        if item["id"] == sid
        for anchor in item["anchors"]
    }
    observation_ids: set[str] = set()
    for observation in observations:
        oid = _string(_require(observation, "observation_id", sid), f"{sid}.observation_id")
        if oid in observation_ids:
            raise ValidationError(f"{sid}: duplicate observation_id {oid}")
        observation_ids.add(oid)
        _string(_require(observation, "occurrence_id", sid), f"{sid}.occurrence_id")
        polarity = _string(_require(observation, "polarity", oid), f"{oid}.polarity")
        if polarity not in POLARITIES:
            raise ValidationError(f"{oid}.polarity: invalid value")
        dimension = _string(_require(observation, "dimension", oid), f"{oid}.dimension")
        if dimension not in DIMENSIONS:
            raise ValidationError(f"{oid}.dimension: invalid value")
        _string(_require(observation, "claim", oid), f"{oid}.claim")
        refs = _require(observation, "evidence_refs", oid)
        if not isinstance(refs, list) or not refs:
            raise ValidationError(f"{oid}.evidence_refs: expected a non-empty list")
        for ref in refs:
            if ref not in anchor_ids:
                raise ValidationError(f"{oid}: unknown evidence ref {ref}")
        source = _require(observation, "source", oid)
        kind = _string(_require(source, "kind", oid), f"{oid}.source.kind")
        if kind not in OBSERVATION_KINDS:
            raise ValidationError(f"{oid}.source.kind: invalid value")
        _string(_require(source, "attempt_id", oid), f"{oid}.source.attempt_id")
        parent = source.get("parent_observation_id")
        if parent is not None:
            _string(parent, f"{oid}.source.parent_observation_id")
    scenario = scenarios[sid]
    if scenario["kind"] == "qa":
        if status != "qa_only" or applicability != "not_applicable":
            raise ValidationError("qa scenario must be qa_only and not_applicable")
        if env_class != "not_applicable":
            raise ValidationError("qa scenario must use not_applicable friction class")
        if any(_validate_rating(ratings[d], f"evaluation.ratings.{d}")["rating"] != "not-assessable" for d in DIMENSIONS):
            raise ValidationError("qa scenario must use not-assessable ratings")
    elif applicability != "applicable":
        raise ValidationError("implementation scenario must be applicable")
    if env_status == "unavailable" and ratings["verify"]["rating"] != "not-assessable":
        raise ValidationError("unavailable environment must make verification not-assessable")


def deduplicate_observations(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for evaluation in evaluations:
        sid = evaluation["scenario_id"]
        for observation in evaluation["observations"]:
            occurrence_id = observation["occurrence_id"]
            key = f"{sid}:{occurrence_id}"
            entry = grouped.setdefault(
                key,
                {
                    "scenario_id": sid,
                    "occurrence_id": occurrence_id,
                    "count": 1,
                    "observation_ids": [],
                    "evaluation_ids": [],
                    "source_kinds": [],
                    "provenance": [],
                    "claims": [],
                    "dimensions": [],
                    "polarities": [],
                    "evidence_refs": [],
                    "collision": False,
                },
            )
            if entry["observation_ids"]:
                entry["count"] += 1
            entry["observation_ids"].append(observation["observation_id"])
            entry["evaluation_ids"].append(evaluation["evaluation_id"])
            entry["source_kinds"].append(observation["source"]["kind"])
            entry["provenance"].append({
                "evaluation_id": evaluation["evaluation_id"],
                "observation_id": observation["observation_id"],
                "source": observation["source"],
            })
            entry["claims"].append(observation["claim"])
            entry["dimensions"].append(observation["dimension"])
            entry["polarities"].append(observation["polarity"])
            entry["evidence_refs"].extend(observation["evidence_refs"])
            if len(set(entry["dimensions"])) > 1 or len(set(entry["polarities"])) > 1:
                entry["collision"] = True
    return {"unique_occurrences": len(grouped), "occurrences": list(grouped.values())}


def load_evaluations(paths: list[Path]) -> list[dict[str, Any]]:
    """Load either one evaluation object or an array of evaluations per path."""
    evaluations: list[dict[str, Any]] = []
    for path in paths:
        value = read_json(path)
        if isinstance(value, list):
            evaluations.extend(value)
        else:
            evaluations.append(value)
    return evaluations


def _median(values: list[int | float]) -> int | float | str:
    return statistics.median(values) if values else "unknown"


def aggregate(evaluations: list[dict[str, Any]], packet: dict[str, Any], expected_per_scenario: int = 2) -> dict[str, Any]:
    validate_packet(packet)
    if expected_per_scenario < 1:
        raise ValidationError("expected_per_scenario must be positive")
    for evaluation in evaluations:
        validate_evaluation(evaluation, packet)
    scenario_ids = [item["id"] for item in packet["scenarios"]]
    grouped: dict[str, list[dict[str, Any]]] = {sid: [] for sid in scenario_ids}
    for evaluation in evaluations:
        grouped[evaluation["scenario_id"]].append(evaluation)
    for sid, items in grouped.items():
        if len(items) != expected_per_scenario:
            raise ValidationError(f"{sid}: expected {expected_per_scenario} evaluations, got {len(items)}")
        evaluator_ids = [item["evaluator_id"] for item in items]
        evaluation_ids = [item["evaluation_id"] for item in items]
        if len(set(evaluator_ids)) != len(evaluator_ids):
            raise ValidationError(f"{sid}: duplicate evaluator_id")
        if len(set(evaluation_ids)) != len(evaluation_ids):
            raise ValidationError(f"{sid}: duplicate evaluation_id")
        requested = {(item["requested_model"], item["requested_effort"]) for item in items}
        if len(requested) != 1:
            raise ValidationError(f"{sid}: requested model/effort differs between evaluators")
    scenario_reports: list[dict[str, Any]] = []
    for sid in scenario_ids:
        items = grouped[sid]
        dimensions: dict[str, Any] = {}
        for dimension in DIMENSIONS:
            ratings = [item["ratings"][dimension]["rating"] for item in items]
            dimensions[dimension] = {"ratings": ratings, "agreement": len(set(ratings)) == 1}
        numeric_time = [item.get("elapsed_seconds", "unknown") for item in items if item.get("elapsed_seconds", "unknown") != "unknown"]
        numeric_input = [item.get("input_tokens", "unknown") for item in items if item.get("input_tokens", "unknown") != "unknown"]
        numeric_output = [item.get("output_tokens", "unknown") for item in items if item.get("output_tokens", "unknown") != "unknown"]
        scenario_reports.append({
            "scenario_id": sid,
            "evaluations": [item["evaluation_id"] for item in items],
            "dimensions": dimensions,
            "friction_classes": [item["environment"]["friction_class"] for item in items],
            "environment_statuses": [item["environment"]["status"] for item in items],
            "overhead": {
                "elapsed_seconds_median": _median(numeric_time),
                "elapsed_seconds_n": len(numeric_time),
                "input_tokens_median": _median(numeric_input),
                "input_tokens_n": len(numeric_input),
                "output_tokens_median": _median(numeric_output),
                "output_tokens_n": len(numeric_output),
            },
        })
    observations = deduplicate_observations(evaluations)
    return {
        "report_version": "code-friction-11.aggregate.v2",
        "evaluation_count": len(evaluations),
        "scenario_count": len(scenario_reports),
        "scenario_reports": scenario_reports,
        "deduplicated_observations": observations,
    }


def freeze(packet_dir: Path, output: Path) -> None:
    packet_dir = packet_dir.resolve()
    manifest = read_json(packet_dir / "manifest.json")
    files = []
    for relative in manifest["files"]:
        path = packet_dir / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        files.append({"path": relative, "sha256": digest, "bytes": path.stat().st_size})
    frozen = {
        "freeze_version": "code-friction-11.freeze.v2",
        "packet_version": manifest.get("packet_version"),
        "files": files,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze_parser = subparsers.add_parser("freeze")
    freeze_parser.add_argument("--packet", type=Path, required=True)
    freeze_parser.add_argument("--output", type=Path, required=True)
    aggregate_parser = subparsers.add_parser("aggregate")
    aggregate_parser.add_argument("--packet", type=Path, required=True)
    aggregate_parser.add_argument("--evaluations", type=Path, nargs="+", required=True)
    aggregate_parser.add_argument("--output", type=Path, required=True)
    aggregate_parser.add_argument("--expected-per-scenario", type=int, default=2)
    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            freeze(args.packet, args.output)
        else:
            packet = load_packet(args.packet)
            evaluations = load_evaluations(args.evaluations)
            report = aggregate(evaluations, packet, args.expected_per_scenario)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except ValidationError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

