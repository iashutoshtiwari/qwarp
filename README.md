# QWarp

A lightweight, Wayland-native Qt6 wrapper for cloudflare-warp-bin.

**Disclaimer:** This is an unofficial community project and is in no way affiliated with, authorized, maintained, sponsored, or endorsed by Cloudflare or any of its affiliates or subsidiaries.

## Features
- Clean, frameless Qt6 UI designed for modern Wayland compositors.
- Uses system-native Freedesktop icons (adapting gracefully to your current KDE/GNOME theme).
- Non-blocking asynchronous state polling.
- Drops quietly into the system tray when not in focus.

## Installation

You can install QWarp natively on Arch Linux using the provided `PKGBUILD`:

```bash
makepkg -si
```

This will automatically build the Python wheel and install `qwarp` natively into your system, along with its desktop entry.

## Usage

Once installed, launch QWarp from your application launcher or by running:
```bash
qwarp
```

It will appear in your system tray. Click the tray icon to bring up the main interface, where you can connect or disconnect from the Cloudflare WARP network.
