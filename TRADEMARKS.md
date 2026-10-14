# Trademark and third-party artwork notices

QWarp is independently developed and is not affiliated with, authorized,
sponsored, or endorsed by Cloudflare, Inc. QWarp requires a separately
installed official client and does not distribute Cloudflare software.

Cloudflare, 1.1.1.1, WARP, and WARP+ are trademarks and/or registered
trademarks of Cloudflare, Inc. in the United States and other jurisdictions.
All other trademarks are the property of their respective owners.

References to Cloudflare products identify the software and services with
which QWarp interoperates. They do not imply affiliation, sponsorship, or
endorsement.

The project continues to use the name QWarp. Because that name incorporates
WARP, it carries trademark risk under Cloudflare's guidelines. Cloudflare has
not approved this name, and this notice is not legal clearance for its use.

The maintainer has elected to retain QWarp. This decision does not establish
permission, non-infringement, or independent legal clearance.

- [Cloudflare Trademark Guidelines](https://www.cloudflare.com/trademark/)
- [Cloudflare WARP client legal information](https://developers.cloudflare.com/warp-client/legal/)
- [Cloudflare Application Terms](https://www.cloudflare.com/application/terms/)
- [Cloudflare Application Privacy Policy](https://www.cloudflare.com/application/privacypolicy/)

Cloudflare retains its intellectual-property and trademark rights. QWarp's
license grants no rights over Cloudflare software, trademarks, services, or
subscriptions and does not override Cloudflare's terms. Technical separation
and a documented CLI do not establish contractual authorization for every
third-party integration.

## QWarp licensing scope

Copyright (c) 2026 Ashutosh. QWarp's independently owned code, tests, build and
packaging scripts, documentation, and translation catalogs are licensed under
[GNU GPL version 3 only](LICENSE) (`GPL-3.0-only`). The artwork exceptions below
retain their own copyrights and licenses. External dependencies retain their
upstream licenses. Earlier releases' MIT grants remain unaffected.

## Application and tray artwork

The application icon combines modified `cloud-1` artwork from Glyphs Poly,
copyright (c) 2018 Goran Spasojevic, with Material Symbols key artwork,
copyright Google LLC. Editing does not extinguish the original copyrights.

| QWarp file under `src/qwarp/assets/` | Origin | Retained license |
| --- | --- | --- |
| `app-icon.svg` (cloud paths) | Glyphs Poly `cloud-1` | MIT |
| `app-icon.svg` (key path), `tray-connected.svg` | Google Material Symbols `vpn_key` | Apache-2.0 |
| `tray-connecting.svg` | Google Material Symbols `vpn_key` outline | Apache-2.0 |
| `tray-disconnected.svg` | Google Material Symbols `vpn_key_off` | Apache-2.0 |
| `tray-error.svg`, `tray-unregistered.svg` | Google Material Symbols `vpn_key_alert`, filled/outline | Apache-2.0 |
| `gear.svg` | Google Material Symbols `settings` | Apache-2.0 |

QWarp modifies colors, SVG coordinate representation, sizing, placement,
composition, and filenames. Modification notices also appear in the SVGs.
The MIT permission notice and Apache-2.0 text are preserved in `LICENSES/`.
No endorsement by Goran Spasojevic or Google is implied. These licenses do not
require an attribution label in the UI.

- [Glyphs Poly source](https://github.com/gorango/glyphs)
- [Glyphs Poly MIT License](LICENSES/Glyphs-Poly-MIT.txt)
- [Material Symbols source](https://github.com/google/material-design-icons)
- [Apache License 2.0](LICENSES/Apache-2.0.txt)

Sources verified 2026-10-13. Exact historical artwork revision records are
incomplete; see [the audit](docs/legal/LICENSING-AUDIT.md) for evidence and gaps.
