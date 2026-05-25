# Changelog

All notable changes to QWarp are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [v0.8.0] – 2026-05-25

- chore: bump version to 0.8.0 ([2da8116](https://github.com/iashutoshtiwari/qwarp/commit/2da81168aa5f51f6cf895baabc6a9c3154bf1eab))
- style: sort imports in window.py using ruff ([5e28b8e](https://github.com/iashutoshtiwari/qwarp/commit/5e28b8e2433aa6aa6f7b346689a278142f2168ab))
- chore: bump version to 0.7.9 ([9a1ecc1](https://github.com/iashutoshtiwari/qwarp/commit/9a1ecc1c1c034592c87c4b3535591732b3cedfb5))
- feat: add WARP+ license, DNS content filtering, and revamp error handling ([8b60ebb](https://github.com/iashutoshtiwari/qwarp/commit/8b60ebb5da390c62c80c150ef2e22ceaa8588464))
- Revert "Update README.md" ([3c769b7](https://github.com/iashutoshtiwari/qwarp/commit/3c769b7f79819ec9c3ce8945d871974f12cb67ec))
- Update README.md ([4cb82c5](https://github.com/iashutoshtiwari/qwarp/commit/4cb82c5f28823d58256685cf736bdc3760d91644))
- fix(ci): scope release body to current version only ([0b97f67](https://github.com/iashutoshtiwari/qwarp/commit/0b97f6752c843203554e9c4a6cd5cfcf19976bca))
- Update README.md ([de160c5](https://github.com/iashutoshtiwari/qwarp/commit/de160c52802b5262d1da50a52ebe6a9c411ac67d))
- Update README.md ([df8cbc0](https://github.com/iashutoshtiwari/qwarp/commit/df8cbc06b023e701b406c559f2ee224712f45ba5))
- Update README.md ([efd6024](https://github.com/iashutoshtiwari/qwarp/commit/efd602407b6969ab7f88afa9a6a0dedd0abca600))
- Fix CI: replace libasound2 with libasound2t64 for Ubuntu 24.04 compatibility ([961b61b](https://github.com/iashutoshtiwari/qwarp/commit/961b61bfa82cf23aaffd48e986889367b6b2c658))
- Fix CI failure: Install missing system dependencies and defer Qt imports ([5b982cb](https://github.com/iashutoshtiwari/qwarp/commit/5b982cb5db61c58e9be4dbd42c981a316b6d0a54))
- Run ruff ([f66c7f3](https://github.com/iashutoshtiwari/qwarp/commit/f66c7f3976bbe5e167d019e9d534cca123780336))
- Update .SRCINFO ([6a12c79](https://github.com/iashutoshtiwari/qwarp/commit/6a12c79b63ca713306caef4686ad9a2d7f12fe20))
- chore: auto-update CHANGELOG for v0.7.8 [skip ci] ([ff169d2](https://github.com/iashutoshtiwari/qwarp/commit/ff169d27f54cdda80f4b5186dffc3795b045c7bb))


## [v0.7.8] – 2026-05-07

- chore: bump version to 0.7.8 ([ba8aed8](https://github.com/iashutoshtiwari/qwarp/commit/ba8aed84606c97ac1da85b6aa67bf26b6c0ab7ad))
- Refactor: Centralize QSS styling and implement dynamic SVG tinting ([8bc7018](https://github.com/iashutoshtiwari/qwarp/commit/8bc7018de5248122714229c44186ad9b3cdce733))
- GNOME dark mode support ([a1505c3](https://github.com/iashutoshtiwari/qwarp/commit/a1505c30f8412e13c6233a6c56149e411da7a0a8))
- Add instantaneous theme toggle and GNOME theme support ([33ab993](https://github.com/iashutoshtiwari/qwarp/commit/33ab993f7d8da3500e5eb808821536ecdc5d8d0d))
- Refactor status polling to use a dedicated QThread ([3b8b37d](https://github.com/iashutoshtiwari/qwarp/commit/3b8b37db173403cd08a50519275ad48e11145fb3))
- Enhance Arch Linux installation instructions ([7b8ab10](https://github.com/iashutoshtiwari/qwarp/commit/7b8ab10d19c73a27fcc9d07b76c58565065bee37))
- chore: auto-update CHANGELOG for v0.7.7 [skip ci] ([f8e38f7](https://github.com/iashutoshtiwari/qwarp/commit/f8e38f79a7e9f688eadfaaf0042f1584298b7307))


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
