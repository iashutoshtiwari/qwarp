# QWarp release procedure

## Scope and review

Choose an unused semantic version: patch for compatible fixes and hardening,
minor for features, major for breaking changes. Work on `release/vX.Y.Z` from
current master unless the maintainer explicitly selects another base. Preserve
unrelated work and published history. Keep runtime/UI review separate from final
version and checksum preparation.

Before review, run Ruff checks and formatting verification, the full offscreen
suite, localization validation, and focused regression tests. Exercise Python
3.11 and 3.14 plus minimum-supported Qt. Mock WARP/systemd/polkit boundaries;
never mutate a real registration or tunnel during automated testing. Build and
inspect wheel, source, frozen, Arch, Debian, and RPM outputs in disposable
workspaces. Report unavailable checks as gaps, not passes.

The maintainer must review the diff and complete affected-area desktop QA and
core smoke tests. Only explicit approval permits release preparation. Additional
runtime/UI changes invalidate that approval and require renewed review.

## Preparation after approval

Review [the licensing audit](legal/LICENSING-AUDIT.md) before preparing a public
release. Frozen binary redistribution is blocked until the exact bundled
components, notices, matching corresponding source, and any required library
replacement/rebuild mechanism have been verified. Structural artifact checks
alone do not establish licensing compliance. QWarp retains its name by
maintainer decision; no renaming is proposed.
Qualified review of naming and Cloudflare integration questions remains external.

Publish matching QWarp source and build instructions beside each GPL-covered
binary. The edited tree differs from the immutable v0.10.1 source asset: do not
publish its updated license metadata against that old artifact. During the next
authorized release, select a new version, build its source archive, regenerate
the checksum and `.SRCINFO`, and verify the exact resulting packages.

Synchronize the application version, changelog, CI version probes,
`packaging/arch/PKGBUILD`, `packaging/arch/.SRCINFO`, and Debian/RPM metadata.
Compile all eight locales. Build public candidate artifacts with
`scripts/build_artifacts.sh --output-dir FRESH_DIRECTORY`. Default builds produce
source archives and a wheel; native jobs add Debian/RPM packages. Standalone
executables are excluded from public manifests, uploads, checksums and
attestations. `--frozen-local` builds only an inspection executable outside
`release/`; it does not enable publication or certify compliance.
Set the candidate source checksum in Arch metadata and regenerate `.SRCINFO`
using `(cd packaging/arch && makepkg --printsrcinfo > .SRCINFO)`.

Validate with `scripts/check_release.py --version X.Y.Z --artifacts OUTPUT/release`,
`scripts/check_build_artifacts.py X.Y.Z OUTPUT`, and `scripts/release_policy.py
X.Y.Z OUTPUT/release --require-native`. The publisher takes its file list from
the policy validator, which rejects frozen/stale/unexpected inputs and checks
complete checksums. Frozen compliance requires a separate evidence-backed code
change before that public allowlist can change; no boolean approval bypass
exists. Verify package ownership: QWarp must
not contain Cloudflare binaries, service units, capability hooks, or install
hooks. Arch must depend on the separately installed `cloudflare-warp-bin`.

Commit coherent implementation changes separately from final release metadata.
Push and open a PR only when authorized. Require CI and reviewed approval before
merging. Keep GitHub Actions SHA-pinned and publishing manually triggered.

## Publication

Only after the approved commit is merged to master, dispatch the protected
Release workflow with the selected version and a truthful live-QA attestation.
The workflow handles final checks, provenance, tags, GitHub assets, and AUR
publication. Credentials stay in the protected release environment; never copy
or print them locally. Never replace published tags/assets or force-push AUR.

Verify the exact published commit, complete artifacts and checksums, successful
workflow, and AUR version. An interrupted release must be diagnosed before retry.
A previous commit's QA attestation does not authorize a changed commit.
