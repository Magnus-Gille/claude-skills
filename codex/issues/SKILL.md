---
name: issues
description: Inspect current-repository tickets in Plane (via the tickets MCP tools, else the tix CLI) or prepare a specifically requested routed ticket. Use when the user asks to list, view, filter, search, or create an issue or ticket.
---

# Tickets

Use this skill to inspect and summarize tickets for the current repository. Tickets live in
Plane CE (`https://tickets.gille.ai`, workspace `gille`) and replaced GitHub Issues: one
Plane project per repository, ticket key `IDENT-N` (for example `GRIM-87`), and migrated
tickets keep their GitHub number (`grimnir#87` is `GRIM-87`). Do not use `gh issue`; old
GitHub issues are closed with a link to their ticket and no new ones are filed. Pull
requests stay on GitHub.

## Tools

Prefer the `tickets` MCP tools when available (`ticket_search`, `ticket_get`,
`ticket_create`, `ticket_update`, `ticket_comment`, `ticket_close`, `project_list`,
`project_meta`, `roadmap`); otherwise use the `tix` CLI. They share one gateway and one set
of conventions. In `tix`, `-p` takes the Plane identifier (`GRIM`) or the repo name
(`grimnir`). Priorities are `urgent`, `high`, `medium`, `low`, `none`; states are Plane
state names (`Backlog`, `Todo`, `In Progress`, `Done`, `Cancelled`) or the aliases `open` and
`closed`. If neither route works, report the exact error and stop; do not mint tokens or
change authentication.

## Workflow

1. Resolve the project from the git remote (not the directory name):
   ```bash
   git remote get-url origin
   ```
   Use the last path segment without `.git` as the project (for example `grimnir`) and
   confirm it with `project_list` or `tix projects`. If the repo has no project, report
   that and stop instead of guessing.

2. Run the narrowest query that matches the request, always with the project:

   | Request | MCP tool | `tix` |
   |---|---|---|
   | Open tickets | `ticket_search {project: "<repo>", state: "open"}` | `tix ls -p <repo> -s open` |
   | One ticket | `ticket_get {key: "<IDENT>-<n>"}` | `tix show <IDENT>-<n>` |
   | By label | `ticket_search {project: "<repo>", state: "open", labels: ["<label>"]}` | `tix ls -p <repo> -s open -l "<label>"` |
   | Recently closed | `ticket_search {project: "<repo>", state: "closed", limit: 10}` | `tix ls -p <repo> -s closed` |
   | Keyword | `ticket_search {project: "<repo>", state: "open", query: "<query>"}` | `tix ls -p <repo> -s open -q "<query>"` |

   A bare number means `<IDENT>-<number>`. Results are ordered by last update. An unknown
   label is an error that lists the valid ones; `project_meta` shows them up front.

3. Present results compactly.
   - For ticket lists, group by type label (`bug`, `enhancement`, else **Other**) and show
     `KEY (priority) - title`. The convention labels `from:*`, `board:*` and `component:*`
     are not groups.
   - For one ticket, show key, title, state, priority, labels, description summary,
     comments/actions, links and relations, and any referenced files.
   - Mention Grimnir Roadmap relevance when the ticket carries `board:grimnir-roadmap`. For
     the cross-project overview use `roadmap` or `tix roadmap`.

4. Prepare or publish a routed ticket when requested.
   - Resolve the owning repository and search its project for likely duplicates before drafting.
   - Prepare a title, priority, verified labels only (`project_meta`), and a temporary body
     file containing the problem, evidence, proposed fix, source, and owning-repository
     attribution. For cross-repo Grimnir work pass the sender as `from` (`--from <sender>`),
     which adds `from:<sender>` and the `Filed by: <sender>` footer; do not add either by hand.
   - Preview the exact project (identifier and repo), title, priority, labels, body, and any
     board label. Use `ticket_create` (or `tix new -p <repo> -t ... -f <file>`) only after
     explicit user direction to publish. Preparation alone does not publish. Report the
     returned key and URL.
   - Only the owning Grimnir session may add the label `board:grimnir-roadmap` (that label is
     Grimnir Roadmap membership), and only with explicit authorization for that board
     mutation. Report board relevance without adding it otherwise.

5. Offer a concrete next step only when useful: inspect, implement, close with a comment, or create a missing ticket. Creating, commenting, closing, or adding a board label requires explicit user direction.

## Cross-Repo Rule

If a fix belongs in another Magnus-owned repo, file a ticket in the owning repo's Plane project instead of editing that repo directly. Pass `from` as the sender (adds `from:<sender>` and `Filed by: <sender>`), and leave `board:grimnir-roadmap` placement to the owning Grimnir session under explicit owner authorization. Follow the preparation and publication boundary above.

## Rules

- Always pass the project; do not rely on working-directory inference.
- Keep list views scannable.
- Do not close or merge anything without explicit user direction. Close tickets explicitly (`ticket_close` or `tix close`); there is no automatic PR linking and `Closes #n` no longer closes anything.
- A pull request references its ticket as `Refs GRIM-87` plus the Plane URL.
- Use ticket body files (`-f FILE.md`) for complex ticket creation instead of shell-inlined markdown.
