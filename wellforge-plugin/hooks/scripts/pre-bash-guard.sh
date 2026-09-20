#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
[ -z "$COMMAND" ] && exit 0
# Block deleting /, /*, ~, ~/, ~/*, bare * — NOT legitimate paths like /tmp/foo
# (the original unanchored "rm -rf /" matched every absolute-path deletion).
if echo "$COMMAND" | grep -qE "rm(\s+-[a-zA-Z-]+)+\s+(/|/\*|~|~/\*?|\*)([[:space:];\"')]|$)"; then
  echo "BLOCKED: recursive deletion from root/home not allowed" >&2; exit 2
fi
if echo "$COMMAND" | grep -qiE 'DROP\s+DATABASE|DROP\s+TABLE\s+[`"'"'"']?\w|TRUNCATE\s+TABLE'; then
  echo "BLOCKED: destructive SQL requires manual execution" >&2; exit 2
fi
# Word-boundary after sh/bash/zsh — without it "| shasum" matched "| sh"
if echo "$COMMAND" | grep -qE '(curl|wget)[^|]+\|\s*(ba|z)?sh([[:space:]]|$|;)'; then
  echo "BLOCKED: piping remote scripts into shell not allowed" >&2; exit 2
fi
# Protected files. This rule reads the COMMAND TEXT, not the files a command opens, so it
# can only ever approximate "touches a secret" — keep it tight in both directions.
#
# `.env` and `.pem`/`.key` need DIFFERENT rules and must not share one alternation:
#   .env       is a dotfile NAME  — it appears as `/.env`, ` .env`, or at line start.
#              Requiring a non-identifier before the dot is what stops `process.env`,
#              `import.meta.env` and `Deno.env.get` — ordinary TS vocabulary that used to
#              block greps and echoes that touched nothing, pushing people into workarounds.
#   .pem/.key  are EXTENSIONS — they always follow a filename (`id_rsa.pem`, `server.key`),
#              so the same leading boundary would silently unblock them. Trailing boundary
#              only, which already handles python's `.keys()`.
# Known limits, accepted deliberately: a mention of `.env.ci`/`.env.local` still blocks
# (those often hold real values), and `production.env` no longer does. Real content is
# backstopped by the gitleaks pre-commit hook and the security-floor CI gate.
# Regression matrix: hooks/scripts/tests/pre-bash-guard.test.sh (run in ci.yml).
# .env.example / .env.jinja are legitimately referenced — scrub them first.
SCRUBBED=$(echo "$COMMAND" | sed 's/\.env\.example//g; s/\.env\.jinja//g')
if echo "$SCRUBBED" | grep -qE '(^|[^A-Za-z0-9_.])\.env([^A-Za-z0-9_]|$)' \
  || echo "$SCRUBBED" | grep -qE '(^|[^A-Za-z0-9_.])\.envrc([^A-Za-z0-9_]|$)' \
  || echo "$SCRUBBED" | grep -qE '\.(pem|key|p12|pfx)([^A-Za-z0-9_]|$)|secrets\.ya?ml|(^|/)id_(rsa|ed25519)([^A-Za-z0-9_]|$)'; then
  echo "BLOCKED: touches protected file (.env/.pem/.key/secrets.yml)" >&2; exit 2
fi
# ── Destructive git (widened 2026-09: the narrow patterns had documented bypasses) ──────
# Force-push in every spelling EXCEPT --force-with-lease, which is the SAFE one (it refuses
# when the remote moved under you) and the one this repo's linear-history policy prescribes
# after a rebase. Covered: --force, -f, and a leading-plus refspec (git push origin +main),
# which is a force push wearing different clothes.
if echo "$COMMAND" | grep -qE 'git\s+push\b' \
   && echo "$COMMAND" | grep -qvE '\-\-force-with-lease' \
   && echo "$COMMAND" | grep -qE '(\-\-force([^-]|$)|\s-[a-zA-Z]*f[a-zA-Z]*(\s|$)|\s\+[A-Za-z0-9_./@-]+(:|\s|$))'; then
  echo "BLOCKED: force push requires manual confirmation (use --force-with-lease if you mean it)" >&2; exit 2
fi
# `git reset --hard` at ANY target, not just HEAD~2..9: `--hard origin/main` discards the same
# work and was the reported bypass. `--soft`/`--mixed` stay allowed — they keep the tree.
if echo "$COMMAND" | grep -qE 'git\s+reset\s+(--\w+\s+)*--hard'; then
  echo "BLOCKED: destructive git operation requires manual confirmation" >&2; exit 2
fi
# Force-delete a branch. Lowercase -d (delete only if merged) stays allowed: the
# worktree-isolation prune step depends on it.
if echo "$COMMAND" | grep -qE 'git\s+branch\s+(-[a-zA-Z]*D[a-zA-Z]*|--delete\s+--force|--force\s+--delete)\b'; then
  echo "BLOCKED: force-deleting a branch requires manual confirmation (-d deletes merged branches)" >&2; exit 2
fi
exit 0
