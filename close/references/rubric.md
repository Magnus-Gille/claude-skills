# Changeability 1.0 rubric

Assess each dimension separately from evidence in the task. Do not compute an aggregate score.

| Dimension | Easy | Manageable | Difficult |
| --- | --- | --- | --- |
| Locate | One obvious owning file or symbol | Two or three related files, or one indirection | Distributed or ambiguous ownership, or a hidden consumer |
| Understand | Local behavior and explicit contract | A few known callers, data paths, or compatibility details | Hidden consumers, cross-layer contracts, or materially uncertain state |
| Verify | An available deterministic direct check | Small setup, several checks, or contract inspection | Validation spans layers or remains materially uncertain despite available checks |

`not-assessable` is a separate value, never zero or easy. Pure Q&A is not applicable and all three
ratings are not-assessable. If the verification environment is unavailable, Verify is
not-assessable while Locate and Understand may remain assessable. Keep code, environment, and
evidenced mixed causes separate; an environmental failure does not automatically lower the code
rating. Ground each assessable rating in bounded source references.

Keep at most three concise observations per assessment. Each describes one concrete helpful or
obstructive factor, with polarity and cause, and may include supporting and counter-evidence
references. Missing evidence is not an easy rating; partial, failed, or aborted attempts cannot be
marked as a complete assessment.
