# QWarp engineering guide

## Architecture

QWarp is an independent Linux PyQt6 GUI for the official WARP CLI. Dependencies
flow from UI to state manager to engine; keep blocking work out of the Qt event loop.

- `main.py` handles startup, logging, translations, consent, IPC, and shutdown.
- `core/engine.py` owns command construction, parsing, executable validation,
  cancellation, bounded output, and redaction. Its lock serializes CLI access.
- `core/state.py` owns the interruptible status thread and private action pool.
  UI objects consume signals; dialogs request asynchronous settings and diagnostics.
- `core/instance.py` owns the per-user single-instance lock and bounded local
  socket protocol. Remove an endpoint only after proving it stale.
- `ui/` contains the window, settings, tray, and shared presentation/styles.
- `platform/` preserves X11 taskbar behavior and desktop autostart integration.
- `utils/system.py` loads assets beside the installed package and renders
  palette-aware icons. Source SVGs and eight Qt catalogs live in `assets/`.

## Behavioral and security invariants

Preserve terms consent before registration, existing personal/Zero Trust accounts,
capability detection, JSON/text fallbacks, and every supported CLI operation.
Reject overlapping mutations, disable initiating controls during an action, and
restore them on both success and failure. Keep worker interruption and joining
on shutdown, close-to-tray behavior, secondary-instance wakeup, theme changes,
and both Wayland and X11 support. Without a tray, keep the window reachable
and allow closing it to exit.

Tests mock daemon/service boundaries and must never run live `warp-cli`,
`warp-svc`, `systemctl`, or `pkexec`. `qwarp --help` and `qwarp --version` exit
before creating Qt, settings, sockets, or workers and are safe package probes.
Normal startup and `--status-json` access the real installed client; use them
only during intentional live testing on a disposable system.

Keep trusted executable validation, subprocess argument arrays, output limits,
timeouts, and cancellation. Redact license keys, organization credentials,
authentication URLs, and network rules in logs and errors. Sensitive values
passed through the upstream CLI's argv can still be visible to authorized local
process observers; log redaction does not hide process arguments.

## Packaging invariants

Native packages use system Python/PyQt6 and depend on the separately installed
`cloudflare-warp-bin` (Arch) or `cloudflare-warp` (Debian/Fedora). Only that
separate package owns Cloudflare executables, service units, and capabilities.
QWarp must not bundle, overwrite, remove, or install hooks for those files.

The source archive uses an explicit allowlist and deterministic tar metadata.
Arch's `PKGBUILD` and `.SRCINFO` stay outside it to avoid a circular checksum.
CI substitutes the current-tree checksum only in a temporary Arch recipe;
committed metadata describes the immutable published source. Release validation
requires the committed checksum to match the exact candidate.

Keep source catalogs and artwork tracked; generated `.qm`, caches, build output,
and packages are ignored. Development and validation commands are in
[CONTRIBUTING.md](../CONTRIBUTING.md); publication is in [RELEASING.md](RELEASING.md).
