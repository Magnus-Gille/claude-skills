---
name: issues
description: Inspect current-repository GitHub issues or prepare a specifically requested routed issue. Use when the user asks to list, view, filter, search, or create an issue.
---

# /issues - Check GitHub Issues

Check open issues and tickets for the current repo using the GitHub CLI.

## Usage

- `/issues` — list all open issues
- `/issues <number>` — view a specific issue by number
- `/issues <label>` — filter by label (e.g., `bug`, `security`, `enhancement`)
- `/issues closed` — show recently closed issues
- `/issues search <query>` — search issues by keyword

## Instructions

### Step 1: Detect the repo

Use the git remote to determine the owner/repo:

```bash
gh repo view --json nameWithOwner -q '.nameWithOwner'
```

If this fails, do not infer that the directory is not a GitHub repo. Check
`git remote get-url origin` (or the relevant remote), resolve its owner/repo, and
retry the read-only lookup. If the lookup may be an authentication/API problem,
retry `gh api user --jq .login` before reporting the exact diagnosis. Stop only
when there is no usable remote or the read-only identity/repository checks fail.

### Step 2: Run the appropriate query

**List open issues (default):**
```bash
gh issue list --repo <owner/repo> --state open
```

**View a specific issue:**
```bash
gh issue view <number> --repo <owner/repo>
```

**Filter by label:**
```bash
gh issue list --repo <owner/repo> --state open --label "<label>"
```

**Show recently closed:**
```bash
gh issue list --repo <owner/repo> --state closed --limit 10
```

**Search by keyword:**
```bash
gh issue list --repo <owner/repo> --state open --search "<query>"
```

### Step 3: Present results

**For issue lists:** Group by label and show a compact summary:

```
**Bugs (2):**
- #1 — Task status tags never flip from pending to running
- #2 — mDNS flaky

**Enhancements (1):**
- #3 — Phase 5: Sensitivity classification
```

If an issue has no labels, group it under **Other**.

**For single issue view:** Show title, status, labels, body, and any comments. If the issue references code, note the relevant files.

### Step 4: Prepare or publish a routed issue

When the user asks to create an issue, or asks for a routed issue proposal:

1. Resolve the owning repository and search it for likely duplicates before drafting.
2. Prepare a title, labels only when verified, and a body in a temporary file with
   the problem, evidence, proposed fix, and source/owning-repo attribution. For a
   cross-repo Grimnir task, include `from:<sender>` when the target uses sender
   labels and `Filed by: <sender>` in the body.
3. Preview the exact owner/repo, title, labels, body, and any board target. Use
   `gh issue create --repo <owner/repo> --title ... --body-file <file>` only after
   explicit user direction to publish; preparation alone never publishes.
4. Only the owning Grimnir session may add an item to the Grimnir Roadmap board,
   and it must have explicit authorization for that board mutation. This skill may
   report board relevance without adding the item.

### Step 5: Offer next steps

After presenting, briefly suggest relevant actions:
- "Want me to look into any of these?"
- "Want me to close this with a comment?" (if viewing a resolved issue)
- "Want me to create a new issue?" (if listing and something is missing)

Don't be verbose about it — one line is enough. Creating, commenting, closing, or adding to a board requires explicit user direction.

## Key Rules

1. **Always use `--repo`** — don't assume `gh` will infer correctly from the working directory in all cases.
2. **Group by label** — the default list should be scannable, not a wall of text.
3. **Link to the project board** — if issues mention a GitHub Project, note it.
4. **Keep it brief** — the list view is the default. Only expand when viewing a single issue.
