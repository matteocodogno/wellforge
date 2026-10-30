#!/bin/bash
# wf-setup — install the per-project half of the WellForge Codex plugin.
#
#   install.sh [--hooks]      (run from anywhere inside the target git repository)
#
# A Codex plugin carries skills, MCP servers and hooks, but not custom agents, and a skill
# cannot find the plugin's install path the way a hook can. So what a WellForge command
# needs on disk is copied INTO the project from this skill's `project/` directory:
#
#   .codex/agents/wf-*.toml     the agent team (Codex reads custom agents from here)
#   .codex/wellforge/           the deterministic layer ($WF), the eval rubric, VERSION
#   AGENTS.md                   the WellForge block, between its markers; the rest is yours
#
# --hooks also installs the hooks into the project (.codex/hooks.json + .codex/wellforge/
# hooks/), for a Codex that does not run plugin hooks — they are documented for manually
# installed desktop plugins only. A project that already has them is kept current without
# the flag. When both are present, the plugin's hooks defer to the project's (run-hook.sh),
# so nothing runs twice.
#
# Idempotent: re-run after every plugin update. Commit what it writes.
set -euo pipefail

SKILL="$(cd "$(dirname "$0")/.." && pwd -P)"          # skills/wf-setup
PAYLOAD="$SKILL/project"
PKG="$(cd "$SKILL/../.." && pwd -P)"                   # the installed plugin root
RUNNER_REL=".codex/wellforge/hooks/run-hook.sh"

HOOKS=0
for a in "$@"; do
  case "$a" in
    --hooks) HOOKS=1 ;;
    *) echo "wf-setup: unknown option '$a' (usage: install.sh [--hooks])" >&2; exit 64 ;;
  esac
done

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "wf-setup: not inside a git repository — open the project in Codex and run \$wf-setup there" >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "wf-setup: python3 is required (the WellForge scripts run on it)" >&2
  exit 1
}
if [ ! -d "$PAYLOAD/.codex/agents" ] || [ ! -f "$PKG/hooks/run-hook.sh" ]; then
  echo "wf-setup: the plugin install at $PKG is incomplete — reinstall the WellForge plugin" >&2
  exit 1
fi

cd "$ROOT"
# Project hooks installed earlier are refreshed with everything else; left alone, their
# scripts would stay at the old release while the rest moved.
if [ -f .codex/hooks.json ] && grep -qF "$RUNNER_REL" .codex/hooks.json; then HOOKS=1; fi

mkdir -p .codex/agents .codex/wellforge
rm -f .codex/agents/wf-*.toml                  # wf- is ours; anything else in agents/ is not
cp "$PAYLOAD"/.codex/agents/wf-*.toml .codex/agents/
rm -rf .codex/wellforge/scripts .codex/wellforge/config
cp -R "$PAYLOAD/.codex/wellforge/." .codex/wellforge/

if [ "$HOOKS" -eq 1 ]; then
  rm -rf .codex/wellforge/hooks
  mkdir -p .codex/wellforge/hooks
  cp "$PKG/hooks/run-hook.sh" .codex/wellforge/hooks/
  cp -R "$PKG/hooks/scripts" .codex/wellforge/hooks/
  chmod +x .codex/wellforge/hooks/run-hook.sh .codex/wellforge/hooks/scripts/*.sh
fi

python3 - "$PAYLOAD" "$HOOKS" "$RUNNER_REL" <<'PY'
import json, os, re, sys

payload, hooks, runner = sys.argv[1], sys.argv[2] == "1", sys.argv[3]

# AGENTS.md: replace the block between the markers, keep everything else.
block = open(os.path.join(payload, "AGENTS.block.md")).read()
start, end = block.splitlines()[0], "<!-- wellforge-codex:end -->"
pat = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
existing = open("AGENTS.md").read() if os.path.exists("AGENTS.md") else ""
rest = pat.sub("", existing).rstrip("\n")
with open("AGENTS.md", "w") as f:
    f.write((rest + "\n\n" if rest else "") + block)

# hooks.json: the same rule as adapters/codex/generate.py — a handler is ours if it runs
# our runner; ours are replaced, every other entry is kept.
if hooks:
    path = os.path.join(".codex", "hooks.json")
    doc = json.load(open(path)) if os.path.exists(path) else {}
    ours = json.load(open(os.path.join(payload, "hooks.json")))
    doc.setdefault("description", ours["description"])
    events = doc.setdefault("hooks", {})
    for ev in list(events):
        kept = []
        for group in events[ev]:
            hs = [h for h in group.get("hooks", []) if runner not in h.get("command", "")]
            if hs:
                kept.append({**group, "hooks": hs})
        if kept:
            events[ev] = kept
        else:
            del events[ev]
    for ev, groups in ours["hooks"].items():
        events.setdefault(ev, []).extend(groups)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
PY

VERSION=$(cat .codex/wellforge/VERSION)
AGENTS=$(find .codex/agents -name 'wf-*.toml' | wc -l | tr -d ' ')
echo "✓ WellForge $VERSION set up in $ROOT"
echo "  $AGENTS agents in .codex/agents · scripts + rubric in .codex/wellforge · AGENTS.md block"
if [ "$HOOKS" -eq 1 ]; then
  echo "  project hooks in .codex/hooks.json — review and trust them with /hooks"
else
  echo "  hooks: the plugin's own — check /hooks lists them as trusted; if it does not list"
  echo "  them at all, re-run with --hooks"
fi
if [ -f .codex/wellforge/generated-skills.txt ]; then
  echo "  note: this project also has the per-project adapter's skills in .agents/skills"
  echo "  (listed in .codex/wellforge/generated-skills.txt) — remove them, or Codex shows"
  echo "  every WellForge skill twice"
fi
echo "  commit .codex/ and AGENTS.md so the team gets the same setup"
