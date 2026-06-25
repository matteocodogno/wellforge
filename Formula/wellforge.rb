# Homebrew formula — the wellforge repo doubles as a tap:
#
#   brew tap matteocodogno/wellforge https://github.com/matteocodogno/wellforge
#   brew install matteocodogno/wellforge/wellforge
#   wellforge setup
#
# Versioned tarball install (NOT head-only): brew's git-based HEAD staging failed
# inside the install sandbox on some machines ("no time information in ''"), and
# plain tarballs also give normal `brew upgrade` semantics. Release procedure:
# bump url/sha256 here in the same commit that tags vX.Y.Z (sha256: curl -sL
# <url> | shasum -a 256).
class Wellforge < Formula
  desc "WellForge internal platform: reproducible, AI-assisted project setup"
  homepage "https://github.com/matteocodogno/wellforge"
  url "https://github.com/matteocodogno/wellforge/archive/refs/tags/v0.3.7.tar.gz"
  sha256 "d9a5965e7691f7c5b88a38a977a8eaf4944b4d772ef046984f265ae4b289398a"
  license "UNLICENSED" # internal WellForge tooling
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
    assert_match version.to_s, shell_output("#{bin}/wellforge --version")
  end
end
