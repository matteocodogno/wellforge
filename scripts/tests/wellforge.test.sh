#!/usr/bin/env bash
# shellcheck disable=SC2034
# ^ FILE-LEVEL, and deliberately so. Every FAKE_* assignment below looks unused because its
# only consumer is a generated shim executable, reached through an INDIRECT expansion over
# the FAKE_VARS array (which holds variable NAMES, not references) — shellcheck cannot
# follow that, and reports 13 separate SC2034s for one mechanism. The repo's rule is
# "inline disable with a reason, never a blanket exclusion"; thirteen copies of the same
# sentence is not more informative than one, and `export`ing them instead would make the
# explicit env list the harness builds redundant. One directive, one reason, one place.
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
assert_called()    { grep -qE "^$1( |\$)" "$SHIM_LOG" 2>/dev/null || _bad "expected a call to '$1'"; }
assert_not_called(){ grep -qE "^$1( |\$)" "$SHIM_LOG" 2>/dev/null && _bad "'$1' should not have been called"; return 0; }
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
      echo "brew-outdated-list" >> "$SHIM_LOG"   # counted: it should run once per command
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
  # Shaped like the real command's output, captured from the CLI:
  #     Configured marketplaces:        Installed plugins:
  #       ❯ wellforge                     ❯ wellforge-extras@wellforge
  # A shim that prints a bare word would let an unanchored grep pass and hide the bug.
  "plugin marketplace list")
    echo "Configured marketplaces:"; echo
    for m in ${FAKE_CLAUDE_MARKETPLACES:-}; do echo "  ❯ $m"; echo "    Source: Directory (/tmp/x)"; done ;;
  "plugin list")
    echo "Installed plugins:"; echo
    for pl in ${FAKE_CLAUDE_PLUGINS:-}; do echo "  ❯ $pl"; echo "    Version: 1.0.0"; echo "    Scope: user"; done ;;
  "plugin marketplace add"*)   exit "${FAKE_CLAUDE_MKT_ADD_RC:-0}" ;;
  "plugin install"*)
    [ "${FAKE_CLAUDE_INSTALL_RC:-0}" = "0" ] || { echo "Error: install refused" >&2; exit 1; } ;;
  "plugin update"*)
    # Modelled on the real CLI, verified by hand: a successful update WRITES a new
    # version-keyed cache dir and leaves the old one for the caller to prune.
    if [ "${FAKE_CLAUDE_UPDATE_RC:-0}" != "0" ]; then
      echo "${FAKE_CLAUDE_UPDATE_ERR:-Error: could not reach the marketplace}" >&2; exit 1
    fi
    [ -n "${FAKE_CLAUDE_UPDATE_TO:-}" ] \
      && mkdir -p "$HOME/.claude/plugins/cache/wellforge/wellforge/$FAKE_CLAUDE_UPDATE_TO" ;;
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
      open|xdg-open) cat > "$bin/$t" <<SH
#!/usr/bin/env bash
# Never actually open a browser during a test run. Both exist in the sandbox on purpose:
# on Linux \`open\` is util-linux's open(1), NOT a browser launcher, so the CLI must reach
# for xdg-open there and leave \`open\` alone.
echo "$t \$*" >> "\$SHIM_LOG"
exit 0
SH
        ;;
      git-watch) cat > "$bin/git" <<'SH'
#!/usr/bin/env bash
# Real git for everything (the fixtures are real repositories), except that a `fetch` is
# logged with its full argv — which is how the fallback path is observed — and hangs when
# asked, which is the flaky-VPN case the 10s bound exists for.
case " $* " in
  *" fetch "*)
    echo "git $*" >> "$SHIM_LOG"
    [ -n "${FAKE_GIT_FETCH_HANG:-}" ] && sleep 300 ;;
esac
exec /usr/bin/git "$@"
SH
        # The file is "git", not "git-watch" — the loop's chmod at the bottom uses $t and
        # would leave it non-executable, so PATH would silently fall through to real git.
        chmod +x "$bin/git" ;;
      timeout) cat > "$bin/timeout" <<'SH'
#!/usr/bin/env bash
# Enough of coreutils' timeout to bound a hanging command. macOS ships neither `timeout`
# nor `gtimeout`, so without this the primary path could only ever be exercised on CI.
dur="$1"; shift
"$@" & pid=$!
( sleep "$dur"; kill -9 "$pid" 2>/dev/null ) & killer=$!
wait "$pid"; rc=$?
kill "$killer" 2>/dev/null
exit "$rc"
SH
        ;;
      uname) cat > "$bin/uname" <<'SH'
#!/usr/bin/env bash
# The whole platform split hangs off this one call.
printf '%s\n' "${FAKE_UNAME:-Darwin}"
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
# Fixture git must not inherit the developer's global config. Signing is the one that bit:
# a locked 1Password agent turned every fixture commit into "failed to fill whole buffer"
# and the suite failed for reasons that had nothing to do with the CLI. A global
# core.hooksPath would be just as bad — this repo's own commit-msg hook would reject
# "fixture" as a non-conventional commit message.
gitf() { git -c commit.gpgsign=false -c tag.gpgsign=false -c init.templateDir= \
             -c core.hooksPath="$SUITE/nohooks" -c user.email=t@t -c user.name=t "$@"; }

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

  mkdir -p "$SUITE/nohooks"
  gitf init -q "$dir"
  gitf -C "$dir" add -A >/dev/null
  gitf -C "$dir" commit -qm "fixture" >/dev/null || { echo "fixture commit failed" >&2; return 1; }
  gitf -C "$dir" tag "$tag"
  gitf init -q --bare "$origin"
  gitf -C "$dir" remote add origin "$origin"
  gitf -C "$dir" push -q -u origin HEAD:refs/heads/main 2>/dev/null
  gitf -C "$dir" branch --set-upstream-to=origin/main >/dev/null 2>&1
}

set_checkout_cli_version() { # <checkout-dir> <version>  — rewrite the fixture CLI's constant
  local f="$1/scripts/wellforge" t; t="$(mktemp)"
  sed "s/^WELLFORGE_CLI_VERSION=\".*\"/WELLFORGE_CLI_VERSION=\"$2\"/" "$f" > "$t"
  cat "$t" > "$f"; rm -f "$t"
}

advance_upstream() { # <checkout-dir> <n>  — put N commits on the bare origin only
  local dir="$1" n="$2" work; work="$(mktemp -d)"
  gitf clone -q "$dir.origin" "$work"
  local i
  for i in $(seq 1 "$n"); do
    echo "$i" >> "$work/upstream.txt"
    gitf -C "$work" add -A >/dev/null; gitf -C "$work" commit -qm "upstream $i" >/dev/null
  done
  gitf -C "$work" push -q origin HEAD:main
  rm -rf "$work"
}

# Telegram wizard inputs: the token line and the Enter after "send a message". Stdin is a
# FILE, so `[ -t 0 ]` stays false and the non-interactive branches are what gets exercised.
tg_stdin() { printf 'shim-token\n\n' > "$SANDBOX/stdin"; RUN_STDIN="$SANDBOX/stdin"; }
tg_canned() {
  FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
  FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":4242,"type":"private"}}}]}'
  FAKE_TG_SEND='{"ok":true}'
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
           FAKE_CLAUDE_UPDATE_RC FAKE_CLAUDE_UPDATE_ERR FAKE_CLAUDE_UPDATE_TO
           FAKE_GH_AUTH_RC FAKE_DOCKER_INFO_RC FAKE_COPIER_RC
           FAKE_MISE_USE_RC FAKE_MISE_USE_ERR FAKE_NPM_INSTALL_RC FAKE_NPM_INSTALL_ERR
           FAKE_TG_GETME FAKE_TG_GETUPDATES FAKE_TG_SEND
           FAKE_UNAME FAKE_GIT_FETCH_HANG)

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
    # Empty unless a case sets RUN_MARKETPLACE. The CLI reads
    # ${WELLFORGE_MARKETPLACE:-matteocodogno/wellforge}, so empty == the git default —
    # and it has to be listed HERE, because env -i deliberately drops ambient WELLFORGE_*.
    WELLFORGE_MARKETPLACE="${RUN_MARKETPLACE:-}"
    TERM=dumb
    # The login shell decides which rc file gets written; env -i would otherwise leave it
    # unset and every shell-wiring case would test the same "unknown shell" branch.
    SHELL="${RUN_SHELL:-/bin/zsh}"
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
  unset RUN_STDIN RUN_REPO RUN_CLI RUN_TIMEOUT RUN_SHELL
}

ALL_TOOLS=(brew claude gh docker uvx mise uv npx node npm open xdg-open curl uname)

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

# ── 9. update: only when needed, and never destructive ───────────────────────
# The old step ran `uninstall && install` on every run. It did the work even when the
# cache already matched, and a failing install left the user with no plugin at all.
reset_fakes; begin "update, cache already current: no plugin calls at all"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" update
assert_has "$OUT" "v2.43.0 already loaded"
assert_lacks "$(cat "$SHIM_LOG")" "plugin uninstall"
assert_lacks "$(cat "$SHIM_LOG")" "plugin install"
assert_lacks "$(cat "$SHIM_LOG")" "plugin update"
finish

reset_fakes; begin "update, cache stale: updates in place, never uninstalls"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
FAKE_CLAUDE_UPDATE_TO="2.43.0"
run_cli "$SANDBOX/wf" update
assert_has "$OUT" "updated to v2.43.0"
assert_has "$(cat "$SHIM_LOG")" "plugin update"
assert_lacks "$(cat "$SHIM_LOG")" "plugin uninstall"
assert_exists "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
assert_absent "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"   # pruned after
finish

# The whole point: a failed refresh must cost nothing. The previous version still loads.
reset_fakes; begin "update fails: nothing uninstalled, the old cache survives"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
FAKE_CLAUDE_UPDATE_RC=1
FAKE_CLAUDE_UPDATE_ERR="Error: could not reach the marketplace"
run_cli "$SANDBOX/wf" update
assert_has "$OUT" "could not reach the marketplace"
assert_has "$OUT" "previous version left in place"
assert_lacks "$(cat "$SHIM_LOG")" "plugin uninstall"
assert_exists "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"
finish

# A cache dir NEWER than the source is someone testing an unreleased bump. Pruning it
# would delete the only copy of work in progress.
reset_fakes; begin "prune: keeps a cached version newer than the source"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0" \
         "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/9.9.9"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
FAKE_CLAUDE_UPDATE_TO="2.43.0"
run_cli "$SANDBOX/wf" update
assert_exists "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/9.9.9"    # newer: kept
assert_absent "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.40.0"   # older: pruned
assert_has "$OUT" "NEWER than the source"
finish

reset_fakes; begin "update, plugin not installed: says so, does not try to update"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS=""
run_cli "$SANDBOX/wf" update
assert_has "$OUT" "not installed"
assert_lacks "$(cat "$SHIM_LOG")" "plugin update"
finish

# ── 10. dispatch ──────────────────────────────────────────────────────────────
reset_fakes; begin "help: prints usage, rc=0"
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" help
assert_rc "$RC" 0
assert_has "$OUT" "wellforge setup"
assert_has "$OUT" "wellforge doctor"
finish

# ── 11. version from a checkout ───────────────────────────────────────────────
reset_fakes; begin "version: prints the CLI constant, the origin, and the describe"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0" "v1.2.3"
set_checkout_cli_version "$SANDBOX/wf" "3.4.5"
RUN_CLI="$SANDBOX/wf/scripts/wellforge"
run_cli "$SANDBOX/wf" version
assert_rc "$RC" 0
assert_has "$OUT" "wellforge 3.4.5"     # the constant, not the Cellar path or the tag
assert_has "$OUT" "(checkout)"
assert_has "$OUT" "v1.2.3"              # the describe is still there, as context
finish

# ── 13. the CLI is a different file from the checkout's copy, and they drift ─────────
reset_fakes; begin "doctor: warns when the running CLI is behind the checkout's"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
set_checkout_cli_version "$SANDBOX/wf" "99.0.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "behind the checkout's 99.0.0"
assert_has "$OUT" "brew upgrade wellforge"
assert_rc "$RC" 0                        # advisory: a stale CLI still works
finish

reset_fakes; begin "doctor: warns when the checkout is behind the running CLI"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
set_checkout_cli_version "$SANDBOX/wf" "0.0.1"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "NEWER than the checkout's 0.0.1"
assert_has "$OUT" "wellforge update"
finish

reset_fakes; begin "doctor: cli ok when the two copies agree"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "matches the checkout"
assert_rc "$RC" 0
finish

# ── 14. the release contract: the constant, the tag and the Formula must agree ───────
# These read the REPO, not a sandbox: they are what stops a CLI release from being
# half-done, which is the failure this whole series exists to fix.
reset_fakes; begin "release: WELLFORGE_CLI_VERSION equals the newest cli-v tag"
const="$(sed -n 's/^WELLFORGE_CLI_VERSION="\([^"]*\)".*/\1/p' "$CLI" | head -1)"
newest_tag="$(git -C "$ROOT" tag -l 'cli-v*' --sort=v:refname 2>/dev/null | tail -1)"
if [ -z "$newest_tag" ]; then
  # A shallow CI checkout has no tags at all. That is not a pass — say which it is.
  if [ "$(git -C "$ROOT" rev-parse --is-shallow-repository 2>/dev/null)" = "true" ]; then
    _bad "no cli-v* tags and the clone is shallow — fetch tags (fetch-depth: 0) or this check is blind"
  else
    _bad "no cli-v* tag exists, but scripts/wellforge declares $const — an untagged release reaches nobody"
  fi
else
  assert_has "$newest_tag" "cli-v$const"
  [ "$newest_tag" = "cli-v$const" ] || _bad "newest tag is $newest_tag but the constant is $const"
fi
finish

# No longer xfail. The url now names the CLI series and the formula carries an explicit
# `version`; only the SHA still waits on a pushed tag (GitHub generates the tarball and its
# bytes are not reproducible locally, so release-cli.sh fetches it after pushing). Pointing
# at the series does not need the tarball — that conflation is why the formula sat on the
# template tag v0.9.0 while the CLI shipped four releases in its own series.
reset_fakes; begin "release: the Formula points at the CLI series, not the template's"
grep -q 'archive/refs/tags/cli-v' "$ROOT/Formula/wellforge.rb" \
  || _bad "Formula url still names a non-cli tag: $(grep -o 'refs/tags/[^"]*' "$ROOT/Formula/wellforge.rb")"
grep -q "^  version \"$const\"\$" "$ROOT/Formula/wellforge.rb" \
  || _bad "Formula has no 'version \"$const\"' line matching the constant"
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

# A group chat in the same payload must not be picked: the hook DMs one person, and
# posting Claude's permission prompts into a group is a leak. `last` took whatever
# arrived most recently, which on a bot that sits in a group is the group.
reset_fakes; begin "telegram: picks the PRIVATE chat when a group message is also present"
new_sandbox "${ALL_TOOLS[@]}"
printf 'shim-token\n\n' > "$SANDBOX/stdin"; RUN_STDIN="$SANDBOX/stdin"
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":4242,"type":"private","username":"me"}}},{"message":{"chat":{"id":-1009,"type":"group","title":"team"}}}]}'
FAKE_TG_SEND='{"ok":true}'
run_cli "$SANDBOX/nowhere" telegram
assert_has "$OUT" "4242"
assert_has "$OUT" "@me"                       # the chosen account is named, not just its id
assert_lacks "$OUT" "-1009"
assert_file_has "$HOME_DIR/.config/wellforge/telegram.env" "TELEGRAM_CHAT_ID=\"4242\""
finish

# Two people have messaged the bot. Picking one is a coin flip that sends someone else's
# permission prompts to the wrong person, so non-interactively it must refuse.
reset_fakes; begin "telegram: two private chats, non-interactive: dies with the list"
new_sandbox "${ALL_TOOLS[@]}"
tg_stdin
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":111,"type":"private","username":"alice"}}},{"message":{"chat":{"id":222,"type":"private","username":"bob"}}}]}'
FAKE_TG_SEND='{"ok":true}'
run_cli "$SANDBOX/nowhere" telegram
assert_rc "$RC" 1
assert_has "$OUT" "more than one private chat"
assert_has "$OUT" "@alice"
assert_has "$OUT" "@bob"
assert_absent "$HOME_DIR/.config/wellforge/telegram.env"   # nothing saved on a refusal
finish

# getUpdates and a webhook are mutually exclusive; without this the retry loop spins for
# 20s and then blames the user for not sending a message.
reset_fakes; begin "telegram: a webhook conflict is explained, not retried"
new_sandbox "${ALL_TOOLS[@]}"
tg_stdin
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":false,"error_code":409,"description":"Conflict: can'"'"'t use getUpdates method while webhook is active"}'
run_cli "$SANDBOX/nowhere" telegram
assert_rc "$RC" 1
assert_has "$OUT" "webhook"
assert_has "$OUT" "deleteWebhook"
assert_lacks "$OUT" "retrying (5/10)"
finish

# Telegram says exactly what is wrong; the old code printed a generic three-way guess.
reset_fakes; begin "telegram: a send failure shows Telegram's own description"
new_sandbox "${ALL_TOOLS[@]}"
tg_stdin
FAKE_TG_GETME='{"ok":true,"result":{"username":"shim_bot"}}'
FAKE_TG_GETUPDATES='{"ok":true,"result":[{"message":{"chat":{"id":4242,"type":"private","username":"me"}}}]}'
FAKE_TG_SEND='{"ok":false,"error_code":403,"description":"Forbidden: bot was blocked by the user"}'
run_cli "$SANDBOX/nowhere" telegram
assert_has "$OUT" "bot was blocked by the user"
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

# ── 15. Linux is a supported platform, so behave like it ────────────────────────────
# README has always said "macOS or Linux with Homebrew". The script said "on a Mac" and
# its Linux failures were the quiet kind: a source line written to a file the shell never
# reads, followed by a tick.


# The wizard no longer writes to ANY rc file. Sourcing the env file from the shell put
# TELEGRAM_BOT_TOKEN into every process the user starts — Claude Code's children included,
# where one `env` in a transcript leaks a live token — while the notify hook was already
# reading the file itself. Exposure with no function. One case per shell, because the old
# code branched per shell and a regression would most likely come back that way.
for _sh in /usr/bin/zsh /bin/bash /usr/bin/fish; do
  for _os in Linux Darwin; do
    reset_fakes; begin "telegram writes no rc file ($(basename "$_sh") on $_os)"
    new_sandbox "${ALL_TOOLS[@]}"
    FAKE_UNAME="$_os"; RUN_SHELL="$_sh"; tg_stdin; tg_canned
    run_cli "$SANDBOX/nowhere" telegram
    assert_absent "$HOME_DIR/.zshrc"
    assert_absent "$HOME_DIR/.bashrc"
    assert_absent "$HOME_DIR/.bash_profile"
    assert_absent "$HOME_DIR/.profile"
    assert_has "$OUT" "token never enters your shell environment"
    finish
  done
done

# The env file is the whole configuration, so its permissions are the whole protection.
reset_fakes; begin "telegram: env file 600, its directory 700"
new_sandbox "${ALL_TOOLS[@]}"
tg_stdin; tg_canned
run_cli "$SANDBOX/nowhere" telegram
assert_exists "$HOME_DIR/.config/wellforge/telegram.env"
[ "$(stat -f '%Lp' "$HOME_DIR/.config/wellforge/telegram.env" 2>/dev/null \
     || stat -c '%a' "$HOME_DIR/.config/wellforge/telegram.env" 2>/dev/null)" = "600" ] \
  || _bad "env file is not mode 600"
[ "$(stat -f '%Lp' "$HOME_DIR/.config/wellforge" 2>/dev/null \
     || stat -c '%a' "$HOME_DIR/.config/wellforge" 2>/dev/null)" = "700" ] \
  || _bad "config dir is not mode 700"
finish

# An earlier run wired the shell. Offer to undo it — non-interactively, print the line.
reset_fakes; begin "telegram: an rc line from an earlier version is surfaced for removal"
new_sandbox "${ALL_TOOLS[@]}"
RUN_SHELL=/bin/bash; tg_stdin; tg_canned
printf '# WellForge Telegram notifications\n[ -f "%s/.config/wellforge/telegram.env" ] && . "%s/.config/wellforge/telegram.env"\n' \
  "$HOME_DIR" "$HOME_DIR" > "$HOME_DIR/.bashrc"
run_cli "$SANDBOX/nowhere" telegram
assert_has "$OUT" "exports the bot token into every process"
assert_has "$OUT" "delete this line"
assert_file_has "$HOME_DIR/.bashrc" "telegram.env"   # non-interactive: reported, not edited
finish

# On Linux, `open` is util-linux's open(1) — it opens a virtual terminal, not a browser.
reset_fakes; begin "linux: opens URLs with xdg-open and never calls open(1)"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Linux; RUN_SHELL=/bin/bash; tg_stdin; tg_canned
run_cli "$SANDBOX/nowhere" telegram
assert_called "xdg-open"
assert_not_called "open"          # util-linux open(1) is not a browser launcher
finish

reset_fakes; begin "macos: opens URLs with open and never calls xdg-open"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Darwin; RUN_SHELL=/bin/zsh; tg_stdin; tg_canned
run_cli "$SANDBOX/nowhere" telegram
assert_called "open"
assert_not_called "xdg-open"
finish

reset_fakes; begin "linux: docker advice is the docker group, not Docker Desktop"
new_sandbox brew claude gh uvx mise uv npx node npm curl uname   # no docker shim
FAKE_UNAME=Linux; RUN_SHELL=/bin/bash
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "add your user to the 'docker' group"
assert_lacks "$OUT" "Docker Desktop"
assert_lacks "$OUT" "--cask"
finish

reset_fakes; begin "macos: docker advice is still Docker Desktop"
new_sandbox brew claude gh uvx mise uv npx node npm curl uname
FAKE_UNAME=Darwin; RUN_SHELL=/bin/zsh
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "docker-desktop"
finish

# A daemon that is installed but unreachable is the group-membership case on Linux at
# least as often as it is a stopped Desktop.
reset_fakes; begin "linux: docker present but daemon unreachable names the group fix"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Linux; RUN_SHELL=/bin/bash; FAKE_DOCKER_INFO_RC=1
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "usermod -aG docker"
assert_lacks "$OUT" "Docker Desktop"
finish

# mise installs into a shim dir that is on PATH only after activation. Claude Code
# inherits the login shell's environment, so an unactivated mise means the MCP servers
# never start — and the old check said "installed" and moved on.
reset_fakes; begin "mise not activated: warns with the exact activate line for the shell"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Linux; RUN_SHELL=/bin/bash
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "mise activated"
assert_has "$OUT" "not activated for bash"
assert_has "$OUT" "mise activate bash"
assert_has "$OUT" "MCP servers"
finish

reset_fakes; begin "mise activated via the rc file: reported ok, no warning"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Linux; RUN_SHELL=/bin/bash
printf 'eval "$(mise activate bash)"\n' > "$HOME_DIR/.bashrc"
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" ".bashrc activates it"
assert_lacks "$OUT" "not activated for"
finish

reset_fakes; begin "fish: the activate line uses fish syntax, not eval"
new_sandbox "${ALL_TOOLS[@]}"
FAKE_UNAME=Linux; RUN_SHELL=/usr/bin/fish
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "mise activate fish | source"
finish

# ── 16. the small-fixes batch ───────────────────────────────────────────────────────

# `brew outdated` resolves the whole tap. Four tools meant four of them per doctor.
reset_fakes; begin "brew outdated runs once per command, not once per tool"
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" doctor --fix
n=$(grep -c '^brew-outdated-list$' "$SHIM_LOG")
[ "$n" = "1" ] || _bad "expected 1 'brew outdated --quiet' call, got $n"
finish

# grep -q "wellforge" matched ANY plugin containing the word. With only the decoy
# installed, doctor used to report the real plugin as present.
reset_fakes; begin "a decoy plugin named wellforge-extras is not mistaken for wellforge"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge"
FAKE_CLAUDE_PLUGINS="wellforge-extras@wellforge"     # the real one is NOT installed
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "claude plugin install wellforge@wellforge"   # reported missing, correctly
assert_lacks "$OUT" "✓ plugin             wellforge installed"
finish

reset_fakes; begin "the real plugin alongside the decoy is recognised"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
mkdir -p "$HOME_DIR/.claude/plugins/cache/wellforge/wellforge/2.43.0"
FAKE_CLAUDE_MARKETPLACES="wellforge"
FAKE_CLAUDE_PLUGINS="wellforge-extras@wellforge wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$OUT" "wellforge installed"
finish

# A diagnostics tool that hangs is worse than one that reports a problem: doctor used to
# run a plain `git fetch` on every invocation.
reset_fakes; begin "a hanging git fetch is bounded, and reads as offline"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
make_shims "$BIN" git-watch timeout        # shadow git AFTER the fixture is built
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
FAKE_GIT_FETCH_HANG=1
RUN_TIMEOUT=45                             # the bound is 10s; the hang would be 300s
run_cli "$SANDBOX/wf" doctor
[ "$RC" = "timeout" ] && _bad "doctor hung on the fetch instead of bounding it"
assert_has "$OUT" "skipped update check"
assert_has "$OUT" "offline"
finish

# No coreutils timeout (bare macOS): git's own low-speed abort has to be the fallback,
# because an unbounded fetch is the thing being removed.
reset_fakes; begin "with no timeout binary, the fetch falls back to git's low-speed abort"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
make_shims "$BIN" git-watch                # note: no timeout shim
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" doctor
assert_has "$(cat "$SHIM_LOG")" "http.lowSpeedLimit=1000"
assert_has "$(cat "$SHIM_LOG")" "http.lowSpeedTime=10"
finish

# A typo used to exit 0, so no wrapper script could tell.
reset_fakes; begin "unknown subcommand: help on stderr, exit 1"
new_sandbox "${ALL_TOOLS[@]}"
run_cli "$SANDBOX/nowhere" dcotor
assert_rc "$RC" 1
assert_has "$OUT" "unknown command: dcotor"
assert_has "$OUT" "wellforge doctor"        # the help still prints
finish

reset_fakes; begin "help, -h and --help all exit 0"
new_sandbox "${ALL_TOOLS[@]}"
for flag in help -h --help; do
  run_cli "$SANDBOX/nowhere" "$flag"
  assert_rc "$RC" 0
  assert_has "$OUT" "wellforge setup"
done
finish

# "no upstream yet" was a guess, and wrong for the commonest case: a contributor with
# local commits on the checkout.
reset_fakes; begin "a pull that fails shows git's reason, not a guess"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/wf" "2.43.0"
advance_upstream "$SANDBOX/wf" 1
echo "local work" >> "$SANDBOX/wf/local.txt"
gitf -C "$SANDBOX/wf" add -A >/dev/null
gitf -C "$SANDBOX/wf" commit -qm "local commit that diverges" >/dev/null
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
run_cli "$SANDBOX/wf" update
assert_has "$OUT" "pull skipped:"
assert_lacks "$OUT" "no upstream / local changes"    # the old undifferentiated guess
finish

# The done message listed three MCP servers while the plugin shipped four.
reset_fakes; begin "setup lists the MCP servers from .mcp.json, not from memory"
new_sandbox "${ALL_TOOLS[@]}"
make_checkout "$SANDBOX/src" "2.43.0"
printf '{"mcpServers":{"alpha":{},"beta":{},"gamma":{},"delta":{}}}\n' \
  > "$SANDBOX/src/wellforge-plugin/.mcp.json"
gitf -C "$SANDBOX/src" add -A >/dev/null
gitf -C "$SANDBOX/src" commit -qm "four servers" >/dev/null
FAKE_CLAUDE_MARKETPLACES="wellforge" FAKE_CLAUDE_PLUGINS="wellforge@wellforge"
RUN_REPO="$SANDBOX/src"
run_cli "$SANDBOX/dest" setup
assert_has "$OUT" "alpha, beta, delta, gamma"
assert_lacks "$OUT" "sequential-thinking, playwright, github"
finish

# ── summary ───────────────────────────────────────────────────────────────────
# ── the marketplace SPELLING setup uses ────────────────────────────────────────────
# Registering the local checkout creates a `directory` marketplace that exists on one
# machine, so a teammate running the same setup gets a plugin nobody else can install —
# and doctor then WARNS about the thing setup just did. $SHIM_LOG already records every
# `claude` call, so the spelling is assertable without touching the shim.
reset_fakes; begin "setup registers the GIT marketplace, not the local checkout"
new_sandbox brew claude gh docker uvx uv npx node npm open curl mise git
run_cli "$SANDBOX/nowhere" setup
assert_file_has "$SHIM_LOG" "plugin marketplace add matteocodogno/wellforge"
assert_lacks "$(cat "$SHIM_LOG")" "plugin marketplace add $SANDBOX"
finish

reset_fakes; begin "WELLFORGE_MARKETPLACE overrides it, for a contributor's checkout"
new_sandbox brew claude gh docker uvx uv npx node npm open curl mise git
RUN_MARKETPLACE="$SANDBOX/checkout" run_cli "$SANDBOX/nowhere" setup
assert_file_has "$SHIM_LOG" "plugin marketplace add $SANDBOX/checkout"
finish

reset_fakes; begin "doctor points at the same spelling setup uses"
new_sandbox brew claude gh docker uvx uv npx node npm open curl mise git
run_cli "$SANDBOX/nowhere" doctor
assert_has "$OUT" "claude plugin marketplace add matteocodogno/wellforge"
finish

printf '\nwellforge CLI: %d passed, %d failed, %d expected-fail' "$pass" "$fail" "$xfail"
[ "$xpass" -gt 0 ] && printf ', %d UNEXPECTEDLY PASSING' "$xpass"
printf '\n'
# An xpass is not a failure of the CLI, but it IS a failure of this file to describe it.
[ "$fail" -eq 0 ] && [ "$xpass" -eq 0 ]
