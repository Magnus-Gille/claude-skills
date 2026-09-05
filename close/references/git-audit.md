## Git Snapshot

**Behavior depends on the repo type:**

#### Snapshot-mode repos (e.g. a personal notes/working directory with no remote)
Snapshot mode requires an explicitly designated repository and owner-authorized snapshot scope. A missing remote alone does not authorize capturing everything. Inspect the staged diff, exclude secrets and unrelated user work, and stage only authorized paths. Commit a dated snapshot only when authorized; do not push from this mode. If there is nothing to capture, continue.

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

- Uncommitted tracked changes: classify task-owned versus unrelated changes; preserve unrelated work.
- Expected local-only/untracked files versus files that belong in Git.
- Unmerged feature branches and unpushed commits.
- Deployed-but-uncommitted changes or production receiving local-only files.
- Stale PR branches/worktrees, including squash-merged branches that are not Git ancestors of main.
- Dirty secondary worktrees and branches with gone upstreams.

Actions:

- Commit task-owned changes only within existing authority, using the repository conventions.
  Preserve unrelated changes and do not stash them without explicit authorization. Otherwise report
  retained changes; a local close does not require a new commit decision.
- If only expected local-only files exist, document and leave them; do not commit scratch/config by
  default.
- Report remaining feature branches. Merge only when explicitly requested and the repository's review/CI requirements pass; closing a session does not require a merge decision.
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

