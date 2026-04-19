# /close - Session Closing Checklist

Run before ending a session to ensure everything is properly wrapped up.

## Usage

- `/close` - Run full closing checklist
- `/close quick` - Abbreviated check (git snapshot + local state file update)

## Checklist

When `/close` is invoked, work through each section:

### 0. Model Check

If the current model is Opus, stop and ask the user to run `/model sonnet`, then wait for them to confirm the switch before proceeding. The remainder of this skill (git, Munin writes, docs) runs fine on Sonnet, and memory-heavy workloads shouldn't burn Opus quota.

### 1. Git Snapshot

**Behavior depends on the repo type:**

#### mgc repo (`/Users/magnus/mimir/`)
Automatic snapshot — no ceremony, no staging review, no conventional messages:
```bash
git add -A
git commit -m "snapshot $(date +%Y-%m-%d)"
```
- No author verification needed (already set)
- No security check needed (no remote, no push, .gitignore handles secrets)
- No push (no remote)
- If nothing changed, move on silently
- Multiple snapshots per day get the same date — that's fine

#### All other repos
- If uncommitted changes exist → **run the `/commit` workflow** (author verify, security check, conventional message). Do not duplicate commit logic here.
- After committing, **push automatically** (`git push`). If no upstream is set, use `git push -u origin <branch>`.
- If feature branches exist, ask user: merge now or leave for later?
- If clean, move on.

### 2. Documentation Review

Check if session work requires documentation updates:
- [ ] CLAUDE.md - folder structure, workflows, MCP integrations, skills
- [ ] Skill SKILL.md files - if skill behavior changed
- [ ] README files - in relevant folders

**Questions to consider:**
- Did we add new folders? → Update CLAUDE.md folder structure
- Did we add/modify skills? → Update CLAUDE.md skills section
- Did we change workflows? → Update relevant docs

### 3. Unsaved Plans & Artifacts

Before reviewing skill improvements, check whether any significant work product from the session exists only in conversation context and hasn't been persisted to a file:

- **Implementation plans** produced by the `/plan` skill or a `Plan` agent — save to a `plan.md` or `*-plan.md` file in an appropriate location (e.g., `debate/`, `docs/`, repo root).
- **Research summaries** that aren't already written to `~/mimir/`.
- **Decision write-ups** that aren't in Munin or a committed file.
- **Debate documents** (if the `debate-codex` skill ran) — verify `debate/*-summary.md` and `debate/*-plan.md` were written; the raw files are gitignored but summaries and plans should persist.

If anything is only in the conversation, write it to a file now. Ask the user where to save if the right location is unclear.

### 4. Skill Improvements

Review session for potential skill enhancements:
- Did we repeat a pattern that could be automated?
- Did a skill's instructions prove incomplete or unclear?
- Did we discover better approaches mid-session?

**If improvements identified:**
- Note them for the user
- Offer to update the skill now

### 4. MGC-Specific Checks

**Only run these when working in `/Users/magnus/mimir/`. Skip entirely for other repos.**

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

### 5. Cleanup

Check for:
- [ ] Temporary files to delete
- [ ] Test files that shouldn't be committed
- [ ] Stale branches that can be deleted

### 6. Session Handoff (Local State File)

Update the project's local state file with resumption context. This is the primary handoff mechanism — the next session reads this file first.

**Detect the project's convention:**
- If `docs/PROGRESS.md` exists → update that (e.g., focusapp)
- If `TODO.md` exists and is used for status tracking → update that (e.g., tieto-competition)
- If `docs/PLAN.md` or `docs/ROADMAP.md` exists → update those (e.g., johans_app)
- Otherwise → update or create `STATUS.md` in the project root

**Required content** (adapt format to match the project's existing convention):
```markdown
# Project Status

**Last session:** YYYY-MM-DD
**Branch:** current branch name

## Completed This Session
- [List of completed work with commit hashes]

## In Progress
- [Work started but not finished, with context to resume]

## Blockers
- [Anything that prevented completion]

## Next Steps
- [Prioritized list of what to do next]
```

### 7. Munin Memory Update

Claude Code is the bridge between local files and Munin. Desktop, Web, and Mobile sessions can only see Munin, so Code sessions must keep it current.

**Update when:** Code was committed or a decision was made this session.
**Skip when:** Pure Q&A, exploration, read-only sessions, or memory already updated during session.

**Write protocol:**
1. **Log decisions** — `memory_log` any decisions made this session with rationale. Append-only logs survive overwrites.
2. **Write status with CAS** — Update `projects/<name>/status` with a lifecycle tag. Pass `expected_updated_at` from your earlier read to prevent blind overwrites. If the server returns a conflict, warn the user.
   - **Phase:** Current project phase or milestone
   - **Current work:** What's actively being worked on (1-2 sentences)
   - **Blockers:** Anything preventing progress (or "None")

### 8. Skills Repo Sync

If skills were created or modified this session, commit and push automatically:
```bash
cd ~/.claude/skills && git add -A && git commit -m "update <skill-name>" && git push
```
Repo: https://github.com/Magnus-Gille/claude-skills (private)

### 9. Session Summary

Provide brief summary to the user:
```
## Session Summary

### Completed
- [List of completed work]

### Commits
- abc1234 Commit message 1
- def5678 Commit message 2

### Pending/Notes for Next Session
- [Any incomplete work or follow-ups]

### Documentation Updated
- [List of docs updated, or "None needed"]
```

## Output Format

```
## Pre-Close Checklist

### Git
✓ Snapshot taken (or: committed via /commit workflow)

### Documentation
✓ CLAUDE.md up to date
✓ Skills documented

### Local State File
✓ STATUS.md updated with resumption context

### Munin Memory
✓ Project status updated (phase change)
✓ Workbench updated (project completed)
- or: ✓ No updates needed (incremental session)

### Potential Skill Improvements
- /inbox skill could auto-detect customer names from content

### Ready to Close
All checks passed. Session can be closed.
```

## Quick Mode

`/close quick` only checks:
1. Git snapshot (mgc) or `/commit` workflow (other repos)
2. Local state file update (always — this is the minimum for session continuity)
3. Brief summary of session commits

Skip documentation review, skill improvements, Munin updates, and detailed cleanup.
