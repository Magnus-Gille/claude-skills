# /capture - Process Raw Capture Items

Process raw notes, voice transcriptions, and other unstructured items from the `capture/` folder into structured, properly routed files.

## Usage

- `/capture` - Process all items in `capture/`
- `/capture <filename>` - Process a specific file

## Location

The capture folder is at the mgc root: `~/mimir/mgc/capture/`

## Processing Flow

### 0. Model Check

If the current model is Opus, stop and ask the user to run `/model sonnet`, then wait for them to confirm the switch before proceeding. This skill is mostly classification + Munin writes and runs fine on Sonnet.

For each file in `capture/`:

### 1. Read & Classify

Read the raw file and determine what it is:

| Type | Signals |
|------|---------|
| Customer/partner meeting | Company names, contact names, meeting times, business discussion |
| Todo/action item | "add to todo", task-like language, deadlines |
| Event/speaking gig | Event dates, venues, audience, pricing |
| Internal note/idea | Strategy, open questions, brainstorming |

**Ask the user to confirm classification if ambiguous.**

### 2. Extract Metadata

From the raw content, extract:
- **Date:** When it happened (convert relative dates to absolute)
- **Customer/company:** Name, normalize to existing folder name if one exists
- **Contacts:** Names and roles mentioned
- **Type:** meeting, telefonsamtal, intro-möte, event, etc.
- **Tags:** Relevant topics (use existing tag conventions)

### 3. Route & Write

Based on classification:

#### Customer/partner meeting → `customers/<name>/`
- Create folder if it doesn't exist
- Write `meeting-YYYYMMDD.md` (or `meeting-YYYYMMDD-<contact>.md` if multiple meetings same day)
- Format:

```markdown
---
date: YYYY-MM-DD
time: "HH:MM–HH:MM"
customer: <name>
contacts:
  - Name (Role)
type: <meeting type>
tags: [relevant, tags]
source_file: archive/<archived-filename>
---

# Möte: <Customer/Contact>

## <Structured summary sections>

## Nästa steg

- [ ] Action items extracted from the notes
```

#### Event/speaking gig → `events/`
- Write `YYYY-MM-DD-<event-slug>.md` with same frontmatter pattern
- Include: audience, venue, duration, pricing, deliverables

#### Todo/action item → Munin
- `memory_write("tasks", "<category>", ...)` per the task architecture
- Confirm with user before writing

#### Internal note → `internal/`
- Write with frontmatter, preserve the substance

### 4. Archive Raw File

- Move raw file to `archive/` with standardized name: `YYYY-MM-DD-<slug>-raw.<ext>`
- The `source_file:` field in the processed file links back to this archive path

### 5. Update Munin (when applicable)

- **New customer?** Create or update `clients/<name>/status` in Munin
- **Existing customer with new info?** Update their Munin entry
- **Action items with deadlines?** Write to Munin `tasks/` namespace
- **Decisions made?** `memory_log` with rationale

### 6. Summary

After processing all items, show:

```
## Capture Processing Complete

### Processed
- <filename> → customers/walkingtree/meeting-20260302.md
- <filename> → events/2026-04-07-modda-sormland.md

### Archived
- archive/2026-03-02-walkingtree-raw.txt
- archive/2026-04-07-modda-sormland-raw.txt

### Munin Updates
- clients/walkingtree — created
- tasks/admin — 2 items added

### Skipped
- <filename> — reason
```

## Customer Matching

Before writing a customer meeting file, **always run `ls ~/mimir/mgc/customers/`** to get the list of existing folders. Then:

1. **Exact match** (e.g., raw notes say "Photowall" and `customers/photowall/` exists) → use existing folder.
2. **Fuzzy match** (e.g., raw notes say "Walkingtree Technologies" and `customers/walkingtree/` exists) → use existing folder, confirm with user if the match isn't obvious.
3. **No match found** → ask the user: *"No existing customer folder matches '<name>'. Create `customers/<suggested-slug>/`?"* — suggest a slug (lowercase, hyphenated) and let them confirm or rename.
4. **Multiple possible matches** → present the options and ask the user to pick.

Also check Munin `clients/` namespace — if a client entry exists there but no local folder, create the local folder to match the Munin namespace name.

## Conventions

- **Language:** Match the language of the raw notes. Swedish notes → Swedish summary. English notes → English summary.
- **Don't invent information.** If something is unclear in the raw notes, flag it with `[?]` or ask the user.
- **Preserve all action items** — extract every commitment, follow-up, or next step mentioned.
- **Keep structured but concise** — the processed file should be scannable, not a transcript.
