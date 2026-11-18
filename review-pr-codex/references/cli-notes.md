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

## 2026-11-15 (codex-cli 0.169.0)

- `--disable multi_agent` and `--disable multi_agent_v2` leave the sub-agent tools
  (`spawn_agent`, `wait_agent`, `send_message`, `followup_task`, `interrupt_agent`,
  `list_agents`) in the reviewer's tool list. `-c agents.enabled=false` removes them.
  Counting `spawn_agent` in `codex debug prompt-input` output: 8 with no options, 8 with
  either `--disable` form, 0 with `-c agents.enabled=false`.
- Before a run, render the effective prompt and tool list locally with
  `codex debug prompt-input`, passing the same `-c`, `--enable` and `--disable` options
  the review will use, and confirm no `spawn_agent` appears. This makes no model call.
- A reviewer that has the tools is also told to use them when `~/.codex/AGENTS.md`
  links the global "Aggressively delegate" rule. The review prompt should say the
  reviewer is a leaf assignment and must not delegate.
- Not verified: whether `--ignore-user-config` keeps `~/.codex/AGENTS.md` out of the
  prompt (`codex debug prompt-input` does not accept that option), and any Codex CLI
  version other than 0.169.0.
