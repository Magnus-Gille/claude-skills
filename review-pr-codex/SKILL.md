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

- `codex` CLI installed and `OPENAI_API_KEY` set
- A branch with commits diverged from main (or a PR number)

## Workflow

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
