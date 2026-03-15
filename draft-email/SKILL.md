---
name: draft-email
description: Draft emails in Magnus's authentic writing style. Use when writing emails, composing messages, or when the user wants to send professional correspondence. Applies Swedish business email conventions with Magnus's characteristic warmth, structured proposals, and clear next steps.
---

# /draft-email - Write emails in Magnus's style

Draft emails that match Magnus Gille's authentic writing voice.

## Instructions

When the user invokes `/draft-email`, help them compose an email in Magnus's characteristic style.

### Step 1: Gather Information

Ask the user for:
1. **Recipient** - Who is this email to?
2. **Context** - What's the situation? (new contact, follow-up, proposal, confirmation, etc.)
3. **Key points** - What needs to be communicated?
4. **Tone preference** - Formal proposal, quick reply, or casual follow-up?

### Step 2: Reference the Style Profile

Read the style profile at `/Users/magnus/mimir/internal/magnus-email-style-profile.md` to ensure the draft matches Magnus's authentic voice.

### Step 3: Draft the Email

Apply these style rules:

**Greeting:**
- New/formal: `Hej [Förnamn],`
- Quick response: `hej!`
- Follow-up: `Hej igen,`

**Body:**
- Use short paragraphs
- Include numbered lists for proposals/options
- Add enthusiasm markers: "Kul att...", "Vad roligt!", "Toppen!"
- Reference credentials when relevant (AI champion, Scania background)
- Always include clear next steps

**Sign-off:**
- Formal: Full signature with website
- Casual: `/Magnus`

### Step 4: Present and Refine

Show the draft to the user and ask:
- "Vill du justera något?"
- "Ska jag skicka detta som utkast eller direkt?"

### Step 5: Send (optional)

If the user approves, offer to:
- Create a draft in Outlook using `mcp__microsoft-mcp__create_email_draft`
- Send directly using `mcp__microsoft-mcp__send_email`

**Account ID:** `00000000-0000-0000-6a32-5c08862b7b5c.9188040d-6c67-4c5b-b112-36a304b66dad`

## Example Invocations

- `/draft-email` - Interactive mode, asks for details
- `/draft-email svar till Hanna om föreläsning` - Draft a reply about a lecture
- `/draft-email proposal för nytt uppdrag` - Draft a new business proposal

## Style Quick Reference

| Situation | Greeting | Length | Sign-off |
|-----------|----------|--------|----------|
| Cold outreach | Hej! | Medium | Full signature |
| Proposal | Hej [Name], | Long, structured | Full signature |
| Quick confirmation | hej! | 1-3 sentences | /Magnus |
| Problem resolution | Hej!, then action | As needed | Full signature |
| Follow-up | Hej igen, | Short | Vänligen, |
