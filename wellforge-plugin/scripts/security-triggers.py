#!/usr/bin/env python3
"""Does this batch need an owasp-reviewer pass? — deterministic answer, not a judgement call.

  security-triggers.py --tier production [--touch 'a/**' --touch b.sql] [--diff-base main]
                       [--files f1 f2 …] [--json]

The security floor is non-negotiable in the rigor-tiers skill; the specialist that reviews
the code behind it used to run when someone remembered. This script is what
/wellforge:implement and /wellforge:orchestrate call between integration and QE, so the
dispatch is a property of the task graph instead of the orchestrator's memory.

It answers one question — dispatch or not, and why — and deliberately owns nothing else:
severity thresholds belong to the agent, routing of findings belongs to the rigor-tiers
table, and the verdict belongs in the run trace.

Pure stdlib except pyyaml for the config.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)


def load_config(path=None):
    p = path or os.path.join(PLUGIN, "config", "security-triggers.yml")
    if not os.path.exists(p):
        return None
    return yaml.safe_load(open(p))


def _norm(path):
    return path.replace("\\", "/").lstrip("./").lower()


def match_path(path, cfg):
    """Return the rule that matched this path, or None."""
    p = _norm(path)
    for pattern in cfg.get("patterns") or []:
        pat = pattern.lower()
        # fnmatch has no `**`; translate the two forms we use. `**/x` must also match a
        # top-level `x` — otherwise `**/migrations/**` misses `migrations/001.sql`, which
        # is exactly where a schema change lives in a single-service repo.
        if pat.startswith("**/"):
            tail = pat[3:]
            if fnmatch.fnmatch(p, tail) or fnmatch.fnmatch(p, "*/" + tail) or fnmatch.fnmatch(p, pat):
                return {"kind": "glob", "rule": pattern}
        if fnmatch.fnmatch(p, pat):
            return {"kind": "glob", "rule": pattern}
    for needle in cfg.get("path_contains") or []:
        if needle.lower() in p:
            return {"kind": "path_contains", "rule": needle}
    return None


def git_changed(base, repo="."):
    """Files changed against the batch's base. Empty on any git problem — the touch: globs
    still decide, and a missing diff must never silently turn a match into a miss."""
    try:
        out = subprocess.run(["git", "-C", repo, "diff", "--name-only", base],
                             capture_output=True, text=True, timeout=15)
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception:  # noqa: BLE001
        return []


def evaluate(tier, touches, files, cfg):
    matches = []
    for source, paths in (("touch:", touches), ("diff", files)):
        for path in paths:
            m = match_path(path, cfg)
            if m:
                matches.append({"path": path, "source": source, **m})
    always = tier in (cfg.get("always_at_tier") or [])
    return {
        "tier": tier,
        "dispatch": bool(matches) or always,
        "reason": ("tier is in always_at_tier" if always and not matches
                   else "matched a security trigger" if matches
                   else "no trigger matched"),
        "always_at_tier": always,
        "matches": matches,
        "scope": sorted({m["path"] for m in matches}) or sorted(set(files)),
        "considered": {"touch": len(touches), "diff": len(files)},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", required=True, choices=["spike", "mvp", "production"])
    ap.add_argument("--touch", action="append", default=[], help="a declared touch: glob (repeatable)")
    ap.add_argument("--files", nargs="*", default=[], help="explicit changed files")
    ap.add_argument("--diff-base", default=None, help="git ref to diff against for changed files")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--config", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cfg = load_config(args.config)
    if cfg is None:
        print("security-triggers.yml not found — cannot decide; treat as DISPATCH", file=sys.stderr)
        # Fail toward review. The cost of an unnecessary pass is one mid-tier agent; the
        # cost of a skipped one is an unreviewed auth change.
        print(json.dumps({"dispatch": True, "reason": "config missing — failing safe"}) if args.json
              else "DISPATCH (config missing — failing safe)")
        return 0

    files = list(args.files)
    if args.diff_base:
        files += git_changed(args.diff_base, args.repo)

    result = evaluate(args.tier, args.touch, files, cfg)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{'DISPATCH' if result['dispatch'] else 'skip'} owasp-reviewer — {result['reason']}")
        for m in result["matches"]:
            print(f"    {m['path']}  ({m['source']} matched {m['kind']} `{m['rule']}`)")
        if result["dispatch"] and not result["matches"]:
            print(f"    (no pattern matched; {result['tier']} reviews every batch)")
        print(f"    considered {result['considered']['touch']} touch globs, "
              f"{result['considered']['diff']} changed files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
