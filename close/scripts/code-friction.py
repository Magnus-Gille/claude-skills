#!/usr/bin/env python3
"""Prepare and retain bounded code-friction evidence for explicit Close use.

This helper never contacts Munin. It creates a private, durable request before
the caller invokes memory_code_health, then records the exact receipt or a
terminal unsaved outcome. The outbox is an idempotency/recovery boundary, not a
second evidence database.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


REF = re.compile(r"^ref:[a-z0-9][a-z0-9-]{0,95}$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
IDENT = re.compile(r"^[a-z0-9][a-z0-9._-]{0,95}$")
KEY = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
SHA = re.compile(r"^[a-f0-9]{40}$")
TIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:[0-5]\dZ$")
REAL_INSTANT = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:[0-5]\d(?:\.\d{3})?Z$")
PRIVATE_TEXT = re.compile(
    r"(?:https?|file|ssh|ftp)://|```|`|-----BEGIN |(?:^|\s)(?:~/|/Users/|/home/|/private/|/tmp/|/var/)|"
    r"(?:^|\s)[A-Za-z]:\\|(?:^|\s)[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
    r"\b(?:Bearer|api[_ -]?key|password|secret|token)\s*[:=]",
    re.IGNORECASE,
)

ROOT_KEYS = {
    "repo_owner", "repo_name", "task_id", "task_class", "attempt_id",
    "parent_attempt_id", "child_attempt_ids", "observed_at", "before_sha",
    "after_sha", "module_refs", "reporter", "actual_worker", "observations",
    "assessment",
}
CAPTURE_KEYS = ROOT_KEYS | {"namespace", "classification"}
TASK_CLASSES = {"implementation", "refactor", "test", "docs", "investigation", "qa"}
DIMENSIONS = {"locate", "understand", "verify"}
RATINGS = {"easy", "manageable", "difficult", "not-assessable"}
CAUSES = {"code", "environment", "mixed"}
POLARITIES = {"positive", "negative"}
MAX_OUTBOX_ENTRIES = 1024
MAX_OUTBOX_BYTES = 4 * 1024 * 1024


class EvidenceError(ValueError):
    pass


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def _keys(value: dict[str, Any], allowed: set[str], required: set[str], label: str) -> None:
    _need(isinstance(value, dict), f"{label} must be an object")
    _need(not (set(value) - allowed), f"{label} has unsupported fields")
    _need(required <= set(value), f"{label} is missing required fields")


def _token(value: Any, label: str) -> None:
    _need(isinstance(value, str) and TOKEN.fullmatch(value) is not None, f"{label} is invalid")


def _ref(value: Any, label: str) -> None:
    _need(isinstance(value, str) and REF.fullmatch(value) is not None, f"{label} must be an opaque ref")


def _id(value: Any, label: str) -> None:
    _need(isinstance(value, str) and IDENT.fullmatch(value) is not None, f"{label} is invalid")


def _timestamp(value: Any, label: str) -> None:
    _need(isinstance(value, str) and TIME.fullmatch(value) is not None, f"{label} must be whole-second UTC")
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise EvidenceError(f"{label} is not a real timestamp") from exc


def _receipt_instant(value: Any, label: str) -> datetime:
    """Validate Munin's ISO UTC instant while preserving its original spelling."""
    _need(isinstance(value, str) and REAL_INSTANT.fullmatch(value) is not None,
          f"{label} must be an ISO UTC instant")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"{label} is not a real timestamp") from exc


def _optional_sha(value: Any, label: str) -> None:
    _need(value is None or (isinstance(value, str) and SHA.fullmatch(value) is not None), f"{label} is invalid")


def _refs(value: Any, label: str, minimum: int = 0, maximum: int = 16) -> None:
    _need(isinstance(value, list) and minimum <= len(value) <= maximum, f"{label} has an invalid size")
    _need(len(set(value)) == len(value), f"{label} must be unique")
    for item in value:
        _ref(item, label)


def _person(value: Any, label: str, kinds: set[str]) -> None:
    _keys(value, {"id", "kind", "requested_model", "observed_model", "observed_effort"},
          {"id", "kind", "requested_model", "observed_model", "observed_effort"}, label)
    _ref(value["id"], f"{label}.id")
    _need(value["kind"] in kinds, f"{label}.kind is invalid")
    for key in ("requested_model", "observed_model", "observed_effort"):
        _need(value[key] is None or (isinstance(value[key], str) and TOKEN.fullmatch(value[key]) is not None),
              f"{label}.{key} is invalid")


def _lineage(task: dict[str, Any], label: str) -> None:
    _id(task["task_id"], f"{label}.task_id")
    _id(task["attempt_id"], f"{label}.attempt_id")
    _need(task["parent_attempt_id"] is None or IDENT.fullmatch(task["parent_attempt_id"]) is not None,
          f"{label}.parent_attempt_id is invalid")
    children = task.get("child_attempt_ids", [])
    _need(isinstance(children, list) and len(children) <= 128, f"{label}.child_attempt_ids is invalid")
    _need(len(children) == len(set(children)), f"{label}.child_attempt_ids must be unique")
    for child in children:
        _id(child, f"{label}.child_attempt_ids item")


def _safe_summary(value: Any) -> None:
    _need(isinstance(value, str) and len(value) <= 280, "summary must be at most 280 characters")
    _need("\n" not in value and "\r" not in value and PRIVATE_TEXT.search(value) is None,
          "summary appears to contain raw content or a private locator")


def _digest_id(*parts: str, prefix: str = "ch") -> str:
    material = "\0".join(parts).encode("utf-8")
    return f"ref:{prefix}-{hashlib.sha256(material).hexdigest()[:32]}"


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _worker_fingerprint(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _base_record(data: dict[str, Any], attempt_id: str, parent_attempt_id: str | None,
                 reporter: dict[str, Any], actual_worker: dict[str, Any], observed_at: str,
                 before_sha: str | None, after_sha: str | None) -> dict[str, Any]:
    return {
        "version": "1.0",
        "repo_owner": data["repo_owner"],
        "repo_name": data["repo_name"],
        "task_id": data["task_id"],
        "task_class": data["task_class"],
        "attempt_id": attempt_id,
        "parent_attempt_id": parent_attempt_id,
        "record_id": "",
        "observed_at": observed_at,
        "before_sha": before_sha,
        "after_sha": after_sha,
        "module_refs": data["module_refs"],
        "reporter": reporter,
        "actual_worker": actual_worker,
        "supersedes_record_id": None,
        "correction_ref": None,
    }


def build_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    _keys(data, CAPTURE_KEYS, ROOT_KEYS - {"assessment"}, "capture")
    _need(data["task_class"] in TASK_CLASSES, "task_class is invalid")
    _need(isinstance(data["repo_owner"], str) and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?", data["repo_owner"]) is not None,
          "repo_owner is invalid")
    _need(isinstance(data["repo_name"], str) and re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,97}[A-Za-z0-9])?", data["repo_name"]) is not None,
          "repo_name is invalid")
    _lineage(data, "capture")
    _timestamp(data["observed_at"], "observed_at")
    _optional_sha(data["before_sha"], "before_sha")
    _optional_sha(data["after_sha"], "after_sha")
    _refs(data["module_refs"], "module_refs", maximum=16)
    _person(data["reporter"], "reporter", {"worker", "parent", "close"})
    _person(data["actual_worker"], "actual_worker", {"worker"})
    _need(data["attempt_id"] != data["parent_attempt_id"], "attempt cannot be its own parent")
    _need(data["attempt_id"] not in data["child_attempt_ids"], "attempt cannot list itself as a child")

    raw_observations = data["observations"]
    _need(isinstance(raw_observations, list) and len(raw_observations) <= 3,
          "at most three observations may be captured per task")
    records: list[dict[str, Any]] = []
    keys_seen: set[str] = set()
    records_by_id: dict[str, dict[str, Any]] = {}
    occurrences: dict[str, tuple[Any, ...]] = {}
    for index, item in enumerate(raw_observations):
        allowed = {"key", "attempt_id", "parent_attempt_id", "reporter", "actual_worker", "observed_at",
                   "before_sha", "after_sha", "dimension", "polarity", "cause", "supporting_refs",
                   "counter_refs", "summary", "source_observation_ref"}
        required = allowed - {"counter_refs", "summary", "source_observation_ref"}
        _keys(item, allowed, required, f"observations[{index}]")
        key = item["key"]
        _need(isinstance(key, str) and KEY.fullmatch(key) is not None, f"observations[{index}].key is invalid")
        keys_seen.add(key)
        attempt = item["attempt_id"]
        _id(attempt, f"observations[{index}].attempt_id")
        parent_attempt = item["parent_attempt_id"]
        _need(parent_attempt is None or (isinstance(parent_attempt, str) and IDENT.fullmatch(parent_attempt) is not None),
              f"observations[{index}].parent_attempt_id is invalid")
        _timestamp(item["observed_at"], f"observations[{index}].observed_at")
        _optional_sha(item["before_sha"], f"observations[{index}].before_sha")
        _optional_sha(item["after_sha"], f"observations[{index}].after_sha")
        _person(item["reporter"], f"observations[{index}].reporter", {"worker", "parent", "close"})
        _person(item["actual_worker"], f"observations[{index}].actual_worker", {"worker"})
        _need(item["dimension"] in DIMENSIONS and item["polarity"] in POLARITIES and item["cause"] in CAUSES,
              f"observations[{index}] has invalid dimension, polarity, or cause")
        _refs(item["supporting_refs"], f"observations[{index}].supporting_refs", 1, 3)
        _refs(item.get("counter_refs", []), f"observations[{index}].counter_refs", 0, 3)
        if "summary" in item:
            _safe_summary(item["summary"])
        source_ref = item.get("source_observation_ref")
        _need(source_ref is None or REF.fullmatch(source_ref) is not None,
              f"observations[{index}].source_observation_ref is invalid")
        _need(item["reporter"]["kind"] == "worker" or source_ref is not None,
              "parent and Close observations must reference their source observation")
        identity = (data["repo_owner"], data["repo_name"], data["task_id"], key)
        signature = (item["dimension"], item["polarity"], item["cause"])
        previous = occurrences.get(key)
        _need(previous is None or previous == signature,
              "observation key has conflicting dimension, polarity, or cause")
        occurrences[key] = signature

        record = {"record_kind": "observation", "rubric_version": "changeability-1.0"}
        record.update(_base_record(data, attempt, parent_attempt, item["reporter"], item["actual_worker"],
                                   item["observed_at"], item["before_sha"], item["after_sha"]))
        record["record_id"] = _digest_id(*identity, attempt, "observation")
        record["occurrence_id"] = _digest_id(*identity, prefix="ch-occ")
        record.update({key_name: item[key_name] for key_name in
                       ("dimension", "polarity", "cause", "supporting_refs")})
        record["counter_refs"] = item.get("counter_refs", [])
        record["source_observation_ref"] = source_ref
        if "summary" in item:
            record["summary"] = item["summary"]
        duplicate = records_by_id.get(record["record_id"])
        if duplicate is not None:
            _need(_canonical(duplicate) == _canonical(record),
                  "same attempt repeated an observation key with different evidence")
        else:
            records_by_id[record["record_id"]] = record
            records.append(record)

    assessment = data.get("assessment")
    if assessment is not None:
        _keys(assessment, {"applicability", "outcome", "completeness", "environment", "ratings", "observation_keys", "observation_refs", "overhead", "correction_ref"},
              {"applicability", "outcome", "completeness", "environment", "ratings", "observation_keys"}, "assessment")
        _need(assessment["applicability"] in {"applicable", "not_applicable"}, "assessment.applicability is invalid")
        _need(assessment["outcome"] in {"completed", "partial", "failed", "aborted"}, "assessment.outcome is invalid")
        _need(assessment["completeness"] in {"complete", "partial"}, "assessment.completeness is invalid")
        _need(assessment["outcome"] == "completed" or assessment["completeness"] == "partial",
              "partial, failed, and aborted attempts cannot claim a complete assessment")
        _need(assessment["environment"] in {"available", "unavailable", "unknown"}, "assessment.environment is invalid")
        _need(isinstance(assessment["ratings"], list) and len(assessment["ratings"]) == 3,
              "assessment must contain exactly three ratings")
        observation_keys = assessment["observation_keys"]
        _need(isinstance(observation_keys, list) and len(observation_keys) <= 3 and len(observation_keys) == len(set(observation_keys)),
              "assessment.observation_keys is invalid")
        _need(set(observation_keys) <= keys_seen, "assessment references an observation not in this capture")
        prior_refs = assessment.get("observation_refs", [])
        _refs(prior_refs, "assessment.observation_refs", 0, 3)
        rating_by_dimension: dict[str, dict[str, Any]] = {}
        for rating in assessment["ratings"]:
            _keys(rating, {"dimension", "value", "reason", "evidence_refs"},
                  {"dimension", "value", "reason", "evidence_refs"}, "rating")
            _need(rating["dimension"] in DIMENSIONS and rating["value"] in RATINGS,
                  "rating dimension or value is invalid")
            _need(rating["reason"] in {"grounded", "environment_unavailable", "insufficient_evidence", "not_applicable"},
                  "rating reason is invalid")
            _refs(rating["evidence_refs"], "rating.evidence_refs", 0, 3)
            _need(rating["dimension"] not in rating_by_dimension, "assessment rating dimensions must be unique")
            rating_by_dimension[rating["dimension"]] = rating
        _need(set(rating_by_dimension) == DIMENSIONS, "assessment needs locate, understand, and verify ratings")
        if assessment["applicability"] == "not_applicable":
            _need(not raw_observations and all(
                x["value"] == "not-assessable" and x["reason"] == "not_applicable" and not x["evidence_refs"]
                for x in rating_by_dimension.values()), "not-applicable assessments require three not-applicable ratings")
        _need(assessment["applicability"] == "not_applicable" or all(
            rating["reason"] != "not_applicable" for rating in rating_by_dimension.values()),
            "applicable assessments cannot use not_applicable ratings")
        for dimension, rating in rating_by_dimension.items():
            if rating["reason"] == "grounded":
                _need(rating["value"] != "not-assessable", f"grounded {dimension} rating must be assessable")
                _need(bool(rating["evidence_refs"]) or any(
                    item["key"] in observation_keys and item["dimension"] == dimension
                    for item in raw_observations),
                    f"grounded {dimension} rating needs evidence references")
            else:
                _need(rating["value"] == "not-assessable", f"non-grounded {dimension} rating must be not-assessable")
            if rating["reason"] == "environment_unavailable":
                _need(assessment["environment"] == "unavailable",
                      f"{dimension} cites unavailable environment when environment is not unavailable")
        if data["task_class"] == "qa":
            _need(assessment["applicability"] == "not_applicable", "QA assessments must be not_applicable")
        if assessment["environment"] == "unavailable":
            verify = rating_by_dimension["verify"]
            _need(verify["value"] == "not-assessable" and verify["reason"] == "environment_unavailable",
                  "unavailable verification environment must leave verify not-assessable")
        if "overhead" in assessment:
            _keys(assessment["overhead"], {"elapsed_ms", "tokens"}, {"elapsed_ms", "tokens"}, "assessment.overhead")
            for field in ("elapsed_ms", "tokens"):
                _need(assessment["overhead"][field] is None or
                      (isinstance(assessment["overhead"][field], int) and assessment["overhead"][field] >= 0),
                      f"assessment.overhead.{field} is invalid")
        if "correction_ref" in assessment:
            _ref(assessment["correction_ref"], "assessment.correction_ref")
        record = {"record_kind": "assessment", "rubric_version": "changeability-1.0"}
        record.update(_base_record(data, data["attempt_id"], data["parent_attempt_id"],
                                   data["reporter"], data["actual_worker"], data["observed_at"],
                                   data["before_sha"], data["after_sha"]))
        record["child_attempt_ids"] = data["child_attempt_ids"]
        record["record_id"] = _digest_id(data["repo_owner"], data["repo_name"], data["task_id"],
                                          data["attempt_id"], "assessment")
        record.update({key: assessment[key] for key in
                       ("applicability", "outcome", "completeness", "environment")})
        refs_by_key: dict[str, str] = {}
        for item in raw_observations:
            if item["key"] in observation_keys:
                occurrence = _digest_id(data["repo_owner"], data["repo_name"], data["task_id"],
                                        item["key"], prefix="ch-occ")
                refs_by_key.setdefault(item["key"], next(
                    candidate["record_id"] for candidate in records
                    if candidate["record_kind"] == "observation" and candidate["occurrence_id"] == occurrence))
        record["observation_refs"] = list(refs_by_key.values())
        for ref in prior_refs:
            if ref not in record["observation_refs"]:
                record["observation_refs"].append(ref)
        _need(len(record["observation_refs"]) <= 3, "assessment may reference at most three observations")
        record["ratings"] = assessment["ratings"]
        if "overhead" in assessment:
            record["overhead"] = assessment["overhead"]
        records.append(record)
    return records


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now_instant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    try:
        if not path.exists():
            return {"version": "1.0", "entries": []}
        _need(not path.is_symlink(), "outbox must not be a symlink")
        _need(path.parent.stat().st_mode & 0o077 == 0, "outbox directory must be private")
        _need(path.stat().st_mode & 0o077 == 0, "outbox permissions must be private (0600)")
        _need(path.stat().st_size <= MAX_OUTBOX_BYTES,
              "outbox exceeds the 4 MiB read limit; evidence is unsaved and was not submitted")
        with path.open("rb") as handle:
            encoded = handle.read(MAX_OUTBOX_BYTES + 1)
        _need(len(encoded) <= MAX_OUTBOX_BYTES,
              "outbox exceeds the 4 MiB read limit; evidence is unsaved and was not submitted")
        value = json.loads(encoded.decode("utf-8"))
    except OSError as exc:
        raise EvidenceError(f"outbox cannot be read (OS error {exc.errno})") from exc
    except json.JSONDecodeError as exc:
        raise EvidenceError("outbox cannot be read as valid JSON") from exc
    except UnicodeDecodeError as exc:
        raise EvidenceError("outbox is not valid UTF-8 JSON") from exc
    _need(isinstance(value, dict) and value.get("version") == "1.0" and isinstance(value.get("entries"), list),
          "outbox has an unsupported shape")
    _need(len(value["entries"]) <= MAX_OUTBOX_ENTRIES,
          "outbox exceeds the 1024-entry limit; evidence is unsaved and was not submitted")
    for entry in value["entries"]:
        allowed = {"record_id", "record_kind", "idempotency_key", "captured_at", "status", "task_identity",
                   "occurrence_id", "observed_at", "worker_fingerprint", "request", "receipt", "refusal_reason",
                   "attempt_id", "namespace", "payload_fingerprint", "supersedes_record_id"}
        allowed |= {"assessment_fingerprint", "correction_ref"}
        required = {"record_id", "record_kind", "idempotency_key", "captured_at", "status", "task_identity",
                    "occurrence_id", "observed_at", "worker_fingerprint"}
        _keys(entry, allowed, required, "outbox entry")
        _ref(entry["record_id"], "outbox record_id")
        _need(entry["record_kind"] in {"observation", "assessment"}, "outbox record_kind is invalid")
        try:
            uuid.UUID(entry["idempotency_key"])
        except (ValueError, TypeError, AttributeError) as exc:
            raise EvidenceError("outbox idempotency key is invalid") from exc
        _timestamp(entry["captured_at"], "outbox captured_at")
        _timestamp(entry["observed_at"], "outbox observed_at")
        _need(isinstance(entry["task_identity"], list) and len(entry["task_identity"]) == 3,
              "outbox task identity is invalid")
        if entry["occurrence_id"] is not None:
            _ref(entry["occurrence_id"], "outbox occurrence_id")
        _need(isinstance(entry["worker_fingerprint"], str)
              and re.fullmatch(r"[a-f0-9]{64}", entry["worker_fingerprint"]) is not None,
              "outbox worker fingerprint is invalid")
        if "attempt_id" in entry:
            _id(entry["attempt_id"], "outbox attempt_id")
        if "namespace" in entry:
            _need(isinstance(entry["namespace"], str) and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]*(?:/[A-Za-z0-9_-]+)*", entry["namespace"]) is not None,
                "outbox namespace is invalid")
        if "payload_fingerprint" in entry:
            _need(isinstance(entry["payload_fingerprint"], str)
                  and re.fullmatch(r"[a-f0-9]{64}", entry["payload_fingerprint"]) is not None,
                  "outbox payload fingerprint is invalid")
        if entry.get("supersedes_record_id") is not None:
            _ref(entry["supersedes_record_id"], "outbox supersedes_record_id")
        if entry.get("assessment_fingerprint") is not None:
            _need(re.fullmatch(r"[a-f0-9]{64}", entry["assessment_fingerprint"]) is not None,
                  "outbox assessment fingerprint is invalid")
        if entry.get("correction_ref") is not None:
            _ref(entry["correction_ref"], "outbox correction_ref")
        _need(entry["status"] in {"pending", "unsaved", "acknowledged", "expired"},
              "outbox status is invalid")
        if entry["status"] in {"pending", "unsaved"}:
            _need(isinstance(entry.get("request"), dict) and "receipt" not in entry,
                  "pending outbox entry must contain its exact request")
            request = entry["request"]
            _keys(request, {"action", "namespace", "idempotency_key", "record", "expected_updated_at", "classification"},
                  {"action", "namespace", "idempotency_key", "record"}, "outbox request")
            _need(request["action"] == "append", "outbox request action must be append")
            _need(isinstance(request["namespace"], str) and re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_-]*(?:/[A-Za-z0-9_-]+)*", request["namespace"]) is not None,
                "outbox request namespace is invalid")
            _need(request["namespace"] == entry.get("namespace")
                  and request["idempotency_key"] == entry["idempotency_key"],
                  "outbox request does not match its persisted namespace and idempotency key")
            _need(isinstance(request["record"], dict) and request["record"].get("record_id") == entry["record_id"],
                  "outbox request record identity is invalid")
            if "classification" in request:
                _need(request["classification"] in {"public", "internal", "client-confidential", "client-restricted"},
                      "outbox request classification is invalid")
            has_correction = request["record"].get("supersedes_record_id") is not None
            _need(has_correction == ("expected_updated_at" in request),
                  "correction request must bind the exact predecessor timestamp")
            if has_correction:
                _ref(request["record"]["supersedes_record_id"], "request.record.supersedes_record_id")
                _receipt_instant(request["expected_updated_at"], "request.expected_updated_at")
            if entry["status"] == "unsaved":
                    _need(entry.get("refusal_reason") in {"record_deleted", "classification_denied", "payload_expired", "access_denied", "user_declined"},
                      "unsaved outbox entry has no valid refusal reason")
        elif entry["status"] == "acknowledged":
            _need("request" not in entry and isinstance(entry.get("receipt"), dict),
                  "acknowledged outbox entry must retain only its receipt")
            _keys(entry["receipt"], {"record_id", "collected_at", "expires_at", "updated_at", "classification"},
                  {"record_id", "collected_at", "expires_at", "updated_at", "classification"}, "outbox receipt")
            _need(entry["receipt"]["record_id"] == entry["record_id"],
                  "outbox receipt record_id does not match its entry")
            receipt_times = {key: _receipt_instant(entry["receipt"][key], f"receipt.{key}")
                             for key in ("collected_at", "expires_at", "updated_at")}
            _need(receipt_times["expires_at"] > receipt_times["collected_at"],
                  "outbox receipt expiry must follow collection")
        else:
            _need("request" not in entry and "receipt" not in entry,
                  "expired outbox entry must not retain a payload or receipt")
    return value


def _save(path: Path, state: dict[str, Any]) -> None:
    temporary_name = ""
    try:
        _need(isinstance(state.get("entries"), list) and len(state["entries"]) <= MAX_OUTBOX_ENTRIES,
              "outbox capacity reached (1024 entries); new evidence remains unsaved and no entries were evicted")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _need(not path.is_symlink(), "outbox must not be a symlink")
        _need(path.parent.stat().st_mode & 0o077 == 0, "outbox directory must be private")
        encoded = (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        _need(len(encoded) <= MAX_OUTBOX_BYTES,
              "outbox capacity reached (4 MiB); new evidence remains unsaved and no entries were evicted")
        with tempfile.NamedTemporaryFile(prefix=".code-health-", dir=path.parent, delete=False) as handle:
            temporary_name = handle.name
            os.chmod(temporary_name, 0o600)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    except OSError as exc:
        if temporary_name:
            try:
                os.unlink(temporary_name)
            except OSError:
                pass
        raise EvidenceError(f"outbox persistence failed (OS error {exc.errno}); do not submit evidence") from exc


@contextmanager
def _outbox_lock(path: Path):
    """Serialize complete outbox transactions across concurrent child processes."""
    fd: int | None = None
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        _need(not path.parent.is_symlink() and path.parent.stat().st_mode & 0o077 == 0,
              "outbox directory must be private")
        lock_path = path.with_name(path.name + ".lock")
        _need(not lock_path.is_symlink(), "outbox lock must not be a symlink")
        flags = os.O_CREAT | os.O_RDWR
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(lock_path, flags, 0o600)
        os.fchmod(fd, 0o600)
        _need(os.fstat(fd).st_mode & 0o077 == 0, "outbox lock permissions must be private (0600)")
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError as exc:
        if fd is not None:
            os.close(fd)
        raise EvidenceError(f"outbox lock failed (OS error {exc.errno})") from exc
    except Exception:
        if fd is not None:
            os.close(fd)
        raise
    try:
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _idem(record: dict[str, Any]) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "code-health:" + record["record_id"]))


def prepare(data: dict[str, Any], outbox: Path, now: str | None = None) -> dict[str, Any]:
    captured_at = now or _utc_now()
    expiry_now = now or _utc_now_instant()
    _timestamp(captured_at, "captured_at")
    _need(isinstance(data.get("namespace"), str) and re.fullmatch(
          r"[A-Za-z0-9][A-Za-z0-9_-]*(?:/[A-Za-z0-9_-]+)*", data["namespace"]) is not None,
          "an exact writable namespace is required")
    _need(data.get("classification") is None or (
          isinstance(data.get("classification"), str) and data.get("classification") in
          {"public", "internal", "client-confidential", "client-restricted"}),
          "classification must be explicitly selected from the supported levels")
    records = build_records(data)
    now_value = datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ")
    for record in records:
        observed = datetime.strptime(record["observed_at"], "%Y-%m-%dT%H:%M:%SZ")
        _need(observed <= now_value, "future evidence cannot be prepared")
    with _outbox_lock(outbox):
        _expire_locked(outbox, expiry_now)
        return _prepare_locked(data, records, outbox, captured_at, expiry_now)


def _prepare_locked(data: dict[str, Any], records: list[dict[str, Any]], outbox: Path,
                    captured_at: str, now: str) -> dict[str, Any]:
    state = _load(outbox)
    current = _receipt_instant(now, "now")
    cutoff = current - timedelta(days=30)
    existing = {item.get("record_id"): item for item in state["entries"]}
    for record in records:
        record["_original_record"] = copy.deepcopy(record)
        record["_idempotency_key"] = _idem(record)
        record["_expected_updated_at"] = None
        record["_namespace"] = data["namespace"]
        record["_classification"] = data.get("classification")

    # New and changed records must be fresh. The six-month server window permits
    # only exact acknowledged replay after the 30-day admission window.
    for record in records:
        observed = datetime.strptime(record["observed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if observed >= cutoff:
            continue
        identity = [record["repo_owner"], record["repo_name"], record["task_id"]]
        if record["record_kind"] == "observation":
            fingerprint = hashlib.sha256(_canonical(record["_original_record"]).encode("utf-8")).hexdigest()
            candidates = [entry for entry in state["entries"] if entry.get("record_id") == record["record_id"]
                         and entry.get("record_kind") == "observation"
                         and entry.get("task_identity") == identity
                         and entry.get("payload_fingerprint") == fingerprint]
        else:
            fingerprint = hashlib.sha256(_canonical(record["_original_record"]).encode("utf-8")).hexdigest()
            correction_ref = data.get("assessment", {}).get("correction_ref")
            candidates = [entry for entry in state["entries"] if entry.get("record_kind") == "assessment"
                         and entry.get("task_identity") == identity
                         and (entry.get("attempt_id") == record["attempt_id"] or
                              entry.get("record_id") == record["record_id"])
                         and entry.get("assessment_fingerprint") == fingerprint
                         and entry.get("correction_ref") == correction_ref]
        replay = next((entry for entry in candidates if entry.get("status") == "acknowledged"
                       and isinstance(entry.get("receipt"), dict)
                       and _receipt_instant(entry["receipt"]["expires_at"], "receipt.expires_at") > current), None)
        _need(replay is not None,
              "evidence older than 30 days cannot be newly prepared; only an exact unexpired acknowledged replay is allowed")

    task_identity = [records[0]["repo_owner"], records[0]["repo_name"], records[0]["task_id"]] if records else None
    assessment_records = [r for r in records if r["record_kind"] == "assessment"]
    for record in assessment_records:
        base_id = record["record_id"]
        record["_base_assessment_id"] = base_id
        original_record = record["_original_record"]
        fingerprint = hashlib.sha256(_canonical(original_record).encode("utf-8")).hexdigest()
        lineage = [entry for entry in state["entries"]
                   if entry.get("record_kind") == "assessment"
                   and entry.get("task_identity") == task_identity
                   and (entry.get("attempt_id") == record["attempt_id"] or entry.get("record_id") == base_id)]
        requested_correction_ref = data.get("assessment", {}).get("correction_ref")
        same = next((entry for entry in lineage if
                     (entry.get("assessment_fingerprint") == fingerprint
                      and entry.get("correction_ref") == requested_correction_ref)
                     or (requested_correction_ref is None and entry.get("record_id") == base_id
                         and (entry.get("payload_fingerprint") == fingerprint
                              or entry.get("request", {}).get("record") == original_record))), None)
        if same is not None:
            saved_namespace = same.get("namespace", same.get("request", {}).get("namespace", data["namespace"]))
            saved_classification = same.get("receipt", {}).get("classification",
                                   same.get("request", {}).get("classification"))
            _need(saved_namespace == data["namespace"],
                  "exact replay must use its persisted namespace")
            _need(data.get("classification") is None or data.get("classification") == saved_classification,
                  "exact replay cannot change its persisted classification")
            record["record_id"] = same["record_id"]
            record["_idempotency_key"] = same["idempotency_key"]
            record["_namespace"] = same.get("namespace", same.get("request", {}).get("namespace", data["namespace"]))
            record["_classification"] = same.get("receipt", {}).get("classification",
                                         same.get("request", {}).get("classification"))
            record["_already_persisted"] = same
            continue
        if lineage:
            heads = [entry for entry in lineage if not any(
                other.get("supersedes_record_id") == entry["record_id"] for other in lineage)]
            _need(len(heads) == 1, "assessment correction predecessor is ambiguous")
            predecessor = heads[0]
            _need(requested_correction_ref is not None,
                  "changed assessment requires an explicit registered correction_ref")
            _need(predecessor.get("status") == "acknowledged" and isinstance(predecessor.get("receipt"), dict),
                  "resolve the uncertain or refused assessment predecessor before correction")
            predecessor_namespace = predecessor.get("namespace", predecessor.get("request", {}).get("namespace"))
            _need(predecessor_namespace == data["namespace"],
                  "assessment correction must use the predecessor's exact namespace")
            correction_ref = data.get("assessment", {}).get("correction_ref")
            correction_basis = {k: v for k, v in record.items() if not k.startswith("_")}
            correction_basis["supersedes_record_id"] = predecessor["record_id"]
            correction_basis["correction_ref"] = correction_ref
            correction_digest = hashlib.sha256(_canonical(correction_basis).encode("utf-8")).hexdigest()
            record["supersedes_record_id"] = predecessor["record_id"]
            record["correction_ref"] = correction_ref
            record["record_id"] = _digest_id(base_id, predecessor["record_id"],
                                             correction_ref, correction_digest,
                                             prefix="ch-correction")
            record["_expected_updated_at"] = predecessor["receipt"]["updated_at"]
            record["_namespace"] = predecessor_namespace
            record["_classification"] = predecessor["receipt"]["classification"]
            record["_supersedes_record_id"] = predecessor["record_id"]
            record["_idempotency_key"] = _idem(record)
        else:
            _need(data.get("assessment", {}).get("correction_ref") is None,
                  "correction_ref requires an existing acknowledged assessment")

    new_items = []
    replays = []
    for record in records:
        if record.get("_already_persisted") is not None:
            if record["record_kind"] == "assessment":
                prior = record["_already_persisted"]
                replays.append({"record_id": prior["record_id"], "status": prior["status"],
                                **({"request": copy.deepcopy(prior["request"])} if prior.get("request") else {}),
                                **({"receipt": copy.deepcopy(prior["receipt"])} if prior.get("receipt") else {})})
            continue
        key = record["record_id"]
        clean_record = {k: v for k, v in record.items() if not k.startswith("_") and k != "_base_assessment_id"}
        idem = record["_idempotency_key"]
        request = {"action": "append", "namespace": record["_namespace"],
                   "idempotency_key": idem, "record": clean_record}
        if record["_expected_updated_at"] is not None:
            request["expected_updated_at"] = record["_expected_updated_at"]
        if record["_classification"] is not None:
            request["classification"] = record["_classification"]
        item = {"record_id": key, "record_kind": record["record_kind"], "idempotency_key": idem,
                "captured_at": captured_at, "status": "pending",
                "task_identity": [record["repo_owner"], record["repo_name"], record["task_id"]],
                "occurrence_id": record.get("occurrence_id"), "observed_at": record["observed_at"],
                "attempt_id": record["attempt_id"], "namespace": record["_namespace"],
                "payload_fingerprint": hashlib.sha256(_canonical(clean_record).encode("utf-8")).hexdigest(),
                "supersedes_record_id": record.get("_supersedes_record_id"),
                "assessment_fingerprint": hashlib.sha256(_canonical(record["_original_record"]).encode("utf-8")).hexdigest()
                    if record["record_kind"] == "assessment" else None,
                "correction_ref": clean_record.get("correction_ref") if record["record_kind"] == "assessment" else None,
                "worker_fingerprint": _worker_fingerprint(record["actual_worker"]),
                "request": request}
        old = existing.get(key)
        if old is not None:
            _need(old.get("idempotency_key") == item["idempotency_key"], "outbox record identity collision")
            _need(old.get("payload_fingerprint") in {None, item["payload_fingerprint"]},
                  "record ID is already bound to different evidence")
            _need(old.get("payload_fingerprint") is not None or old.get("request") is not None,
                  "legacy acknowledged record has no payload fingerprint; exact replay cannot be verified")
            _need(old.get("namespace", old.get("request", {}).get("namespace")) == item["request"]["namespace"],
                  "exact replay must use its persisted namespace")
            saved_classification = old.get("receipt", {}).get("classification",
                                   old.get("request", {}).get("classification"))
            _need(data.get("classification") is None or data.get("classification") == saved_classification,
                  "exact replay cannot change its persisted classification")
            if old.get("request") is not None:
                _need(_canonical(old["request"]) == _canonical(item["request"]),
                      "record already exists with different payload; reuse or resolve the persisted request")
            if record["record_kind"] == "assessment":
                replays.append({"record_id": old["record_id"], "status": old["status"],
                                **({"request": copy.deepcopy(old["request"])} if old.get("request") else {}),
                                **({"receipt": copy.deepcopy(old["receipt"])} if old.get("receipt") else {})})
            continue
        if record.get("_already_persisted") is not None:
            continue
        new_items.append(item)
    # One task cannot accumulate more than three distinct observed occurrences,
    # even when child and parent records preserve separate source provenance.
    if task_identity:
        owner, repo, task = task_identity
        all_occurrences = {
            entry["occurrence_id"] for entry in state["entries"]
            if entry.get("occurrence_id") and entry.get("task_identity") == [owner, repo, task]
        }
        all_occurrences.update(r["occurrence_id"] for r in records if r["record_kind"] == "observation")
        _need(len(all_occurrences) <= 3, "at most three meaningful observations may be retained per task")

    _need(len(state["entries"]) + len(new_items) <= MAX_OUTBOX_ENTRIES,
          "outbox capacity reached (1024 entries); new evidence remains unsaved and no entries were evicted")

    known = {entry["record_id"]: entry for entry in state["entries"]}
    known.update({record["record_id"]: {
        "record_id": record["record_id"], "record_kind": record["record_kind"],
        "task_identity": [record["repo_owner"], record["repo_name"], record["task_id"]],
        "occurrence_id": record.get("occurrence_id"), "observed_at": record["observed_at"],
        "worker_fingerprint": _worker_fingerprint(record["actual_worker"]),
    } for record in records})
    for record in records:
        if record["record_kind"] == "assessment":
            for observation_ref in record.get("observation_refs", []):
                source = known.get(observation_ref)
                _need(source is not None and source.get("record_kind") == "observation"
                      and source.get("task_identity") == [record["repo_owner"], record["repo_name"], record["task_id"]],
                      "assessment observation reference must resolve to a retained observation in this task")
        source_ref = record.get("source_observation_ref")
        if source_ref is None:
            continue
        _need(source_ref != record["record_id"], "an observation cannot cite itself as its source")
        source = known.get(source_ref)
        _need(source is not None and source.get("record_kind") == "observation",
              "source observation must already exist in this task's local evidence history")
        _need(source.get("task_identity") == [record["repo_owner"], record["repo_name"], record["task_id"]]
              and source.get("occurrence_id") == record["occurrence_id"],
              "source observation must match repository, task, and occurrence")
        _need(source.get("worker_fingerprint") == _worker_fingerprint(record["actual_worker"]),
              "parent/Close observation worker identity must match its source")
        _need(source.get("observed_at", "9999") <= record["observed_at"],
              "parent/Close observation cannot predate its source")
    state["entries"].extend(new_items)
    if new_items:
        _save(outbox, state)
    return {"prepared": len(new_items), "existing": len(records) - len(new_items),
            "record_ids": [r["record_id"] for r in records], "replays": replays}


def pending(outbox: Path, now: str | None = None) -> list[dict[str, Any]]:
    with _outbox_lock(outbox):
        _expire_locked(outbox, now or _utc_now_instant())
        state = _load(outbox)
        return [copy.deepcopy(item) for item in state["entries"] if item.get("status") == "pending" and item.get("request")]


def acknowledge(outbox: Path, receipt: dict[str, Any]) -> None:
    _keys(receipt, {"record_id", "collected_at", "expires_at", "updated_at", "classification"},
          {"record_id", "collected_at", "expires_at", "updated_at", "classification"}, "receipt")
    _ref(receipt["record_id"], "receipt.record_id")
    parsed = {key: _receipt_instant(receipt[key], f"receipt.{key}")
              for key in ("collected_at", "expires_at", "updated_at")}
    _need(receipt["classification"] in {"public", "internal", "client-confidential", "client-restricted"},
          "receipt.classification is invalid")
    _need(parsed["expires_at"] > parsed["collected_at"], "receipt expiry must follow collection")
    with _outbox_lock(outbox):
        state = _load(outbox)
        for item in state["entries"]:
            if item.get("record_id") == receipt["record_id"]:
                if item.get("status") == "acknowledged":
                    _need(item.get("receipt") == receipt, "acknowledged receipt conflicts with stored receipt")
                    return
                _need(item.get("status") == "pending" and item.get("request"), "record is not pending")
                item["status"] = "acknowledged"
                item["receipt"] = receipt
                item.pop("request", None)
                _save(outbox, state)
                return
    raise EvidenceError("receipt record_id is not present in the outbox")


def refuse(outbox: Path, record_id: str, reason: str) -> None:
    _ref(record_id, "record_id")
    _need(reason in {"record_deleted", "classification_denied", "payload_expired", "access_denied", "user_declined"},
          "refusal reason is invalid")
    with _outbox_lock(outbox):
        state = _load(outbox)
        for item in state["entries"]:
            if item.get("record_id") == record_id:
                _need(item.get("status") == "pending", "record is not pending")
                item["status"] = "unsaved"
                item["refusal_reason"] = reason
                _save(outbox, state)
                return
    raise EvidenceError("record_id is not present in the outbox")


def expire(outbox: Path, now: str) -> int:
    _receipt_instant(now, "now")
    with _outbox_lock(outbox):
        return _expire_locked(outbox, now)


def _expire_locked(outbox: Path, now: str) -> int:
    current = _receipt_instant(now, "now")
    cutoff = current - timedelta(days=30)
    state = _load(outbox)
    kept = []
    removed = 0
    for item in state["entries"]:
        captured = datetime.strptime(item["captured_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        should_remove = item.get("status") == "expired" or (bool(item.get("request")) and captured <= cutoff)
        if item.get("status") == "acknowledged":
            expiry = _receipt_instant(item["receipt"]["expires_at"], "receipt.expires_at")
            should_remove = expiry <= current
        if should_remove:
            removed += 1
            continue
        kept.append(item)
    if removed:
        state["entries"] = kept
        _save(outbox, state)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("input")
    p_prepare.add_argument("outbox")
    p_pending = sub.add_parser("pending")
    p_pending.add_argument("outbox")
    p_ack = sub.add_parser("ack")
    p_ack.add_argument("outbox")
    p_ack.add_argument("receipt")
    p_refuse = sub.add_parser("refuse")
    p_refuse.add_argument("outbox")
    p_refuse.add_argument("record_id")
    p_refuse.add_argument("reason", choices=["record_deleted", "classification_denied", "payload_expired", "access_denied", "user_declined"])
    p_expire = sub.add_parser("expire")
    p_expire.add_argument("outbox")
    p_expire.add_argument("now")
    args = parser.parse_args()
    try:
        outbox = Path(args.outbox)
        if args.command == "prepare":
            data = json.loads(Path(args.input).read_text(encoding="utf-8"))
            result = prepare(data, outbox)
        elif args.command == "pending":
            result = pending(outbox)
        elif args.command == "ack":
            receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
            acknowledge(outbox, receipt)
            result = {"acknowledged": receipt["record_id"]}
        elif args.command == "refuse":
            refuse(outbox, args.record_id, args.reason)
            result = {"unsaved": args.record_id, "reason": args.reason}
        else:
            result = {"expired": expire(outbox, args.now)}
        print(json.dumps(result, sort_keys=True))
    except OSError as exc:
        print(f"code-friction: local file operation failed (OS error {exc.errno})", file=sys.stderr)
        raise SystemExit(2) from exc
    except (json.JSONDecodeError, EvidenceError, KeyError, TypeError) as exc:
        print(f"code-friction: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    main()
