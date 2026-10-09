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

# ── lifecycle edits are not drift ────────────────────────────────────────────────
# Found by the prompt evals (done-mvp-passes, 2026-10-06), not by this matrix: /wellforge:done
# writes `status: done` into spec.md as its LAST step, tasks.md is untouched, and this hook
# blocked the close it had just watched succeed — while forge-state.py, asked the same
# question, said "no drift". The two must agree, and forge-state.py's rule is the right one.
lifecycle_repo() {
  new_repo
  printf -- '---\nid: 001\ntitle: X\nstatus: in-progress\nrigor: production\n---\n# Spec\n- AC-1: a thing\n' > specs/001-x/spec.md
  git commit -qam "docs: spec with a lifecycle"
}

# 12. the close: `status: done` + `done: <date>`, uncommitted, tasks.md untouched → pass
lifecycle_repo
sed -i.bak 's/^status: in-progress$/status: done/' specs/001-x/spec.md && rm -f specs/001-x/spec.md.bak
awk '{print} /^rigor:/{print "done: 2026-10-06"}' specs/001-x/spec.md > spec.tmp && mv spec.tmp specs/001-x/spec.md
grep -q '^done: 2026-10-06$' specs/001-x/spec.md || { FAIL=$((FAIL+1)); echo "  FAIL: case 12 fixture did not write done:"; }
run 0 "status: done + done: written by /wellforge:done is not drift"

# 13. the same close, COMMITTED on a feature branch → pass
lifecycle_repo
git switch -qc feat/close
sed -i.bak 's/^status: in-progress$/status: done/' specs/001-x/spec.md && rm -f specs/001-x/spec.md.bak
git commit -qam "docs: close the feature"
run 0 "a committed lifecycle-only edit is not drift"

# 14. promote: `rigor:` changes, nothing else → pass
lifecycle_repo
sed -i.bak 's/^rigor: production$/rigor: mvp/' specs/001-x/spec.md && rm -f specs/001-x/spec.md.bak
run 0 "a rigor-only edit is not drift"

# 15. a status edit that ALSO changes the body is still drift → block
lifecycle_repo
sed -i.bak 's/^status: in-progress$/status: done/' specs/001-x/spec.md && rm -f specs/001-x/spec.md.bak
echo "- AC-2: another thing" >> specs/001-x/spec.md
run 2 "a lifecycle edit plus a body change still blocks"

# 16. a NON-lifecycle frontmatter field is a spec change → block
lifecycle_repo
sed -i.bak 's/^title: X$/title: Y/' specs/001-x/spec.md && rm -f specs/001-x/spec.md.bak
run 2 "a changed non-lifecycle frontmatter field blocks"

# 17. a lifecycle-looking line in the BODY is body, not bookkeeping → block
lifecycle_repo
echo "status: done" >> specs/001-x/spec.md
run 2 "'status:' appended to the body is a body change and blocks"

# 18. the hook's lifecycle list is forge-state.py's list — one rule, two readers
FS="$(cd "$(dirname "$HOOK")/../.." && pwd)/scripts/forge-state.py"
want=$(sed -n '/^LIFECYCLE_FIELDS = /,/})/p' "$FS" | grep -o '"[a-z_]*"' | tr -d '"' | sort | tr '\n' ' ')
got=$(sed -n 's/^LIFECYCLE_FIELDS="\(.*\)"$/\1/p' "$HOOK" | tr '|' '\n' | sort | tr '\n' ' ')
if [ -n "$want" ] && [ "$want" = "$got" ]; then PASS=$((PASS+1));
else FAIL=$((FAIL+1)); echo "  FAIL: lifecycle fields differ — forge-state.py: [$want] hook: [$got]"; fi

# ── the type check must never touch the project ─────────────────────────────────
# The bug: the check always ran `pnpm exec tsc`, which in a Bun/npm directory wrote
# pnpm-lock.yaml + pnpm-workspace.yaml and reinstalled node_modules from package.json ranges.
# Stub package managers on PATH make that observable without a toolchain: every one of them
# LOGS its call and writes the pollution files, so any invocation is a visible failure. The
# stub tsc fails (exit 1) only when a file contains TYPE_ERROR.
STUBS=$(mktemp -d)
for pm in pnpm bun npx yarn npm; do
  printf '#!/bin/sh\necho "$0 $*" >> "$STUB_LOG"\ntouch pnpm-lock.yaml pnpm-workspace.yaml\ncase "$*" in *tsc*) exit 1;; esac\nexit 0\n' > "$STUBS/$pm"
  chmod +x "$STUBS/$pm"
done

ts_repo() {   # ts_repo <lockfile|-> <typed|clean|broken>; a compile unit in $REPO/svc
  new_repo
  mkdir -p svc/node_modules/.bin
  printf '{"name":"svc"}\n' > svc/package.json
  echo '{}' > svc/tsconfig.json
  [ "$1" != "-" ] && : > "svc/$1"
  printf '#!/bin/sh\n[ "$1" = "--version" ] && { echo "Version 5.0.0"; exit 0; }\n'\
'if grep -rqs TYPE_ERROR --include=*.ts . --exclude-dir=node_modules; then echo "error TS2345: bad"; exit 1; fi\nexit 0\n' \
    > svc/node_modules/.bin/tsc
  chmod +x svc/node_modules/.bin/tsc
  echo 'export const x = 1' > svc/a.ts
  [ "$2" = "broken" ] && echo 'const y: string = 1 // TYPE_ERROR' >> svc/a.ts
  git add -A; git commit -qm "chore: ts unit"       # node_modules is committed: the stub is the fixture
  echo 'export const z = 2' >> svc/a.ts               # the changed .ts file the hook sees
  STUB_LOG="$REPO/.stub.log"; : > "$STUB_LOG"; export STUB_LOG
}
snapshot() { (cd "$REPO" && git status --porcelain | sort; find svc/node_modules -type f | sort | xargs cksum; ls) 2>&1 | cksum; }
run_stubbed() {   # same as run, with the stub package managers first on PATH
  local want="$1" desc="$2" got out
  out=$(echo '{}' | PATH="$STUBS:$PATH" CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); got=$?
  LAST_OUT="$out"
  if [ "$got" = "$want" ]; then PASS=$((PASS+1))
  else FAIL=$((FAIL+1)); echo "  FAIL: $desc (want exit $want, got $got)"; echo "$out" | sed 's/^/        /'; fi
}
no_pollution() {  # no_pollution <desc>: no package manager ran, nothing written (the snapshot
                  # also catches a stray pnpm-lock.yaml; a pnpm fixture's own lock is in BEFORE)
  if [ ! -s "$STUB_LOG" ] && [ ! -e "$REPO/svc/pnpm-workspace.yaml" ] \
     && [ "$BEFORE" = "$(snapshot)" ]; then PASS=$((PASS+1))
  else FAIL=$((FAIL+1)); echo "  FAIL: $1"; cat "$STUB_LOG" | sed 's/^/        called: /'; ls "$REPO/svc" | sed 's/^/        svc\//'; fi
}

# 19. Bun directory: type-checks, writes nothing, calls no package manager
ts_repo bun.lock clean; BEFORE=$(snapshot)
run_stubbed 0 "Bun directory type-checks clean"
no_pollution "Bun directory was polluted (pnpm-lock.yaml/pnpm-workspace.yaml/node_modules) or a package manager ran"

# 20. npm directory: the same
ts_repo package-lock.json clean; BEFORE=$(snapshot)
run_stubbed 0 "npm directory type-checks clean"
no_pollution "npm directory was polluted or a package manager ran"

# 21. a genuine type error still blocks, in Bun, npm and pnpm directories
for lock in bun.lock package-lock.json pnpm-lock.yaml; do
  ts_repo "$lock" broken; BEFORE=$(snapshot)
  run_stubbed 2 "a real type error blocks in a $lock directory"
  echo "$LAST_OUT" | grep -q 'TypeScript errors in' && PASS=$((PASS+1)) \
    || { FAIL=$((FAIL+1)); echo "  FAIL: $lock block must report the compiler output"; }
done

# 22. pnpm directory with a local tsc: clean passes, and pnpm is still not needed for it
ts_repo pnpm-lock.yaml clean; BEFORE=$(snapshot)
run_stubbed 0 "pnpm directory type-checks clean"
no_pollution "pnpm directory ran a package manager although a local tsc exists"

# 23. no pnpm at all (Bun-only machine) must not skip the check: the gate is per directory
ts_repo bun.lock broken
out=$(echo '{}' | PATH="/usr/bin:/bin" CLAUDE_PROJECT_DIR="$REPO" bash "$HOOK" 2>&1); rc=$?
if [ "$rc" = 2 ]; then PASS=$((PASS+1)); else FAIL=$((FAIL+1)); echo "  FAIL: a machine without pnpm must still check (exit $rc)"; echo "$out" | sed 's/^/        /'; fi

# 24. a project `typecheck` script is preferred, through the directory's own package manager
ts_repo bun.lock clean
printf '{"name":"svc","scripts":{"typecheck":"tsc -b"}}\n' > svc/package.json
git commit -qam "chore: typecheck script"; echo 'export const w = 3' >> svc/a.ts
run_stubbed 0 "a typecheck script runs"
grep -q 'bun run typecheck' "$STUB_LOG" && PASS=$((PASS+1)) \
  || { FAIL=$((FAIL+1)); echo "  FAIL: typecheck script must run via bun (log: $(cat "$STUB_LOG"))"; }

# 25. no installed typescript → advisory, never a block, and nothing fetched
ts_repo bun.lock clean; rm -rf svc/node_modules; git add -A; git commit -qm "chore: no node_modules" 2>/dev/null
echo 'export const v = 4' >> svc/a.ts; : > "$STUB_LOG"
run_stubbed 0 "no installed typescript is an advisory, not a block"
echo "$LAST_OUT" | grep -q 'advisory' && PASS=$((PASS+1)) \
  || { FAIL=$((FAIL+1)); echo "  FAIL: missing typescript must be reported as advisory"; }
# the stub bun runs `--version` and "succeeds", so the only thing that may happen is a no-install exec
grep -qE 'bun x --no-install' "$STUB_LOG" || [ ! -s "$STUB_LOG" ] && PASS=$((PASS+1)) \
  || { FAIL=$((FAIL+1)); echo "  FAIL: fallback must not install (log: $(cat "$STUB_LOG"))"; }

# 26. the old gate and the old unconditional pnpm call must not come back
if grep -q 'command -v pnpm >/dev/null 2>&1 \]' "$HOOK" || grep -qE '^[^#]*pnpm exec tsc --noEmit\)' "$HOOK"; then
  FAIL=$((FAIL+1)); echo "  FAIL: hook is gated on / hardcodes pnpm again"
else PASS=$((PASS+1)); fi

echo
echo "stop-verify: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
