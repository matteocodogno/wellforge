#!/usr/bin/env python3
"""Generate an OpenCode adapter (.opencode/ + opencode.json) from the Claude Code plugin.

  generate.py --plugin <wellforge-plugin> --out <project-dir> [--provider anthropic]

Reads the plugin's agents/commands/skills + config/model-{routing,tiers}.yml and emits
OpenCode-native files for the chosen provider. Option (b): the Claude Code plugin stays the
source of truth; this projects it onto OpenCode. Hooks are NOT generated here — OpenCode
hooks are TS plugins (a separate follow-up); enforcement on OpenCode leans on CI gates.

Run via: uv run --with pyyaml python adapters/opencode/generate.py ...
"""
import argparse
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml (uv run --with pyyaml)")

# Claude tool name -> OpenCode permission key. Agents with NO tools: list get full access.
_TOOL2PERM = {"read": "read", "grep": "grep", "glob": "glob", "write": "edit",
              "edit": "edit", "bash": "bash", "webfetch": "webfetch", "websearch": "websearch"}
_ALL_ALLOW = {k: "allow" for k in ["read", "edit", "bash", "grep", "glob", "list",
                                    "webfetch", "task"]}


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def opencode_text(s):
    """Translate Claude Code command refs to OpenCode (unnamespaced): /wellforge:x -> /x."""
    return s.replace("/wellforge:", "/")


def perms_for(tools):
    if not tools:                       # no tools: list -> full access (dev/devops/QE)
        return dict(_ALL_ALLOW)
    granted = {_TOOL2PERM[t.lower()] for t in tools if t.lower() in _TOOL2PERM}
    perm = {"read": "deny", "edit": "deny", "bash": "deny", "grep": "deny",
            "glob": "deny", "list": "deny", "webfetch": "allow", "task": "deny"}
    for g in granted:
        perm[g] = "allow"
    if perm["glob"] == "allow":
        perm["list"] = "allow"
    return perm


def gen_agents(plugin, out, models):
    d = os.path.join(out, ".opencode", "agents")
    os.makedirs(d, exist_ok=True)
    n = 0
    for fp in sorted(__import__("glob").glob(os.path.join(plugin, "agents", "*.md"))):
        fm, body = split_frontmatter(open(fp).read())
        name = fm.get("name") or os.path.splitext(os.path.basename(fp))[0]
        desc = opencode_text(" ".join((fm.get("description") or "").split()))
        fmt = {"description": desc, "mode": "subagent",
               "model": models.get(name, models["_default"]),
               "permission": perms_for(fm.get("tools"))}
        with open(os.path.join(d, f"{name}.md"), "w") as f:
            f.write("---\n" + yaml.safe_dump(fmt, sort_keys=False).strip() + "\n---\n")
            f.write(opencode_text(body))
        n += 1
    return n


def gen_commands(plugin, out):
    # Command frontmatter (argument-hint with [brackets]/dashes) isn't strict YAML, and we
    # only need `description` — extract it by regex rather than parsing the whole block.
    d = os.path.join(out, ".opencode", "commands")
    os.makedirs(d, exist_ok=True)
    n = 0
    for fp in sorted(__import__("glob").glob(os.path.join(plugin, "commands", "*.md"))):
        text = open(fp).read()
        mm = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        fm_text, body = (mm.group(1), mm.group(2)) if mm else ("", text)
        name = os.path.splitext(os.path.basename(fp))[0]
        dm = re.search(r"^description:\s*(.+)$", fm_text, re.M)
        desc = opencode_text(" ".join(dm.group(1).split())) if dm else name
        fmt = yaml.safe_dump({"description": desc}, sort_keys=False, default_flow_style=False).strip()
        with open(os.path.join(d, f"{name}.md"), "w") as f:
            f.write("---\n" + fmt + "\n---\n" + opencode_text(body))
        n += 1
    return n


def gen_skills(plugin, out):
    src, dst = os.path.join(plugin, "skills"), os.path.join(out, ".opencode", "skills")
    if not os.path.isdir(src):
        return 0
    if os.path.isdir(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    # translate command refs inside skill markdown
    n = 0
    for root, _, files in os.walk(dst):
        for fn in files:
            if fn.endswith(".md"):
                p = os.path.join(root, fn)
                open(p, "w").write(opencode_text(open(p).read()))
                n += 1
    return n


def gen_mcp(plugin, out):
    import json
    src = os.path.join(plugin, ".mcp.json")
    if not os.path.exists(src):
        return 0
    servers = json.load(open(src)).get("mcpServers", {})
    mcp = {}
    for name, cfg in servers.items():
        if cfg.get("type") == "http" or cfg.get("url"):
            mcp[name] = {"type": "remote", "url": cfg.get("url"), "enabled": True}
        else:
            mcp[name] = {"type": "local",
                         "command": [cfg.get("command", "npx"), *cfg.get("args", [])],
                         "enabled": True}
    out_cfg = os.path.join(out, "opencode.json")
    existing = json.load(open(out_cfg)) if os.path.exists(out_cfg) else {}
    existing.setdefault("$schema", "https://opencode.ai/config.json")
    existing["mcp"] = mcp
    json.dump(existing, open(out_cfg, "w"), indent=2)
    return len(mcp)


def gen_plugin(out):
    # Copy the static enforcement plugin (bash guard, post-lint, spec-drift) into place.
    src = os.path.join(os.path.dirname(__file__), "plugin", "wellforge.js")
    if not os.path.exists(src):
        return 0
    d = os.path.join(out, ".opencode", "plugins")
    os.makedirs(d, exist_ok=True)
    shutil.copy(src, os.path.join(d, "wellforge.js"))
    return 1


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(__file__)
    ap.add_argument("--plugin", default=os.path.join(here, "..", "..", "wellforge-plugin"))
    ap.add_argument("--out", required=True, help="target project dir (.opencode/ written here)")
    ap.add_argument("--provider", default="anthropic")
    args = ap.parse_args()

    cfg = os.path.join(args.plugin, "config")
    routing = yaml.safe_load(open(os.path.join(cfg, "model-routing.yml")))
    tiers_all = yaml.safe_load(open(os.path.join(cfg, "model-tiers.yml")))["tools"]["opencode"]
    if args.provider not in tiers_all:
        sys.exit(f"provider '{args.provider}' not in opencode tiers (have: {', '.join(tiers_all)})")
    tiers = tiers_all[args.provider]
    models = {a: tiers[s["tier"]] for a, s in routing["agents"].items()}
    models["_default"] = tiers["mid"]   # unlisted agents (e.g. designer) → mid

    a = gen_agents(args.plugin, args.out, models)
    c = gen_commands(args.plugin, args.out)
    s = gen_skills(args.plugin, args.out)
    m = gen_mcp(args.plugin, args.out)
    p = gen_plugin(args.out)
    print(f"✓ OpenCode adapter ({args.provider}) → {args.out}/.opencode/")
    print(f"  {a} agents · {c} commands · {s} skill files · {m} MCP servers · {p} enforcement plugin")
    print("  enforcement plugin ports: bash guard, post-lint, spec-drift (session.idle).")
    print("  NOT ported: token-trace observability (no OpenCode subagent-usage event) —")
    print("  that gap is covered by the CI quality gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
