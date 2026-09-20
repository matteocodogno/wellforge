#!/usr/bin/env python3
"""Fixture matrix for security-triggers.py — which paths pull in the owasp-reviewer.

The whole point of the config is that the dispatch stops depending on someone remembering.
That only holds if the matching is right, and glob matching is exactly the kind of thing
that looks right and silently misses `migrations/001.sql` because the pattern said `**/`.

Run: uv run --with pyyaml python wellforge-plugin/scripts/tests/security-triggers.test.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("st", os.path.join(HERE, "..", "security-triggers.py"))
st = importlib.util.module_from_spec(spec)
spec.loader.exec_module(st)
CFG = st.load_config()

passed = failed = 0


def check(desc, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"  FAIL: {desc}\n        want {want!r}\n        got  {got!r}")


def matches(path):
    return st.match_path(path, CFG) is not None


print("security-triggers matrix")
print(f"  config: {len(CFG['patterns'])} globs, {len(CFG['path_contains'])} substrings")

# ── paths that MUST pull in a review ────────────────────────────────────────────
for p in [
    "auth/login.ts", "backend/auth/JwtFilter.kt", "frontend/src/auth/useSession.ts",
    "backend/src/security/CorsConfig.kt", "src/security/policy.ts",
    "backend/src/main/kotlin/com/acme/api/OrderController.kt",
    "backend/src/main/java/com/acme/UserController.java",
    "backend/src/routes/orders.ts", "routes/index.ts",
    "backend/src/middleware/error-handler.ts", "middleware/rate-limit.ts",
    "backend/src/handlers/webhook.ts",
    "backend/db/changelog/003-add-users.xml", "db/changelog/init.xml",
    "backend/migrations/0007_add_index.sql", "migrations/001_init.sql",
    "scripts/seed.sql", "backend/src/db/queries.sql",
    # substring rules — named after what they handle
    "src/features/upload/Dropzone.tsx", "api/payment/stripe.ts",
    "lib/token-store.ts", "src/session/refresh.ts",
    "src/PasswordReset.tsx", "internal/secrets_loader.go", "src/credentialCache.ts",
]:
    check(f"triggers: {p}", matches(p), True)

# ── paths that must NOT (otherwise every batch dispatches and the signal dies) ──
for p in [
    "frontend/src/components/Button.tsx", "README.md", "docs/PLAN.md",
    "backend/src/main/kotlin/com/acme/domain/Order.kt",
    "frontend/src/hooks/useDebounce.ts", "mise.toml", "package.json",
    "backend/src/service/ReportExporter.kt", "src/utils/format-date.ts",
    "specs/001-x/spec.md", "e2e/checkout.spec.ts",
]:
    check(f"quiet: {p}", matches(p), False)

# ── the case a naive `**/` glob misses: a top-level match ───────────────────────
check("top-level migrations/ matches despite the **/ prefix", matches("migrations/001.sql"), True)
check("top-level routes/ matches", matches("routes/api.ts"), True)
check("case-insensitive", matches("BACKEND/AUTH/Login.KT"), True)

# ── tier behaviour ──────────────────────────────────────────────────────────────
r = st.evaluate("production", [], ["src/ui/Button.tsx"], CFG)
check("production reviews every batch", r["dispatch"], True)
check("...and says why", r["reason"], "tier is in always_at_tier")
check("...with no false matches listed", r["matches"], [])

r = st.evaluate("mvp", [], ["src/ui/Button.tsx"], CFG)
check("mvp with no match does not dispatch", r["dispatch"], False)
r = st.evaluate("mvp", ["backend/src/routes/**"], ["src/ui/Button.tsx"], CFG)
check("mvp dispatches on a touch: match", r["dispatch"], True)
check("...scoped to the matched path", r["scope"], ["backend/src/routes/**"])
r = st.evaluate("spike", [], ["auth/login.ts"], CFG)
check("spike still dispatches on a real match", r["dispatch"], True)

# ── both halves of the union are consulted ──────────────────────────────────────
r = st.evaluate("mvp", ["backend/src/service/**"], ["backend/migrations/002.sql"], CFG)
check("a file nobody declared still triggers (diff half)", r["dispatch"], True)
check("...and the source is recorded", r["matches"][0]["source"], "diff")
r = st.evaluate("mvp", ["**/auth/**"], [], CFG)
check("a declared glob triggers before any code exists (touch half)", r["dispatch"], True)
check("...and the source is recorded", r["matches"][0]["source"], "touch:")

# ── failing safe ────────────────────────────────────────────────────────────────
check("a missing config yields no rules rather than crashing", st.load_config("/nonexistent.yml"), None)

print(f"\nsecurity-triggers: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
