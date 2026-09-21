#!/usr/bin/env bash
# release-cli.sh — cut a release of the wellforge CLI (the `cli-vX.Y.Z` series).
#
#   scripts/release-cli.sh patch|minor|major|X.Y.Z      # plan only (default)
#   scripts/release-cli.sh patch --execute              # do it
#   scripts/release-cli.sh X.Y.Z --formula-only --execute
#                                                       # step 5-6 alone, for a tag that is
#                                                       # already pushed (first release, or
#                                                       # a retry after the sha step failed)
#
# The CLI has its own tag series because it used to have none: it rode the template's
# `vX.Y.Z` tags, so shipping a one-line CLI fix required a template release, which
# docs/VERSIONING.md says must carry a template change. Nobody cut one, and brew users ran
# the CLI as it stood at v0.9.0 for months.
#
# The checklist is docs/RELEASING-CLI.md. This script prints each step as it performs it,
# with the same numbers, so a reader of either can follow the other — and if they ever
# disagree, what the script did is what happened.
#
# WHY THIS TAKES TWO COMMITS, measured rather than assumed. The Formula pins the sha256 of
# GitHub's generated tarball, and that tarball does not exist until the tag is pushed. It
# is also NOT reproducible locally — for the existing v0.9.0 tag:
#
#   GitHub  b61eafcb2f37753faea37c836ecce6aa4e53ccd207ef39b719a3d04a09115bc6  (what the formula pins)
#   local   746cc34fd84f6563a3ad4c688b1c195852b3a9d7969e7d8538232b4098010441  (git archive, same tree)
#
# So: commit 1 bumps the constant and is tagged; the tag is pushed; only then can the real
# sha be fetched, and commit 2 points the Formula at it. Anyone promising a single commit
# here is either not pinning a sha or not checking it.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLI="$ROOT/scripts/wellforge"
FORMULA="$ROOT/Formula/wellforge.rb"
REMOTE_URL="https://github.com/matteocodogno/wellforge"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
# Same numbering as docs/RELEASING-CLI.md. Printed while the step runs, not after, so an
# interrupted release says where it stopped.
step() { printf '\n[%s/8] %s\n' "$1" "$2"; }

BUMP=""; EXECUTE=0; FORMULA_ONLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    patch|minor|major) BUMP="$1"; shift ;;
    [0-9]*.[0-9]*.[0-9]*) BUMP="$1"; shift ;;
    --execute) EXECUTE=1; shift ;;
    --formula-only) FORMULA_ONLY=1; shift ;;
    -h|--help) sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1 (want patch|minor|major|X.Y.Z [--execute])" ;;
  esac
done
[ -n "$BUMP" ] || die "say what to release: patch|minor|major|X.Y.Z"

cur="$(sed -n 's/^WELLFORGE_CLI_VERSION="\([^"]*\)".*/\1/p' "$CLI" | head -1)"
[ -n "$cur" ] || die "no WELLFORGE_CLI_VERSION constant in $CLI"

case "$BUMP" in
  patch|minor|major)
    IFS=. read -r MA MI PA <<EOF
$cur
EOF
    case "$BUMP" in
      major) MA=$((MA + 1)); MI=0; PA=0 ;;
      minor) MI=$((MI + 1)); PA=0 ;;
      patch) PA=$((PA + 1)) ;;
    esac
    next="$MA.$MI.$PA" ;;
  *) next="$BUMP" ;;
esac
tag="cli-v$next"
url="$REMOTE_URL/archive/refs/tags/$tag.tar.gz"

# ── preflight ────────────────────────────────────────────────────────────────
problems=0; PROBLEMS=""
note() { PROBLEMS="${PROBLEMS}  $*
"; problems=$((problems + 1)); }

[ "$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)" = "main" ] || note "not on main"
[ -z "$(git -C "$ROOT" status --porcelain)" ] || note "working tree is dirty — commit or stash first"
if [ "$FORMULA_ONLY" -eq 1 ]; then
  git -C "$ROOT" rev-parse -q --verify "refs/tags/$tag" >/dev/null \
    || note "tag $tag does not exist — --formula-only points the formula at an EXISTING tag"
else
  git -C "$ROOT" rev-parse -q --verify "refs/tags/$tag" >/dev/null && note "tag $tag already exists"
fi
# One series per commit (docs/VERSIONING.md): a second tag on this commit would make
# `git describe` answer with the wrong one, which is how a scaffold mislabels itself.
existing="$(git -C "$ROOT" tag --points-at HEAD | tr '\n' ' ')"
[ "$FORMULA_ONLY" -eq 0 ] && [ -n "$existing" ] \
  && note "HEAD already carries a tag ($existing) — never two series on one commit; commit something first"
# Nothing but the CLI and the formula may move in a CLI release.
changed="$(git -C "$ROOT" diff --name-only "$(git -C "$ROOT" describe --tags --match 'cli-v*' --abbrev=0 2>/dev/null || echo HEAD)"..HEAD 2>/dev/null \
            | grep -vE '^(scripts/wellforge|scripts/tests/wellforge\.test\.sh|Formula/wellforge\.rb|scripts/release-cli\.sh|scripts/README\.md|docs/VERSIONING\.md)$' | head -5)"

say "wellforge CLI release"
say "  current   $cur"
say "  next      $next   (tag $tag)"
say "  formula   $FORMULA"
say "  tarball   $url"
say ""
if [ -n "$changed" ]; then
  say "  note: this range also touches files outside the CLI —"
  printf '        %s\n' $changed
  say "        that is allowed, but if the CLI itself did not change, do not cut a release."
  say ""
fi
if [ "$problems" -gt 0 ]; then
  say "preflight found $problems problem(s):"
  printf '%s' "$PROBLEMS"
  say ""
fi

say "checklist (docs/RELEASING-CLI.md):"
if [ "$FORMULA_ONLY" -eq 1 ]; then
  say "  --formula-only: steps 5-7 alone, against a tag that already exists"
  say "  5. fetch   $url, compute its sha256"
  say "  6. rewrite the Formula's url/version/sha256, commit 'chore(cli): formula for $tag'"
  say "  7. smoke   brew install --build-from-source + brew test"
else
  say "  1. decide  $BUMP -> $next"
  say "  2. bump    WELLFORGE_CLI_VERSION=\"$next\" in scripts/wellforge"
  say "  3. prove   test suite, shellcheck, brew style  (before the tag)"
  say "  4. commit  'chore(cli): release $next'  +  tag $tag"
  say "  5. push    main and $tag            ← the tarball does not exist before this"
  say "  6. sha     fetch $url, rewrite the Formula, commit, push"
  say "  7. smoke   brew install --build-from-source + brew test"
fi
say "  8. audit   brew audit --strict --online, once the tap has the new commit"

if [ "$EXECUTE" -eq 0 ]; then
  say ""
  say "plan only — nothing changed. Re-run with --execute to do it."
  exit 0
fi
[ "$problems" -eq 0 ] || die "refusing to execute with $problems preflight problem(s) above"

# ── execute ──────────────────────────────────────────────────────────────────
say ""
printf 'This PUSHES a tag and two commits to %s. Type the version to confirm: ' "$REMOTE_URL"
read -r confirm
[ "$confirm" = "$next" ] || die "not confirmed (expected '$next')"

if [ "$FORMULA_ONLY" -eq 0 ]; then
step 2 "bumping WELLFORGE_CLI_VERSION to $next"
tmp="$(mktemp)"
sed "s/^WELLFORGE_CLI_VERSION=\".*\"/WELLFORGE_CLI_VERSION=\"$next\"/" "$CLI" > "$tmp" || die "sed failed"
grep -q "^WELLFORGE_CLI_VERSION=\"$next\"\$" "$tmp" || die "the constant did not take — check $CLI by hand"
cat "$tmp" > "$CLI"; rm -f "$tmp"

step 3 "proving it before the tag — test suite, shellcheck, brew style"
"$ROOT/scripts/tests/wellforge.test.sh" || die "the CLI test suite failed — not releasing this"
if command -v shellcheck >/dev/null 2>&1; then
  # -f gcc: the default format dies rendering a source line with a non-ASCII character,
  # and these scripts are full of em dashes (docs/RELEASING-CLI.md step 3).
  shellcheck -s bash --severity=warning -f gcc "$CLI" "$ROOT"/scripts/*.sh \
    || die "shellcheck rejected the scripts"
else
  say "  (shellcheck not installed — skipped, and a skip is not a pass)"
fi
if command -v brew >/dev/null 2>&1; then
  brew style "$FORMULA" || die "brew style rejected the formula"
else
  say "  (brew not installed — style/audit skipped, and a skip is not a pass)"
fi

step 4 "committing and tagging $tag"
git -C "$ROOT" add scripts/wellforge || die "git add failed"
git -C "$ROOT" commit -qm "chore(cli): release $next" || die "commit failed"
git -C "$ROOT" tag "$tag" || die "tag failed"
# One series per commit: a second tag makes `git describe` answer with the wrong one.
[ "$(git -C "$ROOT" tag --points-at HEAD | wc -l | tr -d ' ')" -eq 1 ] \
  || die "HEAD now carries more than one tag — never two series on one commit"

step 5 "pushing main and $tag — the tarball does not exist until this lands"
git -C "$ROOT" push -q origin main "$tag" || die "push failed — the tag is local; delete it with 'git tag -d $tag' if you are retrying"
fi

step 6 "fetching the tarball and hashing it — the only place the real sha comes from"
tarball="$(mktemp)"
curl -fsSL "$url" -o "$tarball" || die "could not fetch $url (is the tag pushed?)"
sha="$( { command -v sha256sum >/dev/null 2>&1 && sha256sum "$tarball" || shasum -a 256 "$tarball"; } | cut -d' ' -f1)"
rm -f "$tarball"
[ ${#sha} -eq 64 ] || die "got a $((${#sha}))-char sha, expected 64"

# 6 ─ the formula follows the tag it names.
tmp="$(mktemp)"
sed -e "s|^  url \".*\"|  url \"$url\"|" \
    -e "s|^  sha256 \".*\"|  sha256 \"$sha\"|" "$FORMULA" > "$tmp" || die "sed failed"
# `version` is stated explicitly rather than parsed out of the url. Two reasons: brew's
# guess at "cli-v1.0.0.tar.gz" is not something to rely on, and the version must stay
# MONOTONIC across the switch of series — the formula used to resolve 0.9.0 from the
# template tag, so anything below that would make `brew upgrade` a silent no-op for
# everyone who already installed it.
if grep -q '^  version "' "$tmp"; then
  sed -i.bak "s|^  version \".*\"|  version \"$next\"|" "$tmp" && rm -f "$tmp.bak"
else
  sed -i.bak "s|^  url \(.*\)\$|  url \1\n  version \"$next\"|" "$tmp" && rm -f "$tmp.bak"
fi
cat "$tmp" > "$FORMULA"; rm -f "$tmp"
grep -q "$sha" "$FORMULA"         || die "the sha did not take — check $FORMULA by hand"
grep -q "^  version \"$next\"\$" "$FORMULA" || die "the version line did not take — check $FORMULA by hand"

if command -v brew >/dev/null 2>&1; then
  brew style "$FORMULA" || die "brew style rejected the formula — fix it before pushing"
fi

git -C "$ROOT" add Formula/wellforge.rb || die "git add failed"
git -C "$ROOT" commit -qm "chore(cli): formula for $tag" || die "commit failed"
git -C "$ROOT" push -q origin main || die "push failed — the formula commit is local"

step 7 "smoke the PACKAGE, not just the script"
if command -v brew >/dev/null 2>&1; then
  say "  brew install --build-from-source $FORMULA && brew test wellforge"
  say "  ${SKIP_SMOKE:+skipped by SKIP_SMOKE}"
  if [ -z "${SKIP_SMOKE:-}" ]; then
    brew install --build-from-source "$FORMULA" \
      && brew test wellforge \
      || say "  WARNING: the package smoke failed — the tag and formula are pushed, so fix
           it forward with another patch release rather than moving the tag."
  fi
else
  say "  (brew not installed — run it on a Mac before telling anyone to upgrade)"
fi

say ""
say "released $tag"
say "  constant  $next"
say "  sha256    $sha"
say "  install   brew upgrade wellforge   (or: brew install matteocodogno/wellforge/wellforge)"
say ""
step 8 "audit once the tap has the new commit"
say "  brew audit --strict --online matteocodogno/wellforge/wellforge"
say "  (it reads the TAP's checkout, not this one — docs/RELEASING-CLI.md step 8)"
