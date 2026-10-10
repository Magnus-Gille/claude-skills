## Advisory code-friction capture

Use this only for a coding task when the owner has enabled capture for the task or the user has
explicitly authorized it. It is advisory evidence for the Grimnir changeability pilot. It does not
score an agent, establish causation, change merge or Close readiness, or authorize another action.
Read the bundled [changeability-1.0 rubric](rubric.md) when a rating is needed.

Capture up to three distinct observations for a task across its worker attempts. Each observation
states one concrete helpful or obstructive factor, its `locate`, `understand`, or `verify` dimension,
and its `code`, `environment`, or evidenced `mixed` cause. Keep environment limits separate from
the code rating. For no-code Q&A, use `not_applicable` and three `not-assessable` ratings; do not
invent an easy task. Do not make a complete assessment for partial, failed, or aborted work. Do not
make an extra evaluator call to fill gaps.

Use the same stable task ID across child and parent work. Keep each actual attempt ID and parent
attempt ID, reporter, and actual worker separate. A requested model is not an observed model; use
`null` when the worker model or effort is unknown. A parent or Close summary of a worker finding
must use that finding's occurrence key and `source_observation_ref`, preserve the source worker,
and must not create a second finding. Repeated Close runs reuse the exact prepared record. Different
attempts retain separate record IDs and provenance while sharing the occurrence ID. Conflicting
dimension, polarity, or cause for an occurrence is an unresolved conflict; stop and preserve the
evidence instead of choosing newest-wins.

Use only opaque `ref:...` values from the owning repository's evidence registry for module,
supporting, counter, and rating references. If a required source cannot be referenced safely, leave
that rating not-assessable or skip capture. Store no code, diff, transcript, prompt, user text,
private path, URL, credential, or raw error. A summary is a sanitized paraphrase of at most 280
characters. The helper rejects unknown/raw fields and obvious locators, including absolute paths
next to ordinary punctuation, but cannot prove arbitrary prose safe; review it before preparation.

The input is one JSON object matching these fields: exact writable `namespace` and optional explicit
`classification` (`public`, `internal`, `client-confidential`, or `client-restricted`); task identity (`repo_owner`, `repo_name`,
`task_id`, `task_class`, `attempt_id`, nullable `parent_attempt_id`, and `child_attempt_ids`),
whole-second UTC `observed_at`, nullable 40-character `before_sha`/`after_sha`, `module_refs`,
`reporter`, `actual_worker`, and an `observations` array. Each observation supplies a stable local
`key`, its own `attempt_id` and nullable `parent_attempt_id`, `reporter`, `actual_worker`, timestamp,
revisions, `dimension`, `polarity`, `cause`, one to three `supporting_refs`, and optional
`counter_refs`, sanitized `summary`, and `source_observation_ref`. The root reporter and worker
describe the terminal assessment. The optional `assessment` contains `applicability`, `outcome`,
`completeness`, `environment`, three dimension `ratings`, and `observation_keys`; `overhead` is
optional and unknown time/token values stay null. An assessment may include `observation_refs` for
already retained observations that need no payload recreation. To revise a terminal assessment,
include a registered `correction_ref`; the helper requires its predecessor to be acknowledged,
then appends a new record with the stored predecessor's exact `updated_at` as `expected_updated_at`.
An uncertain predecessor must be resolved first. A correction inherits the predecessor's
classification when none is selected; an explicit equal or more restrictive classification is
preserved, and a downgrade is rejected. Existing observation requests retain their original
classification. Use exactly the canonical field names and enum values in the v1 schema.

### Prepare, flush, and retain

The helper is local-only and makes no network call. Use a private state path for example
`~/.codex/state/code-health/outbox.json`:

```bash
python3 <close-skill-dir>/scripts/code-friction.py prepare <capture.json> <outbox.json>
python3 <close-skill-dir>/scripts/code-friction.py pending <outbox.json>
python3 <close-skill-dir>/scripts/code-friction.py ack <outbox.json> <receipt.json>
python3 <close-skill-dir>/scripts/code-friction.py refuse <outbox.json> <record-id> <reason>
python3 <close-skill-dir>/scripts/code-friction.py expire <outbox.json> <current-utc-time>
```

`prepare` validates and atomically writes the exact Munin append arguments (`action`, `namespace`,
`idempotency_key`, `record`, correction `expected_updated_at` when applicable, and explicitly
selected optional `classification`) before any remote append. Exact assessment replays return their
persisted request or receipt. The file is mode `0600`; never put it in the repository.
Keep `capture.json` in the same private directory with mode `0600`, and remove it immediately after
`prepare` succeeds; it is only an input staging file. If preparation fails, keep it private and
expire it within 30 days.
If persistence fails, do not call Munin. Keep the result explicitly unsaved in the current handoff.
Do not prepare another payload for the same record after an uncertain response: retry only the
persisted record and key. A transport retry is not a new observation.

The local outbox is capped at 1,024 entries and 4 MiB. Oversized or full outboxes fail before any
remote append; no entry is evicted to make room. Keep the capture private and report it unsaved.
The existing outbox must be reduced by its normal expiry, or an owner must choose a deliberate
recovery path, before new records can be stored.

When authorized and `memory_code_health` is available, flush pending entries in their stored order
using each persisted append argument object verbatim. Do not guess a namespace or classification. For each successful
receipt, save its `record_id`, server `collected_at`, `expires_at`, `updated_at`, and
`classification`; then run `ack`. Ack removes the local record payload and retains the receipt plus
minimal opaque task/attempt/occurrence identity, namespace, fingerprints, and correction lineage
needed for safe replay and correction. Never calculate a replacement expiry: server retention
metadata is authoritative. If the API returns `record_deleted`, `payload_expired`, `classification_denied`,
or `access_denied`, use `refuse` with the matching reason and do not enter an automatic retry
loop. A refused observation also marks pending assessments and parent/Close observations that cite
it as unsaved with a bounded `source_refused` dependency reason; they are excluded from later flushes.
An unsaved or expired observation cannot be used to prepare a new assessment or parent reference.
Acknowledged retained observations and pending sources that precede dependents in the same flush
remain valid. These items remain clearly unsaved until local expiry or an explicit later decision.

Unsaved payloads remain in the private outbox for at most 30 days from capture. Run `expire` during
Close; `prepare` and `pending` also reap expired entries. Acknowledged metadata is removed at the
exact server `expires_at`; no identity tombstone is retained past expiry. Housekeeping runs only when
the skill or Close is used. Physical erasure while idle needs a separately configured,
owner-approved maintenance mechanism; this skill creates no background job. Stored records follow
the exact server `expires_at` (currently a maximum of six calendar months from
server collection, potentially earlier if reference context is removed). Do not infer stored
retention from local time or from when a record was first observed.

### Close behavior

- Full Close may prepare one terminal assessment for each in-scope completed attempt and flush
  already captured observations. It may mark incomplete work `partial`; it may not turn missing
  evidence into an easy rating.
- Quick Close only flushes records already present in the outbox. It creates no observations or
  assessment. A record captured but not prepared is not added in quick mode.
- On absent tool access, persistence failure, permission denial, or expiry, report the evidence as
  unsaved in the existing `Persistence` section. Do not add a blocker, warning, or pending item
  solely for advisory code-health state; code-health never affects the canonical renderer's
  readiness result.

The canonical Grimnir shapes and semantic rules remain in
`docs/code-health-agent-v1.schema.json` and `scripts/lib/code-health-agent.mjs`. This skill's
helper enforces the bounded capture and local outbox lifecycle; Munin remains the authority for
authenticated admission, idempotency, corrections, export, and server retention.
