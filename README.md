# QWarp

A lightweight, Wayland-native Qt6 GUI wrapper for the `cloudflare-warp-bin` service on Linux.

> **Disclaimer:** This is an unofficial community project and is not affiliated with, authorized, maintained, sponsored, or endorsed by Cloudflare.

## Screenshots

| Main UI | System Tray Area |
|:---:|:---:|
| <!-- Add link to main UI image below --> <br> <img src="/screenshots/UI.png" width="300"/> | <!-- Add link to tray image below --> <br> <img src="screenshots/Tray.png" width="300"/> |

## Features

- **System Integrations**: Lightweight UI, Wayland compatibility, and theme-aware tray icon tinting.
- **Daemon Control**: Connect/Disconnect from WARP visually and switch routing modes (DoH, DoT, Proxy).
- **Diagnostics**: View offline account telemetry (License, Registration) locally.
- **Service Recovery**: Auto-detects stopped WARP services and provides a one-click `pkexec` recovery button.
- **Non-intrusive**: Resides entirely in the system tray, toggles on click, and cleans up conflicting official GUIs automatically.

## Installation

### Arch Linux (Recommended)
You can install using the provided `PKGBUILD` to satisfy dependencies naturally via `pacman`:
```bash
git clone https://github.com/iashutoshtiwari/qwarp.git
cd qwarp
makepkg -si
```

### Generic Linux Binary
Download the pre-compiled `qwarp-linux-x86_64.tar.gz` from the Releases section:
```bash
tar -xzvf qwarp-linux-x86_64.tar.gz
./qwarp
```

### Development
```bash
pip install .
qwarp
```

## Requirements
To actually proxy traffic, the official `cloudflare-warp-bin` package must be installed and the `warp-svc` daemon enabled.

## Authors
- [@iashutoshtiwari](https://www.github.com/iashutoshtiwari)
