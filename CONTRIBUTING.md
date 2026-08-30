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

## Understand the code path

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

Repository-wide architecture, security, packaging, and agent guidance lives in [AGENTS.md](AGENTS.md). Its technical
constraints apply to human-authored changes too.

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

## Submit a pull request

Before opening a pull request:

- Rebase or merge the current `master` branch without rewriting shared history.
- Run the quality checks above and describe any manual testing.
- Add tests for behavior changes and documentation for user-visible changes.
- Keep generated build, wheel, PyInstaller, locale `.qm`, and system package artifacts out of the commit.
- Confirm that no credentials, license keys, account details, or diagnostic secrets are present.

Explain what changed, why it changed, and any compatibility or packaging impact. Maintainers handle version metadata,
release notes, tags, GitHub releases, and AUR publication through the protected release workflow.
