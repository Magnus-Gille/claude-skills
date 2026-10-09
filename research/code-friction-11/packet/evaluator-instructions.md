# Blind evaluator instructions

You are evaluating one synthetic scenario at a time from `scenarios.json`,
using `rubric.md`. Do not search the surrounding repository, consult another
answer, infer hidden expected ratings, or execute commands that require files
outside this packet. Read the task and all supplied synthetic files before
rating it.

Return one JSON object with this shape:

```json
{
  "schema_version": "code-friction-11.eval.v1",
  "evaluation_id": "<fresh opaque id>",
  "evaluator_id": "<run-provided id>",
  "scenario_id": "<scenario id>",
  "requested_model": "<configured request or unknown>",
  "requested_effort": "<configured request or unknown>",
  "observed_model": "<runtime observation or unknown>",
  "observed_effort": "<runtime observation or unknown>",
  "elapsed_seconds": "<number or unknown>",
  "input_tokens": "<integer or unknown>",
  "output_tokens": "<integer or unknown>",
  "task_status": "planned | completed | partial | failed | aborted | qa_only",
  "completion_claim": false,
  "applicability": "applicable | not_applicable",
  "environment": {
    "status": "available | unavailable | partial | unknown",
    "friction_class": "code | environment | mixed | not_applicable",
    "notes": "short evidence-based note"
  },
  "ratings": {
    "locate": {"rating": "easy", "friction_class": "code", "reason": "..."},
    "understand": {"rating": "manageable", "friction_class": "code", "reason": "..."},
    "verify": {"rating": "not-assessable", "friction_class": "environment", "reason": "..."}
  },
  "observations": [
    {
      "observation_id": "<fresh id>",
      "occurrence_id": "<stable finding occurrence id>",
      "polarity": "positive | negative",
      "dimension": "locate | understand | verify",
      "claim": "one concise observation",
      "evidence_refs": ["<scenario anchor id>"],
      "source": {
        "kind": "direct | child | parent | close_retry",
        "attempt_id": "<attempt id>",
        "parent_observation_id": null
      }
    }
  ]
}
```

Use the literal string `unknown` whenever the runtime cannot supply a model,
effort, elapsed time, or token count. Do not estimate those values. Keep the
two requested fields distinct from the two observed fields.

Use `task_status: partial`, `failed`, or `aborted` and
`completion_claim: false` if the supplied work is incomplete or stopped. For a
pure Q&A task use `task_status: qa_only`, `applicability: not_applicable`, and
`friction_class: not_applicable`.

Return at most three observations. Evidence references must be anchor IDs from
the current scenario. The `occurrence_id` is the stable identity of one real
finding; a child observation, parent summary, or Close retry of that finding
must reuse the same occurrence ID. The validator uses this identity to count
one occurrence once while preserving provenance.

