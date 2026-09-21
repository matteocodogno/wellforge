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
  4. plugin.json's version == the version CLAUDE.md quotes, the version the marketplace
     entry publishes, AND the plugin tag its `ref` pins — three files naming one release
  5. every skill description is within the 1024-char limit the loader enforces
  6. cross-skill links are relative markdown links that resolve, not inert [[wiki-links]]
  7. the status/rigor enums in config/spec-frontmatter.schema.json match the spec-driven
     and rigor-tiers skills — the skills stay the human-readable authority, the schema is
     the machine-readable mirror, and a mirror that drifts is worse than no mirror

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

# The marketplace entry is what a NEW teammate installs. It carries the version twice (an
# explicit `version`, and the `ref` tag its git-subdir source is pinned to), so there are two
# more ways for one release to disagree with itself — and the symptom is a teammate silently
# installing a different plugin than the repo describes.
mkt = json.load(open(f"{ROOT}/.claude-plugin/marketplace.json"))
entry = next((e for e in mkt["plugins"] if e["name"] == "wellforge"), None)
if entry is None:
    fail.append("marketplace.json has no `wellforge` plugin entry")
else:
    if entry.get("version") != pj:
        fail.append(f"marketplace.json publishes version {entry.get('version')} but "
                    f"plugin.json is {pj} — bump both in one commit")
    src = entry.get("source")
    if not isinstance(src, dict):
        fail.append(f"marketplace.json source is {src!r}, not a git source — a local path "
                    f"installs for nobody but the machine holding it")
    else:
        want_ref = f"plugin-v{pj}"
        if src.get("ref") != want_ref:
            fail.append(f"marketplace.json pins ref {src.get('ref')!r} but plugin.json is "
                        f"{pj} — the release commit must pin {want_ref!r}")
        if src.get("path") != "wellforge-plugin":
            fail.append(f"marketplace.json source path is {src.get('path')!r}, expected "
                        f"'wellforge-plugin'")

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

# ── 7. schema mirrors the skills ────────────────────────────────────────────────
# The skill is the authority; the schema must say the same thing. Edited apart, the machine
# would accept a status the documentation forbids (or refuse one it blesses), and every
# consumer of forge-state.py would inherit the discrepancy silently.
schema_path = f"{PLUGIN}/config/spec-frontmatter.schema.json"
if os.path.exists(schema_path):
    schema = json.load(open(schema_path))
    sd = open(f"{PLUGIN}/skills/spec-driven/SKILL.md").read()
    rt = open(f"{PLUGIN}/skills/rigor-tiers/SKILL.md").read()

    statuses = schema["$defs"]["status"]["enum"]
    # The lifecycle diagram in spec-driven is the source: every status must appear in it.
    # Pick the fenced block BY CONTENT — the first fence in the file is not the diagram,
    # and an index-based grab silently checks the wrong text.
    fences = sd.split("```")[1::2]
    diagram = next((f for f in fences if "draft" in f and "in-progress" in f), sd)
    for s in statuses:
        if s not in diagram:
            fail.append(f"schema status `{s}` is absent from the spec-driven lifecycle diagram")
    for s in ("draft", "approved", "in-progress", "done", "superseded", "archived"):
        if s not in statuses:
            fail.append(f"spec-driven documents status `{s}` but the schema's enum omits it")

    tiers = schema["$defs"]["rigor"]["enum"]
    for t in ("spike", "mvp", "production"):
        if t not in tiers:
            fail.append(f"rigor-tiers documents tier `{t}` but the schema's enum omits it")
        if f"`{t}`" not in rt:
            fail.append(f"schema tier `{t}` is not documented in the rigor-tiers skill")

# ── the run-trace schema version, stated in one place and quoted in many ────────────
# Four documents named a version and three were stale: implement/spike/orchestrate still
# said v2 and the evaluator said v1, while the observability skill — the authority — was
# already on v3. A producer writing `"schema": "wellforge-run/v2"` is not a cosmetic
# mismatch: the trace it writes claims to be a schema it is not, and a reader that one day
# drops v2 would drop live traces.
#
# The skill's heading is the single source. Everything else must agree, except the two
# places that legitimately name OLD versions: run-report.py's ACCEPTED_SCHEMAS (a reader
# must keep accepting the archive) and the migration notes (history).
_obs_path = os.path.join(PLUGIN, "skills", "observability", "SKILL.md")
_obs = open(_obs_path, encoding="utf-8").read()
_m = re.search(r"^## Semantic run trace — schema `(wellforge-run/v\d+)`", _obs, re.M)
if not _m:
    fail.append("observability/SKILL.md has no `## Semantic run trace — schema `wellforge-run/vN`` "
                "heading — the schema version has no single source")
else:
    current = _m.group(1)
    _EXEMPT = (
        os.path.join(PLUGIN, "scripts", "run-report.py"),      # must accept every old version
        os.path.join(PLUGIN, "scripts", "check-docs.py"),      # this check itself
    )
    for dirpath, dirnames, filenames in os.walk(PLUGIN):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "tests")]
        for fn in filenames:
            if not fn.endswith((".md", ".py", ".json", ".sh")):
                continue
            fp = os.path.join(dirpath, fn)
            if fp in _EXEMPT:
                continue
            try:
                body = open(fp, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for lineno, line in enumerate(body.splitlines(), 1):
                for found in re.findall(r"wellforge-run/v\d+", line):
                    if found != current:
                        rel = os.path.relpath(fp, ROOT)
                        fail.append(f"{rel}:{lineno} names `{found}` but the observability "
                                    f"skill's current schema is `{current}`")

# ── gates/README.md's pin numbers vs the workflows that actually pin them ───────────
# The README is where a human looks up what the gates run. It said osv-scanner v2.0.0 and
# semgrep 1.172.0 while the workflows pinned v2.5.1 and 1.173.0 — numbers that had drifted
# behind the thing they describe, which is the same failure class as the plugin version
# living in four files. A wrong pin in the README is worse than no pin: it is the number
# someone copies into a new gate.
_WORKFLOWS = os.path.join(ROOT, ".github", "workflows")
_readme_path = os.path.join(ROOT, "gates", "README.md")
if os.path.exists(_readme_path) and os.path.isdir(_WORKFLOWS):
    _readme = open(_readme_path, encoding="utf-8").read()
    _env = {}
    for wf in ("quality-node.yml", "quality-jvm.yml"):
        p = os.path.join(_WORKFLOWS, wf)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            m = re.match(r"\s*(SEMGREP_VERSION|OSV_SCANNER_VERSION):\s*(\S+)\s*$", line)
            if m:
                _env.setdefault(m.group(1), set()).add(m.group(2))

    for var, label in (("SEMGREP_VERSION", "semgrep"), ("OSV_SCANNER_VERSION", "osv-scanner")):
        vals = _env.get(var)
        if not vals:
            continue
        if len(vals) > 1:
            fail.append(f"the gate workflows pin different {label} versions: {sorted(vals)}")
            continue
        pinned = next(iter(vals))
        bare = pinned.lstrip("v")
        # Any OTHER version of this tool mentioned in the README is drift. Matching on the
        # tool name keeps this from tripping over unrelated numbers in the prose.
        for lineno, line in enumerate(_readme.splitlines(), 1):
            # TABLE ROWS ONLY. The prose deliberately names OLD versions — the section on
            # keeping the pin current cites semgrep 1.96.0 as the release that stopped
            # starting on newer runner Pythons, and that sentence is history, not a pin.
            # Flagging it would push someone to "fix" a worked example into nonsense.
            if not line.lstrip().startswith("|"):
                continue
            if label not in line.lower():
                continue
            for found in re.findall(rf"{label}[^0-9\n]{{0,4}}v?(\d+\.\d+\.\d+)", line, re.I):
                if found != bare:
                    fail.append(f"gates/README.md:{lineno} says {label} {found} but the gate "
                                f"workflows pin {pinned} — the README is the number people copy")

if fail:
    print("✗ docs drift:")
    for f in fail:
        print(f"    {f}")
    sys.exit(1)
print(f"✓ docs consistent — {len(cmds)} commands, {len(skills)} skills, "
      f"{len(mcp.get('mcpServers', mcp))} MCP servers listed; version {pj} in sync "
      f"(plugin.json = CLAUDE.md = marketplace.json = ref plugin-v{pj})")
