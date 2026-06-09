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
- **A draft is not proof of an unsent obligation.** Outlook leaves a lingering draft *twin* when you save-then-send, and old drafts from long-resolved threads persist forever. Because drafts are fetched with **no date filter**, a draft from months ago surfaces as "action owed" even though the offert was sent and the deal closed *outside* the window (Uddevalla: a March offert+acceptance was invisible to an April-onward window, so the March draft looked unsent). And a draft can carry a *newer* `lastModifiedDateTime` than a real sent reply in the same thread, making the sent reply look absent (Saab: an empty draft shadowed a substantive sent reply from the same morning).
- **The date window clips conversations.** The window is a *discovery* filter for finding candidates, not the boundary of a conversation. A thread that looks open inside the window is frequently resolved by sent/received messages just outside it.
- **A deliverable is often sent as a *new* thread, not a reply.** Magnus answers a request by composing a fresh email with a new subject — so it has a *different* `conversationId` than the request and the lingering draft. ConversationId grouping alone never connects them, so the request looks unanswered and the draft looks unsent (Photowall: the planning-meeting invite + an "Underlag inför vårt samtal" draft looked open, but the material had been sent May 31 as "AI-utbildningar Photowall — upplägg & förslag (juni)" — a separate thread to the same person). **Cure: reconcile by counterparty, not just by conversationId.**
- **The agent has no clock — it guesses dates.** Without today's date stated explicitly, the subagent invents relative deadlines ("passed yesterday", "overdue") and gets them wrong (AFRY: a June-5 deadline was called overdue on June 3). Today's date must be injected, and every deadline claim must show the arithmetic.
- **Editorial nudges masquerade as obligations.** The agent likes to add prophylactic "worth confirming X soon" actions that no inbound message actually asked for, inflating the owed-list with invented work (Traton: "confirm final agenda" — nobody asked). Only a *quotable inbound request* is an obligation.

**Rule: never emit a verdict on a thread without reconstructing the full conversation by `conversationId` across all folders AND across all dates (re-fetch ignoring the window), reconciling against everything Magnus sent the same counterparty (even under a different subject), and reading the actual body of its last *real* (non-draft, or reconciled) message.**

## Account

Pick the mailbox from the request (ask if ambiguous; default Outlook):

**Outlook `magnus.gille@outlook.com` (default)** — the full methodology in Steps 0–2 below targets this account.
- Tool: the **`m365` CLI**, raw Graph API form: `m365 request --url "<url>" -m get`. Do NOT use Microsoft MCP tools (removed).
- Folders: `inbox`, `sentitems`, `drafts`, `junkemail`, `archive` (Magnus archives processed mail — include it).

**iCloud `magnus@gille.ai`** — triage via the `himalaya` CLI. See **the gille.ai section** at the end; the Graph-specific mechanics (conversationId grouping, OData `$filter`/`$search`, draft-twin reconciliation) do NOT transfer, but the *judgment principles* do.

If the user says "both"/"all my email", run both passes and label each section by account.

## Step 0: Auth

Run:
```bash
m365 request --url "https://graph.microsoft.com/v1.0/me" --query "userPrincipalName" 2>&1
```
If it does not return `"magnus.gille@outlook.com"`, tell the user to run `/m365-auth` (or `! m365 login --authType deviceCode --appId e713ead2-4455-4d86-86ec-bd4dcde333cd --tenant common`) and stop. Do not loop on auth errors.

## Step 1: Route through a subagent

**Before launching, compute today's date** with `date "+%Y-%m-%d (%A)"` and **inject it into the subagent prompt verbatim** (e.g. "Today is 2026-06-03 (Wednesday)"). The subagent has no reliable clock — if you don't tell it, it will guess relative deadlines and get them wrong.

Email JSON is large (~10–15k tokens/page). Always run the fetch + analysis inside a `Task` subagent (`subagent_type: general-purpose`, `model: sonnet` — this is mechanical work, Sonnet is sufficient and conserves quota). Give it the methodology below verbatim. The subagent returns only the final structured report.

For a large window or many candidate threads, the subagent may itself fan out: one cheap pass to build the candidate list, then per-candidate full-body verification. Keep raw JSON in `/tmp` files parsed with `python3` — never in any context window.

## Step 2: Methodology the subagent MUST follow

### 2a. Fetch (all folders, full window)

For each of `inbox`, `sentitems`, `drafts`, `junkemail`, `archive`, fetch messages in the window. Use `$select=subject,from,toRecipients,sender,receivedDateTime,sentDateTime,lastModifiedDateTime,conversationId,isRead,isDraft,bodyPreview` and `$top=100`, `$orderby` on the relevant date desc. (`lastModifiedDateTime` is required to time-order drafts, which have no `sentDateTime`.) Date filter examples (keep `$` escaped as `\$` in the shell):

```
inbox/sent/junk/archive:  \$filter=receivedDateTime ge <ISO> and receivedDateTime le <ISO>
sentitems:                \$filter=sentDateTime ge <ISO> and sentDateTime le <ISO>
```
Page through `@odata.nextLink` until exhausted (cap ~400 inbox rows). Write each folder's rows to `/tmp/triage_<folder>.json`.

### 2b. Group by conversation

Load all rows. Group every message — across all five folders — by `conversationId`. For each conversation compute:

- `last_msg`: the message with the maximum timestamp across **all folders**. Use `sentDateTime` for sentitems, `receivedDateTime` for inbox/junk/archive, and **`lastModifiedDateTime` for drafts** (drafts have no `sentDateTime` — using it ranks every draft as epoch/null and breaks ordering, OR treats it as latest; both are wrong).
- `last_real_msg`: same as `last_msg` but **excluding drafts** — the most recent actually-sent or actually-received message. This, not the draft, is what 2d judges.
- `latest_sent`: among `sentitems` messages in this conversation, the max `sentDateTime`.
- `last_direction`: `inbound` if `last_real_msg` is in inbox/junk/archive and from someone other than Magnus; `outbound` if in sentitems; (a draft never sets direction on its own — see draft reconciliation in 2c).
- `has_unsent_draft`: any message for this conversationId in `drafts`.

### 2c. First-pass classification (preview only — provisional)

- `outbound` last + no draft → **provisionally CLOSED** (Magnus replied last).
- `inbound` last → **CANDIDATE-OPEN** — must be verified in 2d before any verdict.
- A `draft` exists in the conversation → **reconcile it first** (below). Only a genuinely-unsent draft becomes **DRAFT-PENDING**.
- Pure newsletter/automated/no-reply sender (substack, *noreply*, *no-reply*, notification@, marketing domains) → **NOISE**, count only.

**Draft reconciliation (do this before trusting any draft).** A draft is **DRAFT-PENDING** (genuinely unsent — surface it, high value) ONLY if *both* hold:
  1. No `sentitems` message in the same conversation is newer than the draft's `lastModifiedDateTime` (`latest_sent` ≤ draft time). If a sent reply is newer, the draft is stale — ignore it; the thread was answered.
  2. The draft is not a **twin** of an already-sent message — i.e. there is no `sentitems` message with the same/near-identical subject sent within ~30 min of the draft's creation. Save-then-send leaves this twin behind.
If either fails, the draft is a **leftover** — discard it from the analysis and judge the conversation by `last_real_msg`. (Saab: empty draft, newer mtime, but a substantive sent reply existed the same morning → leftover. Uddevalla: a sent offert twin existed → leftover.)

A provisionally-CLOSED thread is NOT reported as open. But if its last outbound was Magnus *asking a question* and there is a later inbound answer you missed, the grouping in 2b already handles it (the inbound would be `last_real_msg`). Trust the chronology, not the folder.

### 2c-bis. Full-conversation reconstruction (MANDATORY for every candidate — ignores the window)

The date window only *discovers* candidates; it does not bound conversations. For **every** conversation that is CANDIDATE-OPEN or DRAFT-PENDING, before emitting any verdict, re-fetch its ENTIRE history across all folders with **no date filter**:
```
m365 request --url "https://graph.microsoft.com/v1.0/me/messages?\$filter=conversationId eq '<id>'&\$select=subject,from,toRecipients,sentDateTime,receivedDateTime,lastModifiedDateTime,isDraft,parentFolderId,bodyPreview&\$top=100&\$orderby=receivedDateTime desc" -m get
```
Rebuild the true chronology from this full result, redo the draft reconciliation against it, and only then apply 2d. A thread that looks open inside the window is frequently resolved by sent/received messages just outside it. (Uddevalla: window was Apr 21+, but the offert was sent, accepted, and acknowledged Mar 23–30 — all invisible until the full conversation is pulled, leaving only the orphan March draft to mislead.)

### 2c-ter. By-counterparty reconciliation (MANDATORY — catches deliverables sent as a new thread)

ConversationId grouping misses the most common "looks open but isn't" case: Magnus answered by composing a **fresh email with a new subject**, so the reply lives under a *different* `conversationId` than the request and the draft. For **every** CANDIDATE-OPEN and DRAFT-PENDING thread, before judging, search everything Magnus *sent* to that counterparty — by email address and by domain — with **no conversationId filter**:
```
m365 request --url "https://graph.microsoft.com/v1.0/me/mailFolders/sentitems/messages?\$search=\"<counterparty-email-or-name>\"&\$select=subject,toRecipients,sentDateTime,bodyPreview,conversationId&\$top=25&\$orderby=sentDateTime desc" -m get
```
(Also try the bare domain, e.g. `"photowall.com"`, and the person's display name — `$search` matches recipients and body.) Then:
- If Magnus sent that counterparty a **substantive message after the inbound request** — even under an unrelated subject — the obligation is very likely **already discharged**. Open the body of that sent message and confirm it actually delivers what was asked; if so the thread is **CLOSED**, and any lingering draft is a **leftover**. (Photowall: request + draft "Underlag inför vårt samtal" looked open; a `$search="photowall.com"` of sent items surfaces "AI-utbildningar Photowall — upplägg & förslag (juni)" sent May 31 with the material attached → CLOSED, draft is leftover.)
- Only if **no** substantive sent message to that counterparty exists after the request does the thread stay a candidate for 2d.

This step is cheap (one search per counterparty) and prevents the highest-embarrassment error: telling Magnus to do something he already did.

### 2d. Mandatory full-body verification for every CANDIDATE-OPEN

For each CANDIDATE-OPEN conversation, fetch the **full `body.content`** of its last 1–3 messages:
```
m365 request --url "https://graph.microsoft.com/v1.0/me/messages/<id>?\$select=subject,from,toRecipients,sentDateTime,receivedDateTime,body" -m get
```
Then judge from the *actual text*, accounting for quoted history:

- Read the quoted chain in the body. If Magnus's substantive reply appears in the quoted text after the question, the thread is **CLOSED** (mobile-rolled reply). This is the single most common false positive — check it every time.
- If the last inbound message is a **closure/acknowledgement** ("thanks, will get back to you", "no rush", "I'll fix it", "we accept the offer / see you then", a testimonial, a thank-you with no ask) → **CLOSED** or **COURTESY-OPTIONAL** (a one-line ack would be polite but nothing substantive is owed). Say which.
- If the last inbound message contains a **direct question, a request for a decision/document, or scheduling that needs Magnus's input** and no later outbound/draft answers it → **OPEN — action owed**. You MUST be able to **quote the exact sentence** that constitutes the ask. Put that verbatim quote in the report. No quote → not "action owed".
- If the other party explicitly said the next move is theirs ("I'll come back to you") → **OPEN — awaiting them, not Magnus**; nothing owed.

**No invented obligations.** "Action owed" is reserved for things an inbound message *actually asked for*, with a quotable sentence. Do NOT manufacture prophylactic actions — "worth confirming the agenda soon", "might be good to check in", "should send materials closer to the date" — when nothing was requested. A confirmed booking with no open question is **Awaiting the other party**, not action owed. If you genuinely think a proactive nudge would help but nothing was asked, it does not belong in this report at all; the user asked what they *owe*, not what might be nice. (Traton: "confirm final agenda" was invented — Charlotte asked nothing — and must NOT appear under Action owed.)

**Date arithmetic, never date vibes.** Today's date was given to you at the top of this prompt. For any deadline, scheduling, or "overdue"/"passed"/"upcoming" claim, compute it explicitly: state the deadline date, today's date, and the signed day delta (e.g. "deadline 2026-06-05, today 2026-06-03 → 2 days away, NOT overdue"). Never write "passed", "overdue", "yesterday", or "this week" without that arithmetic behind it. (AFRY: June-5 deadline on June-3 is 2 days out — flagging it "overdue" was a clock-less guess.)

Never downgrade a verdict to "open/needs reply" without having read the body of the last message. Never upgrade to "closed" purely because a `sentitems` row exists with a matching subject — verify it is actually later than the last inbound and actually answers it.

### 2e. Junk scan

In `junkemail`, flag only items that are real correspondence: a named person, a business, or anything touching Magnus's work — **MGC AB** (AI consultancy), **drone-lab** (Vinnova, LiU, kommun, FFK, Carmenta), invoices, account-security mails, or cold outreach that references his actual repos/work specifically. Everything else → spam count only. Account-security mails (password resets he may not have initiated) are always surfaced.

## Step 3: Output

Return exactly this structure, newest-first within each section, every bullet 1–2 lines, with the **date and the evidence** for the verdict:

```
## Action owed by Magnus
- **[Subject]** — [Name], [date]. Owed: [exact action]. Their ask (verbatim): "[quoted sentence]". (verified: last msg body read + by-counterparty sent check)

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
5. **Drafts are findings — but reconcile before surfacing.** A genuinely unsent draft is high-value. A lingering *twin* of an already-sent message, or a draft on a thread that later resolved, is noise. Time-order drafts by `lastModifiedDateTime` (never `sentDateTime`), and check for a newer or twin sent message in the same conversation before calling a draft "unsent".
6. **The window discovers candidates; it does not bound conversations.** For every candidate, re-fetch the full conversation by `conversationId` with no date filter before judging — the resolving messages often sit just outside the window.
7. **Sonnet subagent, raw JSON to /tmp.** Keep the main context clean; this is mechanical work.
8. **Be honest about uncertainty.** If a thread genuinely can't be resolved from available data, say "UNCLEAR — needs human eyes", don't guess a verdict.
9. **Reconcile by counterparty, not just by conversationId.** A reply or deliverable sent as a new-subject thread has a different conversationId. Before flagging any thread open, `$search` sent items for that person/domain — an answer sent under another subject still closes the obligation.
10. **Every "Action owed" carries a verbatim quote; no invented work.** If you can't quote the inbound sentence that asks for it, it isn't owed. Prophylactic nudges nobody requested do not belong in the report.
11. **Date arithmetic, never date vibes.** Today's date is injected at the top of the subagent prompt. Show the day-delta for every deadline claim; never write "overdue"/"passed"/"yesterday" without it.

## gille.ai triage (iCloud via himalaya)

For the `magnus@gille.ai` mailbox the **principles are identical** — reconstruct the whole thread, read the actual body before any verdict, reconcile against what Magnus sent the counterparty (even under a new subject), quote the inbound ask, no invented obligations, date arithmetic not vibes. What changes is the mechanics:

- **No `conversationId` and no OData.** IMAP threads by `References`/`In-Reply-To` headers. himalaya groups loosely by subject in the list; reconstruct a thread by reading messages and matching subject + participants + `References`, not by an ID field.
- **Tooling.** Still route through a Sonnet subagent. Inject today's date. Commands (append `2>/dev/null`):
  - List a folder: `himalaya envelope list -a gille -f INBOX 2>/dev/null` (folders: `INBOX`, `"Sent Messages"`, `Drafts`, `Archive`, `Junk`, `"Deleted Messages"`).
  - Filter (query is positional, no `--`): `himalaya envelope list -a gille -f INBOX not flag seen 2>/dev/null`, or `from <x>`, `subject <x>`, `after <yyyy-mm-dd>`, `before <yyyy-mm-dd>`, combined with `and`/`or`/`not`, plus `order by date desc`.
  - Read full body: `himalaya message read -a gille <ID> 2>/dev/null`.
  - For machine parsing, add `--output json` and parse with `python3`/`jq` in the subagent.
- **By-counterparty reconciliation** = list `"Sent Messages"` and search for that person/domain (`-- from`/`-- subject`, or fetch JSON and filter recipients in python) — a deliverable sent as a new thread still closes the obligation.
- **Drafts:** check the `Drafts` folder; a draft is only "unsent" if no later sent message to the same counterparty exists. Same leftover/twin logic, judged by reading rather than by `lastModifiedDateTime`.
- **Volume is low** (~tens of messages, not hundreds), so a single subagent pass over INBOX + Sent + Drafts + Junk is enough — no `@odata.nextLink` paging, no `/tmp` JSON sharding required unless a folder is unexpectedly large.
- **Output:** same Step 3 structure and Step 4 next-actions; offer `/draft-email` (it knows the gille.ai send path) for anything owed.
