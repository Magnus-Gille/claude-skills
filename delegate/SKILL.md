---
name: delegate
description: Delegate a bounded one-shot task to Hugin's orchestrator-v1 broker — cheaper / smaller runtimes via the `hugin-mcp` MCP. Use for summarize / extract / classify / draft / rewrite / short reason work where you'd rather not spend Claude tokens. Submits, polls to completion, surfaces the result, and prompts the user to rate it.
---

# /delegate — Delegate to a Cheaper Runtime

Hand a bounded task off to Hugin's broker (`/v1/delegate/*`) via the `hugin-mcp` MCP server. The broker dispatches to a cheaper one-shot runtime (Ollama on the Pi, or OpenRouter) and returns a single response. This is **not** the same as `/submit-task` — that runs a full agent (Claude Code / Codex) on the Pi for autonomous, multi-step work.

## When to use which

| Use `/delegate` when… | Use `/submit-task` when… |
|---|---|
| One-shot transformation: summarize, extract, classify, draft, rewrite | Multi-step autonomous work — code changes, commits, multi-tool reasoning |
| You want to save Claude tokens on routine work | The task needs tool use, file I/O, MCP access, git |
| Bounded prompt → bounded response | Open-ended "go figure this out" |
| Fast turnaround (seconds–minute) | Long-running (minutes–hours) |

If the task needs a worktree / git / file edits, use `/submit-task` instead — `pi-large-coder` exists in the alias map but isn't wired in v1.

## Model check

If the current model is Opus, ask the user to run `/model sonnet` first. This skill is prompt-shaping plus MCP calls — Sonnet is enough.

## Prerequisites

`hugin-mcp` must be registered as an MCP and connected. Check with `claude mcp list`. If absent, the user needs to register it (see Hugin's CLAUDE.md for the command and the broker token).

If the MCP is registered but the broker is unreachable, `hugin_submit` will return a `broker_network_error` — surface that clearly and stop.

## Usage

- `/delegate` — interactive: ask what to delegate
- `/delegate <description>` — build a task from the description, confirm, submit

## Flow

### Step 1: Understand the task

If the user gave a description, paraphrase it back in one line and identify:
- **What's the input?** (text, list, document — paste it inline if small, otherwise reference)
- **What's the desired output?** (a summary, a JSON list, a draft email, a rewritten paragraph)
- **What's the format?** (paragraph, bullets, JSON, etc.)

If anything is unclear, ask one focused question.

### Step 2: Pick `task_type`

Map the user's intent to one of these (the broker uses this for accounting + future routing, not execution):

| `task_type` | Examples |
|---|---|
| `summarize` | Condense a meeting note, paper, thread |
| `extract` | Pull entities / action items / structured fields out of text |
| `classify` | Tag, categorize, assign labels |
| `draft` | Compose a new email / message / paragraph from scratch |
| `reason` | Short Q&A, simple inference, "is this X or Y and why" |
| `rewrite` | Reword, simplify, change tone, translate |
| `code-edit` | (reserved — use `/submit-task` for now) |
| `other` | None of the above |

### Step 3: Pick `alias_requested`

| Alias | Use when | Roughly |
|---|---|---|
| `tiny` | Trivial bounded transforms — single-sentence summary, simple classify, format normalization | Small Ollama on Pi |
| `medium` | Default. Most summarize/extract/draft/rewrite work | Mid-size local or cheap cloud |
| `large-reasoning` | Needs real reasoning — multi-step inference, nuanced rewrite, careful analysis | Cloud reasoning model |
| `pi-large-coder` | Code editing in a worktree — **not in v1**, use `/submit-task` |

When unsure, start with `medium`. If the result is poor, tell the user "this might want `large-reasoning` — want me to retry?"

You can call `hugin_models` first if you want the live alias map and want to surface the actual underlying model, but don't do this on every invocation — it's a network round-trip.

### Step 4: Pick `sensitivity`

- `public` — fine to send to any cloud runtime (e.g., paraphrasing public docs)
- `internal` — default. Not public, but no special privacy concern. Stays within trusted runtimes.

If the content is private (personal correspondence, financial details, secrets), **do not delegate** — those belong on a local-only runtime, and the v1 broker doesn't expose `private`. Use `/submit-task` with `Runtime: ollama` and an explicit `Sensitivity: private` instead.

### Step 5: Build the prompt

Write a clean, self-contained prompt. The runtime sees only this string — no MCP, no tools, no follow-up. Include:

1. **Role / framing** — one short sentence ("You are a careful editor.")
2. **Input** — the actual content, clearly delimited (e.g., between `<input>` tags)
3. **Instruction** — what to produce, in what format
4. **Constraints** — length cap, tone, what to avoid

For structured output (JSON, bulleted list with required fields), spell the schema out and ask for *only* that — small models drift if you let them.

Keep prompts short. If you're tempted to write a multi-phase plan, you probably want `/submit-task`, not this.

### Step 6: Pick `timeout_ms`

| Task | Timeout |
|---|---|
| Trivial transform (`tiny`, short input) | 60000 (1 min) |
| Default (`medium`, normal input) | 300000 (5 min — broker default) |
| Long input or `large-reasoning` | 600000 (10 min) |

Omit for the broker default (5 min).

### Step 7: Confirm with the user

Show:
- **Alias:** `medium`
- **Task type:** `summarize`
- **Sensitivity:** `internal`
- **Timeout:** 5 min
- **Prompt:** (full text — collapse if long)

Ask: "Delegate this to Hugin?"

### Step 8: Submit

Call `hugin_submit` with the validated input. The MCP fills in envelope fields. Capture:
- `task_id`
- `idempotency_key` (echoed back — keep it for retries)
- `received_at`

If `reused_idempotency: true`, surface that the broker treated this as a replay (probably benign).

On error:
- `broker_network_error` → broker is unreachable. Tell the user, stop.
- `broker_http_error` with 401/403 → token mismatch. Tell the user to check `HUGIN_BROKER_TOKEN`.
- `broker_http_error` with 4xx + body → schema or policy rejection. Show the body.
- `input_validation` → my fault — re-shape the input and retry.

### Step 9: Poll

Call `hugin_await` with the `task_id`. Poll cadence: every 3–5 seconds for the first 30 seconds, then every 10 seconds. Stop polling when:
- `status: "completed"` — read the result
- `status: "failed"` — read the error
- `orphan_suspected: true` — lease expired without completion. Tell the user, offer to wait longer or give up.
- Wall-clock exceeds the requested `timeout_ms` + 30s buffer

Show light progress feedback ("Still running…") roughly every 30s while polling, not every poll.

### Step 10: Surface the result

When `completed`:
- Show the result body to the user, formatted appropriately for the task type
- Note effective runtime + model from the result envelope (the broker echoes the resolved alias)
- Prompt the user to rate

When `failed`:
- Show the error kind + message
- Suggest a remedy based on `kind`:
  - `alias_unavailable` → retry with a different alias
  - `policy_rejected` → sensitivity / scanner rejection — explain
  - `executor_failed` / `timeout` → retry, or escalate to `/submit-task`
  - `scanner_blocked` → the prompt or output tripped a security scanner

### Step 11: Rate (optional but encouraged)

Ask the user one question: "How did that go? **pass** / **partial** / **redo** / **wrong**"

| Rating | Meaning |
|---|---|
| `pass` | Result was good, used as-is or with trivial edits |
| `partial` | Useful but needed real edits |
| `redo` | Wrong shape — same alias, retry might work |
| `wrong` | Wrong runtime choice — should have gone to a bigger model or to `/submit-task` |

If they rate, also ask for `verification_outcome`:
- `accepted_unchanged` — pasted in as-is
- `minor_edit` — a few tweaks
- `major_rewrite` — kept the structure but rewrote
- `discarded` — didn't use it
- `escalated_to_claude` — re-did the work in Claude

Then call `hugin_rate` with `task_id`, `rating`, `rating_reason` (one short sentence), `verification_outcome`. This feeds the future routing model — skipping it isn't fatal, but rate when you can.

If the user doesn't want to rate, skip and move on.

## Key Rules

1. **Self-contained prompt** — the runtime has no tools, no MCP, no memory.
2. **One-shot only** — no multi-phase, no "after that, do X". For that, use `/submit-task`.
3. **No private content** — v1 broker doesn't accept `sensitivity: private`. Local-only work goes to `/submit-task` with `Runtime: ollama`.
4. **Don't pre-fetch `hugin_models`** every time — only when the user asks "what's behind `medium`?" or you need to disambiguate.
5. **Surface errors honestly** — don't paper over `broker_network_error` with a retry loop. Tell the user the broker is unreachable.
6. **Idempotency on retry** — if the user wants to re-submit the *exact same* task after a transient error, pass back the `idempotency_key` from the failed response so the broker can dedupe.
7. **Rate when you can** — the rating feedback is what makes routing better over time. It's the whole point of the broker existing.
