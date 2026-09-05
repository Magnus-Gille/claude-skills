---
name: friction-triage
description: Triage accumulated Munin friction and prepare or file consolidated GitHub issues routed to their owning repos. Use when the user explicitly asks to review friction signals or turn them into tickets.
---

# /friction-triage — Triage accumulated friction

Use this workflow to read the Munin friction corpus, group recurring root causes, separate local fixes from upstream problems, and produce a compact issue proposal. Filing GitHub issues, adding board items, or writing Munin state requires explicit user direction; report mode is the default.

## Workflow

1. Read [references/triage-details.md](references/triage-details.md) for the exact sweep-window and suppression rules, then filter the open events.
2. Group repeated root causes and classify each cluster as locally actionable or upstream/covered.
3. Route actionable clusters to the repository that owns the fix.
4. Present a compact table before any publication.
5. If the user explicitly requests filing, use the same reference for issue-body handling, board verification, and Munin updates.

Use `/friction-triage report` to stop after the proposed table without filing, changing board state, or writing Munin state.
