#!/usr/bin/env python3
"""Verify agent frontmatter `model:` matches the model-routing policy (drift guard).

  check-routing.py [--policy config/model-routing.yml] [--agents agents/]

The policy is the source of truth (config/model-routing.yml); each agent's frontmatter
must run the model its tier maps to. Exits non-zero on any mismatch or unlisted agent —
run it after editing the policy or an agent, and in the wellforge repo's checks.
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
    ap.add_argument("--policy", default=os.path.join(HERE, "..", "config", "model-routing.yml"))
    ap.add_argument("--agents", default=os.path.join(HERE, "..", "agents"))
    args = ap.parse_args()

    policy = yaml.safe_load(open(args.policy))
    tiers = policy["tiers"]
    expected = {name: tiers[spec["tier"]] for name, spec in policy["agents"].items()}

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
        print("model-routing drift:")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print(f"✓ model routing consistent — {checked} agents match {policy['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
