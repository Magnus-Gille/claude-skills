# Code-friction rubric trial packet v2

This directory is a frozen, public-safe research fixture for issue #11. It is
calibration evidence only. It does not change any installed skill, `Close`
workflow, merge gate, routing rule, or autonomy decision.

The packet is deliberately split into two parts:

- `packet/` is the blind evaluator input. It contains only synthetic source,
  tasks, the rubric, and evaluator instructions.
- `analysis/` contains only the aggregation protocol until the root agent adds
  fresh evaluator outputs. Do not give this directory to an evaluator.

The packet has seven task families represented by eight scenario records.
`S7-before` and `S7-after` are a paired simplification case with the same task.
Scenario `S6-qa` is pure Q&A and is marked not applicable through the
evaluation schema rather than being forced into an implementation rating.

## Frozen inputs

The input manifest is `packet/manifest.json`. It names every packet input; the
SHA-256 digests are recorded in the separate frozen record at
`analysis/frozen-manifest-v2.json`. Freeze the packet by running:

```sh
python3 research/code-friction-11-v2/trial.py freeze \
  --packet research/code-friction-11-v2/packet \
  --output research/code-friction-11-v2/analysis/frozen-manifest-v2.json
```

The evaluator receives only `packet/` and a fresh copy of
`packet/evaluator-instructions.md`. It must not receive `analysis/` or another
evaluator's output. The evaluator returns one JSON object per scenario and
keeps requested model/effort separate from observed model/effort. The literal
string `unknown` is valid and must remain `unknown` when runtime telemetry is
not available.

## Deterministic checks

Run the validator and executable synthetic scenario checks from the repository
root:

```sh
python3 research/code-friction-11-v2/test_trial.py
python3 research/code-friction-11-v2/test_scenarios.py
```

After two fresh blind evaluations, validate the retained JSON arrays and
produce the agreement report with:

```sh
python3 research/code-friction-11-v2/trial.py aggregate \
  --packet research/code-friction-11-v2/packet \
  --evaluations research/code-friction-11-v2/analysis/evaluations/rubric-v2-eval-a.json \
                research/code-friction-11-v2/analysis/evaluations/rubric-v2-eval-b.json \
  --output research/code-friction-11-v2/analysis/aggregate-v2.json \
  --expected-per-scenario 2
```

The validator rejects duplicate evaluator identities, missing scenarios,
ratings outside the rubric, more than three observations, evidence references
to unknown anchors, partial work falsely marked complete, and a missing
not-applicable declaration for the Q&A scenario. The aggregator deduplicates
observations by stable `occurrence_id`, retaining parent/child and Close retry
provenance so one real finding counts once.

For audit, inspect `git status --short`, the scoped research diff, the frozen
manifest hashes, and the deterministic test command above. Reversal is a
normal reviewed revert removing `research/code-friction-11-v2/`; it has no
runtime impact. The superseded v1 calibration remains in
`research/code-friction-11/` with its rejected-calibration notice. Preserve
unrelated worktree changes when auditing or reverting.

## Trial boundary

This packet supports one initial trial set and at most one revised-rubric pass.
It does not claim statistical validity or compare model capability. The report
should state agreement and disagreement by dimension, evidence accuracy,
code-versus-environment separation, and measured time/token overhead only where
the evaluator runtime actually supplies those measurements.

