---
name: magnus-security-review
description: Comprehensive AI-powered security review of a codebase or repository. Builds a threat model, scans for vulnerabilities across OWASP Top 10 + LLM Top 10, validates findings, and proposes patches. Mirrors the workflow of Claude Code Security and Codex Security but using manual best practices.
argument-hint: "[path or scope, e.g. 'src/' or 'auth module' or 'full repo']"
---

# /security-review - AI-Powered Security Review

Perform a structured, multi-phase security review that goes beyond a simple "find vulnerabilities" prompt. This skill replicates the workflow used by dedicated security products (Claude Code Security, OpenAI Codex Security) using best practices for thorough, low-false-positive results.

## Usage

- `/security-review` - Full repo review
- `/security-review src/auth` - Review specific module
- `/security-review --diff` - Review only changed files (staged + unstaged)
- `/security-review --pr 42` - Review a specific PR diff

## Three-Phase Workflow

### Phase 1: Threat Model (understand before scanning)

**Do not skip this phase.** The biggest difference between a naive "find bugs" prompt and a real security review is context. Before looking for vulnerabilities, build a project-specific threat model.

1. **Identify the system's purpose and boundaries:**
   - Read README, CLAUDE.md, architecture docs, deployment configs
   - Identify: What does this system do? What data does it handle? Who are the users?

2. **Map trust boundaries:**
   - Where does external input enter? (HTTP endpoints, CLI args, file uploads, webhooks, MCP tools, AI agent tool calls)
   - Where does data leave? (API responses, database writes, external service calls, logs)
   - What runs with elevated privileges?

3. **Identify assets worth protecting:**
   - Authentication credentials, API keys, tokens
   - User data (PII, financial, health)
   - System access (admin panels, infrastructure)
   - AI-specific: system prompts, training data, model weights, tool permissions

4. **Generate threat model summary** using STRIDE categories:
   - **S**poofing: Can an attacker impersonate a user or system?
   - **T**ampering: Can data be modified in transit or at rest?
   - **R**epudiation: Can actions be performed without audit trail?
   - **I**nformation Disclosure: Can sensitive data leak?
   - **D**enial of Service: Can the system be overwhelmed?
   - **E**levation of Privilege: Can a user gain unauthorized access?

Write the threat model to a temporary file for reference during scanning:
```
# Threat Model: [project name]
## System Purpose: ...
## Trust Boundaries: ...
## Assets: ...
## STRIDE Analysis: ...
```

### Phase 1b: Git History Analysis (find patterns from past fixes)

**This technique found more zero-days than fuzzing in Anthropic's research.** Past security fixes reveal the codebase's weak spots.

1. **Search for security-related commits:**
   ```bash
   git log --all --oneline --grep="CVE\|fix\|vuln\|secur\|overflow\|inject\|saniti\|bounds\|crash" | head -40
   ```

2. **For each security fix found:**
   - Read the diff: what was the bug pattern?
   - Search the rest of the codebase for the **same pattern** that wasn't fixed
   - Example: if a commit fixed an unchecked `strcat` on a fixed buffer, grep for other `strcat` calls on fixed buffers

3. **Look for incomplete fixes:**
   - Was only one call site fixed when multiple exist?
   - Was the fix applied to one branch but not another?
   - Was a similar function/module left unfixed?

This works because security bugs cluster — the same class of mistake tends to repeat across a codebase.

### Phase 2: Vulnerability Scanning (systematic, not shotgun)

Use the threat model AND the git history patterns to guide targeted scanning. Check each category below, reading the actual code — do not guess or assume. **If one approach yields nothing, pivot to another** (e.g., if checklist scanning finds nothing, try deeper pattern analysis from git history).

#### A. Classic Web/API vulnerabilities (OWASP Top 10)

For each finding, note the **file, line, vulnerability type, and severity** (Critical/High/Medium/Low).

1. **Injection** (SQL, NoSQL, command, LDAP)
   - Trace all user input to database queries, shell commands, dynamic code execution
   - Check for parameterized queries vs string concatenation

2. **Broken Authentication**
   - Password hashing (bcrypt/argon2 vs MD5/SHA1/plaintext)
   - Session management (secure cookies, token expiry, rotation)
   - MFA implementation

3. **Sensitive Data Exposure**
   - Secrets in code, config, env files, git history
   - TLS configuration, HSTS headers
   - Logging of sensitive data (passwords, tokens, PII)

4. **XML/XXE** - External entity processing in XML parsers

5. **Broken Access Control**
   - IDOR (can user A access user B's resources?)
   - Missing authorization checks on endpoints
   - Directory traversal

6. **Security Misconfiguration**
   - Default credentials, debug mode in production
   - Overly permissive CORS, CSP headers missing
   - Unnecessary services/ports exposed

7. **XSS** (Reflected, Stored, DOM-based)
   - User input rendered without escaping
   - Template injection

8. **Insecure Deserialization** - Untrusted data deserialized

9. **Known Vulnerable Components**
   - Check package.json/requirements.txt/Cargo.toml for known CVEs
   - Run `npm audit`, `pip-audit`, `cargo audit` if available

10. **Insufficient Logging & Monitoring**
    - Auth failures logged? Rate limiting? Alerting?

#### B. AI/LLM-specific vulnerabilities (OWASP Top 10 for LLM 2025)

If the project uses AI/LLM components:

1. **LLM01: Prompt Injection**
   - Direct: Can users override system instructions?
   - Indirect: Can data the LLM processes (emails, documents, web content) contain hidden instructions?
   - Check for input sanitization before LLM calls

2. **LLM02: Sensitive Information Disclosure**
   - Does the system prompt contain secrets, API keys, internal URLs?
   - Can the LLM be tricked into revealing training data or context?

3. **LLM03: Supply Chain**
   - Third-party models, plugins, MCP servers — are they trusted?
   - Model provenance and integrity verification

4. **LLM04: Data Poisoning**
   - RAG data sources — can they be manipulated?
   - Fine-tuning data integrity

5. **LLM05: Improper Output Handling**
   - Is LLM output treated as trusted? (rendered as HTML, executed as code, used in SQL)

6. **LLM06: Excessive Agency**
   - What tools/permissions does the AI agent have?
   - Principle of least privilege applied?
   - Human-in-the-loop for destructive actions?

7. **LLM07: System Prompt Leakage**
   - Can the system prompt be extracted via conversation?

8. **LLM08: Vector & Embedding Weaknesses**
   - RAG pipeline: can malicious documents poison retrieval?

9. **LLM09: Misinformation** — Output validation for factual claims

10. **LLM10: Unbounded Consumption** — Rate limiting, token limits, cost controls

#### C. Memory safety & native code (C, C++, Rust unsafe)

If the project contains C, C++, or Rust `unsafe` blocks:

1. **Buffer overflows**
   - Fixed-size buffers with unchecked input (especially `strcat`, `strcpy`, `sprintf` without length limits)
   - Off-by-one errors in loop bounds and array indexing
   - Integer overflow leading to undersized allocations

2. **Use-after-free / double-free**
   - Pointers used after the memory they reference has been freed
   - Error paths that skip cleanup or free twice

3. **Bounds-checking bypasses**
   - Security checks that can be circumvented by specific input sequences
   - Even 100% line/branch coverage may not catch these — some bugs require a very specific sequence of operations to trigger

4. **Unsafe string operations**
   - Successive `strcat` on a `PATH_MAX` or fixed buffer without cumulative length tracking
   - Format string vulnerabilities

5. **Use available tools when possible:**
   - Suggest running with AddressSanitizer (`-fsanitize=address`) to catch non-crashing memory errors
   - Suggest running with UndefinedBehaviorSanitizer for undefined behavior
   - Check if the project has fuzzing infrastructure (OSS-Fuzz, libFuzzer) and whether coverage gaps exist

#### D. Infrastructure & configuration

- Dockerfile/docker-compose security (running as root, exposed ports)
- CI/CD pipeline security (secrets in logs, unsigned artifacts)
- IAM/permissions (overly broad roles)
- Network segmentation

### Phase 3: Validation & Remediation

**This is what separates good reviews from noise.** For each finding:

1. **Validate exploitability:**
   - Can this actually be triggered? Trace the full path from input to vulnerability.
   - Is there an upstream control that prevents exploitation? (middleware, framework default, WAF)
   - Mark as Confirmed / Likely / Theoretical

2. **Assess impact:**
   - What is the worst-case outcome? (RCE, data breach, DoS, privilege escalation)
   - What data/systems are affected?

3. **Prioritize** using severity x exploitability:
   - **Critical:** Confirmed + RCE or full data breach
   - **High:** Confirmed + significant data exposure or privilege escalation
   - **Medium:** Likely + limited impact, or Confirmed + low impact
   - **Low:** Theoretical or informational

4. **Propose fix** for each Confirmed/Likely finding:
   - Write the actual patch (not just advice)
   - Explain why the fix works
   - Note any trade-offs

5. **Self-critique and deduplicate:**
   - Before presenting findings, re-read each one critically: "Am I sure about this? Could I be wrong?"
   - Merge findings that are variants of the same root cause
   - Remove findings that are theoretical with no realistic attack path
   - Remove findings already mitigated by framework defaults
   - Be explicit about what you discarded and why
   - Optimizing for low false positives is more important than finding everything — noisy reports erode trust

## Output Format

Present findings as a structured report:

```markdown
# Security Review: [project/scope]
Date: [date]
Scope: [what was reviewed]

## Threat Model Summary
[2-3 paragraphs from Phase 1]

## Findings

### [CRITICAL/HIGH] Title - File:Line
**Category:** OWASP XX / LLM XX
**Status:** Confirmed / Likely
**Description:** What the vulnerability is
**Attack path:** How it can be exploited
**Impact:** What happens if exploited
**Fix:** [code patch]

### ...

## Discarded / False Positives
- [Finding] — discarded because [reason]

## Recommendations
- Prioritized list of actions
```

## Important Notes

- **Read before you scan.** Never generate findings about code you haven't read.
- **Trace, don't guess.** Follow data flow from input to sink. If you can't trace the full path, mark it as Theoretical.
- **Framework awareness.** Know what the framework handles by default (e.g., Django ORM prevents SQL injection, React escapes JSX by default). Don't flag things the framework already mitigates.
- **One repo at a time.** Don't try to review everything at once. Scope matters.
- **Re-read the threat model** before writing findings. Does each finding align with an actual threat?
