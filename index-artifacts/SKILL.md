---
name: index-artifacts
description: Index files from ~/mimir/ into Munin documents/* namespace, making them discoverable by all Claude environments. Extracts metadata, generates summaries, and creates Mímir URL references.
---

# /index-artifacts — Index Files into Munin

Scan files in `~/mimir/` (the local artifact archive), extract metadata and summaries, and write entries to Munin's `documents/*` namespace so that all Claude environments (Desktop, Web, Mobile) can discover and query documents without direct file access.

## Usage

- `/index-artifacts` — Interactive: show what's new/changed, confirm before writing
- `/index-artifacts <path>` — Index a specific subdirectory (e.g., `/index-artifacts customers/lofalk-advokatbyra`)
- `/index-artifacts --dry-run` — Show what would be indexed without writing to Munin
- `/index-artifacts --force` — Re-index everything, overwriting existing entries

## How It Works

### 1. Discover files

Scan `~/mimir/` (or the specified subdirectory) for indexable files:

**Include:** `.pdf`, `.md`, `.txt`, `.html`, `.htm`, `.png`, `.jpg`, `.jpeg`, `.pptx`, `.docx`, `.key`, `.pages`

**Exclude these directories entirely:**
- `archive/` — old materials, low value
- `tests/`, `test-results/` — test infrastructure
- `.git/` — version control
- Any directory starting with `.`

**Exclude these files:**
- `STATUS.md`, `PROGRESS.md`, `TODO.md`, `CLAUDE.md` — session state files, not artifacts
- `pytest.ini`, `run_tests.sh`, `*.pyc` — test/build infrastructure
- Files under 100 bytes (likely empty or stubs)

### 2. Check what's already indexed

Query Munin to find existing `documents/*` entries:

```
memory_list("documents")
```

For each file found in step 1, check if a Munin entry already exists by matching the file path. Skip files that are already indexed (unless `--force` is used).

To detect changes in already-indexed files, compare the SHA-256 hash from the existing entry against the current file hash. Re-index if the hash differs.

### 3. Generate slug

Derive the Munin key from the file path relative to `~/mimir/`:

```
~/mimir/customers/lofalk-advokatbyra/utbildning.pdf
→ namespace: documents/customers
→ key: lofalk-advokatbyra--utbildning-pdf
```

Rules:
- Namespace = `documents/<top-level-dir>` (e.g., `documents/customers`, `documents/internal`, `documents/events`)
- Files at `~/mimir/` root → namespace: `documents/root`
- Key = remaining path with `/` → `--`, spaces → `-`, dots → `-`, lowercased
- Keep keys readable and grep-friendly

### 4. Extract metadata

For each file, compute:

```bash
# File size
stat -f%z "$file"
# Last modified date
stat -f "%Sm" -t "%Y-%m-%d" "$file"
# SHA-256 hash
shasum -a 256 "$file" | cut -d' ' -f1
```

### 5. Extract content and generate summary

**Markdown files (.md):**
- Read the file content
- Summary = first heading + first 2-3 sentences of body text
- Key points = extract all `##` headings
- Extracted text = first 10,000 characters

**Text files (.txt):**
- Read the file content
- Summary = first 2-3 sentences
- Extracted text = first 10,000 characters

**PDF files (.pdf):**
- Use the Read tool (it can read PDFs)
- Summary = describe the document based on content (2-3 sentences)
- Key points = extract main topics/sections
- Extracted text = first 10,000 characters of readable text

**Images (.png, .jpg, .jpeg):**
- Use the Read tool (it can read images)
- Summary = brief visual description (1-2 sentences)
- No extracted text
- Tag with `type:image`

**Office formats (.pptx, .docx, .key, .pages):**
- Note the file type and name
- Summary = infer from filename and context (e.g., "Presentation for Lofalk law firm on AI training")
- Mark as `needs-review` tag if summary is purely inferred

**HTML files (.html, .htm):**
- Read the file content
- Summary = extract `<title>` and first paragraph
- Extracted text = strip tags, first 10,000 characters

### 6. Determine tags

Apply tags based on file location and type:

| Location | Tags |
|----------|------|
| `customers/<name>/` | `client:<name>`, `source:internal` |
| `internal/` | `source:internal` |
| `events/<name>/` | `topic:<event-name>`, `source:internal` |
| `learning/` | `topic:learning`, `source:external` |
| `inbox/` | `needs-review` |

File type tags: `type:pdf`, `type:markdown`, `type:image`, `type:presentation`, `type:document`, `type:html`, `type:text`

### 7. Write to Munin

For each file, write a structured entry:

```
memory_write("documents/<category>", "<slug>", content, tags)
```

Entry content format:

```markdown
## <Filename>

- **Source:** https://mimir.gille.ai/files/<path-relative-to-artifacts>
- **Local:** ~/mimir/<path>
- **Type:** PDF | Markdown | Image | etc.
- **Size:** <bytes> (<human-readable>)
- **Modified:** <YYYY-MM-DD>
- **SHA-256:** <hash>

### Summary
<2-5 sentences describing the document>

### Key Points
- <extracted insight 1>
- <extracted insight 2>

### Extracted Text
<First ~10,000 characters, if applicable>
```

### 8. Report results

After indexing, print a summary:

```
## Index Results

- **Scanned:** 142 files
- **New entries:** 23
- **Updated (hash changed):** 2
- **Skipped (already indexed):** 117
- **Errors:** 0

### New entries
- documents/customers/lofalk-advokatbyra--utbildning-pdf
- documents/internal/brand-guide-md
- ...
```

## Important Rules

1. **Sovereignty policy:** Do NOT use AI summarization for private or client documents that contain confidential information. For `customers/*` files, summaries should be factual descriptions of what the document IS (type, apparent purpose from filename/headings), not interpretive summaries of the content. Example: "PDF presentation for Lofalk law firm, 12 slides covering AI training workshop agenda" — not a summary of the legal content.

2. **Batch size:** Process files in batches of 10-20. After each batch, report progress and confirm with the user before continuing. This prevents runaway indexing and lets the user course-correct.

3. **Idempotent:** Running `/index-artifacts` twice should produce the same result. Use SHA-256 hashes to detect changes.

4. **No secrets:** Never index files that look like credentials, API keys, `.env` files, or private keys.

5. **Mímir path mapping:** The Mímir URL path = the path relative to the artifacts root on the NAS. Since `~/mimir/` syncs to `/home/magnus/artifacts/mgc/` on the NAS, the Mímir URL for `~/mimir/customers/foo.pdf` is `https://mimir.gille.ai/files/mgc/customers/foo.pdf`.

6. **Size guard:** Skip files larger than 50MB. Note them in the report as skipped.
