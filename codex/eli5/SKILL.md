---
name: eli5
description: Explain the previous answer, a selected topic, a technical concept, tool result, document, error, decision, or workflow in very simple language. Use when the user asks for ELI5, "förklara superenkelt", "som för en femåring", "på vanlig svenska", "make it simple", or wants a plain-language explanation of what was just explained.
---

# ELI5

Explain the requested thing in simple, everyday language.

## Core Style

- Use short sentences.
- Use common words.
- Avoid jargon unless it is the thing being explained.
- If jargon is needed, define it immediately.
- Prefer one concrete example over abstract explanation.
- Do not sound childish or patronizing.
- Do not add unrelated background.

## Workflow

1. Identify what should be simplified. If the user says "det som precis förklarades", use the previous assistant answer.
2. State the simple version first.
3. Add a small example or analogy if it helps.
4. Mention practical consequence: what the user can do or should understand from it.

## Output Shape

For a short source, default to 2-5 short sentences; match the source's length when it has several distinct points.

Use bullets only when the original topic has several parts that need separation.

If the user asks for Swedish, answer in Swedish. If the language is unclear, match the user's language.

## Guardrails

- Preserve the original claims, caveats, and conclusions. Simplify rather than summarize unless the user asks for a summary.
- Do not invent missing facts.
- For risky domains such as legal, medical, finance, tax, accounting, or security, keep the explanation simple but include the key caveat.
