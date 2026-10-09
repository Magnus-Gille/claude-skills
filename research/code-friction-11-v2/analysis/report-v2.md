# Issue #11 v2 calibration report

This is the final bounded pilot pass. It is calibration evidence for a small
synthetic set, not statistical validation, a composite quality score, or a
model leaderboard. Each fresh evaluator saw the same eight scenarios in a new
session.

The blind packet is frozen by `analysis/frozen-manifest-v2.json`:

- `evaluator-instructions.md`: `664efd1dc36e1db36ed3a816a98f775ddf5933e69de426f9c688608b01fc2a98`
- `rubric.md`: `2e1d3a1888a444b9f3ecf4ce42a7fc6fbbb6881c44f89fd6ee8b2047b244a4cc`
- `scenarios.json`: `323f5e9155f06671d454d6e3ec5f9b60bf1eb783ffbe1cac49caaeda9bfdad37`

The imported evaluator arrays are unchanged:

- `analysis/evaluations/rubric-v2-eval-a.json`:
  `81f6e5d0d162c2853a4734b5aa7064f0cdde0d6d4a19ae78c26eef0ce4fb806e`
- `analysis/evaluations/rubric-v2-eval-b.json`:
  `5e553920ef4b249e8a4df4bbd7b84759b5abba5935d90a7584521161d62e0823`

Both runs requested `gpt-6-luna` at `high` effort. Both report
`observed_model: unknown`, `observed_effort: unknown`, and unknown time and
token counts. Run A's S6 record omits `elapsed_seconds`; the validator treats
that optional runtime field as unknown without modifying the retained record.

## Agreement and evidence

The aggregate contains 16 evaluations, two per scenario, and 34 observations.
Ratings are shown in evaluator order A / B:

| Scenario | Locate | Understand | Verify | Environment / applicability |
| --- | --- | --- | --- | --- |
| S1 straightforward | easy / easy | easy / easy | easy / easy | code |
| S2 scattered | manageable / manageable | manageable / manageable | manageable / manageable | code |
| S3 hidden dependency | difficult / difficult | difficult / difficult | difficult / difficult | code |
| S4 unavailable test environment | easy / easy | easy / manageable | not-assessable / not-assessable | environment |
| S5 failed or aborted work | easy / easy | manageable / manageable | manageable / manageable | code; partial |
| S6 pure Q&A | not-assessable / not-assessable | not-assessable / not-assessable | not-assessable / not-assessable | explicit not-applicable |
| S7 before simplification | easy / easy | manageable / manageable | manageable / manageable | code |
| S7 after simplification | easy / manageable | easy / manageable | manageable / manageable | code |

There is agreement on 21 of 24 dimension pairs (87.5%). The disagreements are
S4 understanding and S7-after location and understanding. S1, S2, S3, S5,
S6, and S7-before agree on every dimension.

All 34 observations cite only anchor IDs declared by their scenario. A manual
claim-to-anchor pass found the claims grounded in the supplied synthetic files;
this is evidence-reference accuracy for the packet, not proof of correctness
outside it. S3 observations consistently identify both cache and audit
consumers. S5 observations identify incomplete settle cleanup and missing
rejection/concurrency coverage. S7-after observations correctly identify the
shared payload path while retaining a verification gap for false mode and SMS.

The environment distinction remains useful: both S4 evaluators mark the
proprietary runtime unavailable and verification not-assessable, while both
still rate code location easy. S6 remains explicit not-applicable and is kept
outside implementation totals.

## What the pilot suggests

The valid v2 scenarios expose why the v1 high agreement was not validation. V1
had 23/24 agreement, but S3's source did not actually lack slash support and
both S7 variants already implemented the requested option. The evaluators could
agree on a flawed task. V2 corrects those fixtures and produces meaningful
boundary disagreements, especially in the simplification pair.

The paired result is a useful pilot observation: both evaluators see the
before case as manageable to understand, while one sees the shared after case
as easy and the other as manageable. That is a signal to preserve the evidence
claim and inspect the boundary, not a reason to calculate a quality score.
S5 is another useful observation: both evaluators locate the partial edit easily
while keeping consequence and verification at manageable. A partial work state
can therefore be easy to find without being trivial to finish.

## Adopt, adjust, drop

Adopt the bounded observation format: locate, understand, and verify; the four
ratings; explicit applicability; explicit code/environment classification; and
up to three concise observations with grounded anchor references. Keep stable
`occurrence_id` deduplication and retain complete source provenance, including
attempt and parent IDs.

Adjust the guidance in future use:

- Treat `not-assessable` as a dimension-level statement and preserve the code
  rating when only the environment is unavailable.
- Include examples for adjacent boundaries such as S4 understanding and the
  S7 before/after pair. Require the evaluator's evidence claim when a rating
  moves by one level.
- Treat missing optional runtime telemetry as unknown and keep requested and
  observed model metadata separate.

Drop composite ease scores, model rankings, and any authority for merge,
routing, autonomy, promotion, or Close readiness. Keep this as a pilot
observation protocol and rerun only with a new explicitly scoped calibration
set.

## Verification, audit, and reversal

The reproducible aggregate command is the one in the v2 README and consumes
the retained evaluator arrays directly. It produces
`analysis/aggregate-v2.json` with 16 evaluations, 8 scenario reports, and 34
deduplicated observations.

Checks passed:

- `PYTHONDONTWRITEBYTECODE=1 python3 research/code-friction-11-v2/test_trial.py` — 10 tests passed, including missing optional telemetry and complete child/parent/Close-retry provenance.
- `PYTHONDONTWRITEBYTECODE=1 python3 research/code-friction-11-v2/test_scenarios.py` — 2 executable Node fixture tests passed.
- Frozen v2 packet hashes rechecked after aggregation; packet inputs were unchanged.

For audit, inspect `git status --short`, the v2 scoped diff, the frozen
manifest, evaluator hashes, aggregate receipt, and both deterministic test
commands. The superseded v1 tree remains at `research/code-friction-11/` with
its rejected-calibration notice. Reversal is a normal reviewed revert removing
`research/code-friction-11-v2/`; it has no runtime impact. No external state,
production skill, Close behavior, commit, or publication was changed.
