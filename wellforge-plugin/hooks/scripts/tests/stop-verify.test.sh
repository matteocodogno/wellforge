#!/usr/bin/env bash
# Regression matrix for stop-verify.sh. Run by ci.yml (hook-fixtures job).
#
# The bug this suite exists for: the hook used a bare `git diff --name-only`, which sees only
# UNSTAGED changes. Dev agents commit their work, so everything they did was invisible and
# every check passed by seeing nothing. Cases 2-4 are that bug; they fail against the old hook.
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/stop-verify.sh"
PASS=0; FAIL=0

# run <expected-exit> <description>; runs the hook in $REPO
run() {
  local want="$1" desc="$2" got out
  out=$(echo '{}' | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); got=$?
  if [ "$got" = "$want" ]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1)); echo "  FAIL: $desc (want exit $want, got $got)"; echo "$out" | sed 's/^/        /'
  fi
}

new_repo() {
  REPO=$(mktemp -d); cd "$REPO" || exit 1
  git init -q -b main . 2>/dev/null
  git config user.email t@t; git config user.name T; git config commit.gpgsign false
  mkdir -p specs/001-x
  printf -- '---\nid: 001\n---\n# Spec\n' > specs/001-x/spec.md
  printf -- '# Tasks\n- [ ] T1\n' > specs/001-x/tasks.md
  git add -A; git commit -qm "chore: base"
}

echo "stop-verify regression matrix"

# 1. clean tree → pass
new_repo
run 0 "clean tree exits 0"

# 2. spec.md edited but UNCOMMITTED, tasks.md untouched → block (worked before too)
new_repo
echo "change" >> specs/001-x/spec.md
run 2 "unstaged spec change without tasks re-sync blocks"

# 3. THE BUG: same drift, but COMMITTED on a feature branch → must still block
new_repo
git switch -qc feat/drift
echo "change" >> specs/001-x/spec.md
git commit -qam "docs: amend spec"
run 2 "COMMITTED spec change without tasks re-sync blocks (was invisible)"

# 4. committed spec change WITH tasks re-synced → pass
new_repo
git switch -qc feat/ok
echo "change" >> specs/001-x/spec.md
echo "- [ ] T2" >> specs/001-x/tasks.md
git commit -qam "docs: amend spec and re-sync tasks"
run 0 "committed spec + tasks together does not block"

# 5. staged-only drift → block
new_repo
echo "change" >> specs/001-x/spec.md
git add specs/001-x/spec.md
run 2 "staged-only spec change blocks"

# 6. untracked new spec in a dir with tasks.md → block
new_repo
printf -- '---\nid: 002\n---\n' > specs/001-x/plan.md
run 2 "untracked plan.md without tasks re-sync blocks"

# 7. spec dir with NO tasks.md → nothing to drift from → pass
new_repo
mkdir -p specs/002-y; printf -- '# Spec\n' > specs/002-y/spec.md
run 0 "spec without a tasks.md does not block"

# 8. not a git repo → pass (hook must never block outside a repo)
REPO=$(mktemp -d); cd "$REPO" || exit 1
run 0 "non-git directory exits 0"

# 9. the concatenation bug: .kt and pom.xml changed together must not fuse into one
#    path ("Foo.ktpom.xml"). No mvnw here, so the hook must exit 0 with the wrapper warning.
new_repo
mkdir -p svc/src
echo 'fun main() {}' > svc/src/Main.kt
echo '<project/>' > svc/pom.xml
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); rc=$?
if [ "$rc" = 0 ] && ! echo "$out" | grep -q 'ktpom'; then PASS=$((PASS+1));
else FAIL=$((FAIL+1)); echo "  FAIL: kt+pom must not concatenate (exit $rc)"; echo "$out" | sed 's/^/        /'; fi

# 10. two Maven roots both get compiled — assert both are visited, not just the first.
new_repo
for s in a b; do
  mkdir -p "svc-$s"
  printf '#!/bin/sh\necho "built %s"\nexit 0\n' "$s" > "svc-$s/mvnw"; chmod +x "svc-$s/mvnw"
  echo 'fun main() {}' > "svc-$s/Main.kt"
done
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); rc=$?
if [ "$rc" = 0 ] && echo "$out" | grep -q "svc-a" && echo "$out" | grep -q "svc-b"; then PASS=$((PASS+1));
else FAIL=$((FAIL+1)); echo "  FAIL: both Maven roots must be compiled (exit $rc)"; echo "$out" | sed 's/^/        /'; fi

# 11. a failing Maven root blocks
new_repo
mkdir -p svc
printf '#!/bin/sh\necho "[ERROR] boom"\nexit 1\n' > svc/mvnw; chmod +x svc/mvnw
echo 'fun main() {}' > svc/Main.kt
run 2 "failing Maven compile blocks"

# 12. a Maven root over budget is advisory (reported), never a silent pass
new_repo
mkdir -p svc
printf '#!/bin/sh\nsleep 5\n' > svc/mvnw; chmod +x svc/mvnw
echo 'fun main() {}' > svc/Main.kt
if command -v timeout >/dev/null 2>&1 || command -v gtimeout >/dev/null 2>&1; then
  out=$(echo '{}' | CLAUDE_PROJECT_DIR="$REPO" WELLFORGE_STOP_MVN_BUDGET=1 bash "$HOOK" 2>&1); rc=$?
  if [ "$rc" = 0 ] && echo "$out" | grep -q "NOT verified"; then PASS=$((PASS+1));
  else FAIL=$((FAIL+1)); echo "  FAIL: over-budget compile must report NOT verified (exit $rc)"; echo "$out" | sed 's/^/        /'; fi
else
  echo "  SKIP: no timeout/gtimeout available"
fi

# 13. `clean` must not come back — it is the cost regression this hook was fixed for
grep -qE '\./mvnw\s+clean' "$HOOK" && { FAIL=$((FAIL+1)); echo "  FAIL: hook runs 'mvnw clean' again"; } || PASS=$((PASS+1))

# 14. The escape must actually clear the block. A cosmetic spec edit committed earlier on
#     the branch blocks every Stop; /wellforge:tasks re-sync stamps `synced:` even when it
#     changes nothing else, and THAT is what unblocks. Without the stamp the hook tells the
#     user to run a command that cannot help — the trap this case exists to prevent.
new_repo
git switch -qc feat/typo
printf -- 'typo fixed\n' >> specs/001-x/spec.md
git commit -qam "docs: fix a typo in the spec"
echo "unrelated" > other.txt && git add -A && git commit -qm "feat: unrelated work"
run 2 "cosmetic spec edit earlier on the branch still blocks"
# the documented escape
printf -- '\nsynced: 2026-09-20\n' >> specs/001-x/tasks.md
git commit -qam "chore(specs): re-sync tasks"
run 0 "re-sync stamp clears the block"

# 15. The hint must name the fix and the branch-wide scope — a message that only says
#     "not re-synced" leaves the user hunting for an edit they made three commits ago.
new_repo
git switch -qc feat/hint
printf -- 'x\n' >> specs/001-x/spec.md
git commit -qam "docs: amend spec"
out=$(echo '{}' | CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1)
if echo "$out" | grep -q '/wellforge:tasks' && echo "$out" | grep -qi 'branch' && echo "$out" | grep -q 'synced'; then
  PASS=$((PASS+1))
else
  FAIL=$((FAIL+1)); echo "  FAIL: hint must name /wellforge:tasks, the branch scope and the synced stamp"; echo "$out" | sed 's/^/        /'
fi

echo
echo "stop-verify: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
