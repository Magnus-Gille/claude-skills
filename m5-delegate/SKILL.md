---
name: m5-delegate
description: Delegate a self-contained task to Magnus's M5 when local inference is requested or the project's delegation policy applies.
---

# M5 Local Delegation

Use this skill when local inference is requested or an applicable delegation policy calls for a self-contained leaf. The goal is to save frontier tokens and produce useful real delegation data for the home-server project.

## When To Use It

Once activated, suitable leaves include:
- Summarize, classify, extract, rewrite, draft.
- Short, bounded reasoning where an approximate answer is acceptable.
- Single-shot code generation with a clear spec.
- Batch harnesses that can run on the M5 box itself.

Avoid it:
- Work needing the full current repo or conversation context.
- Security-critical reasoning or tasks where a wrong answer is costly to detect.
- Multi-step code edits unless a caged code-loop style tool is explicitly available.
- Private content unless it will stay on a local-only path.

## Model/Runtime Guidance

- Prefer a fast non-thinking model such as `mellum` for short classify/extract/summarize/simple-codegen.
- Use `qwen3-coder-next-80b` for harder coding or agentic-coding leaves.
- Use `gemma4` for general or multimodal tasks when relevant.
- Discover available models and current tool schemas before choosing; the names above are examples, not an availability guarantee. Size output budgets to the task and detect truncated or empty results.
- Batch independent same-model calls when supported to avoid unnecessary model swaps; measure runtime rather than assuming fixed latency.

## Access Paths

Prefer purpose-built MCP tools if they are available in the current agent session, such as `list_models`, `ask`, or `code_loop_*`.

Always pass the cloud delegator model when you know it:
- MCP `ask`: include `delegator_model_id`, for example `"delegator_model_id": "openai/gpt-5.5"`.
- Direct `/delegate`: include `delegatorModelId`, for example `"delegatorModelId": "openai/gpt-5.5"`.
- Homeserver CLI: pass `--delegator <cloud-model-id>`.

Use the actual frontier/conductor model for the current task, not a generic default. This is what lets the M5 ledger measure actual savings rather than only premium-baseline savings. If the cloud delegator is unknown, omit the field instead of guessing.

If writing a harness that talks to the gateway directly:
- Heavy/batch harnesses should run on the M5 box and call llama-swap on loopback: `http://127.0.0.1:8091/v1`. This needs no bearer token.
- For an authenticated laptop call, load the canonical bases with `eval "$(m5-auth --env --tailnet)"` (or omit `--tailnet` when the public gateway is required).
- Call gateway-root routes as `"$M5_GATEWAY_URL/delegate"` or `"$M5_GATEWAY_URL/ledger"`. Call the OpenAI-compatible route as `"$M5_OPENAI_BASE_URL/chat/completions"`.
- Never derive the gateway root by stripping `/v1` from `M5_BASE_URL`. `M5_BASE_URL` remains a compatibility alias for `M5_OPENAI_BASE_URL`; it is not valid for `/delegate` or `/ledger`.
- Get the owner bearer token only through `m5-auth` and macOS Keychain. Never scrape MCP config and never write tokens to tracked or scratch files.

## One-Shot Prompt Shape

The runtime sees only the prompt string. Make it self-contained:

1. One sentence of role/framing.
2. Clearly delimited input.
3. Exact requested output.
4. Constraints, schema, length cap, and things to avoid.

For JSON or structured output, specify the schema and ask for only that output.

## Feedback Loop

When a delegated answer matters, capture whether it was useful:
- `pass`: used as-is or with trivial edits.
- `partial`: useful but needed edits.
- `redo`: wrong shape, retry might work.
- `wrong`: wrong runtime choice; escalate.

This feedback is part of the routing-evidence loop that the project exists to improve.
