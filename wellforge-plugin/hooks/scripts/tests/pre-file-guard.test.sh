#!/usr/bin/env bash
# Regression matrix for pre-file-guard.sh (PreToolUse on the file tools).
#
# Why it exists: pre-bash-guard.sh inspects command TEXT, so it only ever covered Bash.
# Write/Edit could create a secret file and Read could read one — reported 2026-09 along with
# five bash-rule bypasses (see pre-bash-guard.test.sh). These cases are that gap.
set -u
HOOK="$(cd "$(dirname "$0")/.." && pwd)/pre-file-guard.sh"
E="env"; PEM="pem"; SEC="secrets"
PASS=0; FAIL=0

check() { # check <want-exit> <tool> <path>
  local want="$1" tool="$2" path="$3" got out
  out=$(printf '{"tool_name":"%s","tool_input":{"file_path":"%s"}}' "$tool" "$path" | bash "$HOOK" 2>&1)
  got=$?
  if [ "$got" = "$want" ]; then PASS=$((PASS+1));
  else FAIL=$((FAIL+1)); echo "  FAIL: $tool $path (want $want, got $got)"; echo "$out" | sed 's/^/        /'; fi
}

echo "pre-file-guard regression matrix"

# Denied for both read and write
for t in Read Write Edit MultiEdit; do
  check 2 "$t" "backend/.$E"
  check 2 "$t" "backend/.$E.local"
  check 2 "$t" ".${E}rc"
  check 2 "$t" "certs/server.$PEM"
  check 2 "$t" "certs/tls.key"
  check 2 "$t" "config/$SEC.yml"
  check 2 "$t" "config/$SEC.yaml"
  check 2 "$t" "id_rsa"
  check 2 "$t" "id_ed25519"
done

# Manifests and template sources stay editable — this repo is made of them
check 0 Read  "backend/.$E.example"
check 0 Write "templates/hono-react/template/backend/.$E.example.jinja"
check 0 Write "frontend/.$E.jinja"
check 0 Read  "config/$SEC.yml.sample"

# The sanctioned secret store: writable (setup flow), unreadable (transcript leak)
check 0 Write ".mise.local.toml"
check 0 Edit  ".mise.local.toml"
check 2 Read  ".mise.local.toml"

# Ordinary files untouched
check 0 Write "src/main.ts"
check 0 Read  "package.json"
check 0 Edit  "docs/plans/PLAN.md"

# ── Grep, reported 2026-09-20: it sends `path`, not `file_path`, and content mode PRINTS
# matching lines — a read by another name. It was outside the matcher entirely.
check 2 Grep "backend/.env"
check 2 Grep "backend/.env.local"
check 2 Grep "certs/server.pem"
check 2 Grep ".mise.local.toml"          # read-denied like Read, unlike Write
check 0 Grep "backend/.env.example"      # manifests stay greppable
check 0 Grep "src/"                      # a directory grep is not coverable — see README
check 0 Grep "package.json"

# No path in the payload → nothing to judge
out=$(printf '{"tool_name":"Read","tool_input":{}}' | bash "$HOOK" 2>&1); rc=$?
[ "$rc" = 0 ] && PASS=$((PASS+1)) || { FAIL=$((FAIL+1)); echo "  FAIL: empty payload should pass (got $rc)"; }

# NotebookEdit passes its path under a different key
out=$(printf '{"tool_name":"NotebookEdit","tool_input":{"notebook_path":"secret.%s"}}' "$PEM" | bash "$HOOK" 2>&1); rc=$?
[ "$rc" = 2 ] && PASS=$((PASS+1)) || { FAIL=$((FAIL+1)); echo "  FAIL: notebook_path should be read (got $rc)"; }

echo
echo "pre-file-guard: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
