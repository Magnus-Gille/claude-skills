# Debate type and lenses

Identify the debate type first and declare it as a structured field at the top of the self-review:

```markdown
## Debate Type
Primary: <security | architecture | protocol | docs | priority>
Secondary: <type, if mixed>
```

Omit `Secondary` for a single-type debate. For a mixed debate, use both lenses in primary-then-secondary order in both rounds.

## Universal self-review checklist

- [ ] What assumptions in the draft might not hold? Are they listed in the Assumptions section?
- [ ] Are the failure modes exhaustive, or just the obvious ones?
- [ ] What's the strongest argument against my own position?
- [ ] What evidence or baseline is missing?
- [ ] What operational or maintenance burden is hidden or understated?

## Security checklist

- [ ] What are the trust boundaries? What crosses them?
- [ ] What happens if an attacker controls a key input or state?
- [ ] Are auth, authz, and session-management failure modes covered?
- [ ] What's the blast radius of a compromise?
- [ ] Are secrets, keys, and credentials handled correctly throughout the lifecycle?

## Architecture checklist

- [ ] What scale, load, or data-size assumptions are baked in?
- [ ] What coupling is being introduced, and what does it preclude later?
- [ ] How does the system degrade under partial failure?
- [ ] What's the operational burden for deployment, monitoring, and incident response?
- [ ] What's the reversibility cost if this turns out to be wrong?

## Protocol/API checklist

- [ ] What are the edge cases in the protocol state machine?
- [ ] What happens to in-flight requests during failures or restarts?
- [ ] What does a client do when it gets an unexpected response?
- [ ] What's the versioning and backward-compatibility story?
- [ ] What are the timeout, retry, and idempotency semantics?

## Docs/process checklist

- [ ] What's the maintenance burden, and who keeps this updated?
- [ ] Where does this conflict with or duplicate existing documentation?
- [ ] What's the single source of truth, and is it unambiguous?
- [ ] What would a newcomer need that's missing here?

## Priority/product checklist

- [ ] What evidence supports this priority over alternatives?
- [ ] What are the opportunity costs of this choice?
- [ ] What assumptions about user or system behavior are load-bearing?
- [ ] What does "done" look like, and how would we know if it worked?
- [ ] What's the reversibility of this decision?

## Critique lenses

Every critique prompt includes this universal framing:

> Acknowledge strengths before attacking weaknesses. Be specific: cite concrete issues with file and line references, not vague concerns. Flag unsupported claims, missing baselines, and methodological gaps. Be skeptical but intellectually honest; do not strawman.

Add the matching block below. For mixed debates, include both blocks in the declared order.

### Security

> Also examine trust-boundary crossings and what validates each one; auth, authz, and session failure modes under adversarial input; blast radius if any single component is compromised; and secrets and credential handling throughout the lifecycle.

### Architecture

> Also examine scale, load, and data-size assumptions; coupling introduced and what it forecloses; degradation under partial failure; operational burden for deployment, monitoring, and incident response; and reversibility if the design is wrong.

### Protocol/API

> Also examine protocol state-machine edge cases; in-flight requests during failures or restarts; client behavior on unexpected responses; versioning and backward compatibility; and timeout, retry, and idempotency semantics.

### Docs/process

> Also examine maintenance burden and ownership; conflicts with or duplication of existing documentation; whether the single source of truth is unambiguous; and what a newcomer would need that is missing.

### Priority/product

> Also examine evidence for this priority over alternatives; opportunity costs; load-bearing assumptions about user or system behavior; what done means and how success would be measured; and reversibility.
