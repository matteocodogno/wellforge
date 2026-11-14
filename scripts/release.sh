#!/usr/bin/env bash
# release.sh — cut a PLUGIN (`plugin-vX.Y.Z`), TEMPLATE (`vX.Y.Z`) or GATES (`gates-vN`) release.
#
#   scripts/release.sh plugin   patch|minor|major|X.Y.Z             # plan only (default)
#   scripts/release.sh plugin   minor --execute                     # bump, check, commit, tag
#   scripts/release.sh template minor --execute --push              # ...and push main + the tag
#   scripts/release.sh gates    --execute --push                    # gates: always the next N
#   ...  --skip-ci                  # tag without a green CI run on HEAD (banner + tag message)
#
# The CLI has its own script (release-cli.sh, two commits because of the Formula sha) —
# `mise run release:cli` runs it. Plugin and template had only a prose checklist in
# /wellforge:release, executed by hand — every step a chance to miss one of the four places
# the plugin version lives, or to tag a tree nobody checked. Mechanical steps belong in a
# script; the prose stays the WHY (docs/VERSIONING.md) and the judgement (which increment).
# The gates series was a bare tag cut by hand, with no check that anything a consumer pins
# had changed, that the tag was free, or that the commit carried no other series' tag.
#
# What it does, in order, and refuses rather than guesses at each step:
#   1. preflight  on main, clean tree, level with origin/main, tag free locally AND on origin,
#                 and the `ci` workflow GREEN on HEAD — the only place every preset's own gates
#                 run. Step 4 is --quick and cannot see them: v0.13.0 and plugin-v2.63.0 were
#                 cut on a main already red in generated-gates (pulumi-gcp-ts).
#   2. notes      the migration entry for this version exists (PLUGIN- / TEMPLATE-MIGRATIONS):
#                 it is written with the change, not at release time, so a missing one is a
#                 change nobody examined — refused, not stubbed. Gates: something a consumer
#                 pins (gates/, a reusable workflow) changed since the last gates tag
#   3. bump       plugin: plugin.json, marketplace.json version + source.ref, the AGENTS.md
#                 versions line, the Codex install ref, then regenerates the Codex package
#                 template: copier.yml's template_version default, the AGENTS.md versions line
#                 gates: the AGENTS.md versions line only — copier.yml's gates_ref default is
#                 a TEMPLATE file, moved by a template release, never in this commit
#   4. prove      scripts/check-all.sh on the BUMPED tree — the tree that gets tagged
#   5. commit+tag `chore(<series>): release …`, an annotated tag, and exactly one tag on it
#   6. push       only with --push: main first, then the tag (release-guard runs on the tag)
#
# Anything that stops it between 3 and 5 restores the tree, so a retry starts clean.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

SERIES=""; BUMP=""; EXECUTE=0; PUSH=0; SKIP_CHECKS=0; SKIP_CI=0; TOUCHED=()
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
    plugin|template|gates) SERIES="$1"; shift ;;
    patch|minor|major) BUMP="$1"; shift ;;
    [0-9]*.[0-9]*.[0-9]*) BUMP="$1"; shift ;;
    --execute) EXECUTE=1; shift ;;
    --push) PUSH=1; shift ;;
    # For the script's own test matrix, which cannot afford a full check-all per case.
    # Also skips the CI lookup: the matrix's origin is a local bare repo with no Actions.
    --skip-checks) SKIP_CHECKS=1; SKIP_CI=1; shift ;;
    --skip-ci) SKIP_CI=1; shift ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[ -n "$SERIES" ] || die "which series? plugin | template"
if [ "$SERIES" = gates ]; then
  [ -z "$BUMP" ] || die "gates is a plain counter — no increment: scripts/release.sh gates [--execute] [--push]"
else
  [ -n "$BUMP" ] || die "which version? patch | minor | major | X.Y.Z"
fi
[ "$PUSH" -eq 1 ] && [ "$EXECUTE" -eq 0 ] && die "--push needs --execute"

# ── current version and the next one ─────────────────────────────────────────────────
if [ "$SERIES" = plugin ]; then
  cur="$(python3 -c 'import json;print(json.load(open("wellforge-plugin/.claude-plugin/plugin.json"))["version"])')"
elif [ "$SERIES" = gates ]; then
  # The highest gates-vN, local or on origin: a clone without tags must not conclude the
  # series starts over.
  cur="$( { git tag -l 'gates-v*'; git ls-remote --tags --refs origin 'gates-v*' 2>/dev/null | sed 's#.*refs/tags/##'; } \
          | sed -n 's/^gates-v\([0-9][0-9]*\)$/\1/p' | sort -n | tail -1)"
else
  cur="$(awk '/^template_version:/{f=1} f&&/default:/{gsub(/[" ]/,"",$2);print $2;exit}' copier.yml)"
fi
[ -n "$cur" ] || die "cannot read the current $SERIES version"
case "$BUMP" in
  "") next=$((cur + 1)) ;;
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
case "$SERIES" in plugin) tag="plugin-v$next" ;; gates) tag="gates-v$next" ;; *) tag="v$next" ;; esac

say "release $SERIES: $cur -> $next   (tag $tag)"
if [ "$EXECUTE" -eq 0 ]; then
  say "plan only — re-run with --execute (and --push to publish). Steps:"
  sed -n '18,34p' "$0" | sed 's/^# \{0,1\}/  /'
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

# CI on the commit being released. A release commit only bumps version strings, so HEAD's run
# is the verdict on everything the tag will carry.
sha="$(git rev-parse HEAD)"
# A plan reports what --execute would refuse; only --execute refuses.
cifail() { if [ "$EXECUTE" -eq 1 ]; then die "$*"; else say "  note: --execute would refuse — $*"; fi; }
if [ "$SKIP_CI" -eq 1 ]; then
  say "  CI NOT CHECKED (--skip-ci) — the tag message will say so"
else
  [ "$(git rev-parse origin/main)" = "$sha" ] \
    || cifail "HEAD is not on origin yet, so CI has not run on it — push main, wait for CI (gh run watch), then release"
  command -v gh >/dev/null 2>&1 || cifail "gh is not installed — cannot read CI on HEAD (--skip-ci to tag anyway)"
  if ! ci="$(gh run list --workflow ci.yml --branch main --commit "$sha" --limit 1 \
          --json databaseId,status,conclusion --jq '.[0] | "\(.status)|\(.conclusion)|\(.databaseId)"' 2>/dev/null)"; then
    cifail "cannot read CI from GitHub (gh auth status?) — --skip-ci to tag anyway"
  else
  IFS='|' read -r ci_status ci_concl ci_id <<<"$ci"
  case "$ci_status/$ci_concl" in
    completed/success) say "  ok — CI green on $(git rev-parse --short HEAD) (run $ci_id)" ;;
    /*|null/*) cifail "no CI run for $(git rev-parse --short HEAD) on main yet — wait for it (gh run list --branch main)" ;;
    completed/*) cifail "CI is $ci_concl on $(git rev-parse --short HEAD) — red means no tag. Fix it, or for a transient failure: gh run rerun $ci_id --failed" ;;
    *) cifail "CI is still $ci_status on $(git rev-parse --short HEAD) — gh run watch $ci_id, then release" ;;
  esac
  fi
fi

# ── 2. migration notes — gates: what changed for the projects that pin it ────────────
if [ "$SERIES" = gates ]; then
  step 2 "what changed since gates-v$cur"
  git rev-parse -q --verify "refs/tags/gates-v$cur" >/dev/null \
    || git fetch -q origin "refs/tags/gates-v$cur:refs/tags/gates-v$cur" 2>/dev/null \
    || die "cannot read gates-v$cur to compare against"
  # What a consumer pins: gates/ and every reusable workflow (`on: workflow_call`). ci.yml,
  # pages.yml and release.yml are this repo's own and do not count.
  reusable=()
  for f in .github/workflows/*.yml; do
    [ "$f" = .github/workflows/ci.yml ] && continue
    grep -qE '^[[:space:]]+workflow_call:' "$f" && reusable+=("$f")
  done
  changed="$(git diff --name-only "gates-v$cur" HEAD -- gates "${reusable[@]}")"
  [ -n "$changed" ] || die "nothing under gates/ or in a reusable workflow changed since gates-v$cur — no gates release to cut"
  printf '%s\n' "$changed" | sed 's/^/  /'
  nchanged="$(printf '%s\n' "$changed" | wc -l | tr -d ' ')"
  say "  ok — $nchanged file(s) the projects get by pinning $tag"
else
  step 2 "migration notes"
  if [ "$SERIES" = plugin ]; then
    notes=wellforge-plugin/PLUGIN-MIGRATIONS.md; head_re="^## ${next//./\\.}( |$)"; head_shown="$next"
  else
    notes=docs/TEMPLATE-MIGRATIONS.md; head_re="^## v${next//./\\.}( |$)"; head_shown="v$next"
  fi
  grep -qE "$head_re" "$notes" || die "$notes has no '## $head_shown' entry — write it (even 'nothing to do') before releasing"
  say "  ok — $notes has the $head_shown entry"
fi

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
elif [ "$SERIES" = gates ]; then
  TOUCHED=(AGENTS.md)
  python3 - "$cur" "$next" <<'PY' || die "bump failed"
import sys
cur, nxt = sys.argv[1:]
lines = open("AGENTS.md").read().split("\n")
i = next(k for k, l in enumerate(lines) if l.startswith("- Latest tags:"))
for k in range(i, i + 6):
    lines[k] = lines[k].replace(f"`gates-v{cur}`", f"`gates-v{nxt}`")
if f"`gates-v{nxt}`" not in "\n".join(lines[i:i + 6]):
    sys.exit("AGENTS.md versions paragraph did not take the new gates version")
open("AGENTS.md", "w").write("\n".join(lines))
PY
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
  # First NON-EMPTY line: the stale report opens with a blank line, and `head -1` tagged
  # plugin-v2.60.0 with an empty evals status.
  evals="$(scripts/check-evals-fresh.sh 2>/dev/null | grep -m1 -v '^[[:space:]]*$')"
  tag_msg="plugin $next — $evals"
elif [ "$SERIES" = gates ]; then
  msg="chore(gates): release gates-v$next"; tag_msg="gates v$next — $nchanged file(s) changed since gates-v$cur"
else
  msg="chore(template): release v$next"; tag_msg="template v$next"
fi
[ "$SKIP_CI" -eq 1 ] && [ "$SKIP_CHECKS" -eq 0 ] && tag_msg="$tag_msg (CI on the released commit NOT checked: --skip-ci)"
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
if [ "$SERIES" = gates ]; then
  dflt="$(awk '/^gates_ref:/{f=1} f&&/default:/{print $2;exit}' copier.yml)"
  [ "$dflt" = "$tag" ] || say "  note: new scaffolds still pin $dflt (copier.yml gates_ref default) — moving it is a template release"
fi
