# QWarp licensing, trademarks, and artwork

Copyright (c) 2026 Ashutosh Tiwari. All independently owned QWarp source,
tests, packaging, documentation, and translations are licensed under
[GNU GPL version 3 only](LICENSE) (`GPL-3.0-only`). The maintainer has confirmed
ownership and the right to relicense these materials. Earlier MIT grants remain
unaffected. Third-party artwork and external dependencies retain their licenses;
the combined source/wheel package expression is `GPL-3.0-only AND MIT AND Apache-2.0`.

Earlier distributions that bundled Python/Qt dependencies were not verified for
matching source, complete dependency notices, or library replacement/rebuild
obligations. Discontinuing that distribution does not resolve obligations for
copies already conveyed; review those artifacts before redistributing them.

## Cloudflare

QWarp is an independent open-source GUI for the official Cloudflare WARP CLI.
It is not affiliated with, sponsored, or endorsed by Cloudflare, Inc. The official
client must be installed separately; QWarp does not distribute, modify, replace,
or claim ownership of Cloudflare software.

Cloudflare, 1.1.1.1, WARP, WARP+, and associated marks belong to Cloudflare, Inc.
and their respective owners. QWarp's GPL license grants no rights over Cloudflare
software, trademarks, services, or subscriptions and does not override their terms.

The name incorporates WARP and remains an unresolved trademark risk under
[Cloudflare's guidelines](https://www.cloudflare.com/trademark/). The maintainer
has elected to retain QWarp; no rights-holder approval or independent legal
clearance is recorded. This disclaimer does not authorize the name or establish
contractual permission for every CLI integration.

See the [client legal information](https://developers.cloudflare.com/warp-client/legal/),
[Application Terms](https://www.cloudflare.com/application/terms/), and
[Application Privacy Policy](https://www.cloudflare.com/application/privacypolicy/).

## Artwork

The application icon combines modified Glyphs Poly `cloud-1` artwork,
copyright (c) 2018 Goran Spasojevic, with Google Material Symbols key artwork,
copyright Google LLC. These upstream copyrights remain applicable.

| File under `src/qwarp/assets/` | Origin | License |
| --- | --- | --- |
| `app-icon.svg` (cloud paths) | Glyphs Poly `cloud-1` | MIT |
| `app-icon.svg` (key path), `tray-connected.svg` | Material Symbols `vpn_key` | Apache-2.0 |
| `tray-connecting.svg` | Material Symbols `vpn_key` outline | Apache-2.0 |
| `tray-disconnected.svg` | Material Symbols `vpn_key_off` | Apache-2.0 |
| `tray-error.svg`, `tray-unregistered.svg` | Material Symbols `vpn_key_alert`, filled/outline | Apache-2.0 |
| `gear.svg` | Material Symbols `settings` | Apache-2.0 |

QWarp modifies colors, coordinate representation, sizing, placement, composition,
and filenames. Modification notices appear in the SVGs. The original
[MIT notice](LICENSES/Glyphs-Poly-MIT.txt) and [Apache-2.0 license](LICENSES/Apache-2.0.txt)
are preserved. No endorsement by Goran Spasojevic or Google is implied.
Screenshots include this artwork and retain the same third-party notices.

Upstream sources reviewed on 2026-10-13:
[Glyphs Poly](https://github.com/gorango/glyphs/blob/3a7d130bd3ad694c6da048b8b9f0f97f7a1ded07/sets/rounded/poly/cloud-1.svg)
and [Material Symbols](https://github.com/google/material-design-icons/tree/49d4db35df873165d6bd6ba09b063c7dafbac2f4/symbols/web).
Exact historical import revisions were not recorded. Preserve any additional
applicable upstream notices discovered when updating the artwork.
