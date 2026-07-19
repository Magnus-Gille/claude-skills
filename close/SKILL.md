---
name: close
description: Close a coding-agent session by auditing Git and worktrees, preserving handoff state, updating documentation and Munin when warranted, cleaning bounded temporary artifacts, and returning one canonical end-of-session report. Use when the user invokes /close or $close, asks to close or wrap up a session, or requests an end-of-session handoff across one or more repositories.
---

# close - Session Closing Checklist

Run before ending a session to ensure everything is properly wrapped up.

## Usage

- `/close` or `$close` - Run the full closing checklist
- `/close quick` or `$close quick` - Run the abbreviated checklist

## Canonical report contract

The audit may vary with the session. **The final report must not.** Always render the final response
with `scripts/render-report.py`; never compose or reformat the report manually.

1. Assemble a bounded temporary JSON file with this shape:

```json
{
  "mode": "full",
  "closed_at": "YYYY-MM-DD HH:MM TZ",
  "scope": ["repo-or-workspace"],
  "completed": ["Concrete completed outcome."],
  "repositories": [
    {
      "name": "repo",
      "branch": "main",
      "working_tree": "clean",
      "remote": "origin/main synchronized",
      "disposition": "complete"
    }
  ],
  "verification": ["Tests passed."],
  "persistence": ["STATUS.md updated."],
  "deployment": ["Not changed."],
  "cleanup": ["Removed bounded disposable cache."],
  "blockers": [],
  "warnings": [],
  "pending": []
}
```

2. Use short factual strings. Include one repository row per affected Git root, including clean
   roots. Describe deliberately retained dirty state in `working_tree` and `disposition`; do not
   hide it in prose.
3. Put only conditions that prevent a safe close in `blockers`. Put freshness limits, intentionally
   retained dirty state, open PRs, and other non-blocking caveats in `warnings`. Put concrete
   follow-ups in `pending` in priority order.
4. For quick mode, still populate every field. Use explicit entries such as `Not checked in quick
   mode.` rather than dropping sections.
5. Render and capture stdout:

```bash
python3 <close-skill-dir>/scripts/render-report.py <close-report.json>
```

6. Delete the temporary JSON after rendering. Return the renderer's stdout **verbatim** as the final
   answer. Add no greeting, explanation, alternative summary, follow-up question, or text after it.

The renderer fixes heading order, repository sorting, empty-section placeholders, and status:

- `NOT READY` when `blockers` is non-empty.
- `READY WITH NOTES` when there are no blockers but `warnings` or `pending` is non-empty.
- `READY` only when all three are empty.

Do not override or editorialize the derived status. If the renderer itself is missing or fails, add
that as a blocker, preserve the same section order shown by the script, and do not claim `READY`.

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
# Include ignored local handoff files explicitly:
git status --ignored --short STATUS.md PROGRESS.md TODO.md docs/PROGRESS.md docs/PLAN.md docs/ROADMAP.md 2>/dev/null
# For each non-primary worktree from `git worktree list`, check dirtiness before cleanup:
git -C <worktree-path> status --short --branch
```

Check for:

- Uncommitted tracked changes: commit, stash, or explicitly leave them.
- Expected local-only/untracked files versus files that belong in Git.
- Unmerged feature branches and unpushed commits.
- Deployed-but-uncommitted changes or production receiving local-only files.
- Stale PR branches/worktrees, including squash-merged branches that are not Git ancestors of main.
- Dirty secondary worktrees and branches with gone upstreams.

Actions:

- If tracked changes exist and the user has not already authorized committing them, ask whether to
  commit, stash, or leave. If committing is authorized, run the `/commit` workflow rather than
  duplicating its author, security, message, and push checks here.
- If only expected local-only files exist, document and leave them; do not commit scratch/config by
  default.
- If feature branches exist, ask user: merge now or leave for later?
- Group the final Git findings by repository, including clean repos, so cross-repo deployment and
  handoff state is explicit.
- State deployed-but-uncommitted or deployed-local-only changes explicitly.
- For a squash-merged, rebased, or cherry-picked branch, verify forge state and patch equivalence
  before calling it unmerged. Use `git cherry`, `git range-diff`, or stable patch IDs as appropriate.
- Before deleting a stale worktree or branch, verify its status. Delete only clean items and only
  when cleanup was explicitly requested; otherwise record them as pending cleanup.
- Never delete a dirty worktree. If uncertain, preserve it and report the exact path.

#### Concurrency guard

The close audit can race another agent or terminal session. Detect that explicitly instead of
publishing a stale "clean" summary.

After the initial fetch and worktree audit, capture a baseline for the exact affected repo set:

```bash
close_snapshot="$(mktemp "${TMPDIR:-/tmp}/close-recheck.XXXXXX")"
<close-skill-dir>/scripts/final-recheck.sh capture "$close_snapshot" <repo-path>...
```

Keep a small expected-change ledger in the session context for every mutation made by this close
run: repo/worktree, before and after SHA, changed files, push, and PR state. Before the final summary:

1. Refresh each tracking remote again with `git fetch --prune`.
2. Run `final-recheck.sh compare` with the same snapshot and repo paths. It compares local branches,
   every attached worktree's HEAD/upstream/status fingerprint, and open GitHub PR heads/state when
   `gh` is available.
3. Classify every difference against the expected-change ledger. Never dismiss the complete diff
   merely because this close run made one expected commit.
4. For unexpected changes, treat them as concurrent: rerun status/PR inspection for the affected
   repo, reread changed handoff files, and reconcile the final summary. Do not clean, commit, merge,
   or overwrite newly observed work. If Munin was already updated, log the correction first and use
   a fresh read plus compare-and-swap for any status correction.
5. After reconciliation, capture a new baseline, refresh remotes, and compare once more. If this
   second final check changes again, stop mutating state and report active concurrent work plus the
   exact freshness limitation instead of claiming a stable close.
6. Remove the snapshot only after a stable final check or after documenting the concurrency limit.

Exit code `0` means stable, `3` means state changed, and any other nonzero code means the recheck
could not be completed. A forge-unavailable marker is a freshness limitation, not proof of stable
PR state. A registered worktree whose directory is already missing is recorded as
`worktree-missing`; it does not abort the audit and must not be pruned without cleanup authorization.

### 2. Documentation Review

Check if session work requires documentation updates:
- [ ] AGENTS.md / CLAUDE.md - folder structure, workflows, MCP integrations, skills
- [ ] Skill SKILL.md files - if skill behavior changed
- [ ] README files - in relevant folders
- [ ] Operational/configuration docs - if runtime, deployment, or client assumptions changed
- [ ] **Living / generated artifacts** - if the project's CLAUDE.md defines maintained artifacts (e.g. a generated `site/` of HTML status pages, dashboards), follow its documented update contract and refresh them to reflect this session's work. Skip if this session changed no project state.

**Questions to consider:**
- Did we add new folders? → Update the repository's canonical instruction file
- Did we add/modify skills? → Update the canonical instruction file's skills section
- Did we change workflows? → Update relevant docs
- Did production/runtime behavior change? → Update deployment or client docs and record config drift
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
- [ ] Privacy-sensitive temporary artifacts: recordings, transcripts, screenshots, exported mail,
      settings/config backups, credentials, or user-data samples
- [ ] Test files that shouldn't be committed
- [ ] Stale branches that can be deleted or documented
- [ ] Stale PR worktrees that can be removed or documented
- [ ] Dirty secondary worktrees that must be left untouched and called out

Stale PR cleanup guidance:
- For squash-merged PRs, use GitHub PR state as the source of truth; the local branch may not be merged by Git ancestry.
- Before deleting any worktree, run `git -C <worktree-path> status --short --branch`.
- Do not delete dirty worktrees. Document exact path and changed files under pending notes.
- If GitHub API/network is unavailable, document that PR-state verification was skipped rather than guessing.

Temporary artifact guidance:

- Inventory only artifacts created or consumed in the session; do not sweep unrelated temp trees.
- Classify each as disposable build/cache data, reproducibility evidence, or privacy-sensitive data.
- Delete disposable cache only when authorized and not needed for resumption.
- Never delete the sole copy of benchmark, incident, or disclosure evidence without approval.
- Without explicit cleanup authorization, retain privacy-sensitive artifacts, report their bounded
  paths and aggregate size where useful, and request a deliberate keep/delete decision.
- If deletion is authorized, verify absence without echoing private contents.

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

Local Code/CLI sessions bridge local files and Munin. Desktop, Web, and Mobile sessions can only see
Munin, so filesystem-capable sessions must keep it current.

**Update when:** Code was committed or a decision was made this session.
**Skip when:** Pure Q&A, exploration, read-only sessions, or memory already updated during session.

For a multi-repo session, update each affected tracked project whose current state changed; do not
rewrite unrelated project statuses merely because they were included in the Git audit.

**Write protocol:**
1. **Log first** — append decisions and rationale with `memory_log` before changing mutable status.
2. **Read before write** — read the current status and retain its `updated_at` value. If another
   environment wrote since this session began, reconcile rather than blindly overwrite.
3. **Write status with CAS** — update `projects/<name>/status` with the prior `updated_at` as
   `expected_updated_at`. If the server reports a conflict, stop and warn the user.
   - **Phase:** Current project phase or milestone
   - **Current work:** What's actively being worked on (1-2 sentences)
   - **Blockers:** Anything preventing progress (or "None")

Update the cross-project dashboard only when a project was created, completed, blocked, or unblocked.

### 9. Skills Repo Sync

The tracked skill repository is the source of truth. Claude and Codex installations should point to
the same skill folder rather than carry independent copies. Never patch an installed duplicate and
leave the tracked source unchanged.

If skills were created or modified this session and the canonical skill repository has a remote,
commit and push automatically:
```bash
cd <canonical-skill-repo> && git add <skill-name> && git commit -m "update <skill-name>" && git push
```
Skip silently if the canonical repository has no remote configured. Reconcile any divergent
installed copy by replacing it with a symlink to the canonical folder after preserving any unique
content.

### 10. Render the final report

After all mutations and the stable final concurrency comparison, assemble the JSON record described
in **Canonical report contract**, render it, delete the JSON, and return stdout verbatim. Internal
checklist detail, commands, tool logs, discarded alternatives, and potential skill ideas do not
belong in the final response unless they produce a concrete warning or pending action.

## Quick Mode

`/close quick` only checks:

Use the same bounded affected-repository set and refresh each tracking remote before classifying status.

1. Git snapshot for explicitly designated snapshot-mode repos; otherwise audit Git state and run
   `/commit` only when committing is already authorized
2. Dirty secondary worktree warning (`git worktree list` plus `git -C <path> status --short --branch`)
3. Local state file update (always — this is the minimum for session continuity)
4. Final fetch plus `final-recheck.sh compare`; reconcile once or report active concurrent work
5. Canonical rendered report using `mode: "quick"`; all sections remain present

Skip documentation review, skill improvements, Munin updates, and detailed cleanup.
