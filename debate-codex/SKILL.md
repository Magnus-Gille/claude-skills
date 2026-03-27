---
name: debate-codex
description: Run an adversarial debate with Codex to stress-test a draft, plan, research claim, or design decision. Use this whenever you need structured critique before finalizing decisions.
argument-hint: [topic or file to debate]
---

# Adversarial Debate with Codex

Run a structured adversarial review using the Codex CLI. This skill handles the full debate lifecycle: drafting, invoking Codex, responding, and recording outcomes.

## Git Handling

Debate files are **process artifacts**, not deliverables. By default, add `debate/` to `.gitignore`. The summaries and critique logs are useful but belong in project documentation if needed — copy the relevant conclusions into your actual docs/ADRs rather than tracking the raw debate files.

If the project specifically studies the debate process itself (methodology research), track the files. But that's the exception.

Before the first debate in a project, check if `debate/` is gitignored. If not, suggest adding it.

## Codex CLI Invocation

**Correct syntax:**
```bash
script -q /dev/null codex exec --full-auto "<prompt>" 2>&1
```

**Important rules:**
- Wrap with `script -q /dev/null` to provide a pseudo-TTY (Codex auth fails without one when invoked from Claude Code)
- Use `codex exec --full-auto` — NOT `codex -q` or other flags
- Do NOT use the `-o` flag to capture critique content. The `-o` flag writes Codex's final conversational summary, not the file it created. Instead, instruct Codex to write its output file directly (it has workspace-write access via `--full-auto`).
- Set `--timeout 300000` on the Bash tool call (Codex can take a few minutes)
- Codex works in the repo's working directory and can read all project files

## Debate Protocol

### Step 0: Snapshot the artifact

Freeze the artifact being reviewed so all review conditions run against the same version.

- **Single file:** Copy to `debate/<topic>-snapshot.md` (or appropriate extension).
- **Multiple files:** Create `debate/<topic>-snapshot/` directory with copies.
- **Already committed and won't change during debate:** Record the reference instead:
  ```
  Snapshot: commit <hash>, file(s): <path>, <path>
  ```

### Step 1: Write the draft

Write Claude's position/assessment/plan to `debate/<topic>-claude-draft.md`.

**Every draft must include these four sections**, regardless of topic type:

```markdown
## Assumptions
[List load-bearing assumptions — things that must be true for this to work]

## Failure Modes
[What goes wrong if this fails? How does it fail? What's the blast radius?]

## Alternatives Rejected
[What options were considered and discarded, and why]

## Unknowns
[What remains uncertain that could invalidate this position]
```

These sections give both self-review and Codex concrete material to attack. A draft without them is not ready for review.

### Step 2: Self-review

Before invoking Codex, Claude critiques its own draft using the topic-specific checklist below. Write to `debate/<topic>-claude-self-review.md`.

**Identify the debate type first,** then work through the relevant checklist. Be genuinely critical — this baseline reveals whether cross-model review adds value over self-review. The `caught_by_self_review` field in the critique log (Step 8) tracks this.

#### Universal checklist (all types)
- [ ] What assumptions in the draft might not hold? Are they listed in the Assumptions section?
- [ ] Are the failure modes exhaustive, or just the obvious ones?
- [ ] What's the strongest argument *against* my own position?
- [ ] What evidence or baseline is missing?
- [ ] What operational/maintenance burden is hidden or understated?

#### Security debates
- [ ] What are the trust boundaries? What crosses them?
- [ ] What happens if an attacker controls a key input or state?
- [ ] Are auth, authz, and session management failure modes covered?
- [ ] What's the blast radius of a compromise?
- [ ] Are secrets, keys, and credentials handled correctly throughout?

#### Architecture debates
- [ ] What scale, load, or data-size assumptions are baked in?
- [ ] What coupling is being introduced, and what does it preclude later?
- [ ] How does the system degrade under partial failure?
- [ ] What's the operational burden (deployment, monitoring, incident response)?
- [ ] What's the reversibility cost if this turns out to be wrong?

#### Protocol/API debates
- [ ] What are the edge cases in the protocol state machine?
- [ ] What happens to in-flight requests during failures or restarts?
- [ ] What does a client do when it gets an unexpected response?
- [ ] What's the versioning and backward-compatibility story?
- [ ] What are the timeout, retry, and idempotency semantics?

#### Docs/process debates
- [ ] What's the maintenance burden? Who keeps this updated?
- [ ] Where does this conflict with or duplicate existing documentation?
- [ ] What's the single source of truth, and is it unambiguous?
- [ ] What would a newcomer need that's missing here?

#### Priority/product debates
- [ ] What evidence supports this priority over alternatives?
- [ ] What are the opportunity costs of this choice?
- [ ] What assumptions about user or system behavior are load-bearing?
- [ ] What does "done" look like, and how would we know if it worked?
- [ ] What's the reversibility of this decision?

### Step 3: Invoke Codex (Round 1 critique)

```bash
script -q /dev/null codex exec --full-auto "You are acting as a grounded but adversarial reviewer.

Read the file debate/<topic>-claude-draft.md. [Additional context files to read if needed.]

Your job is to critique this. Be skeptical but intellectually honest — no strawmanning. Ground critique in evidence, not opinion. Specifically:
- [List specific questions for this debate]
- Acknowledge strengths before attacking weaknesses
- Be specific — cite concrete issues with file:line references, not vague concerns

Write your full critique to debate/<topic>-codex-critique.md in markdown format." 2>&1
```

### Step 4: Verify Codex output

Read `debate/<topic>-codex-critique.md`. Check for these failure modes:

- **File missing:** Codex didn't write it. Extract the critique content from the Bash tool output (the Codex execution log) and write it to the file.
- **File is a brief summary (< 500 chars):** Codex wrote a conversational summary instead of the full critique. Same recovery — pull the real content from the execution log.
- **File looks complete:** Proceed to Step 5.

### Step 5: Write Claude's response

Read the critique carefully. Write a response to `debate/<topic>-claude-response-1.md` with:
- **Concessions** — where the critique is valid, concede explicitly
- **Partial concessions** — where partially valid, explain what you accept and what you push back on
- **Defenses** — where you disagree, defend with evidence
- **Revised positions table** — summarize what changed

### Step 6: Invoke Codex (Round 2 rebuttal)

Run Codex again, pointing it to all files so far (draft, critique, response). Ask it to:
- Acknowledge which concessions are genuine and adequate
- Identify where defenses are valid vs where they dodge the point
- Flag any new issues that emerged
- Give a final verdict on the single most important next step

Write to `debate/<topic>-codex-rebuttal-1.md`.

### Step 7: Additional rounds (if needed)

**Most debates end after 2 rounds.** Only continue if Round 2 surfaced genuinely new issues that weren't addressed. Add rounds as:
- `debate/<topic>-claude-response-N.md`
- `debate/<topic>-codex-rebuttal-N.md`

Stop when: (a) both sides are repeating themselves, (b) remaining disagreements are preference not substance, or (c) the cost of another round exceeds the value of resolving the remaining issues.

### Step 8: Structured critique log

Create `debate/<topic>-critique-log.json` with every critique point from all rounds:

```json
[
  {
    "id": "<topic>-C01",
    "source": "codex-round-1",
    "text": "Brief description of the critique point",
    "classification": "valid | partially_valid | invalid",
    "impact": "changed | partially_changed | acknowledged | deferred | rejected",
    "severity": "critical | major | minor",
    "caught_by_self_review": true | false
  }
]
```

**Impact values:**
- `changed` — position or plan materially changed as a result
- `partially_changed` — partial change; some aspects adopted, others defended
- `acknowledged` — accepted as valid but no immediate action taken
- `deferred` — valid point, intentionally set aside for later
- `rejected` — disagreed with and defended

Classification and impact should be filled after the debate concludes.

**Periodic synthesis (every 5–10 debates):** Look at `impact` across recent critique logs. Which severity levels produce the most `changed` outcomes? Which `critical` points were `rejected`? Which `minor` points drove `changed`? Revise the Step 2 checklists if a pattern is consistent. This is more useful than per-debate instrumentation.

### Step 8.5: Sanitize PII in debate artifacts

Before writing the summary, scan all debate files for PII and local environment details that should not appear in public repos:

- **Local paths:** Replace `/Users/<username>/...` or `/home/<username>/...` with `<home>/...` or `<repo-root>/...`
- **Email addresses:** Replace personal emails (not `noreply@` addresses) with `<email>` unless they are the repo owner's intentionally public email
- **Names of non-public individuals:** Replace with role descriptions (e.g., "the client contact") unless the person is a public figure or has given consent
- **Internal hostnames/IPs:** Replace with `<hostname>` or `<ip>` placeholders
- **API keys, tokens, credentials:** Should never appear — if found, replace with `<redacted>`

Apply these replacements to all `debate/<topic>-*` files created in this debate. This is especially important for:
- Codex critique/rebuttal files (Codex may echo back paths or identifiers from project context)
- Critique log JSON files (may contain quoted content with paths)
- Snapshots of project files used as debate input

### Step 9: Write the summary

Create `debate/<topic>-summary.md` with:
- Date, participants, and round count
- Concessions accepted by both sides
- Defenses accepted by Codex
- Unresolved disagreements
- New issues from later rounds
- Final verdict (both sides' positions)
- Action items with owners (if applicable)
- List of all debate files

Append a cost table at the end:

```
## Costs
| Invocation | Wall-clock time | Model version |
|------------|-----------------|---------------|
| Codex R1   | ~Nm             | gpt-5.3-codex |
| Codex R2   | ~Nm             | gpt-5.3-codex |
```

### Step 10: Update debate index

Append a row to `debate/INDEX.md` (create the file if it doesn't exist):

```markdown
# Debate Index

| Date | Topic | Rounds | Key decision | Critique points | Self-review catch rate |
|------|-------|--------|--------------|----------------|-----------------------|
| YYYY-MM-DD | [topic](topic-summary.md) | N | One-line outcome | X | Y/X (Z%) |
```

### Step 11: Verify completeness

Confirm all required files exist before finishing:
- `debate/<topic>-claude-draft.md`
- `debate/<topic>-claude-self-review.md`
- `debate/<topic>-codex-critique.md`
- `debate/<topic>-claude-response-1.md`
- `debate/<topic>-codex-rebuttal-1.md`
- `debate/<topic>-summary.md`
- `debate/<topic>-critique-log.json`
- `debate/INDEX.md` updated

If any are missing, create them before declaring the debate complete.

## Prompting Principles for Codex

- Ask Codex to **critique the specific artifact**, not generate alternatives
- Instruct it to be **skeptical but intellectually honest** — no strawmanning
- Require **evidence-grounded** critique, not opinion
- Ask it to **flag unsupported claims, missing baselines, and methodological gaps**
- Ask it to **acknowledge strengths before attacking weaknesses**
- Request **file:line references** for concrete issues
- Give Codex sufficient context — point it to relevant project files, not just the draft

## When to Run a Debate

- Architectural decisions or significant design changes
- Research claims or evidence assessments
- Experiment design and methodology
- Evaluation of results before drawing conclusions
- Any decision where blind spots could be costly
- Plans that are hard to reverse once committed

## When NOT to Run a Debate

- Typo fixes, formatting changes, comment edits
- Decisions already resolved in a previous debate (check `debate/INDEX.md`)
- Time-sensitive fixes where the cost of delay exceeds the risk of blind spots
- Implementation details with no architectural or correctness impact
- Purely mechanical refactors with well-defined transformations
