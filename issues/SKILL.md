---
name: issues
description: Check GitHub issues and tickets for the current repo. List open issues, view details, filter by label, or search. Use when the user asks about issues, tickets, bugs, or backlog.
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

If this fails, tell the user they're not in a GitHub repo.

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

### Step 4: Offer next steps

After presenting, briefly suggest relevant actions:
- "Want me to look into any of these?"
- "Want me to close this with a comment?" (if viewing a resolved issue)
- "Want me to create a new issue?" (if listing and something is missing)

Don't be verbose about it — one line is enough.

## Key Rules

1. **Always use `--repo`** — don't assume `gh` will infer correctly from the working directory in all cases.
2. **Group by label** — the default list should be scannable, not a wall of text.
3. **Link to the project board** — if issues mention a GitHub Project, note it.
4. **Keep it brief** — the list view is the default. Only expand when viewing a single issue.
