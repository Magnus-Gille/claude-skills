---
name: research-spike
description: Submit a deep-dive research spike to Hugin. Compares tools/systems/techniques against the Grimnir ecosystem, produces a structured report, and lands it in ~/mimir/research/. Use when you want to investigate a tool, library, technique, or competitor in depth.
argument-hint: <topic or repo to research>
---

# /research-spike - Deep-Dive Research via Hugin

Submit a research spike task to Hugin that produces a structured report comparing a tool, system, technique, or idea against the Grimnir ecosystem.

## Usage

- `/research-spike <topic>` - Build a research spike from the topic, confirm before submitting
- `/research-spike` - Interactive: ask what to research

## Report Destination

All research reports land in the same place:

| Location | Path |
|----------|------|
| **Pi (scratch)** | `/home/magnus/scratch/<slug>.md` |
| **NAS inbox** | `magnus@100.99.119.52:/home/magnus/mimir-inbox/research/<slug>.md` |
| **Laptop (after sync)** | `~/mimir/research/<slug>.md` |

The slug is derived from the task ID slug (e.g., `mempalace-deepdive.md`).

## How It Works

### Step 1: Understand the Research Target

From the user's description, determine:

1. **What** is being researched (repo URL, tool name, technique, paper)
2. **Why** — what question is the user trying to answer? Common patterns:
   - "Could we use this?" → fit assessment
   - "Compare with X" → competitive analysis
   - "Is this approach better?" → technique evaluation
   - "Should we adopt this?" → strategic recommendation
3. **Grimnir context** — which parts of the ecosystem are relevant? Read Munin project statuses as needed.

### Step 2: Check Existing Research

Before submitting, check if this topic was already researched:

1. Check `~/mimir/research/` for existing reports on the topic
2. Check Munin: `memory_query` with relevant topic tags
3. Check `docs/competitive-analysis.md` in the relevant repo if one exists

If prior research exists, tell the user and ask whether to update or start fresh.

### Step 3: Build the Research Prompt

Use the template below. Adapt the phases based on what's being researched:

- **Tool/system comparison** → include architecture analysis, comparison matrix, Grimnir fit assessment
- **Technique evaluation** → include proof-of-concept feasibility, effort/value matrix
- **Paper/concept** → include summary, applicability analysis, implementation sketch
- **Benchmark/eval** → include methodology review, applicability to our systems, run plan

Always include:
- Phase for cloning/reading the source material
- Phase for structured comparison against relevant Grimnir components
- Phase for concrete, prioritized recommendations
- Completion section with report delivery and Munin indexing

### Step 4: Generate Task ID

Format: `YYYYMMDD-HHMMSS-<slug>`

Generate the timestamp from current UTC time. The slug should be 2-4 words in kebab-case describing the research topic (e.g., `mempalace-deepdive`, `graphiti-temporal-kg`, `longmemeval-benchmark`).

### Step 5: Confirm with User

Show:
- Task ID
- Research question (one sentence)
- Key comparison targets (which Grimnir components)
- Runtime + model + timeout
- Report destination

Ask: "Submit this research spike?"

### Step 6: Submit

Write to Munin using the submit-task protocol:
```
memory_write(
  namespace: "tasks/<task-id>",
  key: "status",
  content: <full task prompt>,
  tags: ["pending", "runtime:claude", "type:research"]
)
```

### Step 7: Confirm

Tell the user:
- Task ID
- How to check status
- Where the report will land after sync

## Prompt Template

```markdown
## Task: Research Spike — <title>

- **Runtime:** claude
- **Context:** scratch
- **Model:** claude-opus-4-6
- **Timeout:** <typically 3600000 for deep research>
- **Submitted by:** claude-code
- **Submitted at:** <UTC ISO 8601>
- **Reply-to:** none

### Prompt

You are a research agent on the Hugin-Munin Raspberry Pi (huginmunin).
You have MCP access to Munin (`munin-memory` MCP server).
Your working directory is `/home/magnus/scratch` — a general-purpose workspace for non-code tasks.

**YOUR MISSION: <one clear research question>.**

---

## Background

<2-3 paragraphs of context: what is being researched, what we already know, why this matters, what the user wants to learn>

## Phase 1: Gather Source Material

<Clone repo / fetch paper / read docs — whatever is needed to understand the research target>

1. <specific steps>
2. Document the architecture/approach in detail, covering:
   - <list of specific aspects to analyze>

## Phase 2: Structured Comparison

Compare against the relevant Grimnir component(s) on these dimensions:

<Adapt dimensions to the research topic. Common ones:>

1. **Architecture** — how is it built vs how we build it
2. **Capabilities** — what can it do that we can't, and vice versa
3. **Philosophy/approach** — fundamental design differences
4. **Deployment** — hardware requirements, external dependencies, sovereignty
5. **Community/maturity** — stars, contributors, maintenance, production use
6. **Integration** — MCP support, API surface, extensibility

For each dimension, describe both systems and assess which approach is stronger and why.

## Phase 3: Fit Assessment

Read Munin context for ecosystem understanding:
- `memory_read("projects/grimnir", "status")` — current Grimnir state
- `memory_read("projects/<relevant-project>", "status")` — relevant project state

Then evaluate:

### Can we use it alongside our current system?
- Integration architecture
- What breaks / what's redundant

### Could it replace our current system?
- What capabilities would be lost
- Migration cost

### What can we mine/extract for our own use?
- Specific techniques worth adopting
- For each: effort (S/M/L), value (high/medium/low), risk

**Deliver a clear recommendation** with justification.

## Phase 4: <Topic-Specific Phase>

<Add phases specific to the research topic, e.g.:>
- Benchmark evaluation (can we run it against our system?)
- Security review (what are the risks?)
- Performance analysis (how does it scale?)

## Phase 5: Write Report

Produce a structured report at `/home/magnus/scratch/<slug>.md`.

Structure:
1. **Executive Summary** — one paragraph: verdict + key insight
2. **Source Analysis** — Phase 1 findings
3. **Comparison Matrix** — Phase 2, as a table + commentary
4. **Fit Assessment** — Phase 3, with clear recommendation
5. **<Topic-specific section>** — Phase 4
6. **Actionable Recommendations** — prioritized list of what to do next

---

## Completion

1. Push the report to NAS inbox:
   `rsync /home/magnus/scratch/<slug>.md magnus@100.99.119.52:/home/magnus/mimir-inbox/research/<slug>.md`

2. Index in Munin:
   memory_write("documents/<slug>", "index", <2-3 sentence summary + file reference + key recommendation>, tags: ["topic:<relevant>", "type:research", "source:internal"])

3. Log the research:
   memory_log("projects/<relevant-project>", "<topic> research spike completed. <key finding>.", tags: ["research", "topic:<relevant>"])

4. **Follow-up actions:** If anything could not be completed, append to the shared action list:
   memory_read("actions", "pending") — read current list first
   memory_write("actions", "pending", <updated list with new items>, tags: ["active", "action-items"])
   Format new items as: `## From tasks/<task-id>\n- [ ] <description>`

5. Signal task completion:
   memory_write("tasks/<task-id>", "result", "DONE — <summary>")

---

## Constraints

- **Read-only on Munin project data** — do not modify any project statuses, only read for context.
- **Be honest** — if the researched system is genuinely better at something, say so. This is for strategic decision-making, not cheerleading.
- **Grimnir context matters** — evaluate everything through the lens of a personal AI system running on Raspberry Pis with sovereignty as a core value.
- **No secrets** — don't include any API keys, tokens, or credentials.
- **Signal completion:** Write "DONE" to `tasks/<task-id>/result` when finished.
- **Follow-up actions:** If anything remains unresolved, append to `actions/pending` in Munin.
```

## Defaults

| Setting | Default | Override when |
|---------|---------|--------------|
| Runtime | `claude` | Never — research needs tool access |
| Model | `claude-opus-4-6` | Use `claude-sonnet-4-6` for narrow/well-scoped research |
| Timeout | `3600000` (1 hour) | Increase for very broad topics |
| Report path | `research/<slug>.md` | Only if user specifies different location |

## Key Rules

1. **Always check for prior research** before submitting — don't duplicate work.
2. **Reports always go to `mimir-inbox/research/`** on the NAS — this is the canonical location. No exceptions.
3. **Always index in Munin** (`documents/<slug>`) so future sessions can find the research by topic.
4. **Opus for research** — complex analytical reasoning benefits from the strongest model.
5. **Be specific about what to compare against** — don't just say "compare with Grimnir." Name the specific projects/components.
6. **Include actionable recommendations** — research without a "what to do next" list is incomplete.
7. **The recommendation must be honest** — if the answer is "don't adopt this," say so clearly.
