#!/bin/bash
# continue-ticket.sh <worktree_dir> <model> <log_file> — resume an interrupted headless session
set -uo pipefail
WT="$1"; MODEL="$2"; LOG="$3"
cd "$WT" || { echo "FATAL: no worktree $WT" | tee -a "$LOG"; exit 1; }
echo "=== headless session RESUME $(date '+%H:%M:%S') wt=$WT model=$MODEL ===" >> "$LOG"
claude -p "You were interrupted mid-task by an API spend limit (now lifted). Continue EXACTLY where you left off and complete the original task end-to-end: finish the implementation and tests (red/green where applicable), run the full suite, commit (conventional message referencing the issue, Claude Code co-author line), push the branch, open the PR with 'Closes #<issue>' and the Claude Code footer, run your review-pr-codex skill on it (effort 'high' for small diffs), fix real findings, and print the FINAL REPORT in the exact required format (PR / TESTS / CODEX / UNCERTAINTIES / STATUS). Remember the operating rules: PR only — no deploys, no STATUS.md edits, never switch branches." \
  --continue --model "$MODEL" --permission-mode acceptEdits \
  --allowedTools "Bash(git:*)" "Bash(gh:*)" "Bash(npm:*)" "Bash(npx:*)" "Bash(node:*)" \
    "Bash(python3:*)" "Bash(codex:*)" "Bash(shellcheck:*)" "Bash(mkdir:*)" "Bash(ls:*)" \
    "Bash(grep:*)" "Bash(find:*)" "Bash(wc:*)" "Bash(head:*)" "Bash(tail:*)" "Bash(jq:*)" \
    "Bash(cat:*)" "Bash(cp:*)" "Bash(mv:*)" "Bash(chmod:*)" "Bash(echo:*)" "Bash(cd:*)" \
    "Bash(sed:*)" "Bash(awk:*)" "Bash(touch:*)" "Bash(diff:*)" "Bash(which:*)" "Bash(date:*)" \
    "Bash(rm -f /tmp/codex-pr-review-*)" "Bash(rm -f /tmp/codex-*)" \
    "Bash(bash:*)" "Bash(sh:*)" "Bash(make:*)" "Bash(xargs:*)" "Bash(tee:*)" "Bash(sort:*)" "Bash(uniq:*)" "Bash(cut:*)" "Bash(tr:*)" \
  >> "$LOG" 2>&1
RC=$?
echo "=== headless session RESUME end $(date '+%H:%M:%S') exit=$RC ===" >> "$LOG"
echo "TICKET_RESUME_DONE wt=$WT rc=$RC log=$LOG"
tail -c 2500 "$LOG"
exit $RC
