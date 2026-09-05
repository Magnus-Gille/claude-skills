---
name: presentify
description: Create a self-contained HTML one-page briefing from supplied material.
---

# Presentify

## Core Workflow

1. Locate and read the source material. If the user provides a folder, search for the named file from that folder first. If duplicates exist, compare hashes or timestamps and state which copy is used.
2. Extract the presentation spine:
   - title and audience
   - executive message in one sentence
   - key facts supported by the source
   - sections appropriate to the audience and material
   - risks, data gaps, and next actions when relevant
3. Run a separate error-review pass before writing the final page. For detailed checks, read `references/review-checklist.md`.
4. If the user gives a style-reference URL or brand page, inspect it before designing. Capture reusable signals: color palette, typography feel, spacing density, section patterns, card style, footer/header style, and CTA treatment. Do not copy restricted assets unless the user explicitly provides permission and the asset is appropriate to reuse.
5. Build a self-contained HTML file. Prefer a single page that works from `file://` with no build step. Use `assets/onepager-template.html` as a starting point when useful.
6. Validate the output:
   - HTML parses without obvious errors.
   - CSS is embedded or reliably local.
   - The page is compact at desktop width and usable on mobile.
   - Any material errors or gaps are visible and distinct from the executive summary.
   - Visually inspect the rendered page at desktop and mobile widths before calling it complete.
   - The final file is saved in the appropriate deliverables folder, usually `outputs/` for projectless sessions.
7. Open or hand off the file according to the user request. If they ask to see it in Safari, use the local file path with Safari.

## Recommended One-Page Structure

Choose only the elements supported by the source and useful to the audience; this is an optional layout menu:

1. Header with title, date/context, and optional brand cue.
2. Hero summary with the core message.
3. Top facts or metrics strip.
4. Main content cards grouped by market, region, topic, or decision area.
5. Executive takeaway with 2-4 concise bullets.
6. Errors, gaps, and checks found.
7. Next actions or items to fix in the next report.
8. Small footer with source note and caveat if data is fictional, draft, or incomplete.

## Writing Rules

- Keep the page concise. Prefer short noun phrases, numbers, and active verbs over source-style paragraphs.
- Preserve caveats instead of smoothing them away.
- Do not mix estimates with final numbers without labeling them.
- Keep error findings visible but secondary to the executive readout.
- Use exact dates when the source contains relative timing or stale follow-up dates.
- Use brand-inspired styling without impersonating a live corporate site or implying official publication unless the user asks for that and owns the context.

## Output Rules

- For projectless sessions, write user-facing deliverables under `outputs/`.
- Name files clearly, for example `market-input-june-onepager.html`.
- Keep the HTML self-contained unless the user requests a web app or hosted site.
- Return the output path and any material errors or gaps actually found.
