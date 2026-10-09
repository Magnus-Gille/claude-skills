# Aggregation protocol

Run exactly two fresh evaluations for every scenario with the same requested
model and requested effort. Keep `requested_*` and `observed_*` values as
separate fields. Never replace `unknown` with a guessed runtime value.

For each dimension, report both raw ratings and an agreement boolean. A
disagreement is a pair of different valid ratings, including a disagreement
between a code-friction rating and `not-assessable` caused by environment
limits. Report evidence accuracy by comparing cited anchor IDs and claims with
the supplied scenario anchors and separately held analysis; do not treat
agreement alone as evidence accuracy.

Report code/environment separation from the evaluation `friction_class` and
environment status. Scenario S4 is the explicit environment test: an
unavailable runtime should affect verification assessability, not erase the
code location. Scenario S6 is explicit not-applicable and should remain out of
changeability totals.

Observations are deduplicated by `occurrence_id`, not by evaluator ID,
observation ID, attempt ID, or wording. The output retains every observation
ID, evaluator ID, and complete source object, including source kind, attempt
ID, and parent observation ID. Thus a child observation summarized by a parent
and repeated by a Close retry contributes one occurrence while its full
provenance remains inspectable. If the same occurrence ID has conflicting
dimensions or polarities, retain it once and emit a collision warning for
human review.

Do not infer time or token overhead. The report may calculate medians only over
numeric values present in the two evaluator outputs and must show the sample
count. Missing values remain unknown.

After the initial trial, allow at most one revision of the rubric and rerun the
same packet. Stop or rescope if the intended code/environment or paired
simplification distinction remains unreliable; this is calibration evidence,
not statistical validation or a model leaderboard.

