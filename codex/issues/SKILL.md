---
name: issues
description: Inspect current-repository GitHub issues or prepare a specifically requested routed issue. Use when the user asks to list, view, filter, search, or create an issue.
---

# GitHub Issues

Use this skill to inspect and summarize GitHub issues for the current repository.

## Workflow

1. Detect the repository:
   ```bash
   gh repo view --json nameWithOwner -q '.nameWithOwner'
   ```
   If this fails, do not infer that the directory is not connected to GitHub. Check
   `git remote get-url origin` (or the relevant remote), resolve its owner/repo, and
   retry the read-only lookup. Retry `gh api user --jq .login` to distinguish an
   authentication/API problem from a missing or unusable remote; report the exact
   diagnosis before stopping.

2. Run the narrowest query that matches the request:
   ```bash
   gh issue list --repo <owner/repo> --state open
   gh issue view <number> --repo <owner/repo>
   gh issue list --repo <owner/repo> --state open --label "<label>"
   gh issue list --repo <owner/repo> --state closed --limit 10
   gh issue list --repo <owner/repo> --state open --search "<query>"
   ```

3. Present results compactly.
   - For issue lists, group by label and show `#number - title`.
   - For one issue, show title, status, labels, body summary, comments/actions, and any referenced files.
   - Mention Grimnir Roadmap board relevance when visible.

4. Prepare or publish a routed issue when requested.
   - Resolve the owning repository and search it for likely duplicates before drafting.
   - Prepare a title, verified labels only, and a temporary body file containing the
     problem, evidence, proposed fix, source, and owning-repository attribution.
     For cross-repo Grimnir work, add `from:<sender>` when the target uses sender
     labels and include `Filed by: <sender>` in the body.
   - Preview the exact owner/repo, title, labels, body, and any board target. Use
     `gh issue create --repo <owner/repo> --title ... --body-file <file>` only after
     explicit user direction to publish. Preparation alone does not publish.
   - Only the owning Grimnir session may add an item to the Grimnir Roadmap board,
     and only with explicit authorization for that board mutation. Report board
     relevance without adding it otherwise.

5. Offer a concrete next step only when useful: inspect, implement, close with a comment, or create a missing issue. Creating, commenting, closing, or adding to a board requires explicit user direction.

## Cross-Repo Rule

If a fix belongs in another Magnus-owned repo, file a GitHub issue in the owning repo instead of editing that repo directly. Add `from:<sender>` when the target repo uses sender labels, include `Filed by: <sender>` in the issue body, and leave board placement to the owning Grimnir session under explicit owner authorization. Follow the preparation and publication boundary above.

## Rules

- Always pass `--repo`; do not rely on working-directory inference.
- Keep list views scannable.
- Do not close or merge anything without explicit user direction.
- Use issue body files for complex issue creation instead of shell-inlined markdown.
