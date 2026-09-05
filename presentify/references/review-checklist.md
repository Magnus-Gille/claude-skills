# Presentify Review Checklist

Use this checklist after reading the source and before writing the HTML.

## Content Compression

- Identify the actual decision or executive message.
- Keep the short version meaningfully shorter than the source.
- Preserve the strongest numbers and remove process chatter.
- Convert long quotes into concise implications unless the wording itself matters.
- Separate final figures from estimates, forecasts, and pending updates.

## Error and Gap Review

Check for:

- Missing values presented as if complete.
- Duplicate files with conflicting contents.
- Totals that do not equal their parts.
- KPI definitions that differ by region, author, or system.
- Count-based ratios described as affected by currency or price movements.
- Stale follow-up dates, especially dates earlier than the current date.
- Claims like "all markets" when one market is missing.
- Ambiguous units, denominators, time periods, or YTD vs monthly mixing.
- Logic mismatches between source comments and tables.
- Unclear ownership for next actions.

## Styling From A Reference Page

When a user provides a style URL:

- Browse or inspect the page if current access is available.
- Note the dominant colors, accent colors, typography character, section rhythm, density, grid structure, and navigation/footer feel.
- Recreate the design language using original code and generic shapes.
- Avoid copying logos, photos, icons, proprietary fonts, or complete CSS unless the user provided assets or permission.
- Keep the presentation readable and compact even if the reference page is spacious.

## Final QA

- Parse the HTML using a local parser or equivalent check.
- Search the generated file for placeholder text.
- Confirm the error/gap section includes source issues found during review.
- Confirm the page can open directly as a local file.
- If the user requested Safari or browser viewing, open the generated file there after writing.
