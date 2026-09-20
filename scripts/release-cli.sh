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
# the CLI as it stood at v0.9.0 for months. See docs/VERSIONING.md → "the CLI series".
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

if [ "$FORMULA_ONLY" -eq 1 ]; then
  say "plan (--formula-only — the tag already exists):"
  say "  1. fetch   $url, compute its sha256"
  say "  2. rewrite the Formula's url/version/sha256, commit 'chore(cli): formula for $tag'"
  say "  3. push    main"
else
  say "plan:"
  say "  1. set WELLFORGE_CLI_VERSION=\"$next\" in scripts/wellforge"
  say "  2. commit  'chore(cli): release $next'"
  say "  3. tag     $tag"
  say "  4. push    main and $tag            ← the tarball does not exist before this"
  say "  5. fetch   $url, compute its sha256"
  say "  6. rewrite the Formula's url/version/sha256, commit 'chore(cli): formula for $tag'"
  say "  7. push    main"
fi

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
# 1-3 ─ the constant is the release; the tag names the commit that sets it.
tmp="$(mktemp)"
sed "s/^WELLFORGE_CLI_VERSION=\".*\"/WELLFORGE_CLI_VERSION=\"$next\"/" "$CLI" > "$tmp" || die "sed failed"
grep -q "^WELLFORGE_CLI_VERSION=\"$next\"\$" "$tmp" || die "the constant did not take — check $CLI by hand"
cat "$tmp" > "$CLI"; rm -f "$tmp"

git -C "$ROOT" add scripts/wellforge || die "git add failed"
git -C "$ROOT" commit -qm "chore(cli): release $next" || die "commit failed"
git -C "$ROOT" tag "$tag" || die "tag failed"

# 4 ─ push before the sha: GitHub generates the tarball, and it is not reproducible here.
git -C "$ROOT" push -q origin main "$tag" || die "push failed — the tag is local; delete it with 'git tag -d $tag' if you are retrying"
fi

# 5 ─ the only place the real sha can come from.
say "  fetching the tarball…"
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

say ""
say "released $tag"
say "  constant  $next"
say "  sha256    $sha"
say "  install   brew upgrade wellforge   (or: brew install matteocodogno/wellforge/wellforge)"
say ""
say "Next: brew audit --strict matteocodogno/wellforge/wellforge — it needs the tap, so it"
say "      can only run now that the tag is published (docs/VERSIONING.md)."
