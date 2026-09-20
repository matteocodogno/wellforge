#!/usr/bin/env python3
"""Prove an adapter's OUTPUT is shippable — the machine half of adapters/*/SMOKE-TEST.md.

    uv run --with pyyaml python adapters/smoke-test.py --adapter copilot|opencode
    uv run --with pyyaml python adapters/smoke-test.py --adapter opencode --keep /tmp/x

Generates the adapter into a temp dir and asserts four things about what came out. Each
assertion exists because its failure is INVISIBLE — the generator prints a healthy summary
either way:

  a. no generated file is empty      — both generators once emitted 44 zero-byte skill
                                       files (`open(p, "w")` evaluated before the read) and
                                       still reported "44 skill files". Count is not content.
  b. every relative link resolves    — the plugin's links are right in the PLUGIN tree; the
                                       adapter writes a different tree. Two Copilot links
                                       pointed at nothing until this check existed.
  c. every command/agent/skill has   — a generator that silently stops emitting one artifact
     a counterpart, or is declared     kind looks identical in the summary. Deliberate gaps
     absent in the adapter README      are legitimate; UNDECLARED gaps are the bug.
  d. generated model names match     — model-tiers.yml is the single source of routing; a
     config/model-tiers.yml            hand-edited or stale generated `model:` sends work to
                                       the wrong tier and nothing complains.

Exit 0 = all four pass. Non-zero = the adapter would ship broken; the output names the file.
"""
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import yaml
except ImportError:
    sys.exit("smoke-test.py needs pyyaml (uv run --with pyyaml)")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLUGIN = os.path.join(ROOT, "wellforge-plugin")

# Per-adapter layout: where the generator writes, and how a generated filename maps back to
# the plugin artifact it came from. `name_re` must expose a `name` group.
ADAPTERS = {
    "copilot": {
        "roots": [".github", ".vscode"],
        "commands": (".github/prompts", "wf-*.prompt.md", r"wf-(?P<name>.+)\.prompt"),
        "agents": (".github/chatmodes", "wf-*.chatmode.md", r"wf-(?P<name>.+)\.chatmode"),
        "skills": ".github/wf-skills",
    },
    "opencode": {
        "roots": [".opencode", "opencode.json"],
        "commands": (".opencode/commands", "wf-*.md", r"wf-(?P<name>.+)"),
        "agents": (".opencode/agents", "wf-*.md", r"wf-(?P<name>.+)"),
        "skills": ".opencode/skills",
    },
}

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def plugin_inventory():
    return {
        "commands": {os.path.basename(f)[:-3] for f in glob.glob(f"{PLUGIN}/commands/*.md")},
        "agents": {os.path.basename(f)[:-3] for f in glob.glob(f"{PLUGIN}/agents/*.md")},
        "skills": {os.path.basename(os.path.dirname(f))
                   for f in glob.glob(f"{PLUGIN}/skills/*/SKILL.md")},
    }


def declared_absent(adapter):
    """`wellforge-adapter-coverage` YAML block in the adapter README — the ONLY sanctioned
    way to have a plugin artifact with no counterpart. An undeclared gap fails assertion c;
    declaring one is a visible edit to a file humans read, which is the point."""
    readme = os.path.join(HERE, adapter, "README.md")
    m = re.search(r"```yaml wellforge-adapter-coverage\n(.*?)```", open(readme).read(), re.S)
    if not m:
        return None
    doc = yaml.safe_load(m.group(1)) or {}
    absent = doc.get("intentionally_absent") or {}
    return {k: set(absent.get(k) or []) for k in ("commands", "agents", "skills")}


def generate(adapter, out):
    cmd = [sys.executable, os.path.join(HERE, adapter, "generate.py"), "--out", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr, sep="\n")
        sys.exit(f"✗ {adapter}: generator exited {r.returncode}")
    return r.stderr


def a_nonempty(out, roots):
    """a. Every emitted file has bytes. Not just markdown — an empty mcp.json or an empty
    enforcement plugin is the same class of failure and just as quiet."""
    empties = []
    for root in roots:
        p = os.path.join(out, root)
        if os.path.isfile(p):
            if os.path.getsize(p) == 0:
                empties.append(root)
            continue
        for dp, _, fns in os.walk(p):
            for fn in fns:
                fp = os.path.join(dp, fn)
                if os.path.getsize(fp) == 0:
                    empties.append(os.path.relpath(fp, out))
    return sorted(empties)


def b_links(out, roots):
    """b. Every relative markdown link resolves inside the GENERATED tree."""
    bad = []
    for root in roots:
        base = os.path.join(out, root)
        if not os.path.isdir(base):
            continue
        for dp, _, fns in os.walk(base):
            for fn in fns:
                if not fn.endswith(".md"):
                    continue
                fp = os.path.join(dp, fn)
                text = open(fp, encoding="utf-8", errors="replace").read()
                for m in LINK.finditer(text):
                    t = m.group(1)
                    # absolute, anchor-only, or a template placeholder the tool expands
                    if t.startswith(("http://", "https://", "mailto:", "#", "<")):
                        continue
                    if "${" in t or "{{" in t:
                        continue
                    tp = t.split("#")[0]
                    if not tp:
                        continue
                    if not os.path.exists(os.path.normpath(os.path.join(dp, tp))):
                        bad.append(f"{os.path.relpath(fp, out)} → {t}")
    return sorted(bad)


def c_coverage(out, spec, adapter):
    """c. Counterpart for every plugin command / agent / skill, or a declared absence."""
    absent = declared_absent(adapter)
    if absent is None:
        return [f"adapters/{adapter}/README.md has no ```yaml wellforge-adapter-coverage "
                f"block — coverage cannot be judged, so it is a failure, not a pass"], {}
    have = {}
    for kind in ("commands", "agents"):
        d, pat, name_re = spec[kind]
        rx = re.compile(name_re + "$")
        names = set()
        for f in glob.glob(os.path.join(out, d, pat)):
            stem = os.path.basename(f)[:-3]
            m = rx.match(stem)
            if m:
                names.add(m.group("name"))
        have[kind] = names
    have["skills"] = {os.path.basename(d)
                      for d in glob.glob(os.path.join(out, spec["skills"], "*"))
                      if os.path.isdir(d)}

    plugin = plugin_inventory()
    problems = []
    for kind in ("commands", "agents", "skills"):
        missing = plugin[kind] - have[kind] - absent[kind]
        for n in sorted(missing):
            problems.append(f"{kind[:-1]} '{n}' has no counterpart and is not listed in "
                            f"intentionally_absent.{kind} (adapters/{adapter}/README.md)")
        # A declared absence that is actually present is stale documentation, not a crisis,
        # but it is exactly how the list stops meaning anything.
        for n in sorted(absent[kind] & have[kind]):
            problems.append(f"{kind[:-1]} '{n}' IS generated but is listed as "
                            f"intentionally_absent — remove it from the README")
    return problems, have


def d_routing(out, spec, adapter):
    """d. Generated `model:` values == routing × tiers for this tool. Reuses the plugin's
    own drift guard rather than re-deriving the expectation here."""
    d, pat, name_re = spec["agents"]
    cmd = [sys.executable, os.path.join(PLUGIN, "scripts", "check-routing.py"),
           "--tool", adapter, "--agents", os.path.join(out, d),
           "--glob", pat, "--name-re", name_re]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True, choices=sorted(ADAPTERS))
    ap.add_argument("--keep", help="generate here and keep it (default: a temp dir, removed)")
    args = ap.parse_args()

    spec = ADAPTERS[args.adapter]
    out = args.keep or tempfile.mkdtemp(prefix=f"wf-smoke-{args.adapter}-")
    os.makedirs(out, exist_ok=True)
    try:
        generate(args.adapter, out)
        print(f"\n{args.adapter} adapter smoke test  ({out})")

        failed = 0

        empties = a_nonempty(out, spec["roots"])
        if empties:
            failed += 1
            print(f"  ✗ a. {len(empties)} EMPTY generated file(s):")
            for e in empties[:20]:
                print(f"       {e}")
        else:
            print("  ✓ a. no empty generated files")

        bad = b_links(out, spec["roots"])
        if bad:
            failed += 1
            print(f"  ✗ b. {len(bad)} unresolved relative link(s):")
            for e in bad[:20]:
                print(f"       {e}")
        else:
            print("  ✓ b. every relative link resolves")

        problems, have = c_coverage(out, spec, args.adapter)
        if problems:
            failed += 1
            print(f"  ✗ c. {len(problems)} coverage problem(s):")
            for e in problems[:20]:
                print(f"       {e}")
        else:
            counts = " · ".join(f"{len(have[k])} {k}" for k in ("commands", "agents", "skills"))
            print(f"  ✓ c. coverage complete — {counts}")

        rc, msg = d_routing(out, spec, args.adapter)
        if rc != 0:
            failed += 1
            print("  ✗ d. model routing:")
            for line in msg.splitlines():
                print(f"       {line}")
        else:
            print(f"  ✓ d. {msg.lstrip('✓ ')}")

        print()
        if failed:
            print(f"{args.adapter}: {failed} of 4 assertions FAILED")
            return 1
        print(f"{args.adapter}: 4 of 4 assertions passed")
        return 0
    finally:
        if not args.keep:
            shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
