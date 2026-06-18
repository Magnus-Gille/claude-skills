---
name: review-pr-codex
description: Run a cross-model PR review using Codex CLI. Invokes Codex headless to review the current branch diff, then reads findings and fixes issues or reports to user.
argument-hint: [PR number or branch name]
---

# /review-pr-codex - Cross-Model PR Review via Codex

Run an adversarial code review of the current branch using the Codex CLI (a different model family), then act on the findings. The value is catching blind spots that Claude misses.

## Usage

- `/review-pr-codex` - Review the current branch diff against main
- `/review-pr-codex 42` - Review PR #42

## Prerequisites

- `codex` CLI installed and **authenticated** — *either* via ChatGPT sign-in (`codex login`, the common case on a personal machine) *or* via an `OPENAI_API_KEY` env var. **Do not gate on `OPENAI_API_KEY` alone** — ChatGPT-authenticated Codex works with no API key set, and bailing on a missing key is a false negative (it stores auth in `~/.codex/auth.json`). Verify with `codex login status` (prints `Logged in ...`); only treat Codex as unavailable if that fails *and* no `OPENAI_API_KEY` is set. **A passing `codex login status` does NOT guarantee Codex will run** — a ChatGPT/workspace plan can be out of quota, so `codex exec` may still fail at run time with `ERROR: Your workspace is out of credits. Add credits to continue.` Confirm availability at *exec* time, not just auth time; on genuine unavailability, use the **adversarial self-review fallback** (below).
- A branch with commits diverged from main (or a PR number)

## When Codex is unavailable — adversarial self-review fallback

Codex can fail in a way `codex login status` does **not** catch: auth succeeds ("Logged in using ChatGPT") but `codex exec` returns `ERROR: Your workspace is out of credits` (quota/credit exhaustion), or a transient API error. The review subagent comes back empty or with that error. **When Codex is genuinely unavailable and topping up isn't an option, do NOT silently skip the review** — fall back to an **adversarial self-review** as the substitute gate:

1. **Multi-lens review.** Spawn several skeptical reviewer agents in parallel (a small `Workflow` with one agent per lens works well), each with a *distinct* lens — e.g. for a code PR: billing/correctness, concurrency & error-paths, privacy/security, test-adequacy; for a web/docs PR: docs-vs-reality, web-security/secret-leak, clarity. Each reads the diff read-only (`git diff main...HEAD`, `git show <branch>:<file>`) and returns structured findings (severity / file:line / issue / fix). Tell each agent to be adversarial — *assume there is a bug and hunt for the worst one* — but to substantiate every finding from the code.
2. **Refute-pass (this is what makes a self-review trustworthy).** For each critical/high finding, spawn a skeptic that tries to *refute* it from the actual code; default `confirmed=false` unless demonstrable (many review findings are false positives — the guard exists elsewhere, the path is unreachable, a test already covers it). Only confirmed findings block the merge. Without this step a self-review churns on noise.
3. **Fix the confirmed findings test-first, then merge** on a clean refute-pass — the same bar as Codex (no surviving critical/medium). Findings that are real but bigger/orthogonal → file as GitHub issues and fast-follow rather than bloat the PR.

**Label it honestly — it is NOT the cross-model check this skill exists for.** The whole value of Codex is a *different model family* catching Claude's blind spots, which Claude-reviewing-itself cannot fully replace. So: tell the user it was a self-review (not Codex), note it in the PR/commit, and **flag those PRs for a real Codex pass when credits/availability return.** This fallback is strictly better than (a) skipping review, or (b) blocking the whole pipeline on a credit top-up the user has declined — but it is a substitute, not an equal.

## Workflow

> **Run the verbose work in a subagent (recommended).** Steps 2–4 generate a large diff and a long Codex execution log that you don't need verbatim — only the structured findings. Delegate Steps 1–4 to a subagent (e.g. an `Agent`/`Task` with `model: "sonnet"`) that runs the Codex invocation and **returns only the findings** (severity, file:line, issue, suggested fix), then you act on them in Steps 5–6 in the root session. This keeps the diff and raw Codex log out of root context — which matters when the review is one step in a longer session, and is essential for multi-round review loops (review → fix → re-review), where accumulated logs would otherwise force premature compaction. Give the subagent the exact commands and `< /dev/null` / timeout caveats below verbatim, and tell it explicitly what to return. **In the subagent prompt, state the auth rule from Prerequisites explicitly** — verify Codex with `codex login status`, and do NOT abort just because `OPENAI_API_KEY` is unset (ChatGPT-authenticated Codex is the normal case and needs no key). When reviewing a PR branch held in a worktree, point the subagent at that worktree dir. (For a quick one-off review in a short session, running inline is fine.)

### Step 1: Determine what to review

**If a PR number is given:**
```bash
gh pr view <number> --json baseRefName,headRefName
```
Use the base and head refs for the diff.

**If no argument:**
Use the current branch vs `main`. Verify there are commits to review:
```bash
git log --oneline main..HEAD
```
If empty, tell the user there's nothing to review.

### Step 2: Generate the diff context

Clean up any stale temp files from a prior run first — Codex runs in a shared environment and a leftover result file from a previous project will pollute the review:

```bash
rm -f /tmp/codex-pr-review-diff.txt /tmp/codex-pr-review-commits.txt /tmp/codex-pr-review-result.md
git diff main...HEAD > /tmp/codex-pr-review-diff.txt
git log --oneline main..HEAD > /tmp/codex-pr-review-commits.txt
```

Check the diff size. If over 5000 lines, warn the user that the review may be expensive and ask to proceed.

### Step 3: Invoke Codex

Before invoking Codex, compose a one-paragraph **PR context description** from your knowledge of the diff: what it does, why it was written, what the key risk or design decision is. Weave it into the prompt below where `<PR_CONTEXT>` appears — this is what makes Codex's review sharp instead of generic. A security guard PR gets security scrutiny; a refactor gets coupling scrutiny; a data-migration gets idempotency scrutiny.

```bash
codex exec --sandbox workspace-write --skip-git-repo-check -m gpt-5.5 -c model_reasoning_effort='"xhigh"' "You are a senior code reviewer performing a thorough review of a pull request.

<PR_CONTEXT>

Read the diff at /tmp/codex-pr-review-diff.txt and the commit log at /tmp/codex-pr-review-commits.txt.
Also read any source files referenced in the diff to understand the full context — including test files that cover the changed code.

Review the changes for:
1. **Bugs and regressions** — logic errors, broken edge cases, state that was correct before but isn't now
2. **Security issues** — injection, auth bypasses, secrets exposure, unsafe input handling
3. **API contract mismatches** — does the code match what the docs/README/CHANGELOG claim?
4. **Missing error handling** — unhappy paths that silently fail or crash
5. **Test coverage gaps** — changed behaviour that has no test, or tests that assert the wrong thing
6. **Doc/config drift** — version numbers, setup instructions, or config files that contradict the code changes

For each finding, include:
- **Severity:** critical / medium / low
- **File and line:** specific location
- **Description:** what's wrong and why it matters
- **Suggested fix:** how to address it (be concrete)

If you find no issues, say so explicitly — don't invent problems.

Write your complete review to /tmp/codex-pr-review-result.md in markdown format." < /dev/null 2>&1
```

**Important:**
- **Always redirect stdin from `/dev/null`** (`… < /dev/null 2>&1`). `codex exec` reads stdin even when the prompt is passed as an argument, so in a non-TTY shell (Claude Code's Bash tool, background tasks, CI) it otherwise blocks forever on `Reading additional input from stdin...`. Do **not** wrap the call in `script -q /dev/null` to fake a TTY — `script` fails in socket-backed shells with `tcgetattr/ioctl: Operation not supported on socket`, leaving you with a silent hang. `< /dev/null` is the portable fix and works in both TTY and non-TTY contexts.
- Use `--sandbox workspace-write` (not `-q` or `-o`, and NOT the deprecated `--full-auto` — Codex 0.132+ warns and `--sandbox workspace-write` is the replacement). Add `--skip-git-repo-check` so it also runs in non-git working dirs (without it Codex refuses with "Not inside a trusted directory").
- **Pin the strongest model and effort:** `-m gpt-5.5 -c model_reasoning_effort='"xhigh"'`. Cross-model PR reviews are high-stakes — use the "best model / Extra High" setting, not the everyday config default. (`gpt-5.5` is the current Codex frontier model; if it's unavailable in the active account, fall back to `-m gpt-5.4`.)
- Set Bash tool `--timeout 600000` — `xhigh` effort can push close to the limit.
- Codex writes its output to a file; do NOT rely on `-o` for review content

### Step 4: Read and verify the review

Read `/tmp/codex-pr-review-result.md`. Check for failure modes:

- **File missing:** Codex didn't write it. Extract review content from the Bash tool output (the Codex execution log) and proceed with that.
- **File is a brief summary (< 300 chars):** Codex wrote a conversational summary instead of the real review. Same recovery — pull content from the execution log.
- **File looks complete:** Proceed.

### Step 5: Present findings and act

**If critical or medium findings exist:**

Present each finding to the user with the severity, location, and suggested fix. Ask:
> "I can fix these now, or you can review them first. What do you prefer?"

If the user says fix:
- Fix each issue
- Run tests to verify fixes don't break anything
- Stage and commit with message: `fix: address codex review findings`

**If only low findings or no issues:**

Report the clean review to the user. No action needed.

### Step 6: Clean up

```bash
rm -f /tmp/codex-pr-review-diff.txt /tmp/codex-pr-review-commits.txt /tmp/codex-pr-review-result.md
```

## Key Rules

1. **Always read the full review output** — don't summarize findings you haven't read
2. **Don't auto-fix without asking** — present findings first, let the user decide
3. **Run tests after fixing** — never push fixes without verifying they work
4. **Don't argue with valid findings** — if Codex is right, concede and fix it
5. **Do push back on invalid findings** — explain why to the user so they can judge
6. **Protect root context** — delegate the verbose Steps 2–4 to a subagent that returns only the structured findings; never let a full diff + raw Codex log accumulate in the root session, especially across review→fix→re-review rounds
