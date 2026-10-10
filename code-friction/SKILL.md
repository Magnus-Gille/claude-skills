---
name: code-friction
description: Capture a small, opt-in set of concrete code-changeability observations during a coding task and hand them to Close without affecting readiness.
---

# Code-friction capture

This skill records advisory evidence about how easy or difficult a coding change was to locate,
understand, and verify. It is not an agent score, quality gate, telemetry stream, or authorization
to write to Munin.

Capture is off by default. Begin only when the owner has enabled it for this task or the user
explicitly authorizes it. Continue noticing meaningful events during the work instead of waiting
until Close: record a concrete helpful or obstructive factor when it changes how the task proceeds.
Keep no more than three distinct observations for the task across all worker attempts. Quick Close
can flush prepared records but never invents observations; full Close can finalize an assessment.

Use this when a coding task encounters or benefits from a specific property of the code or its
environment, such as a hidden consumer that changes the implementation path or a deterministic test
that makes verification direct. Do not use it for ordinary Q&A, routine steps without a meaningful
friction or helpful factor, generalized agent performance claims, or a task without explicit opt-in.

Examples:

- Capture: a second known caller had to be traced before the behavior was understandable.
- Capture: an existing deterministic test isolated the changed behavior with no additional setup.
- Do not capture: “the task was hard” without a concrete, evidenced cause.
- Do not capture: a failed network or unavailable tool as a code difficulty; classify the cause as
  environmental and leave unsupported ratings not-assessable.

Before capture, read [the Close integration and persistence rules](../close/references/code-friction.md)
and [the bundled changeability rubric](../close/references/rubric.md). Keep summaries sanitized,
short, and free of code, prompts, transcripts, private locators, raw errors, or credentials. Use
opaque evidence references only. If safe minimization or evidence provenance is uncertain, omit the
observation. Do not make an extra evaluator call.

Prepare evidence only with an exact writable namespace supplied by the user or owner. Persist the
full Munin append arguments before sending; retry only those saved arguments and their stable
idempotency key after an uncertain response. Never guess classification. Report unavailable,
refused, or failed persistence as unsaved through the existing Close Persistence section. The
helper is local-only; it makes no network call and changes no Close renderer or readiness result.
