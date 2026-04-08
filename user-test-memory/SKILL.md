---
name: user-test-memory
description: Spawn 3 independent AI agents (Opus, Sonnet, Haiku) to user-test the Munin memory system. Each explores with minimal pre-knowledge and returns structured feedback on what works, what's broken, and what's missing.
argument-hint: [optional focus area, e.g. "retrieval quality" or "onboarding experience"]
---

# /user-test-memory - Multi-Model Memory User Testing

Spawn three independent subagents at different capability levels to stress-test the Munin memory MCP tools. Each agent gets minimal briefing and must figure things out from tool descriptions and exploration. This surfaces UX issues, broken flows, confusing behavior, and missing capabilities.

## Usage

- `/user-test-memory` - Full exploratory test across all tools
- `/user-test-memory retrieval` - Focus testing on search/query
- `/user-test-memory onboarding` - Focus on first-time orientation experience
- `/user-test-memory writing` - Focus on write/log/update flows

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

## Key Rules

1. **Minimal briefing** — The whole point is testing discoverability. Don't teach the agents how to use the system.
2. **Parallel launch** — All three agents MUST be launched in a single message for parallel execution.
3. **Test namespaces** — All writes go to `testing/*` to avoid polluting production data.
4. **Read access is fine** — Agents can and should read real data to evaluate the system.
5. **No coaching** — If an agent gets stuck, that's a finding, not a problem to solve.
6. **Specific feedback** — Vague feedback ("it was fine") is useless. The report format enforces specificity.
7. **Cross-model comparison** — The synthesis matters more than individual reports. Consensus findings are high-confidence signals.
