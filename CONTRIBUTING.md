# Contributing to QWarp

Thanks for helping improve QWarp. Bug reports, documentation fixes, translations, tests, and focused code changes are
all welcome.

## Report a bug or propose a change

Search [existing issues](https://github.com/iashutoshtiwari/qwarp/issues) before opening a new one. A useful bug report
includes:

- QWarp version (`qwarp --version`)
- Cloudflare WARP version (`warp-cli --version`)
- Distribution, version, desktop environment, and Wayland or X11 session
- Exact steps, expected behavior, actual behavior, and relevant error output

Remove account identifiers, organization details, license keys, tokens, and other private data from logs and
screenshots. For a feature proposal, explain the problem and desired behavior before prescribing an implementation.

## Set up a development environment

Development requires Linux, Git, Python 3.11 or newer, and Python virtual-environment support. The full QWarp interface
also requires an installed Cloudflare WARP client, but the automated tests do not: they mock daemon and command access.

```bash
git clone https://github.com/iashutoshtiwari/qwarp.git
cd qwarp
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -c requirements/ci.txt -e ".[dev]"
```

Confirm the development environment without touching the host's WARP state:

```bash
qwarp --version
qwarp --help
```

Launching `qwarp` starts background polling of the real WARP installation. Do that only when live testing is intended.

### Run from source or make a clean test build

From the repository root, run the current source directly:

```bash
PYTHONPATH=src .venv/bin/python -m qwarp.main
```

For source, wheel and native-package inputs, install the matching release lock
and build into a fresh directory without removing existing output:

```bash
uv pip install --python .venv/bin/python --require-hashes --only-binary=:all: -r requirements/locks/release-py3.11.txt
PATH="$PWD/.venv/bin:$PATH" bash scripts/build_artifacts.sh --output-dir dist/local-candidate
```

Select the lock matching your interpreter (3.11 or 3.14). Add `--frozen-local`
only for a local inspection build. The executable is placed under
`dist/local-candidate/local-frozen/qwarp`, outside the public `release/` directory.
Its `evidence/inventory.json` binds every embedded payload and notice to the
executable SHA-256. The legal status remains BLOCKED; this manifest does not
permit redistribution. Never upload the local-frozen directory.

`scripts/clean_build.py` remains an explicit destructive cleanup helper. It
removes `build/`, `dist/`, and caches; preview with `--dry-run` first. It builds
unfrozen artifacts by default; `--frozen-local` requests the inspection executable.
No helper automatically launches QWarp. Use `--help` or `--version` for a
side-effect-free probe. Normal startup polls the separately installed WARP client.

Builds compile all eight catalogs; review any tracked `.ts` changes. Candidate
checksums stay in the chosen output directory. Local builds do not update
committed release versions or Arch checksums. Validate dependency coherence with
`python scripts/check_requirements.py` and inspect public inputs with
`python scripts/release_policy.py VERSION OUTPUT/release`.

## Understand the code path

### Repository layout

- `src/qwarp/` contains the application and its bundled assets and translations.
- `tests/` contains deterministic application tests.
- `docs/` contains audit reports and README screenshots; see the
  [2026-09-26 audit](docs/audits/2026-09-26.md).
- `packaging/arch/`, `packaging/debian/`, and `packaging/rpm/` contain distribution metadata.
- `scripts/` contains build and validation tools; `requirements/` pins CI and release dependencies.

The shared `qwarp.desktop` launcher and legal notices stay at the repository root.
`build/`, `dist/`, and test/lint caches are disposable generated output; `.venv/`
is the local development environment.

Arch builds should copy `packaging/arch/PKGBUILD`, `packaging/arch/.SRCINFO`, and
the source archive into a temporary directory before running `makepkg`. Normal
CI adjusts the checksum only in that temporary copy to test the current tree;
committed metadata continues to describe the immutable published release.

### Application architecture

QWarp keeps dependencies in one direction:

```text
PyQt interface (src/qwarp/ui)
          ↓
asynchronous state manager (src/qwarp/core/state.py)
          ↓
synchronous command engine (src/qwarp/core/engine.py)
          ↓
warp-cli, systemctl, and pkexec
```

Keep command execution out of the Qt event loop. UI objects consume state and signals; the state manager owns workers,
polling, and action serialization; the engine owns subprocess access and parsing.

Repository-wide architecture, security, and packaging guidance lives in the
[engineering guide](docs/DEVELOPMENT.md). See the [release guide](docs/RELEASING.md)
for validation and publication requirements.

## Make and test changes

Keep changes focused and add deterministic tests for changed behavior. Tests must never invoke live `warp-cli`,
`systemctl`, `pkexec`, registration, license, or service-management commands.

Run the same core checks used for review:

```bash
ruff check src/ tests/
ruff format src/ tests/ --check --diff
QT_QPA_PLATFORM=offscreen pytest tests/ -v --tb=short
```

`scripts/format.sh` modifies files with Ruff. Use it only when you intend to apply formatting changes.

### User-visible text and translations

Wrap new UI text for Qt translation. When translatable strings change, install the Qt 6 localization tools for your
distribution and run:

```bash
bash scripts/build_locales.sh
```

Common tool packages are `qt6-l10n-tools` and `qt6-tools-dev-tools` on Ubuntu/Debian, `qt6-linguist` on Fedora, and
`qt6-tools` on Arch. Review the tracked `.ts` changes, preserve existing translations, and do not commit generated
`.qm` files.

## Contribution licensing

New contributions to QWarp's independently owned code and documentation must be
offered under `GPL-3.0-only`, without assigning copyright to the maintainer.
Identify imported code and artwork, their owners, sources, licenses, and changes;
retain required notices. Third-party artwork retains its existing license.
This policy does not assert consent from historical contributors or revoke
previous MIT grants. See [the licensing audit](docs/legal/LICENSING-AUDIT.md).

## Submit a pull request

Before opening a pull request:

- Rebase or merge the current `master` branch without rewriting shared history.
- Run the quality checks above and describe any manual testing.
- Add tests for behavior changes and documentation for user-visible changes.
- Keep generated build, wheel, PyInstaller, locale `.qm`, and system package artifacts out of the commit.
- Confirm that no credentials, license keys, account details, or diagnostic secrets are present.

Explain what changed, why it changed, and any compatibility or packaging impact. Maintainers handle version metadata,
release notes, tags, GitHub releases, and AUR publication through the protected release workflow.
