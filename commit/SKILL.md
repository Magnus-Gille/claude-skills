---
name: commit
description: Standardized git commit workflow with author verification, diff review, and conventional commit messages.
---

# /commit - Standardized Git Commit

Create clean, well-documented git commits with safety checks.

## Usage

- `/commit` - Stage, review, commit, and optionally push
- `/commit <message>` - Commit with a specific message (still runs safety checks)
- `/commit amend` - Amend the last commit (with confirmation)

## Workflow

### Step 1: Verify Author Identity

```bash
git config user.name
git config user.email
```

- Expected: **Magnus Gille** / **magnus.gille@outlook.com**
- If wrong, warn the user and ask before proceeding
- Do NOT silently fix it — the user should decide

### Step 2: Review Changes

Run in parallel:
```bash
git status
git diff --stat
git diff --staged --stat
```

Present a summary:
- Files modified (staged vs unstaged)
- Files added/deleted
- Untracked files that might need staging

Ask the user which files to stage if there are unstaged changes. Prefer staging specific files over `git add -A`.

### Step 3: Security Check

Before committing, verify:
- No `.env`, `credentials.json`, `token.json`, or `client_secret_*.json` files are staged
- No files in `secrets/` are staged
- No files with `key`, `secret`, or `token` in the name are staged (unless they're clearly code files)

If any are found, **warn and stop**. Do not commit.

### Step 4: Write Commit Message

If no message was provided, draft one:
- Use conventional commit format: `type: description`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`
- Keep the first line under 72 characters
- Add a body paragraph if the change is non-trivial
- Always end with: `Co-Authored-By: Claude <assistant> <noreply@anthropic.com>` (use the current model name)

Show the proposed message and ask for confirmation.

### Step 5: Commit

```bash
git add <files>
git commit -m "<message>"
```

Use a heredoc for multi-line messages.

### Step 6: Push

After committing:
- Show the commit hash and summary
- If a remote is configured and the branch tracks one: ask "Push to remote?" and push if confirmed
- If no remote or untracked branch: just confirm the local commit

## Key Rules

1. **Never auto-push** — always ask first
2. **Never amend without confirmation** — amending rewrites history
3. **Never use `--no-verify`** — respect pre-commit hooks
4. **Never use `git add -A`** — stage specific files
5. **Always show the diff summary** — the user should know what they're committing
6. **Always verify author** — wrong author requires force-push to fix
