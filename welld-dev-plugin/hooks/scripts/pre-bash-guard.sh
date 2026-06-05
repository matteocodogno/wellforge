#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0
# Block deleting /, /*, ~, ~/, ~/*, bare * — NOT legitimate paths like /tmp/foo
# (the original unanchored "rm -rf /" matched every absolute-path deletion).
if echo "$COMMAND" | grep -qE "rm\s+-[a-zA-Z]+\s+(/|/\*|~|~/\*?|\*)([[:space:];\"')]|$)"; then
  echo "BLOCKED: recursive deletion from root/home not allowed" >&2; exit 2
fi
if echo "$COMMAND" | grep -qiE 'DROP\s+DATABASE|DROP\s+TABLE\s+\w+\s*;|TRUNCATE\s+TABLE'; then
  echo "BLOCKED: destructive SQL requires manual execution" >&2; exit 2
fi
if echo "$COMMAND" | grep -qE 'curl.+\|\s*(bash|sh)|wget.+\|\s*(bash|sh)'; then
  echo "BLOCKED: piping remote scripts into shell not allowed" >&2; exit 2
fi
# Literal (-F) matching — these are filenames, not regexes (an unescaped ".env"
# regex matches any char + "env", e.g. the word " environment").
# .env.example and template .env.jinja files are legitimately referenced — strip
# them before testing so they don't trip the .env substring.
SCRUBBED=$(echo "$COMMAND" | sed 's/\.env\.example//g; s/\.env\.jinja//g')
for pattern in ".env" ".pem" ".key" "secrets.yml"; do
  if echo "$SCRUBBED" | grep -qF -- "$pattern"; then
    echo "BLOCKED: touches protected file ($pattern)" >&2; exit 2
  fi
done
if echo "$COMMAND" | grep -qE 'git\s+(push\s+--force|reset\s+--hard\s+HEAD~[2-9])'; then
  echo "BLOCKED: destructive git operation requires manual confirmation" >&2; exit 2
fi
exit 0
