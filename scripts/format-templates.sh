#!/usr/bin/env bash
# format-templates.sh — run each preset's OWN formatter over its OWN rendered output, and
# put the result back into the template.
#
#   scripts/format-templates.sh            # rewrite the template sources
#   scripts/format-templates.sh --check    # report only; non-zero if anything would change
#
# Why this exists: every preset ships a formatter (biome / prettier) and a config, and the
# template sources had never been run through it — so `mise run lint` failed on a FRESH
# scaffold, on the template's own files, before anyone had written a line. Fixing those
# files by hand fixes today; this fixes the class, because the next edit to a template can
# be put through the same formatter the generated project will judge it with.
#
# The one thing it must not do blindly: a `.jinja` source is not its rendered output.
# Copying a formatted render back over one would bake `{{ project_slug }}` into a literal —
# turning a template into one project's copy of itself. Those are reported with their diff
# and applied by hand; plain sources are copied back automatically. Both counts are printed
# every run, so the manual half never goes quiet.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECK=0
[ "${1:-}" = "--check" ] && CHECK=1

for req in uvx python3 pnpm; do
  command -v "$req" >/dev/null || { echo "needs $req on PATH"; exit 1; }
done

# preset : the services that carry a formatter config
PRESETS="hono-react:backend,frontend pulumi-gcp-ts:infra spring-kotlin-react:frontend"

copied=0 manual=0 failed=0

for entry in $PRESETS; do
  preset="${entry%%:*}"; services="${entry#*:}"
  gen="$(mktemp -d)"
  echo
  echo "── $preset ──────────────────────────────────────────────────────────────────"
  if ! uvx copier copy --defaults --trust --vcs-ref HEAD "$ROOT" "$gen" \
         --data preset="$preset" >/dev/null 2>&1; then
    echo "  ✗ could not render $preset"; failed=$((failed + 1)); rm -rf "$gen"; continue
  fi

  # Without this the render's mise.toml is untrusted, mise refuses to resolve node/pnpm,
  # and every `pnpm install` below fails with a message about trust rather than about the
  # project. `--all` because a generated project has a mise.toml per service.
  ( cd "$gen" && mise trust --all ) >/dev/null 2>&1

  for svc in ${services//,/ }; do
    [ -d "$gen/$svc" ] || continue

    if [ -f "$gen/$svc/biome.json" ]; then formatter=biome
    elif [ -f "$gen/$svc/.prettierrc" ]; then formatter=prettier
    else echo "  $svc: no biome.json or .prettierrc — nothing to run"; continue; fi

    echo "  $svc: installing ($formatter at the version the PROJECT pins, not one we pick)…"
    if ! ( cd "$gen/$svc" && pnpm install --silent ) >/dev/null 2>&1; then
      echo "    ✗ install failed — skipped"; failed=$((failed + 1)); continue
    fi

    # Exact before/after: snapshot the sources, format, then diff. No mtime guessing.
    snap="$(mktemp -d)"
    # tar, not `cp --parents`: --parents is GNU-only, so on macOS every copy failed while
    # `find` still exited 0 — the snapshot came out EMPTY and this script cheerfully
    # reported "0 sources changed" with nothing compared. Both GNU tar and bsdtar take
    # --exclude.
    ( cd "$gen/$svc" && tar --exclude=node_modules --exclude=dist -cf - . ) \
      | ( cd "$snap" && tar -xf - ) || { echo "    ✗ snapshot failed — skipped"; failed=$((failed + 1)); continue; }

    case "$formatter" in
      biome)    ( cd "$gen/$svc" && pnpm exec biome check --write . ) >/dev/null 2>&1 ;;
      prettier) ( cd "$gen/$svc" && pnpm exec prettier --write . )   >/dev/null 2>&1 ;;
    esac

    while IFS=$'\t' read -r rendered source kind; do
      [ -n "$rendered" ] || continue
      case "$kind" in
        plain)
          copied=$((copied + 1))
          if [ "$CHECK" -eq 1 ]; then
            echo "    would rewrite  ${source#"$ROOT"/}"
          else
            cat "$rendered" > "$source" && echo "    rewrote  ${source#"$ROOT"/}"
          fi ;;
        jinja)
          manual=$((manual + 1))
          echo "    MANUAL   ${source#"$ROOT"/}"
          diff -u "$snap/${rendered#"$gen/$svc/"}" "$rendered" 2>/dev/null \
            | sed -n '4,14p' | sed 's/^/             /' ;;
      esac
    done < <(python3 - "$gen/$svc" "$snap" "$ROOT/templates/$preset/template/$svc" <<'PY'
import os, re, subprocess, sys
gen_dir, snap_dir, tpl_dir = sys.argv[1], sys.argv[2], sys.argv[3]

def rendered_name(rel):
    """Template-relative path -> the path it renders to, where that is knowable.
    `{% if db == 'postgres' %}db{% endif %}` -> `db`. A `{{ … }}` segment (package_path)
    cannot be resolved without the answers, so those files are skipped rather than guessed."""
    out = []
    for seg in rel.split(os.sep):
        if '{{' in seg:
            return None
        seg = re.sub(r"\{%.*?%\}", "", seg)
        if not seg:
            return None
        out.append(seg)
    return os.sep.join(out)

sources = {}
for dp, _, fns in os.walk(tpl_dir):
    for fn in fns:
        src = os.path.join(dp, fn)
        rel = os.path.relpath(src, tpl_dir)
        jinja = rel.endswith('.jinja')
        name = rendered_name(rel[:-6] if jinja else rel)
        if name:
            sources[name] = (src, 'jinja' if jinja else 'plain')

skip = {'node_modules', 'dist', 'coverage', '.git'}
for dp, dirs, fns in os.walk(gen_dir):
    dirs[:] = [d for d in dirs if d not in skip]
    for fn in fns:
        rendered = os.path.join(dp, fn)
        rel = os.path.relpath(rendered, gen_dir)
        hit = sources.get(rel)
        if not hit:
            continue
        before = os.path.join(snap_dir, rel)
        # Only what the FORMATTER changed: compare against the pre-format snapshot.
        if not os.path.exists(before):
            continue
        if subprocess.run(['cmp', '-s', rendered, before]).returncode == 0:
            continue
        print(f"{rendered}\t{hit[0]}\t{hit[1]}")
PY
    )
    rm -rf "$snap"
  done
  rm -rf "$gen"
done

echo
echo "───────────────────────────────────────────────────────────────────────────────"
if [ "$CHECK" -eq 1 ]; then
  printf 'plain sources that would change: %d\n' "$copied"
else
  printf 'plain sources rewritten: %d\n' "$copied"
fi
printf 'jinja sources needing a hand: %d\n' "$manual"
[ "$failed" -gt 0 ] && printf 'services that could not be processed: %d\n' "$failed"

if [ "$manual" -gt 0 ]; then
  echo
  echo "A .jinja source is never rewritten automatically: its render has the answers baked"
  echo "in (project_slug, base_package), so writing that back would turn the template into"
  echo "one project's copy of it. Apply the diffs above by hand."
fi

if [ "$CHECK" -eq 1 ] && { [ "$copied" -gt 0 ] || [ "$manual" -gt 0 ]; }; then
  exit 1
fi
[ "$failed" -eq 0 ]
