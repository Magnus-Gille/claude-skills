---
name: ticket-fleet
description: Resolve a batch of GitHub tickets via parallel headless Claude Code sessions — one isolated git worktree per ticket, gated permissions, triple review (Codex + local-model first-pass + orchestrator comment), interrupt-resume, and merge orchestration. Use when the user wants many well-scoped tickets solved autonomously across one or more repos.
---

# /ticket-fleet — Headless Ticket Fleet

Resolve N well-scoped GitHub tickets in parallel: each ticket gets its own headless
`claude -p` session in an isolated git worktree of the owning repo (so the repo's
CLAUDE.md governs it), produces a PR, self-runs a Codex review, and reports
uncertainties. The orchestrator (you, the main session) does a second review leg per
PR, relays uncertainties to the user, and handles merges + conflicts.

**Proven:** 2026-07-03→04, 23 tickets across 10 repos, 29 PRs merged, 0 rejected;
cross-model review caught 2 criticals + 1 high the authoring model missed; survived a
mid-flight spend-limit outage via `--continue` resume.

## Usage

- `/ticket-fleet <ticket-list>` — e.g. `verdandi#9 skuld#3 heimdall#104` or "all open from:grimnir tickets"

## Assets

- `scripts/run-ticket.sh <repo_dir> <issue_no> <model> <prompt_file> <log_file>` — creates
  worktree `~/repos/.wt/<repo>-t<issue>` on branch `ticket/<issue>-headless` from
  `origin/<default>`, runs the headless session with the gated allowlist, logs everything.
- `scripts/continue-ticket.sh <worktree_dir> <model> <log_file>` — resumes an interrupted
  session in its worktree via `claude -p --continue` (conversation context + partial edits
  survive).
- `scripts/run-ticket-m5.sh` / `scripts/continue-ticket-m5.sh` — **M5-enabled variants**
  (proven 2026-07-04, 4/4 tickets): add `mcp__m5__ask`/`mcp__m5__list_models` to the allowlist
  plus optional per-ticket extra tools as trailing args (e.g. `"Bash(curl:*)"` for live-seam
  tickets). Use these when sessions should offload bounded sub-tasks to the M5 box; include an
  M5-offload paragraph in the prompt's EXTRA section requiring the session to VERIFY every M5
  output before use, and add an `M5:` line to the FINAL REPORT format. **Reliability data so
  far (2026-07-04):** qwen3-coder review legs were clean and correct on 3 TypeScript diffs but
  confabulated 5-of-6 findings on a shell/docs diff — trust the M5 review leg on TS, treat its
  shell/docs findings as hypotheses to verify, and always verify its codegen with tests.
- `templates/ticket-prompt.md` — the per-ticket prompt. Fill `{ISSUE}`, `{TITLE}`,
  `{EXTRA_TASK_SPECIFIC_GUIDANCE}` (2–6 sentences: concrete scope, files, constraints,
  known traps). The EXTRA section is where quality is won — be specific per ticket.

## Workflow

### 1. Triage the tickets
Group by repo. Well-scoped, self-contained tickets only — split or skip anything needing
production access, cross-repo edits, or the user's judgment mid-flight. Per-ticket model:
`sonnet` for mechanical/clear-spec, `opus` for architectural/security. If a repo has a
concurrent active session (dirty main checkout), schedule its tickets LAST and say so in
the prompt ("do not touch <branch/area>").

### 2. Write prompts, launch in waves
One prompt file per ticket from the template. Launch each via `run-ticket.sh` as a
**background Bash task** (no 10-min cap; you get a notification per completion).
Wave size ~6–8; mechanical wave first (validates the pipeline cheaply), harder wave
after. **Pilot one ticket end-to-end before the first fan-out.**

### 3. Permission posture (hard-learned)
- `--dangerously-skip-permissions` **will be refused** by the auto-mode classifier —
  correctly. The scripts use `--permission-mode acceptEdits` + a scoped `--allowedTools`
  list (git/gh/npm/node/python3/codex/shellcheck/bash/sh/make + read-only utils).
- Include `Bash(bash:*)` and `Bash(sh:*)` — without them sessions detour through
  `python3 subprocess` to run test scripts.
- Sessions are told: PR only — no deploys, no service restarts, no ssh, no STATUS.md.

### 4. Per-completion processing (orchestrator loop)
On each completion notification:
1. `tail -c 3000 <log>` — read the FINAL REPORT (PR / TESTS / CODEX / UNCERTAINTIES / STATUS).
2. **Second review leg:** fetch the PR diff (bounded), independently verify the riskiest
   claim yourself (grep the worktree — it still exists), optionally pipe the diff to a
   local model for a first-pass (see §7). Post findings as a PR **comment, never an
   approval** — the classifier blocks orchestrator self-approval of its own spawn's PR,
   and it's right; the formal stamp stays with the human.
3. Relay the session's UNCERTAINTIES to the user (they're consistently the highest-value
   output). File follow-up tickets for real discoveries (owning repo, `from:<sender>`
   label, board).

### 5. Interrupts & failures
- **Spend-limit / API death mid-flight:** sessions die with partial work in their
  worktrees. Do NOT delete and relaunch — `continue-ticket.sh` resumes with full context.
  Check `git log @{u}..` + `status --porcelain` per worktree first to see what survived.
- **Same-repo PR collisions** (e.g. two tickets both add a `make test` target): rebase in
  the ticket worktree, merge the hunks (union), re-run the full suite, `push
  --force-with-lease`. Expect this whenever >1 ticket touches one repo.
- After resolving rebase conflicts, `grep -c '^<<<<<<<'` EVERY conflicted file before
  `rebase --continue` — a truncated conflict listing hides hunks (bit us once).

### 6. Merge & cleanup
- Merge only on the user's word. `--squash --delete-branch`; check `mergeStateStatus`
  (BEHIND → `gh pr update-branch`; UNSTABLE → CI running, use `gh pr merge --auto`).
- Check merge **gates** from the reports before merging (e.g. "env var X must exist in
  prod first") — verify read-only via ssh, don't assume.
- After merges: remove worktrees (`git worktree remove`, clean-only — keep any backing an
  unmerged PR), delete merged local branches, **pull every local repo before any deploy**
  (stale-checkout trap — see the deploy skill).

### 7. Local-model review leg (optional, cost-saving)
Pipe each PR diff to the m5 box (`mcp__m5__ask`, qwen3-coder) via a haiku pipe-agent that
reads the diff file and inlines it into the ask prompt — the diff never enters root
context. **Never call `ask` with the diff "attached" but not actually in the prompt** —
you'll get a worthless NO FINDINGS on empty input (bit us once). If the box times out
(load/cold-swap), fall back without ceremony and say so in the PR comment.

## Report format to the user

Running scoreboard per wave: PR / tests / Codex verdict / your leg. Consolidate at the
end: totals, criticals caught, grouped uncertainties as decision buckets (activation
steps, policy blessings, filed follow-ups, recurring fleet themes), pending user actions.
