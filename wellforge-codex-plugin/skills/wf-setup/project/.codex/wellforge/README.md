# WellForge deterministic layer (codex)

Generated — do not edit by hand. Regenerate with `adapters/codex/generate.py`.

These are byte copies of `wellforge-plugin/scripts/` and `wellforge-plugin/config/` from the
WellForge plugin. The generated prompts invoke them as `$WF/scripts/<name>`, where `$WF` is
this directory.

| File | Used by |
|---|---|
| `wellforge/scripts/forge-state.py` | generated prompts and skills |
| `wellforge/scripts/run-report.py` | generated prompts and skills |
| `wellforge/scripts/security-triggers.py` | generated prompts and skills |
| `wellforge/scripts/migrate-ids.py` | generated prompts and skills |
| `wellforge/config/security-triggers.yml` | generated prompts and skills |
| `wellforge/config/rigor-budgets.yml` | generated prompts and skills |
| `wellforge/config/model-pricing.yml` | generated prompts and skills |
| `wellforge/config/spec-frontmatter.schema.json` | generated prompts and skills |
| `wellforge/PLUGIN-MIGRATIONS.md` | generated prompts and skills |

`forge-state.py` loads `run-report.py` from this same directory at runtime — they are one
unit, so do not prune either.

Requires `python3` with `pyyaml`, or `uv` (the prompts fall back to
`uv run --with pyyaml python`). `/wf-doctor` checks this.
