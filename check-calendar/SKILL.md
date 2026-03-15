---
name: check-calendar
description: Check calendar, find available dates, verify if specific dates work, or see upcoming events. Use whenever the user mentions calendar, scheduling, availability, dates, or asks "does [date] work?" or "when am I free?". Routes MCP data through a subagent to keep main context clean.
---

# /check-calendar - Check calendar and availability

Check calendar events and find available dates without flooding the main conversation context.

## Instructions

When the user asks about their calendar — whether checking availability, verifying specific dates, or browsing upcoming events — follow these steps.

### Step 1: Determine the Query Type

Parse the user's request into one of these patterns:

| Request Pattern | Action |
|----------------|--------|
| "check my calendar", "what's coming up?" | List events for the next 7-14 days |
| "does March 25 work?", "am I free on [date]?" | Check specific date(s) for conflicts |
| "when am I free in March?" | Scan a month and identify open dates |
| "check calendar mars-april" | Scan a date range |
| "next week", "nästa vecka" | List events for next 7 days |

### Step 2: Calculate the Date Range

Based on today's date and the user's request:
- **Specific dates:** Calculate `days_ahead` to cover those dates plus a few buffer days
- **Month scan:** Calculate `days_ahead` to cover the entire target month(s)
- **General check:** Default to `days_ahead: 14`
- **If looking back:** Use `days_back` for recent events

Formula: `days_ahead = (last day of target period) - (today's date) + 3 buffer days`

### Step 3: Route Through a Subagent

**CRITICAL:** Always use the Task tool with `subagent_type: "general-purpose"` to fetch and process calendar data. This prevents large MCP responses from filling up the main conversation context.

Launch the subagent with a prompt like:

```
Check calendar using the Microsoft MCP tools.

Account ID: 00000000-0000-0000-6a32-5c08862b7b5c.9188040d-6c67-4c5b-b112-36a304b66dad
Today's date: [current date]

Task: [describe what the user wants — specific date check, month scan, general overview, etc.]

Use `mcp__microsoft-mcp__list_events` with:
- days_ahead: [calculated value]
- days_back: [0 unless looking back]
- include_details: true

Analysis rules:
1. Filter out events where Magnus has DECLINED the invitation
2. Convert UTC times to Swedish time (CET: UTC+1 in winter Oct-Mar, CEST: UTC+2 in summer Mar-Oct)
3. Categorize events:
   - isAllDay=true or "heldag"/"blocker" in subject → blocks full day
   - Multi-day events → block ALL days in range
   - Multi-hour daytime events → likely blocks the day
   - Short appointments (30-60 min) → does NOT block the day
   - Evening events (after 17:00) → does NOT block daytime
   - Recurring admin tasks → does NOT block the day
4. Exclude weekends unless explicitly asked
5. Account for Swedish holidays (röda dagar): 1 jan, 6 jan, långfredagen, påsk, 1 maj, Kristi himmelsfärd, 6 juni, midsommar, alla helgons dag, 24-26 dec, 31 dec

Return a CONCISE summary in this format:

## Calendar Summary ([period])

### Blocked days:
- [Date] ([weekday]): [Event name]

### Partially busy (but flexible):
- [Date] ([weekday]): [Event] ([time])

### [If checking specific dates]:
- **[Date]: [FREE/BUSY]** — [reason if busy]

### [If scanning for availability]:
### Available days:
- [Date] ([weekday])
- [Date] ([weekday])

Recommend Tuesday-Thursday for business meetings. Flag days adjacent to travel/multi-day events as potentially unsuitable.
```

### Step 4: Present Results

Take the subagent's summary and present it to the user. Add context if relevant:
- If dates were proposed in an email, connect the dots ("Both dates Jane proposed are free")
- If multiple options exist, suggest the best ones (mid-week preferred for business)

### Step 5: Offer Next Actions

Based on context:
- "Ska jag svara med dessa datum?"
- "Vill du att jag skapar en kalenderhändelse?"
- "Ska jag kolla tillgängligheten för de andra deltagarna också?"

## Example Invocations

- `/check-calendar` — Overview of the next 2 weeks
- `/check-calendar mars` — Scan March for availability
- `/check-calendar mars-april` — Scan March and April
- `/check-calendar 25-26 mars` — Check specific dates
- `/check-calendar nästa vecka` — Next week's events
- Natural language: "check my calendar", "does March 25 work?", "when am I free next week?", "am I available on Thursday?"

## Account Information

**Account ID:** `00000000-0000-0000-6a32-5c08862b7b5c.9188040d-6c67-4c5b-b112-36a304b66dad`

**Timezone:** Events are returned in UTC. Convert to Swedish time:
- **Vintertid (CET):** UTC+1 — sista söndagen i oktober till sista söndagen i mars
- **Sommartid (CEST):** UTC+2 — sista söndagen i mars till sista söndagen i oktober

## Integration with Other Skills

- Use `/check-email` if the user needs to cross-reference calendar with email proposals
- Use `/draft-email` to reply with availability
