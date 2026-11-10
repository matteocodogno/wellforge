#!/usr/bin/env bash
# Regression matrix for scripts/release.sh, run in a throwaway clone with a local bare
# "origin" — nothing here can reach the real remote or tag the real repo.
#
# The working tree is overlaid onto the clone (every modified or untracked file), so the
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
( cd "$ROOT" && git ls-files --modified --others --exclude-standard ) | while IFS= read -r f; do
  [ -f "$ROOT/$f" ] && { mkdir -p "$(dirname "$W/$f")"; cp "$ROOT/$f" "$W/$f"; }
done
git add -A >/dev/null; git commit -qm "test: overlay working tree" --allow-empty; git push -q origin main

pv() { python3 -c 'import json;print(json.load(open("wellforge-plugin/.claude-plugin/plugin.json"))["version"])'; }
tv() { awk '/^template_version:/{f=1} f&&/default:/{gsub(/[" ]/,"",$2);print $2;exit}' copier.yml; }
nextpatch() { python3 -c 'import sys;M,m,p=sys.argv[1].split(".");print(f"{M}.{m}.{int(p)+1}")' "$1"; }
nextminor() { python3 -c 'import sys;M,m,p=sys.argv[1].split(".");print(f"{M}.{int(m)+1}.0")' "$1"; }
note() { printf '\n## %s — test entry\n\nNothing to do.\n' "$2" >> "docs/$1"; git commit -qam "docs: $2 notes"; git push -q origin main; }

echo "release.sh matrix"

# 1. plan only changes nothing
P0="$(pv)"; out="$(scripts/release.sh plugin patch 2>&1)"; rc=$?
expect "$rc" 1 "plan without a migration entry refuses" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "plan leaves the tree clean"

NP="$(nextpatch "$P0")"; note PLUGIN-MIGRATIONS.md "$NP"
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
note PLUGIN-MIGRATIONS.md "x"   # any commit, so HEAD is not the tagged one
out="$(scripts/release.sh plugin "$NP" --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "an existing version is refused" "$out"

# 5. a tag only on origin is refused too
git tag -d "plugin-v$NP" >/dev/null
NP2="$(nextpatch "$NP")"; note PLUGIN-MIGRATIONS.md "$NP2"
git tag "plugin-v$NP2" origin/main >/dev/null 2>&1; git push -q origin "plugin-v$NP2"; git tag -d "plugin-v$NP2" >/dev/null
out="$(scripts/release.sh plugin "$NP2" --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "a tag present only on origin is refused" "$out"
expect "$(git status --porcelain --untracked-files=no)" "" "...and touches nothing"

# 6. the template release
T0="$(tv)"; NT="$(nextminor "$T0")"; note TEMPLATE-MIGRATIONS.md "v$NT"
out="$(scripts/release.sh template minor --execute --skip-checks 2>&1)"; rc=$?
expect "$rc" 0 "template minor --execute" "$out"
expect "$(tv)" "$NT" "copier.yml template_version bumped"
grep -q "\`v$NT\` (template series" AGENTS.md && ok || bad "AGENTS.md template version bumped"
expect "$(git tag --points-at HEAD)" "v$NT" "template tag on the release commit"

# 7. behind origin is refused
git reset -q --hard HEAD~1; git push -qf origin "$(git rev-parse HEAD~0)":refs/heads/tmp 2>/dev/null
git fetch -q origin; git reset -q --hard origin/main
git commit -q --allow-empty -m "chore: other"; git push -q origin main; git reset -q --hard HEAD~1
out="$(scripts/release.sh template patch --skip-checks 2>&1)"; rc=$?
expect "$rc" 1 "behind origin/main is refused" "$out"

echo
echo "release.sh: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
