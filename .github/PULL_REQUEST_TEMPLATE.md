## What and why

<!-- One paragraph. What changes, and what was wrong or missing before. -->

## Series

<!-- Which tag series does this bump? template vX.Y.Z / gates-vN / plugin-vX.Y.Z / cli-vX.Y.Z,
     or "none — repo-level docs". Never two series on one commit (docs/VERSIONING.md). -->

## Checklist

- [ ] `mise run check` is green (paste the summary line)
- [ ] `check-docs.py` is green
- [ ] a regression case covers the behaviour, and I saw it **fail** before the fix
- [ ] migrations entry added, or not needed (would a project set up by the older version be
      wrong, incomplete or noisy under this one?)
- [ ] adapters regenerated if the plugin's prompts changed (never hand-edited)
- [ ] Conventional Commits, linear history (no merge commits)

## Security

- [ ] this change does **not** touch a guard, a hook, `.mcp.json`, or what an agent may read
      or run — **or** it does, and I have said how below

<!-- CONTRIBUTING.md has the detail. SECURITY.md has the threat model. -->
