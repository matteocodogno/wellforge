#!/usr/bin/env bash
# Regression matrix for scripts/release.sh, run in a throwaway clone with a local bare
# "origin" — nothing here can reach the real remote or tag the real repo.
#
# The working tree is overlaid onto the clone (every changed, staged or untracked file), so the
# script under test is the one on disk, not the last committed one.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL: %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2" | sed 's/^/        /'; }
expect() { if [ "$1" = "$2" ]; then ok; else bad "$3 (want '$2', got '$1')" "${4:-}"; fi; }

T="$(mktemp -d)"
trap 'rm -rf -- "${T:?}"' EXIT
# The clone carries this repo's mise.toml, which mise has never been asked to trust there;
# untrusted, every `python3` through a mise shim errors. The clone needs no mise at all.
export MISE_IGNORED_CONFIG_PATHS="$T"
git clone -q --bare --no-tags "$ROOT" "$T/origin.git"
# The origin needs a `main` at the tree under test. A CI checkout of a TAG is a detached HEAD
# with no local main, so the bare clone had none and every push in this file failed
# ("src refspec main does not match any") — green on a laptop, red on both release tags.
git -C "$T/origin.git" update-ref refs/heads/main "$(git -C "$ROOT" rev-parse HEAD)"
git -C "$T/origin.git" symbolic-ref HEAD refs/heads/main
git clone -q "$T/origin.git" "$T/w" 2>/dev/null
W="$T/w"; cd "$W" || exit 1
git config user.email t@t; git config user.name T; git config commit.gpgsign false; git config tag.gpgsign false
git config core.hooksPath /dev/null
# Changed vs HEAD (staged OR not — `ls-files --modified` missed staged files) plus untracked;
# a file deleted in the working tree is deleted in the clone too.
( cd "$ROOT" && { git diff --name-only HEAD; git ls-files --others --exclude-standard; } ) | sort -u | while IFS= read -r f; do
  if [ -f "$ROOT/$f" ]; then mkdir -p "$(dirname "$W/$f")"; cp "$ROOT/$f" "$W/$f"; else rm -f -- "$W/$f"; fi
done
git add -A >/dev/null; git commit -qm "test: overlay working tree" --allow-empty; git push -q origin main

pv() { python3 -c 'import json;print(json.load(open("wellforge-plugin/.claude-plugin/plugin.json"))["version"])'; }
tv() { awk '/^template_version:/{f=1} f&&/default:/{gsub(/[" ]/,"",$2);print $2;exit}' copier.yml; }
nextpatch() { python3 -c 'import sys;M,m,p=sys.argv[1].split(".");print(f"{M}.{m}.{int(p)+1}")' "$1"; }
nextminor() { python3 -c 'import sys;M,m,p=sys.argv[1].split(".");print(f"{M}.{int(m)+1}.0")' "$1"; }
note() { printf '\n## %s — test entry\n\nNothing to do.\n' "$2" >> "$1"; git commit -qam "docs: $2 notes"; git push -q origin main; }

echo "release.sh matrix"

# 1. plan only changes nothing
# major, not patch: the next patch may already have its entry (it is written with the
# change, before the release) — that is how this case went red on main at ccdca85.
P0="$(pv)"; out="$(scripts/release.sh plugin major 2>&1)"; rc=$?
expect "$rc" 1 "plan without a migration entry refuses" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "plan leaves the tree clean"

NP="$(nextpatch "$P0")"; note wellforge-plugin/PLUGIN-MIGRATIONS.md "$NP"
out="$(scripts/release.sh plugin patch 2>&1)"; rc=$?
expect "$rc" 0 "plan with the entry succeeds" "$out"
expect "$(pv)" "$P0" "plan does not bump"

# 2. a missing entry is refused before anything changes
# (major: the next minor may legitimately have its entry already, written with the change)
out="$(scripts/release.sh plugin major --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "--execute without the version's entry refuses" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "...and touches nothing"

# 3. the plugin release
out="$(scripts/release.sh plugin patch --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 0 "plugin patch --execute" "$out"
expect "$(pv)" "$NP" "plugin.json bumped"
expect "$(python3 -c 'import json;d=json.load(open(".claude-plugin/marketplace.json"))["plugins"][0];print(d["version"],d["source"]["ref"])')" \
       "$NP plugin-v$NP" "marketplace version + ref bumped"
grep -q "plugin-v$NP" AGENTS.md && grep -q "plugin \`$NP\`" AGENTS.md && ok || bad "AGENTS.md versions line bumped"
grep -q "\"version\": \"$NP\"" wellforge-codex-plugin/plugin.json && ok || bad "Codex package regenerated"
expect "$(git tag --points-at HEAD)" "plugin-v$NP" "exactly one tag, on the release commit"
expect "$(git log -1 --format=%s)" "chore(plugin): release $NP" "release commit message"
expect "$(git status --porcelain --untracked-files=no)" "" "tree clean after the release"
git tag -n1 "plugin-v$NP" | grep -q "evals:" && ok || bad "plugin tag message carries the evals status" "$(git tag -n1 "plugin-v$NP")"

# 4. the same version again is refused (tag exists)
git push -q origin main; git push -q origin "plugin-v$NP"
note wellforge-plugin/PLUGIN-MIGRATIONS.md "x"   # any commit, so HEAD is not the tagged one
out="$(scripts/release.sh plugin "$NP" --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "an existing version is refused" "$out"

# 5. a tag only on origin is refused too
git tag -d "plugin-v$NP" >/dev/null
NP2="$(nextpatch "$NP")"; note wellforge-plugin/PLUGIN-MIGRATIONS.md "$NP2"
git tag "plugin-v$NP2" origin/main >/dev/null 2>&1; git push -q origin "plugin-v$NP2"; git tag -d "plugin-v$NP2" >/dev/null
out="$(scripts/release.sh plugin "$NP2" --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "a tag present only on origin is refused" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "...and touches nothing"

# 6. the template release
T0="$(tv)"; NT="$(nextminor "$T0")"; note docs/TEMPLATE-MIGRATIONS.md "v$NT"
out="$(scripts/release.sh template minor --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 0 "template minor --execute" "$out"
expect "$(tv)" "$NT" "copier.yml template_version bumped"
grep -q "\`v$NT\` (template series" AGENTS.md && ok || bad "AGENTS.md template version bumped"
expect "$(git tag --points-at HEAD)" "v$NT" "template tag on the release commit"

# 6b. the gates release — a plain counter, cut only when something a project pins changed
G0="$(grep -m1 -o '`gates-v[0-9]*`' AGENTS.md | tr -dc 0-9)"; NG=$((G0 + 1))
git tag "gates-v$G0" >/dev/null; git push -q origin "gates-v$G0"
out="$(scripts/release.sh gates minor 2>&1)"; rc=$?
expect "$rc" 1 "gates with an increment is refused (it is a counter)" "$out"
out="$(scripts/release.sh gates --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "gates with nothing changed since the last gates tag is refused" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "...and touches nothing"
git commit -q --allow-empty -m "ci: unrelated"; echo "# x" >> .github/workflows/ci.yml; git commit -qam "ci: own workflow"
git push -q origin main
out="$(scripts/release.sh gates --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "a change to ci.yml alone (not a reusable workflow) is no gates release" "$out"
echo "# x" >> gates/hooks/pre-push; git commit -qam "fix(gates): hook"; git push -q origin main
out="$(scripts/release.sh gates 2>&1)"; rc=$?
expect "$rc" 0 "gates plan lists what changed" "$out"
printf '%s' "$out" | grep -q "gates/hooks/pre-push" && ok || bad "gates plan names the changed file" "$out"
git tag -d "gates-v$G0" >/dev/null   # only on origin now: the series must still be found there
out="$(scripts/release.sh gates --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 0 "gates --execute" "$out"
expect "$(git tag --points-at HEAD)" "gates-v$NG" "gates tag is the next integer, alone on its commit"
grep -q "\`gates-v$NG\`" AGENTS.md && ok || bad "AGENTS.md gates version bumped"
expect "$(git log -1 --format=%s)" "chore(gates): release gates-v$NG" "gates release commit message"
expect "$(git diff --name-only HEAD~1 HEAD)" "AGENTS.md" "the gates release commit touches AGENTS.md only (copier.yml is the template's)"

# 7. behind origin is refused
git reset -q --hard HEAD~1; git push -qf origin "$(git rev-parse HEAD~0)":refs/heads/tmp 2>/dev/null
git fetch -q origin; git reset -q --hard origin/main
git commit -q --allow-empty -m "chore: other"; git push -q origin main; git reset -q --hard HEAD~1
out="$(scripts/release.sh template patch --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "behind origin/main is refused" "$out"

# 8. CI on HEAD gates --execute — v0.13.0 and plugin-v2.63.0 were cut on a main already red in
# generated-gates, which step 4's --quick check-all cannot see. A fake gh answers for GitHub.
git fetch -q origin; git reset -q --hard origin/main
mkdir -p "$T/bin"
fakegh() { printf '#!/bin/sh\necho "%s"\n' "$1" > "$T/bin/gh"; chmod +x "$T/bin/gh"; }
runci() { PATH="$T/bin:$PATH" scripts/release.sh template patch "$@" 2>&1; }
fakegh "completed|failure|42"
out="$(runci --execute)"; rc=$?
expect "$rc" 1 "--execute on a red CI is refused" "$out"
printf '%s' "$out" | grep -q "gh run rerun 42 --failed" && ok || bad "the refusal names the rerun command" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "...and touches nothing"
expect "$(git tag --points-at HEAD)" "" "...and tags nothing"
out="$(runci)"
printf '%s' "$out" | grep -q "would refuse" && ok || bad "a plan on a red CI reports that --execute would refuse" "$out"
printf '%s' "$out" | grep -q "\[2/6\]" && ok || bad "...and carries on planning" "$out"
fakegh "in_progress||7"
out="$(runci --execute)"; rc=$?
expect "$rc" 1 "--execute while CI is still running is refused" "$out"
printf '%s' "$out" | grep -q "gh run watch 7" && ok || bad "...naming the run to watch" "$out"
fakegh ""
out="$(runci --execute)"; rc=$?
expect "$rc" 1 "--execute with no CI run for HEAD is refused" "$out"
fakegh "completed|success|9"
out="$(runci)"; rc=$?
printf '%s' "$out" | grep -q "CI green on" && ok || bad "a green CI is reported as such" "$out"
git commit -q --allow-empty -m "chore: unpushed"
out="$(runci --execute)"; rc=$?
expect "$rc" 1 "--execute on a commit not yet on origin is refused (CI never saw it)" "$out"
git reset -q --hard origin/main

echo
echo "release.sh: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
