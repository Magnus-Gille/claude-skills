# Debate artifacts and records

## Git handling

Debate files have two tiers: searchable artifacts worth tracking, and raw process logs that are useful during the debate but noisy afterward. Drafts, self-reviews, critiques, responses, and rebuttals are scratch paper. Summaries, critique logs, and the index are the searchable residue.

The default project `.gitignore` pattern is:

```gitignore
debate/*
!debate/INDEX.md
!debate/*-summary.md
!debate/*-critique-log.json
```

This tracks `INDEX.md`, each summary, and structured critique logs while keeping drafts and raw review output local. Before the first debate in a project, inspect the existing `debate/` ignore policy. If it is absent, suggest the default pattern. If the whole directory is ignored, suggest upgrading to the summaries-tracked pattern when future search value justifies it.

If the project specifically studies debate methodology or prompt engineering, full tracking is a valid exception. If the outcome is fully incorporated into a durable ADR or plan and no one will search for the debate again, ignoring the whole directory is also valid.

The skill does not authorize commits, pushes, issue comments, or other publication. Follow the repository's authorization and review policy for any publication.

## Step 8: Structured critique log

Create `debate/<topic>-critique-log.json` with every critique point from every round:

```json
[
  {
    "id": "<topic>-C01",
    "source": "claude-round-1",
    "text": "Brief description of the critique point",
    "classification": "valid | partially_valid | invalid",
    "impact": "changed | partially_changed | acknowledged | deferred | rejected",
    "severity": "critical | major | minor",
    "caught_by_self_review": true
  }
]
```

The `source` field identifies Claude and the round, for example `claude-round-1` or `claude-round-2`. Fill classification and impact after the debate concludes.

Impact values:

- `changed` — position or plan materially changed as a result of the critique.
- `partially_changed` — part of the critique was adopted and part defended.
- `acknowledged` — accepted as valid but no immediate action was taken.
- `deferred` — valid point intentionally set aside for later.
- `rejected` — disagreed with and defended.

Severity measures the consequence of ignoring the critique:

- `critical` — correctness, security, or design flaw with wide blast radius and damage hard to reverse after shipping.
- `major` — real problem with contained blast radius or reasonable recovery effort.
- `minor` — low-consequence observation, cosmetic issue, or unlikely edge case.

When uncertain, ask how difficult recovery would be if the issue were found three months after shipping. Hard recovery belongs at the higher level; easy recovery stays lower.

Every 5–10 debates, review recent logs. Check which severities most often led to `changed`, which critical points were rejected, and which minor points drove changes. Revise the self-review checklists only when a pattern is consistent.

## Step 8.5: Sanitize debate artifacts

Before writing the summary, scan all debate files for private information and local environment details:

- Replace `/Users/<username>/...` and `/home/<username>/...` with `<home>/...` or `<repo-root>/...`.
- Replace personal email addresses with `<email>` unless intentionally public.
- Replace names of non-public individuals with role descriptions.
- Replace internal hostnames and IPs with `<hostname>` and `<ip>`.
- Never retain API keys, tokens, credentials, or other secrets; replace them with `<redacted>`.

Apply these replacements to snapshots, drafts, self-reviews, critiques, responses, rebuttals, critique logs, and summaries. Pay particular attention to any conductor-supplied project-context excerpt, which may contain client paths, relationships, or memory namespace identifiers.

## Step 9: Write the summary

Create `debate/<topic>-summary.md` with:

- Date, participants, exact requested and actual reviewer model for each round, effort, and round count.
- Concessions accepted by both sides.
- Defenses accepted by the reviewer.
- Unresolved disagreements.
- New issues from later rounds.
- Final verdict from both sides.
- Action items with owners, when applicable.
- List of all debate files.
- An explicit note if actual model or effort metadata could not be verified.

Append this cost table:

```markdown
## Costs
| Invocation | Wall-clock time | Requested model | Actual model |
|------------|-----------------|-----------------|--------------|
| Claude R1  | ~Nm             | exact id        | metadata / unverified |
| Claude R2  | ~Nm             | exact id        | metadata / unverified |
```

Do not identify the model from reviewer prose. Use structured invocation metadata or mark it unverified.

## Step 10: Update the debate index

Append a row to `debate/INDEX.md`, creating it if needed:

```markdown
# Debate Index

| Date | Topic | Reviewer | Rounds | Key decision | Critique points | Self-review catch rate |
|------|-------|----------|--------|--------------|----------------|-----------------------|
| YYYY-MM-DD | [topic](topic-summary.md) | claude | N | One-line outcome | X | Y/X (Z%) |
```

If an existing index lacks the `Reviewer` column, add it and backfill known values. Use `unknown` where the reviewer family cannot be established.

## Step 11: Verify completeness

For a normal two-round debate, confirm these files exist before declaring completion:

- `debate/<topic>-codex-draft.md`
- `debate/<topic>-codex-self-review.md`
- `debate/<topic>-claude-critique.md`
- `debate/<topic>-codex-response-1.md`
- `debate/<topic>-claude-rebuttal-1.md`
- `debate/<topic>-summary.md`
- `debate/<topic>-critique-log.json`
- `debate/INDEX.md`
