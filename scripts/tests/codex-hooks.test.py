#!/usr/bin/env python3
"""The Codex adapter's hooks: the plugin's own scripts, driven by Codex-shaped payloads.

The Codex adapter does not reimplement a single rule — `adapters/codex/hooks/run-hook.sh`
translates a Codex payload and runs the unchanged plugin script. That is only true if the
translation is right, and the translation has exactly two jobs a mistake in which is silent:

  1. apply_patch. Codex edits files with one tool whose `tool_input.command` is patch text;
     the file hooks read `tool_input.file_path`. Miss a path and the guard sees nothing —
     which is indistinguishable from the guard finding nothing to refuse.
  2. The root. Codex runs hooks in the session cwd, which may be a subdirectory, and patch
     paths are relative to THAT. Resolve them against the root instead and every guard keyed
     on `specs/*/spec.md` misses from inside `specs/`.

So this suite generates the real adapter into a throwaway git repo and runs the COMMAND
STRINGS out of the generated `.codex/hooks.json` — the wiring, not just the runner — from
the root and from a subdirectory.

Run: python3 scripts/tests/codex-hooks.test.py   (needs pyyaml + jq; skips without jq)
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GENERATOR = os.path.join(ROOT, "adapters", "codex", "generate.py")

ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
ENV.pop("CLAUDE_PROJECT_DIR", None)     # Codex does not set it; the runner must
passed = failed = 0

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
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *args],
                   check=True, capture_output=True, text=True, env=ENV)


def write(repo, rel, text):
    path = os.path.join(repo, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def new_repo(tmp):
    repo = os.path.join(tmp, "proj")
    os.makedirs(os.path.join(repo, "src"))
    git(repo, "init", "-q", "-b", "main", ".")
    write(repo, "specs/001-x/spec.md", SPEC)
    write(repo, "specs/001-x/tasks.md", "# Tasks\n- [ ] T1\n")
    write(repo, "src/a.ts", "export const a = 1\n")
    r = subprocess.run([sys.executable, GENERATOR, "--out", repo],
                       capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        sys.exit(f"generator failed:\n{r.stdout}\n{r.stderr}")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore: base")
    return repo


def commands(repo):
    """{hook-name: command string} exactly as the generated hooks.json wires them."""
    doc = json.load(open(os.path.join(repo, ".codex", "hooks.json")))
    out = {}
    for groups in doc["hooks"].values():
        for g in groups:
            for h in g["hooks"]:
                out[h["command"].rsplit(" ", 1)[1]] = h["command"]
    return out


def fire(repo, cmd, payload, cwd=None):
    cwd = cwd or repo
    payload = {"session_id": "s1", "cwd": cwd, "model": "gpt-5.4", **payload}
    return subprocess.run(["bash", "-c", cmd], input=json.dumps(payload), cwd=cwd,
                          capture_output=True, text=True, env=ENV)


def patch(*lines):
    return {"hook_event_name": "PreToolUse", "tool_name": "apply_patch",
            "tool_input": {"command": "\n".join(["*** Begin Patch", *lines, "*** End Patch"])}}


def bash(command):
    return {"hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": command}}


def main():
    if not shutil.which("jq"):
        print("  SKIP: jq not on PATH — the hooks need it (and so does Claude Code's)")
        return 0
    tmp = tempfile.mkdtemp(prefix="wf-codex-hooks-")
    try:
        repo = new_repo(tmp)
        cmd = commands(repo)
        sub = os.path.join(repo, "specs")

        case("hooks.json wires the eight ported hooks",
             sorted(cmd) == sorted(["session-start", "pre-bash-guard", "pre-file-guard",
                                    "post-lint", "post-spec-guard", "stop-verify",
                                    "trace-subagent", "subagent-decisions-guard"]), sorted(cmd))

        # ── pre-bash-guard: unchanged script, Codex payload ──────────────────────────
        r = fire(repo, cmd["pre-bash-guard"], bash("rm -rf ~"))
        case("Bash `rm -rf ~` is refused (exit 2)", r.returncode == 2, r.stderr)
        r = fire(repo, cmd["pre-bash-guard"], bash("cat .env"))
        case("Bash `cat .env` is refused — the read half of the file guard", r.returncode == 2,
             r.stderr)
        r = fire(repo, cmd["pre-bash-guard"], bash("ls -la src"), cwd=sub)
        case("Bash `ls` passes, from a subdirectory too", r.returncode == 0, r.stderr)

        # ── pre-file-guard through apply_patch ───────────────────────────────────────
        r = fire(repo, cmd["pre-file-guard"], patch("*** Add File: .env", "+K=v"))
        case("patch adding .env is refused", r.returncode == 2 and ".env" in r.stderr, r.stderr)
        r = fire(repo, cmd["pre-file-guard"],
                 patch("*** Update File: src/a.ts", "@@", "-export const a = 1",
                       "+export const a = 2", "*** Add File: config/server.pem", "+x"))
        case("a patch with ONE protected path among clean ones is refused whole",
             r.returncode == 2 and "server.pem" in r.stderr, r.stderr)
        r = fire(repo, cmd["pre-file-guard"],
                 patch("*** Update File: src/a.ts", "*** Move to: .env.local", "@@", "+x"))
        case("a patch MOVING a file onto .env.local is refused", r.returncode == 2, r.stderr)
        r = fire(repo, cmd["pre-file-guard"], patch("*** Delete File: secrets.yml"))
        case("a patch deleting secrets.yml is refused", r.returncode == 2, r.stderr)
        r = fire(repo, cmd["pre-file-guard"], patch("*** Add File: .env.example", "+K="))
        case(".env.example passes (a committed manifest)", r.returncode == 0, r.stderr)
        r = fire(repo, cmd["pre-file-guard"], patch("*** Add File: ../.env", "+K=v"), cwd=sub)
        case("a relative path is resolved against the session cwd (subdir ../.env refused)",
             r.returncode == 2, r.stderr)
        r = fire(repo, cmd["pre-file-guard"], patch("*** Update File: src/a.ts", "@@", "+x"))
        case("an ordinary source edit passes", r.returncode == 0, r.stderr)

        # ── post-spec-guard through apply_patch (PostToolUse: the file is already written)
        write(repo, "specs/001-x/spec.md", SPEC.replace("rigor: production", "rigor: spike"))
        post = dict(patch("*** Update File: specs/001-x/spec.md", "@@", "-rigor: production",
                          "+rigor: spike"), hook_event_name="PostToolUse")
        r = fire(repo, cmd["post-spec-guard"], post)
        case("lowering rigor: in a patch is refused (exit 2) — mechanism, not promise",
             r.returncode == 2 and "rigor" in r.stderr, r.stderr)
        post_sub = dict(post, tool_input={"command": post["tool_input"]["command"]
                                          .replace("specs/001-x/", "001-x/")})
        r = fire(repo, cmd["post-spec-guard"], post_sub, cwd=sub)
        case("…and from inside specs/, where the patch path is 001-x/spec.md",
             r.returncode == 2, r.stderr)
        write(repo, "specs/001-x/spec.md", SPEC.replace("status: in-progress", "status: done"))
        r = fire(repo, cmd["post-spec-guard"], post)
        case("status: done written by hand is refused — only $wf-done may close",
             r.returncode == 2, r.stderr)
        git(repo, "checkout", "--", "specs/001-x/spec.md")
        r = fire(repo, cmd["post-spec-guard"], post)
        case("an unchanged lifecycle passes", r.returncode == 0, r.stderr)

        # ── Stop: drift (spec body changed, tasks.md not) ────────────────────────────
        write(repo, "specs/001-x/spec.md", SPEC + "- AC-2: another thing\n")
        stop = {"hook_event_name": "Stop", "stop_hook_active": False}
        r = fire(repo, cmd["stop-verify"], stop)
        case("Stop: a spec body change without tasks.md is drift (exit 2 → Codex continues)",
             r.returncode == 2, r.stderr)
        r = fire(repo, cmd["stop-verify"], dict(stop, stop_hook_active=True))
        case("Stop: stop_hook_active ends the loop (exit 0)", r.returncode == 0, r.stderr)
        git(repo, "checkout", "--", "specs/001-x/spec.md")

        # ── SessionStart: plain stdout is developer context on Codex ─────────────────
        r = fire(repo, cmd["session-start"], {"hook_event_name": "SessionStart",
                                              "source": "startup"}, cwd=sub)
        case("SessionStart prints the session context, from a subdirectory",
             r.returncode == 0 and "SESSION CONTEXT" in r.stdout, r.stdout + r.stderr)

        # ── packaging faults are loud, never a silent pass, never a block ────────────
        os.remove(os.path.join(repo, ".codex", "wellforge", "hooks", "scripts",
                               "pre-file-guard.sh"))
        r = fire(repo, cmd["pre-file-guard"], patch("*** Add File: .env", "+K=v"))
        case("a missing hook script exits 1 with a message (reported, not blocking)",
             r.returncode == 1 and "missing" in r.stderr, r.stderr)

        # ── regeneration is idempotent and keeps what the user owns ──────────────────
        with open(os.path.join(repo, ".codex", "config.toml"), "a") as fh:
            fh.write('\n[mcp_servers.mine]\ncommand = "my-server"\n')
        hooks_path = os.path.join(repo, ".codex", "hooks.json")
        doc = json.load(open(hooks_path))
        doc["hooks"].setdefault("Stop", []).append(
            {"hooks": [{"type": "command", "command": "echo mine"}]})
        json.dump(doc, open(hooks_path, "w"))
        write(repo, "AGENTS.md", open(os.path.join(repo, "AGENTS.md")).read() + "\nMy notes.\n")
        write(repo, ".agents/skills/my-skill/SKILL.md", "---\nname: my-skill\ndescription: x\n---\n")
        for _ in range(2):
            subprocess.run([sys.executable, GENERATOR, "--out", repo], check=True,
                           capture_output=True, env=ENV)
        cfg = open(os.path.join(repo, ".codex", "config.toml")).read()
        agents_md = open(os.path.join(repo, "AGENTS.md")).read()
        hooks = json.load(open(hooks_path))["hooks"]
        stop_cmds = [h["command"] for g in hooks["Stop"] for h in g["hooks"]]
        case("regenerate ×2: one WellForge block in config.toml, the user's server kept",
             cfg.count("# >>> wellforge") == 1 and "[mcp_servers.mine]" in cfg, cfg)
        case("regenerate ×2: one WellForge block in AGENTS.md, the user's notes kept",
             agents_md.count("wellforge-codex:start") == 1 and "My notes." in agents_md,
             agents_md)
        case("regenerate ×2: the user's Stop hook kept, ours present exactly once",
             "echo mine" in stop_cmds and sum("stop-verify" in c for c in stop_cmds) == 1,
             stop_cmds)
        case("regenerate ×2: a user skill in .agents/skills survives",
             os.path.isfile(os.path.join(repo, ".agents", "skills", "my-skill", "SKILL.md")))
        case("regenerate restores the deleted hook script",
             os.path.isfile(os.path.join(repo, ".codex", "wellforge", "hooks", "scripts",
                                         "pre-file-guard.sh")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\ncodex hooks: {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
