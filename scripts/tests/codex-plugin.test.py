#!/usr/bin/env python3
"""The native Codex plugin package (`wellforge-codex-plugin/`): committed, generated, installed.

The package is the one adapter output this repo COMMITS — a Codex marketplace installs it
from git, so it has to exist at the tag. A committed generated tree has one way to go wrong
that nothing else would report: someone changes the plugin and not the package, and Codex
users get the previous release under the new version number. So:

  1. drift      a fresh `generate.py --package` into a temp dir equals the committed tree
                and marketplace, byte for byte (and exec bit for exec bit);
  2. manifest   plugin.json's version is the Claude plugin's, every `./` path it names
                exists, and every hook command runs the runner via PLUGIN_ROOT;
  3. wf-setup   install.sh, run in a throwaway repo from a subdirectory, installs the agents,
                $WF and the AGENTS.md block — twice, without touching what is the user's;
  4. hooks      the PLUGIN's hooks.json commands, run with PLUGIN_ROOT set as Codex does,
                refuse what the plugin's matrices say they refuse; SessionStart says when a
                project needs `$wf-setup`; and with project hooks installed (`--hooks`) the
                plugin's copy steps aside, so nothing runs twice.

Regenerate after a plugin change:
  uv run --with pyyaml python adapters/codex/generate.py \\
      --package wellforge-codex-plugin --marketplace .agents/plugins/marketplace.json

Run: python3 scripts/tests/codex-plugin.test.py   (needs pyyaml; the hook cases need jq)
"""
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GENERATOR = os.path.join(ROOT, "adapters", "codex", "generate.py")
PKG = os.path.join(ROOT, "wellforge-codex-plugin")
MARKET = os.path.join(ROOT, ".agents", "plugins", "marketplace.json")
CLAUDE_PLUGIN = os.path.join(ROOT, "wellforge-plugin", ".claude-plugin", "plugin.json")
INSTALL = os.path.join(PKG, "skills", "wf-setup", "scripts", "install.sh")

ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
ENV.pop("CLAUDE_PROJECT_DIR", None)
ENV.pop("PLUGIN_ROOT", None)
REGEN = ("uv run --with pyyaml python adapters/codex/generate.py --package "
         "wellforge-codex-plugin --marketplace .agents/plugins/marketplace.json")
passed = failed = 0


def case(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok    {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        for line in str(detail).strip().splitlines()[-12:]:
            print(f"          {line}")


def git(repo, *args):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True, text=True, env=ENV)


def tree(root):
    out = {}
    for d, _, files in os.walk(root):
        for f in files:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = os.access(p, os.X_OK)
    return out


def tree_diff(a, b):
    ta, tb = tree(a), tree(b)
    diffs = [f"only in committed: {p}" for p in sorted(set(ta) - set(tb))]
    diffs += [f"missing from committed: {p}" for p in sorted(set(tb) - set(ta))]
    for p in sorted(set(ta) & set(tb)):
        if not filecmp.cmp(os.path.join(a, p), os.path.join(b, p), shallow=False):
            diffs.append(f"differs: {p}")
        elif ta[p] != tb[p]:
            diffs.append(f"exec bit differs: {p}")
    return diffs


def hook_commands(path):
    doc = json.load(open(path))
    return {h["command"].rsplit(" ", 1)[1]: h["command"]
            for groups in doc["hooks"].values() for g in groups for h in g["hooks"]}


def fire(cmd, payload, cwd, plugin_root=None):
    env = dict(ENV, PLUGIN_ROOT=plugin_root) if plugin_root else ENV
    payload = {"session_id": "s1", "cwd": cwd, "model": "gpt-5.4", **payload}
    return subprocess.run(["bash", "-c", cmd], input=json.dumps(payload), cwd=cwd,
                          capture_output=True, text=True, env=env)


def bash(command):
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}


def add_env_patch():
    return {"hook_event_name": "PreToolUse", "tool_name": "apply_patch",
            "tool_input": {"command": "*** Begin Patch\n*** Add File: .env\n+FOO=1\n"
                                      "*** End Patch"}}


SESSION = {"hook_event_name": "SessionStart", "source": "startup"}


def new_project(tmp, name):
    repo = os.path.join(tmp, name)
    os.makedirs(os.path.join(repo, "src"))
    git(repo, "init", "-q", "-b", "main", ".")
    with open(os.path.join(repo, "AGENTS.md"), "w") as f:
        f.write("# Team rules\n\nMy notes.\n")
    return repo


def install(repo, *args, cwd=None):
    return subprocess.run(["bash", INSTALL, *args], cwd=cwd or repo,
                          capture_output=True, text=True, env=ENV)


def snapshot(repo):
    out = {}
    for rel in (".codex", "AGENTS.md"):
        p = os.path.join(repo, rel)
        if os.path.isfile(p):
            out[rel] = open(p).read()
        for d, _, files in os.walk(p):
            for f in files:
                fp = os.path.join(d, f)
                out[os.path.relpath(fp, repo)] = open(fp, "rb").read()
    return out


def main():
    tmp = tempfile.mkdtemp(prefix="wf-codex-plugin-")
    try:
        # ── 1. drift ────────────────────────────────────────────────────────────────
        fresh = os.path.join(tmp, "pkg")
        fresh_market = os.path.join(tmp, "marketplace.json")
        r = subprocess.run([sys.executable, GENERATOR, "--package", fresh,
                            "--marketplace", fresh_market],
                           capture_output=True, text=True, env=ENV)
        if r.returncode != 0:
            sys.exit(f"generator failed:\n{r.stdout}\n{r.stderr}")
        diffs = tree_diff(PKG, fresh) if os.path.isdir(PKG) else ["package dir missing"]
        case("committed package == a fresh generation", not diffs,
             "\n".join(diffs[:10]) + f"\nregenerate: {REGEN}")
        case("committed marketplace == a fresh generation",
             os.path.isfile(MARKET) and filecmp.cmp(MARKET, fresh_market, shallow=False),
             f"regenerate: {REGEN}")

        # ── 2. manifest ─────────────────────────────────────────────────────────────
        man = json.load(open(os.path.join(PKG, "plugin.json")))
        want = json.load(open(CLAUDE_PLUGIN))["version"]
        case("plugin.json version is the Claude plugin's", man["version"] == want,
             f"{man['version']} != {want}")
        oa = man["extensions"]["com.openai"]
        paths = [oa["hooks"], oa["onboardingSkill"]]
        case("every manifest path starts with ./ and exists",
             all(p.startswith("./") and os.path.exists(os.path.join(PKG, p)) for p in paths),
             paths)
        market = json.load(open(MARKET))
        src = market["plugins"][0]["source"]["path"]
        case("marketplace points at the package",
             os.path.normpath(os.path.join(ROOT, src)) == PKG, src)
        pcmd = hook_commands(os.path.join(PKG, "hooks", "hooks.json"))
        case("plugin hooks run the runner via PLUGIN_ROOT, scripts present",
             len(pcmd) == 7 and all("${PLUGIN_ROOT}/hooks/run-hook.sh" in c for c in pcmd.values())
             and all(os.path.isfile(os.path.join(PKG, "hooks", "scripts", f"{h}.sh"))
                     for h in pcmd), pcmd)
        mcp = json.load(open(os.path.join(PKG, "mcp.json")))["mcpServers"]
        case("every MCP server declares a portable type",
             all(s.get("type") in ("stdio", "streamable-http") for s in mcp.values()), mcp)

        if not shutil.which("jq"):
            print("  SKIP: jq not on PATH — install and hook cases need it")
            return 1 if failed else 0

        # ── 3. wf-setup ─────────────────────────────────────────────────────────────
        repo = new_project(tmp, "proj")
        r = install(repo, cwd=os.path.join(repo, "src"))
        case("install.sh succeeds from a subdirectory", r.returncode == 0, r.stdout + r.stderr)
        agents = [f for f in os.listdir(os.path.join(repo, ".codex", "agents"))
                  if f.startswith("wf-")]
        case("installs the 10 agents", len(agents) == 10, agents)
        wf = os.path.join(repo, ".codex", "wellforge")
        case("installs $WF: forge-state.py, the rubric, VERSION",
             os.path.isfile(os.path.join(wf, "scripts", "forge-state.py"))
             and os.path.isfile(os.path.join(wf, "eval-rubric.yml"))
             and open(os.path.join(wf, "VERSION")).read().strip() == want)
        case("no project hooks without --hooks",
             not os.path.exists(os.path.join(repo, ".codex", "hooks.json")))
        before = snapshot(repo)
        r = install(repo)
        md = open(os.path.join(repo, "AGENTS.md")).read()
        case("re-run is idempotent", r.returncode == 0 and snapshot(repo) == before,
             r.stderr)
        case("one WellForge block in AGENTS.md, the user's notes kept",
             md.count("wellforge-codex:start") == 1 and "My notes." in md, md)
        r = install(os.path.join(tmp))
        case("outside a git repo: refuses, says why",
             r.returncode == 1 and "not inside a git repository" in r.stderr, r.stderr)

        # ── 4. plugin hooks ─────────────────────────────────────────────────────────
        r = fire(pcmd["pre-bash-guard"], bash("cat .env"), repo, plugin_root=PKG)
        case("plugin hook: Bash `cat .env` refused", r.returncode == 2, r.stderr)
        r = fire(pcmd["pre-file-guard"], add_env_patch(), os.path.join(repo, "src"),
                 plugin_root=PKG)
        case("plugin hook: a patch adding .env refused (from a subdir)", r.returncode == 2,
             r.stderr)
        r = fire(pcmd["session-start"], SESSION, repo, plugin_root=PKG)
        case("plugin SessionStart: set-up project gets no setup note",
             r.returncode == 0 and "$wf-setup" not in r.stdout, r.stdout)
        bare = new_project(tmp, "bare")
        r = fire(pcmd["session-start"], SESSION, bare, plugin_root=PKG)
        case("plugin SessionStart: project never set up → told to run $wf-setup",
             "not set up for the Codex plugin yet" in r.stdout, r.stdout)
        with open(os.path.join(wf, "VERSION"), "w") as f:
            f.write("0.0.1\n")
        r = fire(pcmd["session-start"], SESSION, repo, plugin_root=PKG)
        case("plugin SessionStart: stale project → told to refresh",
             f"from 0.0.1, the plugin is {want}" in r.stdout, r.stdout)

        # ── --hooks: project hooks win, nothing runs twice ──────────────────────────
        os.makedirs(os.path.join(repo, ".codex"), exist_ok=True)
        with open(os.path.join(repo, ".codex", "hooks.json"), "w") as f:
            json.dump({"hooks": {"Stop": [{"hooks": [{"type": "command",
                                                      "command": "echo mine"}]}]}}, f)
        r = install(repo, "--hooks")
        jcmd = hook_commands(os.path.join(repo, ".codex", "hooks.json"))
        case("--hooks wires the project runner, the user's hook kept",
             r.returncode == 0 and "mine" in jcmd and "pre-bash-guard" in jcmd
             and os.path.isfile(os.path.join(wf, "hooks", "scripts", "pre-bash-guard.sh")),
             r.stdout + r.stderr)
        r = fire(jcmd["pre-bash-guard"], bash("cat .env"), repo)
        case("project hook refuses `cat .env`", r.returncode == 2, r.stderr)
        r = fire(pcmd["pre-bash-guard"], bash("cat .env"), repo, plugin_root=PKG)
        case("plugin hook steps aside when project hooks are wired",
             r.returncode == 0 and not r.stderr.strip(), r.stderr)
        os.remove(os.path.join(wf, "hooks", "scripts", "pre-bash-guard.sh"))
        r = install(repo)
        stop = json.load(open(os.path.join(repo, ".codex", "hooks.json")))["hooks"]["Stop"]
        case("re-run without --hooks refreshes the installed project hooks, once",
             os.path.isfile(os.path.join(wf, "hooks", "scripts", "pre-bash-guard.sh"))
             and sum("stop-verify" in h["command"] for g in stop for h in g["hooks"]) == 1,
             stop)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\ncodex plugin: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
