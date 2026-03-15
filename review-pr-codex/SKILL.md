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

```bash
git diff main...HEAD > /tmp/codex-pr-review-diff.txt
git log --oneline main..HEAD > /tmp/codex-pr-review-commits.txt
```

Check the diff size. If over 5000 lines, warn the user that the review may be expensive and ask to proceed.

### Step 3: Invoke Codex

```bash
codex exec --full-auto "You are a senior code reviewer performing a thorough review of a pull request.

Read the diff at /tmp/codex-pr-review-diff.txt and the commit log at /tmp/codex-pr-review-commits.txt.
Also read any source files referenced in the diff to understand the full context.

Review the changes for:
1. **Bugs and regressions** — logic errors, broken edge cases, state that was correct before but isn't now
2. **Security issues** — injection, auth bypasses, secrets exposure, unsafe input handling
3. **API contract mismatches** — does the code match what the docs/README claim?
4. **Missing error handling** — unhappy paths that silently fail or crash
5. **Doc/config drift** — version numbers, setup instructions, or config files that contradict the code changes

For each finding, include:
- **Severity:** critical / medium / low
- **File and line:** specific location
- **Description:** what's wrong and why it matters
- **Suggested fix:** how to address it (be concrete)

If you find no issues, say so explicitly — don't invent problems.

Write your complete review to /tmp/codex-pr-review-result.md in markdown format." 2>&1
```

**Important:**
- Use `--full-auto` (not `-q` or `-o`)
- Set Bash tool `--timeout 300000` (Codex can take a few minutes)
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
