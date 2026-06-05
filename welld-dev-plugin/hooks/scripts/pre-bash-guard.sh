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
# Word-boundary after sh/bash/zsh — without it "| shasum" matched "| sh"
if echo "$COMMAND" | grep -qE '(curl|wget)[^|]+\|\s*(ba|z)?sh([[:space:]]|$|;)'; then
  echo "BLOCKED: piping remote scripts into shell not allowed" >&2; exit 2
fi
# Protected file extensions need BOTH boundaries: an unanchored ".env" regex
# matched " environment"; a literal ".key" matched python's ".keys()". So:
# extension must be followed by a non-alphanumeric or end-of-string.
# .env.example / .env.jinja are legitimately referenced — scrub them first.
SCRUBBED=$(echo "$COMMAND" | sed 's/\.env\.example//g; s/\.env\.jinja//g')
if echo "$SCRUBBED" | grep -qE '\.(env|pem|key)([^A-Za-z0-9_]|$)|secrets\.ya?ml'; then
  echo "BLOCKED: touches protected file (.env/.pem/.key/secrets.yml)" >&2; exit 2
fi
if echo "$COMMAND" | grep -qE 'git\s+(push\s+--force|reset\s+--hard\s+HEAD~[2-9])'; then
  echo "BLOCKED: destructive git operation requires manual confirmation" >&2; exit 2
fi
exit 0
