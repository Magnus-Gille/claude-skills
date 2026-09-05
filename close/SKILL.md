---
name: close
description: Close a coding-agent session or produce its final handoff only when the user explicitly asks to close, wrap up, or produce an end-of-session handoff.
---

# Close a session

Audit only repositories affected by this session, preserve unrelated work, and complete the authorized handoff. An ordinary reply is not a session close. A close does not authorize publication, deployment, credential operations, or destructive cleanup.

- For Git/worktree scope, snapshot exceptions, and the mandatory final concurrency check, read [git-audit](references/git-audit.md).
- When execution state or project truth changed, read [persistence](references/persistence.md). Skip state rewrites for read-only inspection.
- Only for personal notes/workspaces with capture/tasks conventions, read [personal-workspace](references/personal-workspace.md).
- For every close, read [report-contract](references/report-contract.md) and return `scripts/render-report.py` output verbatim. Preserve all fields in quick mode; missing evidence is not a clean result.

All script paths are relative to the skill root. Preserve a reversal recipe and audit event for mutations where required by project policy.

## Documentation Review

Check if session work requires documentation updates:
- [ ] AGENTS.md / CLAUDE.md - folder structure, workflows, MCP integrations, skills
- [ ] Skill SKILL.md files - if skill behavior changed
- [ ] README files - in relevant folders
- [ ] Operational/configuration docs - if runtime, deployment, or client assumptions changed
- [ ] **Living / generated artifacts** - if the project's canonical instruction file defines maintained artifacts (e.g. a generated `site/` of HTML status pages, dashboards), follow its documented update contract and refresh them to reflect this session's work. Skip if this session changed no project state.

**Questions to consider:**
- Did we add new folders? → Update the repository's canonical instruction file
- Did we add/modify skills? → Update the canonical instruction file's skills section
- Did we change workflows? → Update relevant docs
- Did production/runtime behavior change? → Update deployment or client docs and record config drift
- Did deployment copy local-only files, require manual cleanup, or change rsync/exclude behavior? → Document the operational fix or verified cleanup location.
- Does the canonical instruction file define living artifacts (e.g. `site/`)? → Apply their documented update contract

## Unsaved Plans & Artifacts

Before reviewing skill improvements, check whether any significant work product from the session exists only in conversation context and hasn't been persisted to a file:

- **Implementation plans** produced by the `/plan` skill or a `Plan` agent — save to a `plan.md` or `*-plan.md` file in an appropriate location (e.g., `debate/`, `docs/`, repo root).
- **Research summaries** that aren't already written to your notes/research directory.
- **Decision write-ups** that aren't in Munin or a committed file.
- **Debate documents** (if the `debate-claude` skill ran) — verify `debate/*-summary.md` and `debate/*-critique-log.json` were written; the raw files are gitignored but summaries and critique logs should persist.

If anything is only in the conversation, write it to a file now. Ask the user where to save if the right location is unclear.

## Skill Improvements

Review session for potential skill enhancements:
- Did we repeat a pattern that could be automated?
- Did a skill's instructions prove incomplete or unclear?
- Did we discover better approaches mid-session?

**If improvements identified:**
- Note them for the user
- Offer to update the skill now

## Cleanup

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

## Skills Repo Sync

Update the canonical skill source and reconcile installed copies within the authorized task. Preserve intentional harness adapters; inspect unique behavior before replacing any copy with a symlink. Do not modify unrelated installations.

A close or local skill edit does not authorize publication. Commit only scoped changes under the owner's existing authority; push or create a PR only with an explicit owner request and exact target/diff preview, following the repository's branch policy. Report pending publication without blocking an otherwise complete local close.

## Render the final report

After all mutations and the stable final concurrency comparison, assemble the JSON record described
in [report-contract](references/report-contract.md), render it, delete the JSON, and return stdout verbatim. Internal
checklist detail, commands, tool logs, discarded alternatives, and potential skill ideas do not
belong in the final response unless they produce a concrete warning or pending action.

## Quick Mode

`/close quick` only checks:

Use the same bounded affected-repository set and refresh each tracking remote before classifying status.

1. Git snapshot for explicitly designated snapshot-mode repos; otherwise audit Git state and run
   `/commit` only when committing is already authorized
2. Dirty secondary worktree warning (`git worktree list` plus `git -C <path> status --short --branch`)
3. Local state file update only for substantive execution-state changes; skip read-only inspection
4. Final fetch plus `final-recheck.sh compare`; reconcile once or report active concurrent work
5. Canonical rendered report using `mode: "quick"`; all sections remain present

Skip documentation review, skill improvements, Munin updates, and detailed cleanup.
