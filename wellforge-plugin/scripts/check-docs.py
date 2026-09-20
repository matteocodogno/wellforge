#!/usr/bin/env python3
"""Docs drift guard — the plugin's README and CLAUDE.md must describe what ships.

Same idea as check-routing.py: the failure is silent (a command exists, nobody can find it),
so it needs a test rather than a convention. Reported 2026-09-20 with the README at 13/19
commands, 7/18 skills and one MCP server missing, and plugin.json one patch ahead of the
version CLAUDE.md quoted.

Checks:
  1. every commands/*.md appears in wellforge-plugin/README.md
  2. every skills/*/SKILL.md appears there too
  3. every server in .mcp.json appears there
  4. plugin.json's version == the version CLAUDE.md quotes
  5. every skill description is within the 1024-char limit the loader enforces
  6. cross-skill links are relative markdown links that resolve, not inert [[wiki-links]]

Run: wellforge-plugin/scripts/check-docs.py   (needs pyyaml)
"""
import glob
import json
import os
import re
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
ROOT = os.path.dirname(PLUGIN)
README = open(os.path.join(PLUGIN, "README.md")).read()
fail = []

cmds = sorted(os.path.basename(p)[:-3] for p in glob.glob(f"{PLUGIN}/commands/*.md"))
for c in cmds:
    if f"commands/{c}.md" not in README:
        fail.append(f"README does not list command `{c}`")

skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{PLUGIN}/skills/*/SKILL.md"))
for s in skills:
    if f"skills/{s}/" not in README:
        fail.append(f"README does not list skill `{s}`")

mcp = json.load(open(f"{PLUGIN}/.mcp.json"))
for server in mcp.get("mcpServers", mcp):
    if server not in README:
        fail.append(f"README does not list MCP server `{server}`")

pj = json.load(open(f"{PLUGIN}/.claude-plugin/plugin.json"))["version"]
quoted = re.search(r"plugin `([0-9]+\.[0-9]+\.[0-9]+)`", open(f"{ROOT}/CLAUDE.md").read())
if not quoted:
    fail.append("CLAUDE.md no longer quotes a plugin version — the sync check cannot run")
elif quoted.group(1) != pj:
    fail.append(f"plugin.json is {pj} but CLAUDE.md says {quoted.group(1)} — bump both in one commit")

for p in glob.glob(f"{PLUGIN}/skills/*/SKILL.md"):
    fm = yaml.safe_load(open(p).read().split("---\n", 2)[1])
    n = len(fm.get("description", ""))
    if n > 1024:
        fail.append(f"skill `{fm['name']}` description is {n} chars (limit 1024)")

# Cross-skill references are relative markdown links, so they resolve for a human on GitHub
# and in an editor — not `[[wiki-links]]`, which look like links and are inert everywhere.
# Both halves are checked: no wiki-links come back, and every relative link has a real file
# behind it (in this layout AND in the adapters', which mirror it).
for p in glob.glob(f"{PLUGIN}/**/*.md", recursive=True):
    body = open(p).read()
    for link in re.findall(r"\[\[([a-z0-9-]+)\]\]", body):
        fail.append(f"{os.path.relpath(p, ROOT)}: [[{link}]] is an inert wiki-link — "
                    f"use a relative markdown link instead")
    for target in re.findall(r"\]\((\.\./[^)]*\.md)\)", body):
        resolved = os.path.normpath(os.path.join(os.path.dirname(p), target))
        if not os.path.exists(resolved):
            fail.append(f"{os.path.relpath(p, ROOT)}: link -> {target} resolves to nothing")

if fail:
    print("✗ docs drift:")
    for f in fail:
        print(f"    {f}")
    sys.exit(1)
print(f"✓ docs consistent — {len(cmds)} commands, {len(skills)} skills, "
      f"{len(mcp.get('mcpServers', mcp))} MCP servers listed; version {pj} in sync")
