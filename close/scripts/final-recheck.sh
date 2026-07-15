#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage:
  final-recheck.sh capture <snapshot-file> <repo-path>...
  final-recheck.sh compare <snapshot-file> <repo-path>...

Run git fetch --prune for each tracking remote before capture/compare.
Exit codes: 0 stable/success, 3 changed, 2 usage or capture failure.
EOF
}

die() {
  printf 'final-recheck: %s\n' "$*" >&2
  exit 2
}

github_slug() {
  local url="$1"

  case "$url" in
    https://github.com/*)
      url="${url#https://github.com/}"
      ;;
    git@github.com:*)
      url="${url#git@github.com:}"
      ;;
    ssh://git@github.com/*)
      url="${url#ssh://git@github.com/}"
      ;;
    *)
      return 1
      ;;
  esac

  url="${url%.git}"
  case "$url" in
    */*) printf '%s\n' "$url" ;;
    *) return 1 ;;
  esac
}

dedupe_roots() {
  local candidate root common existing seen
  ROOTS=()
  COMMON_DIRS=()

  for candidate in "$@"; do
    root="$(git -C "$candidate" rev-parse --show-toplevel 2>/dev/null)" ||
      die "not a Git worktree: $candidate"
    common="$(git -C "$candidate" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" ||
      die "cannot resolve common Git directory: $candidate"
    seen=false
    for existing in "${COMMON_DIRS[@]:-}"; do
      if [[ "$existing" == "$common" ]]; then
        seen=true
        break
      fi
    done
    if [[ "$seen" == false ]]; then
      ROOTS+=("$root")
      COMMON_DIRS+=("$common")
    fi
  done
}

status_fingerprint() {
  local path="$1"
  git -C "$path" status --porcelain=v2 --branch --untracked-files=normal |
    git -C "$path" hash-object --stdin
}

capture_state() {
  local destination="$1"
  shift
  local temporary="${destination}.tmp.$$"
  local root worktree resolved_worktree head branch upstream upstream_sha fingerprint remote slug forge_output

  dedupe_roots "$@"
  : >"$temporary"

  for root in "${ROOTS[@]}"; do
    printf 'repo\t%s\n' "$root" >>"$temporary"

    git -C "$root" for-each-ref \
      --format='branch%09%(refname:short)%09%(objectname)%09%(upstream:short)%09%(upstream:track)' \
      refs/heads | LC_ALL=C sort >>"$temporary"

    while IFS= read -r worktree; do
      resolved_worktree="$(git -C "$worktree" rev-parse --show-toplevel 2>/dev/null || true)"
      if [[ "$resolved_worktree" != "$worktree" ]]; then
        printf 'worktree-missing\t%s\t%s\n' "$root" "$worktree" >>"$temporary"
        continue
      fi

      head="$(git -C "$worktree" rev-parse HEAD)"
      branch="$(git -C "$worktree" symbolic-ref --quiet --short HEAD 2>/dev/null || printf 'DETACHED')"
      if [[ "$branch" == "DETACHED" ]]; then
        upstream=""
      else
        upstream="$(git -C "$worktree" for-each-ref --format='%(upstream:short)' "refs/heads/$branch")"
      fi
      if [[ -n "$upstream" ]]; then
        upstream_sha="$(git -C "$worktree" rev-parse --verify --quiet "${upstream}^{commit}" || true)"
        upstream_sha="${upstream_sha:-MISSING}"
      else
        upstream_sha="-"
      fi
      fingerprint="$(status_fingerprint "$worktree")"
      printf 'worktree\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$root" "$worktree" "$head" "$branch" "${upstream:--}" "$upstream_sha" >>"$temporary"
      printf 'status\t%s\t%s\n' "$worktree" "$fingerprint" >>"$temporary"
    done < <(git -C "$root" worktree list --porcelain | sed -n 's/^worktree //p')

    remote="$(git -C "$root" remote get-url origin 2>/dev/null || true)"
    if [[ -n "$remote" ]] && slug="$(github_slug "$remote" 2>/dev/null)" && command -v gh >/dev/null 2>&1; then
      forge_output="${temporary}.forge"
      if gh pr list --repo "$slug" --state open --limit 100 \
        --json number,headRefName,headRefOid,isDraft \
        --jq '. | sort_by(.number) | .[] | ["forge", .number, .headRefName, .headRefOid, .isDraft] | @tsv' \
        >"$forge_output" 2>/dev/null; then
        printf 'forge-ok\t%s\n' "$slug" >>"$temporary"
        while IFS= read -r line; do
          printf '%s\n' "$line" >>"$temporary"
        done <"$forge_output"
      else
        printf 'forge-unavailable\t%s\n' "$slug" >>"$temporary"
      fi
      rm -f "$forge_output"
    elif [[ -n "$remote" ]]; then
      printf 'forge-unavailable\t%s\n' "$remote" >>"$temporary"
    fi
  done

  mv "$temporary" "$destination"
}

[[ $# -ge 3 ]] || {
  usage
  exit 2
}

mode="$1"
snapshot="$2"
shift 2

case "$mode" in
  capture)
    capture_state "$snapshot" "$@"
    printf 'captured\t%s\n' "$snapshot"
    ;;
  compare)
    [[ -f "$snapshot" ]] || die "snapshot not found: $snapshot"
    current="${snapshot}.current.$$"
    trap 'rm -f "${current:-}"' EXIT
    capture_state "$current" "$@"
    if diff -u "$snapshot" "$current"; then
      printf 'stable\t%s\n' "$snapshot"
      exit 0
    fi
    printf 'changed\t%s\n' "$snapshot" >&2
    exit 3
    ;;
  *)
    usage
    exit 2
    ;;
esac
