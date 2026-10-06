#!/usr/bin/env python3
"""check-docs.py and the Formula's placeholder sha — the rule a CLI release depends on.

The Formula pins the sha256 of GitHub's generated tarball, and that tarball does not exist
until the `cli-v*` tag is pushed. So the commit a CLI tag points at can only ever carry a
PLACEHOLDER sha: the real one lands in the commit after it. check-docs.py used to fail a
placeholder the moment the tag was on the remote — which is the state of the tagged commit
itself, in CI, on every release. `release-guard` then refused the tag: the release path
could not produce a green tag at all, and `cli-v1.5.1` was indeed cut from a red tree.

The rule that holds, pinned here against a real clone with a real remote:

  placeholder, tag not on the remote          → pass (an unreleased formula is a true state)
  placeholder, tag on the remote, HEAD IS it  → pass (the release commit; it cannot be otherwise)
  placeholder, tag on the remote, HEAD past it → FAIL (the formula commit never landed)

Run: python3 wellforge-plugin/scripts/tests/check-docs-formula.test.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
passed = failed = 0

# The suite must not inherit the developer's git config (hooks path, signing, templates).
ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
           WELLFORGE_SKIP_SHA_VERIFY="1")
ENV.pop("GITHUB_REF", None)


def git(cwd, *args, check=True):
    r = subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@t",
                        "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
                       capture_output=True, text=True, env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def check_docs(repo, **extra):
    cmd = [sys.executable, os.path.join(repo, "wellforge-plugin", "scripts", "check-docs.py")]
    r = subprocess.run(cmd, capture_output=True, text=True, env=dict(ENV, **extra),
                       cwd=os.path.join(repo, "wellforge-plugin"))
    return r.returncode, r.stdout + r.stderr


def case(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok    {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")
        for line in detail.strip().splitlines()[-12:]:
            print(f"          {line}")


def main():
    tmp = tempfile.mkdtemp(prefix="wf-docs-formula-")
    try:
        repo, bare = os.path.join(tmp, "repo"), os.path.join(tmp, "origin.git")
        subprocess.run(["git", "clone", "-q", "--no-tags", ROOT, repo], check=True, env=ENV,
                       capture_output=True)
        # The clone is HEAD; the code under test is the WORKING TREE's check-docs.py and the
        # files it reads, so carry the uncommitted versions across.
        for rel in ("wellforge-plugin/scripts/check-docs.py", "scripts/wellforge",
                    "Formula/wellforge.rb", "CLAUDE.md"):
            shutil.copyfile(os.path.join(ROOT, rel), os.path.join(repo, rel))
        subprocess.run(["git", "init", "-q", "--bare", bare], check=True, env=ENV)
        # CI checks out with depth 1, so the clone above is shallow, and a bare repository
        # refuses a push from one ("shallow update not allowed") unless told otherwise.
        # Found before it reached CI, by running this suite from a `--depth 1` clone.
        subprocess.run(["git", "-C", bare, "config", "receive.shallowUpdate", "true"],
                       check=True, env=ENV)
        git(repo, "remote", "set-url", "origin", bare)
        git(repo, "checkout", "-q", "-B", "main")

        cli = open(os.path.join(repo, "scripts", "wellforge")).read()
        ver = re.search(r'^WELLFORGE_CLI_VERSION="([^"]+)"', cli, re.M).group(1)
        tag = f"cli-v{ver}"

        # The release commit: the url names the tag, the sha is the placeholder.
        fpath = os.path.join(repo, "Formula", "wellforge.rb")
        f = open(fpath).read()
        f, n = re.subn(r'sha256 "[0-9a-f]{64}"', 'sha256 "' + "0" * 64 + '"', f, count=1)
        assert n == 1, "fixture: no sha256 line to blank"
        open(fpath, "w").write(f)
        git(repo, "add", "-A")
        # --allow-empty: when this suite runs ON a release commit (CI on the tag, or the
        # release script's own gate), HEAD already carries the placeholder and there is
        # nothing to commit. Found by rehearsing a release: the gate died right here.
        git(repo, "commit", "-q", "--allow-empty", "-m", "chore(cli): release (fixture)")
        git(repo, "push", "-q", "origin", "main")

        rc, out = check_docs(repo)
        case("placeholder, tag not on the remote: passes, and says so",
             rc == 0 and "placeholder" in out, out)

        # ── mid-release: the constant is ahead of the newest tag, by design ──────────
        # release-cli.sh bumps, proves the bumped tree, and only then cuts the tag. In that
        # window "newest cli tag == the constant" is false and must stay false for anyone
        # else — an untagged bump reaches nobody — but not for the release that is about
        # to cut exactly that tag. The rehearsal of this very fix stopped here.
        git(repo, "tag", "cli-v0.0.1")
        rc, out = check_docs(repo)
        case("constant ahead of the newest tag: fails",
             rc != 0 and "newest cli tag" in out, out)
        rc, out = check_docs(repo, WELLFORGE_RELEASING=ver)
        case("…unless WELLFORGE_RELEASING names exactly that version",
             rc == 0, out)
        rc, out = check_docs(repo, WELLFORGE_RELEASING="9.9.9")
        case("…and a WELLFORGE_RELEASING that names another version does not excuse it",
             rc != 0 and "newest cli tag" in out, out)
        git(repo, "tag", "-d", "cli-v0.0.1")

        for kind, tagargs in (("annotated", ["-a", tag, "-m", "fixture"]), ("lightweight", [tag])):
            git(repo, "tag", "-f", *tagargs)
            git(repo, "push", "-q", "-f", "origin", tag)
            rc, out = check_docs(repo)
            case(f"placeholder, {kind} tag on the remote, HEAD is the tagged commit: passes",
                 rc == 0 and "release commit" in out, out)

        git(repo, "commit", "-q", "--allow-empty", "-m", "docs: something unrelated")
        rc, out = check_docs(repo)
        case("placeholder, tag on the remote, HEAD is PAST it: fails and names the fix",
             rc != 0 and "placeholder" in out and "--formula-only" in out, out)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\ncheck-docs formula: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
