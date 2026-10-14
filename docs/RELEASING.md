# QWarp release procedure

## Prepare a candidate

Use an unused semantic version and preserve published releases and tags. Review
[TRADEMARKS.md](../TRADEMARKS.md) for attribution and the unresolved naming and
integration questions. Publish matching QWarp source and build instructions
alongside packages; dependencies are provided separately by the distribution.

Synchronize `src/qwarp/__init__.py`, `CHANGELOG.md`, Arch's `pkgver`/`.SRCINFO`,
Debian's changelog, and the RPM `Version`. Native package revisions are currently
`1`. Run the checks in [CONTRIBUTING.md](../CONTRIBUTING.md), including all eight
locales. CI tests Python 3.11/3.14 and Qt 6.6/current, builds all native targets,
and checks package installation, reinstallation, and removal with synthetic
WARP dependencies. No automated check should change a real account or service.

```bash
uv run --no-sync bash scripts/build_artifacts.sh --output-dir dist/candidate
sha256sum dist/candidate/release/qwarp-X.Y.Z-source.tar.gz
```

Record that source hash in `packaging/arch/PKGBUILD`, then regenerate `.SRCINFO`
with `(cd packaging/arch && makepkg --printsrcinfo > .SRCINFO)`. Arch metadata is
excluded from the archive, so these checksum edits do not change its bytes.

```bash
uv run --no-sync python scripts/check_release.py --version X.Y.Z \
  --artifacts dist/candidate/release --release
```

The current 0.10.1 source checksum identifies an older published asset. Cleanup
changes must ship with a new version and checksum; never replace that release.
Normal CI validates the current tree without requiring the old checksum to match.

## Review and publish

Review the complete diff, CI results, package contents/dependencies/notices, and
affected desktop behavior. Complete live QA on a disposable system with a
separately installed official client: consent/registration, connect/disconnect,
settings/DNS/protocols, split tunnels, Zero Trust, diagnostics, tray, single
instance, Wayland/X11, and shutdown. Record any unavailable checks. Runtime
changes after QA require another review.

After the approved commit is merged to master, manually dispatch the protected
Release workflow with the version and truthful `live_qa_completed` attestation.
The workflow checks master has not moved, validates the exact source/checksums,
uses the same native package jobs as CI, attests the public artifacts, creates
or validates a tag, and publishes GitHub assets and AUR metadata. The `release`
environment retains publishing approval and credentials. Actions remain SHA-pinned.

The public bundle contains the wheel, Python sdist, native source archive,
Debian package, Fedora package, and `SHA256SUMS`. Arch users build from the AUR
recipe, published using the existing SSH workflow. No automatic merging or
publishing occurs on dependency PRs. Diagnose an interrupted release before
retrying; never force-push AUR or replace published tags/assets.
