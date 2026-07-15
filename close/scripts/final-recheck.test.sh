#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_PARENT="${TMPDIR:-/tmp}"
TEMP_ROOT="$(mktemp -d "${TEMP_PARENT%/}/close-recheck-test.XXXXXX")"
trap 'rm -rf "$TEMP_ROOT"' EXIT

repo="$TEMP_ROOT/repo"
remote="$TEMP_ROOT/remote.git"
missing="$TEMP_ROOT/missing-worktree"
snapshot="$TEMP_ROOT/snapshot"

git init --bare -q "$remote"
git init -q -b main "$repo"
git -C "$repo" config user.name "Close Skill Test"
git -C "$repo" config user.email "close-skill-test@example.invalid"
printf 'fixture\n' >"$repo/fixture.txt"
git -C "$repo" add fixture.txt
git -C "$repo" commit -qm "test fixture"
git -C "$repo" remote add origin "$remote"
git -C "$repo" push -qu origin main
git -C "$repo" worktree add -q -b missing-branch "$missing"

repo="$(cd "$repo" && pwd -P)"
missing="$(cd "$missing" && pwd -P)"
rm -rf "$missing"

"$SCRIPT_DIR/final-recheck.sh" capture "$snapshot" "$repo" >/dev/null

expected="$(printf 'worktree-missing\t%s\t%s' "$repo" "$missing")"
grep -Fqx "$expected" "$snapshot"
"$SCRIPT_DIR/final-recheck.sh" compare "$snapshot" "$repo" >/dev/null

printf 'ok - missing registered worktree is recorded without aborting\n'
