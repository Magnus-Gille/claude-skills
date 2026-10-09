# Blind code-friction rubric

Rate the requested task, not the model, the evaluator, or a general notion of
how hard software is. Use exactly one rating for each applicable dimension:
`easy`, `manageable`, `difficult`, or `not-assessable`.

The dimensions are:

| Dimension | easy | manageable | difficult | not-assessable |
| --- | --- | --- | --- | --- |
| Locate code | One obvious owning file/symbol is present. | Two or three related files, or one indirection, must be followed. | Ownership is distributed, ambiguous, or a hidden consumer must be discovered. | The task has no code location to assess, or the supplied material cannot support a location claim. |
| Understand consequences | The behavior is local and the affected contract is explicit. | A few known callers, data paths, or compatibility details must be checked. | A hidden consumer, cross-layer contract, or incomplete state makes impact reasoning materially uncertain. | The material is insufficient to make a grounded consequence claim. |
| Verify change | A deterministic, available check directly exercises the requested behavior. | Verification needs a small targeted setup, multiple checks, or an explicit contract inspection. | Verification spans layers or remains materially uncertain even with the supplied checks. | A required environment/tool is unavailable, or the task has no change to verify. |

For a pure Q&A or otherwise out-of-scope scenario, set `applicability` to
`not_applicable` and use `not-assessable` for all three dimensions. Explain the
reason in the dimension objects. Do not turn “not applicable” into an ease
rating.

Keep code friction separate from tool and infrastructure friction:

- `friction_class: code` means the supplied code/task creates the difficulty.
- `friction_class: environment` means a missing runtime, service, dependency,
  permission, or other external condition limits verification.
- `friction_class: mixed` is allowed only when both are evidenced.
- `friction_class: not_applicable` is required for a not-applicable task.

Give at most three concise observations per scenario. Each observation is
positive or negative, names the affected dimension, and cites one or more
anchor IDs from the scenario. Do not invent evidence, run commands outside the
supplied packet, or cite hidden analysis.

