#!/usr/bin/env python3
"""Verify a tool's agent frontmatter `model:` matches routing × tiers (drift guard).

  check-routing.py [--tool claude] [--routing config/model-routing.yml]
                   [--tiers config/model-tiers.yml] [--agents agents/]

routing.yml assigns each agent a TIER (tool-neutral); tiers.yml resolves tier → model per
tool. Expected model for an agent = tiers[tool][routing.agents[agent].tier]. Exits non-zero
on any mismatch — run after editing routing/tiers or an agent, and in the repo's checks.
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


def frontmatter_model(path):
    t = open(path).read()
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.strip().startswith("model:"):
            return line.split(":", 1)[1].strip()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tool", default="claude")
    ap.add_argument("--provider", default="anthropic")
    ap.add_argument("--routing", default=os.path.join(HERE, "..", "config", "model-routing.yml"))
    ap.add_argument("--tiers", default=os.path.join(HERE, "..", "config", "model-tiers.yml"))
    ap.add_argument("--agents", default=os.path.join(HERE, "..", "agents"))
    args = ap.parse_args()

    routing = yaml.safe_load(open(args.routing))
    tier_map = yaml.safe_load(open(args.tiers))["tools"]
    if args.tool not in tier_map:
        sys.exit(f"tool '{args.tool}' not in model-tiers.yml (have: {', '.join(tier_map)})")
    if args.provider not in tier_map[args.tool]:
        sys.exit(f"provider '{args.provider}' not in tiers for {args.tool} "
                 f"(have: {', '.join(tier_map[args.tool])})")
    tiers = tier_map[args.tool][args.provider]        # tier → model for this tool+provider
    expected = {name: tiers[spec["tier"]] for name, spec in routing["agents"].items()}

    problems = []
    checked = 0
    for fp in sorted(glob.glob(os.path.join(args.agents, "*.md"))):
        name = os.path.splitext(os.path.basename(fp))[0]
        actual = frontmatter_model(fp)
        if name not in expected:
            # specialists may legitimately be unlisted only if they set no model; flag if they do
            if actual is not None:
                problems.append(f"{name}: not in routing policy but pins model '{actual}'")
            continue
        checked += 1
        want = expected[name]
        if actual != want:
            problems.append(f"{name}: frontmatter model '{actual}' != policy tier model '{want}'")

    listed = set(expected) - {os.path.splitext(os.path.basename(f))[0] for f in glob.glob(os.path.join(args.agents, '*.md'))}
    for missing in sorted(listed):
        problems.append(f"{missing}: in policy but no agent file found")

    if problems:
        print(f"model-routing drift ({args.tool}):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print(f"✓ model routing consistent ({args.tool}) — {checked} agents match {routing['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
