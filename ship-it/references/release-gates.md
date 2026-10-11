# Fresh release evidence

## CI and merge

Discover the actual required check set from repository policy and provider
rules/workflows. Confirm those checks ran for the exact accepted PR head and
current integration context. Do not infer success from a watcher returning 0,
old logs, a temporarily incomplete rerun rollup, skipped checks or an empty set.
Ambiguous check identities, head/base drift or missing required results leave
the gate pending. A repository intentionally lacking hosted CI must be reported
as such; do not label absence as green CI or invent workflows outside scope.

For GitHub, the optional offline helper validates a fresh receipt's consistency:

```bash
gh pr view <PR> --repo <OWNER/REPO> --json headRefOid,statusCheckRollup > <receipt.json>
python3 <skill-dir>/scripts/check_ci.py <receipt.json> \
  --expected-head <FULL_REVIEWED_HEAD_SHA> \
  --required '<required-check-name>' \
  --required '<another-required-check-name>'
```

Supply every required name, including matrix jobs and provider status contexts;
resolve duplicate names from current provider evidence before using the helper.
Include additional configured jobs when the task's green-CI acceptance requires
them. Ignored optional contexts are not proven successful; report relevant
failures separately rather than describing only a passing subset as all green.
The helper checks names only; verify each selected entry's workflow or status
publisher against provider policy before accepting it. If names cannot be
unambiguously mapped, use the provider's qualified check evidence instead.
It does not discover policy, prove freshness/authenticity or publisher identity,
check the base, or authorize mutation. Independently re-fetch base/head and check
mergeability immediately before normal guarded merge. Other providers use their
equivalent fresh immutable evidence; GitHub is not required by this skill.

After merge, read the provider receipt. Verify integration identity with the
method actually chosen: a merge commit's tree and parents, a squash result's
intended diff, or a rebase's accepted integrated changes. A concurrent unrelated
base change requires evaluating its effect on the accepted scope; do not merely
assume the resulting tree equals a previously reviewed head.

## Production

Determine whether push, merge, tag or release publication automatically deploys
before any such action. Follow global `AGENTS.md` for whether that trigger is
covered by an applicable bounded release mandate or needs exact-revision
confirmation; this reference creates or extends no authority. Before the
trigger, finish recovery and verification preparation and bind the exact
deployable revision through the repository's fail-closed mechanism. If the
revision cannot be bound before the trigger, keep it pending. Do not merge first
and seek authority afterward, change deployment configuration to avoid the
boundary, or execute a second rollout after a successful automatic one.

For an automatic rollout, use the accepted pre-trigger candidate/artifact
binding; for a manual post-merge rollout, use the accepted merge/release receipt.
Never obtain the release from whatever the current checkout happens to contain.
Bind the deploy source and deployed
artifact to that immutable revision through the owning project's deployment
tool. Build and inspect outgoing artifact/configuration scope before execution.

Before a production trigger, finish the safe preparation required by global
`AGENTS.md`: accepted immutable source, required checks and independent review,
verified recovery readiness, verification, and rollback. Record the applicable
authorization provenance and action with the audit evidence. A corrected
in-scope revision does not itself end a valid mandate, but its affected checks
and review must pass for the exact revision. Changes to protected scope are
handled under global policy.

Run the repo's approved deploy, preserving protected configuration and data.
Record real install/restart/health failures; never swallow exceptions or stamp a
release marker early. Verify the installed artifact/dependency identity and
change-specific running behavior. Compare service/journal/worker/schema evidence
with the accepted baseline without exposing secrets or raw sensitive messages.

For rollback, distinguish restoring code from restoring data. Apply only the
approved plan. Follow global `AGENTS.md` before any recovery that could discard
newer writes. Retain evidence and report the actual deployed/rolled-back state
even if the requested rollout could not be completed.
