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

# ── the filenames the globs miss ────────────────────────────────────────────────
# `auth/**` needs a DIRECTORY called auth. Measured before path_contains gained these:
# every one of the six below reported "no trigger matched" at mvp — six of the most
# security-sensitive filenames a project can have, skipped for where they sat rather than
# what they were.
for path in ("src/Authorization.kt", "src/OAuthClient.ts", "src/rbac/policy.ts",
             "src/jwt/verify.ts", "src/crypto/hash.ts", "src/permissions/check.ts",
             "src/SessionStore.ts"):
    r = st.evaluate("mvp", [], [path], CFG)
    check(f"{path} dispatches at mvp", r["dispatch"], True)

# The accepted false positive, asserted so it is a decision and not a surprise.
r = st.evaluate("mvp", [], ["src/authors/list.ts"], CFG)
check("`auth` also matches `author` — known, accepted", r["dispatch"], True)

# Something genuinely inert must still not dispatch, or the list means nothing.
r = st.evaluate("mvp", [], ["src/ui/Button.tsx", "README.md"], CFG)
check("ordinary files do not dispatch at mvp", r["dispatch"], False)

# ── touch globs are globs, not literal paths ────────────────────────────────────
# `src/**` covers src/auth/login.ts but names no trigger, so a literal match missed it and
# a batch declaring the broader glob was never reviewed.
import shutil
import subprocess
import tempfile

repo = tempfile.mkdtemp()
os.makedirs(os.path.join(repo, "src", "auth"))
open(os.path.join(repo, "src", "auth", "login.ts"), "w").write("x\n")
open(os.path.join(repo, "src", "Button.tsx"), "w").write("x\n")

r = st.evaluate("mvp", ["src/**"], [], CFG, repo)
check("a broad touch glob expands and triggers on what it covers", r["dispatch"], True)
check("...and the matched path is the real file, not the glob",
      r["matches"][0]["path"].replace(os.sep, "/"), "src/auth/login.ts")
check("...and the source names the glob it came from",
      r["matches"][0]["source"], "touch:src/**")

r = st.evaluate("mvp", ["src/*"], [], CFG, repo)
check("a single-level glob does not reach into subdirectories", r["dispatch"], False)

# The intent half still works with no working tree at all: a glob naming a trigger
# dispatches before the code exists.
r = st.evaluate("mvp", ["**/auth/**"], [], CFG, "/nonexistent-repo")
check("a declared trigger glob still fires with no files on disk", r["dispatch"], True)

# ── a diff we could not read is not a diff that found nothing ───────────────────
subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True)
for k, v in (("user.email", "t@t"), ("user.name", "T"), ("commit.gpgsign", "false")):
    subprocess.run(["git", "-C", repo, "config", k, v], check=True, capture_output=True)
subprocess.run(["git", "-C", repo, "add", "-A"], check=True, capture_output=True)
subprocess.run(["git", "-C", repo, "commit", "-qm", "f"], check=True, capture_output=True)

files, err = st.git_changed("HEAD", repo)
check("a good ref reports no error", err, None)

files, err = st.git_changed("no-such-ref-xyz", repo)
check("a bad ref returns an error instead of an empty list", bool(err), True)
check("...and names the ref", "no-such-ref-xyz" in (err or ""), True)

r = st.evaluate("mvp", [], [], CFG, repo, err)
check("an unreadable diff dispatches rather than reading as 'nothing matched'",
      r["dispatch"], True)
check("...and carries the note", "no-such-ref-xyz" in r.get("note", ""), True)
check("...and says so in the reason", "could not determine" in r["reason"], True)

# End to end, because the exit code is the part a caller actually sees.
out = subprocess.run([sys.executable, os.path.join(HERE, "..", "security-triggers.py"),
                      "--tier", "mvp", "--diff-base", "no-such-ref-xyz", "--repo", repo],
                     capture_output=True, text=True)
check("a bad --diff-base exits non-zero", out.returncode, 2)
check("...and prints DISPATCH", "DISPATCH" in out.stdout, True)

shutil.rmtree(repo, ignore_errors=True)

print(f"\nsecurity-triggers: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
