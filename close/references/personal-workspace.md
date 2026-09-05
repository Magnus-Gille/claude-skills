## Personal-Workspace Checks (optional)

**Only run these when working in a personal notes/working directory that has its own conventions for capture, tasks, and learnings. Skip entirely for normal source repos.**

**Insights cadence:**
```bash
stat -f "%Sm" ~/.claude/usage-data/report.html 2>/dev/null
```
- If the report doesn't exist or is older than 30 days, suggest running `/insights` followed by `/apply-insights`.
- If recent, skip silently.

**Capture & tasks:**
```bash
ls capture/ 2>/dev/null
```
- Any unprocessed capture items? → Run `/capture` or note for next session
- Any new tasks from this session? → Add to Munin via `memory_write("tasks", "<category>", ...)`. Tasks live in Munin `tasks/` namespace (commitments, projects, admin, events) — NOT in local TASKS.md files.
- Session learnings worth capturing? → Add to `learning/`

