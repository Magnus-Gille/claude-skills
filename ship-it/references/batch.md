# Batch delivery

Use this reference when the requested scoped outcome contains several
well-defined tickets. The `/ship-it` endpoint and authority rules still apply
to each ticket; this reference adds coordination mechanics only.

A ticket is a Plane ticket (https://tickets.gille.ai), identified by its key
`IDENT-N` such as `GRIM-87`. Read and update tickets through the `tickets` MCP
tools or the `tix` CLI, and use the key (not a GitHub issue number) in the
scoreboard, handoffs and PRs. A PR stays on GitHub and references its ticket as
`Refs <KEY>` plus the Plane URL; there is no automatic PR linking, so a ticket
is closed only by an explicit, authorized update.

## Plan the batch

- Group tickets by owning repository and identify cross-ticket dependencies
  before parallelizing. Keep each ticket's acceptance criteria, exclusions,
  repository, and requested endpoint explicit.
- Complete a representative ticket end to end before scaling the workflow.
  Use small waves, starting with the clearest independent work; adjust wave
  size to the tools, repository load, and review capacity.
- Give every concurrent implementation its own approved isolated worktree and
  branch in the owning repository. Do not use a shared dirty checkout as a
  worker workspace.
- Leave tickets that need production access, cross-repository edits, or an
  unresolved owner decision out of autonomous implementation. Continue
  independent tickets; hold only tickets whose dependency requires the
  unresolved decision or action.
- If a ticket needs build/test dependencies, meet the full credential-free
  isolation requirements in global `AGENTS.md`; a disposable directory alone
  is not isolation. If the required boundary cannot be established, classify
  the install under global policy and hold dependent ticket work while other
  authorized work continues.

## Track, resume, and integrate

Maintain a compact batch scoreboard with ticket key, repository, worktree/branch,
requested endpoint, PR, required-check status, independent-review disposition,
uncertainties, and next dependency. Surface uncertainty to the owner with the
affected ticket and decision needed.

When a worker or session stops unexpectedly, inspect the worktree and provider
state before resuming. Preserve partial work and continue from the verified
state when possible; do not launch a duplicate worker or repeat an external
action while its outcome is unknown. Reconcile provider receipts and immutable
revision identity first.

If same-repository changes collide, resolve the conflict in the affected
worktree. Inspect every conflicted file, preserve both changes only where
their intent is compatible, then rerun the repository's required checks and
independent review for the resulting revision. A rebase or new SHA invalidates
affected evidence, not authorization for an otherwise unchanged action and
scope. Keep collision repair bounded; report an unresolved conflict as a
blocker rather than weakening checks.

## Dependency boundaries

Represent dependencies explicitly. A blocked dependency holds only downstream
work that requires it. Work on unrelated tickets and safe preparation may
continue. A production-only prerequisite does not prevent local implementation
or PR preparation unless that work itself depends on production state. Apply
the global `AGENTS.md` authority rules before any action that crosses the
relevant boundary.

Each ticket reaches only its requested `/ship-it` endpoint. A batch requested
through the PR endpoint can produce reviewed PRs and verified checks, but it
does not authorize or imply merging them. Likewise, merge or production work
must be requested and handled under the global authority rules for each
repository and action.
