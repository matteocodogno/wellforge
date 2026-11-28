#!/usr/bin/env python3
"""Find the tells that make a UI read as generated — deterministic, advisory, with the fix.

  slop-check.py [PATH …] [--diff-base REF] [--files F …] [--format text|json|github|markdown]
                [--strict] [--config slop-signs.yml] [--repo DIR]

PATH may be a file or a directory (walked, skipping node_modules/dist/build/…). --diff-base
narrows the scan to files changed since REF (under PATH, when one is given). With no PATH,
no --files and no --diff-base, the tracked files of --repo are scanned. A saved HTML snapshot
of a live site is a valid PATH: the markup rules apply to it like to any template.

The catalogue is config/slop-signs.yml. Each finding names its sign and its fix, and is
grouped by the pass that fixes it, so the output is the designer's audit list in the order
frontend-dev should work through it.

ADVISORY: exit 0 whatever it finds — every sign has a legitimate use somewhere, so a finding
is a question for the designer, not a verdict. `--strict` exits 1 on findings, for a caller
that wants a hard stop (a re-check after a fix pass, never a CI default). Exit 2 means the
input could not be read (bad config, git failure): an empty answer resting on missing input
must not look like a clean screen.

A line carrying `slop-ok` is skipped — the documented way to keep a deliberate choice.

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

MARKUP = {".tsx", ".jsx", ".vue", ".svelte", ".astro", ".html", ".htm"}
STYLE = {".css", ".scss"}
KINDS = {"markup": MARKUP, "style": STYLE, "all": MARKUP | STYLE}
# Single-file components and pages carry their own <style> block, so the style rules apply to
# them as well. This is also what makes a saved snapshot of a live site checkable: its CSS is
# inline in the HTML.
EMBEDS_STYLE = {".html", ".htm", ".vue", ".svelte", ".astro"}

# Directories that hold generated, vendored or test code — never the screen a person sees.
SKIP_DIRS = {"node_modules", "dist", "build", "out", ".next", ".nuxt", ".svelte-kit",
             ".astro", "coverage", "vendor", ".git", ".venv", "storybook-static",
             "__tests__", "__mocks__", "playwright-report", "test-results",
             ".wellforge-gates"}  # the gate checkout inside a CI workspace, never the caller's UI
SKIP_GLOBS = ("*.min.css", "*.test.*", "*.spec.*", "*.d.ts")

GROUP_ORDER = ["spacing", "color", "icons", "copy", "type", "layout", "details", "motion"]
SUPPRESS = "slop-ok"


def load_config(path=None):
    p = path or os.path.join(PLUGIN, "config", "slop-signs.yml")
    cfg = yaml.safe_load(open(p))
    signs = []
    for s in cfg.get("signs") or []:
        flags = re.I if s.get("ignore_case") else 0
        signs.append({
            **s,
            "_re": re.compile(s["pattern"], flags),
            "_require": re.compile(s["require"], flags) if s.get("require") else None,
            "_exts": KINDS[s.get("files", "all")] | (EMBEDS_STYLE if s.get("files") == "style" else set()),
        })
    return signs


def ext_of(path):
    """The extension that decides the rules. A Copier/Jinja template (`App.tsx.jinja`) is
    judged as what it renders to, so a preset can be checked before anyone scaffolds it."""
    name = os.path.basename(path)
    if name.endswith(".jinja"):
        name = name[: -len(".jinja")]
    return os.path.splitext(name)[1].lower()


def scannable(path):
    p = path.replace("\\", "/")
    parts = p.split("/")
    if any(d in SKIP_DIRS for d in parts[:-1]):
        return False
    name = parts[-1]
    if any(fnmatch.fnmatch(name, g) for g in SKIP_GLOBS):
        return False
    return ext_of(name) in KINDS["all"]


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for f in sorted(filenames):
            yield os.path.join(dirpath, f)


def _git(args, repo):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip() or f"git {' '.join(args)} failed"
    return [l for l in r.stdout.splitlines() if l.strip()], None


def collect(paths, files, diff_base, repo):
    """Return (sorted scannable paths, error).

    PATHs and --files are scanned as given. --diff-base narrows to the files changed since
    that ref — and when PATHs are given too, to the changed files UNDER them (a PR touching
    the backend and the frontend, checked from the frontend's directory). With none of the
    three, the tracked files of `repo` are scanned.
    """
    out, error = [], None
    if diff_base:
        # ACMR: a deleted file has no screen left to judge.
        changed, error = _git(["diff", "--name-only", "--diff-filter=ACMR", f"{diff_base}...HEAD"], repo)
        changed = [os.path.normpath(os.path.join(repo, c)) for c in changed or []]
        if paths:
            roots = [os.path.normpath(p) for p in paths]
            changed = [c for c in changed
                       if any(r == "." or c == r or c.startswith(r + os.sep) for r in roots)]
        out += changed
    else:
        for p in paths:
            out += list(walk(p)) if os.path.isdir(p) else [p]
        if not paths and not files:
            tracked, error = _git(["ls-files"], repo)
            out += [os.path.join(repo, t) for t in tracked or []]
    out += files
    seen = sorted({os.path.normpath(p) for p in out if scannable(p) and os.path.isfile(p)})
    return seen, error


def off_grid(match):
    """True when the captured px value is not on the 4px grid (2 allowed: a nudge, not a rhythm)."""
    try:
        v = float(match.group(1))
    except (IndexError, TypeError, ValueError):
        return True
    return not (v == 0 or v == 2 or (v.is_integer() and int(v) % 4 == 0))


def scan_text(text, path, signs):
    ext = ext_of(path)
    findings = []
    for n, line in enumerate(text.splitlines(), 1):
        if SUPPRESS in line:
            continue
        for s in signs:
            if ext not in s["_exts"]:
                continue
            if s["_require"] and not s["_require"].search(line):
                continue
            for m in s["_re"].finditer(line):
                if s.get("check") == "off_grid" and not off_grid(m):
                    continue
                findings.append({
                    "path": path, "line": n, "col": m.start() + 1, "id": s["id"],
                    "group": s["group"], "match": m.group(0).strip()[:60],
                    "sign": s["sign"], "fix": s["fix"],
                })
                break  # one finding per sign per line: the line is the unit a fix touches
    return findings


def scan(paths, signs):
    findings = []
    for p in paths:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        findings += scan_text(text, p, signs)
    rank = {g: i for i, g in enumerate(GROUP_ORDER)}
    findings.sort(key=lambda f: (rank.get(f["group"], 99), f["path"], f["line"], f["id"]))
    return findings


def summarize(findings, scanned):
    by_group = {}
    for f in findings:
        by_group[f["group"]] = by_group.get(f["group"], 0) + 1
    files = len({f["path"] for f in findings})
    # Coarse triage, the same three answers a redline review starts from. Thresholds are
    # deliberately blunt: the designer reads the list, this only says how long it is.
    groups = len(by_group)
    if not findings:
        level = "none"
    elif groups >= 3 or len(findings) >= 10:
        level = "heavy"
    else:
        level = "light"
    return {"scanned": scanned, "findings": len(findings), "files": files,
            "by_group": {g: by_group[g] for g in GROUP_ORDER if g in by_group}, "level": level}


def render(findings, summary, fmt):
    if fmt == "json":
        return json.dumps({"summary": summary, "findings": findings}, indent=2, ensure_ascii=False)
    if fmt == "github":
        lines = [f"::warning file={f['path']},line={f['line']},col={f['col']},"
                 f"title=ui-slop {f['id']}::{f['sign']} → {f['fix']}" for f in findings]
        lines.append(_headline(summary))
        return "\n".join(lines)
    if fmt == "markdown":
        out = ["## UI slop check (advisory)", "", _headline(summary), ""]
        if findings:
            out += ["| Pass | Where | Sign | Fix |", "|---|---|---|---|"]
            out += [f"| {f['group']} | `{f['path']}:{f['line']}` | {f['sign']} (`{f['id']}`) | {f['fix']} |"
                    for f in findings]
            out += ["", "Keep a deliberate one with a `slop-ok: <reason>` comment on its line."]
        return "\n".join(out)
    out = []
    group = None
    for f in findings:
        if f["group"] != group:
            group = f["group"]
            out.append(f"\n{group}")
        out.append(f"  {f['path']}:{f['line']}  [{f['id']}] {f['sign']}  `{f['match']}`")
        out.append(f"      → {f['fix']}")
    out.append("\n" + _headline(summary))
    return "\n".join(out).lstrip("\n")


def _headline(s):
    if not s["findings"]:
        return f"ui-slop: no signs in {s['scanned']} file(s)"
    groups = ", ".join(f"{g} {n}" for g, n in s["by_group"].items())
    return (f"ui-slop: {s['findings']} sign(s) in {s['files']} of {s['scanned']} file(s) — "
            f"{s['level']} ({groups})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", help="files or directories to scan")
    ap.add_argument("--files", nargs="*", default=[], help="explicit files")
    ap.add_argument("--diff-base", default=None, help="scan only files changed since this git ref")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--config", default=None)
    ap.add_argument("--format", choices=["text", "json", "github", "markdown"], default="text")
    ap.add_argument("--json", action="store_const", const="json", dest="format",
                    help="shorthand for --format json")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything is found")
    args = ap.parse_args(argv)

    try:
        signs = load_config(args.config)
    except (OSError, yaml.YAMLError, re.error, KeyError) as e:
        print(f"slop-check: cannot load the catalogue: {e}", file=sys.stderr)
        return 2

    paths, error = collect(args.paths, args.files, args.diff_base, args.repo)
    if error:
        print(f"slop-check: {error}", file=sys.stderr)
        return 2
    findings = scan(paths, signs)
    summary = summarize(findings, len(paths))
    print(render(findings, summary, args.format))
    return 1 if (args.strict and findings) else 0


if __name__ == "__main__":
    sys.exit(main())
