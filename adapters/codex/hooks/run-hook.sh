#!/bin/bash
# Codex hook runner — feeds a Codex hook payload to the UNCHANGED WellForge hook script.
#
#   run-hook.sh <hook-name>      (stdin: the Codex hook payload)
#
# WHY A RUNNER AND NOT A PORT
# Codex hooks speak the Claude Code hook contract closely enough that most scripts run as
# they are: the payload carries `tool_input.command` for shell calls, `stop_hook_active` on
# Stop, `agent_type`/`agent_id` on SubagentStop, and exit 2 + stderr blocks. The OpenCode
# and Copilot adapters each had to REIMPLEMENT the spec-drift rule, and Phase 35 found both
# copies carrying the same bug. Here the rule runs from the plugin's own script, so there is
# no second copy to drift. This file only translates the two things that differ:
#
#   1. The project root. Claude Code exports CLAUDE_PROJECT_DIR; Codex runs the hook in the
#      session cwd, which may be a subdirectory. Every script falls back to $(pwd), so the
#      runner resolves the git toplevel from the payload's `cwd` and exports it.
#   2. File edits. Codex edits files with ONE tool, `apply_patch`, whose `tool_input.command`
#      is the patch text — there is no `file_path`. The file hooks (pre-file-guard,
#      post-lint, post-spec-guard) read `file_path`, so the runner extracts every path the
#      patch touches and runs the script once per path, as a Write (added file) or an Edit
#      (updated, moved or deleted file). Any one refusal refuses the whole patch: that is
#      what the same edit made file by file would have got.
#
# Codex has no Read tool — it reads through the shell — so the read half of pre-file-guard
# is covered by pre-bash-guard's command-text check, exactly as on OpenCode.
HOOK="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPT="$HERE/scripts/$HOOK.sh"
INPUT=$(cat)

if [ ! -f "$SCRIPT" ]; then
  # Exit 1, not 2: a missing script is an install fault, and Codex reports a non-2 failure
  # without blocking the tool. Blocking every shell call on a packaging mistake would teach
  # people to turn hooks off.
  echo "wellforge: hook script missing: $SCRIPT — regenerate the Codex adapter" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "wellforge: jq not found — $HOOK skipped. Install jq; \$wf-doctor checks it." >&2
  exit 0
fi

CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty')
[ -n "$CWD" ] && [ -d "$CWD" ] || CWD=$(pwd)
# PHYSICAL path: `git rev-parse --show-toplevel` resolves symlinks, the payload's cwd need
# not (macOS /var → /private/var, any project under a symlinked dir). Mixed, the scripts'
# "${FILE#$PROJECT_DIR/}" strips nothing, `git show HEAD:<abs path>` finds nothing, and
# post-spec-guard reads every edited spec as NEW — which waves a lowered rigor through.
CWD=$(cd "$CWD" && pwd -P)
ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$CWD")
export CLAUDE_PROJECT_DIR="$ROOT"
cd "$ROOT" || exit 0

# ── plugin install vs project install ───────────────────────────────────────────────────
# The same runner ships in the Codex plugin (hooks/) and in a project (.codex/wellforge/
# hooks/). A project with both would run every guard twice and record every subagent twice
# in its traces, so the plugin's copy steps aside when the project wires its own: that one
# is pinned to the project's release and is what `$wf-setup --hooks` installed on purpose.
if [ "$(cd "$HERE" && pwd -P)" != "$ROOT/.codex/wellforge/hooks" ]; then
  if [ -f "$ROOT/.codex/hooks.json" ] &&
     grep -qF ".codex/wellforge/hooks/run-hook.sh" "$ROOT/.codex/hooks.json"; then
    exit 0
  fi
  if [ "$HOOK" = "session-start" ]; then
    printf '%s' "$INPUT" | bash "$SCRIPT"
    rc=$?
    # Plain stdout here becomes session context: the one place a project that the plugin
    # update left behind (or that never ran setup) can be told before a command fails on it.
    want=$(jq -r '.version // empty' "$HERE/../plugin.json" 2>/dev/null)
    have=$(cat "$ROOT/.codex/wellforge/VERSION" 2>/dev/null)
    if [ -z "$have" ]; then
      echo "WellForge: this project is not set up for the Codex plugin yet — run \$wf-setup."
    elif [ -n "$want" ] && [ "$have" != "$want" ]; then
      echo "WellForge: project files are from $have, the plugin is $want — run \$wf-setup to refresh them."
    fi
    exit $rc
  fi
fi

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty')
if [ "$TOOL" != "apply_patch" ]; then
  printf '%s' "$INPUT" | bash "$SCRIPT"
  exit $?
fi

# ── apply_patch: one run of the script per touched path ─────────────────────────────────
# Patch grammar: `*** Add File: p`, `*** Update File: p`, `*** Delete File: p`, and
# `*** Move to: p` under an Update. Paths are relative to the session cwd, so they are made
# absolute against CWD before the script sees them — the scripts resolve relative paths
# against the project ROOT, which is a different directory when Codex runs in a subfolder.
PATCH=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$PATCH" ] && exit 0

RC=0
ERRS=""
while IFS=$'\t' read -r kind path; do
  [ -z "$path" ] && continue
  case "$path" in /*) abs="$path" ;; *) abs="$CWD/$path" ;; esac
  case "$kind" in Add) as="Write" ;; *) as="Edit" ;; esac
  payload=$(printf '%s' "$INPUT" | jq -c --arg t "$as" --arg p "$abs" \
    '.tool_name = $t | .tool_input = {file_path: $p}')
  err=$(printf '%s' "$payload" | bash "$SCRIPT" 2>&1 >/dev/null)
  rc=$?
  if [ "$rc" -eq 2 ]; then
    RC=2
    ERRS="${ERRS}${err}"$'\n'
  elif [ -n "$err" ]; then
    # Advisory output (post-lint's "eslint issues …") is not a refusal; pass it through.
    printf '%s\n' "$err" >&2
  fi
done < <(printf '%s\n' "$PATCH" | awk '
  # awk, not sed: BSD sed (macOS) does not expand \t in a replacement and would emit a
  # literal "t" as the separator, so every path would arrive glued to its kind.
  /^\*\*\* (Add|Update|Delete) File: / { k = $2; sub(/^\*\*\* [A-Za-z]+ File: /, ""); print k "\t" $0; next }
  /^\*\*\* Move to: /                  { sub(/^\*\*\* Move to: /, "");                 print "Move\t" $0 }')

if [ "$RC" -eq 2 ]; then
  printf '%s' "$ERRS" >&2
  exit 2
fi
exit 0
