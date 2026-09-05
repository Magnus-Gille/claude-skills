---
name: eli5
description: Explain a previous response or requested technical topic in plain language. Use when the user asks for an ELI5 explanation or invokes /eli5; preserve the claims and match the source length.
---

# /eli5 — Explain Like I'm 5

Explain the requested source in plain language. Use the immediately previous assistant
message when the user points to the previous answer; otherwise use the named topic,
document, error, decision, or workflow.

## Rules

1. **Same content, simpler form.** Cover the same points as the selected source. Don't drop information; translate it.
2. **No jargon.** If a technical term is unavoidable, define it inline the first time. ("aider — a command-line tool that lets an AI edit code")
3. **Short sentences.** Aim for ~15 words per sentence. Break up long ones.
4. **Concrete over abstract.** Replace "harness misconfiguration" with "I was running the tool with the wrong settings."
5. **Tables stay if useful.** Numbers and comparisons survive translation; the surrounding prose gets simplified.
6. **Don't apologize or preface.** Just give the simpler explanation. No "Sure, here's an easier version:" — start with the content.
7. **Match length to the original.** A short message gets a short re-explanation. A long one gets a similarly long but simpler one. Don't pad.

## What this is NOT

- Not a summary. Cover everything, just in simpler words.
- Not dumbed-down to the point of being wrong. Accuracy stays.
- Not a different answer. Same conclusions, same recommendation.

## Example

Previous message: "The harness misconfig invalidated prior aider+qwen-coder ranking. Real picture: aider and opencode are comparable when aider has per-task file scope."

ELI5: "Earlier I had aider set up wrong, so its scores were unfairly low. With the right settings, aider does about as well as opencode — they're roughly tied."
