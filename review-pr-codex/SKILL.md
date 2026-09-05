---
name: review-pr-codex
description: Run a requested, read-only cross-model review of a pull request or branch diff using the installed Codex CLI. Use only when the user asks for review-pr-codex or a Codex PR review.
---

# /review-pr-codex — Read-only Codex review

This Claude-facing skill invokes the installed Codex CLI as a separate reviewer. It reports findings for the current user to assess. It never edits files, commits, merges, pushes, posts comments, or silently substitutes another reviewer.

## Resolve the review scope

- For a PR number, read its base and head with:

  ```bash
  gh pr view <number> --json baseRefName,headRefName,title,url
  ```

- For a branch argument, resolve the branch and its intended base from the repository's PR or remote metadata.
- With no argument, first inspect whether the current branch has an open PR. If it does not, discover the remote default branch from Git rather than assuming `main`; stop clearly if no reliable base exists. Confirm that the selected range contains changes.

Keep the review scoped to the selected base/head and the changed files plus directly relevant tests and callers. Do not send unrelated repository content or secrets to another model.

## Prepare a read-only invocation

Before constructing the command, inspect the installed CLI rather than relying on remembered flags:

```bash
codex exec --help
codex exec review --help
```

Read [references/cli-notes.md](references/cli-notes.md) for dated, unverified
local observations about invocation behavior. They are failure-handling hints, not
CLI guarantees.

Create a unique scratch directory with `mktemp -d`; never use a shared fixed `/tmp/codex-pr-review-*` path. Store only the selected diff, commit summary, and returned report there. The scratch directory must not contain credentials or unrelated files.

Use an invocation supported by the help output that is explicitly read-only and ephemeral, for example:

```bash
set +e
codex exec -s read-only --ephemeral -C <worktree> -o <scratch>/result.md <prompt> \
  </dev/null > <scratch>/stdout.log 2> <scratch>/stderr.log
review_exit=$?
set -e
```

Redirect stdin when the prompt is a positional argument. Capture stdout, stderr,
and the exit status separately; inspect all three and treat a non-zero status as a
failed review. Do not assume `-o` produced a usable file: check that it exists and
is non-empty, and use captured stdout only when it contains the complete returned
report. If there is no complete result, report the invocation failure rather than a
clean review. Do not use workspace-write, danger-full-access, automatic approvals,
or commands that allow the reviewer to alter the repository. A read-only shell
sandbox does not by itself disable MCP, hooks, network access, or other configured
capabilities: inspect the effective configuration and available flags, and narrow
them where supported. Prefer a frozen, supplied diff/commit context with no tools
when the CLI supports that mode. If the installed CLI cannot provide a suitably
scoped review, stop and report the actual limitation.

Respect a model explicitly selected by the user. If no model is selected, use the configured/default model. Do not silently substitute a fallback model. Record the actual runtime model from CLI output or structured events; never infer it from the requested flag alone. If the CLI does not expose it, report that it was not exposed.

The prompt must tell the reviewer to inspect only the selected diff and relevant context, avoid all mutations and external communication, and return findings with severity, file/line, evidence, impact, and a concrete fix. Require it to say explicitly when no grounded findings exist.

## Report findings

Read the complete returned message and distinguish a failed/empty invocation from a clean review. Present findings first, ordered by severity, with file and line references. Include residual test gaps and the actual reviewer/model identity when available.

Do not auto-fix or merge based on findings. The review process itself never mutates; code changes or publication require an explicit user request or an already-authorized task that includes them. If Codex is unavailable, report the failure and let the user choose a next step; do not silently replace the cross-model review with a forced multi-agent or self-review.

Remove the unique scratch directory after capturing the report unless the user asks to preserve it.
