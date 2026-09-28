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

Synchronize the application version, changelog, CI version probes,
`packaging/arch/PKGBUILD`, `packaging/arch/.SRCINFO`, and Debian/RPM metadata.
Compile all eight locales. Build artifacts with `scripts/build_artifacts.sh`.
Set the candidate source checksum in Arch metadata and regenerate `.SRCINFO`
using `(cd packaging/arch && makepkg --printsrcinfo > .SRCINFO)`.

Validate with `scripts/check_release.py --version X.Y.Z --artifacts dist/release`,
`scripts/smoke_frozen.sh dist/qwarp-build/qwarp X.Y.Z`, and `sha256sum --check
SHA256SUMS` inside the artifact directory. Verify package ownership: QWarp must
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

### Application metadata

Keep the newest release version and date in
`packaging/appstream/io.github.iashutoshtiwari.qwarp.metainfo.xml` synchronized
with `CHANGELOG.md`. `scripts/check_release.py` checks these along with the
application name, license, launcher, and icon identity. AppStream uses the
reverse-DNS ID while the established launcher and icon remain `qwarp.desktop`
and `qwarp`.

Validate metadata with:

```bash
appstreamcli validate --pedantic packaging/appstream/*.metainfo.xml
desktop-file-validate qwarp.desktop
```

CI validates without network access; run the command above locally when changing
screenshot URLs. Use existing screenshots at immutable commit URLs. Qt translation
catalogs are associated with AppStream using the `qwarp` prefix; the current Qt
translation extraction does not translate desktop entries or metainfo text.

Debian and RPM must both contain the metainfo file in `/usr/share/metainfo/`,
the launcher in `/usr/share/applications/`, and the SVG in
`/usr/share/icons/hicolor/scalable/apps/`. Package artifact checks enforce this.
Software-center display depends on the frontend and distribution's AppStream
catalog ingestion. This metadata does not establish package-origin trust;
signed repository infrastructure is a separate release concern.
