
# QWarp

QWarp is a lightweight, Wayland-native Qt6 GUI wrapper for the cloudflare-warp-bin service. It is designed for minimal resource usage, deep system integration, and high performance on modern Linux desktops.

Disclaimer: This is an unofficial community project. It is not affiliated with, authorized, maintained, sponsored, or endorsed by Cloudflare or any of its affiliates.




## Features

- Frameless Qt6 interface optimized for Wayland compositors.
- Integration with system-native Freedesktop icon themes.
- Asynchronous state polling to ensure a responsive UI.
- Automatic backgrounding to the system tray when losing focus.
- Lightweight binary footprint.



## Installation

### Arch Linux
The recommended way to install QWarp on Arch Linux is via the provided PKGBUILD. (Note: An AUR package is planned and will be available soon.) This method ensures all Python dependencies, desktop entries, and system icons are managed by pacman.

```bash
git clone https://github.com/iashutoshtiwari/qwarp.git
cd qwarp
makepkg -si
```

### Generic Linux Binary
For users on other distributions or for quick testing, a pre-compiled standalone binary is available in the Releases section.

1. Download the qwarp-linux-x86_64.tar.gz archive.
2. Extract the archive: 
```bash 
tar -xzvf qwarp-linux-x86_64.tar.gz
```
3. Execute the binary: 
```bash 
./qwarp
```

### Development Build
To run the project from source in a development environment:
```sh
pip install .
PYTHONPATH=src python -m qwarp.main
```
## Usage

Launch QWarp from your application menu or via the terminal using the qwarp command.
- System Tray: The application resides in the system tray. Left-click the icon to toggle the main control window. Right-click to access the quick-action menu (Connect, Disconnect, or Quit).
- Auto-Hide: The main window will automatically hide when it loses focus, behaving like a native system utility.


## Requirements

- Cloudflare WARP: The official cloudflare-warp-bin package must be installed and the warp-svc daemon must be active.


## Authors

- [@iashutoshtiwari](https://www.github.com/iashutoshtiwari)

