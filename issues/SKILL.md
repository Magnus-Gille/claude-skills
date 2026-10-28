---
name: issues
description: Inspect current-repository tickets in Plane (via the tickets MCP tools, else the tix CLI) or prepare a specifically requested routed ticket. Use when the user asks to list, view, filter, search, or create an issue or ticket.
---

# /issues - Check tickets

Check open tickets for the current repo in Plane CE (`https://tickets.gille.ai`, workspace
`gille`). Tickets replaced GitHub Issues: there is one Plane project per repository, a
ticket key is `IDENT-N` (for example `GRIM-87`), and migrated tickets keep their GitHub
number (`grimnir#87` is `GRIM-87`). Do not use `gh issue`; old GitHub issues are closed
with a link to their ticket and no new ones are filed. Pull requests stay on GitHub.

## Tools

Prefer the `tickets` MCP server when its tools are available (in Claude Code they appear
as `mcp__tickets__*`; load them through tool search if deferred). Otherwise use the `tix`
CLI. Both reach the same gateway and share the same conventions.

| Need | MCP tool | `tix` |
|---|---|---|
| List / filter / search | `ticket_search` | `tix ls -p P [-s STATE] [-l LABEL]... [-q QUERY] [--json]` |
| View one ticket | `ticket_get` | `tix show KEY [--json]` |
| Create | `ticket_create` | `tix new -p P -t TITLE -f FILE.md [-l LABEL]... [--priority PRIO] [--from SENDER]` |
| Update / comment / close | `ticket_update`, `ticket_comment`, `ticket_close` | `tix edit`, `tix comment`, `tix close` |
| Projects, valid labels and states | `project_list`, `project_meta` | `tix projects` |
| Cross-project modules and cycles | `roadmap` | `tix roadmap [-p P]` |

`P` is the Plane identifier (`GRIM`) or the repo name (`grimnir`). Priorities are
`urgent`, `high`, `medium`, `low`, `none`. States are Plane state names (`Backlog`, `Todo`,
`In Progress`, `Done`, `Cancelled`) or the aliases `open` and `closed`.

If neither the MCP tools nor `tix` work, report the exact error and stop. A missing `tix`
token is exit code 2. Do not mint tokens or change authentication.

## Usage

- `/issues` — list all open tickets
- `/issues <KEY|number>` — view a specific ticket (`87` means `<IDENT>-87`)
- `/issues <label>` — filter by label (e.g., `bug`, `security`, `enhancement`)
- `/issues closed` — show recently closed tickets
- `/issues search <query>` — search tickets by keyword

## Instructions

### Step 1: Resolve the project

Take the repo name from the git remote, not from the directory name:

```bash
git remote get-url origin
```

Use the last path segment without `.git` as the project (for example `grimnir`). Confirm it
with `project_list` (or `tix projects`) the first time. If the repo has no project, report
that and stop instead of guessing another project. Always pass the project explicitly:
omitting it searches every project.

### Step 2: Run the appropriate query

**List open tickets (default):**
```text
ticket_search {project: "<repo>", state: "open"}
tix ls -p <repo> -s open
```

**View a specific ticket:**
```text
ticket_get {key: "<IDENT>-<n>"}
tix show <IDENT>-<n>
```

**Filter by label:**
```text
ticket_search {project: "<repo>", state: "open", labels: ["<label>"]}
tix ls -p <repo> -s open -l "<label>"
```

**Show recently closed:**
```text
ticket_search {project: "<repo>", state: "closed", limit: 10}
tix ls -p <repo> -s closed
```
Results are ordered by last update; show the first 10.

**Search by keyword:**
```text
ticket_search {project: "<repo>", state: "open", query: "<query>"}
tix ls -p <repo> -s open -q "<query>"
```

An unknown label is an error that lists the valid ones; `project_meta` shows them up front.

### Step 3: Present results

**For ticket lists:** Group by label and show a compact summary with the key and priority:

```
**Bugs (2):**
- GRIM-1 (high) — Task status tags never flip from pending to running
- GRIM-2 (medium) — mDNS flaky

**Enhancements (1):**
- GRIM-3 (low) — Phase 5: Sensitivity classification
```

Group by type labels such as `bug` and `enhancement`. The convention labels `from:*`,
`board:*` and `component:*` are not groups; mention them inline when useful. If a ticket has
no type label, group it under **Other**.

**For single ticket view:** Show key, title, state, priority, labels, description, comments,
links and relations. If the ticket references code, note the relevant files. A ticket with
the label `board:grimnir-roadmap` is on the Grimnir Roadmap; say so. For the cross-project
overview use `roadmap` / `tix roadmap`.

### Step 4: Prepare or publish a routed ticket

When the user asks to create a ticket, or asks for a routed ticket proposal:

1. Resolve the owning repository and search its project for likely duplicates before drafting.
2. Prepare a title, priority, labels only when verified (`project_meta`), and a body in a
   temporary file with the problem, evidence, proposed fix, and source/owning-repo
   attribution. For a cross-repo Grimnir task, pass the sender as `from` (`--from <sender>`),
   which adds the label `from:<sender>` and the `Filed by: <sender>` footer; do not add
   either by hand.
3. Preview the exact project (identifier and repo), title, priority, labels, body, and any
   board label. Use `ticket_create` (or `tix new -p <repo> -t ... -f <file>`) only after
   explicit user direction to publish; preparation alone never publishes. Report the
   returned key and URL.
4. Only the owning Grimnir session may add the label `board:grimnir-roadmap` (that label is
   Grimnir Roadmap membership), and it must have explicit authorization for that board
   mutation. This skill may report board relevance without adding the label.

### Step 5: Offer next steps

After presenting, briefly suggest relevant actions:
- "Want me to look into any of these?"
- "Want me to close this with a comment?" (if viewing a resolved ticket)
- "Want me to create a new ticket?" (if listing and something is missing)

Don't be verbose about it — one line is enough. Creating, commenting, closing, or adding a board label requires explicit user direction.

## Key Rules

1. **Always pass the project** — don't rely on cwd inference, and don't search every project unless the user asked for that.
2. **Group by label** — the default list should be scannable, not a wall of text.
3. **Link to the board** — if a ticket carries `board:grimnir-roadmap`, note it.
4. **Keep it brief** — the list view is the default. Only expand when viewing a single ticket.
5. **PRs reference tickets by key** — a pull request says `Refs GRIM-87` plus the Plane URL. There is no automatic PR linking and `Closes #n` no longer closes anything, so close a ticket explicitly (`ticket_close`) and only on user direction.
