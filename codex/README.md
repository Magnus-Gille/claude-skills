# Codex skill adapters

The directories here are tracked Codex-native companions to the Claude-facing skills at the repository root. Some are adapters because invocation syntax, available tools, and review boundaries differ between harnesses. The two explicitly marked mirrors preserve the same body; compare their complete directory contents during sync to detect drift.

| Adapter | Claude-facing source | Deliberate difference |
|---|---|---|
| `commit` | `../commit` | Uses `$commit` and the Codex coauthor trailer. |
| `eli5` | `../eli5` | Supports direct topic/tool/error explanations and keeps Codex's concise routing. |
| `friction-triage` | `../friction-triage` | Mirror of the canonical workflow; keep the complete directory byte-identical during sync. |
| `issues` | `../issues` | Preserves Grimnir cross-repository routing and Codex CLI conventions. |
| `magnus-security-review` | `../magnus-security-review` | Mirror of the canonical manual review; keep the complete directory byte-identical during sync. |
| `review-pr-codex` | `../review-pr-codex` | Reviews directly in the current Codex session; it must not invoke Codex recursively. |

These adapters are not installed by `claude-config/bootstrap.sh`. Install or sync an adapter as a complete directory, including its `references/` files. Do not replace an adapter with the Claude-facing skill.
