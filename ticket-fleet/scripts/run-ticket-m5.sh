#!/bin/bash
# run-ticket-m5.sh <repo_dir> <issue_no> <model> <prompt_file> <log_file> [extra_allowed_tool ...]
# Variant of ticket-fleet run-ticket.sh: adds m5 MCP tools to the allowlist so
# sessions can offload bounded sub-tasks to the M5 box, plus optional per-ticket
# extra tools (e.g. "Bash(curl:*)" for tickets that must touch live seams).
set -uo pipefail
REPO_DIR="$1"; ISSUE="$2"; MODEL="$3"; PROMPT_FILE="$4"; LOG="$5"; shift 5
EXTRA_TOOLS=("$@")
REPO_NAME=$(basename "$REPO_DIR")
WT="/Users/magnus/repos/.wt/${REPO_NAME}-t${ISSUE}"

cd "$REPO_DIR" || { echo "FATAL: no repo dir $REPO_DIR" | tee "$LOG"; exit 1; }
git fetch origin -q 2>/dev/null || true
DEF=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
if [ -z "$DEF" ]; then DEF=$(gh repo view --json defaultBranchRef -q .defaultBranchRef.name 2>/dev/null); fi
[ -z "$DEF" ] && DEF=main

if [ -d "$WT" ]; then echo "FATAL: worktree exists $WT" | tee "$LOG"; exit 1; fi
git worktree add "$WT" -b "ticket/${ISSUE}-headless" "origin/${DEF}" >> "$LOG" 2>&1 || {
  echo "FATAL: worktree add failed" | tee -a "$LOG"; exit 1; }

cd "$WT"
echo "=== headless session start $(date '+%H:%M:%S') repo=$REPO_NAME issue=#$ISSUE model=$MODEL base=origin/$DEF extra_tools=${EXTRA_TOOLS[*]:-none} ===" >> "$LOG"
claude -p "$(cat "$PROMPT_FILE")" --model "$MODEL" --permission-mode acceptEdits \
  --allowedTools "Bash(git:*)" "Bash(gh:*)" "Bash(npm:*)" "Bash(npx:*)" "Bash(node:*)" \
    "Bash(python3:*)" "Bash(codex:*)" "Bash(shellcheck:*)" "Bash(mkdir:*)" "Bash(ls:*)" \
    "Bash(grep:*)" "Bash(find:*)" "Bash(wc:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(jq:*)" \
    "Bash(cat:*)" "Bash(cp:*)" "Bash(mv:*)" "Bash(chmod:*)" "Bash(echo:*)" "Bash(cd:*)" \
    "Bash(sed:*)" "Bash(awk:*)" "Bash(touch:*)" "Bash(diff:*)" "Bash(which:*)" "Bash(date:*)" \
    "Bash(rm -f /tmp/codex-pr-review-*)" "Bash(rm -f /tmp/codex-*)" \
    "Bash(bash:*)" "Bash(sh:*)" "Bash(make:*)" "Bash(xargs:*)" "Bash(tee:*)" "Bash(sort:*)" "Bash(uniq:*)" "Bash(cut:*)" "Bash(tr:*)" \
    "mcp__m5__ask" "mcp__m5__list_models" \
    ${EXTRA_TOOLS[@]+"${EXTRA_TOOLS[@]}"} \
    >> "$LOG" 2>&1
RC=$?
echo "=== headless session end $(date '+%H:%M:%S') exit=$RC ===" >> "$LOG"
echo "TICKET_DONE repo=$REPO_NAME issue=$ISSUE rc=$RC log=$LOG"
tail -c 2500 "$LOG"
exit $RC
