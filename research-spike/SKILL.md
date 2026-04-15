---
name: research-spike
description: Submit a deep-dive research spike to Hugin. Produces a detailed, source-cited report and a popular 5–10 minute summary in Simon Willison's blog style. Reports land in ~/mimir/research/<project>/; summaries land in ~/mimir/reading/ and are served by Heimdall's /read page.
argument-hint: <topic or repo to research>
---

# /research-spike — Deep-Dive Research via Hugin

Submit a research spike to Hugin that produces **two artefacts**:

1. A **detailed report** — exhaustive, source-cited, structured for AI-agent consumption. Length is not a constraint; quality is.
2. A **popular summary** — a 5–10 minute read in Simon Willison's blog style. Substantive, not dumbed down. Served by Heimdall's `/read` page (Tailscale/LAN only; no public exposure).

Both artefacts are indexed in Munin so they're discoverable across sessions and environments.

## Usage

- `/research-spike <topic>` — build a spike from the topic, confirm before submitting
- `/research-spike` — interactive: ask what to research

## Outputs

Every spike produces matching-slug files:

| Output | Path on NAS | Purpose | Audience |
|---|---|---|---|
| Detailed report | `~/mimir/research/<project>/<YYYY-MM-DD>-<slug>.md` | Canonical, exhaustive | AI agents + deep reading |
| Popular summary | `~/mimir/reading/<YYYY-MM-DD>-<slug>.md` | 5–10 min narrative | Magnus via Heimdall `/read` (Tailscale/LAN only) |

Conventions:
- `<project>` is a kebab-case slug (e.g. `fort-gille`, `grimnir`, `drone-lab`, `mgc-ab`, `munin`). Use `scratch` if unaffiliated.
- `<YYYY-MM-DD>` is the UTC date of submission.
- `<slug>` is 2–4 kebab-case words describing the research topic.
- Detailed report and popular summary share the same `<YYYY-MM-DD>-<slug>` for trivial cross-reference.

## Sensitivity

Every spike MUST set a sensitivity level. It's metadata (tag, frontmatter) — Heimdall `/read` is Tailscale/LAN-only, so every popular summary is published there regardless of level. The `restricted` level is the only routing gate: it skips the popular summary entirely.

| Level | Rule | Examples |
|---|---|---|
| `public` | Popular summary → `~/mimir/reading/`, served via Heimdall `/read`. | Public tools, OSS systems, published market analysis, general techniques |
| `internal` | Popular summary → `~/mimir/reading/`, served via Heimdall `/read`. Tagged `internal` for future filtering. | Business strategy, MGC AB specifics, personal finance, fort-gille tactical decisions |
| `restricted` | No popular summary. Only the detailed report, stored on NAS, no sync elsewhere. | Säkerhetsskydd-adjacent, highly personal, anything not suitable for long-term retention |

## Detailed report format

YAML frontmatter (required):

```yaml
---
title: <descriptive title>
slug: <slug>
project: <project-slug>
date: YYYY-MM-DD
task_id: <YYYYMMDD-HHMMSS-slug>
sensitivity: public | internal | restricted
tags: [topic1, topic2, ...]
summary_link: <relative path to popular summary, or "none">
reading_time_min: <estimated minutes for the detailed report>
---
```

Fixed section order (AI-agent-parseable):

1. **Executive Summary** — 3–5 bullets with headline findings. Each bullet links to its home section via markdown anchor.
2. **Background** — what is being researched, why it matters, what was already known.
3. **Findings** — substantive body. H2 per major topic. Every factual claim cited inline via `[text](url)` markdown link.
4. **Comparison / Analysis** — tables + commentary. Tables beat prose for dense comparisons.
5. **Recommendations** — numbered, prioritised, each with rationale, effort (S/M/L), and risk.
6. **Uncertainty & Gaps** — what could not be verified; what follow-up would close the gap.
7. **Sources** — full bibliography with descriptive titles, URLs, one-line annotation.

Rules:
- **Every factual claim must link to a source.** No exceptions.
- **Length is not a constraint. Quality is.** Do not truncate findings for brevity.
- **Tables for structure; prose for argument.**
- **No emojis** unless the user explicitly requested them.
- **Callouts sparingly** (`> Note:`, `> Warning:`) — only for high-impact items.

## Popular summary format

Target: **1,500–2,500 words**. Reading time 5–10 minutes at ~250 wpm.

**Style reference: [Simon Willison's blog](https://simonwillison.net/).**

Elements to match:
- **First-person voice.** "I spent the afternoon reading…", "What surprised me was…"
- **Concrete, temporal hook in the opening paragraph.** Not an executive summary. Not a thesis statement. Start from something specific.
- **Flow as prose; H2 subheadings only where they genuinely help.** A short piece may only have 2–3 subheadings. Don't impose structure that isn't earned.
- **Inline links to sources, liberally.** Every name, claim, and referenced work gets a link the first time it appears.
- **Tables, code blocks, quotes** only when they earn their place — never as structure for its own sake.
- **Opinionated.** If the answer is "this is overhyped," say so. Don't hedge. Willison reads as a friend sharing what they learned, not as a consultant.
- **Short paragraphs.** 2–4 sentences is normal.
- **Honest about uncertainty and personal limits.** "I haven't actually tried X, so take this with a pinch of salt."
- **Ends with "what I'm going to do about it."** A concrete next step, an action, or a decision. Not a summary.
- **Final line: link to the detailed report** for readers who want to go deeper.

Format rules:
- **No YAML frontmatter.** Heimdall's `read-docs.js` does not strip it; frontmatter would show up in the excerpt. Metadata lives in Munin only.
- **First line: `# <Title>`** — title should be concrete, specific, Willison-esque. Good: *"What I learned about Swedish civil-defence drone funding in 2026"*. Bad: *"Drone Funding Analysis"*.

## How it works

### Step 1: Understand the research target

From the user's description, determine:

1. **What** — repo URL, tool name, technique, paper, market question
2. **Why** — what question is the user actually trying to answer
3. **Project** — which project the spike belongs to (affects path + Munin indexing)
4. **Sensitivity** — default `internal` unless clearly public or clearly restricted

### Step 2: Check existing research

Before submitting:

1. `memory_query` with relevant topic tags; look for `type:research`
2. Glob `~/mimir/research/<project>/` for prior reports
3. Check any project-local `docs/competitive-analysis.md` if one exists

If prior research exists, tell the user and ask whether to update or start fresh.

### Step 3: Build the research prompt

Use the template below. Adapt phases based on research type:

- **Tool/system comparison** → architecture analysis, comparison matrix, fit assessment
- **Technique evaluation** → PoC feasibility, effort/value matrix
- **Paper/concept** → summary, applicability, implementation sketch
- **Market/strategy** → landscape, actors, gaps, positioning

Always include:
- Source gathering phase (cite exhaustively)
- Structured comparison phase
- Recommendations phase
- Write-detailed-report phase
- Write-popular-summary phase (skip if restricted)
- Delivery + Munin indexing phase

### Step 4: Generate task ID

Format: `YYYYMMDD-HHMMSS-<slug>`. UTC time. Slug = 2–4 kebab words.

### Step 5: Confirm with user

Show:
- Task ID
- Research question (one sentence)
- Project
- Sensitivity
- Runtime + model + timeout
- Output paths (detailed + popular)

Ask: "Submit this research spike?"

### Step 6: Submit

```
memory_write(
  namespace: "tasks/<task-id>",
  key: "status",
  content: <full task prompt>,
  tags: ["pending", "runtime:claude", "type:research", "project:<project>", "sensitivity:<level>"]
)
```

### Step 7: Confirm

Tell the user:
- Task ID
- How to check status
- Where the detailed report and popular summary will land
- That the popular summary will appear on Heimdall `/read` (Tailscale/LAN) within ~5 min of completion, unless sensitivity=restricted

## Prompt template

```markdown
## Task: Research Spike — <title>

- **Runtime:** claude
- **Context:** scratch
- **Sensitivity:** <public | internal | restricted>
- **Project:** <project-slug>
- **Model:** claude-opus-4-6
- **Timeout:** <3600000 standard; 5400000 for very broad topics>
- **Submitted by:** claude-code
- **Submitted at:** <UTC ISO 8601>
- **Reply-to:** none

### Prompt

You are a research agent on the Hugin-Munin Raspberry Pi (huginmunin).
You have MCP access to Munin (`munin-memory` MCP server) and web search/fetch tools.
Your working directory is `/home/magnus/scratch`.

**YOUR MISSION: <one clear research question>.**

---

## Background

<2–3 paragraphs: what is being researched, what is already known, why this matters, what the user wants to learn>

---

## Output contract

You will produce TWO artefacts with matching slugs (skip #2 if sensitivity=restricted):

1. **Detailed report** — `/home/magnus/scratch/<slug>-detailed.md`
   → synced to NAS: `~/mimir/research/<project>/<YYYY-MM-DD>-<slug>.md`

2. **Popular summary** — `/home/magnus/scratch/<slug>-popular.md`
   → synced to NAS: `~/mimir/reading/<YYYY-MM-DD>-<slug>.md`
   (skip entirely if sensitivity=restricted)

Both artefacts must be produced in the same task run (popular may be skipped only for `restricted`).

---

## Phase 1: Gather source material

<specific steps: clone repos, fetch docs, web search, read papers, interviews if any>

For every factual claim you intend to make, record the source URL and a brief note. You will cite every claim inline via markdown link in the detailed report.

## Phase 2: Structured analysis

<dimensions to evaluate, adapted to the research type>

## Phase 3: Recommendations

Concrete, prioritised recommendations. Each recommendation:
- What to do
- Why (with supporting evidence)
- Effort (S/M/L)
- Risk

## Phase 4: Write the detailed report

Write `<slug>-detailed.md` with the required structure:

- YAML frontmatter (title, slug, project, date, task_id, sensitivity, tags, summary_link, reading_time_min)
- Executive Summary (3–5 bullets, each anchored to its home section)
- Background
- Findings (H2 per topic; every claim cited inline)
- Comparison / Analysis (tables + commentary)
- Recommendations (numbered)
- Uncertainty & Gaps
- Sources (full bibliography with annotations)

Rules:
- Every factual claim links to a source
- Length is not a constraint — quality is
- Tables for structure, prose for argument
- No emojis
- Callouts sparingly

## Phase 5: Write the popular summary

**Skip this phase entirely if sensitivity=restricted.**

Write `<slug>-popular.md` — 1,500–2,500 words, Simon Willison's blog style:

- First-person voice
- Concrete temporal hook in the opening paragraph
- Flow as prose; H2 subheadings only where genuinely helpful
- Inline links to sources, liberally
- Tables and code blocks only when they earn their place
- Opinionated, no hedging
- Short paragraphs (2–4 sentences)
- Honest about uncertainty and personal limits
- Ends with "what I'm going to do about it"
- Final line links to the detailed report at `~/mimir/research/<project>/<YYYY-MM-DD>-<slug>.md`

**Do NOT include YAML frontmatter.** First line is `# <Title>`. Title is concrete and specific, Willison-esque.

## Phase 6: Deliver and index

1. Sync the detailed report to NAS (create project dir if missing):
   ```
   ssh magnus@100.99.119.52 "mkdir -p /home/magnus/mimir-inbox/research/<project>"
   rsync /home/magnus/scratch/<slug>-detailed.md \
     magnus@100.99.119.52:/home/magnus/mimir-inbox/research/<project>/<YYYY-MM-DD>-<slug>.md
   ```

2. Sync the popular summary (skip if sensitivity=restricted):
   ```
   rsync /home/magnus/scratch/<slug>-popular.md \
     magnus@100.99.119.52:/home/magnus/mimir-inbox/reading/<YYYY-MM-DD>-<slug>.md
   ```

3. Index in Munin — three writes per spike:

   **a. `documents/<slug>`** — canonical research index:
   ```
   memory_write(
     namespace: "documents/<slug>",
     key: "index",
     content: "<2–3 sentence summary + detailed path + popular path (or 'n/a') + key recommendation>",
     tags: ["type:research", "project:<project>", "sensitivity:<level>",
            "date:<YYYY-MM-DD>", "topic:<topic1>", "topic:<topic2>"]
   )
   ```

   **b. `reading/<slug>`** (skip if restricted) — surfaces the popular summary:
   ```
   memory_write(
     namespace: "reading/<slug>",
     key: "entry",
     content: "<one-sentence hook + reading time + popular path + detailed path>",
     tags: ["type:summary", "project:<project>", "sensitivity:<level>",
            "date:<YYYY-MM-DD>", "topic:<topic1>"]
   )
   ```

   **c. `projects/<project>`** — log as a project event:
   ```
   memory_log(
     namespace: "projects/<project>",
     content: "Research spike: <title>. Key finding: <one sentence>. Detailed: <path>. Popular: <path or 'n/a'>.",
     tags: ["research", "topic:<topic1>"]
   )
   ```

4. **Follow-up actions** — if anything remains unresolved:
   ```
   memory_read("actions", "pending")   # read current list first
   memory_write("actions", "pending", <updated list>, tags: ["active", "action-items"])
   ```
   Format new items as: `## From tasks/<task-id>\n- [ ] <description>`

5. Signal completion:
   ```
   memory_write("tasks/<task-id>", "result", "DONE — detailed: <path>, popular: <path or 'n/a'>")
   ```

---

## Constraints

- **Read-only on Munin project data.** Do not modify project statuses; read for context only.
- **Be honest.** If the researched system is genuinely better at something, say so. This is for strategic decision-making, not cheerleading.
- **Project context matters.** Evaluate through the lens of the named project. If `fort-gille`: personal + household resilience. If `grimnir`: personal AI system on Pis with sovereignty as core value. If `drone-lab`: Swedish civil-defence drone capability + MGC AB revenue option. If `mgc-ab`: AI consulting business positioning.
- **No secrets.** No API keys, tokens, credentials in either artefact.
- **Source-citation is non-negotiable in the detailed report.** Every factual claim must link to a source.
- **Popular summary voice is non-negotiable.** Simon Willison's blog style. Not consultant voice, not academic voice, not press-release voice.
- **Signal completion.** Write "DONE" to `tasks/<task-id>/result` when finished.
```

## Defaults

| Setting | Default | Override when |
|---------|---------|--------------|
| Runtime | `claude` | Never — research needs tool access |
| Model | `claude-opus-4-6` | Use `claude-sonnet-4-6` for narrow/well-scoped research |
| Timeout | `3600000` (1 hour) | `5400000` for very broad topics |
| Sensitivity | `internal` | `public` for clearly public, `restricted` for säkerhetsskydd-adjacent |
| Project | — | Required; use `scratch` if unaffiliated |

## Key rules

1. **Always check for prior research** before submitting. Don't duplicate work.
2. **Two outputs per spike** unless `sensitivity=restricted` (which skips the popular summary).
3. **Detailed reports go to `mimir-inbox/research/<project>/`** with date-prefixed filenames.
4. **Popular summaries go to `mimir-inbox/reading/` (public) or `mimir-inbox/reading-internal/` (internal).** Heimdall's `/read` page serves the former — *note:* depends on `read-docs.js` being retargeted at `~/mimir/reading/`; tracked as a separate heimdall issue.
5. **Every factual claim in the detailed report must cite a source via inline markdown link.**
6. **Popular summary follows Simon Willison's blog style** — first-person, concrete hook, opinionated, ends with a concrete next step.
7. **Three Munin indexing writes per spike:** `documents/<slug>` (index), `reading/<slug>` (summary surfacing, unless restricted), `projects/<project>` (event log).
8. **Opus is the default.** Research needs strong analytical reasoning.
9. **Be specific about comparison targets.** Name projects, versions, actors.
10. **Be honest.** If the recommendation is "don't adopt," say so clearly.
