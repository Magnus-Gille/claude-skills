---
name: submit-task
description: Submit a task to Hugin (the Pi task dispatcher) by writing a properly formatted entry to Munin. Use when the user wants to dispatch work to the Pi — code implementation, Codex reviews, research, email drafting, maintenance scripts, or any autonomous task.
---

# /submit-task - Submit a Task to Hugin

Submit a task to the Hugin dispatcher running on the Pi (huginmunin). Hugin polls Munin every 30 seconds for pending tasks and spawns an AI runtime to execute them.

## Usage

- `/submit-task` - Interactive: ask what the task should do, then build the prompt together
- `/submit-task <description>` - Build a task from the description, confirm before submitting
- `/submit-task codex <description>` - Use Codex runtime instead of Claude
- `/submit-task ollama <description>` - Use local ollama model on Pi (or laptop if available)

## How It Works

### Step 1: Gather Requirements

If no description provided, ask the user:
- What should the task do?
- Which context? (repo name, scratch, files, or custom path)
- How long might it take? (for timeout)
- Any specific constraints?

If a description was provided, infer these from context. Check Munin (`projects/*/status`) for relevant project state if needed.

### Step 2: Infer Context

Determine the execution context from the task description:

| Signal in description | Context | Resolved path on Pi |
|----------------------|---------|-------------------|
| Mentions a specific repo name | `repo:<name>` | `/home/magnus/repos/<name>` |
| Research, analysis, investigation | `scratch` | `/home/magnus/scratch` |
| Email drafting, admin tasks | `scratch` | `/home/magnus/scratch` |
| File organization, document work | `files` | `/home/magnus/mimir` |
| Explicit path given | Raw path | Used as-is |
| Ambiguous | Ask the user | — |

Default: `scratch` for non-code tasks, `repo:<name>` for code tasks.

### Step 3: Detect Multi-Task Decomposition

If the task involves **multiple repos** or **clearly sequential phases with different scopes**, decompose into a task group:

1. Generate a group ID: `YYYYMMDD-HHMMSS-<slug>` (same timestamp for all sub-tasks)
2. Each sub-task gets its own task ID, `**Group:**` field, and `**Sequence:**` number
3. Each sub-task prompt (except the first) includes at the top:
   ```
   **PREREQUISITE CHECK:** Before starting, read `tasks/<prev-task-id>/result`.
   If it does not contain "DONE", write to your own result:
   "SKIPPED — prerequisite <prev-task-id> did not complete successfully" and exit.
   ```
4. Show the full decomposition to the user before submitting
5. Submit all sub-tasks at once (they queue in FIFO order)

**When NOT to decompose:** If the task can be done in a single repo or a single session even if it has multiple phases, keep it as one task. Decomposition is for cross-repo or truly independent work items.

### Step 4: Choose Runtime and Timeout

| Runtime | When to use | Munin tag |
|---------|-------------|-----------|
| `claude` | Most tasks — implementation, multi-step work, Munin integration | `runtime:claude` |
| `codex` | Pure code review, quick file edits, single-focus tasks | `runtime:codex` |
| `ollama` | Bounded tasks suitable for small models — summarization, triage, log analysis, status review, structured data extraction. No tool use. | `runtime:ollama` |

Default runtime: `claude`

**Ollama-specific fields** (only for `runtime: ollama`):

| Field | Values | Default | Purpose |
|-------|--------|---------|---------|
| `Ollama-host` | `pi`, `laptop`, or URL | auto (prefers pi) | Which ollama instance to target |
| `Fallback` | `claude`, `none` | `none` | Fall back to Claude on **infra failures only** (host unreachable, 5xx). Semantic failure (model responds but poorly) is never retried — that's experiment data. |
| `Model` | e.g. `qwen2.5:3b`, `qwen2.5:7b` | `qwen2.5:3b` | Ollama model name. 3b is default (fits Pi comfortably). 7b is available but causes swap pressure. |
| `Context-refs` | Comma-separated Munin refs | *(none)* | Munin entries to fetch and inject into prompt. Format: `namespace/key`. E.g. `meta/conventions/status, projects/heimdall/status` |
| `Context-budget` | Integer (chars) | `8000` | Max characters for injected context. Truncated from end if exceeded. |

**When to use ollama vs claude:**
- Use `ollama` when the task is bounded, doesn't need tools (file editing, shell, MCP), and the output quality bar is "good enough" not "best possible."
- Use `claude` when the task needs tool use, multi-step reasoning, code changes, or high-quality judgment.
- Set `Fallback: claude` on important ollama tasks where failure is costly.
- Ollama models have NO tool access — everything the model needs must be in the prompt (via Context-refs or inline data).

Timeout guidelines:
| Task type | Timeout |
|-----------|---------|
| Quick script/edit | 300000 (5 min) |
| Code review | 600000 (10 min) |
| Research / email draft | 1200000 (20 min) |
| Small implementation | 1800000 (30 min) |
| Full feature implementation | 3600000 (1 hour) |
| Large multi-phase task | 7200000 (2 hours) |
| Ollama task (3b, short) | 120000 (2 min) |
| Ollama task (7b or longer input) | 300000 (5 min) |

Default: 1800000 (30 min) for claude/codex, 120000 (2 min) for ollama. Ask the user if unsure.
Note: Ollama cold-starts (model not in memory) add ~5-60s depending on model size. The 5 min idle auto-unload means most scheduled tasks will hit a cold start.

### Step 4b: Choose Model (optional)

Hugin supports model selection via the `**Model:**` field. If omitted, uses the Pi's default model.

| Model | Runtime | When to use |
|-------|---------|-------------|
| `claude-sonnet-4-6` | claude | Implementation tasks with clear specs, routine code changes |
| `claude-opus-4-6` | claude | Complex architecture, ambiguous requirements, tasks that failed on Sonnet |
| `opusplan` | claude | Plans with Opus, implements with Sonnet (good for complex but decomposable tasks) |
| `qwen2.5:3b` | ollama | Default for Pi. Fits comfortably (1.9 GB). Good for bounded structured tasks. |
| `qwen2.5:7b` | ollama | Higher quality but causes swap on Pi (~4.7 GB). Use for tasks needing better reasoning. |
| *(omit)* | any | Uses runtime default (Claude: Opus, Ollama: qwen2.5:3b) |

Default: `claude-sonnet-4-6` for well-scoped code tasks. Use `claude-opus-4-6` or `opusplan` for complex/ambiguous tasks. For ollama, default to `qwen2.5:3b` unless the task needs better quality.

### Step 5: Determine Task Type Tag

Add a `type:` tag based on the task nature:

| Type tag | When to use |
|----------|-------------|
| `type:code` | Implementation, bug fixes, refactoring |
| `type:review` | Code review, audit |
| `type:research` | Investigation, analysis, feasibility |
| `type:email` | Email drafting |
| `type:admin` | Maintenance, cleanup, config changes |

### Step 6: Generate Task ID

Format: `YYYYMMDD-HHMMSS-<slug>` — **all three parts are required**.

Generate the date-time prefix from the current UTC time:
```js
const d = new Date();
const pad = (n) => String(n).padStart(2, '0');
const prefix = `${d.getUTCFullYear()}${pad(d.getUTCMonth()+1)}${pad(d.getUTCDate())}-${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}`;
// e.g. "20260315-170000"
```

- The `HHMMSS` portion is **mandatory** — omitting it breaks Heimdall's task display
- Slug: 2-4 word kebab-case summary (e.g. `heimdall-code`, `fix-backup-detection`, `codex-review`)

Example: `tasks/20260315-170000-heimdall-code`

### Step 7: Write the Prompt

Build a clear, explicit prompt. Include:

1. **Context** — where the agent is, what tools it has access to
2. **Mission** — one sentence, bold, unmistakable
3. **Phases** — numbered steps with clear deliverables
4. **Constraints** — what NOT to do, privacy rules, tool paths
5. **Completion signal** — always end with writing result to task namespace

#### Template for code tasks (Context: repo:*)

```markdown
## Task: <title>

- **Runtime:** claude | codex
- **Context:** repo:<name>
- **Model:** <optional: claude-sonnet-4-6 | claude-opus-4-6 | opusplan>
- **Timeout:** <ms>
- **Submitted by:** claude-code
- **Submitted at:** <UTC ISO 8601>
- **Reply-to:** none
- **Group:** <group-id if part of a group>
- **Sequence:** <number if part of a group>

### Prompt

You are working on <project> at `/home/magnus/repos/<name>` on the Hugin-Munin Raspberry Pi (huginmunin).
You have MCP access to Munin (`munin-memory` MCP server).

**YOUR MISSION: <one clear sentence>.**

---

## Phase 1: <name>
<steps>

## Phase 2: <name>
<steps>

...

## Final Phase: Commit, Push & Report

1. Commit changes with a conventional commit message.

2. **Push to origin — REQUIRED:** `git push origin <branch>` — commits that are not pushed are invisible to other environments and will be flagged as drift in Heimdall. Hugin will attempt a fallback push, but you must push explicitly.

3. Update Munin project status:
   memory_write("projects/<name>", "status", <summary>, tags: ["active"])

4. Log the milestone:
   memory_log("projects/<name>", "<summary>", tags: ["milestone"])

5. **Follow-up actions:** If anything could not be completed (e.g., sandbox blocked sudo, wrong auth, missing resource), append to the shared action list:
   memory_read("actions", "pending") — read current list first
   memory_write("actions", "pending", <updated list with new items>, tags: ["active", "action-items"])
   Format new items as: `## From tasks/<task-id>\n- [ ] <description of what needs to be done and why>`

6. Signal task completion:
   memory_write("tasks/<task-id>", "result", "DONE — <summary>")

---

## Constraints

- <list constraints>
- **Signal completion:** Write "DONE" to `tasks/<task-id>/result` when finished.
- **Follow-up actions:** If anything remains unresolved, append to `actions/pending` in Munin. Do NOT silently swallow blockers.
```

#### Template for non-code tasks (Context: scratch)

```markdown
## Task: <title>

- **Runtime:** claude
- **Context:** scratch
- **Timeout:** <ms>
- **Submitted by:** claude-code
- **Submitted at:** <UTC ISO 8601>
- **Reply-to:** none

### Prompt

You are a general-purpose agent on the Hugin-Munin Raspberry Pi (huginmunin).
You have MCP access to Munin (`munin-memory` MCP server).
Your working directory is `/home/magnus/scratch` — a general-purpose workspace for non-code tasks.

**YOUR MISSION: <one clear sentence>.**

---

<task-specific instructions>

---

## Completion

1. Write findings/output to Munin:
   memory_write("<appropriate-namespace>", "<key>", <content>, tags: [<relevant tags>])

2. If file artifacts were produced, push to NAS inbox:
   `rsync <file> magnus@100.99.119.52:/home/magnus/mimir-inbox/<path>`

3. **Follow-up actions:** If anything could not be completed, append to the shared action list:
   memory_read("actions", "pending") — read current list first
   memory_write("actions", "pending", <updated list with new items>, tags: ["active", "action-items"])
   Format new items as: `## From tasks/<task-id>\n- [ ] <description of what needs to be done and why>`

4. Signal task completion:
   memory_write("tasks/<task-id>", "result", "DONE — <summary>")

---

## Constraints

- <list constraints>
- **Signal completion:** Write "DONE" to `tasks/<task-id>/result` when finished.
- **Follow-up actions:** If anything remains unresolved, append to `actions/pending` in Munin. Do NOT silently swallow blockers.
```

#### Template for ollama tasks (Runtime: ollama)

```markdown
## Task: <title>

- **Runtime:** ollama
- **Context:** scratch
- **Model:** qwen2.5:3b
- **Ollama-host:** pi
- **Fallback:** none
- **Context-refs:** <comma-separated Munin refs, if needed>
- **Context-budget:** 8000
- **Timeout:** <ms>
- **Submitted by:** claude-code
- **Submitted at:** <UTC ISO 8601>
- **Reply-to:** none

### Prompt

<task instructions — must be fully self-contained>
<include all data inline if not using Context-refs>
```

**Ollama prompt guidelines:**
- **No tool-use instructions** — the model has no tools. Everything it needs must be in the prompt.
- **No MCP references** — the model cannot call Munin, write results, or interact with services.
- **No completion signal** — Hugin captures the model output directly. No `memory_write` to result key needed (Hugin does this automatically).
- **Be specific about output format** — small models follow explicit format instructions better than vague ones.
- **Keep prompts focused** — one clear task, not multi-phase workflows.
- **Use Context-refs** for Munin state the model needs to read — Hugin fetches and injects it before calling the model.
- **Inline data directly** for non-Munin content (journal entries, file contents, etc.)

#### Codex-specific notes

If runtime is `codex`, the prompt goes directly to `codex exec`. Keep it focused — Codex works best with single-purpose tasks. No MCP access, no multi-phase workflows.

If the Claude task needs to invoke Codex internally (e.g., for adversarial review), include:
```
**Codex path:** `~/.npm-global/bin/codex`
**Sandbox note:** Use `--dangerously-bypass-approvals-and-sandbox` (Landlock broken on ARM64 Pi)
```

### Step 8: Confirm with User

Show the user:
- Task ID (and group info if multi-task)
- Context (resolved)
- Runtime
- Timeout (human-readable)
- Task type tag
- First line of the mission
- Full prompt (collapsed or summarized if long)

Ask: "Submit this task? Hugin will pick it up within 30 seconds."

### Step 9: Submit

Write to Munin:
```
memory_write(
  namespace: "tasks/<task-id>",
  key: "status",
  content: <the full task content>,
  tags: ["pending", "runtime:<runtime>", "type:<type>"]
)
```

Confirm submission with the returned entry ID.

### Step 10: Monitoring Tips

Tell the user how to check on it:
```
Check status:  memory_read("tasks/<task-id>", "status")  — tags flip: pending → running → completed
Check result:  memory_read("tasks/<task-id>", "result")   — written when done
Check process: ssh huginmunin "ps aux | grep claude"      — is it still running?
```

## Key Rules

1. **One task at a time** — Hugin has no parallelism. If a task is already running, warn the user it will queue.
2. **Be explicit** — The Pi agent has no conversation context. The prompt must be fully self-contained.
3. **Always include completion signal** — Without `memory_write` to the result key, you can't tell if it finished or crashed.
4. **UTC timestamps** — All dates in the task must be UTC ISO 8601.
5. **No secrets in prompts** — API keys, tokens, passwords must come from env vars on the Pi, not the prompt.
6. **Privacy in committed code** — Remind the task to use placeholders for IPs, emails, domains in any files it commits.
7. **Codex sandbox** — Always use `--dangerously-bypass-approvals-and-sandbox` on the Pi (Landlock broken on ARM64).
8. **Context must resolve** — For `repo:<name>`, the repo must exist on the Pi. For `scratch`, the directory `/home/magnus/scratch` must exist (created by the Hugin enhancements task).
9. **Timeout is a hard kill** — Hugin kills the process when time's up. Err on the generous side.
10. **Always git push** — Code tasks must push after committing. Unpushed commits are invisible to the laptop and Heimdall deploy drift tracking.
11. **Never stop what you can't restart** — Task prompts must include explicit restart commands (e.g., `sudo systemctl restart <service>`) when the task modifies a running service. Agents must NEVER stop a service without restarting it — a stopped service is worse than a buggy one.
12. **Codex adversarial review** — For non-trivial implementation tasks, include a phase where the agent runs Codex to review the changes before committing. This catches bugs before they land. See `~/.npm-global/bin/codex` with `--dangerously-bypass-approvals-and-sandbox`.
13. **File outputs go to NAS inbox** — Hugin runs on huginmunin, but the laptop syncs with the NAS Pi (100.99.119.52). If a task produces file outputs (reports, artifacts), it must push them to the NAS inbox: `rsync <file> magnus@100.99.119.52:/home/magnus/mimir-inbox/<path>`. The inbox is auto-imported to the laptop on next sync. Files left on huginmunin or written directly to NAS `~/mimir/` will be lost.
14. **Non-code tasks use scratch** — Research, email drafts, admin tasks go to `Context: scratch`. The scratch workspace has its own CLAUDE.md with tool orientation.
15. **Follow-up actions go to `actions/pending`** — If a task can't complete something (sandbox blocked sudo, wrong auth, missing resource), it must append the unresolved item to `actions/pending` in Munin. Read the current list first, then write back with the new item appended. This ensures nothing gets silently lost. Format: `## From tasks/<task-id>\n- [ ] <what needs doing and why>`.
16. **Never use deploy targets as working directories** — Some projects have separate deploy paths (e.g., mimir deploys to `~/mimir-server/` on the NAS Pi via rsync). Changes made there get overwritten on the next deploy. Always use `repo:<name>` (resolves to `~/repos/<name>` on huginmunin) so changes are committed and pushed to GitHub, surviving future deploys.
