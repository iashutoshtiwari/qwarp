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

Development requires Linux, Git, Python 3.11 or newer, and `uv`. The full QWarp interface
also requires an installed Cloudflare WARP client, but the automated tests do not: they mock daemon and command access.

```bash
git clone https://github.com/iashutoshtiwari/qwarp.git
cd qwarp
uv venv --python 3.11
uv pip install --python .venv/bin/python -e ".[dev]"
source .venv/bin/activate
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

Build the wheel, Python sdist, and deterministic native-package source archive
into a fresh directory:

```bash
uv run --no-sync bash scripts/build_artifacts.sh --output-dir dist/local-candidate
```

Builds compile all eight catalogs; review any tracked `.ts` changes. Existing
outputs are preserved, and candidate checksums stay in the chosen output
directory. Builds do not change committed versions or Arch checksums. Validate
with `uv run --no-sync python scripts/check_release.py --version 0.10.1
--artifacts dist/local-candidate/release`.

## Understand the code path

### Repository layout

- `src/qwarp/` contains the application and its bundled assets and translations.
- `tests/` contains deterministic application tests.
- `docs/` contains engineering/release references and README screenshots.
- `packaging/arch/`, `packaging/debian/`, and `packaging/rpm/` contain distribution metadata.
- `scripts/` contains locale and release build/check tools. `pyproject.toml` declares all Python dependencies.

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
uv run --no-sync ruff check src/ tests/ scripts/
uv run --no-sync ruff format src/ tests/ scripts/ --check
QT_QPA_PLATFORM=offscreen uv run --no-sync pytest -q --override-ini addopts=''
uv run --no-sync python scripts/check_locales.py
shellcheck scripts/*.sh
actionlint
```

Apply Ruff fixes/formatting directly when intended. CI covers Python 3.11 and 3.14
with current PyQt6, and Python 3.11 with PyQt6/Qt 6.6. There is no dedicated
type-checker configuration. Dependabot proposes weekly Python and Actions updates,
grouping minor/patch changes; review and merge them manually after CI passes.

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
previous MIT grants. See [TRADEMARKS.md](TRADEMARKS.md) for attribution and scope.

## Submit a pull request

Before opening a pull request:

- Rebase or merge the current `master` branch without rewriting shared history.
- Run the quality checks above and describe any manual testing.
- Add tests for behavior changes and documentation for user-visible changes.
- Keep generated build, wheel, locale `.qm`, and system package artifacts out of the commit.
- Confirm that no credentials, license keys, account details, or diagnostic secrets are present.

Explain what changed, why it changed, and any compatibility or packaging impact. Maintainers handle version metadata,
release notes, tags, GitHub releases, and AUR publication through the protected release workflow.
