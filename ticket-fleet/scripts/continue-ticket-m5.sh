#!/bin/bash
# continue-ticket-m5.sh <worktree_dir> <model> <log_file> [extra_allowed_tool ...]
# M5-enabled resume: same as continue-ticket.sh but with m5 MCP tools + per-ticket
# extras in the allowlist, and accurate interruption wording (connection drop).
set -uo pipefail
WT="$1"; MODEL="$2"; LOG="$3"; shift 3
EXTRA_TOOLS=("$@")
cd "$WT" || { echo "FATAL: no worktree $WT" | tee -a "$LOG"; exit 1; }
echo "=== headless session RESUME $(date '+%H:%M:%S') wt=$WT model=$MODEL extra_tools=${EXTRA_TOOLS[*]:-none} ===" >> "$LOG"
claude -p "You were interrupted mid-task by an API connection drop (transient; service is healthy again). Your working tree still holds your partial edits — check git status first, then continue EXACTLY where you left off and complete the original task end-to-end: finish the implementation and tests (red/green where applicable), run the full suite, commit (conventional message referencing the issue, Claude Code co-author line), push the branch, open the PR with the required body/footer, run your review-pr-codex skill on it (effort 'high' for small diffs), fix real findings, and print the FINAL REPORT in the exact required format from your original instructions (including the M5: line). Remember the operating rules: PR only — no deploys, no STATUS.md edits, never switch branches. The M5 offload practice still applies: mcp__m5__ask for bounded sub-tasks, verify every output before use." \
  --continue --model "$MODEL" --permission-mode acceptEdits \
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
echo "=== headless session RESUME end $(date '+%H:%M:%S') exit=$RC ===" >> "$LOG"
echo "TICKET_RESUME_DONE wt=$WT rc=$RC log=$LOG"
tail -c 2500 "$LOG"
exit $RC
