# Isolated reviewer invocation

The reviewer receives the complete round package through stdin. The package is a frozen, scoped, sanitized rendering prepared by the conductor. It contains the artifact and only the context explicitly selected for that round. The reviewer must treat it as the sole source of context and must not try to inspect the live repository, filesystem, Munin, browser, hooks, plugins, settings, or MCP.

Do not pre-assemble private or unnecessary context. Redact credentials, tokens, personal data, internal hostnames, and unrelated paths before the package is created. Do not include ambient tool instructions in the package.

## Model selection

- If the user names a model or version, pass that exact identifier. Do not add `--fallback-model` or silently substitute another model.
- If the user does not name a model, the conductor may select a suitable configured model and must report the requested and actual model after the run.
- Use high effort when the selected model supports it. If the exact model or requested effort is unavailable, stop and report the limitation rather than changing the model choice automatically.
- Verify actual model metadata from the structured CLI result when available. A model name in reviewer prose is not evidence.

## Safe CLI baseline

Before changing the command, run the installed `claude --help` and, when needed, `claude -p --help`. Use only flags shown by that help. The current safe baseline is:

```bash
printf '%s' "$round_prompt" | claude -p \
  --output-format json \
  --model "$reviewer_model" \
  --effort high \
  --no-session-persistence \
  --no-chrome \
  --safe-mode \
  --restricted \
  --tools "" \
  --strict-mcp-config \
  --mcp-config '{"mcpServers":{}}' \
  --permission-mode plan
```

This baseline disables custom settings, hooks, plugins, skills, agents, and MCP startup; restricts built-in tools; exposes an empty tool list; prevents edits; and prevents session persistence. Keep the reviewer input on stdin. Do not add `--setting-sources`, ambient project settings, `dontAsk`, a debug file, browser integration, or a fallback model by default.

## CLI verification evidence

The safe baseline was checked against the installed CLI with `claude --help` and `claude -p --help` during this cleanup session on 2026-09-05. Help exposed these exact flags: `--output-format json`, `--model`, `--effort`, `--no-session-persistence`, `--no-chrome`, `--safe-mode`, `--restricted`, `--tools`, `--strict-mcp-config`, `--mcp-config`, and `--permission-mode plan`. Re-run help in the target environment before use; version drift wins over this note. Two read-only debate rounds then completed successfully using this baseline on 2026-09-05. Structured CLI metadata identified `claude-fable-5-1` for both substantive reviews, with high effort requested, exit status 0, and no tool access.

If the local CLI does not support a flag in this command, re-check its help and use the narrowest verified equivalent. Never weaken the isolation because startup is inconvenient. Authentication or account repair is outside this skill; report a failure for the conductor to handle.

## Round 1 prompt envelope

The conductor supplies a complete frozen package after writing the draft and self-review. The prompt should contain the following shape, with the relevant type lens from [lenses](lenses.md):

```text
You are acting as a grounded but adversarial reviewer.

The conductor has supplied a frozen, sanitized review package below. Treat it as the sole source of context. Do not access tools, files, settings, hooks, plugins, MCP, Munin, or the live repository, and do not attempt to write a file.

Review the draft against its stated assumptions, failure modes, rejected alternatives, unknowns, and self-review. Be skeptical but intellectually honest; do not strawman.

Universal:
- Acknowledge strengths before attacking weaknesses.
- Cite concrete issues with file and line references when the package provides them.
- Flag unsupported claims, missing baselines, and methodological gaps.

[Insert the declared type-specific lens from lenses.md.]

OUTPUT: Begin with a brief `Context loaded` section listing the package sections actually received and any gaps or conflicts. Do not claim to have used tools or live project context. Then print the complete critique in markdown. Do not attempt to write a file or identify your model in prose.

--- BEGIN FROZEN ROUND PACKAGE ---
[sanitized package]
--- END FROZEN ROUND PACKAGE ---
```

The package must include enough context for a grounded critique. If it does not, record the gap rather than inviting ambient access.

## Round 2 prompt envelope

After reading the Round 1 critique, the conductor writes a response with concessions, partial concessions, defenses, and revised positions. Then create a new frozen, sanitized package containing the original draft, self-review, Round 1 critique, and the response. Add only explicitly selected refreshed context; do not let the reviewer observe live state.

Use the same exact model, effort, safe CLI baseline, universal framing, and type-specific lens as Round 1. Add these questions:

- Which concessions are genuine and adequate?
- Which defenses are valid, and which dodge the point?
- What new issues emerged, including risks from the type lens?
- Is there any difference between the explicitly supplied Round 1 and Round 2 context?
- What is the single most important next step?

Require the same `Context loaded` section and complete markdown response. Capture the structured CLI result and stdout yourself, and write `debate/<topic>-claude-rebuttal-1.md` only after checking that the result is a substantive rebuttal rather than an authentication or startup error.

## Output checks

Write captured reviewer output to the appropriate artifact. Sanity-check that it is the expected critique or rebuttal, not an auth error, startup transcript, or very short response. Record the actual model from structured metadata; if metadata is absent or ambiguous, mark the model as unverified in the summary and do not infer it from prose.
