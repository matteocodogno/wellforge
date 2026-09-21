"""Ship the deterministic layer into an adapter's output, and repoint the prompts at it.

THE GAP THIS CLOSES
Seven generated prompts — status, done, triage, promote, implement, orchestrate, doctor —
plus the quality-gates and rigor-tiers skills tell the reader to run `forge-state.py`,
`run-report.py` and `security-triggers.py`, and to consult `config/rigor-budgets.yml` and
`config/security-triggers.yml`. Neither generator copied any of them, so every one of those
instructions pointed at a file that did not exist in the output. Nothing noticed, because
`smoke-test.py` inventoried commands, agents and skills — not the paths those artifacts
reference.

The prompts also carried the Claude-specific root resolution, which reads
`~/.claude/plugins/installed_plugins.json`. In a Copilot or OpenCode checkout that file is
absent or belongs to an unrelated install, so the fallback silently pointed `$WF` at
`<cwd>/wellforge-plugin` — a directory that does not exist in a generated project either.

So: copy the scripts and configs under a tool-specific root, and replace the resolution
preamble with a plain assignment to that root. `$WF` keeps its name, so the body of every
prompt is unchanged and the two trees stay easy to diff.
"""
import os
import re
import shutil

# The scripts a generated prompt may invoke. check-docs/check-routing/check-budget are
# repo-maintenance tools for THIS repository and are deliberately not shipped: a generated
# project has no plugin README to check against, and shipping them would invite someone to
# run a guard that cannot pass.
SCRIPTS = ("forge-state.py", "run-report.py", "security-triggers.py")

# Configs the prompts and skills cite by path.
CONFIGS = ("security-triggers.yml", "rigor-budgets.yml", "model-pricing.yml",
           "spec-frontmatter.schema.json")

# The Claude-only preamble, as commands/*.md carry it. Matched loosely (the comment wording
# changes more often than the code) but anchored on both assignments, so a partial match
# cannot leave half a preamble behind.
_PREAMBLE = re.compile(
    r"(?:^[ \t]*#[^\n]*\n)*"                       # leading comment block
    r"^[ \t]*WF=\$\(python3 -c[^\n]*\n"            # the installed_plugins.json lookup
    r"(?:^[ \t]*#[^\n]*\n)*"                       # its explanatory comment
    r"^[ \t]*\[ -n \"\$WF\" \] \|\| WF=[^\n]*\n",  # the checkout fallback
    re.M)


def repoint(text, root_expr, tool):
    """Replace the Claude plugin-root resolution with `root_expr`.

    Returns (text, n) so a caller can assert that a prompt which references $WF actually
    had its preamble rewritten — a silent no-op here would ship a prompt that resolves the
    root the Claude way in a tool that has no Claude install.
    """
    replacement = (
        f"# The deterministic layer ships INSIDE this repository for {tool}; there is no\n"
        f"# plugin install to resolve. `wf-doctor` checks that python3 + pyyaml (or uv) can\n"
        f"# run it.\n"
        f"WF={root_expr}\n")
    text, n = _PREAMBLE.subn(lambda _m: replacement, text)
    return text, n


def needs_repoint(text):
    """Does this body reference the deterministic layer at all?"""
    return "$WF/" in text or "wfpy " in text


def ship(plugin, out, root_rel):
    """Copy scripts/ and config/ into <out>/<root_rel>/. Returns the list of written paths."""
    written = []
    for kind, names in (("scripts", SCRIPTS), ("config", CONFIGS)):
        src_dir = os.path.join(plugin, kind)
        dst_dir = os.path.join(out, root_rel, kind)
        os.makedirs(dst_dir, exist_ok=True)
        for name in names:
            src = os.path.join(src_dir, name)
            if not os.path.exists(src):
                continue
            dst = os.path.join(dst_dir, name)
            shutil.copyfile(src, dst)
            if name.endswith(".py"):
                os.chmod(dst, 0o755)
            written.append(os.path.join(root_rel, kind, name))

    # forge-state.py imports run-report.py by path from its own directory, so the two must
    # land together — they do, but say so where someone might prune the list.
    readme = os.path.join(out, root_rel, "README.md")
    os.makedirs(os.path.dirname(readme), exist_ok=True)
    with open(readme, "w", encoding="utf-8") as f:
        f.write(f"""# WellForge deterministic layer ({tool_of(root_rel)})

Generated — do not edit by hand. Regenerate with `adapters/{tool_of(root_rel)}/generate.py`.

These are byte copies of `wellforge-plugin/scripts/` and `wellforge-plugin/config/` from the
WellForge plugin. The generated prompts invoke them as `$WF/scripts/<name>`, where `$WF` is
this directory.

| File | Used by |
|---|---|
{os.linesep.join(f"| `{p.split('/', 1)[1]}` | generated prompts and skills |" for p in written)}

`forge-state.py` loads `run-report.py` from this same directory at runtime — they are one
unit, so do not prune either.

Requires `python3` with `pyyaml`, or `uv` (the prompts fall back to
`uv run --with pyyaml python`). `/wf-doctor` checks this.
""")
    written.append(os.path.join(root_rel, "README.md"))
    return written


def tool_of(root_rel):
    return "copilot" if root_rel.startswith(".github") else "opencode"
