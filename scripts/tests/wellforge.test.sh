#!/usr/bin/env bash
# Regression matrix for scripts/wellforge — the CLI every teammate runs first, and the one
# piece of this repo that had no test at all.
#
# It drives the REAL script (temp HOME, temp PATH of shim executables, real git fixtures)
# rather than re-stating its logic, so a rule cannot pass its test and fail in practice —
# the same contract as wellforge-plugin/hooks/scripts/tests/*.test.sh.
#
# Why shims work here: every external dependency of this CLI is a command on PATH. Replacing
# brew/claude/gh/docker/mise/npx/node/npm/curl/open with recording stubs makes the whole tool
# deterministic and offline, and lets the matrix pin failure paths (a brew install that
# fails, an unauthenticated gh) that are otherwise unreachable on a healthy machine.
#
# git and jq are NOT shimmed: the checkout fixtures are real repositories with a real bare
# upstream, because "is this checkout behind?" is exactly the logic worth testing for real.
#
# Run: scripts/tests/wellforge.test.sh
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CLI="$ROOT/scripts/wellforge"
[ -x "$CLI" ] || { echo "not executable: $CLI"; exit 1; }

for req in git jq sed grep; do
  command -v "$req" >/dev/null || { echo "this suite needs $req on PATH"; exit 1; }
done

SUITE="$(mktemp -d)"
trap 'rm -rf "$SUITE"' EXIT

pass=0 fail=0 xfail=0 xpass=0
CASE=""

# ── assertions ────────────────────────────────────────────────────────────────
# Every case declares whether it is expected to pass. XFAIL marks behaviour a LATER
# prompt introduces: the case runs, its failure does not break the suite, and an
# unexpected PASS is reported loudly — that is the signal to drop the marker.
EXPECT="pass"
begin() { CASE="$1"; EXPECT="${2:-pass}"; CASE_FAILED=0; }
finish() {
  if [ "$EXPECT" = "xfail" ]; then
    if [ "$CASE_FAILED" -eq 0 ]; then
      xpass=$((xpass + 1))
      printf '  XPASS %s\n         ↑ expected to fail until the behaviour lands — remove the xfail marker\n' "$CASE"
    else
      xfail=$((xfail + 1)); printf '  xfail %s (not implemented yet)\n' "$CASE"
    fi
    return
  fi
  if [ "$CASE_FAILED" -eq 0 ]; then pass=$((pass + 1)); printf '  ok    %s\n' "$CASE"
  else fail=$((fail + 1)); fi
}
_bad() { # <detail>
  [ "$CASE_FAILED" -eq 0 ] && [ "$EXPECT" != "xfail" ] && printf '  FAIL  %s\n' "$CASE"
  CASE_FAILED=1
  [ "$EXPECT" != "xfail" ] && printf '          %s\n' "$1"
  return 0
}
assert_rc()        { [ "$1" = "$2" ] || _bad "expected rc=$2, got rc=$1"; }
assert_has()       { printf '%s' "$1" | grep -qF -- "$2" || _bad "output is missing: $2"; }
assert_has_re()    { printf '%s' "$1" | grep -qE -- "$2" || _bad "output does not match /$2/"; }
assert_lacks()     { printf '%s' "$1" | grep -qF -- "$2" && _bad "output should NOT contain: $2"; return 0; }
assert_file_has()  { grep -qF -- "$2" "$1" 2>/dev/null || _bad "$1 is missing: $2"; }
assert_exists()    { [ -e "$1" ] || _bad "expected to exist: $1"; }
assert_absent()    { [ -e "$1" ] && _bad "expected NOT to exist: $1"; return 0; }

# ── shims ─────────────────────────────────────────────────────────────────────
# Each shim appends "<name> <args>" to $SHIM_LOG so a case can assert on calls that
# produce no output (a plugin reinstall that should not have happened), and reads its
# behaviour from env vars so one shim set covers success and failure paths.
make_shims() { # <bindir> <tool…>   — only the named tools exist, so "brew missing" is a case
  local bin="$1"; shift
  mkdir -p "$bin"
  local t
  for t in "$@"; do
    case "$t" in
      brew) cat > "$bin/brew" <<'SH'
#!/usr/bin/env bash
echo "brew $*" >> "$SHIM_LOG"
case "$1" in
  --version) echo "Homebrew ${FAKE_BREW_VERSION:-4.0.0-shim}" ;;
  update)    exit "${FAKE_BREW_UPDATE_RC:-0}" ;;
  outdated)
    # `brew outdated <pkg>` (used for the CLI self-check) exits 0 when CURRENT.
    if [ "${2:-}" = "--quiet" ] || [ -z "${2:-}" ]; then
      printf '%s\n' ${FAKE_BREW_OUTDATED:-}
      exit 0
    fi
    exit "${FAKE_BREW_OUTDATED_PKG_RC:-0}" ;;
  install)
    if [ "${FAKE_BREW_INSTALL_RC:-0}" != "0" ]; then
      echo "Warning: noise on the first line" >&2
      echo "${FAKE_BREW_INSTALL_ERR:-Error: install failed}" >&2
      exit "${FAKE_BREW_INSTALL_RC}"
    fi ;;
  upgrade)
    if [ "${FAKE_BREW_UPGRADE_RC:-0}" != "0" ]; then
      echo "${FAKE_BREW_UPGRADE_ERR:-Error: upgrade failed}" >&2
      exit "${FAKE_BREW_UPGRADE_RC}"
    fi ;;
  list) echo "wellforge ${FAKE_BREW_LIST_VERSION:-0.0.0}" ;;
esac
exit 0
SH
        ;;
      claude) cat > "$bin/claude" <<'SH'
#!/usr/bin/env bash
echo "claude $*" >> "$SHIM_LOG"
case "$*" in
  "--version")                 echo "${FAKE_CLAUDE_VERSION:-2.0.0 (Claude Code)}" ;;
  "plugin marketplace list")   printf '%s\n' "${FAKE_CLAUDE_MARKETPLACES:-}" ;;
  "plugin list")               printf '%s\n' "${FAKE_CLAUDE_PLUGINS:-}" ;;
  "plugin marketplace add"*)   exit "${FAKE_CLAUDE_MKT_ADD_RC:-0}" ;;
  "plugin install"*)
    [ "${FAKE_CLAUDE_INSTALL_RC:-0}" = "0" ] || { echo "Error: install refused" >&2; exit 1; } ;;
  "plugin uninstall"*)         ;;
esac
exit 0
SH
        ;;
      gh) cat > "$bin/gh" <<'SH'
#!/usr/bin/env bash
echo "gh $*" >> "$SHIM_LOG"
case "$*" in
  "--version")   echo "gh version 2.0.0 (shim)" ;;
  "auth status")
    if [ "${FAKE_GH_AUTH_RC:-0}" = "0" ]; then echo "Logged in to github.com account shim"
    else echo "You are not logged into any GitHub hosts."; fi
    exit "${FAKE_GH_AUTH_RC:-0}" ;;
esac
exit 0
SH
        ;;
      docker) cat > "$bin/docker" <<'SH'
#!/usr/bin/env bash
echo "docker $*" >> "$SHIM_LOG"
[ "${1:-}" = "info" ] && exit "${FAKE_DOCKER_INFO_RC:-0}"
exit 0
SH
        ;;
      uvx) cat > "$bin/uvx" <<'SH'
#!/usr/bin/env bash
echo "uvx $*" >> "$SHIM_LOG"
case "$*" in "copier --version") echo "copier 9.0.0-shim"; exit "${FAKE_COPIER_RC:-0}" ;; esac
exit 0
SH
        ;;
      mise) cat > "$bin/mise" <<'SH'
#!/usr/bin/env bash
echo "mise $*" >> "$SHIM_LOG"
case "$*" in
  "--version") echo "2026.1.0 shim" ;;
  "use -g node@22")
    [ "${FAKE_MISE_USE_RC:-0}" = "0" ] || { echo "${FAKE_MISE_USE_ERR:-Error: mise refused}" >&2; exit 1; } ;;
esac
exit 0
SH
        ;;
      uv|jq-shim|npx|node|npm) cat > "$bin/$t" <<SH
#!/usr/bin/env bash
echo "$t \$*" >> "\$SHIM_LOG"
case "\${1:-}" in
  --version) echo "$t v1.0.0-shim" ;;
  install)   [ "\${FAKE_NPM_INSTALL_RC:-0}" = "0" ] || { echo "\${FAKE_NPM_INSTALL_ERR:-Error: npm refused}" >&2; exit 1; } ;;
esac
exit 0
SH
        ;;
      open) cat > "$bin/open" <<'SH'
#!/usr/bin/env bash
# Never actually open a browser during a test run.
echo "open $*" >> "$SHIM_LOG"
exit 0
SH
        ;;
      curl) cat > "$bin/curl" <<'SH'
#!/usr/bin/env bash
# Canned Telegram API. The method is the last path segment of the api.telegram.org URL.
echo "curl $*" >> "$SHIM_LOG"
method=""
for a in "$@"; do case "$a" in https://api.telegram.org/*) method="${a##*/}" ;; esac; done
# No inline JSON defaults here: a `}` inside ${VAR:-…} closes the expansion, which made
# this shim a syntax error and left the CLI spinning on an empty getMe reply. Callers set
# the payloads; unset means "the API said nothing", which is itself a case worth having.
case "$method" in
  getMe)       printf '%s\n' "${FAKE_TG_GETME-}" ;;
  getUpdates)  printf '%s\n' "${FAKE_TG_GETUPDATES-}" ;;
  sendMessage) printf '%s\n' "${FAKE_TG_SEND-}" ;;
  *)           printf '{"ok":false}\n' ;;
esac
exit 0
SH
        ;;
    esac
    chmod +x "$bin/$t" 2>/dev/null
  done
}

# ── fixtures ──────────────────────────────────────────────────────────────────
# A real checkout with a real bare upstream: "N commits behind" is measured, not mocked.
make_checkout() { # <dir> <plugin-version> [tag]
  local dir="$1" ver="$2" tag="${3:-v9.9.9}" origin="$1.origin"
  mkdir -p "$dir/wellforge-plugin/.claude-plugin" \
           "$dir/wellforge-plugin/agents" \
           "$dir/wellforge-plugin/skills/spec-driven" \
           "$dir/wellforge-plugin/hooks" \
           "$dir/.claude-plugin" "$dir/scripts"
  echo '{"name":"wellforge","plugins":[]}'            > "$dir/.claude-plugin/marketplace.json"
  echo "{\"name\":\"wellforge\",\"version\":\"$ver\"}" > "$dir/wellforge-plugin/.claude-plugin/plugin.json"
  echo "# architect"                                   > "$dir/wellforge-plugin/agents/architect.md"
  echo "# spec-driven"                                 > "$dir/wellforge-plugin/skills/spec-driven/SKILL.md"
  echo '{"mcpServers":{"sequential-thinking":{}}}'     > "$dir/wellforge-plugin/.mcp.json"
  echo '{"hooks":{"Stop":[]}}'                         > "$dir/wellforge-plugin/hooks/hooks.json"
  cp "$CLI" "$dir/scripts/wellforge"                   # so `version` resolves this checkout

  git init -q "$dir"
  git -C "$dir" config user.email t@t; git -C "$dir" config user.name t
  git -C "$dir" add -A >/dev/null; git -C "$dir" commit -qm "fixture"
  git -C "$dir" tag "$tag"
  git init -q --bare "$origin"
  git -C "$dir" remote add origin "$origin"
  git -C "$dir" push -q -u origin HEAD:refs/heads/main 2>/dev/null
  git -C "$dir" branch --set-upstream-to=origin/main >/dev/null 2>&1
}

advance_upstream() { # <checkout-dir> <n>  — put N commits on the bare origin only
  local dir="$1" n="$2" work; work="$(mktemp -d)"
  git clone -q "$dir.origin" "$work"
  git -C "$work" config user.email t@t; git -C "$work" config user.name t
  local i
  for i in $(seq 1 "$n"); do
    echo "$i" >> "$work/upstream.txt"
    git -C "$work" add -A >/dev/null; git -C "$work" commit -qm "upstream $i"
  done
  git -C "$work" push -q origin HEAD:main
  rm -rf "$work"
}

# ── runner ────────────────────────────────────────────────────────────────────
# Each case gets its own HOME, its own bin dir and its own shim log.
SANDBOX_N=0
new_sandbox() { # <tool…>  → sets HOME_DIR, BIN, SHIM_LOG, SANDBOX
  SANDBOX_N=$((SANDBOX_N + 1))
  SANDBOX="$SUITE/s$SANDBOX_N"
  HOME_DIR="$SANDBOX/home"; BIN="$SANDBOX/bin"; SHIM_LOG="$SANDBOX/calls.log"
  mkdir -p "$HOME_DIR" "$BIN"; : > "$SHIM_LOG"
  make_shims "$BIN" "$@"
}

# Every FAKE_* the shims understand. Passed through an ARRAY, never an unquoted
# ${var+…} expansion: several of these values contain spaces and quotes, and word
# splitting there would turn an env assignment into a command.
FAKE_VARS=(FAKE_BREW_VERSION FAKE_BREW_OUTDATED FAKE_BREW_OUTDATED_PKG_RC
           FAKE_BREW_INSTALL_RC FAKE_BREW_INSTALL_ERR FAKE_BREW_UPGRADE_RC
           FAKE_BREW_UPGRADE_ERR FAKE_BREW_UPDATE_RC FAKE_BREW_LIST_VERSION
           FAKE_CLAUDE_VERSION FAKE_CLAUDE_MARKETPLACES FAKE_CLAUDE_PLUGINS
           FAKE_CLAUDE_MKT_ADD_RC FAKE_CLAUDE_INSTALL_RC
           FAKE_GH_AUTH_RC FAKE_DOCKER_INFO_RC FAKE_COPIER_RC
           FAKE_MISE_USE_RC FAKE_MISE_USE_ERR FAKE_NPM_INSTALL_RC FAKE_NPM_INSTALL_ERR
           FAKE_TG_GETME FAKE_TG_GETUPDATES FAKE_TG_SEND)

run_cli() { # <wellforge-home> <args…> ; stdin from $RUN_STDIN (default /dev/null)
  local wf_home="$1"; shift
  local stdin_file="${RUN_STDIN:-/dev/null}" v
  # env -i so the developer's real TELEGRAM_* / WELLFORGE_* / PATH cannot reach the CLI:
  # an ambient TELEGRAM_BOT_TOKEN would silently change what telegram_configured answers.
  local -a envs=(
    HOME="$HOME_DIR"
    PATH="$BIN:/usr/bin:/bin:/usr/sbin:/sbin"
    SHIM_LOG="$SHIM_LOG"
    WELLFORGE_HOME="$wf_home"
    WELLFORGE_REPO="${RUN_REPO:-}"
    TERM=dumb
  )
  for v in "${FAKE_VARS[@]}"; do
    [ -n "${!v+set}" ] && envs+=("$v=${!v}")
  done
  # Watchdog, not a nicety: `wellforge telegram` with an exhausted stdin spins forever in
  # its token loop (read fails, token is empty, `continue`). Without this a single such
  # regression hangs CI until the job limit instead of failing in seconds. `timeout(1)` is
  # not on a bare macOS, so poll a background job.
  local out_file="$SANDBOX/out.$$"
  env -i "${envs[@]}" bash "${RUN_CLI:-$CLI}" "$@" < "$stdin_file" > "$out_file" 2>&1 &
  local pid=$! i
  for i in $(seq 1 "${RUN_TIMEOUT:-30}"); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 1
  done
  if kill -0 "$pid" 2>/dev/null; then
    kill -9 "$pid" 2>/dev/null
    wait "$pid" 2>/dev/null
    OUT="$(cat "$out_file" 2>/dev/null)"; RC="timeout"
    _bad "timed out after ${RUN_TIMEOUT:-30}s — the CLI did not exit"
  else
    wait "$pid"; RC=$?
    OUT="$(cat "$out_file" 2>/dev/null)"
  fi
  rm -f "$out_file"
}

reset_fakes() {
  local v
  for v in "${FAKE_VARS[@]}"; do unset "$v"; done
  unset RUN_STDIN RUN_REPO RUN_CLI RUN_TIMEOUT
}

ALL_TOOLS=(brew claude gh docker uvx mise uv npx node npm open curl)

# ══ cases ═════════════════════════════════════════════════════════════════════
printf '\nwellforge CLI matrix\n\n'

# ── 1. doctor with no checkout — the prompt-1 bug: it used to die at rc=2 here ──
reset_fakes; begin "doctor, no checkout: complete report and rc=1"
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" doctor
assert_rc "$RC" 1
assert_has "$OUT" "wellforge repo"
assert_has "$OUT" "run: wellforge setup"
assert_has "$OUT" "collisions"          # skipped-with-reason, not silence
assert_has "$OUT" "telegram"            # the run reached the end…
assert_has "$OUT" "check(s) failed"     # …and printed its summary
assert_has "$OUT" "next: no checkout"
finish

# ── 2. healthy checkout, current with upstream ────────────────────────────────
reset_fakes; begin "doctor, healthy checkout: rc=0 and 'environment ready'"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_rc "$RC" 0
assert_has "$OUT" "environment ready."
assert_has "$OUT" "current with origin/main"
assert_has "$OUT" "collisions         none"
finish

# ── 3. checkout behind upstream — the warning must name the count ─────────────
reset_fakes; begin "doctor, 3 commits behind: the warning names 3"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
advance_upstream "$SANDBOX/wf" 3
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "3 commit(s) behind"
assert_has "$OUT" "wellforge update"
finish

# ── 4. plugin cache drift ─────────────────────────────────────────────────────
reset_fakes; begin "doctor, cache version != source: cache warning"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "loaded v2.40.0 but source is v2.43.0"
finish

reset_fakes; begin "doctor, cache version == source: cache ok"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "v2.43.0 matches source"
assert_lacks "$OUT" "but source is"
finish

# ── 5. collisions are advisory: they warn, they never change the exit status ──
reset_fakes; begin "doctor, colliding global agent: warns, rc unaffected"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0" "$HOME_DIR/.claude/agents"
echo "# mine" > "$HOME_DIR/.claude/agents/architect.md"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "collision"
assert_has "$OUT" "architect"
assert_rc "$RC" 0                        # advisory: never counted as a failure
assert_exists "$HOME_DIR/.claude/agents/architect.md"
finish

reset_fakes; begin "doctor --fix non-interactive: warns, never prompts, moves nothing"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0" "$HOME_DIR/.claude/agents"
echo "# mine" > "$HOME_DIR/.claude/agents/architect.md"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor --fix       # stdin is /dev/null by default
assert_has "$OUT" "collision"
assert_lacks "$OUT" "disable global agent"     # the prompt text must not appear
assert_exists "$HOME_DIR/.claude/agents/architect.md"
assert_absent "$HOME_DIR/.claude/agents-disabled-by-wellforge"
finish

# ── 6. brew missing: counted, and every later check still runs ────────────────
reset_fakes; begin "doctor, no brew: homebrew counted and the run continues"
new_sandbox claude gh docker uvx mise uv npx node npm open curl   # no brew shim
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "homebrew"
assert_has "$OUT" "telegram"             # reached the end despite the first check failing
assert_has "$OUT" "check(s) failed"
assert_rc "$RC" 1
finish

# ── 7. --fix with a failing brew install: brew's own error reaches the user ───
reset_fakes; begin "doctor --fix, brew install fails: shows brew's error, keeps going"
new_sandbox brew claude gh docker uvx uv npx node npm open curl   # no mise → --fix installs it
FAKE_BREW_INSTALL_RC=1
FAKE_BREW_INSTALL_ERR="Error: No available formula with the name \"mise\"."
run_cli "$SANDBOX/nowhere" doctor --fix
assert_has "$OUT" 'No available formula with the name "mise".'
assert_has "$OUT" "check(s) failed"      # continued to the summary
assert_rc "$RC" 1
finish

# ── 8. setup, non-interactive ─────────────────────────────────────────────────
reset_fakes; begin "setup </dev/null: never blocks, ends with a message, writes config"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/src" "2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
RUN_REPO="$SANDBOX/src"
run_cli "$SANDBOX/dest" setup
assert_has_re "$OUT" "(done\.|setup finished)"
assert_file_has "$HOME_DIR/.config/wellforge/config" "$SANDBOX/dest"
assert_exists "$SANDBOX/dest/.claude-plugin/marketplace.json"
finish

# ── 9. update must not churn a plugin that is already current ─────────────────
#    Reinstalling unconditionally throws away a good cache and costs a download every
#    run. Expected to fail until that behaviour lands.
reset_fakes; begin "update, plugin already current: no uninstall/install" xfail
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" update
assert_lacks "$(cat "$SHIM_LOG")" "plugin uninstall"
assert_lacks "$(cat "$SHIM_LOG")" "plugin install"
finish

# ── 10. dispatch ──────────────────────────────────────────────────────────────
reset_fakes; begin "help: prints usage, rc=0"
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" help
assert_rc "$RC" 0
assert_has "$OUT" "wellforge setup"
assert_has "$OUT" "wellforge doctor"
finish

# An unknown subcommand is a user error, and a tool that exits 0 on one cannot be
# used in a script. Expected to fail until that lands.
reset_fakes; begin "unknown subcommand: prints help and exits non-zero" xfail
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" not-a-command
assert_has "$OUT" "wellforge setup"
[ "$RC" -ne 0 ] || _bad "expected a non-zero rc for an unknown subcommand, got 0"
finish

# ── 11. version from a checkout ───────────────────────────────────────────────
reset_fakes; begin "version, run from a checkout: names the checkout and its describe"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0" "v1.2.3"
RUN_CLI="$SANDBOX/wf/scripts/wellforge"
run_cli "$SANDBOX/wf" version
assert_rc "$RC" 0
assert_has "$OUT" "running from checkout"
assert_has "$OUT" "v1.2.3"
finish

# ── 12. telegram wizard, fully canned ─────────────────────────────────────────
reset_fakes; begin "telegram: verifies the token against getMe"
new_sandbox "${ALL_TOOLS[@]}"
printf 'shim-token\n\n' > "$SANDBOX/stdin"; RUN_STDIN="$SANDBOX/stdin"
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":4242,"type":"private"}}}]}'
FAKE_TG_SEND='{"ok":true}'
run_cli "$SANDBOX/nowhere" telegram
assert_has "$OUT" "bot verified"
assert_has "$OUT" "shim_bot"
assert_has "$OUT" "4242"
finish

# A group chat in the same payload must not be picked: the notify hook DMs one person,
# and posting Claude's permission prompts into a group is a privacy leak. `last` takes
# whatever arrived most recently. Expected to fail until the selection is type-aware.
reset_fakes; begin "telegram: picks the PRIVATE chat when a group message is also present" xfail
new_sandbox "${ALL_TOOLS[@]}"
printf 'shim-token\n\n' > "$SANDBOX/stdin"; RUN_STDIN="$SANDBOX/stdin"
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":4242,"type":"private"}}},{"message":{"chat":{"id":-1009,"type":"group"}}}]}'
FAKE_TG_SEND='{"ok":true}'
run_cli "$SANDBOX/nowhere" telegram
assert_has "$OUT" "4242"
assert_lacks "$OUT" "-1009"
finish

# Found while building this suite, not from the brief: with stdin at EOF the token loop
# spins forever — `read` fails, the token is empty, `continue`, repeat. Interactively you
# press Ctrl-C; in a script or CI it burns a core until something kills it. A guided
# wizard that cannot be run non-interactively should say so and exit.
reset_fakes; begin "telegram </dev/null: exits instead of spinning on an exhausted stdin" xfail
new_sandbox "${ALL_TOOLS[@]}"
RUN_TIMEOUT=8                      # it is expected to hang; do not wait the full budget
run_cli "$SANDBOX/nowhere" telegram
[ "$RC" = "timeout" ] && _bad "spun forever instead of exiting"
finish

# ── summary ───────────────────────────────────────────────────────────────────
printf '\nwellforge CLI: %d passed, %d failed, %d expected-fail' "$pass" "$fail" "$xfail"
[ "$xpass" -gt 0 ] && printf ', %d UNEXPECTEDLY PASSING' "$xpass"
printf '\n'
# An xpass is not a failure of the CLI, but it IS a failure of this file to describe it.
[ "$fail" -eq 0 ] && [ "$xpass" -eq 0 ]
