# Changelog

All notable changes to QWarp are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v0.7.7] – 2026-03-27

- Bump version to 0.7.7 ([83980bc](https://github.com/iashutoshtiwari/qwarp/commit/83980bcb4eeb2a1daec31fe039d3959634e52bb9))
- Include .qm, update locale TS files, add test ([78b8cf2](https://github.com/iashutoshtiwari/qwarp/commit/78b8cf2a1b8bb55c2704169498a9b13662aaf9f2))
- Update .SRCINFO ([bfcf67b](https://github.com/iashutoshtiwari/qwarp/commit/bfcf67b850a14805bd975e4ac6a9552b75211119))
- chore: auto-update CHANGELOG for v0.7.6 [skip ci] ([e90439b](https://github.com/iashutoshtiwari/qwarp/commit/e90439b212de681eb76b7047cd8bfa67b94494d1))


## [v0.7.6] – 2026-03-27

- Bump version to 0.7.6 and switch CI to master ([46ce029](https://github.com/iashutoshtiwari/qwarp/commit/46ce029cb6129d2554f30983651dba857b3fca1b))


<!-- New release entries are automatically inserted here by CI on each tag push -->

## [0.7.1] – 2026-03-27

### Fixed
- PKGBUILD version bump to 0.7.1.

---

## [0.7.0] – 2026-03-27

### Added
- **Internationalization (i18n)**: Full PyQt6 translation pipeline using `pylupdate6` and `lrelease6`.
- Translation support for 8 languages: English, Spanish, Portuguese, German, Italian, Chinese, Japanese, and Hindi.
- `scripts/build_locales.sh` build script to extract and compile `.ts` → `.qm` locale files.
- Language selection UI in the Settings menu.
- Locale files bundled into the Arch Linux PKGBUILD via `qt6-tools` makedepend.

---

## [0.6.0] – 2026-03-26

### Added
- **Offline Telemetry Interface**: Asynchronous diagnostics panel parsing `warp-cli` account and network data.
- **Theme-Aware SVG Icon Tinting**: Icons adapt to light/dark system themes via dynamic SVG color replacement.

---

## [0.5.0] – 2026-03-26

### Added
- **System-Wide Logging**: Structured `logging` integration across `engine.py`, `state.py`, and `ui/` modules.
- State transition logging at INFO level; polling suppressed unless state changes.
- Subprocess command logging at appropriate DEBUG/ERROR levels.

---

## [0.4.0] – 2026-03-25

### Added
- **systemd Service Lifecycle Management**: Deep status checks and service repair via `pkexec`.
- New `SERVICE_STOPPED` and `DAEMON_ERROR` states in `WarpState`.
- "Start & Enable" repair action exposed in the UI and tray menu.

---

## [0.1.0] – 2026-03-25

### Added
- Initial release: modular, Wayland-native PyQt6 GUI for `cloudflare-warp-bin`.
- System tray icon with live status monitoring.
- Frameless connection toggle window.
- `WarpEngine` for `warp-cli` subprocess management.
- `WarpStateManager` for async background polling.
- PKGBUILD for Arch Linux (AUR).
