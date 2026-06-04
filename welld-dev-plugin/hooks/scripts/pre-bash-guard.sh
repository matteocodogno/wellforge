#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0
if echo "$COMMAND" | grep -qE 'rm\s+-rf\s+/|rm\s+-rf\s+\*|rm\s+-rf\s+~'; then
  echo "BLOCKED: recursive deletion from root/home not allowed" >&2; exit 2
fi
if echo "$COMMAND" | grep -qiE 'DROP\s+DATABASE|DROP\s+TABLE\s+\w+\s*;|TRUNCATE\s+TABLE'; then
  echo "BLOCKED: destructive SQL requires manual execution" >&2; exit 2
fi
if echo "$COMMAND" | grep -qE 'curl.+\|\s*(bash|sh)|wget.+\|\s*(bash|sh)'; then
  echo "BLOCKED: piping remote scripts into shell not allowed" >&2; exit 2
fi
for pattern in ".env" ".env.local" ".env.production" "*.pem" "*.key" "secrets.yml"; do
  if echo "$COMMAND" | grep -q "$pattern"; then
    echo "BLOCKED: touches protected file ($pattern)" >&2; exit 2
  fi
done
if echo "$COMMAND" | grep -qE 'git\s+(push\s+--force|reset\s+--hard\s+HEAD~[2-9])'; then
  echo "BLOCKED: destructive git operation requires manual confirmation" >&2; exit 2
fi
exit 0
