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
- It already has an `issue:*` tag.

Cluster surviving events by tool/subsystem and root failure, using `tool_name` and `user_tags`. Repeated events become one issue; keep distinct failure modes as sub-points and retain the source keys for evidence.

Flag a cluster instead of filing when it is a harness/provider bug, an external MCP failure, or behavior already covered by an existing repository rule. Explain the reason in the report.

## Route and prepare issues

Route by where the fix lives:

| Signal | Owning repo |
|---|---|
| codex, review-pr-codex, submit-task signing, friction-mcp, hugin orchestration, delegate/broker | `hugin` |
| memory tools, status updates, consolidation, retrieval, openrouter key | `munin-memory` |
| ratatoskr or Telegram notification | `ratatoskr` |
| m5, gateway, llama-swap, serving, inference evaluation | `gille-inference` |
| drone-lab-specific behavior | `drone-lab` |

All repos are under `Magnus-Gille`. If no route matches, ask the user rather than guessing. Verify a chosen slug with:

```bash
gh repo view Magnus-Gille/<repo> --json name -q .name
```

Write each body to a scratch file and use `--body-file`; never inline friction details containing backticks, markup, or shell metacharacters. Include **Problem**, **Evidence**, **Proposed Fix**, and **Source** friction keys so the issue stands without Munin access.

When filing is authorized, create and board each issue in a bounded loop:

```bash
url=$(gh issue create --repo "Magnus-Gille/<repo>" --title "<title>" --body-file "<file>")
gh project item-add 1 --owner Magnus-Gille --url "$url"
```

Project 1 is the Grimnir Roadmap. Omit `--label` unless that label has been verified in the target repository. `item-add` requires the `project` write scope; `read:project` is insufficient. Do not attempt authentication or scope changes as part of triage without separate owner authorization.

## Verify board state

`item-add` may print no useful success output. Verify with a limit well above the board size:

```bash
LIMIT=2000
gh project item-list 1 --owner Magnus-Gille --format json -L "$LIMIT"
```

Count returned items and inspect the newly-created repository/issue numbers. If the count equals `LIMIT`, assume truncation, raise the limit, and repeat before concluding an item is absent. New items can sort last, so a low limit can hide exactly the items just added.

## Log state

After an authorized sweep:

1. `memory_log` to `meta/friction-triage` with filed issues, deliberately unfiled items, and cross-cutting findings; use tags `milestone`, `decision`, and `friction`.
2. Update `meta/friction-triage/status` with the sweep date and compact open-issue index so the next window is correct.
3. Optionally add `issue:<repo>#<num>` to each source event with `patch.tags_add`; the sweep date already prevents double filing.

Report repository/issue, title, severity, event count, and filing decision. End with the highest-leverage issue.
