# Two-round debate protocol

The default debate has two rounds. The conductor owns all writing, invocation, context selection, and acceptance decisions. Read [reviewer safety](reviewer.md) before invoking Claude and [type lenses](lenses.md) before writing the self-review.

## Step 0: Freeze the artifact and round package

Freeze the artifact being reviewed so every condition refers to the same version.

- For one file, copy it to `debate/<topic>-snapshot.md` or the appropriate extension.
- For multiple files, create `debate/<topic>-snapshot/` with copies.
- If already committed and guaranteed not to change, record `Snapshot: commit <hash>, file(s): <path>, <path>`.

Before each reviewer invocation, create a separate scoped, sanitized round package. Include the snapshot, the draft material needed for the round, and only context explicitly selected by the conductor. The package is sent through stdin; the reviewer does not inspect live state. Round 2 must be a newly frozen package containing the Round 1 response and any explicitly refreshed context. If live Munin state would be useful, the conductor may read it separately and include a sanitized excerpt with its retrieval time and source; never give the reviewer direct Munin access.

## Step 1: Write the draft

Write Codex's position, assessment, or plan to `debate/<topic>-codex-draft.md`.

Every draft includes these sections, regardless of topic:

```markdown
## Assumptions
[Load-bearing assumptions — things that must be true for this to work]

## Failure Modes
[What goes wrong if this fails? How does it fail? What's the blast radius?]

## Alternatives Rejected
[Options considered and discarded, and why]

## Unknowns
[What remains uncertain and could invalidate this position]
```

## Step 2: Self-review

Before invoking Claude, write `debate/<topic>-codex-self-review.md`. Start with the structured type declaration from [lenses](lenses.md), then work through the universal checklist and each declared type-specific checklist. Be genuinely critical: the self-review establishes what the cross-model critique adds. The `caught_by_self_review` field in the critique log records this comparison.

## Step 3: Round 1 critique

Read the declared type from the self-review and assemble the prompt envelope in [reviewer safety](reviewer.md). Add the matching type-specific lens from [lenses](lenses.md). Include the complete frozen package through stdin. The reviewer prompt must:

- Ask for an evidence-grounded critique of the specific draft, not a replacement design.
- Require strengths before weaknesses, concrete references, unsupported-claim checks, missing baselines, and methodological gaps.
- State that the package is the sole context and that no tools or files should be accessed.
- Require a `Context loaded` section listing only package sections actually received and any gaps or conflicts.

Capture structured output and stdout yourself. Write the critique to `debate/<topic>-claude-critique.md`; do not rely on Claude to write it.

## Step 4: Verify Round 1

Ensure the critique exists and is substantive. Reject or flag output that is an authentication error, startup transcript, or brief summary under 500 characters. Confirm the machine-readable result supplies the requested/actual model metadata; if it does not, record the uncertainty rather than inferring it from prose. Check that the `Context loaded` section reports only the frozen package.

## Step 5: Write Codex's response

Read the critique carefully and write `debate/<topic>-codex-response-1.md` with:

- **Concessions** — where the critique is valid, concede explicitly.
- **Partial concessions** — where partially valid, explain what is accepted and what is disputed.
- **Defenses** — where there is disagreement, defend with evidence from the frozen package or explicitly supplied sources.
- **Revised positions table** — summarize what changed.

## Step 6: Round 2 rebuttal

Create a new frozen, sanitized Round 2 package containing the draft, self-review, Round 1 critique, and response. Include refreshed project context only when the conductor explicitly selects and sanitizes it. This makes context drift visible: if the conductor supplies changed decisions or status, label the change and its source.

Use the same exact model, effort, isolation, universal framing, and declared type lens as Round 1. Follow [reviewer safety](reviewer.md), and ask the reviewer to:

- Acknowledge which concessions are genuine and adequate.
- Identify where defenses are valid and where they dodge the point.
- Flag new issues, including risks from the type-specific lens.
- Flag differences between the explicitly supplied Round 1 and Round 2 context.
- Give a final verdict on the single most important next step.

Capture the structured result and stdout, then write `debate/<topic>-claude-rebuttal-1.md`. Verify it is a substantive rebuttal before continuing.

## Step 7: Additional rounds

Most debates stop after two rounds. Continue only when Round 2 surfaces a genuinely new issue that cannot be resolved from the existing response. Add:

- `debate/<topic>-codex-response-N.md`
- `debate/<topic>-claude-rebuttal-N.md`

Freeze a fresh package for every additional round. Stop when both sides repeat themselves, remaining disagreements are preference rather than substance, or another round costs more than the value of resolving the issue.
