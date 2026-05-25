<div align="center">
  <img src="src/qwarp/assets/app-icon.svg" width="128" alt="QWarp Logo"/>

  # QWarp

  [![GitHub stars](https://img.shields.io/github/stars/iashutoshtiwari/qwarp?style=for-the-badge)](https://github.com/iashutoshtiwari/qwarp/stargazers)
  [![GitHub forks](https://img.shields.io/github/forks/iashutoshtiwari/qwarp?style=for-the-badge)](https://github.com/iashutoshtiwari/qwarp/network/members)
  [![GitHub issues](https://img.shields.io/github/issues/iashutoshtiwari/qwarp?style=for-the-badge)](https://github.com/iashutoshtiwari/qwarp/issues)
  [![License](https://img.shields.io/github/license/iashutoshtiwari/qwarp?style=for-the-badge)](https://github.com/iashutoshtiwari/qwarp/blob/master/LICENSE)

  A lightweight, self-contained, Wayland-native Qt6 GUI for Cloudflare WARP on Linux.
</div>

> [!WARNING]
> **Early Development:** QWarp is currently in very early development. It is **not** a 1:1 replacement for the official Cloudflare WARP application and may lack certain advanced features or stability. Expect bugs and breaking changes as the project evolves.

> [!IMPORTANT]
> **Disclaimer:** This is an unofficial community project and is not affiliated with, authorized, maintained, sponsored, or endorsed by Cloudflare.

## Screenshots

<div align="center">

| Main UI | System Tray Area |
|:---:|:---:|
| <img src="screenshots/UI.png" width="400" alt="QWarp Main UI"/> | <img src="screenshots/Tray.png" width="400" alt="QWarp System Tray"/> |

</div>

## Features

- **Self-Contained**: Ships core WARP binaries directly — no external dependencies on `cloudflare-warp-bin` or conflicting GUIs.
- **System Integrations**: Lightweight UI, Wayland compatibility, and theme-aware tray icon tinting.
- **Daemon Control**: Connect/Disconnect from WARP visually and switch routing modes (DoH, DoT, Proxy).
- **Families DNS Filtering**: Toggle Cloudflare's 1.1.1.1 for Families (malware blocking, adult content filtering).
- **WARP+ License Support**: Easily apply your WARP+ license key to unlock premium routing directly from the UI.
- **Diagnostics**: View offline account telemetry (License, Registration) locally.
- **Service Recovery**: Auto-detects stopped WARP services and provides a one-click `pkexec` recovery button.
- **Non-intrusive**: Resides entirely in the system tray, toggles on click.

## Installation

### Arch Linux (Recommended)

You can install using the AUR using any AUR helper like `yay`:
```bash
yay -S qwarp
```

Or you can install using the provided `PKGBUILD`:
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

To install in editable mode for Python-only changes:
```bash
pip install -e .
qwarp
```

To build and install the full package (including the Cloudflare daemon, systemd service, and capability configurations) directly from your local source directory:
```bash
makepkg -p PKGBUILD.local -si
```

## Requirements
QWarp is self-contained. The WARP daemon (`warp-svc`) and CLI (`warp-cli`) are bundled during installation. After installing, enable the daemon:
```bash
sudo systemctl enable --now warp-svc
```

## Known Issues
- Enterprise Zero Trust (Teams) login is not yet supported. Consumer WARP and WARP+ work fully.
- If `cloudflare-warp-bin` is already installed, pacman will prompt you to remove it before installing QWarp (they conflict on the same binaries).

## Contribution
Any kind of contribution is highly welcome! Whether it's reporting bugs, suggesting new features, or submitting pull requests, I appreciate community input to help build out the application.

## Authors
- [@iashutoshtiwari](https://www.github.com/iashutoshtiwari)
