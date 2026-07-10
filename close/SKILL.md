---
name: close
description: Session closing checklist for Git state, documentation, handoff files, and Munin memory. Use when the user invokes /close or asks to wrap up a session, including work that touched multiple repositories.
---

# /close - Session Closing Checklist

Run before ending a session to ensure everything is properly wrapped up.

## Usage

- `/close` - Run full closing checklist
- `/close quick` - Abbreviated check (git snapshot + local state file update)

## Checklist

When `/close` is invoked, work through each section:

### 1. Git Snapshot

**Behavior depends on the repo type:**

#### Snapshot-mode repos (e.g. a personal notes/working directory with no remote)
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
Determine the audit scope before deciding what to commit or clean up:

- Always include the current repository.
- If the session touched other repositories (edits, commits, PRs, deploy sources, local state files,
  or production verification), include every affected Git root. Derive this bounded set from the
  session's workdirs, commands, PRs, and deploy paths; do not sweep every repo under `$HOME`.
- Resolve each candidate with `git -C <path> rev-parse --show-toplevel` and deduplicate roots.
- Audit each affected repo and all of its worktrees. A clean current repo does not prove the
  multi-repo session is clean.

Before classifying ahead/behind state, `[gone]` upstreams, or stale PR branches, refresh the relevant
remote in each affected repo:

```bash
git remote
git fetch --prune <tracking-remote>  # usually origin
```

Treat fetch as non-destructive to the remote and working tree, but remember that it updates local
remote-tracking refs and `FETCH_HEAD`. If the repo has no remote, network/auth is unavailable, or the
session is restricted to strictly read-only local operations, continue the local audit and state that
remote/PR disposition could not be freshly verified; prefer forge PR metadata or `git ls-remote` for
fresh non-local verification, and do not guess from stale remote-tracking refs.

Then run the full audit in each affected repo:
```bash
git status
git branch
git log --oneline -5
git worktree list
git branch --verbose --no-abbrev
git branch --format='%(refname:short) %(upstream:track) %(objectname:short) %(subject)'
git status --ignored --short STATUS.md PROGRESS.md TODO.md docs/PROGRESS.md docs/PLAN.md docs/ROADMAP.md 2>/dev/null
# For each non-primary worktree from `git worktree list`:
git -C <worktree-path> status --short --branch
```
- If uncommitted tracked changes exist → **run the `/commit` workflow** (author verify, security check, conventional message). Do not duplicate commit logic here.
- If only expected local-only/untracked files exist, document them as intentionally left; do not run `/commit` just to commit scratch/config.
- After committing, **push automatically** (`git push`). If no upstream is set, use `git push -u origin <branch>`.
- If feature branches exist, ask user: merge now or leave for later?
- If stale branches/worktrees exist, document them. Delete only clean worktrees/branches and only when cleanup was explicitly requested.
- Group the final Git findings by repository, including clean repos, so cross-repo deployment and
  handoff state is explicit.
- If clean, move on.

### 2. Documentation Review

Check if session work requires documentation updates:
- [ ] CLAUDE.md - folder structure, workflows, MCP integrations, skills
- [ ] Skill SKILL.md files - if skill behavior changed
- [ ] README files - in relevant folders
- [ ] **Living / generated artifacts** - if the project's CLAUDE.md defines maintained artifacts (e.g. a generated `site/` of HTML status pages, dashboards), follow its documented update contract and refresh them to reflect this session's work. Skip if this session changed no project state.

**Questions to consider:**
- Did we add new folders? → Update CLAUDE.md folder structure
- Did we add/modify skills? → Update CLAUDE.md skills section
- Did we change workflows? → Update relevant docs
- Did deployment copy local-only files, require manual cleanup, or change rsync/exclude behavior? → Document the operational fix or verified cleanup location.
- Does CLAUDE.md define living artifacts (e.g. `site/`)? → Apply their documented update contract

### 3. Unsaved Plans & Artifacts

Before reviewing skill improvements, check whether any significant work product from the session exists only in conversation context and hasn't been persisted to a file:

- **Implementation plans** produced by the `/plan` skill or a `Plan` agent — save to a `plan.md` or `*-plan.md` file in an appropriate location (e.g., `debate/`, `docs/`, repo root).
- **Research summaries** that aren't already written to your notes/research directory.
- **Decision write-ups** that aren't in Munin or a committed file.
- **Debate documents** (if the `debate` skill ran) — verify `debate/*-summary.md` and `debate/*-plan.md` were written; the raw files are gitignored but summaries and plans should persist.

If anything is only in the conversation, write it to a file now. Ask the user where to save if the right location is unclear.

### 4. Skill Improvements

Review session for potential skill enhancements:
- Did we repeat a pattern that could be automated?
- Did a skill's instructions prove incomplete or unclear?
- Did we discover better approaches mid-session?

**If improvements identified:**
- Note them for the user
- Offer to update the skill now

### 5. Personal-Workspace Checks (optional)

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

### 6. Cleanup

Check for:
- [ ] Temporary files to delete
- [ ] Test files that shouldn't be committed
- [ ] Stale branches that can be deleted or documented
- [ ] Stale PR worktrees that can be removed or documented
- [ ] Dirty secondary worktrees that must be left untouched and called out

Stale PR cleanup guidance:
- For squash-merged PRs, use GitHub PR state as the source of truth; the local branch may not be merged by Git ancestry.
- Before deleting any worktree, run `git -C <worktree-path> status --short --branch`.
- Do not delete dirty worktrees. Document exact path and changed files under pending notes.
- If GitHub API/network is unavailable, document that PR-state verification was skipped rather than guessing.

### 7. Session Handoff (Local State File)

Update the project's local state file with resumption context. This is the primary handoff mechanism — the next session reads this file first.

Apply this per affected repository whose execution state changed substantively. Do not create or
rewrite a handoff merely because a repo was inspected read-only. A coordinating/system repo may carry
the consolidated cross-repo summary, but it does not replace a changed owning repo's local handoff.

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

Also include when relevant:
- Deployment status (for example: deployed to Pi/prod, not yet committed)
- Deploy verification (health check, deployed commit, and local-only artifact cleanup if relevant)
- Ignored/local-only handoff files (for example `STATUS.md`) using `git status --ignored` when normal `git status` hides them
- Pending stale branches/worktrees that were intentionally left alone
- Where any presentation, incident, or postmortem notes were stored

### 8. Munin Memory Update

Claude Code is the bridge between local files and Munin. Desktop, Web, and Mobile sessions can only see Munin, so Code sessions must keep it current.

**Update when:** Code was committed or a decision was made this session.
**Skip when:** Pure Q&A, exploration, read-only sessions, or memory already updated during session.

For a multi-repo session, update each affected tracked project whose current state changed; do not
rewrite unrelated project statuses merely because they were included in the Git audit.

**Write protocol:**
1. **Log decisions** — `memory_log` any decisions made this session with rationale. Append-only logs survive overwrites.
2. **Write status with CAS** — Update `projects/<name>/status` with a lifecycle tag. Pass `expected_updated_at` from your earlier read to prevent blind overwrites. If the server returns a conflict, warn the user.
   - **Phase:** Current project phase or milestone
   - **Current work:** What's actively being worked on (1-2 sentences)
   - **Blockers:** Anything preventing progress (or "None")

### 9. Skills Repo Sync

If skills were created or modified this session and `~/.claude/skills` is a git checkout with a remote, commit and push automatically:
```bash
cd ~/.claude/skills && git add -A && git commit -m "update <skill-name>" && git push
```
Skip silently if `~/.claude/skills` has no remote configured.

### 10. Session Summary

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
✓ Affected repositories audited: <repo list>
✓ Remote refs refreshed (or freshness limitation documented) per affected repo
✓ Snapshot taken (or: committed via /commit workflow)
✓ Expected branches and remote status checked per repo
!! Local-only untracked files documented
!! Dirty secondary worktree '<path>' left untouched - changed files listed

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

Use the same bounded affected-repository set and refresh each tracking remote before classifying status.

1. Git snapshot (snapshot-mode repos) or `/commit` workflow (normal repos)
2. Dirty secondary worktree warning (`git worktree list` plus `git -C <path> status --short --branch`)
3. Local state file update (always — this is the minimum for session continuity)
4. Brief summary of session commits

Skip documentation review, skill improvements, Munin updates, and detailed cleanup.
