---
name: check-tasks
description: Check status of Hugin tasks — running, pending, completed, failed, or timed out. Use when the user asks about task status, what's running on the Pi, or wants a task update.
---

# /check-tasks - Check Hugin Task Status

Check status of tasks dispatched to Hugin on the Pi.

## Usage

- `/check-tasks` - Show all active (pending/running) tasks, plus recent completed/failed
- `/check-tasks <task-id>` - Check a specific task by ID or partial match
- `/check-tasks all` - Show all tasks including old completed ones

## Instructions

### Step 1: Query Munin for Tasks

Run these queries in parallel:

**Active tasks:**
```
memory_query(query: "task", tags: ["running"], namespace: "tasks/", entry_type: "state", limit: 10)
memory_query(query: "task", tags: ["pending"], namespace: "tasks/", entry_type: "state", limit: 10)
```

**Recent completed/failed:**
```
memory_query(query: "task", tags: ["completed"], namespace: "tasks/", entry_type: "state", limit: 5)
memory_query(query: "task", tags: ["failed"], namespace: "tasks/", entry_type: "state", limit: 5)
```

If the user asked about a specific task, use `memory_read("tasks/<task-id>", "result")` instead.

### Step 2: Read Results for Active/Recent Tasks

For each task found, read its result key to get exit code, duration, and output:
```
memory_read("tasks/<namespace>", "result")
```

### Step 3: Present a Summary

Format as a compact status table:

```
| Task | Status | Duration | Summary |
|------|--------|----------|---------|
| 20260316-070033-heimdall-operator-intent | completed | 15m | Overall status, collector health, saturation metrics |
| 20260316-070100-heimdall-quality-signals | failed (timeout) | 2h | Exit 143 — code committed but post-commit phase timed out |
| 20260316-145200-hugin-task-logging | running | 3m | ... |
```

**Status indicators:**
- **pending** — queued, waiting for Hugin to pick up
- **running** — currently executing
- **completed** — finished successfully (exit 0)
- **failed** — exited non-zero. Check exit code: 143 = SIGTERM (timeout), other = crash
- **failed (timeout)** — use this label when exit code is 143 and duration matches the timeout

**For failed/timed-out tasks:**
- Note if the task committed code despite failing (check output for commit hashes)
- If a log file is referenced (`~/.hugin/logs/<id>.log`), mention it
- Suggest resubmission if the failure was a timeout on post-commit steps

**For running tasks:**
- Show elapsed time so far
- If elapsed > timeout, warn that it will be killed soon

### Step 4: Optional — Check Log Files

If the user asks for details on a failed/timed-out task, or says "what happened?", SSH to the Pi to read the log:

```bash
ssh huginmunin "tail -100 ~/.hugin/logs/<task-id>.log"
```

Only do this if asked — don't proactively dump logs.

## Key Rules

1. **Keep it concise** — the table format is the default. Only expand on tasks the user asks about.
2. **Identify timeouts** — exit code 143 + duration matching timeout = timeout, not a crash.
3. **Check for partial success** — timed-out tasks may have committed code. Always note this.
4. **Suggest next steps** — for failed tasks, suggest resubmission or manual intervention as appropriate.
