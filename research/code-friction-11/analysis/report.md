# Issue #11 calibration report

This is one bounded calibration trial, not a statistical validation or model
leaderboard. The blind packet remains frozen at
`analysis/frozen-manifest.json`. The two evaluator arrays are retained
unchanged at `analysis/evaluations/rubric-eval-a.json` and
`analysis/evaluations/rubric-eval-b.json`.

Their SHA-256 digests are `3ec827860b7e9cb7fe72597bd4223574df20edbcd54dc917ab7086d9f78b25f0`
and `10d8b3a4cb16436fee09586f1ace827109340137875d3e4f010a4f58b742a9f5`,
respectively.

The requested model and effort were `gpt-6-luna` and `high` for both runs.
Both evaluator records report `observed_model: unknown`,
`observed_effort: unknown`, and unknown elapsed time and token counts. Those
values remain unknown; no overhead estimate is made.

## Validator correction

The first validator revision incorrectly limited each observation to three
evidence references. Issue #11 limits meaningful observations to three, not
the number of references supporting one observation. The validator now requires
each observation to have a non-empty list of known anchor IDs, with no cap on
that list. A regression test accepts the four references in run A's
`S2-scattered` observation while continuing to reject four observations.

The frozen packet itself was not changed.

## Aggregated ratings

The 16 records (two fresh evaluations for each of eight scenarios) aggregate to
the following ratings. `NA` is the explicit `not-assessable` value required for
the pure Q&A scenario.

| Scenario | Locate | Understand | Verify | Environment separation |
| --- | --- | --- | --- | --- |
| S1 straightforward | easy / easy | easy / easy | easy / easy | code |
| S2 scattered | manageable / manageable | manageable / manageable | manageable / manageable | code |
| S3 hidden dependency | difficult / difficult | difficult / difficult | difficult / difficult | code |
| S4 unavailable test environment | easy / easy | manageable / manageable | NA / NA | environment; code location remained assessable |
| S5 failed or aborted work | easy / easy | manageable / manageable | manageable / manageable | code |
| S6 pure Q&A | NA / NA | NA / NA | NA / NA | explicit not-applicable |
| S7 before simplification | easy / easy | manageable / manageable | manageable / manageable | code |
| S7 after simplification | easy / easy | manageable / easy | manageable / manageable | code |

There was agreement on 23 of 24 dimension pairs (95.8%). Seven of eight
scenarios had complete three-dimension agreement. The sole disagreement was
whether the simplified S7-after implementation made consequences `easy` or
`manageable` to understand.

The observations supplied 20 evidence-backed observations in run A and 14 in
run B. All 34 observations cited only predeclared anchor IDs; a claim-to-anchor
pass found no unsupported claim. This checks grounding against the supplied
synthetic packet, not truth outside it. The original run-A S2 observation with
four references is included in that count and passes validation.

The environment distinction worked as intended. Both S4 evaluations kept code
location at `easy` and code understanding at `manageable`, while rating
verification `not-assessable` and classifying the blocker as environment. Both
S6 records kept all dimensions `not-assessable` with explicit
`not_applicable`, so the Q&A case does not enter implementation totals.

## Comparison with internal calibration anchors

The hidden `expected-anchors.json` contains likely ratings used only for this
calibration check. Evaluators matched 39 of 48 likely dimension ratings
(81.25%). This is a diagnostic comparison, not ground truth.

- S1, S2, S4, and S6 matched all likely ratings.
- Both S3 evaluators called location `difficult` where the internal anchor
  expected `manageable`; both still matched the hidden-consequence and
  verification judgments.
- Both S5 evaluators called location `easy` and understanding `manageable`
  where the internal anchor expected `manageable` and `difficult`. The
  supplied partial edit made the target symbol obvious even though the
  lifecycle consequence was incomplete; the rubric needs clearer guidance for
  this boundary.
- Both S7-before evaluators called location `easy` where the internal anchor
  expected `manageable`, showing that duplicated branches in one file may not
  register as scattered ownership.
- The paired S7-after result was mixed: run B moved understanding from
  `manageable` to `easy`, while run A retained `manageable`. Both kept
  verification `manageable`, correctly noticing that the focused test still
  omits the opt-out and SMS cases.

These are useful counterexamples to treating agreement as sufficient evidence:
S3 and S5 agree internally while missing the predeclared calibration boundary,
and the before/after pair detects simplification only in one fresh evaluation.

## Recommendation

Adopt the rubric as a lightweight observation format with these adjustments:

1. Keep the three dimensions and four ratings. They produced high pairwise
   agreement and distinguished S1, S2, S3, S4, S5, and S6 in plausible ways.
2. Keep the separate applicability and code/environment fields. S4 shows why
   an unavailable test tool must not erase an assessable code location.
3. Keep a maximum of three meaningful observations, but allow each observation
   any non-empty number of grounded anchor references. The validator now matches
   that rule.
4. Add evaluator examples for boundary cases: a single file with duplicated
   branches can still be `manageable` to locate, and an aborted edit can be
   easy to locate while difficult to understand. Treat before/after changes of
   one adjacent rating as a signal requiring the evidence claim, not as a
   decisive automation input.

Do not adopt ease ratings as authority for merging, routing, model promotion,
autonomy, or Close readiness. Do not fold unavailable tools into code friction,
and do not use this two-evaluator set to compare models. Stop this trial after
the validator correction; a revised rubric pass is optional future calibration,
not required to repair the evidence packet.

## Verification and limitations

`python3 research/code-friction-11/test_trial.py` passes 9 tests, including the
new four-reference regression, three-observation cap, parent/child and Close
retry deduplication, partial-task rejection, N/A handling, and unavailable
environment validation. The aggregate is reproducible directly from the
retained JSON arrays with `trial.py aggregate` and
`--expected-per-scenario 2`; array inputs are flattened by the validator and
it produced 16 evaluations and eight scenario reports.

The repository has no applicable hosted CI for this research directory. Its
only workflow is `.github/workflows/ship-it.yml`, path-filtered to `ship-it/**`
and its own workflow file. `make test` is also unavailable because the
repository has no `test` target. No production skill, Close behavior, or
runtime artifact was changed; this trial did not commit or publish.
