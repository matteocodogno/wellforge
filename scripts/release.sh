#!/usr/bin/env bash
# release.sh — cut a PLUGIN (`plugin-vX.Y.Z`) or TEMPLATE (`vX.Y.Z`) release of this repo.
#
#   scripts/release.sh plugin   patch|minor|major|X.Y.Z             # plan only (default)
#   scripts/release.sh plugin   minor --execute                     # bump, check, commit, tag
#   scripts/release.sh template minor --execute --push              # ...and push main + the tag
#
# The CLI has its own script (release-cli.sh, two commits because of the Formula sha); the
# gates series is a bare `gates-vN` tag. These two series had only a prose checklist in
# /wellforge:release, executed by hand — every step a chance to miss one of the four places
# the plugin version lives, or to tag a tree nobody checked. Mechanical steps belong in a
# script; the prose stays the WHY (docs/VERSIONING.md) and the judgement (which increment).
#
# What it does, in order, and refuses rather than guesses at each step:
#   1. preflight  on main, clean tree, level with origin/main, tag free locally AND on origin
#   2. notes      the migration entry for this version exists (PLUGIN- / TEMPLATE-MIGRATIONS):
#                 it is written with the change, not at release time, so a missing one is a
#                 change nobody examined — refused, not stubbed
#   3. bump       plugin: plugin.json, marketplace.json version + source.ref, the AGENTS.md
#                 versions line, the Codex install ref, then regenerates the Codex package
#                 template: copier.yml's template_version default, the AGENTS.md versions line
#   4. prove      scripts/check-all.sh on the BUMPED tree — the tree that gets tagged
#   5. commit+tag `chore(<series>): release …`, an annotated tag, and exactly one tag on it
#   6. push       only with --push: main first, then the tag (release-guard runs on the tag)
#
# Anything that stops it between 3 and 5 restores the tree, so a retry starts clean.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

SERIES=""; BUMP=""; EXECUTE=0; PUSH=0; SKIP_CHECKS=0; TOUCHED=()
say() { printf '%s\n' "$*"; }
step() { printf '\n[%s/6] %s\n' "$1" "$2"; }
die() {
  printf 'error: %s\n' "$*" >&2
  if [ "${#TOUCHED[@]}" -gt 0 ]; then
    git checkout -q -- "${TOUCHED[@]}" 2>/dev/null
    git clean -qfd -- wellforge-codex-plugin 2>/dev/null
    printf '       (the uncommitted bump was reverted — the tree is as it was)\n' >&2
  fi
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    plugin|template) SERIES="$1"; shift ;;
    patch|minor|major) BUMP="$1"; shift ;;
    [0-9]*.[0-9]*.[0-9]*) BUMP="$1"; shift ;;
    --execute) EXECUTE=1; shift ;;
    --push) PUSH=1; shift ;;
    # For the script's own test matrix, which cannot afford a full check-all per case.
    --skip-checks) SKIP_CHECKS=1; shift ;;
    -h|--help) sed -n '2,7p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[ -n "$SERIES" ] || die "which series? plugin | template"
[ -n "$BUMP" ] || die "which version? patch | minor | major | X.Y.Z"
[ "$PUSH" -eq 1 ] && [ "$EXECUTE" -eq 0 ] && die "--push needs --execute"

# ── current version and the next one ─────────────────────────────────────────────────
if [ "$SERIES" = plugin ]; then
  cur="$(python3 -c 'import json;print(json.load(open("wellforge-plugin/.claude-plugin/plugin.json"))["version"])')"
else
  cur="$(awk '/^template_version:/{f=1} f&&/default:/{gsub(/[" ]/,"",$2);print $2;exit}' copier.yml)"
fi
[ -n "$cur" ] || die "cannot read the current $SERIES version"
case "$BUMP" in
  patch|minor|major)
    next="$(python3 - "$cur" "$BUMP" <<'PY'
import sys
M, m, p = map(int, sys.argv[1].split("."))
b = sys.argv[2]
print(f"{M+1}.0.0" if b == "major" else f"{M}.{m+1}.0" if b == "minor" else f"{M}.{m}.{p+1}")
PY
)" ;;
  *) next="$BUMP" ;;
esac
python3 -c "import sys;a,b=(tuple(map(int,v.split('.'))) for v in sys.argv[1:]);sys.exit(0 if b>a else 1)" "$cur" "$next" \
  || die "$next is not newer than the current $SERIES version $cur"
if [ "$SERIES" = plugin ]; then tag="plugin-v$next"; else tag="v$next"; fi

say "release $SERIES: $cur -> $next   (tag $tag)"
if [ "$EXECUTE" -eq 0 ]; then
  say "plan only — re-run with --execute (and --push to publish). Steps:"
  sed -n '14,24p' "$0" | sed 's/^# \{0,1\}/  /'
fi

# ── 1. preflight ──────────────────────────────────────────────────────────────────────
step 1 "preflight"
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || die "not on main"
[ -z "$(git status --porcelain --untracked-files=no)" ] || die "tracked files are modified — commit or stash first"
git fetch -q origin main 2>/dev/null || die "cannot fetch origin/main"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] \
  || say "  note: main is not level with origin/main ($(git rev-list --count origin/main..HEAD) ahead, $(git rev-list --count HEAD..origin/main) behind)"
[ "$(git rev-list --count HEAD..origin/main)" -eq 0 ] || die "main is behind origin/main — pull --rebase first"
git rev-parse -q --verify "refs/tags/$tag" >/dev/null && die "tag $tag already exists locally"
[ -z "$(git ls-remote --tags origin "refs/tags/$tag" 2>/dev/null)" ] || die "tag $tag already exists on origin"
say "  ok — main, clean, tag $tag free"

# ── 2. migration notes ───────────────────────────────────────────────────────────────
step 2 "migration notes"
if [ "$SERIES" = plugin ]; then
  notes=docs/PLUGIN-MIGRATIONS.md; head_re="^## ${next//./\\.}( |$)"
else
  notes=docs/TEMPLATE-MIGRATIONS.md; head_re="^## v${next//./\\.}( |$)"
fi
[ "$SERIES" = template ] && head_shown="v$next" || head_shown="$next"
grep -qE "$head_re" "$notes" || die "$notes has no '## $head_shown' entry — write it (even 'nothing to do') before releasing"
say "  ok — $notes has the $head_shown entry"

[ "$EXECUTE" -eq 1 ] || { say; say "plan only: nothing changed."; exit 0; }

# ── 3. bump ───────────────────────────────────────────────────────────────────────────
step 3 "bump $cur -> $next"
if [ "$SERIES" = plugin ]; then
  TOUCHED=(wellforge-plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json AGENTS.md
           adapters/codex/README.md wellforge-codex-plugin)
  python3 - "$cur" "$next" <<'PY' || die "bump failed"
import sys, re
cur, nxt = sys.argv[1:]
def sub(path, pairs, need):
    s = open(path).read(); n0 = s
    for a, b in pairs: s = s.replace(a, b)
    for b in need:
        if b not in s: sys.exit(f"{path}: '{b}' did not take")
    if s == n0: sys.exit(f"{path}: nothing changed")
    open(path, "w").write(s)
sub("wellforge-plugin/.claude-plugin/plugin.json", [(f'"version": "{cur}"', f'"version": "{nxt}"')], [f'"version": "{nxt}"'])
sub(".claude-plugin/marketplace.json", [(f'"version": "{cur}"', f'"version": "{nxt}"'),
    (f'"ref": "plugin-v{cur}"', f'"ref": "plugin-v{nxt}"')], [f'"version": "{nxt}"', f'"ref": "plugin-v{nxt}"'])
sub("adapters/codex/README.md", [(f"--ref plugin-v{cur}", f"--ref plugin-v{nxt}")], [f"--ref plugin-v{nxt}"])
# Only the versions paragraph: every other version in AGENTS.md is history.
lines = open("AGENTS.md").read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("- Latest tags:"))
for k in range(i, i + 6):
    lines[k] = lines[k].replace(f"plugin-v{cur}", f"plugin-v{nxt}").replace(f"plugin `{cur}`", f"plugin `{nxt}`")
para = "\n".join(lines[i:i + 6])
if f"plugin-v{nxt}" not in para or f"plugin `{nxt}`" not in para:
    sys.exit("AGENTS.md versions paragraph did not take the new plugin version")
open("AGENTS.md", "w").write("\n".join(lines))
PY
  uv run -q --with pyyaml python adapters/codex/generate.py --package wellforge-codex-plugin \
    --marketplace .agents/plugins/marketplace.json >/dev/null 2>&1 || die "Codex package regeneration failed"
else
  TOUCHED=(copier.yml AGENTS.md)
  python3 - "$cur" "$next" <<'PY' || die "bump failed"
import sys, re
cur, nxt = sys.argv[1:]
s = open("copier.yml").read()
s2 = re.sub(r'(template_version:\n(?:  .*\n)*?  default: )"' + re.escape(cur) + '"', r'\g<1>"' + nxt + '"', s, count=1)
if s2 == s: sys.exit("copier.yml: template_version default did not take")
open("copier.yml", "w").write(s2)
lines = open("AGENTS.md").read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("- Latest tags:"))
lines[i] = lines[i].replace(f"`v{cur}` (template series", f"`v{nxt}` (template series")
if f"`v{nxt}` (template series" not in lines[i]:
    sys.exit("AGENTS.md versions line did not take the new template version")
open("AGENTS.md", "w").write("\n".join(lines))
PY
fi
git --no-pager diff --stat
say "  ok"

# ── 4. prove the bumped tree ──────────────────────────────────────────────────────────
step 4 "scripts/check-all.sh on the bumped tree"
if [ "$SKIP_CHECKS" -eq 1 ]; then
  say "  SKIPPED (--skip-checks) — this tag was not proven; do not push it"
else
  scripts/check-all.sh --quick || die "self-tests are red — red means no tag"
fi

# ── 5. commit + tag ───────────────────────────────────────────────────────────────────
step 5 "commit and tag"
if [ "$SERIES" = plugin ]; then
  msg="chore(plugin): release $next"
  evals="$(scripts/check-evals-fresh.sh 2>/dev/null | head -1)"
  tag_msg="plugin $next — $evals"
else
  msg="chore(template): release v$next"; tag_msg="template v$next"
fi
git add -A -- "${TOUCHED[@]}" || die "git add failed"
git commit -q -m "$msg" || die "commit failed"
TOUCHED=()
git tag -a "$tag" -m "$tag_msg" || die "tag failed (the release commit stays — tag it by hand)"
others="$(git tag --points-at HEAD | grep -vx "$tag" || true)"
[ -z "$others" ] || die "HEAD carries another tag too ($others) — never two series on one commit"
say "  ok — $(git log --oneline -1), tag $tag"

# ── 6. push ───────────────────────────────────────────────────────────────────────────
step 6 "push"
if [ "$PUSH" -eq 0 ]; then
  say "  not pushed. To publish:  git push origin main && git push origin $tag"
  exit 0
fi
git push -q origin main || die "push of main failed — the tag is still local"
git push -q origin "$tag" || die "push of $tag failed (main is pushed) — retry: git push origin $tag"
say "  ok — pushed. release-guard runs on the tag: gh run list --branch $tag"
