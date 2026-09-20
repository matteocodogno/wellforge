#!/bin/bash
# PreToolUse guard for the FILE tools (Read/Write/Edit/MultiEdit/NotebookEdit).
#
# WHY THIS EXISTS SEPARATELY FROM pre-bash-guard.sh
# The bash guard inspects COMMAND TEXT, so it only ever covered Bash. Write and Edit could
# create a dotenv or secrets file freely and Read could read one — the protection was real
# for `cat` and absent for the tool an agent actually reaches for. This hook closes that, and
# it is strictly more precise: it reads the tool's `file_path` PARAMETER, so there are no
# false positives from a path merely appearing inside a command string.
#
# Two lists, because the two risks differ:
#   DENY  — secret-bearing files nothing should read OR write.
#   READ  — files an agent may legitimately create during setup, but must not slurp into the
#           transcript. .mise.local.toml is the one that matters: it is WellForge's SANCTIONED secret
#           store (connections skill), so blocking writes to it would push people back to
#           dotenv files — exactly the convention we moved away from.
#
# Allowed everywhere: *.example, *.sample, *.template and *.jinja variants. They are
# committed manifests of which variables exist, and the templates in this repo are made of
# them.
INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')
[ -z "$FILE" ] && exit 0

BASE=$(basename -- "$FILE")

# Placeholders / manifests are always fine.
case "$BASE" in
  *.example|*.example.*|*.sample|*.sample.*|*.template|*.template.*|*.jinja|*.dist) exit 0 ;;
esac

deny() {
  echo "BLOCKED: $1 is a protected secret file ($2)." >&2
  echo "  Secrets live in .mise.local.toml (gitignored, injected by mise) — see the connections skill." >&2
  echo "  If you genuinely need this file, run the command yourself outside the agent." >&2
  exit 2
}

# ── Read + write denied ────────────────────────────────────────────────────────
if echo "$BASE" | grep -qE '^\.env($|\.)' \
  || echo "$BASE" | grep -qE '^\.envrc$' \
  || echo "$BASE" | grep -qE '\.(pem|key|p12|pfx)$' \
  || echo "$BASE" | grep -qE '^secrets\.ya?ml$' \
  || echo "$BASE" | grep -qE '^id_(rsa|ed25519|dsa|ecdsa)$'; then
  deny "$BASE" "read and write"
fi

# ── Read denied, write allowed ─────────────────────────────────────────────────
# Creating it during setup is the documented flow; reading its values back into the
# conversation is the leak.
if [ "$TOOL" = "Read" ] && echo "$BASE" | grep -qE '^\.mise\.local\.toml$|^credentials\.json$'; then
  echo "BLOCKED: reading $BASE would pull secret values into the transcript." >&2
  echo "  Write to it if setup needs it; to inspect values, run 'mise env' yourself." >&2
  exit 2
fi

exit 0
