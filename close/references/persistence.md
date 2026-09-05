## Session Handoff (Local State File)

Update the project's local state file with resumption context. This is the primary handoff mechanism — the next session reads this file first.

Apply this per affected repository whose execution state changed substantively. Do not create or
rewrite a handoff merely because a repo was inspected read-only. A coordinating/system repo may carry
the consolidated cross-repo summary, but it does not replace a changed owning repo's local handoff.

**Use the handoff file(s) declared by the repository's canonical instructions first.** Only when no declaration exists, detect an established convention from the files below; do not let a stale roadmap override an explicit handoff declaration:

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

## Munin Memory Update

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

