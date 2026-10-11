---
name: ticket-fleet
description: Compatibility route for legacy ticket-fleet requests. Use ship-it's PR endpoint for each scoped ticket and its batch reference for coordination; this entrypoint does not dispatch workers or authorize merge/deploy.
---

# Ticket-fleet compatibility

For an existing `/ticket-fleet` request, use the single delivery workflow in
[`../ship-it/SKILL.md`](../ship-it/SKILL.md) at the **PR endpoint**. It ends
after publication and fresh checks; it never merges. If the user separately
requests a later endpoint, handle that as an explicit `/ship-it` request under
its normal workflow. For multi-ticket coordination, read ship-it's
[batch reference](../ship-it/references/batch.md).

An explicit `/ticket-fleet` invocation that names the task and owning
repository is the user's request to prepare and publish PRs as needed to reach
this endpoint, subject to global policy and exact target/change preview. If the
repository or target is unclear, clarify it before publication. Automatic
skill selection does not authorize publication.

This compatibility entrypoint does not launch headless sessions, grant tool
permissions, invoke local models, or authorize merge or deployment. The global
`AGENTS.md` remains the authority source for mutation boundaries. Legacy runner
scripts now fail closed and direct callers to `/ship-it`.
