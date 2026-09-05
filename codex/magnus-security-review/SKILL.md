---
name: magnus-security-review
description: Perform a requested, project-specific security review of a codebase, diff, PR, module, or repository. Use for an explicit security audit; ordinary security-adjacent edits do not activate it.
---

# Magnus Security Review

Run the requested review in three phases: threat model, targeted analysis, and validation/remediation. Keep findings grounded in reachable data flow and state residual uncertainty instead of manufacturing issues.

## Scope and workflow

1. State the repository and exact scope. Review one repository at a time.
2. Read the relevant code, tests, configuration, architecture, and deployment context before scanning. For a full-repository or comprehensive review, read [references/checklists.md](references/checklists.md) and select the categories that apply; for a small diff, inspect only relevant categories.
3. Map entry points, exits, assets, trust boundaries, and privileged operations. Summarize the likely STRIDE risks.
4. Trace inputs to security-sensitive sinks and inspect classic web/API, dependency, infrastructure, CI, IAM, native-safety, and LLM risks that the scope can reach.
5. Validate each candidate against reachability, guards, framework defaults, tests, and exploitability. Mark it Confirmed, Likely, or Theoretical and rate severity by impact and exploitability.
6. Self-critique findings, remove noise, and propose a concrete fix. Do not claim a scanner result, deployment state, or mitigation that was not observed.

For a full review, also inspect relevant security history and sibling occurrences of past fixes. Keep temporary review artifacts out of the repository unless the user requests a durable threat model.

## Output

Lead with findings ordered by severity:

```markdown
# Security Review: <scope>

## Threat Model Summary
<2-3 short paragraphs>

## Findings

### [HIGH] Title - path:line
**Category:** OWASP/LLM/STRIDE
**Status:** Confirmed/Likely/Theoretical
**Attack path:** ...
**Impact:** ...
**Fix:** ...

## Discarded / False Positives
- ...

## Recommendations
- ...
```

If there are no confirmed or likely issues, say so clearly and state residual risk and test gaps.
