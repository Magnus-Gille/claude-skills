---
name: email-triage
description: Reliable conversation-level email triage over a date range. Identifies genuinely open threads, emails that actually need a reply, and real correspondence hiding in junk — by reconstructing each conversation across inbox + sent + drafts + junk before judging, so mobile-quoted or already-sent replies are never mis-flagged. Use for "what's still open / what do I owe a reply / anything missed" over weeks or months.
---

# /email-triage — Reliable conversation-level email triage

`/check-email` is for quick inbox glances. **This skill is for trustworthy backlog triage** over a long window (weeks/months), where the cost of a wrong verdict is real (chasing a closed deal, missing a live one).

## The failure mode this skill exists to prevent

Naive triage judges a thread from one message's `bodyPreview`. That is wrong because:

- **Mobile replies roll into quoted text.** A reply Magnus sent from his phone often does *not* appear as a separate `sentitems` row in the window — it lives inside the quoted body of a later message. Judging by inbox rows alone makes resolved threads look open.
- **The last *inbound* message is not the same as an open obligation.** Martin/Saab, Koenigsegg, William — all were flagged "needs Magnus" when Magnus had already replied (or the ball was explicitly in the other party's court).
- **`bodyPreview` truncates before the resolution.** "Thanks for this — will get back within 1–2 weeks" reads as a question in preview; the closure is past the cutoff.

**Rule: never emit a verdict on a thread without reconstructing the full conversation by `conversationId` across all folders and reading the actual body of its last message.**

## Account

- Account: `magnus.gille@outlook.com`
- Tool: the **`m365` CLI**, raw Graph API form: `m365 request --url "<url>" -m get`. Do NOT use Microsoft MCP tools (removed).
- Folders: `inbox`, `sentitems`, `drafts`, `junkemail`, `archive` (Magnus archives processed mail — include it).

## Step 0: Auth

Run:
```bash
m365 request --url "https://graph.microsoft.com/v1.0/me" --query "userPrincipalName" 2>&1
```
If it does not return `"magnus.gille@outlook.com"`, tell the user to run `/m365-auth` (or `! m365 login --authType deviceCode --appId e713ead2-4455-4d86-86ec-bd4dcde333cd --tenant common`) and stop. Do not loop on auth errors.

## Step 1: Route through a subagent

Email JSON is large (~10–15k tokens/page). Always run the fetch + analysis inside a `Task` subagent (`subagent_type: general-purpose`, `model: sonnet` — this is mechanical work, Sonnet is sufficient and conserves quota). Give it the methodology below verbatim. The subagent returns only the final structured report.

For a large window or many candidate threads, the subagent may itself fan out: one cheap pass to build the candidate list, then per-candidate full-body verification. Keep raw JSON in `/tmp` files parsed with `python3` — never in any context window.

## Step 2: Methodology the subagent MUST follow

### 2a. Fetch (all folders, full window)

For each of `inbox`, `sentitems`, `drafts`, `junkemail`, `archive`, fetch messages in the window. Use `$select=subject,from,toRecipients,sender,receivedDateTime,sentDateTime,conversationId,isRead,isDraft,bodyPreview` and `$top=100`, `$orderby` on the relevant date desc. Date filter examples (keep `$` escaped as `\$` in the shell):

```
inbox/sent/junk/archive:  \$filter=receivedDateTime ge <ISO> and receivedDateTime le <ISO>
sentitems:                \$filter=sentDateTime ge <ISO> and sentDateTime le <ISO>
```
Page through `@odata.nextLink` until exhausted (cap ~400 inbox rows). Write each folder's rows to `/tmp/triage_<folder>.json`.

### 2b. Group by conversation

Load all rows. Group every message — across all five folders — by `conversationId`. For each conversation compute:

- `last_msg`: the message with the maximum timestamp (use `sentDateTime` for sent/drafts, `receivedDateTime` otherwise) across **all folders**.
- `last_direction`: `inbound` if `last_msg` is in inbox/junk/archive and from someone other than Magnus; `outbound` if in sentitems; `draft` if in drafts.
- `has_unsent_draft`: any message for this conversationId in `drafts`.

### 2c. First-pass classification (preview only — provisional)

- `outbound` last + no draft → **provisionally CLOSED** (Magnus replied last).
- `draft` exists as the latest → **DRAFT-PENDING** (unsent reply sitting in drafts — surface this; it is high value).
- `inbound` last → **CANDIDATE-OPEN** — must be verified in 2d before any verdict.
- Pure newsletter/automated/no-reply sender (substack, *noreply*, *no-reply*, notification@, marketing domains) → **NOISE**, count only.

A provisionally-CLOSED thread is NOT reported as open. But if its last outbound was Magnus *asking a question* and there is a later inbound answer you missed, the grouping in 2b already handles it (the inbound would be the last_msg). Trust the chronology, not the folder.

### 2d. Mandatory full-body verification for every CANDIDATE-OPEN

For each CANDIDATE-OPEN conversation, fetch the **full `body.content`** of its last 1–3 messages:
```
m365 request --url "https://graph.microsoft.com/v1.0/me/messages/<id>?\$select=subject,from,toRecipients,sentDateTime,receivedDateTime,body" -m get
```
Then judge from the *actual text*, accounting for quoted history:

- Read the quoted chain in the body. If Magnus's substantive reply appears in the quoted text after the question, the thread is **CLOSED** (mobile-rolled reply). This is the single most common false positive — check it every time.
- If the last inbound message is a **closure/acknowledgement** ("thanks, will get back to you", "no rush", "I'll fix it", "we accept the offer / see you then", a testimonial, a thank-you with no ask) → **CLOSED** or **COURTESY-OPTIONAL** (a one-line ack would be polite but nothing substantive is owed). Say which.
- If the last inbound message contains a **direct question, a request for a decision/document, or scheduling that needs Magnus's input** and no later outbound/draft answers it → **OPEN — action owed**, and state exactly what is owed.
- If the other party explicitly said the next move is theirs ("I'll come back to you") → **OPEN — awaiting them, not Magnus**; nothing owed.

Never downgrade a verdict to "open/needs reply" without having read the body of the last message. Never upgrade to "closed" purely because a `sentitems` row exists with a matching subject — verify it is actually later than the last inbound and actually answers it.

### 2e. Junk scan

In `junkemail`, flag only items that are real correspondence: a named person, a business, or anything touching Magnus's work — **MGC AB** (AI consultancy), **drone-lab** (Vinnova, LiU, kommun, FFK, Carmenta), invoices, account-security mails, or cold outreach that references his actual repos/work specifically. Everything else → spam count only. Account-security mails (password resets he may not have initiated) are always surfaced.

## Step 3: Output

Return exactly this structure, newest-first within each section, every bullet 1–2 lines, with the **date and the evidence** for the verdict:

```
## Action owed by Magnus
- **[Subject]** — [Name], [date]. Owed: [exact action]. (verified: last msg body read)

## Awaiting the other party (no action owed)
- **[Subject]** — [Name], [date]. They said: [closure/next-move quote].

## Courtesy-optional (closed; a one-liner would be polite)
- **[Subject]** — [Name], [date]. [why it's substantively closed]

## Unsent drafts (you started a reply and didn't send)
- **[Subject]** — to [Name], drafted [date].

## Missed in junk (real, not spam)
- **[Subject]** — [sender], [date]. Why it matters: [...]

## Noise
- ~N newsletters/automated; ~M junk spam — nothing actionable.
```

If a section is empty, write "None."

End with a short **Time-sensitive** call-out listing only items with a real deadline (expiry, scheduling that will pass, payment due).

## Step 4: Offer next actions

- Offer to `/draft-email` replies for the "Action owed" set.
- If anything is scheduling-related, offer `/check-calendar` before drafting.
- Offer to send the courtesy one-liners as a batch if the user wants the inbox clean.

## Key rules

1. **Conversation, never message.** Every verdict is per `conversationId`, computed across inbox+sent+drafts+junk+archive.
2. **Read the body before flagging.** No "needs reply" verdict from `bodyPreview` alone — ever.
3. **Last-sender ≠ obligation.** Distinguish "inbound last" from "Magnus owes something". State who the ball is with.
4. **Mobile-quoted replies are the #1 false positive.** Always inspect quoted text of the last inbound message for an already-sent answer.
5. **Drafts are findings.** An unsent draft is more urgent than an unread inbound — always surface.
6. **Sonnet subagent, raw JSON to /tmp.** Keep the main context clean; this is mechanical work.
7. **Be honest about uncertainty.** If a thread genuinely can't be resolved from available data, say "UNCLEAR — needs human eyes", don't guess a verdict.
