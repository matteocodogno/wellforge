#!/usr/bin/env python3
"""check-routing.py — the drift guard for agent `model:` and effort.

A guard that only ever runs against the files it was written for proves nothing: it passes
whether it checks effort or not. Each case below copies the real agents into a temp dir,
breaks ONE thing, and expects the guard to name it.

  real agents, claude                      → pass
  architect effort lowered to medium       → FAIL, names architect
  effort line removed from backend-dev     → FAIL, names backend-dev
  codex TOML with the wrong reasoning      → FAIL (effort read from model_reasoning_effort)
  tool with no reasoning_effort map        → effort not checked, model still is

Run: python3 wellforge-plugin/scripts/tests/check-routing.test.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(HERE, "..", ".."))
GUARD = os.path.join(PLUGIN, "scripts", "check-routing.py")
passed = failed = 0


def run(*args):
    r = subprocess.run([sys.executable, GUARD, *args], capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def check(label, cond, out=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {label}")
    else:
        failed += 1
        print(f"  ✗ {label}\n{out}")


def agents_copy():
    d = tempfile.mkdtemp(prefix="wf-routing-")
    for f in os.listdir(os.path.join(PLUGIN, "agents")):
        if f.endswith(".md"):
            shutil.copy(os.path.join(PLUGIN, "agents", f), d)
    return d


def edit(path, pattern, repl):
    t = open(path).read()
    new, n = re.subn(pattern, repl, t, count=1, flags=re.M)
    assert n == 1, f"{pattern!r} not found in {path}"
    open(path, "w").write(new)


tmp = []
try:
    rc, out = run("--tool", "claude")
    check("real agents pass (claude)", rc == 0 and "model + effort" in out, out)

    d = agents_copy(); tmp.append(d)
    edit(os.path.join(d, "architect.md"), r"^effort: high$", "effort: medium")
    rc, out = run("--tool", "claude", "--agents", d)
    check("lowered architect effort fails, named", rc != 0 and "architect: effort 'medium'" in out, out)

    d = agents_copy(); tmp.append(d)
    edit(os.path.join(d, "backend-dev.md"), r"^effort: medium\n", "")
    rc, out = run("--tool", "claude", "--agents", d)
    check("missing effort fails, named", rc != 0 and "backend-dev: effort 'None'" in out, out)

    # Codex: one TOML agent per routed agent, all correct except the architect's effort.
    d = tempfile.mkdtemp(prefix="wf-routing-codex-"); tmp.append(d)
    import yaml
    cfg = os.path.join(PLUGIN, "config")
    routing = yaml.safe_load(open(os.path.join(cfg, "model-routing.yml")))["agents"]
    tiers = yaml.safe_load(open(os.path.join(cfg, "model-tiers.yml")))
    for name, spec in routing.items():
        model = tiers["tools"]["codex"]["openai"][spec["tier"]]
        effort = tiers["reasoning_effort"]["codex"][spec["tier"]]
        if name == "architect":
            effort = "low"
        with open(os.path.join(d, f"{name}.toml"), "w") as f:
            f.write(f'model = "{model}"\nmodel_reasoning_effort = "{effort}"\n'
                    'developer_instructions = """\nmodel_reasoning_effort = "high"\n"""\n')
    rc, out = run("--tool", "codex", "--provider", "openai", "--agents", d, "--glob", "*.toml")
    check("codex effort drift fails (TOML key, not body text)",
          rc != 0 and "architect: effort 'low'" in out and out.count("✗") == 1, out)

    # opencode has no reasoning_effort map: a missing effort line is not drift there.
    d = agents_copy(); tmp.append(d)
    edit(os.path.join(d, "backend-dev.md"), r"^effort: medium\n", "")
    for f in os.listdir(d):
        p = os.path.join(d, f)
        name = os.path.splitext(f)[0]
        if name in routing:
            want = tiers["tools"]["opencode"]["anthropic"][routing[name]["tier"]]
            edit(p, r"^model: .*$", f"model: {want}")
    rc, out = run("--tool", "opencode", "--agents", d)
    check("no effort map → effort unchecked, model still checked",
          rc == 0 and "agents' model match" in out, out)
finally:
    for d in tmp:
        shutil.rmtree(d, ignore_errors=True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
