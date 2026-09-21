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
import glob
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
    """(files, error). Files changed against the batch's base.

    The docstring here used to promise that "a missing diff must never silently turn a match
    into a miss" and then do exactly that: every failure returned [] with no note and exit 0,
    so `--diff-base` with a typo'd ref reported "no trigger matched" and the reviewer was
    never dispatched. A bad ref does not raise — git exits non-zero with empty stdout — so
    the try/except never even fired. The error is now returned and the caller fails toward
    review, which is this file's stated policy everywhere else.
    """
    try:
        out = subprocess.run(["git", "-C", repo, "diff", "--name-only", base],
                             capture_output=True, text=True, timeout=15)
    except Exception as e:  # noqa: BLE001
        return [], f"git diff failed to run: {type(e).__name__}: {e}"
    if out.returncode != 0:
        detail = (out.stderr or "").strip().splitlines()
        return [], (f"git diff --name-only {base!r} exited {out.returncode}"
                    + (f": {detail[-1]}" if detail else ""))
    return [l for l in out.stdout.splitlines() if l.strip()], None


def expand_touch(glob_pattern, repo="."):
    """A declared `touch:` glob → the files it currently covers, repo-relative.

    `touch:` globs are matched literally as well (intent before the code exists), but a
    literal match only fires when the glob itself names a trigger — `src/auth/**` matches
    `**/auth/**`, while `src/**` does not, even though it covers `src/auth/login.ts`. A
    batch declaring the broader glob was therefore never reviewed. Expanding against the
    working tree closes that without giving up the intent half.
    """
    if not any(ch in glob_pattern for ch in "*?["):
        return []
    pat = glob_pattern
    # `a/**` in task globs means "everything under a"; glob's recursive form is `a/**/*`.
    if pat.endswith("/**"):
        pat = pat + "/*"
    try:
        hits = glob.glob(os.path.join(repo, pat), recursive=True)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for h in hits:
        if not os.path.isfile(h):
            continue
        try:
            out.append(os.path.relpath(h, repo))
        except ValueError:
            continue
    return out


def evaluate(tier, touches, files, cfg, repo=".", error=None):
    matches = []
    expanded = []
    for glob_pattern in touches:
        expanded.extend((glob_pattern, f) for f in expand_touch(glob_pattern, repo))
    for source, paths in (("touch:", touches), ("diff", files)):
        for path in paths:
            m = match_path(path, cfg)
            if m:
                matches.append({"path": path, "source": source, **m})
    for glob_pattern, path in expanded:
        m = match_path(path, cfg)
        if m:
            matches.append({"path": path, "source": f"touch:{glob_pattern}", **m})
    always = tier in (cfg.get("always_at_tier") or [])
    # An unusable diff cannot be allowed to read as "nothing matched": we do not know what
    # changed, so we cannot know that nothing sensitive did. Same policy as a missing config.
    dispatch = bool(matches) or always or bool(error)
    if error:
        reason = f"could not determine changed files — dispatching anyway ({error})"
    elif always and not matches:
        reason = "tier is in always_at_tier"
    elif matches:
        reason = "matched a security trigger"
    else:
        reason = "no trigger matched"
    result = {
        "tier": tier,
        "dispatch": dispatch,
        "reason": reason,
        "always_at_tier": always,
        "matches": matches,
        "scope": sorted({m["path"] for m in matches}) or sorted(set(files)),
        "considered": {"touch": len(touches), "touch_expanded": len(expanded), "diff": len(files)},
    }
    if error:
        result["note"] = error
    return result


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
    error = None
    if args.diff_base:
        changed, error = git_changed(args.diff_base, args.repo)
        files += changed

    result = evaluate(args.tier, args.touch, files, cfg, args.repo, error)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"{'DISPATCH' if result['dispatch'] else 'skip'} owasp-reviewer — {result['reason']}")
        for m in result["matches"]:
            print(f"    {m['path']}  ({m['source']} matched {m['kind']} `{m['rule']}`)")
        if result["dispatch"] and not result["matches"]:
            print(f"    (no pattern matched; {result['tier']} reviews every batch)")
        print(f"    considered {result['considered']['touch']} touch globs "
              f"({result['considered']['touch_expanded']} files after expansion), "
              f"{result['considered']['diff']} changed files")
        if result.get("note"):
            print(f"    note: {result['note']}", file=sys.stderr)
    # Non-zero when the answer rests on incomplete input, so a caller that only checks the
    # exit code still learns something is wrong. `dispatch` is already true in that case.
    if result.get("note"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
