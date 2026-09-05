---
name: debate-claude
description: Run a two-round adversarial review from Codex with Claude as the independent reviewer for a consequential decision or substantive draft when cross-model critique is warranted.
---

# Debate with Claude

This is a Codex-conductor workflow: Codex writes the draft and self-review, invokes Claude as the independent reviewer, and writes the response, summary, and index. Do not have Claude invoke this skill or present a Claude-run self-review as independent cross-model review. Other harnesses may read these references for context, but should route execution back to the Codex conductor.

Use this skill when a consequential architecture, protocol, security assessment, research claim, product priority, or similarly substantive decision benefits from an independent adversarial review. Do not invoke it for typos, formatting, routine implementation details, or mechanical refactors.

Codex owns the artifact, context, model choice, and final decision. This skill does not authorize publication, deployment, credential access, or external messages.

Read only the references needed for the current stage:

- [Protocol](references/protocol.md) — the two-round lifecycle, frozen inputs, draft, self-review, response, and rebuttal.
- [Reviewer safety](references/reviewer.md) — the isolated CLI invocation, model selection, prompt envelope, and output metadata.
- [Type lenses](references/lenses.md) — universal and topic-specific self-review and critique questions.
- [Artifacts and records](references/artifacts.md) — scratch/trackable files, critique-log schema, sanitization, summary, index, and completeness checks.

## Non-negotiable boundaries

- Freeze a scoped, sanitized input package before each round. Feed that package through stdin; do not give the reviewer live repository, Munin, filesystem, browser, hook, plugin, or MCP access by default.
- If extra project context is warranted, the conductor selects, sanitizes, and freezes it explicitly in the round package. Round 2 gets a refreshed frozen package that includes the conductor's response and any explicitly selected new context.
- Use the exact model the user specifies. Do not add an automatic fallback or substitute another model. If no model is specified, choose a suitable configured model and record both the requested and actual model from invocation metadata.
- Verify current CLI flags with `claude --help` before changing the invocation. The safe baseline is print mode, plan permissions, no session persistence, safe mode, restricted mode, an empty tool list, and an empty strict MCP configuration. Use only flags confirmed by local help.
- Record the actual model from structured CLI metadata when available; never treat a model name written in the reviewer's prose as verification.
- Capture stdout yourself and write the debate artifacts. Do not ask Claude to write files or invoke tools.

For the detailed lifecycle and records, follow the linked references. Stop after two rounds unless Round 2 surfaces a genuinely new issue that merits another bounded round.

## Choosing a debate

Before starting, check the debate index for a prior review of the same decision. A new debate is appropriate when the decision is hard to reverse, the evidence is contested, the blast radius is material, or an independent review is required by project policy. If the outcome is already incorporated into a durable ADR or plan and no future search value remains, the project may retain only that artifact.
