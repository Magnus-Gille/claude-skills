# Codex CLI invocation notes

These are dated local observations, not promises about every Codex CLI release.
Recheck `codex exec --help` and the installed configuration before relying on them.

## 2026-09-05

- An earlier invocation appeared to wait when standard input stayed open while the
  prompt was supplied as a positional argument. Redirect standard input from
  `/dev/null` for that form, unless stdin is intentionally the prompt source.
- An earlier invocation did not reliably create the file requested with `-o`.
  Capture stdout and stderr, record the exit status, and verify that the output file
  exists and is non-empty. Treat a missing or empty result as a failed review and
  report the captured diagnostics; do not call it a clean review.
