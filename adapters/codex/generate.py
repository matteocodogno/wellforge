#!/usr/bin/env python3
"""Generate a Codex adapter (.agents/skills, .codex/, AGENTS.md block) from the Claude Code plugin.

  generate.py [--plugin <wellforge-plugin>] --out <project-dir> [--provider openai]
  generate.py --package wellforge-codex-plugin --marketplace .agents/plugins/marketplace.json

`--out` writes everything into one project. `--package` writes the native Codex PLUGIN
instead — skills, MCP and hooks installed once; agents and the deterministic layer copied
into each project by its `$wf-setup` skill (see "the native Codex plugin package" below).

Option (b), like the OpenCode and Copilot adapters: the Claude Code plugin stays the source
of truth; this projects it onto OpenAI Codex (CLI and IDE extension share the same files).

What Codex offers, and where each plugin artifact lands:

  commands/*.md   → .agents/skills/wf-<cmd>/SKILL.md   Codex custom prompts are deprecated in
                                                       favour of skills, so a command becomes a
                                                       skill invoked as `$wf-spec …`, with
                                                       implicit invocation OFF (agents/openai.yaml)
                                                       — a command is something the user asks
                                                       for, never something Codex decides to run.
  agents/*.md     → .codex/agents/wf-<agent>.toml       Codex custom agents (parallel subagents).
  skills/         → .agents/skills/<name>/              SKILL.md is the shared format; copied.
  .mcp.json       → .codex/config.toml [mcp_servers]    inside a managed block.
  hooks/scripts   → .codex/hooks.json + .codex/wellforge/hooks/
                                                       Codex hooks follow the Claude contract, so
                                                       the plugin's own scripts run unchanged
                                                       behind adapters/codex/hooks/run-hook.sh.
  scripts/, config/ → .codex/wellforge/                 the deterministic layer (deterministic.py).
  (generated)     → AGENTS.md, managed block            the thin always-loaded guide.

Nothing the user owns is overwritten: .agents/skills is shared with other tools, so only the
directories this generator wrote last time are replaced; config.toml, hooks.json and AGENTS.md
are edited inside a marked block or by WellForge-owned entries only.

Run via: uv run --with pyyaml python adapters/codex/generate.py --out <dir>
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys
import tomllib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import deterministic  # noqa: E402  — adapters/deterministic.py, shared with the other adapters

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml (uv run --with pyyaml)")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT_REL = os.path.join(".codex", "wellforge")      # the deterministic layer + hooks + rubric
SKILLS_REL = os.path.join(".agents", "skills")
AGENTS_REL = os.path.join(".codex", "agents")
OWNED_LIST = os.path.join(ROOT_REL, "generated-skills.txt")

# Codex skill frontmatter limits (the Agent Skills format): exceeding them makes Codex skip
# the skill at load, which nothing in a generator summary would show.
NAME_MAX, DESC_MAX = 64, 1024

# Never copied: host litter would make the committed plugin package differ from CI's run.
_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")

# The hooks the runner wires, and the plugin scripts they need. notify and pre-compact-backup
# are deliberately absent — see the README's hook table for why.
HOOK_SCRIPTS = ("session-start", "pre-bash-guard", "pre-file-guard", "post-lint",
                "post-spec-guard", "stop-verify", "trace-subagent")

_AGENT_NAMES = []   # set in main(); lowercase agent ids (== filenames)


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def translate(s):
    """Map Claude Code refs onto the Codex adapter:
       /wellforge:x      -> $wf-x          (a command is now a skill, and `$` mentions one)
       wellforge:<agent> -> wf-<agent>     (dispatch refs → the custom agent's name)
       `<agent>`         -> `wf-<agent>`   (any still-bare backtick'd agent ref)"""
    s = s.replace("/wellforge:", "$wf-").replace("wellforge:", "wf-")
    bt = chr(96)
    for name in sorted(_AGENT_NAMES, key=len, reverse=True):   # longest first
        s = s.replace(f"{bt}{name}{bt}", f"{bt}wf-{name}{bt}")
    return s


_CMD_LINK = re.compile(r"\]\(((?:\.\./)+)commands/([a-z0-9-]+)\.md\)")


def relink_skill(s):
    """A skill linking to a COMMAND: `(../)^k commands/x.md` climbs k levels to the plugin
    root. Here the command is the skill `.agents/skills/wf-x/SKILL.md`, one level below the
    skills root rather than beside it — so one fewer `../`, then `wf-x/SKILL.md`."""
    return _CMD_LINK.sub(lambda m: f"]({m.group(1)[3:]}wf-{m.group(2)}/SKILL.md)", s)


def relink_command(s):
    """A command linking to a SKILL: `../skills/x/…` from `commands/`. The command is itself
    a skill now, a sibling of the one it links to."""
    return s.replace("](../skills/", "](../")


def toml_str(s):
    """A TOML string. Multi-line literal when the text allows it (readable in review, no
    escaping), else a basic string — JSON escapes are a subset of TOML's."""
    if "\n" in s and "'''" not in s and not s.endswith("'"):
        return "'''\n" + s + "'''"
    return json.dumps(s, ensure_ascii=False)


def rmtree_if(path):
    if os.path.isdir(path):
        shutil.rmtree(path)


# ── commands → explicit-only skills ──────────────────────────────────────────────────────

# Extra lines for commands whose procedure leans on a Claude Code mechanism Codex lacks.
# Kept here, next to the mapping that creates the gap, rather than edited into the plugin.
CODEX_NOTES = {
    "implement": "worktree",
    "orchestrate": "worktree",
}
_NOTE_TEXT = {
    "worktree": (
        "> **Codex:** dispatch a `wf-<role>` agent by asking Codex to spawn the custom agent of "
        "that name. Codex subagents share this checkout — `isolation: \"worktree\"` is not a "
        "spawn option — so the worktree-isolation **Fallback** applies to every batch of ≥2 "
        "implementation agents: run them **sequentially** in the main tree and record the "
        "isolation mode as `sequential (codex: no worktree isolation)`. Read-only agents "
        "(security review, eval) may still run in parallel.\n"),
}


def gen_command_skills(plugin, skills_dir):
    names = []
    for fp in sorted(glob.glob(os.path.join(plugin, "commands", "*.md"))):
        text = open(fp).read()
        # Command frontmatter (argument-hint with [brackets]) isn't strict YAML; extract by
        # regex, as the OpenCode generator does.
        mm = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        fm_text, body = (mm.group(1), mm.group(2)) if mm else ("", text)
        cmd = os.path.splitext(os.path.basename(fp))[0]
        name = f"wf-{cmd}"
        dm = re.search(r"^description:\s*(.+)$", fm_text, re.M)
        hm = re.search(r"^argument-hint:\s*(.+)$", fm_text, re.M)
        hint = hm.group(1).strip() if hm else ""
        invoke = f"${name}" + (f" {hint}" if hint else "")
        desc = translate(" ".join(dm.group(1).split())) if dm else name
        desc = f"WellForge command — {desc}. Invoke explicitly: {invoke}"

        body = relink_command(translate(body))
        # `$ARGUMENTS` is Claude Code's substitution; Codex hands a skill the whole message
        # instead. Name the thing once, then refer to it by that name.
        body = body.replace("$ARGUMENTS", "ARGUMENTS")
        if deterministic.needs_repoint(body):
            body, k = deterministic.repoint(
                body, f'"$(git rev-parse --show-toplevel)/{ROOT_REL}"', "Codex")
            if not k:
                raise SystemExit(
                    f"{name}: references $WF but no plugin-root preamble was found to rewrite "
                    f"— the skill would resolve the root the Claude way. Fix the preamble in "
                    f"commands/{cmd}.md or the matcher in adapters/deterministic.py")
        head = (f"> WellForge command, generated for Codex from `wellforge-plugin/commands/"
                f"{cmd}.md` — do not edit; regenerate with `adapters/codex/generate.py`.\n"
                f"> Invoked as `{invoke}`. **ARGUMENTS** below means the text the user wrote "
                f"after `${name}` in the invoking message (empty if nothing).\n")
        if cmd in CODEX_NOTES:
            head += ">\n" + _NOTE_TEXT[CODEX_NOTES[cmd]]

        d = os.path.join(skills_dir, name)
        rmtree_if(d)
        os.makedirs(os.path.join(d, "agents"))
        write_skill(d, name, desc, head + "\n" + body)
        # Implicit invocation OFF: `$wf-release` tags and pushes, `$wf-orchestrate` spawns a
        # team. Codex matches a skill to a prompt by its description; a command must run
        # because someone asked for it by name, never because a sentence resembled it.
        with open(os.path.join(d, "agents", "openai.yaml"), "w") as f:
            f.write("# Generated by adapters/codex/generate.py — a WellForge command runs only\n"
                    "# when invoked by name.\n")
            yaml.safe_dump({"policy": {"allow_implicit_invocation": False}}, f, sort_keys=False)
        names.append(name)
    return names


def write_skill(d, name, desc, body):
    if len(name) > NAME_MAX or len(desc) > DESC_MAX:
        raise SystemExit(f"{name}: name {len(name)}/{NAME_MAX} or description "
                         f"{len(desc)}/{DESC_MAX} chars over the Codex skill limit — Codex "
                         f"would skip it at load")
    fm = yaml.safe_dump({"name": name, "description": desc}, sort_keys=False,
                        width=10_000, allow_unicode=True).strip()
    with open(os.path.join(d, "SKILL.md"), "w") as f:
        f.write("---\n" + fm + "\n---\n" + body)


# ── skills ───────────────────────────────────────────────────────────────────────────────

def gen_skills(plugin, skills_dir):
    names = []
    for src in sorted(glob.glob(os.path.join(plugin, "skills", "*"))):
        if not os.path.isfile(os.path.join(src, "SKILL.md")):
            continue
        name = os.path.basename(src)
        dst = os.path.join(skills_dir, name)
        rmtree_if(dst)
        shutil.copytree(src, dst, ignore=_IGNORE)
        for root, _, files in os.walk(dst):
            for fn in files:
                if fn.endswith(".md"):
                    p = os.path.join(root, fn)
                    # Read first, then write: open(p, "w") as the argument of its own write
                    # truncates before the read (the bug that once emptied 44 skill files).
                    content = open(p).read()
                    open(p, "w").write(relink_skill(translate(content)))
        fm, _ = split_frontmatter(open(os.path.join(dst, "SKILL.md")).read())
        if len(fm.get("description") or "") > DESC_MAX:
            raise SystemExit(f"skills/{name}: description over {DESC_MAX} chars — Codex "
                             f"would skip it at load")
        names.append(name)
    return names


def prune_owned_skills(out, keep):
    """Remove skill dirs this generator wrote LAST time and is not writing now. Only those:
    .agents/skills is shared with every other tool that reads the Agent Skills layout."""
    lst = os.path.join(out, OWNED_LIST)
    if os.path.exists(lst):
        for name in open(lst).read().split():
            if name not in keep:
                rmtree_if(os.path.join(out, SKILLS_REL, name))
    os.makedirs(os.path.dirname(lst), exist_ok=True)
    with open(lst, "w") as f:
        f.write("\n".join(sorted(keep)) + "\n")


# ── agents → Codex custom agents ─────────────────────────────────────────────────────────

def tool_scope(tools):
    """Codex cannot narrow an agent's tools: a custom agent inherits the session's sandbox
    and approval policy, and it READS through the shell, so turning the shell off would
    blind it. A Claude allowlist therefore becomes an instruction, stated first."""
    if not tools:
        return ""
    low = {t.lower() for t in tools}
    shell, writes = "bash" in low, bool(low & {"write", "edit"})
    if shell and writes:
        return ""
    head = (f"## Tool scope (Codex)\n\nYour WellForge definition grants: {', '.join(tools)}. "
            "Codex cannot restrict tools per agent, so this is on you: ")
    if shell:   # e.g. owasp-reviewer — runs checks, changes nothing
        return head + "run commands to read, search and check, but **do not create, edit or " \
                      "delete files** and do not change git state.\n\n"
    return head + ("use the shell **only to read and search** (`cat`, `rg`, `ls`, "
                   "`git log/diff/show`). Do not build, install, run tests, or change git state"
                   + (", and write only the artifact your task names" if writes
                      else ", and do not write files") + ".\n\n")


def gen_agents(plugin, out, models, efforts):
    d = os.path.join(out, AGENTS_REL)
    os.makedirs(d, exist_ok=True)
    for old in glob.glob(os.path.join(d, "wf-*.toml")):
        os.remove(old)                      # wf- is ours; anything else in agents/ is not
    n = 0
    for fp in sorted(glob.glob(os.path.join(plugin, "agents", "*.md"))):
        fm, body = split_frontmatter(open(fp).read())
        agent = fm.get("name") or os.path.splitext(os.path.basename(fp))[0]
        tier = models.get(agent, models["_default"])
        desc = translate(" ".join((fm.get("description") or "").split()))
        if fm.get("disallowedTools"):
            print(f"note: {agent}: disallowedTools {fm['disallowedTools']} not representable "
                  f"in Codex — relying on the agent prompt", file=sys.stderr)
        instructions = tool_scope(fm.get("tools")) + translate(body).strip() + "\n"
        text = (f"# Generated from wellforge-plugin/agents/{agent}.md by "
                f"adapters/codex/generate.py — do not edit; regenerate.\n"
                f"name = {toml_str('wf-' + agent)}\n"
                f"description = {toml_str(desc)}\n"
                f"model = {toml_str(tier[0])}\n"
                f"model_reasoning_effort = {toml_str(tier[1])}\n"
                f"developer_instructions = {toml_str(instructions)}\n")
        tomllib.loads(text)                 # fail here, not in someone's Codex session
        with open(os.path.join(d, f"wf-{agent}.toml"), "w") as f:
            f.write(text)
        n += 1
    return n


# ── MCP → config.toml managed block ──────────────────────────────────────────────────────

BLOCK_START = "# >>> wellforge (generated by adapters/codex/generate.py — regenerate, don't edit) >>>"
BLOCK_END = "# <<< wellforge <<<"
_BLOCK = re.compile(re.escape(BLOCK_START) + r".*?" + re.escape(BLOCK_END) + r"\n?", re.S)


def gen_mcp(plugin, out):
    src = os.path.join(plugin, ".mcp.json")
    if not os.path.exists(src):
        return 0
    servers = json.load(open(src)).get("mcpServers", {})
    cfg = os.path.join(out, ".codex", "config.toml")
    os.makedirs(os.path.dirname(cfg), exist_ok=True)
    existing = open(cfg).read() if os.path.exists(cfg) else ""
    user_part = _BLOCK.sub("", existing)
    try:
        user_servers = tomllib.loads(user_part).get("mcp_servers", {})
    except tomllib.TOMLDecodeError as e:
        raise SystemExit(f".codex/config.toml is not valid TOML outside the WellForge block "
                         f"({e}) — fix it first; refusing to edit a file I cannot parse")

    lines = [BLOCK_START]
    n = 0
    for name, c in servers.items():
        if name in user_servers:
            print(f"note: mcp_servers.{name} already defined in .codex/config.toml — "
                  f"keeping yours", file=sys.stderr)
            continue
        lines.append(f"[mcp_servers.{name}]")
        if c.get("type") == "http" or c.get("url"):
            # Streamable HTTP. Authenticate once with `codex mcp login <name>` (OAuth) — no
            # token in a committed file.
            lines.append(f"url = {json.dumps(c['url'])}")
        else:
            lines.append(f"command = {json.dumps(c.get('command', 'npx'))}")
            lines.append(f"args = {json.dumps(c.get('args', []))}")
        lines.append("")
        n += 1
    lines.append(BLOCK_END)
    block = "\n".join(lines) + "\n"
    # Appended at the END: a table header in our block must not capture the user's
    # top-level keys, and everything after the last header belongs to it.
    new = user_part.rstrip("\n") + ("\n\n" if user_part.strip() else "") + block
    tomllib.loads(new)
    with open(cfg, "w") as f:
        f.write(new)
    return n


# ── hooks ────────────────────────────────────────────────────────────────────────────────

HOOKS_DESC = "WellForge hooks (generated by adapters/codex/generate.py)"
RUNNER_REL = f"{ROOT_REL}/hooks/run-hook.sh"


def project_cmd(hook):
    # Codex runs a hook in the session cwd, which can be a subdirectory — resolve the root.
    return f'bash "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/{RUNNER_REL}" {hook}'


def plugin_cmd(hook):
    # Codex sets PLUGIN_ROOT (the installed package) for a plugin's hook commands.
    return f'bash "${{PLUGIN_ROOT}}/hooks/run-hook.sh" {hook}'


def wf_hooks(cmd):
    def h(hook, **kw):
        return {"type": "command", "command": cmd(hook), **kw}
    return {
        "SessionStart": [{"hooks": [h("session-start")]}],
        "PreToolUse": [
            {"matcher": "^Bash$", "hooks": [h("pre-bash-guard")]},
            {"matcher": "^apply_patch$", "hooks": [h("pre-file-guard")]},
        ],
        "PostToolUse": [
            {"matcher": "^apply_patch$", "hooks": [h("post-lint"), h("post-spec-guard")]},
        ],
        "Stop": [{"hooks": [h("stop-verify", timeout=300)]}],
        # Only WellForge's own agents; Codex's built-in explorer/worker are not pipeline stages.
        "SubagentStop": [{"matcher": "^wf-", "hooks": [h("trace-subagent")]}],
    }


def ship_hook_scripts(plugin, hd):
    """The plugin's scripts, unchanged, plus the runner that feeds them a Codex payload."""
    rmtree_if(hd)
    os.makedirs(os.path.join(hd, "scripts"))
    for h in HOOK_SCRIPTS:
        dst = os.path.join(hd, "scripts", f"{h}.sh")
        shutil.copyfile(os.path.join(plugin, "hooks", "scripts", f"{h}.sh"), dst)
        os.chmod(dst, 0o755)
    runner = os.path.join(hd, "run-hook.sh")
    shutil.copyfile(os.path.join(HERE, "hooks", "run-hook.sh"), runner)
    os.chmod(runner, 0o755)


def dump_json(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def gen_hooks(plugin, out):
    ship_hook_scripts(plugin, os.path.join(out, ROOT_REL, "hooks"))
    # hooks.json: keep every entry that is not ours, replace ours. Ours = any handler whose
    # command runs our runner — identified by what it does, not by a position in the file.
    # wf-setup's install.sh applies the same rule when it installs project hooks.
    path = os.path.join(out, ".codex", "hooks.json")
    doc = json.load(open(path)) if os.path.exists(path) else {}
    doc.setdefault("description", HOOKS_DESC)
    events = doc.setdefault("hooks", {})
    for ev in list(events):
        kept = []
        for group in events[ev]:
            hs = [h for h in group.get("hooks", []) if RUNNER_REL not in h.get("command", "")]
            if hs:
                kept.append({**group, "hooks": hs})
        if kept:
            events[ev] = kept
        else:
            del events[ev]
    for ev, groups in wf_hooks(project_cmd).items():
        events.setdefault(ev, []).extend(groups)
    dump_json(path, doc)
    return len(HOOK_SCRIPTS)


# ── AGENTS.md managed block ──────────────────────────────────────────────────────────────

GUIDE_START = "<!-- wellforge-codex:start — generated by adapters/codex/generate.py; regenerate, don't edit -->"
GUIDE_END = "<!-- wellforge-codex:end -->"
_GUIDE = re.compile(re.escape(GUIDE_START) + r".*?" + re.escape(GUIDE_END) + r"\n?", re.S)


def guide_text(commands, agents, mode):
    """The always-loaded part. Kept small on purpose: every line here is paid for in every
    Codex session, and the skills already load on demand. `mode` is where the skills and
    hooks come from: files in this project, or the WellForge Codex plugin."""
    agent_list = ", ".join(f"`wf-{a}`" for a in agents)
    if mode == "plugin":
        source = "from the WellForge Codex plugin"
        agents_from = "installed by `$wf-setup`"
        hooks_from = ("from the plugin, or `.codex/hooks.json` after `$wf-setup --hooks`; "
                      "trust them once via `/hooks`")
        owned = ("`.codex/wellforge/` and `.codex/agents/wf-*` are installed by `$wf-setup` — "
                 "re-run it after a plugin update, never edit them here.")
    else:
        source = "in `.agents/skills/`"
        agents_from = "in `.codex/agents/`"
        hooks_from = "`.codex/hooks.json`, trust them once via `/hooks`"
        owned = ("WellForge files under `.codex/wellforge/`, `.codex/agents/wf-*` and "
                 "`.agents/skills/` are generated — change the plugin and regenerate, never "
                 "edit them here.")
    return f"""{GUIDE_START}
## WellForge (Codex)

This project uses the WellForge spec-driven workflow: **spec → plan → tasks → implement →
QE → eval**, under `specs/NNN-slug/`. The `spec-driven` and `rigor-tiers` skills are the
authority; load them before touching a spec or a task list.

- **Commands are skills {source}, invoked by name only:** `$wf-status` (where every
  feature stands), `$wf-spec`, `$wf-plan`, `$wf-tasks`, `$wf-implement`, `$wf-orchestrate`,
  `$wf-done`, `$wf-doctor` — {len(commands)} in all, `/skills` lists them. A WellForge text
  that says `/wellforge:x` means `$wf-x`.
- **Agents** are Codex custom agents {agents_from}: {agent_list}. To dispatch one, spawn the
  custom agent of that name. Subagents share this checkout, so a batch of ≥2 implementation
  agents runs **sequentially** (worktree-isolation Fallback).
- **Enforced by hooks** ({hooks_from}): destructive shell commands and secret files are
  refused, spec drift blocks the end of a turn, and a spec's `status: done` / `rigor:` can
  only be set through `$wf-done` / `$wf-promote`. CI quality gates are the durable half; a
  red gate is never fixed by lowering a threshold.
- {owned}
{GUIDE_END}
"""


def write_guide(out, text):
    path = os.path.join(out, "AGENTS.md")
    existing = open(path).read() if os.path.exists(path) else ""
    rest = _GUIDE.sub("", existing).rstrip("\n")
    with open(path, "w") as f:
        f.write((rest + "\n\n" if rest else "") + text)


# ── misc ─────────────────────────────────────────────────────────────────────────────────

def gen_rubric(plugin, out):
    """The evaluator's last-resort rubric path: a scaffold has no gates/ on disk, and here
    there is no plugin install to fall back on either."""
    src = os.path.join(plugin, "config", "eval-rubric.yml")
    if not os.path.exists(src):
        return 0
    dst = os.path.join(out, ROOT_REL, "eval-rubric.yml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    return 1


def write_version(out, version):
    """Which plugin release produced the per-project files. The plugin's SessionStart hook
    compares it with its own, so a project left behind by a plugin update says so."""
    with open(os.path.join(out, ROOT_REL, "VERSION"), "w") as f:
        f.write(version + "\n")


def assert_nonempty(roots, label):
    """Count is not content — see the OpenCode generator for the 44 empty skill files."""
    empties = []
    for root in roots:
        empties += [p for p in glob.glob(os.path.join(root, "**", "*"), recursive=True)
                    if os.path.isfile(p) and os.path.getsize(p) == 0]
    if empties:
        raise SystemExit(f"FATAL: {label} emitted {len(empties)} EMPTY file(s), e.g. "
                         f"{empties[0]} — refusing to ship a blank library")


# ── the native Codex plugin package ──────────────────────────────────────────────────────
#
# One install instead of files in every project. A Codex plugin carries skills, MCP servers
# and hooks — NOT custom agents, and a skill cannot resolve the plugin's install path the way
# a hook can (PLUGIN_ROOT). So the package splits in two:
#
#   in the plugin  skills (commands + skills), mcp.json, hooks/        — installed once
#   per project    .codex/agents/wf-*.toml, .codex/wellforge/ (the deterministic layer,
#                  the rubric), the AGENTS.md block                   — `$wf-setup` copies
#                  them in from skills/wf-setup/project/, which is also the plugin's
#                  onboarding skill. $WF therefore resolves exactly as in the per-project
#                  adapter, and the command skills are byte-identical in both.
#
# The package is COMMITTED (a marketplace installs it from git) and is generated: CI
# regenerates it and fails on any difference (scripts/tests/codex-plugin.test.py).

PKG_DIR = "wellforge-codex-plugin"
MARKETPLACE = os.path.join(".agents", "plugins", "marketplace.json")
SETUP = "wf-setup"
SETUP_SRC = os.path.join(HERE, "plugin", SETUP)       # hand-written: SKILL.md, install.sh


def portable_mcp(plugin):
    servers = json.load(open(os.path.join(plugin, ".mcp.json"))).get("mcpServers", {})
    out = {}
    for name, c in servers.items():
        if c.get("type") == "http" or c.get("url"):
            # Authenticate with `codex mcp login <name>` (OAuth) — no secret in a manifest.
            out[name] = {"type": "streamable-http", "url": c["url"]}
        else:
            out[name] = {"type": "stdio", "command": c.get("command", "npx"),
                         "args": c.get("args", [])}
    return {"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
            "mcpServers": out}


def gen_package(plugin, pkg, models, effort, meta):
    rmtree_if(pkg)
    skills_dir = os.path.join(pkg, "skills")
    os.makedirs(skills_dir)
    cmds = gen_command_skills(plugin, skills_dir)
    skills = gen_skills(plugin, skills_dir)
    if SETUP in cmds or SETUP in skills:
        raise SystemExit(f"{SETUP}: a plugin command or skill now has this name — rename one")

    setup = os.path.join(skills_dir, SETUP)
    shutil.copytree(SETUP_SRC, setup, ignore=_IGNORE)
    os.chmod(os.path.join(setup, "scripts", "install.sh"), 0o755)
    payload = os.path.join(setup, "project")
    a = gen_agents(plugin, payload, models, effort)
    deterministic.ship(plugin, payload, ROOT_REL)
    gen_rubric(plugin, payload)
    write_version(payload, meta["version"])
    # `$wf-setup --hooks` only: the hooks.json entries for a project that cannot run the
    # plugin's own hooks. The scripts it points at are copied from ../../hooks at install.
    dump_json(os.path.join(payload, "hooks.json"),
              {"description": HOOKS_DESC, "hooks": wf_hooks(project_cmd)})
    with open(os.path.join(payload, "AGENTS.block.md"), "w") as f:
        f.write(guide_text(cmds, _AGENT_NAMES, "plugin"))

    ship_hook_scripts(plugin, os.path.join(pkg, "hooks"))
    dump_json(os.path.join(pkg, "hooks", "hooks.json"),
              {"description": HOOKS_DESC, "hooks": wf_hooks(plugin_cmd)})
    dump_json(os.path.join(pkg, "mcp.json"), portable_mcp(plugin))

    repo = "https://github.com/matteocodogno/wellforge"
    dump_json(os.path.join(pkg, "plugin.json"), {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": meta["name"],
        "version": meta["version"],
        "description": meta["description"],
        "author": meta.get("author", {"name": "WellForge"}),
        "homepage": repo,
        "repository": repo,
        "license": meta.get("license", "MIT"),
        "keywords": meta.get("keywords", []) + ["codex"],
        "extensions": {"com.openai": {
            "hooks": "./hooks/hooks.json",
            "onboardingSkill": f"./skills/{SETUP}/SKILL.md",
            "interface": {
                "displayName": "WellForge",
                "shortDescription": "Spec-driven workflow, a role-based agent team and "
                                    "enforced quality gates for Codex.",
                "developerName": "WellForge",
                "category": "Coding",
                "websiteURL": repo,
            },
        }},
    })
    with open(os.path.join(pkg, "README.md"), "w") as f:
        f.write(f"""# WellForge — Codex plugin {meta['version']}

**Generated** by `adapters/codex/generate.py --package` from `wellforge-plugin/` — do not
edit; change the plugin and regenerate. CI fails if this tree differs from a fresh run.

Install, then run `$wf-setup` once in each project (agents, scripts, AGENTS.md block):

```bash
codex plugin marketplace add matteocodogno/wellforge --ref plugin-v{meta['version']}
```

See [`adapters/codex/README.md`](../adapters/codex/README.md) for what is covered and what
is not.
""")
    assert_nonempty([pkg], "codex plugin package")
    return a, cmds, skills


def gen_marketplace(path):
    dump_json(path, {
        "name": "wellforge",
        "interface": {"displayName": "WellForge"},
        "plugins": [{
            "name": "wellforge",
            # Local to the marketplace root: the version is the ref the marketplace was
            # added at (`--ref plugin-vX.Y.Z`), so this file never names a tag that the
            # commit carrying it cannot yet have.
            "source": {"source": "local", "path": f"./{PKG_DIR}"},
            "policy": {"installation": "AVAILABLE"},
            "category": "Coding",
        }],
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", default=os.path.join(HERE, "..", "..", "wellforge-plugin"))
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--out", help="target project dir (per-project adapter)")
    mode.add_argument("--package", help="write the native Codex plugin package to this dir")
    ap.add_argument("--marketplace", help="with --package: also write this marketplace.json")
    ap.add_argument("--provider", default="openai")
    args = ap.parse_args()

    cfg = os.path.join(args.plugin, "config")
    routing = yaml.safe_load(open(os.path.join(cfg, "model-routing.yml")))
    tiers_doc = yaml.safe_load(open(os.path.join(cfg, "model-tiers.yml")))
    tiers_all = tiers_doc["tools"]["codex"]
    if args.provider not in tiers_all:
        sys.exit(f"provider '{args.provider}' not in codex tiers (have: {', '.join(tiers_all)})")
    tiers = tiers_all[args.provider]
    effort = tiers_doc.get("reasoning_effort", {}).get("codex", {})
    resolve = lambda t: (tiers[t], effort.get(t, "medium"))   # noqa: E731
    models = {a: resolve(s["tier"]) for a, s in routing["agents"].items()}
    models["_default"] = resolve("mid")
    meta = json.load(open(os.path.join(args.plugin, ".claude-plugin", "plugin.json")))

    _AGENT_NAMES[:] = sorted(os.path.splitext(os.path.basename(f))[0]
                             for f in glob.glob(os.path.join(args.plugin, "agents", "*.md")))

    if args.package:
        a, cmds, skills = gen_package(args.plugin, args.package, models, effort, meta)
        if args.marketplace:
            gen_marketplace(args.marketplace)
        print(f"✓ Codex plugin package {meta['version']} ({args.provider}) → {args.package}")
        print(f"  {len(cmds)} command skills + {SETUP} · {len(skills)} skills · "
              f"{len(HOOK_SCRIPTS)} hooks · {a} agents (installed per project by ${SETUP})")
        return 0

    gen_rubric(args.plugin, args.out)
    deterministic.ship(args.plugin, args.out, ROOT_REL)
    write_version(args.out, meta["version"])
    a = gen_agents(args.plugin, args.out, models, effort)
    skills_dir = os.path.join(args.out, SKILLS_REL)
    cmds = gen_command_skills(args.plugin, skills_dir)
    skills = gen_skills(args.plugin, skills_dir)
    prune_owned_skills(args.out, set(cmds) | set(skills))
    m = gen_mcp(args.plugin, args.out)
    h = gen_hooks(args.plugin, args.out)
    write_guide(args.out, guide_text(cmds, _AGENT_NAMES, "project"))
    assert_nonempty([os.path.join(args.out, ROOT_REL), os.path.join(args.out, AGENTS_REL)]
                    + [os.path.join(skills_dir, n) for n in cmds + skills],
                    "codex adapter")

    print(f"✓ Codex adapter ({args.provider}) → {args.out}")
    print(f"  {a} agents · {len(cmds)} command skills · {len(skills)} skills · "
          f"{m} MCP servers · {h} hooks (Claude scripts, unchanged)")
    print("  next, in Codex: trust the project, then review + trust the hooks with /hooks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
