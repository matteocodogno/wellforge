#!/usr/bin/env python3
"""The adapters' spec-drift checks: a lifecycle edit is not drift — in every tool.

`/wellforge:done` writes `status: done` + `done:` into spec.md as its last step, and
`/wellforge:promote` writes `rigor:`. Neither changes what the feature asks for, and
tasks.md is rightly untouched. forge-state.py has said so since 2.49.1 and the Claude Code
Stop hook since 2.55.0 — but the two adapters carry their OWN copies of the drift check, and
both still called it drift:

  Copilot   lefthook `spec-drift` (pre-commit)  → BLOCKED the commit that closes a feature
  OpenCode  `session.idle` in the plugin         → warned about it on every idle

Three copies of one rule is the real defect, and until the shared core is extracted the
honest fix is to pin all three to forge-state.py's list and behaviour. This suite drives the
REAL artifacts — the `run:` script out of lefthook.yml under /bin/sh, and the shipped
wellforge.js under node with a fake `$` that runs real git — in real temporary repositories.

Run: python3 scripts/tests/adapters-drift.test.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
LEFTHOOK = os.path.join(ROOT, "adapters", "copilot", "githooks", "lefthook.yml")
OPENCODE = os.path.join(ROOT, "adapters", "opencode", "plugin", "wellforge.js")
FORGE_STATE = os.path.join(ROOT, "wellforge-plugin", "scripts", "forge-state.py")
STOP_HOOK = os.path.join(ROOT, "wellforge-plugin", "hooks", "scripts", "stop-verify.sh")

ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
passed = failed = skipped = 0

SPEC = "---\nid: 001\ntitle: X\nstatus: in-progress\nrigor: production\n---\n# Spec\n- AC-1: a thing\n"


def case(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok    {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        for line in str(detail).strip().splitlines()[-10:]:
            print(f"          {line}")


def git(repo, *args):
    r = subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t",
                        "-c", "commit.gpgsign=false", *args],
                       capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def new_repo(tmp, name):
    repo = os.path.join(tmp, name)
    os.makedirs(os.path.join(repo, "specs", "001-x"))
    git(repo, "init", "-q", "-b", "main", ".")
    write(repo, "specs/001-x/spec.md", SPEC)
    write(repo, "specs/001-x/tasks.md", "# Tasks\n- [x] T1\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: base")
    return repo


def write(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


# ── the scenarios, shared by both adapters ──────────────────────────────────────────
# (name, {path: new content}, is it drift?)
SCENARIOS = [
    ("the close: status: done + done:",
     {"specs/001-x/spec.md": SPEC.replace("status: in-progress", "status: done")
                                 .replace("rigor: production\n", "rigor: production\ndone: 2026-10-06\n")},
     False),
    ("promote: rigor only",
     {"specs/001-x/spec.md": SPEC.replace("rigor: production", "rigor: mvp")}, False),
    ("a body change",
     {"specs/001-x/spec.md": SPEC + "- AC-2: another thing\n"}, True),
    ("a lifecycle edit PLUS a body change",
     {"specs/001-x/spec.md": SPEC.replace("status: in-progress", "status: done") + "- AC-2: x\n"}, True),
    ("a non-lifecycle frontmatter field (title)",
     {"specs/001-x/spec.md": SPEC.replace("title: X", "title: Y")}, True),
    ("'status: done' typed into the BODY",
     {"specs/001-x/spec.md": SPEC + "status: done\n"}, True),
    ("a brand-new plan.md beside an existing tasks.md",
     {"specs/001-x/plan.md": "---\nspec: 001\nstatus: draft\n---\n# Plan\n"}, True),
]


def lifecycle_fields_of_forge_state():
    src = open(FORGE_STATE).read()
    block = re.search(r"LIFECYCLE_FIELDS = frozenset\(\{(.*?)\}\)", src, re.S).group(1)
    return sorted(re.findall(r'"([a-z_]+)"', block))


def main():  # noqa: C901
    global skipped
    want = lifecycle_fields_of_forge_state()

    # ── one rule, four readers ──────────────────────────────────────────────────────
    hook = re.search(r'^LIFECYCLE_FIELDS="([^"]+)"', open(STOP_HOOK).read(), re.M)
    case("Claude Code Stop hook lists forge-state.py's lifecycle fields",
         bool(hook) and sorted(hook.group(1).split("|")) == want,
         f"want {want}\ngot  {hook and sorted(hook.group(1).split('|'))}")

    lh_text = open(LEFTHOOK).read()
    lh = re.search(r'LIFECYCLE_FIELDS="([^"]+)"', lh_text)
    case("Copilot lefthook lists forge-state.py's lifecycle fields",
         bool(lh) and sorted(lh.group(1).split("|")) == want,
         f"want {want}\ngot  {lh and sorted(lh.group(1).split('|'))}")

    oc_text = open(OPENCODE).read()
    oc = re.search(r"const LIFECYCLE_FIELDS = \[(.*?)\]", oc_text, re.S)
    got_oc = sorted(re.findall(r'"([a-z_]+)"', oc.group(1))) if oc else None
    case("OpenCode plugin lists forge-state.py's lifecycle fields",
         got_oc == want, f"want {want}\ngot  {got_oc}")

    tmp = tempfile.mkdtemp(prefix="wf-adapters-drift-")
    try:
        # ── Copilot: the real `run:` script, under /bin/sh, on STAGED changes ────────
        script = yaml.safe_load(lh_text)["pre-commit"]["commands"]["spec-drift"]["run"]
        for i, (name, changes, drift) in enumerate(SCENARIOS):
            repo = new_repo(tmp, f"lh{i}")
            for rel, text in changes.items():
                write(repo, rel, text)
            git(repo, "add", "-A")
            staged = " ".join(changes)          # what lefthook substitutes for the glob
            r = subprocess.run(["/bin/sh", "-c", script.replace("{staged_files}", staged)],
                               cwd=repo, capture_output=True, text=True, env=ENV)
            blocked = r.returncode != 0
            case(f"copilot pre-commit — {name}: {'blocks' if drift else 'passes'}",
                 blocked == drift, f"rc={r.returncode}\n{r.stdout}{r.stderr}")

        # re-syncing tasks.md in the same commit is still the way to clear real drift
        repo = new_repo(tmp, "lh-resync")
        write(repo, "specs/001-x/spec.md", SPEC + "- AC-2: another thing\n")
        write(repo, "specs/001-x/tasks.md", "# Tasks\n- [x] T1\n- [ ] T2\n")
        git(repo, "add", "-A")
        r = subprocess.run(["/bin/sh", "-c", script.replace("{staged_files}", "specs/001-x/spec.md")],
                           cwd=repo, capture_output=True, text=True, env=ENV)
        case("copilot pre-commit — a body change WITH tasks.md staged: passes",
             r.returncode == 0, f"rc={r.returncode}\n{r.stdout}{r.stderr}")

        # ── OpenCode: the shipped plugin, under node, with a fake `$` running real git ─
        node = shutil.which("node")
        if not node:
            skipped += len(SCENARIOS)
            print(f"  SKIP: node is not on PATH — {len(SCENARIOS)} OpenCode cases not run "
                  f"(a skip is not a pass)")
        else:
            harness = os.path.join(tmp, "harness.mjs")
            with open(harness, "w") as fh:
                fh.write(HARNESS)
            for i, (name, changes, drift) in enumerate(SCENARIOS):
                repo = new_repo(tmp, f"oc{i}")
                for rel, text in changes.items():
                    write(repo, rel, text)
                # session.idle looks at the WORKING TREE; a new file must be known to git
                # to show up in `git diff`, exactly as in a real session.
                git(repo, "add", "-N", ".")
                r = subprocess.run([node, harness, OPENCODE], cwd=repo, capture_output=True,
                                   text=True, env=ENV)
                try:
                    logs = json.loads(r.stdout.strip().splitlines()[-1])
                except Exception:  # noqa: BLE001
                    case(f"opencode session.idle — {name}", False, r.stdout + r.stderr)
                    continue
                warned = any("drift" in (m or "") for m in logs)
                case(f"opencode session.idle — {name}: {'warns' if drift else 'silent'}",
                     warned == drift, f"logs={logs}\n{r.stderr}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nadapters drift: {passed} passed, {failed} failed"
          + (f", {skipped} skipped" if skipped else ""))
    return 0 if failed == 0 else 1


# A fake of the two things the plugin is handed. `$` is Bun's shell tag in OpenCode: a
# tagged template whose result is awaitable and chainable (.quiet().nothrow()), resolving to
# an object with .exitCode and .text(). Here it runs the command for real, in the cwd.
HARNESS = r"""
import { spawnSync } from "node:child_process"
import { pathToFileURL } from "node:url"

const sh = (strings, ...values) => {
  const quote = (v) => "'" + String(v).replace(/'/g, "'\\''") + "'"
  const cmd = strings.reduce((acc, s, i) => acc + s + (i < values.length ? quote(values[i]) : ""), "")
  const run = () => {
    const r = spawnSync("/bin/sh", ["-c", cmd], { encoding: "utf8" })
    return { exitCode: r.status ?? 1, stdout: r.stdout || "", text: () => r.stdout || "" }
  }
  const p = {
    quiet() { return p }, nothrow() { return p },
    text() { return Promise.resolve(run().text()) },
    then(resolve, reject) { try { resolve(run()) } catch (e) { reject(e) } },
  }
  return p
}

const logs = []
const client = { app: { log: async ({ body }) => { logs.push(body && body.message) } } }
const mod = await import(pathToFileURL(process.argv[2]).href)
const plugin = await mod.WellForge({ $: sh, client })
await plugin["session.idle"]()
console.log(JSON.stringify(logs))
"""


if __name__ == "__main__":
    sys.exit(main())
