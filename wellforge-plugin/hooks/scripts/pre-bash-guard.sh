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
# METADATA-ONLY QUERIES may name a protected file: they reveal nothing of its contents.
# Without this carve-out the connections skill's own secrets-hygiene check —
# `git check-ignore .mise.local.toml .env.local` — is refused, which is how a guard teaches people
# to work around it.
# ...and ONLY for a single simple command. Anchoring at the start is not enough on its own:
# `ls . && cat <secret>` begins with `ls`, so an early exit here would wave the whole line
# through. Any separator (&& || ; | newline) or substitution disqualifies the carve-out.
if echo "$COMMAND" | grep -qE '^[[:space:]]*(git[[:space:]]+check-(ignore|attr)|ls|stat|test|\[)[[:space:]]' \
   && ! echo "$COMMAND" | grep -qE '(\&\&|\|\||;|\||\$\(|`)'; then
  exit 0
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

# .mise.local.toml is WellForge's sanctioned secret store: the setup flow WRITES it, so a
# blanket block would break the documented path — but it must never be READ back into the
# transcript.
#
# This is an INVERTED rule, and the inversion is the point. It used to allow-list reader
# commands (cat, head, less, ...), which cannot work: the set of ways to read a file is
# unbounded, and `grep`, `awk`, `sed`, `cp`, `python3 -c`, `curl -d @file` and `git diff`
# all sailed past. The set of sanctioned WRITES is short and closed, so that is what gets
# enumerated. Anything else naming the file is refused, including tools nobody has thought
# of yet.
#
# Sanctioned writes: redirection INTO it (> / >>), tee, touch, and `mise set`. Metadata
# queries (ls / stat / test / git check-ignore) exited above.
#
# HOW THE TEST WORKS, and why it is not "does a write pattern appear somewhere".
# That was the bug: the allow-list matched ANYWHERE in the command, so one sanctioned write
# excused every other mention on the line. All five of these read the file and passed:
#     cat .mise.local.toml > .mise.local.toml.bak
#     cat .mise.local.toml; echo x > .mise.local.toml
#     cat .mise.local.toml | tee .mise.local.toml
#     mise set FOO=bar; cat .mise.local.toml
#     touch .mise.local.toml; cat .mise.local.toml
# (and two more found while fixing it: `echo $(cat <file>) > <file>` and `tee <file> < <file>`)
# while plain `cat .mise.local.toml` was correctly refused.
#
# So: STRIP every mention that is itself a sanctioned write, then ask whether any mention
# SURVIVES. A survivor is a read, or something this guard cannot classify, and either way it
# is refused. Each write is removed on its own terms, so the number of chained commands stops
# mattering — which is what the old rule got wrong.
#
# Note this deliberately does NOT copy the metadata carve-out's "no separators, no
# substitution" condition verbatim. Both would break documented writes: `echo x | tee <file>`
# is a sanctioned write whose whole point is a pipe, and
# `echo "K=$(op read op://v/i/f)" > <file>` is the 1Password setup flow the connections skill
# prescribes. A substitution is harmless here precisely BECAUSE of the residue test — if it
# reads the file it must name it, and then it survives the strip and is blocked.
#
# PFX is the path prefix a write target may carry (./, ~/, "$HOME/, a quote). It excludes
# whitespace, separators and redirect operators, so no single pattern can span two commands.
if echo "$COMMAND" | grep -qE '\.mise\.local\.toml'; then
  PFX='["'"'"']?[^[:space:];&|<>()`]*'
  RESIDUE=$(echo "$COMMAND" | sed -E \
    -e "s|>>?[[:space:]]*${PFX}\.mise\.local\.toml||g" \
    -e "s|tee([[:space:]]+-[a-zA-Z-]+)*[[:space:]]+${PFX}\.mise\.local\.toml||g" \
    -e "s|touch([[:space:]]+-[a-zA-Z-]+)*[[:space:]]+${PFX}\.mise\.local\.toml||g" \
    -e "s|mise[[:space:]]+set[[:space:]]+([^;&|]*[[:space:]])?${PFX}\.mise\.local\.toml||g")
  if echo "$RESIDUE" | grep -qE '\.mise\.local\.toml'; then
    echo "BLOCKED: .mise.local.toml holds live secrets — only writing it is allowed" >&2
    echo "  Allowed:  > / >> redirection into it, tee, touch, mise set, and metadata (ls/stat/test/git check-ignore)" >&2
    echo "  Refused:  everything else that names it, including read tools not on any list" >&2
    echo "  A sanctioned write does NOT excuse another mention on the same line: each" >&2
    echo "  mention has to be a write on its own." >&2
    echo "  To see resolved values, run 'mise env' yourself outside the agent." >&2
    exit 2
  fi
fi
exit 0
