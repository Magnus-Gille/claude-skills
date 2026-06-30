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

**Known-working model ids by auth type (Fix for the `400 invalid_request_error` failure mode):**
- **ChatGPT-account auth** (the common personal-machine case): use `gpt-5.5` (frontier) or `gpt-5.4` (fallback). **Do NOT use `-m gpt-5-codex`** — under ChatGPT-account auth it is rejected with `400 invalid_request_error: 'gpt-5-codex' model is not supported when using Codex with a ChatGPT account`, and the default model then tends to hang (seen 2026-05-31). The `*-codex` model ids are an API-key-auth surface only.
- **`OPENAI_API_KEY` auth:** `gpt-5.5` works; the `*-codex` ids are also available here.

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

### Step 2b: Pre-flight credit/availability probe (do this BEFORE the expensive review)

`codex login status` passing does **not** mean `codex exec` will run — a ChatGPT/workspace plan can be out of credits, and that only surfaces *after* a full `xhigh` round is consumed (observed 3× across May–June 2026). Run a near-free read-only probe first; it costs a trivial call instead of a 15–22 min review round:

```bash
codex exec --sandbox read-only --skip-git-repo-check -m gpt-5.5 "Reply with exactly: PROBE_OK" < /dev/null 2>&1 | tee /tmp/codex-pr-review-probe.txt
PROBE_RC=${PIPESTATUS[0]}
```

Evaluate the probe:
- Output contains `out of credits` / `workspace is out of credits` → **Codex is unavailable.** Do NOT run Step 3 (it would silently burn a round and fail). Go straight to the **adversarial self-review fallback** and tell the user Codex is out of credits.
- Output contains `400` / `model is not supported` → wrong model id for this auth type. Retry the probe with `-m gpt-5.4`; if it still fails, see the Prerequisites model-id table and fall back.
- `PROBE_RC != 0` or no `PROBE_OK` in the output → treat Codex as unavailable; fall back.
- Probe prints `PROBE_OK` → proceed to Step 3 with confidence the account can execute.

Then `rm -f /tmp/codex-pr-review-probe.txt`.

### Step 3: Invoke Codex

Before invoking Codex, compose a one-paragraph **PR context description** from your knowledge of the diff: what it does, why it was written, what the key risk or design decision is. Weave it into the prompt below where `<PR_CONTEXT>` appears — this is what makes Codex's review sharp instead of generic. A security guard PR gets security scrutiny; a refactor gets coupling scrutiny; a data-migration gets idempotency scrutiny.

```bash
codex exec --sandbox workspace-write --skip-git-repo-check -m gpt-5.5 -c model_reasoning_effort='"xhigh"' "You are a senior code reviewer performing a thorough review of a pull request.

<PR_CONTEXT>

FIRST, before any exploration, create /tmp/codex-pr-review-result.md containing a single line: '# Codex review (in progress)'. This guarantees a result file exists even if you run long. As you complete the review, OVERWRITE that file with your full findings. Do NOT defer the first write until the end.

Then read the diff at /tmp/codex-pr-review-diff.txt and the commit log at /tmp/codex-pr-review-commits.txt.
Also read any source files referenced in the diff to understand the full context — including test files that cover the changed code. Keep exploration proportional to the diff size — for a small diff, read only the changed files plus their direct tests; do not wander the whole repo.

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
- **No turn-budget flag exists.** `codex exec` (as of CLI 0.142.x) has no `--max-turns`/turn-cap option, so the only guards against the "runs 15–22 min, exits 0, writes nothing" hang (mode B, seen 2026-05-31 & 2026-06-23) are: (a) the **write-first** instruction in the prompt above (a placeholder result file is created before any exploration, so a hang still leaves a detectable artifact), (b) the **`< /dev/null`** stdin redirect, and (c) the Bash `--timeout`. If mode B recurs on a small diff, retry once with `-c model_reasoning_effort='"high"'` (less likely to wander) before falling back.
- Codex writes its output to a file; do NOT rely on `-o` for review content

### Step 4: Read and verify the review

First scan the raw Bash output for an **out-of-credits / hard error** signature — `out of credits`, `workspace is out of credits`, `429`, `quota`. If present, Codex consumed the round and produced nothing usable: **do NOT try to salvage an empty log.** Go directly to the **adversarial self-review fallback** (or a non-Anthropic provider — see below) and label the review honestly. (Step 2b should have caught this earlier; this is the backstop for an account that runs dry mid-review.)

Otherwise read `/tmp/codex-pr-review-result.md` and check for failure modes:

- **File contains only the `# Codex review (in progress)` placeholder (or is missing):** mode B — Codex hung/exited without finishing. Check the Bash log for partial findings; if the log is also empty (just repo grepping/reading, no synthesized findings), treat this as a **failed Codex run** and branch to the fallback. Do not pass off an empty log as "clean."
- **File is a brief conversational summary (< 300 chars):** Codex wrote chatter instead of the review. Pull findings from the execution log if present; if absent, fall back.
- **File looks complete:** Proceed to Step 5.

**Auto-fallback target (Fix 3).** When the above branches to a fallback, prefer in this order so the **cross-model property is preserved** where possible:
1. A **non-Anthropic** reviewer that's available — e.g. Gemini / `agy` (Antigravity) via the `debate` skill — so a different model family still reviews the diff.
2. Otherwise the **adversarial multi-lens self-review Workflow** documented above (worked reliably and found real bugs on hugin #68). Label it as a self-review, not the cross-model check, and flag the PR for a real Codex pass when credits return.

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
