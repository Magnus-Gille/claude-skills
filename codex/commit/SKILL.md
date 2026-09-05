---
name: commit
description: Create or amend a Git commit with author verification, diff review, and a conventional message. Use only when the user explicitly invokes $commit or asks to commit or amend changes.
---

# $commit - Standardized Git Commit

Create clean, well-documented git commits with safety checks.

## Usage

- `$commit` - Stage, review, and commit changes
- `$commit <message>` - Commit with a specific message (still runs safety checks)
- `$commit amend` - Amend the explicitly requested commit

## Workflow

### Step 1: Verify Author Identity

```bash
git config user.name
git config user.email
```

- The configured identity should be the user's intended name and email for this repository. If either is empty or unexpected (for example, a CI or bot identity), warn before proceeding.
- Do NOT silently fix it — the user should decide whether to update the config or commit under the current identity.

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

Stage specific task-owned files within the requested commit scope. Preserve unrelated staged and unstaged changes; ask only when ownership or scope is unclear. Inspect the exact staged diff before committing, including any pre-existing staged content. Do not include unrelated staged content in this commit or unstage it without authorization.

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
- Always end with: `Co-Authored-By: Codex <noreply@openai.com>`

Show the proposed message and staged diff summary, then commit under the existing request. Ask again only when the user required message approval or a material scope decision remains.

### Step 5: Commit

```bash
git add <files>
git commit -m "<message>"
```

Use a heredoc for multi-line messages.

### Step 6: Post-Commit

Show the commit hash and summary. Push only when the owner has explicitly authorized publication in this task, after previewing the exact remote, branch, and concise diff. Otherwise report the local commit as complete.

## Key Rules

1. Publication needs explicit owner authorization; reuse authorization already given for this task.
2. Amend only the owner-requested commit. Rewriting published history needs explicit authorization for that action and target.
3. Never use `--no-verify`; respect pre-commit hooks.
4. Stage specific files and preserve unrelated work.
5. Inspect the exact staged diff and report what was committed.
6. Verify author identity; stop on an unexpected identity without silently changing configuration.
