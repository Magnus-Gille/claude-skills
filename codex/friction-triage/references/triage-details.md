# Friction triage details

Read this reference when filtering a corpus or when the user has explicitly authorized filing and state updates. The entrypoint keeps these operational details out of unrelated triage requests.

## Read the corpus

The data layer is in hugin (`src/friction-mcp.ts` and `scripts/friction-report.mjs`). Prefer the munin-memory MCP in-session; shell out to the hugin report only for raw aggregate counts.

1. Enumerate `signals/friction` with `memory_list` to get event previews and tags.
2. Read `meta/friction-triage/status` for the previous sweep date. Triage only events after that date; if no sweep exists, use the full corpus.
3. Read the full content of in-window open events with `memory_read_batch`, including `summary`, `detail`, `tool_name`, and `user_tags`.

## Suppression and grouping

Skip an event when any of these apply:

- It has `status:completed`, `fixed-by:*`, or a `**Resolution:**` note.
- Its key starts with `smoke-test` or `tailscale-smoke`.
- It already has an `issue:*` tag (legacy `issue:<repo>#<num>` or a ticket key such as `issue:HUGIN-412`).

Cluster surviving events by tool/subsystem and root failure, using `tool_name` and `user_tags`. Repeated events become one ticket; keep distinct failure modes as sub-points and retain the source keys for evidence.

Flag a cluster instead of filing when it is a harness/provider bug, an external MCP failure, or behavior already covered by an existing repository rule. Explain the reason in the report.

## Route and prepare tickets

Route by where the fix lives. Each repo is a Plane project (one per former GitHub repo; ticket key `IDENT-N`):

| Signal | Owning repo |
|---|---|
| codex, review-pr-codex, submit-task signing, friction-mcp, hugin orchestration, delegate/broker | `hugin` |
| memory tools, status updates, consolidation, retrieval, openrouter key | `munin-memory` |
| ratatoskr or Telegram notification | `ratatoskr` |
| m5, gateway, llama-swap, serving, inference evaluation | `gille-inference` |
| drone-lab-specific behavior | `drone-lab` |

If no route matches, ask the user rather than guessing. Verify a chosen repo has a project with `project_list` (MCP) or:

```bash
tix projects
```

Write each body to a scratch file and pass it with `-f`; never inline friction details containing backticks, markup, or shell metacharacters. Include **Problem**, **Evidence**, **Proposed Fix**, and **Source** friction keys so the ticket stands without Munin access.

When filing is authorized, create each ticket with the Grimnir Roadmap board label and component label in one bounded call:

```bash
tix new -p "<repo>" -t "<title>" -f "<file>" -l board:grimnir-roadmap -l "component:<Component>" --priority "<priority>" --from "<sender>"
```

The MCP equivalent is `ticket_create` with `project`, `title`, `description`, `labels`, `priority` and `from`. Either way the call returns the ticket key and URL; record both.

- Board membership is the label `board:grimnir-roadmap`; the former Component field is the label `component:<Component>` (for example `component:Hugin`).
- Map severity to Plane priority: Critical to `urgent`, High to `high`, Medium to `medium`, Low to `low`.
- `--from <sender>` (MCP `from`) adds the label `from:<sender>` and the `Filed by: <sender>` footer; do not add either by hand. `board:*`, `component:*` and `from:*` labels are created on first use. Omit any other label unless it exists in the target project (`project_meta`; an unknown label makes the call fail and lists the valid ones).
- Do not attempt authentication or token changes as part of triage without separate owner authorization. Pull requests stay on GitHub; do not file GitHub issues.

## Verify ticket and board state

The create call returns the key and URL; read each new ticket back by key to confirm it landed as intended:

```bash
tix show "<KEY>" --json
```

Confirm the project, title, `priority`, and that the labels include `board:grimnir-roadmap`, `component:<Component>` and `from:<sender>`. For the board as a whole, `tix ls -l board:grimnir-roadmap -s open --json` lists every open roadmap ticket across projects. `tix ls` pages up to 500 tickets, so a result of exactly 500 may be truncated.

## Log state

After an authorized sweep:

1. `memory_log` to `meta/friction-triage` with filed tickets, deliberately unfiled items, and cross-cutting findings; use tags `milestone`, `decision`, and `friction`.
2. Update `meta/friction-triage/status` with the sweep date and compact open-ticket index so the next window is correct.
3. Optionally add `issue:<KEY>` (the Plane ticket key, e.g. `issue:HUGIN-412`) to each source event with `patch.tags_add`; the sweep date already prevents double filing.

Report ticket key (or repository when not filed), title, severity, event count, and filing decision. End with the highest-leverage ticket.
