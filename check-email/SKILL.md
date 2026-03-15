---
name: check-email
description: Check emails, search for messages from a specific sender or topic, look up email threads, or review inbox. Use whenever the user mentions email, messages, inbox, or asks about correspondence from someone. Routes MCP data through a subagent to keep main context clean.
---

# /check-email - Check and search emails

Search, filter, and summarize emails without flooding the main conversation context.

## Instructions

When the user asks about email — whether it's a general inbox check, a search for specific messages, or a question like "did X email me?" — follow these steps.

### Step 1: Determine the Query Type

Parse the user's request into one of these patterns:

| Request Pattern | Action |
|----------------|--------|
| "check my email", "any new emails?" | General inbox scan (list_emails, limit 10) |
| "emails from sylog", "did Jane email me?" | Search by sender (search_emails with sender name) |
| "emails about invoice", "messages about workshop" | Search by topic (search_emails with keyword) |
| "check email 20" or a specific count | General inbox scan with custom limit |
| "unread emails" | General scan, filter isRead=false |

### Step 2: Route Through a Subagent

**CRITICAL:** Always use the Task tool with `subagent_type: "general-purpose"` to fetch and process email data. This prevents large MCP responses (~10-15k tokens) from filling up the main conversation context.

Launch the subagent with a prompt like:

```
Search/check emails using the Microsoft MCP tools.

Account ID: 00000000-0000-0000-6a32-5c08862b7b5c.9188040d-6c67-4c5b-b112-36a304b66dad

Task: [describe what the user wants — inbox check, search for sender, topic search, etc.]

Use `mcp__microsoft-mcp__list_emails` for general inbox checks or `mcp__microsoft-mcp__search_emails` for specific searches.

For general inbox checks, also check sent items (folder: "sentitems", limit: 20) to identify which emails have already been replied to. Compare by conversationId.

Return a CONCISE summary in this format:

## Email Summary

### Needs Reply:
- **[Subject]** — From: [Name], [relative date]. [1-line preview if relevant]

### Already Replied:
- **[Subject]** — From: [Name], replied [date]

### Newsletters/Automated (no reply needed):
- [Subject] — [Sender]

### Key Details:
[If a specific email was searched for, include the essential content: what they said, any dates proposed, any action items. Keep it to 3-5 lines max.]

Categorization rules:
- Newsletters: known bulk senders (substack, lakera.ai, etc.) → no reply needed
- Automated: subject contains "noreply", "notification" → no reply needed
- Meeting invites: @odata.type contains "eventMessage" → maybe (respond via calendar)
- Personal/Business: direct from a person → likely needs reply
- Already replied: conversationId matches a sent item → note as replied
```

### Step 3: Present Results and Offer Actions

Take the subagent's summary and present it to the user. Then offer next steps:

- "Vill du läsa något av dessa mejl i detalj?"
- "Ska jag hjälpa dig svara på något?"
- If calendar dates are mentioned in emails: "Ska jag kolla kalendern för de föreslagna datumen?"

### Step 4: Handle Follow-up Requests

If the user wants to read a specific email in full, draft a reply, or take action:
- Use `mcp__microsoft-mcp__get_email` for full email content (also route through subagent if the email body is likely large)
- Use `/draft-email` for composing replies
- Use `/check-calendar` if scheduling is involved

## Example Invocations

- `/check-email` — Check last 10 emails
- `/check-email 20` — Check last 20 emails
- `/check-email unread` — Only show unread emails
- `/check-email from:jane.stenius@sylog.se` — Search by sender
- `/check-email sylog` — Search for emails mentioning "sylog"
- Natural language: "check my email", "any emails from Sylog?", "did Jane reply?"

## Account Information

**Account ID:** `00000000-0000-0000-6a32-5c08862b7b5c.9188040d-6c67-4c5b-b112-36a304b66dad`
**Folders:** `inbox`, `sentitems`, `drafts`, `deleteditems`

## Integration with Other Skills

- Use `/draft-email` to compose replies to emails identified here
- Use `/check-calendar` if email requests meeting scheduling
