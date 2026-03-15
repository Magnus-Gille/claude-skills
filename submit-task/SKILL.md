---
name: submit-task
description: Submit a task to Hugin (the Pi task dispatcher) by writing a properly formatted entry to Munin. Use when the user wants to dispatch work to the Pi — code implementation, Codex reviews, maintenance scripts, or any autonomous task.
---

# /submit-task - Submit a Task to Hugin

Submit a task to the Hugin dispatcher running on the Pi (huginmunin). Hugin polls Munin every 30 seconds for pending tasks and spawns an AI runtime to execute them.

## Usage

- `/submit-task` - Interactive: ask what the task should do, then build the prompt together
- `/submit-task <description>` - Build a task from the description, confirm before submitting
- `/submit-task codex <description>` - Use Codex runtime instead of Claude

## How It Works

### Step 1: Gather Requirements

If no description provided, ask the user:
- What should the task do?
- Which repo/directory on the Pi? (default: `/home/magnus/workspace`)
- How long might it take? (for timeout)
- Any specific constraints?

If a description was provided, infer these from context. Check Munin (`projects/*/status`) for relevant project state if needed.

### Step 2: Choose Runtime and Timeout

| Runtime | When to use | Munin tag |
|---------|-------------|-----------|
| `claude` | Most tasks — implementation, multi-step work, Munin integration | `runtime:claude` |
| `codex` | Pure code review, quick file edits, single-focus tasks | `runtime:codex` |

Default runtime: `claude`

Timeout guidelines:
| Task type | Timeout |
|-----------|---------|
| Quick script/edit | 300000 (5 min) |
| Code review | 600000 (10 min) |
| Small implementation | 1800000 (30 min) |
| Full feature implementation | 3600000 (1 hour) |
| Large multi-phase task | 7200000 (2 hours) |

Default: 1800000 (30 min). Ask the user if unsure.

### Step 3: Generate Task ID

Format: `YYYYMMDD-HHMMSS-<slug>`

- Date/time in **UTC** (use `new Date().toISOString()`)
- Slug: 2-4 word kebab-case summary (e.g. `heimdall-code`, `fix-backup-detection`, `codex-review`)

Example: `tasks/20260315-170000-heimdall-code`

### Step 4: Write the Prompt

Build a clear, explicit prompt. Include:

1. **Context** — where the agent is, what tools it has access to
2. **Mission** — one sentence, bold, unmistakable
3. **Phases** — numbered steps with clear deliverables
4. **Constraints** — what NOT to do, privacy rules, tool paths
5. **Completion signal** — always end with writing result to task namespace

Template:
```markdown
## Task: <title>

- **Runtime:** claude | codex
- **Working dir:** /home/magnus/repos/<project>
- **Timeout:** <ms>
- **Submitted by:** claude-code-laptop
- **Submitted at:** <UTC ISO 8601>

### Prompt

You are working on <project> at `<path>` on the Hugin-Munin Raspberry Pi (huginmunin).
You have MCP access to Munin (`munin-memory` MCP server).

**YOUR MISSION: <one clear sentence>.**

---

## Phase 1: <name>
<steps>

## Phase 2: <name>
<steps>

...

## Final Phase: Report Completion

1. Update Munin project status:
   memory_write("projects/<name>", "status", <summary>, tags: ["active"])

2. Log the milestone:
   memory_log("projects/<name>", "<summary>", tags: ["milestone"])

3. Signal task completion:
   memory_write("tasks/<task-id>", "result", "DONE — <summary>")

---

## Constraints

- <list constraints>
- **Signal completion:** Write "DONE" to `tasks/<task-id>/result` when finished.
```

#### Codex-specific notes

If runtime is `codex`, the prompt goes directly to `codex exec`. Keep it focused — Codex works best with single-purpose tasks. No MCP access, no multi-phase workflows.

If the Claude task needs to invoke Codex internally (e.g., for adversarial review), include:
```
**Codex path:** `~/.npm-global/bin/codex`
**Sandbox note:** Use `--dangerously-bypass-approvals-and-sandbox` (Landlock broken on ARM64 Pi)
```

### Step 5: Confirm with User

Show the user:
- Task ID
- Runtime
- Timeout (human-readable)
- Working directory
- First line of the mission
- Full prompt (collapsed or summarized if long)

Ask: "Submit this task? Hugin will pick it up within 30 seconds."

### Step 6: Submit

Write to Munin:
```
memory_write(
  namespace: "tasks/<task-id>",
  key: "status",
  content: <the full task content>,
  tags: ["pending", "runtime:<runtime>"]
)
```

Confirm submission with the returned entry ID.

### Step 7: Monitoring Tips

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
8. **Working dir must exist** — Verify the directory exists on the Pi, or tell the task to create it.
9. **Timeout is a hard kill** — Hugin kills the process when time's up. Err on the generous side.
