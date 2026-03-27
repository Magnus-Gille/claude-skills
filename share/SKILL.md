---
name: share
description: Share a file from ~/mimir/ by generating a temporary public URL. Syncs the file to the Pi, mints an HMAC-signed token, and copies the link to clipboard. Use when the user wants to share a file, send a link, or make something temporarily accessible.
---

# /share - Share a File from Mimir

Generate a temporary, read-only public URL for any file in `~/mimir/`.

## Usage

- `/share <file-path>` — Share with default 24h expiry
- `/share <file-path> <ttl>` — Share with custom TTL (e.g. 1h, 7d)

## How It Works

### Step 1: Parse Arguments

Extract file path and optional TTL from the arguments.

- File path can be absolute (`~/mimir/presentations/deck.pdf`), relative to `~/mimir/` (`presentations/deck.pdf`), or just a filename to search for.
- TTL formats: `1h`, `6h`, `12h`, `24h` (default), `3d`, `7d`
- If no file path provided, ask the user what they want to share.

### Step 2: Resolve the File

If the path is ambiguous or just a filename, search `~/mimir/` for matches:

```bash
find ~/mimir -name "<filename>" -type f 2>/dev/null
```

If multiple matches, show them and ask the user to pick. If no matches, tell the user the file doesn't exist.

### Step 3: Run the Share Script

Execute the share script from the mimir repo:

```bash
~/repos/mimir/scripts/share.sh <resolved-path> <ttl>
```

This script:
1. Validates the file exists locally
2. Rsyncs just that file to the Pi
3. SSHs to the Pi and generates an HMAC-signed token
4. Prints the URL and copies to clipboard

### Step 4: Report

Show the user:
- The generated URL
- Expiry time (human-readable, e.g. "expires tomorrow at 14:30")
- Confirm it's on the clipboard

If the script fails (Pi unreachable, secret not configured, etc.), show the error and suggest fixes.

## Prerequisites

- `MIMIR_SHARE_SECRET` must be set in the Pi's `.env` at `/home/magnus/mimir-server/.env`
- Pi must be reachable via Tailscale (`100.99.119.52`)
- Cloudflare Access bypass must be configured for `/share/*` on `mimir.gille.ai`

## Examples

```
User: /share ~/mimir/presentations/q1-review.pdf
→ Syncs file, generates 24h link, copies to clipboard

User: /share deck.pdf 7d
→ Finds ~/mimir/**/deck.pdf, syncs, generates 7-day link

User: /share
→ Asks "What file do you want to share?"
```
