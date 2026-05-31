---
name: debate
description: Run an adversarial debate with a cross-model reviewer (Codex or Antigravity/agy) to stress-test a draft, plan, research claim, or design decision. Use this whenever you need structured critique before finalizing decisions.
argument-hint: [--model codex|agy] [topic or file to debate]
---

# Adversarial Debate (cross-model)

Run a structured adversarial review using an external reviewer model. This skill handles the full debate lifecycle: drafting, invoking the reviewer, responding, and recording outcomes. The reviewer is a *different* model from Claude — the cross-model gap is where the value comes from.

Two reviewer backends are supported, selected per invocation (see **Reviewer Selection** below):

- **`codex`** — OpenAI Codex CLI. Model-pinnable, stable, and the existing corpus of critique logs was built with it.
- **`agy`** — Google Antigravity CLI (Gemini). The forward path as Codex's free tier winds down.

The entire debate protocol — draft, self-review, response cycle, critique log, summary, index — is **identical regardless of backend**. Only the **Reviewer CLI Invocation** section branches by model. Throughout this skill, `<reviewer>` is a placeholder for the chosen backend (`codex` or `agy`); it appears in filenames and in the critique log's `source` field so cross-model results stay comparable.

## Reviewer Selection

Pick the backend at invocation time:

- Explicit flag: `/debate --model agy <topic>` or `/debate --model codex <topic>`.
- If the user names a model in prose ("debate this with agy"), honor it.
- **Default when unspecified: `codex`.** It is the proven-reliable backend, supports inline model pinning, and keeps the critique-log corpus consistent with prior debates (catch-rate trends stay comparable). Switch the default to `agy` once its reviewer model is reliably pinned to a Pro tier and its auth is stable in this environment.

Record the chosen backend in the draft header and carry it through every file name and log entry for the debate.

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

This is the **only** section that branches by backend. Steps 3 and 6 reference "invoke the reviewer" — use the block matching the selected `<reviewer>`. The prompt body (adversarial framing, type-specific blocks, Munin instructions) is identical across backends; only the command wrapper and output-capture mechanics differ.

### Backend: `codex`

**Correct syntax:**
```bash
script -q /dev/null codex exec --sandbox workspace-write --skip-git-repo-check -m gpt-5.5 -c model_reasoning_effort='"xhigh"' "<prompt>" 2>&1
```

**Important rules:**
- Wrap with `script -q /dev/null` to provide a pseudo-TTY (Codex auth fails without one when invoked from Claude Code)
- Use `codex exec --sandbox workspace-write` — NOT `codex -q`, and NOT the deprecated `--full-auto` (Codex 0.132+ warns and `--sandbox workspace-write` is the replacement). Add `--skip-git-repo-check` so it runs in non-git working dirs too (e.g. `~/mimir/mgc`); without it Codex refuses with "Not inside a trusted directory".
- **Always pin the strongest model and effort** for debates: `-m gpt-5.5 -c model_reasoning_effort='"xhigh"'`. `gpt-5.5` is the current Codex-recommended frontier model; verify with `codex exec -m gpt-5.5 ...` before relying on it. If unavailable in the active account (e.g., API-key auth without ChatGPT sign-in), fall back to `-m gpt-5.4`. Debates are high-stakes adversarial reviews — use the strongest available model at "Extra High" effort, not the global `config.toml` default (which is tuned for everyday use). The `'"xhigh"'` quoting is intentional: the outer single quotes protect from shell interpolation, the inner double quotes make the value a TOML string literal.
- Do NOT use the `-o` flag to capture critique content. The `-o` flag writes Codex's final conversational summary, not the file it created. Instead, instruct Codex to write its output file directly (it has workspace-write access via `--sandbox workspace-write`).
- Set `--timeout 300000` on the Bash tool call (Codex can take a few minutes; with `xhigh` effort it may run longer — consider `--timeout 600000`)
- Codex works in the repo's working directory and can read all project files

### Backend: `agy` (Antigravity / Gemini)

**Correct syntax:**
```bash
agy --print --dangerously-skip-permissions "<prompt>" 2>&1
```

**Important rules:**
- `agy --print` runs a single prompt non-interactively. No pseudo-TTY wrapper is needed (unlike Codex), but auth must already be established (see auth note below).
- `--dangerously-skip-permissions` is **required** in headless mode — without it, agy blocks on a permission prompt the moment it tries to read a file, run a command, or call an MCP tool, and the run hangs until it times out. The debate prompt only asks agy to read project files and (optionally) call Munin, so the scope is bounded.
- **Add `--add-dir <repo-root>`** if the debate files live outside agy's default workspace, so it can read the draft. From the repo root this is usually unnecessary.
- **No per-prompt model flag exists.** agy uses the model set via the sticky interactive `/model` command, which persists across sessions. The out-of-box default is **Gemini 3.5 Flash** — the fast/cheap tier, *wrong* for adversarial review. Before relying on agy for debates, set a Pro-tier reasoning model once: run `agy` interactively, type `/model`, pick the strongest Gemini (e.g. a 3.x Pro), exit. **Verify the active model at the start of a debate** by checking the reviewer's `Context loaded` header or asking it; if it reports Flash, warn the user and recommend they switch via `/model` before continuing — a Flash-tier critique is materially weaker and should be flagged in the summary.
- **Capture critique via stdout, not a written file.** agy on the Flash tier is chatty and unreliable at the "write your output to file X" instruction (it tends to narrate or run a handshake instead). The robust pattern is: instruct agy to print its **complete** critique to stdout as its final response, capture the Bash tool output, and have *Claude* write `debate/<topic>-agy-critique.md` from that output. (This is the same recovery path Codex uses in Step 4 when its file is missing — for agy, make it the default.)
- Set `--timeout 300000` on the Bash tool call; raise to `600000` for large drafts.
- **Auth note:** agy's OAuth token expires (observed: hours to days) and `--print` will re-emit a `Waiting for authentication` URL when stale. agy writes auth prompts directly to the **TTY**, so they cannot be fed through a pipe — if a debate run prints an auth URL, stop and ask the user to refresh by running `agy --print 'hi'` interactively in their terminal (via the `!` prefix), complete the browser flow, then re-run the debate step.
- agy works in the current working directory and can read project files (confirmed via its file tools); it also has Munin access (see below).

## Munin Memory Access

**Both backends have Munin access**, so the live-context approach applies regardless of reviewer:
- **Codex** is configured with the full Munin memory tool surface (`memory_read`, `memory_query`, `memory_orient`, `memory_history`, `memory_narrative`, `memory_commitments`, `memory_patterns`, `memory_insights`, `memory_handoff`, `memory_resume`, `memory_attention`, `memory_extract`, `memory_read_batch`, `memory_get`, `memory_list`, `memory_status`).
- **agy** reaches Munin through a bridge (observed: it runs `memory_orient` on its own and resolves the same `projects/*` namespaces). Treat its memory surface as equivalent for debate purposes.

Use this to give the reviewer **live** project context instead of pasting a snapshot into the prompt.

**Infer the Munin namespace from the current git repo** before invoking the reviewer:

```bash
git remote get-url origin 2>/dev/null | sed -E 's|.*/([^/]+?)(\.git)?$|projects/\1|'
```

- Example: repo `munin-memory` → namespace `projects/munin-memory`
- If the repo name doesn't map cleanly (fork, monorepo, cross-cutting topic), ask the user. Do not guess.
- If there is no matching Munin namespace at all (new project, methodology debate, topic not yet represented), skip the memory access instructions in the reviewer prompt and note this in the draft.

Pass the inferred namespace as a placeholder substitution into the reviewer prompts in Steps 3 and 6. Do **not** pre-assemble context into a file — let the reviewer self-serve from Munin at critique time, so Round 1 and Round 2 read live state rather than a stale snapshot.

**agy caveat:** on the Flash tier, agy sometimes performs the full CLAUDE.md-style Munin handshake and wanders off-task. Keep its prompt tightly scoped — instruct it to load only the specific calls listed in Step 3 and then critique, nothing else.

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

These sections give both self-review and the reviewer concrete material to attack. A draft without them is not ready for review.

### Step 2: Self-review

Before invoking the reviewer, Claude critiques its own draft using the topic-specific checklist below. Write to `debate/<topic>-claude-self-review.md`.

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

Read the `## Debate Type` field from `debate/<topic>-claude-self-review.md` and include the matching type-specific block(s) below. The type-specific questions are **additive** — always include the universal adversarial framing, then layer on domain-specific attack vectors.

For **mixed-type debates**, include blocks for both primary and secondary types. Primary type block goes first.

The **prompt body** below is backend-independent. Wrap it in the command for the selected `<reviewer>` from the **Reviewer CLI Invocation** section (codex: `script -q /dev/null codex exec --sandbox workspace-write --skip-git-repo-check -m gpt-5.5 ...`; agy: `agy --print --dangerously-skip-permissions ...`).

```
You are acting as a grounded but adversarial reviewer.

Read the file debate/<topic>-claude-draft.md. [Additional context files to read if needed.]

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

OUTPUT: Begin with a brief 'Context loaded' section listing which memory tools you called, the model you are running as, and any notable gaps or conflicts between the draft and the memory state. Then give the full critique in markdown.
[codex only] Write your full critique to debate/<topic>-codex-critique.md.
[agy only] Print your full, complete critique as your final response to stdout — do NOT attempt to write a file.
```

**Output capture by backend:**
- **codex** writes `debate/<topic>-codex-critique.md` directly (workspace-write via `--sandbox workspace-write`). Verify in Step 4.
- **agy** prints the critique to stdout; *Claude* writes it to `debate/<topic>-agy-critique.md` from the captured Bash output. (agy on Flash is unreliable at file-writing — capturing stdout is the default, not a fallback.)

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

Ensure `debate/<topic>-<reviewer>-critique.md` exists and is complete.

- **codex:** read the file Codex wrote. Failure modes: **file missing** (extract critique from the Bash tool output and write it yourself); **brief summary < 500 chars** (Codex wrote a conversational summary, not the full critique — pull the real content from the execution log).
- **agy:** the critique came back on stdout. Write the captured output to `debate/<topic>-agy-critique.md` yourself. Sanity-check it is the actual critique and not an auth-URL dump (stale token — see auth note) or a Munin handshake transcript (Flash wandered — re-run with a tighter prompt).
- **File looks complete:** Proceed to Step 5.

### Step 5: Write Claude's response

Read the critique carefully. Write a response to `debate/<topic>-claude-response-1.md` with:
- **Concessions** — where the critique is valid, concede explicitly
- **Partial concessions** — where partially valid, explain what you accept and what you push back on
- **Defenses** — where you disagree, defend with evidence
- **Revised positions table** — summarize what changed

### Step 6: Invoke the reviewer (Round 2 rebuttal)

Run the same `<reviewer>` again, pointing it to all files so far (draft, critique, response). **Re-read the `## Debate Type` field from the self-review and include the same type-specific prompt block(s) used in Step 3** so the rebuttal maintains the same domain-specific lens. Use the same backend as Round 1 — do not switch models mid-debate (it breaks the comparison and the critique-log `source` continuity).

**Re-load project context from Munin.** Include the same `LOAD PROJECT CONTEXT FROM MUNIN FIRST` paragraph from Step 3 (with the same inferred `<namespace>`). Round 2 may happen minutes or hours after Round 1 — memory state may have moved. Instruct the reviewer to note if synthesis, status, or decisions have changed since Round 1 and let that shape the rebuttal. If no Munin namespace applies, omit the paragraph as in Step 3.

Ask the reviewer to:
- Acknowledge which concessions are genuine and adequate
- Identify where defenses are valid vs where they dodge the point
- Flag any new issues that emerged, including domain-specific risks from the Step 3 type block
- Flag any drift between Round 1 and Round 2 memory state (new decisions, status updates)
- Give a final verdict on the single most important next step

Output capture is the same as Step 3: **codex** writes `debate/<topic>-codex-rebuttal-1.md`; **agy** prints to stdout and Claude writes `debate/<topic>-agy-rebuttal-1.md`.

### Step 7: Additional rounds (if needed)

**Most debates end after 2 rounds.** Only continue if Round 2 surfaced genuinely new issues that weren't addressed. Add rounds as:
- `debate/<topic>-claude-response-N.md`
- `debate/<topic>-<reviewer>-rebuttal-N.md`

Stop when: (a) both sides are repeating themselves, (b) remaining disagreements are preference not substance, or (c) the cost of another round exceeds the value of resolving the remaining issues.

### Step 8: Structured critique log

Create `debate/<topic>-critique-log.json` with every critique point from all rounds:

```json
[
  {
    "id": "<topic>-C01",
    "source": "<reviewer>-round-1",
    "text": "Brief description of the critique point",
    "classification": "valid | partially_valid | invalid",
    "impact": "changed | partially_changed | acknowledged | deferred | rejected",
    "severity": "critical | major | minor",
    "caught_by_self_review": true | false
  }
]
```

The `source` field encodes the reviewer backend and round, e.g. `codex-round-1`, `agy-round-2`. Keep it consistent so the periodic-synthesis pass can compare catch rates and severity distributions **across models** (does codex or agy surface more `critical` points? more false positives?). This is the only telemetry change versus the single-backend skill — the schema is otherwise unchanged, so historical `codex-round-N` logs remain valid and comparable.

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
- **Reviewer critique/rebuttal files that quote memory-tool output** — both codex and agy load project state from Munin, so critiques may quote `clients/<name>/*`, `people/<name>/*`, or cross-references that expose private relationships. Scrub namespace paths containing real names, and collapse `clients/<name>/...` → `clients/<client>/...` when in doubt.
- Critique log JSON files (may contain quoted content with paths)
- Snapshots of project files used as debate input

### Step 9: Write the summary

Create `debate/<topic>-summary.md` with:
- Date, participants (note the **reviewer backend and model**, e.g. "Reviewer: codex / gpt-5.5" or "Reviewer: agy / Gemini 3.x Pro"), and round count
- Concessions accepted by both sides
- Defenses accepted by the reviewer
- Unresolved disagreements
- New issues from later rounds
- Final verdict (both sides' positions)
- Action items with owners (if applicable)
- List of all debate files
- If agy ran on the Flash tier, **flag it explicitly** here — the critique should be weighted accordingly.

Append a cost table at the end. The `Model` column records the actual reviewer model so cost and quality can be tracked per backend:

```
## Costs
| Invocation        | Wall-clock time | Model              |
|-------------------|-----------------|--------------------|
| <reviewer> R1     | ~Nm             | gpt-5.5 / Gemini … |
| <reviewer> R2     | ~Nm             | gpt-5.5 / Gemini … |
```

### Step 10: Update debate index

Append a row to `debate/INDEX.md` (create the file if it doesn't exist). The `Reviewer` column lets the periodic-synthesis pass slice catch rate and critique quality by backend:

```markdown
# Debate Index

| Date | Topic | Reviewer | Rounds | Key decision | Critique points | Self-review catch rate |
|------|-------|----------|--------|--------------|----------------|-----------------------|
| YYYY-MM-DD | [topic](topic-summary.md) | codex/agy | N | One-line outcome | X | Y/X (Z%) |
```

If an existing `INDEX.md` predates the `Reviewer` column (older debates were codex-only), add the column to the header and backfill prior rows as `codex`.

### Step 11: Verify completeness

Confirm all required files exist before finishing:
- `debate/<topic>-claude-draft.md`
- `debate/<topic>-claude-self-review.md`
- `debate/<topic>-<reviewer>-critique.md`
- `debate/<topic>-claude-response-1.md`
- `debate/<topic>-<reviewer>-rebuttal-1.md`
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
- **agy-specific:** keep the prompt tightly scoped and directive (Flash tends to narrate or wander); state "do exactly this and nothing else" framing, and require the full critique in the final stdout response since Claude captures it from there

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
