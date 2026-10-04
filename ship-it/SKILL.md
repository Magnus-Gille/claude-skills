---
name: ship-it
description: Deliver a scoped repository task through independent model review, green CI/CD, merge and verified deployment. Use for ship-it or explicit requests to solve a task hela vägen to production; not for an isolated fix, review-only request or deploy-only task without this workflow's existing handoff.
---

# Ship it

Carry the authorized task to verified production. Keep the same acceptance
criteria and revision trail through implementation, independent review, CI,
merge and rollout. Resume a partly completed delivery from its verified state.

## Establish scope and authority

- Read the owning repository's `AGENTS.md`, deployment contract and current
  handoff; orient in persistent memory when the owner's instructions require it.
  Record the task, repository, intended base, acceptance criteria, exclusions,
  required checks and deployment target. Ask early about a material ambiguity;
  continue independent work while awaiting its answer.
- An explicit full-pipeline request covers the requested publication, PR,
  readiness and merge stages in the identified repository, subject to applicable
  policies. Preview the exact target and concise change; reuse existing
  authorization instead of asking again at every stage. Automatic selection of
  this skill does not turn a generic bug-fix request into rollout authorization.
- The skill does not waive owner, repository or harness boundaries. Prepare the
  concrete release, backup, verification and rollback before asking for any
  required production confirmation. Execute without another question when a
  valid confirmation already covers that exact action and target.
- Keep deployments, external mutations, security judgment and final acceptance
  on the conductor. Delegate bounded implementation/checks under the owner's
  routing policy. Preserve co-tenant changes and use isolated worker worktrees.

## Delivery workflow

1. **Implement and verify.** Work on a task branch. Reproduce behavioral failures
   before fixing them and preserve legitimate controls. Run the repository's
   required gates and change-relevant checks; add native/runtime/UI evidence
   when mocks or source inspection cannot establish acceptance. Fix failures
   caused by the change; identify unrelated failures without silently widening
   scope or claiming every warning has been resolved.
2. **Independent model review.** After deterministic checks pass, freeze the
   candidate diff and relevant source. Follow [review.md](references/review.md)
   for the latest Opus/Sol review defaults, both at `xhigh`, and route constraints.
   Prefer another provider; a genuinely different independent model is an
   acceptable fallback. Validate findings as hypotheses, fix grounded defects
   with regression evidence, and explain declined findings. Material subsequent
   changes require renewed review of the affected scope unless an active
   specialized workflow prescribes a different review cycle. Tests/docs-only
   follow-ups may retain the original review with a recorded conductor check.
3. **Publish and obtain green CI/CD.** Inspect the complete outgoing diff, push
   the task branch normally and create/update the scoped PR into the discovered
   base. Attach a created PR when the harness supports it. Read back its exact
   head/base and wait for the configured checks. Apply the fresh-receipt rules
   in [release-gates.md](references/release-gates.md); a watcher exit code or an
   empty rollup is insufficient. Diagnose failures before retrying. Retry a
   demonstrated transient failure once; a repeated condition needs investigation
   and a bounded correction or an explicit blocker, not endless reruns.
4. **Merge the accepted revision.** Immediately recheck head, current base,
   review dispositions, required checks and mergeability. Mark ready if needed,
   then use the provider's normal merge with a head-matching guard. Never bypass
   checks or force-push. Verify the merge receipt, resulting tree/parents as
   appropriate to the chosen merge method, and intended issue closure. Base
   drift must be evaluated before integration; preserve the existing handoff if
   acceptance needs to be repeated.
5. **Prepare and deploy.** Bind an isolated source to the accepted immutable
   merge/release receipt, using the repo's fail-closed deploy mechanism rather
   than deriving the release from the current checkout. Prepare and verify a
   recoverable backup and rollback appropriate to this change. Present the
   repository, exact revision, target, deploy command, verification command and
   rollback for any required just-in-time approval; then run only that approved
   rollout. Follow the owning deploy contract, including its environment/data
   preservation and client/server scope.
6. **Verify production.** Prove both artifact identity and running behavior:
   expected source/dependency hashes or equivalent platform receipt, service
   health, relevant authenticated/application probes, migrations and workers.
   Source code, a version string or an HTTP 200 alone does not prove deployment.
   Stamp a deployed marker only after all required checks pass. On failure,
   perform only the approved rollback; a data restore that loses newer writes
   requires its own authorization.

## Keep a small delivery handoff

At natural breakpoints retain these facts in the repo's designated handoff and,
when required, a brief persistent-memory milestone/status with concurrency
protection. Use an active tool/skill's artifact-storage rules for its evidence.

| Stage | Minimum evidence |
|---|---|
| Scope | Task, owning repo/base/target, acceptance and authorization boundaries |
| Candidate | Immutable head, intended paths, local gate results and limitations |
| Review | Input head/scope, reviewer identity evidence, findings/dispositions |
| Hosted checks | PR URL, exact head/base, expected check set and fresh conclusions |
| Merge | Provider receipt/revision, integration identity and issue state |
| Rollout | Source/target binding, backup, deploy/verify/rollback commands, approval |
| Production | Verified artifact and health receipt; rollback result if used |

On continuation, re-read live facts and pending approvals; do not repeat a
completed publication, merge or deploy solely because the chat was compacted.
A changed head invalidates its hosted-check receipt and requires the affected
test/review gates again. A changed target/release/sensitive action invalidates
confirmation for the previous one.

If a required capability or approval is unavailable, complete unaffected work
and leave the exact next action and missing condition. Do not call the task
complete while a required stage remains pending. For a narrower endpoint the
user explicitly requested, report that endpoint accurately. Keep the final
answer short: outcome, verification, remaining limitations and the smallest
necessary next step. Use a requested completion phrase only when that endpoint
has actually been verified.
