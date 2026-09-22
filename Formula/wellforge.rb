# Homebrew formula — the wellforge repo doubles as a tap:
#
#   brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
#   brew install matteocodogno/wellforge/wellforge
#   wellforge setup
#
# Versioned tarball install (NOT head-only): brew's git-based HEAD staging failed
# inside the install sandbox on some machines ("no time information in ''"), and
# plain tarballs also give normal `brew upgrade` semantics.
#
# THE CLI HAS ITS OWN TAG SERIES: `cli-vX.Y.Z`, not the template's `vX.Y.Z`. It used to
# follow the template, so a CLI fix could only ship with a template release — and since
# docs/VERSIONING.md requires a template release to carry a template change, CLI fixes
# simply did not ship. Do not bump url/sha256 by hand:
#
#   scripts/release-cli.sh patch --execute
#
# That script is the release: it bumps WELLFORGE_CLI_VERSION in scripts/wellforge, tags
# cli-vX.Y.Z, pushes, and only THEN fetches the tarball to compute its sha256 — GitHub
# generates that archive and it is not reproducible locally (measured: for v0.9.0, a local
# `git archive` of the same tree hashes to 746cc34f…, the formula pins b61eafcb…).
#
# `version` is stated explicitly rather than parsed out of the url, so the number cannot
# drift from what the script prints and stays monotonic across the change of series.
class Wellforge < Formula
  desc "Reproducible, AI-assisted project setup platform"
  homepage "https://github.com/matteocodogno/wellforge"
  url "https://github.com/matteocodogno/wellforge/archive/refs/tags/cli-v1.5.1.tar.gz"
  # NO explicit `version` line, deliberately. Homebrew scans the version out of the url —
  # including out of a `cli-vX.Y.Z` tag (`brew info` reports "derived version: 1.5.1"), so an
  # explicit one is REDUNDANT and `brew audit --strict` fails on it. The first attempt at this
  # release carried `version "1.5.1"` on the belief that brew could not parse this tag shape;
  # that belief was wrong. The real bug it was papering over was a url that still named the
  # TEMPLATE tag v0.9.0, from which brew correctly derived 0.9.0.
  #
  # So the url IS the version, and check-docs.py asserts exactly that: the url must name
  # cli-v<the version scripts/wellforge prints>, because `test do` below asserts the derived
  # version against that same string.
  # Filled by `scripts/release-cli.sh <v> --formula-only --execute`, never by hand: the
  # tarball only exists once the tag is pushed, and GitHub's generated archive is not
  # byte-reproducible locally. check-docs.py fails if this is left as a placeholder once
  # the matching cli-v tag is on the remote.
  sha256 "8c2d0a25404128f556b0eae7b6d0d77a7a4fb36db9992a6a59490133d9a6ce9d"
  license "MIT"
  head "https://github.com/matteocodogno/wellforge.git", branch: "main"

  depends_on "gh"
  depends_on "jq"
  depends_on "mise"
  depends_on "uv"

  def install
    bin.install "scripts/wellforge"
  end

  def caveats
    <<~EOS
      Finish the setup (clones the wellforge repo — default ~/.ai/wellforge,
      asked interactively — checks the toolchain, registers the Claude Code
      plugin):

        wellforge setup

      Anytime health check:  wellforge doctor
      Stay current:          wellforge update  (checkout) · brew upgrade  (this CLI)
    EOS
  end

  test do
    assert_match "doctor", shell_output("#{bin}/wellforge help")

    # The CLI's version is the WELLFORGE_CLI_VERSION constant inside the script, not this
    # formula and not the Cellar path. Asserting they agree is what catches a release that
    # bumped one and forgot the other — the failure mode that let brew users run the CLI
    # as it stood at v0.9.0 while every report called it current.
    assert_match version.to_s, shell_output("#{bin}/wellforge version")

    # The error model, verified through packaging rather than only in the repo's own
    # suite. `doctor` on a machine with no checkout is the first thing a new teammate
    # runs, and it used to die mid-report at exit 2 with no summary and no advice. It must
    # print the whole report and exit 1: a complete failure, not a crash.
    report = shell_output("HOME=#{testpath} #{bin}/wellforge doctor 2>&1", 1)
    assert_match "check(s) failed", report
    assert_match "wellforge setup", report

    # A typo must not look like success. `wellforge dcotor` exited 0 for a long time, so
    # nothing wrapping this script could tell the difference.
    shell_output("HOME=#{testpath} #{bin}/wellforge notacommand 2>&1", 1)
  end
end
