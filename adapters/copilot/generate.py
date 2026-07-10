#!/usr/bin/env python3
"""Generate a GitHub Copilot adapter (.github/ + .vscode/mcp.json) from the Claude Code plugin.

  generate.py --plugin <wellforge-plugin> --out <project-dir> [--provider anthropic]

Reads the plugin's agents/commands/skills + config/model-{routing,tiers}.yml and emits
Copilot-native files for VS Code. Option (b): the Claude Code plugin stays the source of
truth; this projects it onto Copilot's customization surface. The Claude→Copilot mapping:

  commands/*.md            -> .github/prompts/wf-*.prompt.md      (slash: /wf-spec)
  agents/*.md              -> .github/chatmodes/wf-*.chatmode.md  (mode picker: wf-architect)
  stack skills/*/SKILL.md  -> .github/instructions/wf-*.instructions.md  (applyTo: glob)
  workflow skills          -> .github/copilot-instructions.md (thin) + inlined into prompts
  .mcp.json                -> .vscode/mcp.json
  hooks                    -> lefthook.yml (git-hook fallback) — Copilot has no hook runtime

Copilot has NO hook runtime and NO parallel subagent dispatch, so enforcement leans on the
CI quality gates + a generated lefthook.yml, and orchestration degrades to a single-session
"wear each hat" chat mode. See adapters/copilot/README.md for the honest support-tier table.

Run via: uv run --with pyyaml python adapters/copilot/generate.py ...
"""
import argparse
import glob
import json
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml (uv run --with pyyaml)")


# Claude tool name -> Copilot built-in chat tools. Agents with NO `tools:` list get the full
# agentic set. MCP tools (e.g. playwright for designer/QE) are NOT enumerated here — they
# become available once .vscode/mcp.json is generated (step 5) and enabled in the mode.
_TOOL2COPILOT = {"read": ["codebase", "search", "usages"], "grep": ["search"],
                 "glob": ["search"], "write": ["editFiles"], "edit": ["editFiles"],
                 "bash": ["runCommands", "runTasks"], "webfetch": ["fetch"],
                 "websearch": ["fetch"]}
_ALL_COPILOT = ["codebase", "search", "usages", "editFiles", "runCommands", "runTasks",
                "runTests", "findTestFiles", "problems", "changes", "fetch", "githubRepo"]

# Skills that map to file paths -> a glob-scoped `.instructions.md` that auto-applies only
# when matching files are in context (Copilot has no on-demand skill loading, so scoping is
# how we avoid always-on bloat). `applyTo` takes a comma-separated glob list. Skills NOT here
# (connections, heartbeat, template-extraction, visual-companion) are command-scoped: copied
# to the library and referenced by their prompt, never auto-applied.
_SKILL_APPLY = {
    "react-ts-vite":       "**/*.tsx,**/*.jsx,**/*.css",
    "kotlin-springboot":   "**/*.kt,**/*.kts",
    "springboot-scaffold": "**/*.kt,**/*.kts,**/pom.xml",
    "hono-ts-backend":     "**/*.ts",
    "pulumi-gcp-ts":       "**/Pulumi*.yaml,**/index.ts,**/*.pulumi.ts",
    "mise":                "**/mise.toml,**/.mise.toml,**/mise.*.toml",
    "spec-driven":         "specs/**",
    "rigor-tiers":         "specs/**,.forge/**",
    "observability":       ".forge/**",
}


def split_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return {}, text
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


_AGENT_NAMES = []   # set in main(); lowercase agent ids (== filenames)


def translate(s):
    """Map Claude Code refs to the namespaced Copilot adapter:
       /wellforge:x -> /wf-x        (slash commands -> prompt files)
       wellforge:<agent> -> wf-<agent>   (namespaced dispatch refs)
       `<agent>` -> `wf-<agent>`    (any still-bare BACKTICK'd agent ref)
    NOTE: the `$ARGUMENTS` -> `${input:args}` substitution is prompt-file-only and lives in
    gen_prompts, not here — chat modes and instructions take no arguments."""
    s = s.replace("/wellforge:", "/wf-").replace("wellforge:", "wf-")
    bt = chr(96)
    for name in sorted(_AGENT_NAMES, key=len, reverse=True):   # longest first
        s = s.replace(f"{bt}{name}{bt}", f"{bt}wf-{name}{bt}")
    return s


# ── emit stage (Copilot-native) ─────────────────────────────────────────────────────────
# Implemented incrementally per docs/PLAN-copilot-adapter.md build order. Each returns a
# count for the summary line. Stubs below are filled in by the noted step.

def gen_prompts(plugin, out):
    """commands/*.md -> .github/prompts/wf-*.prompt.md.

    Copilot prompt files are invoked as `/wf-<name>` in chat. `mode: agent` — these are
    multi-step workflow commands that read/write files and run tools. The Claude `$ARGUMENTS`
    placeholder becomes Copilot's `${input:args}` variable, seeded with the command's
    `argument-hint` as the input-box placeholder. Commands carry NO `model:` — they run in
    the user's current session/model, not a routed agent (parity with the OpenCode adapter).

    Frontmatter is regex-scraped, not YAML-parsed: `argument-hint` values contain
    `[brackets]`, `|`, and dashes that aren't strict YAML (same reason as OpenCode's
    gen_commands).
    """
    d = os.path.join(out, ".github", "prompts")
    os.makedirs(d, exist_ok=True)
    n = 0
    for fp in sorted(glob.glob(os.path.join(plugin, "commands", "*.md"))):
        text = open(fp).read()
        mm = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
        fm_text, body = (mm.group(1), mm.group(2)) if mm else ("", text)
        name = os.path.splitext(os.path.basename(fp))[0]
        dm = re.search(r"^description:\s*(.+)$", fm_text, re.M)
        desc = translate(" ".join(dm.group(1).split())) if dm else name
        hm = re.search(r"^argument-hint:\s*(.+)$", fm_text, re.M)
        # placeholder text runs to the closing `}`; strip braces so it can't break the var
        hint = " ".join(hm.group(1).split()).replace("{", "").replace("}", "") if hm else ""
        arg_var = f"${{input:args:{hint}}}" if hint else "${input:args}"
        body = translate(body).replace("$ARGUMENTS", arg_var)
        fm = yaml.safe_dump({"mode": "agent", "description": desc},
                            sort_keys=False, allow_unicode=True, width=4096).strip()
        with open(os.path.join(d, f"wf-{name}.prompt.md"), "w") as f:
            f.write("---\n" + fm + "\n---\n" + body)
        n += 1
    return n


def tools_for(tools, disallowed=None):
    """Map a Claude agent's tool access to a Copilot chat-mode `tools` allowlist.

    `tools` = the Claude allowlist (None → full agentic set). `disallowed` = a Claude
    deny-list. A disallowed tool's Copilot tool is dropped ONLY when no still-allowed Claude
    tool also maps to it — Copilot's `editFiles` covers both Claude `Write` and `Edit`, so
    denying `Edit` must not strip `Write` (designer keeps `editFiles`, relying on its prompt).
    Un-representable denials are noted on stderr, never silently dropped.
    """
    disallowed = {t.lower() for t in (disallowed or [])}
    if not tools:
        selected = list(_ALL_COPILOT)
        available = set(_TOOL2COPILOT)
    else:
        available = {t.lower() for t in tools}
        selected = []
        for t in tools:
            for ct in _TOOL2COPILOT.get(t.lower(), []):
                if ct not in selected:
                    selected.append(ct)
    for t in disallowed:
        for ct in _TOOL2COPILOT.get(t, []):
            still_needs = any(ct in _TOOL2COPILOT.get(a, []) for a in available
                              if a != t and a not in disallowed)
            if still_needs:
                print(f"note: Copilot can't deny '{t}' here — tool '{ct}' is shared with "
                      f"another allowed tool (e.g. Write); relying on the chat-mode prompt",
                      file=sys.stderr)
            elif ct in selected:
                selected.remove(ct)
    return selected


def gen_chatmodes(plugin, out, models):
    """agents/*.md -> .github/chatmodes/wf-*.chatmode.md.

    Each Claude subagent becomes a Copilot custom chat mode (mode picker: `wf-architect`),
    carrying its persona (body), a routed `model` (routing tier × the copilot provider), and
    a `tools` allowlist mapped from the Claude `tools:`/`disallowedTools:`. Copilot cannot
    spawn/parallelise subagents, so orchestration bodies degrade to single-session guidance —
    the honest gap documented in the README.
    """
    d = os.path.join(out, ".github", "chatmodes")
    os.makedirs(d, exist_ok=True)
    n = 0
    for fp in sorted(glob.glob(os.path.join(plugin, "agents", "*.md"))):
        fm, body = split_frontmatter(open(fp).read())
        name = fm.get("name") or os.path.splitext(os.path.basename(fp))[0]
        desc = translate(" ".join((fm.get("description") or "").split()))
        mode_fm = {"description": desc,
                   "model": models.get(name, models["_default"]),
                   "tools": tools_for(fm.get("tools"), fm.get("disallowedTools"))}
        with open(os.path.join(d, f"wf-{name}.chatmode.md"), "w") as f:
            f.write("---\n" + yaml.safe_dump(mode_fm, sort_keys=False, allow_unicode=True,
                                             width=4096).strip() + "\n---\n" + translate(body))
        n += 1
    return n


_ROOT_INSTRUCTIONS = """\
# WellForge — repository AI guide (GitHub Copilot)

This repo uses the **WellForge** spec-driven workflow. Copilot is set up with matching
prompts, chat modes, and instructions generated from the WellForge plugin.

## Workflow
Idea → `/wf-spec` → `/wf-plan` → (`/wf-design` for UI) → `/wf-tasks` → `/wf-implement`, then
verify with QE and `/wf-done`. `/wf-orchestrate` runs the whole flow; `/wf-spike` is the fast
lane for throwaway prototypes. All commands live in `.github/prompts/` (invoke as `/wf-*`).

## Roles (chat modes)
Switch the chat-mode picker to a `wf-*` role for focused work: `wf-product-owner` (spec),
`wf-architect` (plan), `wf-designer` (UX), `wf-frontend-dev` / `wf-backend-dev` (build),
`wf-devops` (CI/infra), `wf-quality-engineer` (verify), `wf-evaluator` (LM-judge),
`wf-owasp-reviewer` (security), `wf-adr-writer` (decision records).
NOTE: Copilot runs ONE chat mode at a time — it cannot spawn parallel subagents, so
orchestration is sequential (switch modes yourself as the flow progresses).

## Stack conventions
Stack + workflow guidance auto-applies by file type via
`.github/instructions/*.instructions.md` (e.g. editing `*.kt` loads the Spring Boot Kotlin
conventions). The full skills — with their `references/` deep-dives — live in
`.github/wf-skills/<name>/`; open the relevant `SKILL.md` before non-trivial work.

## Quality floor (all work, non-negotiable)
No secrets/credentials in code; dependency audit on critical CVEs; lint + type-check + tests
must pass before "done". Gates run in CI (`.github/workflows/`) and locally via the generated
git hooks (`lefthook.yml`). Never weaken a gate to make code pass.
"""


def _essence(body):
    """H1 + intro blurb of a SKILL.md — everything up to the first `## ` section."""
    b = body.strip()
    idx = b.find("\n## ")
    return (b[:idx] if idx != -1 else b).strip()


def gen_instructions(plugin, out):
    """Skills -> Copilot instructions + a skill library.

    Two outputs:
    - `.github/wf-skills/<name>/` — the FULL skill (SKILL.md + references/ + scripts/),
      refs translated. The knowledge base agents/prompts read on demand; never auto-loaded.
    - `.github/instructions/wf-<name>.instructions.md` — for path-mappable skills only
      (`_SKILL_APPLY`): a lean `applyTo`-scoped file carrying the skill's essence + a pointer
      to the library. Loads only when matching files are in context (the anti-bloat move).
    Also writes a thin `.github/copilot-instructions.md` (repo-wide guide).

    Returns the number of `.instructions.md` files written (for the summary line).
    """
    src = os.path.join(plugin, "skills")
    if not os.path.isdir(src):
        return 0

    # 1. copy the full skill library, translating refs in markdown
    lib = os.path.join(out, ".github", "wf-skills")
    if os.path.isdir(lib):
        shutil.rmtree(lib)
    shutil.copytree(src, lib)
    n_lib = 0
    for root, _, files in os.walk(lib):
        for fn in files:
            if fn.endswith(".md"):
                p = os.path.join(root, fn)
                open(p, "w").write(translate(open(p).read()))
                n_lib += 1

    # 2. glob-scoped instruction pointers for path-mappable skills
    d = os.path.join(out, ".github", "instructions")
    os.makedirs(d, exist_ok=True)
    n_inst = 0
    for name, apply_to in _SKILL_APPLY.items():
        skill_md = os.path.join(src, name, "SKILL.md")
        if not os.path.exists(skill_md):
            print(f"note: skill '{name}' in _SKILL_APPLY has no SKILL.md — skipped",
                  file=sys.stderr)
            continue
        fm, body = split_frontmatter(open(skill_md).read())
        desc = translate(" ".join((fm.get("description") or name).split()))
        essence = translate(_essence(body))
        head = yaml.safe_dump({"applyTo": apply_to, "description": desc},
                              sort_keys=False, allow_unicode=True, width=4096).strip()
        pointer = (f"\n\n**Full reference:** follow `.github/wf-skills/{name}/SKILL.md` and "
                   f"its `references/` for the complete conventions. Load it before "
                   f"non-trivial work matching `{apply_to}`.\n")
        with open(os.path.join(d, f"wf-{name}.instructions.md"), "w") as f:
            f.write("---\n" + head + "\n---\n" + essence + pointer)
        n_inst += 1

    # 3. thin repo-wide guide
    with open(os.path.join(out, ".github", "copilot-instructions.md"), "w") as f:
        f.write(_ROOT_INSTRUCTIONS)

    print(f"  instructions: {n_inst} scoped + copilot-instructions.md; "
          f"library: {n_lib} skill md files in .github/wf-skills/", file=sys.stderr)
    return n_inst


def gen_mcp(plugin, out):
    """.mcp.json -> .vscode/mcp.json.

    Near-1:1: VS Code keys the map `servers` (Claude uses `mcpServers`); each entry's shape
    (`type` + `command`/`args`/`env` for stdio, `url`/`headers` for http|sse) is the same.
    Merges into any existing .vscode/mcp.json so a user's own servers aren't clobbered.
    """
    srcf = os.path.join(plugin, ".mcp.json")
    if not os.path.exists(srcf):
        return 0
    servers = {}
    for name, cfg in json.load(open(srcf)).get("mcpServers", {}).items():
        t = cfg.get("type") or ("http" if cfg.get("url") else "stdio")
        if t in ("http", "sse") or cfg.get("url"):
            entry = {"type": "sse" if t == "sse" else "http", "url": cfg.get("url")}
            if cfg.get("headers"):
                entry["headers"] = cfg["headers"]
        else:
            entry = {"type": "stdio", "command": cfg.get("command", "npx"),
                     "args": cfg.get("args", [])}
            if cfg.get("env"):
                entry["env"] = cfg["env"]
        servers[name] = entry
    d = os.path.join(out, ".vscode")
    os.makedirs(d, exist_ok=True)
    outf = os.path.join(d, "mcp.json")
    existing = json.load(open(outf)) if os.path.exists(outf) else {}
    existing["servers"] = {**existing.get("servers", {}), **servers}
    with open(outf, "w") as f:
        json.dump(existing, f, indent=2)
        f.write("\n")
    return len(servers)


def gen_githooks(out):
    """Copy the static lefthook.yml enforcement fallback to the project root.

    Copilot has no hook runtime, so the high-value LOCAL hooks (secret-scan, post-lint,
    spec-drift, compile checks) are ported to git hooks. The file is static (not derived) —
    it lives in adapters/copilot/githooks/. Merges nothing: if a lefthook.yml already exists
    it is LEFT ALONE (the user owns it) and we note it, rather than clobbering their config.
    """
    src = os.path.join(os.path.dirname(__file__), "githooks", "lefthook.yml")
    if not os.path.exists(src):
        return 0
    dst = os.path.join(out, "lefthook.yml")
    if os.path.exists(dst):
        print(f"note: {dst} exists — left as-is; see adapters/copilot/githooks/lefthook.yml "
              f"to merge the WellForge gates manually", file=sys.stderr)
        return 0
    shutil.copy(src, dst)
    return 1


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(__file__)
    ap.add_argument("--plugin", default=os.path.join(here, "..", "..", "wellforge-plugin"))
    ap.add_argument("--out", required=True, help="target project dir (.github/ written here)")
    ap.add_argument("--provider", default="anthropic")
    args = ap.parse_args()

    cfg = os.path.join(args.plugin, "config")
    routing = yaml.safe_load(open(os.path.join(cfg, "model-routing.yml")))
    tiers_all = yaml.safe_load(open(os.path.join(cfg, "model-tiers.yml")))["tools"]["copilot"]
    if args.provider not in tiers_all:
        sys.exit(f"provider '{args.provider}' not in copilot tiers (have: {', '.join(tiers_all)})")
    tiers = tiers_all[args.provider]
    models = {a: tiers[s["tier"]] for a, s in routing["agents"].items()}
    models["_default"] = tiers["mid"]   # unlisted agents (e.g. designer) → mid

    # agent ids (== filenames) → drive the wf- ref translation in bodies/prompts
    _AGENT_NAMES[:] = [os.path.splitext(os.path.basename(f))[0]
                       for f in __import__("glob").glob(os.path.join(args.plugin, "agents", "*.md"))]

    p = gen_prompts(args.plugin, args.out)
    cm = gen_chatmodes(args.plugin, args.out, models)
    i = gen_instructions(args.plugin, args.out)
    m = gen_mcp(args.plugin, args.out)
    g = gen_githooks(args.out)
    print(f"✓ Copilot adapter ({args.provider}) → {args.out}/.github/")
    print(f"  {p} prompts · {cm} chat modes · {i} instruction files · {m} MCP servers · {g} githook config")
    print("  NOT ported: token-trace observability (no Copilot event) and parallel subagent")
    print("  dispatch — covered by the CI quality gates; orchestration degrades to a single")
    print("  'wear each hat' chat mode. See adapters/copilot/README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
