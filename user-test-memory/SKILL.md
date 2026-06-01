---
name: user-test-memory
description: Spawn independent AI agents across one or more ecosystems (Claude, Codex, Antigravity) to user-test the Munin memory system. Each explores with minimal pre-knowledge and returns structured feedback on what works, what's broken, and what's missing.
argument-hint: [optional focus area, e.g. "retrieval quality" or "onboarding experience"]
---

# /user-test-memory - Multi-Model Memory User Testing

Spawn independent subagents at different capability levels to stress-test the Munin memory MCP tools. Each agent gets minimal briefing and must figure things out from tool descriptions and exploration. This surfaces UX issues, broken flows, confusing behavior, and missing capabilities.

**Default mode:** 3 Claude agents (Opus/Sonnet/Haiku). Extended mode adds Codex (via `codex exec`) and Antigravity (via `agy --print`) — see [Cross-Ecosystem Extension](#cross-ecosystem-extension) below.

## Usage

- `/user-test-memory` - Full exploratory test across all tools (3 Claude agents)
- `/user-test-memory retrieval` - Focus testing on search/query
- `/user-test-memory onboarding` - Focus on first-time orientation experience
- `/user-test-memory writing` - Focus on write/log/update flows
- `/user-test-memory full` - 9-runner cross-ecosystem test (Claude + Codex + Antigravity)

## How It Works

### Step 1: Generate Test Session ID

```
test-<YYYYMMDD-HHMMSS>
```

Each agent gets a unique test namespace: `testing/<model>-<session-id>` (e.g., `testing/opus-test-20260408-120000`).

### Step 2: Build the Agent Briefing

Each agent gets the SAME briefing — a deliberately minimal context that simulates a new user. Do NOT include CLAUDE.md conventions, namespace patterns, tag vocabulary, or usage guides. The agents should discover these from the tools themselves.

**Briefing template** (fill in `{test_namespace}`, `{session_id}`, and `{focus_area}` if provided):

```
You are a QA tester evaluating a memory system called Munin. You have access to
MCP tools prefixed with "mcp__munin-memory__". Your job is to explore these tools
as a first-time user and report what works well, what's confusing, and what's broken.

Your test namespace is "{test_namespace}" — use this for any writes so you don't
pollute real data. You may READ from any namespace to understand the system.

{focus_area_instruction}

## Your Mission

Work through these test phases. Spend roughly equal effort on each.

### Phase 1: Orient (understand the system)
- Call memory_orient. What do you learn? Is it helpful? Overwhelming? Missing things?
- Try memory_list to browse. Can you understand the namespace structure?
- Pick 2-3 interesting namespaces and read their contents.

### Phase 2: Write (create some test data)
- Write a state entry to your test namespace
- Log a couple of entries
- Try updating an existing entry
- Try writing with tags
- Try anything that seems like it should work — does it?

### Phase 3: Retrieve (find things)
- Use memory_query to search for something you just wrote
- Search for something that exists in the system already
- Try different search modes if available
- Try filtering by tags, time ranges, namespaces

### Phase 4: Advanced tools (if they exist)
- Explore any tools you haven't tried yet
- Try edge cases: empty queries, very long content, special characters
- Look for tools that seem powerful but unclear how to use

### Phase 5: Stress test
- Try something you think SHOULD work but aren't sure about
- Try to break something (within your test namespace)
- Look for inconsistencies between tool descriptions and actual behavior

## Report Format

End your exploration with a structured report. Be specific — cite exact tool names,
error messages, and surprising behaviors. Rate each category:
  S = Superb (delightful, better than expected)
  A = Good (works well, minor polish needed)
  B = Acceptable (works but has rough edges)
  C = Poor (confusing, hard to use, or unreliable)
  F = Broken (doesn't work, produces wrong results, or crashes)

```markdown
# Munin Memory User Test Report — {model_name}

## Scores
- Onboarding/Orientation: [S/A/B/C/F]
- Writing & Updating: [S/A/B/C/F]
- Reading & Retrieval: [S/A/B/C/F]
- Tool Discoverability: [S/A/B/C/F]
- Error Messages & Feedback: [S/A/B/C/F]
- Overall Coherence: [S/A/B/C/F]

## What Works Great
<specific things that were impressive or well-designed>

## What's Confusing
<things that weren't intuitive, unclear tool descriptions, surprising behavior>

## What's Broken
<bugs, crashes, wrong results, inconsistencies>

## What's Missing
<capabilities you expected but didn't find, workflows that felt incomplete>

## Verbatim Tool Friction Log
<chronological log of moments where you got stuck, had to retry, or were surprised>

## Top 3 Recommendations
1. <highest impact improvement>
2. <second>
3. <third>
```
```

### Step 3: Determine Focus Area Instruction

If a focus area was provided, add this to the briefing:

| Focus | Instruction |
|-------|-------------|
| `retrieval` | "Spend 60% of your effort on Phase 3 (retrieval). Test query reformulations, semantic vs lexical search, temporal filters, tag filters, and result quality." |
| `onboarding` | "Spend 60% of your effort on Phase 1 (orient). Evaluate whether a brand-new agent can understand the system from orient alone, without any documentation." |
| `writing` | "Spend 60% of your effort on Phase 2 (writing). Test edge cases in writes, updates, patches, tag handling, validation errors, and content limits." |
| (none) | "Distribute your effort roughly equally across all phases." |

### Step 4: Launch All Three Agents in Parallel

Spawn three Agent tool calls in a SINGLE message (parallel execution):

1. **Opus** (`model: "opus"`) — the deep thinker. Will find subtle design issues.
2. **Sonnet** (`model: "sonnet"`) — the practical middle. Represents the typical AI user.
3. **Haiku** (`model: "haiku"`) — the constrained model. If Haiku can't figure it out, the UX needs work.

Each agent gets the same briefing with its own `{test_namespace}`.

**Claude-specific note:** MCP tools are deferred — prepend the briefing with:
> "First call ToolSearch with query `select:mcp__munin-memory__memory_orient,...` (list the key tools) to load their schemas, then proceed."

Agent description format: `"Memory user test ({model})"`.

### Step 5: Collect and Synthesize Reports

Once all three agents return:

1. **Extract each report** from the agent results
2. **Build a synthesis document** that cross-references findings:

```markdown
# Munin Memory User Testing — {date}

## Test Configuration
- Session: {session_id}
- Focus: {focus_area or "full exploratory"}
- Models: Opus, Sonnet, Haiku

## Score Matrix

| Category | Opus | Sonnet | Haiku | Consensus |
|----------|------|--------|-------|-----------|
| Onboarding | | | | |
| Writing | | | | |
| Retrieval | | | | |
| Discoverability | | | | |
| Error Messages | | | | |
| Overall | | | | |

## Consensus Findings (2+ models agree)
<findings reported by at least 2 of the 3 models>

## Unique Findings
### Opus only
<issues only Opus caught — likely subtle or architectural>

### Sonnet only
<issues only Sonnet caught>

### Haiku only
<issues only Haiku caught — likely UX/clarity issues>

## Bugs Found
<concrete bugs with reproduction steps>

## Prioritized Recommendations
1. <highest impact, based on consensus + severity>
2. ...

## Raw Reports
<include each model's full report below for reference>
```

3. **Save the synthesis** to `docs/user-testing-{session_id}.md` in the current repo (if in munin-memory) or print it to the conversation.

### Step 6: Offer Cleanup

After presenting results, offer to clean up test namespaces:
```
memory_delete("testing/opus-{session_id}")
memory_delete("testing/sonnet-{session_id}")
memory_delete("testing/haiku-{session_id}")
```

---

## Cross-Ecosystem Extension

For a richer signal, run the test across Claude + Codex (OpenAI) + Antigravity (Gemini) in a Workflow. This surfaces ecosystem-specific UX issues that a single-family run can't catch.

### Runner families

| Family | How | Constraint |
|--------|-----|------------|
| **Claude** opus/sonnet/haiku | Native subagents (Workflow `agent()`) | Full read+write |
| **Codex** `gpt-5.5` ×3 | Wrapper agent shells out: `codex exec -m gpt-5.5 < /tmp/brief-<id>.txt` | Full read+write via munin bridge |
| **Antigravity** `agy` ×3 | Wrapper agent shells out: `agy --print "$(cat /tmp/brief-<id>.txt)"` | **Read-only** — writes hit a permission prompt in headless mode; skip Phase 2 for agy runners |

**Model note:** Only `gpt-5.5` is available under ChatGPT-account Codex auth (other slugs return 400). Probe first with `codex exec -m <slug> "Reply with only: PROBE_OK"` and check that the output is NOT echoed from the prompt.

### Namespace rules (critical)

**Namespace grammar:** `[a-zA-Z0-9][a-zA-Z0-9/_-]*` — **dots and spaces are invalid.** Runner IDs used in sandbox namespace names MUST be sanitised. Use `codex-a`, `codex-b`, `codex-c` — NOT `codex-gpt5.5-a` (the dot breaks the namespace and blocks the entire write phase with no warning).

### Briefing variants

- **Claude:** standard briefing (MCP tools natively available; prepend ToolSearch hint).
- **Codex:** same briefing written to `/tmp/brief-<id>.txt`, piped to `codex exec`. Codex resolves as `principal: owner` via the munin bridge in `~/.codex/config.toml`.
- **Antigravity (read-only):** modified briefing that instructs the runner to skip write tools (`memory_write`, `memory_log`, `memory_update_status`, `memory_delete`) and mark Writing grade as "N/A — could not test headlessly". `agy` resolves munin tools without a `mcp__`-prefix (uses generic `call_mcp_tool`).

### De-risk before fan-out

Before launching 9 parallel runners, verify each family can actually call munin:
1. Claude: no de-risk needed (native).
2. Codex: `codex exec -m gpt-5.5 "Call memory_status with no args and paste the result."` — confirm it returns JSON, not a sandbox/network error.
3. agy: `agy --print "List the MCP tools available to you."` — confirm munin tools appear. Then `agy --print "Call memory_status (no args) and paste the raw result."` — confirm a live response.

### Synthesis weighting

When synthesising across families, weight **cross-family consensus** higher than within-family agreement. Two different ecosystems independently reporting the same issue is near-certain signal. One family reporting something the others didn't may still be worth filing, but note the limited confidence.

### Cleanup

After the run, delete all `testing/*` sandbox namespaces. Codex and agy runners connect as `principal: owner`, so their writes land in prod munin — clean up even if you think they failed.

---

## Key Rules

1. **Minimal briefing** — The whole point is testing discoverability. Don't teach the agents how to use the system.
2. **Parallel launch** — All three agents MUST be launched in a single message for parallel execution.
3. **Test namespaces** — All writes go to `testing/*` to avoid polluting production data. Sanitise runner IDs — no dots or spaces in namespace names.
4. **Read access is fine** — Agents can and should read real data to evaluate the system.
5. **No coaching** — If an agent gets stuck, that's a finding, not a problem to solve.
6. **Specific feedback** — Vague feedback ("it was fine") is useless. The report format enforces specificity.
7. **Cross-model comparison** — The synthesis matters more than individual reports. Consensus findings are high-confidence signals.
8. **De-risk external runners first** — Verify Codex and agy can reach and call munin with a single-tool probe before running the full fan-out.
