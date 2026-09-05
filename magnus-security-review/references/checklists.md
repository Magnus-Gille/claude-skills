# Security review checklists

Use only the sections relevant to the requested scope. These are prompts for code-grounded inspection, not a substitute for tracing a reachable attack path.

## Web, API, and application controls

- **Access control:** verify authorization at every sensitive route, object, tenant, and tool boundary; check default-deny behavior and privilege changes.
- **Authentication and session:** inspect credential validation, token/session lifetime, reset and recovery flows, MFA boundaries, replay protection, and brute-force controls.
- **Injection and output handling:** trace untrusted values into SQL, shell, templates, HTML, LDAP, path/file APIs, regular expressions, and serializers; verify context-appropriate encoding and parameterization.
- **Cryptography and secrets:** check transport/storage protection, key handling, rotation, secret sources, logs, error messages, crash dumps, and repository history.
- **Validation and resource limits:** inspect parsing, canonicalization, upload limits, pagination, rate limits, queue growth, timeout/cancellation, and cost/token ceilings.
- **Configuration and error handling:** check secure defaults, debug/admin endpoints, CORS/CSRF, security headers, error disclosure, and fail-open behavior.
- **Integrity and dependencies:** inspect lockfiles, update paths, signature/provenance checks, deserialization, generated artifacts, and dependency advisories where metadata is present.
- **Logging and monitoring:** verify security events are attributable without logging secrets or personal data; check alerting and audit-trail integrity.
- **SSRF and outbound access:** trace user-controlled URLs, redirects, DNS/IP handling, metadata endpoints, proxy rules, and egress restrictions.

## LLM, agent, MCP, and tool-use controls

- Direct and indirect prompt injection from user, web, document, memory, tool, and retrieved content.
- Sensitive prompt, context, memory, credential, and tool-result disclosure.
- Untrusted model, plugin, MCP server, skill, or instruction supply chain.
- Model output reaching code, SQL, shell, HTML, policy, file, or network sinks without validation.
- Excessive agency, missing approval boundaries, confused deputy paths, and cross-tenant/tool authorization failures.
- Unbounded token, tool-call, retry, financial, or external-side-effect consumption.
- Persistence and provenance: whether untrusted content can alter durable memory, instructions, audit records, or future behavior.
- Evaluation and fallback paths that weaken production controls or conceal failed safety checks.

## Infrastructure, deployment, CI, and IAM

- Infrastructure-as-code and deployment configuration: public exposure, network boundaries, security groups, TLS, admin ports, storage access, backups, and rollback behavior.
- CI workflows: untrusted event triggers, pull-request permissions, action pinning, artifact provenance, checkout of attacker-controlled refs, secret exposure, and shell interpolation.
- IAM: least privilege, service-account scope, role assumption, trust policies, break-glass access, token lifetime, environment separation, and human approval for consequential actions.
- Container and host boundaries: image provenance, root/capabilities, filesystem mounts, sandbox escape paths, kernel/runtime exposure, and resource limits.
- Secret management: injection into builds/deploys, masking, rotation, recovery, and accidental persistence in logs or artifacts.
- Data lifecycle: retention, deletion, backups, export paths, tenant isolation, and privacy classification.
- Observability and incident response: tamper-resistant audit events, useful alerts, and a tested recovery path.

## Native code and dependency review

- Bounds, lifetime, ownership, integer conversion, race, unsafe deserialization, format-string, and untrusted parser paths.
- Compiler hardening, sanitizer/fuzz coverage, unsafe FFI boundaries, and crash/error handling.
- Direct and transitive dependency versions, lockfile integrity, package scripts, vendored code, and known vulnerable components where package metadata is available.
