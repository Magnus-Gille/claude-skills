---
name: debate-claude
description: Run an adversarial debate with Claude to stress-test a draft, plan, research claim, or design decision. Use when Codex needs structured cross-model critique before finalizing a consequential decision, architecture, protocol, research claim, security assessment, or product priority.
---

# Adversarial Debate with Claude

Run a structured adversarial review using Claude as the external reviewer. This skill handles the full debate lifecycle: drafting, invoking Claude, responding, and recording outcomes. Claude is a *different* model from Codex — the cross-model gap is where the value comes from.

Use **Claude Fable at high effort**, with **Claude Opus at high effort as the automatic fallback**. Record the actual model reported by Claude in the summary and cost table.

## Git Handling

Debate files split into two tiers: **searchable artifacts** worth tracking, and **raw process logs** that aren't. Drafts, self-reviews, critiques, responses, and rebuttals are scratch paper — they are load-bearing *during* the debate and noise afterward. Summaries, critique logs, and the index are the searchable residue that has cross-debate reuse value (decision history, catch-rate tracking, "have I debated this before?" queries).

**Default pattern — track summaries, gitignore the rest.** In the project's `.gitignore`:

```
debate/*
!debate/INDEX.md
!debate/*-summary.md
!debate/*-critique-log.json
```

This commits `INDEX.md`, each debate's `*-summary.md`, and the structured `*-critique-log.json` files. Everything else (drafts, self-reviews, raw critiques, rebuttals, snapshots) stays local.

**Rationale:**
- Summaries distill the conclusions. They're what a reader actually needs.
- Critique logs are small, structured, and enable pattern recognition across debates (severity distributions, self-review catch rate trends, which critiques were rejected vs adopted).
- Raw rebuttals and drafts are verbose, context-specific, and rarely re-read. Keeping them out of git avoids repo bloat and leaking in-progress reasoning.
- INDEX.md is the directory — without it, committed summaries are orphaned.

**Exception — full tracking:** If the project specifically studies the debate *process* (methodology research, prompt engineering on the skill itself), commit everything. That's rare.

**Exception — nothing tracked:** If the debate outcome was fully incorporated into an ADR or plan file that's already committed, and no one will ever search for the debate again, gitignoring the whole `debate/` directory is fine too.

Before the first debate in a project, check if `debate/` is gitignored. If not, suggest adding the default pattern above. If it's already fully gitignored (the old default), suggest upgrading to the summaries-tracked pattern so the corpus accumulates.

## Reviewer CLI Invocation

**Correct syntax:**
```bash
printf '%s' "<prompt>" | claude -p \
  --no-session-persistence \
  --permission-mode dontAsk \
  --model fable \
  --fallback-model opus \
  --effort high 2>&1
```

**Important rules:**
- Use `claude -p` for non-interactive single-prompt invocation and provide the prompt via stdin.
- **Always pin `--model fable --fallback-model opus --effort high`.** The fallback is automatic when Fable is overloaded or unavailable; do not lower the effort for Opus.
- Use `--no-session-persistence --permission-mode dontAsk` for a stable headless run.
- Use the normal user/project settings first so Claude can access the configured Munin server.
- If startup hangs, retry once with `--setting-sources project --strict-mcp-config --mcp-config '{"mcpServers":{}}'` to disable user-level hooks, plugins, and MCP startup. When using this lean fallback, remove the Munin instructions from the prompt and note that the debate used repository context only.
- Capture the complete critique from stdout and have Codex write `debate/<topic>-claude-critique.md`. Do not rely on Claude to write the file.
- Set the shell tool timeout to 300000 ms; raise it to 600000 ms for large drafts or long high-effort runs.
- If Claude reports `Not logged in`, run `claude auth status`; authentication or login may need to be completed outside the sandbox.
- If the command hangs, retry once with `--debug-file /tmp/claude-headless-debug.log` and inspect the log before changing more variables.
- Verify the actual model from Claude's output. The fallback may mean a run used Opus even though Fable was requested.

## Munin Memory Access

Use Claude's configured Munin access to provide live project context. If the lean empty-MCP fallback is required, omit the Munin instructions from the prompt and note that the debate used repository context only.

Use this to give the reviewer **live** project context instead of pasting a snapshot into the prompt.

**Infer the Munin namespace from the current git repo** before invoking the reviewer:

```bash
git remote get-url origin 2>/dev/null | sed -E 's|.*/([^/]+?)(\.git)?$|projects/\1|'
```

- Example: repo `munin-memory` → namespace `projects/munin-memory`
- If the repo name doesn't map cleanly (fork, monorepo, cross-cutting topic), ask the user. Do not guess.
- If there is no matching Munin namespace at all (new project, methodology debate, topic not yet represented), skip the memory access instructions in the reviewer prompt and note this in the draft.

Pass the inferred namespace as a placeholder substitution into the reviewer prompts in Steps 3 and 6. Do **not** pre-assemble context into a file — let Claude self-serve from Munin at critique time, so Round 1 and Round 2 read live state rather than a stale snapshot.

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

Write Codex's position/assessment/plan to `debate/<topic>-codex-draft.md`.

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

These sections give both self-review and the reviewer concrete material to attack. A draft without them is not ready for review.

### Step 2: Self-review

Before invoking the reviewer, Codex critiques its own draft using the topic-specific checklist below. Write to `debate/<topic>-codex-self-review.md`.

**Identify the debate type first** and declare it as a structured field at the top of the self-review file:

```markdown
## Debate Type
Primary: <security | architecture | protocol | docs | priority>
Secondary: <type, if mixed> (omit if single-type)
```

This classification drives the type-specific prompts in Steps 3 and 6. For mixed-type debates, list the primary type first.

Then work through the relevant checklist. Be genuinely critical — this baseline reveals whether cross-model review adds value over self-review. The `caught_by_self_review` field in the critique log (Step 8) tracks this.

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

### Step 3: Invoke the reviewer (Round 1 critique)

Read the `## Debate Type` field from `debate/<topic>-codex-self-review.md` and include the matching type-specific block(s) below. The type-specific questions are **additive** — always include the universal adversarial framing, then layer on domain-specific attack vectors.

For **mixed-type debates**, include blocks for both primary and secondary types. Primary type block goes first.

Wrap the prompt body below in the command from the **Reviewer CLI Invocation** section.

```
You are acting as a grounded but adversarial reviewer.

Read the file debate/<topic>-codex-draft.md. [Additional context files to read if needed.]

LOAD PROJECT CONTEXT FROM MUNIN FIRST. You have full access to Munin memory tools. Before critiquing, run these calls in order — then STOP using memory tools and critique; do not perform a general handshake or wander:
1. memory_read(namespace: '<namespace>', key: 'synthesis') — load the current synthesized project state
2. If synthesis_age_days > 3, or the entry is marked stale, or missing → memory_read(namespace: '<namespace>', key: 'status') as fallback
3. memory_query(query: '<topic keywords>', tags: ['decision'], limit: 5) — surface prior decisions that may constrain or relate to this debate
4. Optionally call memory_history, memory_narrative, memory_commitments, or memory_patterns on the namespace if the debate type would benefit (architecture → narrative; priority → commitments; protocol → history)

Ground your critique in this live project state, not just the draft file. If the draft contradicts or omits something the memory shows, flag it as a first-class finding.

Your job is to critique this. Be skeptical but intellectually honest — no strawmanning. Ground critique in evidence, not opinion.

Universal:
- Acknowledge strengths before attacking weaknesses
- Be specific — cite concrete issues with file:line references, not vague concerns
- Flag unsupported claims, missing baselines, and methodological gaps

[Include the type-specific block(s) below that match the debate type]

OUTPUT: Begin with a brief 'Context loaded' section listing which memory tools you called, the exact model you are running as, and any notable gaps or conflicts between the draft and the memory state. Then print your full, complete critique as your final response in markdown. Do not attempt to write a file.
```

Capture Claude's stdout and have Codex write it to `debate/<topic>-claude-critique.md`. Verify the file in Step 4.

**Namespace substitution:** Before running, replace `<namespace>` with the value inferred from `git remote get-url origin` per the **Munin Memory Access** section above. If no Munin namespace applies (new project, cross-cutting topic), remove the entire `LOAD PROJECT CONTEXT FROM MUNIN FIRST` paragraph and the memory mention in the `OUTPUT` line before invoking the reviewer.

#### Type-specific prompt blocks

**Security debates — add:**
> Also specifically examine: trust boundary crossings and what validates each one, auth/authz/session failure modes under adversarial input, blast radius if any single component is compromised, secrets and credential handling throughout the lifecycle.

**Architecture debates — add:**
> Also specifically examine: scale/load/data-size assumptions baked into the design, coupling introduced and what it forecloses, degradation behavior under partial failure, operational burden (deployment, monitoring, incident response), reversibility cost if this turns out wrong.

**Protocol/API debates — add:**
> Also specifically examine: edge cases in the protocol state machine, behavior of in-flight requests during failures or restarts, client behavior on unexpected responses, versioning and backward-compatibility story, timeout/retry/idempotency semantics.

**Docs/process debates — add:**
> Also specifically examine: maintenance burden and who keeps this updated, conflicts with or duplication of existing documentation, whether the single source of truth is unambiguous, what a newcomer would need that is missing.

**Priority/product debates — add:**
> Also specifically examine: evidence supporting this priority over alternatives, opportunity costs, load-bearing assumptions about user or system behavior, what "done" looks like and how success would be measured, reversibility of the decision.

### Step 4: Verify reviewer output

Ensure `debate/<topic>-claude-critique.md` exists and is complete.

- Write the captured stdout to `debate/<topic>-claude-critique.md`.
- Sanity-check that it is the actual critique, not an authentication error, startup transcript, or brief summary under 500 characters.
- Confirm the `Context loaded` section reports `fable` or the `opus` fallback at high effort. If model or effort cannot be verified, flag that uncertainty in the summary.
- **File looks complete:** Proceed to Step 5.

### Step 5: Write Codex's response

Read the critique carefully. Write a response to `debate/<topic>-codex-response-1.md` with:
- **Concessions** — where the critique is valid, concede explicitly
- **Partial concessions** — where partially valid, explain what you accept and what you push back on
- **Defenses** — where you disagree, defend with evidence
- **Revised positions table** — summarize what changed

### Step 6: Invoke the reviewer (Round 2 rebuttal)

Run Claude again with the same Fable/high-effort command and Opus/high-effort fallback, pointing it to all files so far (draft, critique, response). **Re-read the `## Debate Type` field from the self-review and include the same type-specific prompt block(s) used in Step 3** so the rebuttal maintains the same domain-specific lens. Record the actual model used in each round; an automatic Fable-to-Opus fallback is allowed, but never deliberately lower model quality or effort mid-debate.

**Re-load project context from Munin.** Include the same `LOAD PROJECT CONTEXT FROM MUNIN FIRST` paragraph from Step 3 (with the same inferred `<namespace>`). Round 2 may happen minutes or hours after Round 1 — memory state may have moved. Instruct the reviewer to note if synthesis, status, or decisions have changed since Round 1 and let that shape the rebuttal. If no Munin namespace applies, omit the paragraph as in Step 3.

Ask the reviewer to:
- Acknowledge which concessions are genuine and adequate
- Identify where defenses are valid vs where they dodge the point
- Flag any new issues that emerged, including domain-specific risks from the Step 3 type block
- Flag any drift between Round 1 and Round 2 memory state (new decisions, status updates)
- Give a final verdict on the single most important next step

Output capture is the same as Step 3: Claude prints to stdout and Codex writes `debate/<topic>-claude-rebuttal-1.md`.

### Step 7: Additional rounds (if needed)

**Most debates end after 2 rounds.** Only continue if Round 2 surfaced genuinely new issues that weren't addressed. Add rounds as:
- `debate/<topic>-codex-response-N.md`
- `debate/<topic>-claude-rebuttal-N.md`

Stop when: (a) both sides are repeating themselves, (b) remaining disagreements are preference not substance, or (c) the cost of another round exceeds the value of resolving the remaining issues.

### Step 8: Structured critique log

Create `debate/<topic>-critique-log.json` with every critique point from all rounds:

```json
[
  {
    "id": "<topic>-C01",
    "source": "claude-round-1",
    "text": "Brief description of the critique point",
    "classification": "valid | partially_valid | invalid",
    "impact": "changed | partially_changed | acknowledged | deferred | rejected",
    "severity": "critical | major | minor",
    "caught_by_self_review": true | false
  }
]
```

The `source` field encodes Claude and the round, e.g. `claude-round-1` or `claude-round-2`. Keep it consistent so the periodic-synthesis pass can compare catch rates and severity distributions across debates.

**Impact values:**
- `changed` — position or plan materially changed as a result
- `partially_changed` — partial change; some aspects adopted, others defended
- `acknowledged` — accepted as valid but no immediate action taken
- `deferred` — valid point, intentionally set aside for later
- `rejected` — disagreed with and defended

**Severity measures the consequence of ignoring the critique point**, anchored to two dimensions:

- **critical** — Ignoring this would cause a correctness, security, or design flaw with **wide blast radius** (affects multiple components, users, or data paths) AND the resulting damage is **hard to reverse** once shipped or committed to.
- **major** — Ignoring this is a real problem, but either the blast radius is **contained** (affects one component or a narrow path) OR the damage is **reversible** with reasonable effort.
- **minor** — Valid observation, but ignoring it has **low consequence** — cosmetic, stylistic, or affects edge cases that are unlikely to matter in practice.

When in doubt between two levels, ask: "If we ship with this issue and discover it in 3 months, how bad is the recovery?" Hard recovery = bump up. Easy recovery = keep it where it is.

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
- Reviewer critique/rebuttal files (the reviewer may echo back paths or identifiers from project context)
- **Reviewer critique/rebuttal files that quote memory-tool output** — Claude may load project state from Munin, so critiques may quote `clients/<name>/*`, `people/<name>/*`, or cross-references that expose private relationships. Scrub namespace paths containing real names, and collapse `clients/<name>/...` → `clients/<client>/...` when in doubt.
- Critique log JSON files (may contain quoted content with paths)
- Snapshots of project files used as debate input

### Step 9: Write the summary

Create `debate/<topic>-summary.md` with:
- Date, participants, exact Claude model used in each round (`fable` or fallback `opus`), effort (`high`), and round count
- Concessions accepted by both sides
- Defenses accepted by the reviewer
- Unresolved disagreements
- New issues from later rounds
- Final verdict (both sides' positions)
- Action items with owners (if applicable)
- List of all debate files
- If the actual Claude model or effort could not be verified, **flag that explicitly** here.

Append a cost table at the end. The `Model` column records the actual reviewer model so cost and quality can be tracked:

```
## Costs
| Invocation        | Wall-clock time | Model              |
|-------------------|-----------------|--------------------|
| Claude R1         | ~Nm             | fable / opus fallback |
| Claude R2         | ~Nm             | fable / opus fallback |
```

### Step 10: Update debate index

Append a row to `debate/INDEX.md` (create the file if it doesn't exist). The `Reviewer` column keeps the index compatible with the source debate skill and lets periodic synthesis compare reviewer families:

```markdown
# Debate Index

| Date | Topic | Reviewer | Rounds | Key decision | Critique points | Self-review catch rate |
|------|-------|----------|--------|--------------|----------------|-----------------------|
| YYYY-MM-DD | [topic](topic-summary.md) | claude | N | One-line outcome | X | Y/X (Z%) |
```

If an existing `INDEX.md` predates the `Reviewer` column, add the column to the header and backfill prior rows with the reviewer that produced them when known; otherwise use `unknown`.

### Step 11: Verify completeness

Confirm all required files exist before finishing:
- `debate/<topic>-codex-draft.md`
- `debate/<topic>-codex-self-review.md`
- `debate/<topic>-claude-critique.md`
- `debate/<topic>-codex-response-1.md`
- `debate/<topic>-claude-rebuttal-1.md`
- `debate/<topic>-summary.md`
- `debate/<topic>-critique-log.json`
- `debate/INDEX.md` updated

If any are missing, create them before declaring the debate complete.

## Prompting Principles for the Reviewer

- Ask the reviewer to **critique the specific artifact**, not generate alternatives
- Instruct it to be **skeptical but intellectually honest** — no strawmanning
- Require **evidence-grounded** critique, not opinion
- Ask it to **flag unsupported claims, missing baselines, and methodological gaps**
- Ask it to **acknowledge strengths before attacking weaknesses**
- Request **file:line references** for concrete issues
- Give the reviewer sufficient context — point it to relevant project files, not just the draft
- Keep the prompt tightly scoped and directive; require the full critique in the final stdout response since Codex captures it from there

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
