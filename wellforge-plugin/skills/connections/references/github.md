# GitHub — repo, protection, secrets

All via `gh` CLI. Pre-check: `gh auth status` (needs repo + admin scopes for protection).

## 1. Repository

```bash
# Verify first (idempotency)
gh repo view <org>/<slug> --json name,defaultBranchRef 2>/dev/null

# Create (private by default for WellForge projects) + push
gh repo create <org>/<slug> --private --source . --remote origin --push
```

**Verify:** `gh repo view <org>/<slug> --json name,visibility,defaultBranchRef`
→ name matches, visibility `PRIVATE`, default branch `main`.

## 2. Merge strategy (linear history — mandatory)

Every WellForge repo keeps a **linear history**: no merge commits, ever. Disable the merge
button and leave squash + rebase (`gates/README.md` → "Linear history gate").

```bash
gh api -X PATCH "repos/<org>/<slug>" \
  -F allow_merge_commit=false \
  -F allow_squash_merge=true \
  -F allow_rebase_merge=true \
  -F delete_branch_on_merge=true
```

**Verify:** `gh api repos/<org>/<slug> --jq '{merge: .allow_merge_commit, squash: .allow_squash_merge, rebase: .allow_rebase_merge}'`
→ `merge: false`. If it is `true`, the linear-history policy is one click from being broken.

## 3. Branch protection (main)

Standard WellForge policy: PRs only, 1 approval, gates must pass, linear history, no force push.

```bash
gh api -X PUT "repos/<org>/<slug>/branches/main/protection" \
  -H "Accept: application/vnd.github+json" \
  --input - <<'JSON'
{
  "required_status_checks": { "strict": true, "contexts": ["quality", "commits", "linear-history"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 1 },
  "required_linear_history": true,
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false
}
JSON
```

Note: the status-check contexts must match the job names in the generated
`.github/workflows/quality.yml`. Check the workflow file first; adjust contexts to the
actual job names.

**Verify:** `gh api repos/<org>/<slug>/branches/main/protection --jq '{checks: .required_status_checks.contexts, reviews: .required_pull_request_reviews.required_approving_review_count, linear: .required_linear_history.enabled}'`
→ `linear: true`.

Then tell the team to run the local half once per clone (config is per-clone, not committed):
`git config merge.ff only && git config pull.rebase true`.

## 4. CI secrets & variables

The gate workflows need no secrets by default (lint/test/coverage run self-contained).
Add only what the project actually uses:

```bash
# From env var or file — never inline literals
gh secret set SONAR_TOKEN --body "$SONAR_TOKEN"          # if Sonar is adopted
gh secret set REGISTRY_PASSWORD < /path/to/secret        # if publishing images
gh variable set REGISTRY_URL --body "ghcr.io/<org>"
```

**Verify:** `gh secret list && gh variable list` → expected names present (values are
never shown — that's correct).

## Common failures

| Symptom | Fix |
|---|---|
| `protection` 404 | repo is personal, not org — protection API needs the right plan/permissions; do it in the UI and verify via API |
| status check never required | contexts don't match job names — read the workflow, use exact job name |
| `gh auth status` missing scopes | `gh auth refresh -s repo,admin:repo_hook` |
