#!/usr/bin/env python3
"""Verify a tool's agent frontmatter `model:` (and effort) matches routing × tiers (drift guard).

  check-routing.py [--tool claude] [--routing config/model-routing.yml]
                   [--tiers config/model-tiers.yml] [--agents agents/]
                   [--glob '*.md'] [--name-re '(?P<name>.+)']

routing.yml assigns each agent a TIER (tool-neutral); tiers.yml resolves tier → model per
tool. Expected model for an agent = tiers[tool][routing.agents[agent].tier]. Where the tool
has a `reasoning_effort` map in tiers.yml, the agent's effort (`effort:` in Markdown
frontmatter, `model_reasoning_effort` in Codex TOML) must equal that map's value for the same
tier. Unlisted agents follow the `mid` tier for effort, as the adapters do. Exits non-zero
on any mismatch — run after editing routing/tiers or an agent, and in the repo's checks.

--glob/--name-re point it at an ADAPTER's generated agents, whose filenames are namespaced
(`wf-architect.chatmode.md`): the same policy, checked against what actually shipped rather
than against the plugin files the generator read. adapters/smoke-test.py is the caller.
"""
import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("check-routing.py needs pyyaml (uv run --with pyyaml)")

HERE = os.path.dirname(__file__)


def frontmatter_field(path, key, toml_key=None):
    t = open(path).read()
    # Codex custom agents are TOML, not Markdown with frontmatter: `model = "gpt-5.5"` at
    # top level. Read with tomllib rather than a regex — a `model = ` line inside the
    # multi-line developer_instructions would otherwise be a match.
    if path.endswith(".toml"):
        import tomllib
        return tomllib.loads(t).get(toml_key or key)
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith(key + ":"):
            return line.split(":", 1)[1].strip()
    return None


def frontmatter_model(path):
    return frontmatter_field(path, "model")


def frontmatter_effort(path):
    return frontmatter_field(path, "effort", toml_key="model_reasoning_effort")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="claude")
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--routing", default=os.path.join(HERE, "..", "config", "model-routing.yml"))
    ap.add_argument("--tiers", default=os.path.join(HERE, "..", "config", "model-tiers.yml"))
    ap.add_argument("--agents", default=os.path.join(HERE, "..", "agents"))
    ap.add_argument("--glob", default="*.md", help="filename pattern inside --agents")
    ap.add_argument("--name-re", default=r"(?P<name>.+)",
                    help="regex with a 'name' group mapping a filename (sans .md) to an agent id")
    args = ap.parse_args()

    try:
        name_rx = re.compile(args.name_re + "$")
    except re.error as e:
        sys.exit(f"--name-re is not a valid regex: {e}")
    if "name" not in (name_rx.groupindex or {}):
        sys.exit("--name-re must contain a (?P<name>...) group")

    def agent_id(path):
        """Filename → the agent id the routing policy knows. None = not an agent file."""
        m = name_rx.match(os.path.splitext(os.path.basename(path))[0])
        return m.group("name") if m else None

    files = sorted(glob.glob(os.path.join(args.agents, args.glob)))

    routing = yaml.safe_load(open(args.routing))
    tiers_doc = yaml.safe_load(open(args.tiers))
    tier_map = tiers_doc["tools"]
    effort_map = (tiers_doc.get("reasoning_effort") or {}).get(args.tool)   # None = not checked
    if args.tool not in tier_map:
        sys.exit(f"tool '{args.tool}' not in model-tiers.yml (have: {', '.join(tier_map)})")
    if args.provider not in tier_map[args.tool]:
        sys.exit(f"provider '{args.provider}' not in tiers for {args.tool} "
                 f"(have: {', '.join(tier_map[args.tool])})")
    tiers = tier_map[args.tool][args.provider]        # tier → model for this tool+provider
    expected = {name: tiers[spec["tier"]] for name, spec in routing["agents"].items()}
    tier_of = {name: spec["tier"] for name, spec in routing["agents"].items()}

    problems = []
    checked = 0
    for fp in files:
        name = agent_id(fp)
        if name is None:
            continue
        actual = frontmatter_model(fp)
        if effort_map is not None:
            want_effort = effort_map.get(tier_of.get(name, "mid"))
            got_effort = frontmatter_effort(fp)
            if got_effort != want_effort:
                problems.append(f"{name}: effort '{got_effort}' != tier "
                                f"'{tier_of.get(name, 'mid')}' effort '{want_effort}'")
        if name not in expected:
            # specialists may legitimately be unlisted only if they set no model; flag if they do
            if actual is not None:
                problems.append(f"{name}: not in routing policy but pins model '{actual}'")
            continue
        checked += 1
        want = expected[name]
        if actual != want:
            problems.append(f"{name}: frontmatter model '{actual}' != policy tier model '{want}'")

    listed = set(expected) - {n for n in (agent_id(f) for f in files) if n}
    for missing in sorted(listed):
        problems.append(f"{missing}: in policy but no agent file found")

    if problems:
        print(f"model-routing drift ({args.tool}):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    what = "model + effort" if effort_map is not None else "model"
    print(f"✓ model routing consistent ({args.tool}) — {checked} agents' {what} match "
          f"{routing['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
