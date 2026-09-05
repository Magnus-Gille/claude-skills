## Canonical report contract

The audit may vary with the session. **The final report must not.** Always render the final response
with `scripts/render-report.py`; never compose or reformat the report manually.

1. Assemble a bounded temporary JSON file with this shape:

```json
{
  "mode": "full",
  "closed_at": "YYYY-MM-DD HH:MM TZ",
  "scope": ["repo-or-workspace"],
  "completed": ["Concrete completed outcome."],
  "repositories": [
    {
      "name": "repo",
      "branch": "main",
      "working_tree": "clean",
      "remote": "origin/main synchronized",
      "disposition": "complete"
    }
  ],
  "verification": ["Tests passed."],
  "persistence": ["STATUS.md updated."],
  "deployment": ["Not changed."],
  "cleanup": ["Removed bounded disposable cache."],
  "blockers": [],
  "warnings": [],
  "pending": []
}
```

2. Use short factual strings. Include one repository row per affected Git root, including clean
   roots. Describe deliberately retained dirty state in `working_tree` and `disposition`; do not
   hide it in prose.
3. Put only conditions that prevent a safe close in `blockers`. Put freshness limits, intentionally
   retained dirty state, open PRs, and other non-blocking caveats in `warnings`. Put concrete
   follow-ups in `pending` in priority order.
4. For quick mode, still populate every field. Use explicit entries such as `Not checked in quick
   mode.` rather than dropping sections.
5. Render and capture stdout:

```bash
python3 <close-skill-dir>/scripts/render-report.py <close-report.json>
```

6. Delete the temporary JSON after rendering. Return the renderer's stdout **verbatim** as the final
   answer. Add no greeting, explanation, alternative summary, follow-up question, or text after it.

The renderer fixes heading order, repository sorting, empty-section placeholders, and status:

- `NOT READY` when `blockers` is non-empty.
- `READY WITH NOTES` when there are no blockers but `warnings` or `pending` is non-empty.
- `READY` only when all three are empty.

Do not override or editorialize the derived status. If the renderer itself is missing or fails, add
that as a blocker, preserve the same section order shown by the script, and do not claim `READY`.

