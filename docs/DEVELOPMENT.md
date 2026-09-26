# QWarp engineering guide

## Project priorities

QWarp is an unofficial, Linux-only PyQt6 GUI for the Cloudflare WARP client. It
is intended to remain lightweight, Wayland-native, usable on X11, and suitable
for both Python package and frozen PyInstaller builds. Reliability comes before
feature velocity or packaging convenience: daemon control must be safe, the Qt
event loop must stay responsive, and existing desktop integrations must keep
working.

Proactive refactors are welcome when they materially improve reliability,
maintainability, or testability. Preserve compatibility, explain any broad
change, and add verification proportional to its risk. Do not overwrite or
discard unrelated work already present in the worktree.

## Architecture

- `src/qwarp/main.py` bootstraps logging, `QApplication`, translations,
  single-instance IPC, the state manager, the main window, the tray icon, and
  graceful shutdown.
- `src/qwarp/core/engine.py` is the synchronous boundary around `warp-cli`,
  `systemctl`, and `pkexec`. It parses command output into `WarpState` values and
  returns `(success, message)` results for actions. Its subprocess lock is a
  reliability contract: polling, diagnostics, settings reads, and mutations
  must not invoke the WARP CLI concurrently.
- `src/qwarp/core/state.py` is the asynchronous boundary between the engine and
  UI. A dedicated interruptible `QThread` polls status; a private `QThreadPool`
  runs actions, settings reads, and diagnostics; Qt signals publish results
  back to UI objects. It owns action serialization, busy state, immediate
  post-action refreshes, and worker shutdown.
- `src/qwarp/ui/window.py` and `src/qwarp/ui/tray.py` are state consumers. Keep
  their enabled actions, labels, icons, and toggle behavior consistent for every
  `WarpState`.
- `src/qwarp/core/instance.py` implements the local-socket single-instance
  contract and wakes the existing window when a second process starts. Socket
  acquisition must remain atomic: remove a socket only after proving it stale,
  retry listening once, and report unresolved ownership instead of starting a
  second instance.
- `src/qwarp/utils/system.py` resolves assets in source and PyInstaller modes,
  detects X11, and creates palette-aware icons. Shared styling lives in
  `src/qwarp/ui/styles.py`; SVGs and Qt locales live under
  `src/qwarp/assets/`.

Keep dependencies flowing in this direction: UI -> state manager -> engine.
Do not make the engine depend on Qt widgets or perform blocking daemon work
directly in the UI thread.

`qwarp --help` and `qwarp --version` are deliberately side-effect-free package
and frozen-binary probes. Handle these options before creating `QApplication`,
IPC sockets, settings objects, or polling workers.

## Development workflow

The package declares Python 3.11 or newer; CI exercises Python 3.11 and 3.14.
From the repository root, install the editable package and development tools:

```bash
python -m pip install -e ".[dev]"
```

The [release guide](RELEASING.md) defines the pre-review quality gates. `scripts/format.sh` is
a mutating helper (`ruff check --fix` followed by `ruff format`); run it only
when formatting changes are intended.

When reproducing CI dependency resolution, use the tracked constraints:

```bash
python -m pip install -c requirements/ci.txt -e ".[dev]"
python -m pip install -c requirements/release.txt build pyinstaller PyQt6 setuptools wheel
```

Tests must be deterministic and independent of a display, installed WARP
client, active network tunnel, systemd state, polkit prompt, and user account.
Mock subprocess calls at the engine boundary. Never let a test execute live
`warp-cli`, `systemctl`, `pkexec`, registration, license, or service-management
commands. For engine changes, cover successful output, nonzero exit status,
missing executables, timeouts, and relevant parsing variants. For Qt changes,
exercise state/signal behavior offscreen and shut down worker threads cleanly.

Do not launch QWarp as a routine validation step: startup creates IPC and
settings objects and begins polling the host's WARP installation. Only perform
live daemon or desktop testing when the task explicitly requires it and the
user has authorized the environmental effects.

## Qt and localization rules

- Keep blocking subprocess and polling work outside the Qt event loop. Send
  results to UI objects through signals and slots.
- Fetch WARP settings through `WarpStateManager`; do not call the synchronous
  engine from dialogs or other UI code. Reuse a single `warp-cli settings`
  result when multiple settings are needed.
- Reject overlapping mutations, keep controls disabled while an action is in
  flight, and restore them on every success or failure path. Route errors to
  the surface that initiated the operation.
- Preserve clean interruption and joining of the long-running status thread on
  application shutdown, and wait for the private action pool to finish.
- Preserve the tray-resident lifecycle, close-to-hide behavior, secondary
  instance wakeup, Wayland behavior, X11 cursor positioning, theme changes, and
  source/frozen asset lookup when touching related code.
- Treat an unavailable system tray as a supported environment: ignore
  start-minimized, keep the main window reachable, and let closing it exit.
- Wrap new user-visible strings with `self.tr(...)` or an appropriate
  `QCoreApplication.translate(...)` call. Do not translate internal CLI tokens,
  settings keys, or parser literals.
- Treat WARP license keys and future account credentials as secrets. Never put
  raw values in logs, exception text, test fixtures, screenshots, or command
  diagnostics; redact sensitive command arguments in logging paths.

After changing translatable strings, run:

```bash
bash scripts/build_locales.sh
```

This requires Qt6 `lupdate` and `lrelease` tools. It updates the eight tracked
`src/qwarp/assets/locales/qwarp_*.ts` catalogs and generates ignored `.qm`
files. Review catalog diffs, preserve existing translations, and do not invent
translations for languages you do not know. Release and Arch builds compile the
`.qm` files before packaging.

## Packaging invariants

- `packaging/arch/PKGBUILD` packages only the QWarp GUI and declares `cloudflare-warp-bin` as a
  hard runtime dependency. The dependency owns `warp-cli`, `warp-svc`, its
  systemd units, capabilities, and other official client files. QWarp packaging
  must never install, patch, remove, or replace those files.
- The former self-contained packaging path is intentionally gone:
  `qwarp.install`, `scripts/update_warp.sh`, and `PKGBUILD.local` are not part of
  the supported build. Do not recreate them or assume a local PKGBUILD exists.
- `scripts/build_source_archive.sh` uses an explicit source allowlist and
  deterministic tar metadata. Keep new required source files in that allowlist.
  `packaging/arch/PKGBUILD` and `packaging/arch/.SRCINFO` stay outside the source archive so
  the archive checksum can be recorded in them without a circular input.
- Keep GitHub Actions pinned to audited commit SHAs. Do not add tag-triggered
  publishing or post-tag content generation.

Arch metadata lives in `packaging/arch/`; CI copies it and the source archive
into a temporary build directory. AUR publication copies the metadata to the
AUR repository root under the conventional `PKGBUILD` and `.SRCINFO` names.

CI's Arch job builds from the generated source archive and asserts that the
result owns QWarp files only. Any package containing `warp-cli`, `warp-svc`, a
WARP systemd unit, a capability hook, an install hook, or a conflict with
`cloudflare-warp-bin` is a release blocker.

Generated `.qm`, wheel, PyInstaller, makepkg, and package artifacts are ignored
and must not be committed. Track source `.ts` catalogs, `packaging/arch/.SRCINFO`, application
assets, and packaging metadata when they intentionally change.
