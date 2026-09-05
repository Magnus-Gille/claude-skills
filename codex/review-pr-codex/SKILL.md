---
name: review-pr-codex
description: Review a requested pull request or branch diff read-only in this Codex session. Use when the user asks for review-pr-codex or a Codex PR review.
---

# Review PR With Codex

Perform this review directly in the current Codex session. Do not shell out recursively to `codex exec` unless the user explicitly requests a separate child Codex run.

## Workflow

1. Determine the scope.
   - For a PR number, run `gh pr view <number> --json baseRefName,headRefName,title,url`.
   - For a branch, resolve its intended base from the PR or remote metadata.
   - Without an argument, use the current branch's open PR when available; otherwise discover the remote default branch instead of assuming `main`. Stop clearly if no reliable base exists.
2. Read the selected diff and nearby code in proportion to its size. Start with changed files, direct callers, and tests. Keep the review read-only.
3. Review for bugs/regressions, security, API/doc/config drift, error paths, tests, and deployment or portal contracts when they are in scope.
4. Present grounded findings first, ordered by severity, with file/line, evidence, impact, and a concrete fix. Say clearly when no findings are supported and include residual test gaps.
5. If the user explicitly asks to fix findings, or the already-authorized task includes fixing them, implement them and run focused tests; otherwise do not modify, commit, merge, push, or post comments. The review process itself remains read-only.

Do not invent findings from names or conventions alone. Confirm the path is reachable and the claimed behavior is affected by the reviewed change.

This is a native Codex review in the current session, not Claude invoking an external Codex CLI process.
