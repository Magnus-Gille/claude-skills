---
name: friction-triage
description: Sweep the Munin signals/friction corpus (report_friction self-reports), group recurring failures, and file consolidated GitHub issues routed to their owning repos + the Grimnir Roadmap board. Use when the user wants to triage accumulated friction, turn friction signals into tickets, or asks "what friction have we collected / let's file tickets for it".
---

# /friction-triage — Turn friction signals into routed, boarded GitHub issues

Codifies the manual sweep: read `signals/friction` → group recurrences → classify actionable-vs-upstream → write issue bodies → file in the **owning** repo → add to the Grimnir Roadmap board → log the sweep to Munin.

This is the workflow layer. The data layer lives in hugin (`src/friction-mcp.ts` collector, `scripts/friction-report.mjs` aggregator). Read friction via the **munin-memory MCP** in-session (keyless); only shell out to the hugin script when you want raw aggregate counts.

## Model

Triage is judgment-heavy (grouping recurrences, actionable-vs-upstream calls, writing issue bodies). Prefer **Opus**. Do not downshift to a small model for the grouping/classification step.

## Step 1 — Read the corpus

1. `memory_list` namespace `signals/friction` to enumerate events (previews + tags).
2. Determine the **sweep window**: read `meta/friction-triage` (`status` key) for the last sweep date. Only triage events **after** that date — older ones were already filed. If no prior sweep, take everything.
3. `memory_read_batch` the full content of the in-window, **open** events (need the `summary`/`detail`/`tool_name` fields, not just tags).

## Step 2 — Filter out the non-actionable

Skip an event if any of:
- Tag `status:completed`, `fixed-by:*`, or the content has a `**Resolution:**` note → already handled.
- Key starts with `smoke-test` / `tailscale-smoke` → test artifacts, not real friction.
- Already carries an `issue:*` tag from a prior sweep (see Step 8) → already filed.

## Step 3 — Group recurrences

Cluster the surviving events by **tool / subsystem** (`tool_name` + `user_tags`). Multiple events with the same root cause become **one** consolidated issue (e.g. 6 `tool:codex` failures → one "Codex review reliability" issue listing each failure mode). Note distinct failure modes within a cluster as sub-points.

## Step 4 — Classify: actionable vs upstream

For each cluster decide if it's **Magnus-fixable**:
- **File it** if the fix lives in a repo Magnus owns.
- **Do NOT file — flag only** if it's a Claude Code **harness** bug (e.g. `StructuredOutput` param-drop, core tool transport), an external **MCP/provider** bug (e.g. playwright MCP internals), or already covered by a CLAUDE.md rule (e.g. concurrent git-tree → worktree rule). List these in the summary as "not filed — upstream/covered" with a one-line reason.

## Step 5 — Route to the owning repo

Map each cluster to where the **fix** lives (not where the friction surfaced):

| Cluster signal | Owning repo |
|---|---|
| codex / review-pr-codex, submit-task signing, friction-mcp, hugin orchestration, delegate/broker | `hugin` |
| memory_update_status, munin core, consolidation, openrouter key, memory_* tools | `munin-memory` |
| ratatoskr / Telegram notify | `ratatoskr` |
| m5 / gateway / llama-swap / serving / inference eval | `gille-inference` |
| drone-lab specifics | `drone-lab` |

All repos are under `Magnus-Gille/`. If a cluster doesn't match, ask the user which repo owns it rather than guessing. Verify the slug exists: `gh repo view Magnus-Gille/<repo> --json name -q .name`.

## Step 6 — Write issue bodies to files

**Always write the body to a file and use `--body-file`** — never inline. Issue bodies contain backticks, `</parameter>` markup, and shell metacharacters that break inline command substitution (a real past failure). Write each to the scratchpad dir.

Each body includes: **Problem** · **Evidence** (dated event summaries from the `detail` fields) · **Proposed fix(es)** · **Source** (the `signals/friction` keys). Keep it self-contained so the issue stands without Munin access.

## Step 7 — File issues + add to the board

For each cluster, in a single bounded loop (capture URLs, don't dump full output):
```bash
url=$(gh issue create --repo "Magnus-Gille/<repo>" --title "<title>" --body-file "<file>")
gh project item-add 1 --owner Magnus-Gille --url "$url"
```
The **Grimnir Roadmap** is project **1** (`--owner Magnus-Gille`); new items auto-land in **Todo**. Omit `--label` unless you've confirmed the label exists in that repo (missing labels fail the create).

Then **verify** all landed on the board (item-add prints nothing useful on success):
```bash
gh project item-list 1 --owner Magnus-Gille --format json -L 300 | \
  python3 -c 'import sys,json; d=json.load(sys.stdin); [print((c:=it["content"]).get("repository","").split("/")[-1], c.get("number"), it.get("status")) for it in d["items"]]'
```

## Step 8 — Log the sweep to Munin

1. `memory_log` to `meta/friction-triage` (tags `["milestone","decision","friction"]`): the issues filed (repo#num + one-line each), the not-filed/upstream items, and any cross-cutting finding.
2. `memory_write` `meta/friction-triage/status` (tag `active`): compact index table of open issues with priorities, the **sweep date** (so the next run's Step 1 window is correct), and next steps.
3. **Optional, closes the loop:** tag each filed source event so the next sweep skips it — `memory_write` the event back with an added `issue:<repo>#<num>` tag (use the `patch.tags_add` form). Skip if it adds too many round-trips; the sweep-date window already prevents double-filing.

## Step 9 — Report

Give the user: a table of issues filed (repo#num, title, severity, event count), what was deliberately not filed and why, and the highest-leverage issue to start on. Offer to begin on the top one.

## Quick mode

`/friction-triage report` — Steps 1–4 only: read, filter, group, classify, and present the proposed issue table **without** filing anything. Use to preview a sweep before committing to tickets.
