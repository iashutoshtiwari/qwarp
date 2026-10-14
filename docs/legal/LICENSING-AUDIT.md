# QWarp licensing audit

Verification dates: **2026-10-13–14**. Original MIT baseline:
`4d6237ee4088d4e1dee0773cfcd2a9fb524004ec`; remediation baseline:
`f19a102644df55f58c9b68fd9473f5bbd5d884e2` on `release/gplv3-migration`
(application version 0.10.1). This is an engineering compliance record,
not legal advice, rights-holder permission, or clearance for release.

## A. Executive summary

The baseline licensed QWarp under MIT, used deprecated setuptools license
metadata, and carried MIT/Apache-2.0 artwork notices. Native packages already
kept the Cloudflare client external. Frozen archives carried application and
artwork notices but had no demonstrated dependency source/notice mechanism.

This maintenance change licenses independently owned QWarp material under
**GPL-3.0-only**, installs GNU's unmodified GPL v3 text, preserves the original
artwork license texts, scopes attribution, modernizes PEP 639 metadata, and
updates package declarations and checks. Source/wheel/native QWarp payloads
use **GPL-3.0-only AND MIT AND Apache-2.0**. This expression does not describe
all dependencies inside a frozen executable. Earlier MIT grants are not revoked.
Application version, package identifiers, published checksums, runtime behavior,
translations, and artwork geometry are unchanged. The second pass reconciles
five locks with already-reviewed constraints (SIP 13.13.0, hooks-contrib 2026.8,
iniconfig 2.3.1, Ruff 0.16.10), verifies native installation/removal, and disables
public frozen distribution throughout assembly, checksums, uploads, attestations
and publication. Optional local inspection remains outside the public bundle.
The Debian CI build environment moves to Ubuntu 26.04 because its setuptools
78.1.1 supports PEP 639; the reproduced Ubuntu 24.04 build failed with 68.1.2.
This changes the build environment, not application runtime dependencies.
Verified [Ubuntu package metadata](https://packages.ubuntu.com/resolute/python3-setuptools)
and the [GitHub runner image list](https://github.com/actions/runner-images).

**Public frozen releases remain blocked**: artifact-bound notices and hashes
are now collected, but complete per-file terms, matching supplier source, and
library modification/rebuild rights are unproven. A production-target local
replica was inspected without starting QWarp; it is not a published artifact
or a complete copy of the GitHub hosted runner image.
QWarp's name and Cloudflare integration also require qualified review.
Metadata cleanup and legal clearance are separate outcomes.

## B. Ownership and component inventory

### Repository ownership

Inspected tracked files, all-ref history, additions and asset changes,
`git shortlog -sne --all`, and source/notice/provenance searches. History is not
shallow. It records 110 commits by Ashutosh, seven dependency-bot commits, and
six changelog-bot commits. All application-source and translation changes are
attributed to Ashutosh; bots update dependency/workflow metadata and changelogs.
Initial application source entered at `7a0ccda`; the replacement artwork and
its notices entered at `64aed32`; current screenshots entered at `dcfe09e`.
No separate human source contributor or imported third-party code notice was
identified. Git authorship is evidence, not proof of exclusive copyright.

The migration proceeds on the maintainer's instruction for independently owned
material. Preserve the historical `Copyright (c) 2026 Ashutosh` notice and the
Debian attribution to Ashutosh Tiwari. A scoped package SPDX header avoids mass
edits to source, tests, generated locales, and data. New contributions use GPL v3
only without copyright assignment. If undisclosed copied code, employer rights,
or external translations are discovered, obtain the affected owners' permission
or preserve their compatible license and notices; do not overwrite their rights.

Maintainer factual checklist (not a fabricated declaration or assignment):

- [ ] Confirm code, scripts, documentation and eight translations attributed
  to Ashutosh were independently authored, with no undisclosed employer rights.
- [ ] Identify any externally supplied snippets, translations, generated inputs
  or contributions absent from Git authorship; record affected files and grants.
- [ ] Confirm captures are maintainer-created and record any historical artwork
  import records available. Retain third-party notices regardless of editing.
- [ ] Obtain any necessary owner's GPL-v3-only permission, or preserve compatible
  original licensing, before covering newly discovered external material.

History and the migration instruction support proceeding for independently
owned material; they do not substitute for these factual confirmations.

### Repository and runtime components

“External” means separately installed, not part of QWarp's source, wheel, or
native package. “Frozen” means actually observed in the local one-file build.
Confidence concerns evidence, not a guarantee of compliance.

| Component/files | Owner; origin and evidence | License/version; modified? | Distribution; obligations | Status/action; confidence |
| --- | --- | --- | --- | --- |
| Python code, tests, scripts, packaging, docs, eight `.ts` catalogs | Ashutosh; [repository history](https://github.com/iashutoshtiwari/qwarp/commits/master/) | GPL-3.0-only after this change; original work per history | Source/wheel/native/frozen as applicable; retain copyright, GPL, modified-work notices, matching source/build scripts for object code | Migrated; undisclosed provenance remains a maintainer question; medium-high |
| `docs/screenshots/*.png` | Maintainer's application captures; include artwork below | GPL-3.0-only for owned capture material, MIT/Apache-2.0 artwork retained | Source/docs; preserve applicable artwork notices | Inspected four existing screenshots; no artwork replacement; medium |
| `src/qwarp/assets/app-icon.svg` cloud paths | Goran Spasojevic; [rounded/poly/cloud-1.svg at upstream revision](https://github.com/gorango/glyphs/blob/3a7d130bd3ad694c6da048b8b9f0f97f7a1ded07/sets/rounded/poly/cloud-1.svg) | MIT; modified colors, precision, sizing, composition | All payloads; preserve copyright and permission notice | Existing MIT text matches [upstream license](https://github.com/gorango/glyphs/blob/771993addf00d5a7080fadb763f0da72ddc0f716/license) byte-for-byte; cloud coordinates match original design. Historical retrieval revision absent; high license/medium revision |
| Key in `app-icon.svg`, all five `tray-*.svg`, `gear.svg` | Google LLC; [Material Symbols](https://github.com/google/material-design-icons/tree/49d4db35df873165d6bd6ba09b063c7dafbac2f4/symbols/web) | Apache-2.0; modified | All payloads; license, applicable copyrights/NOTICE, prominent modification notices | File mapping in `TRADEMARKS.md`; SVG comments added, geometry unchanged; high license/medium exact historical revision |
| PyQt6 6.11.0 | Riverbank Computing/Phil Thompson; [official introduction](https://riverbankcomputing.com/software/pyqt/intro), installed wheel LICENSE/METADATA, [version metadata](https://pypi.org/pypi/PyQt6/6.11.0/json) | GPL-3.0-only in inspected wheel; commercial alternative requires a separate license; not LGPL; no modifications identified | External or frozen; GPL notices and matching corresponding source when conveyed as object code | Application GPL path compatible in engineering interpretation; frozen source delivery missing; high |
| PyQt6-Qt6 6.11.2 | Qt Group and contributors; Riverbank distributes wheel; [version metadata](https://pypi.org/pypi/PyQt6-Qt6/6.11.2/json), installed LGPL text | Package label LGPL v3; actual modules have separate options and third-party terms; vendor modifications unknown | External or frozen; select verified per-file path and fulfill it | Frozen release blocker; high package label/medium binary provenance |
| PyQt6-sip 13.13.0 | Phil Thompson; [version metadata](https://pypi.org/pypi/PyQt6-sip/13.13.0/json) | BSD-2-Clause; inspected wheel retains Phil Thompson copyright; unmodified by QWarp | External/frozen; retain copyright, conditions and disclaimer in binary materials | Original wheel notice copied to artifact-bound local evidence; public frozen distribution blocked; high |
| CPython 3.14.8 tests; 3.11.17 production-target candidate | Python Software Foundation and historical contributors; [3.14 license history](https://docs.python.org/3.14/license.html), installed Arch metadata | PSF-2.0 plus historical/component notices; upstream/distro patches not inventoried | External/frozen; preserve applicable Python notices and licenses, summarize modifications if applicable | Actual candidate interpreter and original LICENSE.txt recorded; supplier source/build correspondence unproven; high observed/medium supplier correspondence |
| PyInstaller 6.22.3 bootloader/loaders | PyInstaller team, Giovanni Bajo, McMillan Enterprises; installed `COPYING.txt`, [versioned official license](https://pyinstaller.org/en/v6.22.3/license.html) | GPL-2.0-or-later with bootloader exception; no QWarp modification identified | Build tool; bootloader/loader embedded | Exception permits combined executable without PyInstaller license/credit requirement; does not excuse other components; high |
| PyInstaller runtime hooks `pyi_rth_inspect`, `pyi_rth_pkgutil`, `pyi_rth_pyqt6`, `_pyi_rth_utils` | PyInstaller contributors; same COPYING, source headers | Apache-2.0 for runtime hooks/utilities; unmodified by QWarp | Frozen; respect scope of official distribution exception and applicable notices | Official summary does not require PyInstaller attribution; no UI credit added; high |
| `warp-cli`, `warp-svc`, client libraries/installers | Cloudflare and its licensors; [client legal page](https://developers.cloudflare.com/warp-client/legal/) | Proprietary application/subscription terms and client third-party terms; not relicensed | External only; user's separate installation and agreements | None identified in tracked payload or inspected frozen member list. No client modifications or operations performed; high technical separation, unresolved contractual authorization |

Artwork mapping: `vpn_key` filled/outline, `vpn_key_off` filled,
`vpn_key_alert` filled/outline, and `settings` filled. The reviewed Google
200-weight SVG paths have corresponding key/settings geometry in normalized
QWarp coordinates. Original import hashes/tooling were not recorded. Google's
root license is Apache 2.0; no root `NOTICE` was present at the checked revision.
Retain any additional applicable notices discovered during a future import
review. Google expressly makes About-screen attribution optional; no UI change
is necessary. Modifications do not eliminate upstream copyrights.

### Locked build/test tools (not automatically distributed)

Inspected installed versioned metadata and original license files. These are
build/test dependencies unless the frozen inventory establishes otherwise;
none of the following Python packages was present in the inspected embedded
PYZ as a runtime dependency. Their own licenses are not replaced by QWarp's GPL.

| Package/version in release locks | Owner; authoritative origin | Verified license; obligations if redistributed | Status/confidence |
| --- | --- | --- | --- |
| altgraph 0.17.5 | Istvan Albert, Bob Ippolito, Ronald Oussoren; [metadata](https://pypi.org/pypi/altgraph/0.17.5/json) | Metadata says MIT; shipped permissive text omits standard MIT notice condition; preserve supplied notice if shipped | Build only; high |
| build 1.6.1 | Filipe Laíns and PyPA; [metadata](https://pypi.org/pypi/build/1.6.1/json) | MIT; copyright/permission/disclaimer | Build only; high |
| iniconfig 2.3.1 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/iniconfig/2.3.1/json) | MIT; retain notice | Test only; high versioned metadata/installed license evidence |
| packaging 26.3 | Donald Stufft and contributors/PyPA; [metadata](https://pypi.org/pypi/packaging/26.3/json) | Apache-2.0 OR BSD-2-Clause; retain selected text and notices | Build/test only; high |
| pluggy 1.6.0 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/pluggy/1.6.0/json) | MIT; retain notice | Test only; high |
| Pygments 2.21.0 | Respective authors listed in AUTHORS; [metadata](https://pypi.org/pypi/Pygments/2.21.0/json) | BSD-2-Clause; retain copyright/conditions/disclaimer | Test only; high |
| pyproject-hooks 1.3.3 | Thomas Kluyver/PyPA contributors; [metadata](https://pypi.org/pypi/pyproject-hooks/1.3.3/json) | MIT; retain notice | Build only; high |
| pytest 9.1.1 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/pytest/9.1.1/json) | MIT; retain notice | Test only; high |
| ruff 0.16.10 | Charles Marsh/Astral contributors; [metadata](https://pypi.org/pypi/ruff/0.16.10/json) | MIT; retain notice | Development only; high versioned metadata/installed license evidence |
| setuptools 84.0.0 | Python Packaging Authority/contributors; [metadata](https://pypi.org/pypi/setuptools/84.0.0/json) | MIT; vendored components have separate notices | Build only; high; no evidence vendored components frozen |
| wheel 0.48.0 | Daniel Holth and contributors/PyPA; [metadata](https://pypi.org/pypi/wheel/0.48.0/json) | MIT; retain notice | Build only; high |
| pyinstaller-hooks-contrib 2026.8 | Community contributors; [metadata](https://pypi.org/pypi/pyinstaller-hooks-contrib/2026.8/json) | Standard hooks GPL-2.0-or-later; runtime hooks Apache-2.0, per installed LICENSE | Build only in inspected build; installed 2026.8 LICENSE inspected; no hooks-contrib payload identified; high |
| PyQt6/PyQt6-Qt6 6.6.0 | Riverbank/Qt; [binding metadata](https://pypi.org/pypi/PyQt6/6.6.0/json), [Qt metadata](https://pypi.org/pypi/PyQt6-Qt6/6.6.0/json) | GPL v3 / LGPL v3 labels | Minimum-version CI only; no 6.6 binary redistributed here; medium |

All five locks now match `ci.txt`/`release.txt`, with the intentional
PyQt6/Qt6 6.6.0 override only in the minimum lock. The existing lock generator
downloaded target wheels and computed their real hashes; no guessed hashes or
major upgrades. `check_requirements.py` rejects constraint drift before builds.
Python 3.11 and 3.14 SIP wheel hashes differ. Installed 13.13.0 SIP and 2026.8
hook license files were reviewed in the production-target environment.
Actions, compilers, Qt translation tools, packaging tools, pip and installer
remain infrastructure; running them does not establish that they are shipped.
Their separate terms apply if future artifacts include them.

### Frozen libraries and Qt third-party code

The historical Arch/Python 3.14 inventory is now explicitly archived at
[snapshots/2026-10-13-arch-python314.tsv](snapshots/2026-10-13-arch-python314.tsv).
It is not current release evidence and is not copied into standalone archives.

Current local replica: Ubuntu 22.04 x86_64, Actions CPython **3.11.17**,
PyInstaller 6.22.3, reconciled `release-py3.11.txt`. Ubuntu image digest:
`sha256:5ec03bb3441e8b0bf3b4f9cd4629a1ae763010dc3035bb8da3ae6cf026486401`.
Official [interpreter archive](https://github.com/actions/python-versions/releases/download/3.11.17-36876195594/python-3.11.17-linux-22.04-x64.tar.gz)
SHA-256: `9f7233ce8c4dacb2112c52842d6eb21be6e43907234f74c5a34f29bbba441eab`.
The container reproduces target OS, interpreter and explicit workflow inputs,
not every preinstalled hosted-runner package. It is neither a published binary
nor proof that future hosted builds will have the identical native closure.

`scripts/frozen_inventory.py generate` reads CArchive, nested PYZ and
`base_library.zip` without running QWarp. It hashes all payloads, bootloader,
build input files, locked wheels and original notice files; records OS/Python,
installed build package versions, supplier package/source references; and
compares every actual native member with that build's `Analysis-00.toc`.
`verify` binds the record to executable bytes, member set, payload hashes and
notice contents, rejecting stale/tampered/unsupported records. Output contains
no build-machine absolute paths or usernames. Copyright lines are an evidence
index, not an inferred owner list (a license author's copyright is not ownership
of every library). Package-level declarations are not per-file legal clearance.
The record always states **BLOCKED**, with no approval switch.

Ignored evidence: `build/remediation/production/candidate/local-frozen/`
(`final-evidence/inventory.json` and hashed `notices/`). Actual candidate
SHA-256: `4a2adf9af940ce279aeb4626ec77401d4f8293a28d5075455242afd3fb385017`;
594 hashed records, **165 native binaries/extensions**, 50 Qt plugins, 53
provider registry entries (including an unused unknown sentinel; no payload
assigned to an unknown supplier). The baseline with old locks had 165 native
entries and SHA-256
`a3f08800253f7752ae61a108dc667a4026cce4ebe0ea2a7ec5d40b85e2eb504f`.
These ignored outputs are local evidence, not promised public download URLs.
Every future local candidate must generate its own record from its own build.

Observed Qt 6.11.2 libraries: Core, DBus, EglFSDeviceIntegration, Gui, Network,
OpenGL, Pdf, Svg, WaylandClient, Widgets, WlShellIntegration, XcbQpa. PyQt
extensions: QtCore, QtDBus, QtGui, QtNetwork, QtSvg, QtWidgets, and SIP.
Fifty plugins cover EGL device integration, generic input, SVG icon engines,
image formats (including PDF, JPEG, TIFF and WebP), network information,
platform input contexts/platforms/platform themes, TLS, Wayland decoration,
graphics/shell integration, and XCB GL integration. Qt translations are bundled.
The inventory lists each plugin; no Wayland Compositor module was observed.

Verified [Qt Core source header at v6.11.2](https://code.qt.io/cgit/qt/qtbase.git/tree/src/corelib/kernel/qobject.h?h=v6.11.2)
and [Qt PDF header](https://code.qt.io/cgit/qt/qtwebengine.git/tree/src/pdf/qpdfdocument.h?h=v6.11.2)
offer LGPL-3.0-only, GPL-2.0-only, GPL-3.0-only, or commercial options.
The package label alone does not select a valid path for every file. Use
[Qt 6.11 license inventory](https://doc.qt.io/qt-6.11/licenses-used-in-qt.html),
[SVG](https://doc.qt.io/qt-6.11/qtsvg-index.html),
[Wayland Client](https://doc.qt.io/qt-6.11/qtwaylandclient-index.html),
[Image Formats](https://doc.qt.io/qt-6.11/qtimageformats-index.html), and
[PDF licensing](https://doc.qt.io/qt-6.11/qtpdf-licensing.html) to map the actual
binary build. PDFium and its embedded components need separate review.
Potential included Qt third-party code includes ICU 73, PCRE2, zlib, HarfBuzz,
FreeType, libpng, libjpeg-turbo, libtiff, libwebp, double-conversion, Unicode
data, XSVG, and Wayland protocol definitions. Exact compile options, patches,
versions and notices are not established by the wheel's LGPL text. **Blocked.**

The actual Ubuntu-native providers and their exact installed/source package
versions are in the artifact-bound record, with original distribution copyright
files copied only for observed components. These include glibc, GCC runtime,
GLib, DBus, OpenSSL, X11/XCB, xkbcommon, fontconfig, FreeType, compression,
Kerberos and other observed dependencies. Their differing permissive/copyleft
terms and exceptions need file-specific review and concrete source delivery.
Do not presume a GPL System Library exception for everything from `/usr/lib`.
No bundled dependency is marked fully cleared.

Corresponding-source investigation: PyPI provides no Qt6 6.11.2 sdist. Upstream
[Qt submodule archives](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/)
exist, but the Riverbank wheel's exact patches, flags and PDFium/component
snapshot correspondence were not established. Downloaded and hash-verified:

- PyQt6 6.11.0 sdist: `45dd60aa69976de1918b5ced6b4e7b6a25abd2a919ecef5fd5826ecc76718889`.
- PyQt6-sip 13.13.0 sdist: `2cd55f575cde208c398d6cfdecc5a13394ed2afb54226210c50e3a6df7c3a997`.

Their versioned PyPI records link exact archives; availability does not by itself
prove binary-source correspondence or satisfy conveyance. Supplier confirmation
and complete matching source/build inputs remain necessary before frozen release.

Constrained replacement experiment: copied Qt Core, added a non-loadable ELF
section using `objcopy`, loaded that copy in a Qt-Core-only QCoreApplication
probe (verified through `/proc/self/maps`), then rebuilt QWarp from its companion
source archive with PyInstaller `--add-binary` selecting those modified bytes.
Archive extraction confirmed the rebuilt executable contains that exact hash
and marker. QWarp was never started; installed Qt was not edited. This proves
build-time selection of modified library bytes and a limited ABI probe, **not**
source-level Qt modification, whole-application operation, complete corresponding
source, or full LGPL section 4 compliance. Qt source compilation was not performed
because supplier source correspondence remains missing. Evidence is under
`build/remediation/production/replacement/`.

## C. Distribution audit and required mechanisms

| Format | Contents, declaration and notice locations | Remaining verification |
| --- | --- | --- |
| Python wheel | QWarp source, SVGs and locale source/compiled catalogs; PEP 639 expression; four legal files under `.dist-info/licenses/`; no PyQt/Qt/Python binaries | Actual metadata/members and isolated install/remove checked; separate dependency installation remains governed by upstream terms |
| Python sdist | Same legal files, source `.ts` catalogs, build scripts/locks and legal/development/release documentation; same expression | Built and inspected; GPL-owned program source/build information retained |
| Release source archive | Source/docs/scripts/tests/requirements plus Debian/RPM build recipes; legal files retained; deliberately excludes recursive Arch checksum metadata | Source and build instructions must match each actual binary; publish matching Arch metadata through the reviewed AUR workflow; not a substitute for dependency corresponding source |
| Arch | License list GPL-3.0-only, MIT, Apache-2.0; `/usr/share/licenses/qwarp/` texts, `/usr/share/doc/qwarp/TRADEMARKS.md`; wheel legal files | Disposable build/install/remove passed; external dependencies unchanged. Published checksum remains old—authorized new-version preparation required |
| Debian | DEP-5 GPL-3 (version 3 only), scoped MIT/Apache assets; `/usr/share/doc/qwarp/` LICENSE, copyright, artwork texts and TRADEMARKS (may be compressed) | Ubuntu 26.04 build/install/remove passed; external dependencies unchanged. Backend must support PEP 639 (setuptools >=77.0.3) |
| RPM | SPDX AND expression; `%license` preserves all four legal files even with docs excluded; wheel license metadata retained | Fedora 44 build/install/remove passed; external dependencies unchanged; notice checks use `%license` paths |
| Standalone executable | Optional local-only one-file build plus executable-bound inventory/original notices, outside `release/` | **BLOCKED:** supplier-source/per-file terms/full modification mechanism unproven; no public standalone archive assembled |
| GitHub release | Manual protected workflow; source archive, sdist, wheel, .deb, .rpm and exact checksums only | Allowlist validated before attestation/publication; no frozen uploads or release-note promotion. Actual publication not run |

For QWarp object code, publish the exact matching source archive and necessary
build scripts/instructions beside the binary at the same release/download
location (GPL v3 section 6(d)); identify the binary/source hashes and ensure
continued access. The current build creates a companion application source
archive. It does not include all dependency source or vendor patches.

Public artifacts are generated into an empty output directory; existing ignored
outputs are preserved. `release_policy.py` rejects stale versions, unexpected or
frozen filenames, symlinks, missing native packages at publication, and incomplete,
duplicate or corrupt checksums. The same policy supplies `gh release` filenames.
Source/wheel payload validators reject Cloudflare filenames and native objects
(including ELF content hidden under a renamed data file). Focused negative tests
exercise these guards. No boolean legal-approval bypass exists. A future frozen
channel needs a separately reviewed code change and the following evidence:

1. Regenerate the inventory for the **actual release artifact**, not this local
   replica. The new extractor establishes shipped members, versions and hashes;
   supplier patches/build flags, per-file terms and compiled-in correspondence
   are still missing.
2. Ship the applicable original copyright, license and NOTICE files for Python,
   SIP, Qt and native dependencies. Generic homepage links are insufficient.
3. Choose verified Qt licensing paths. If GPL v3 is available for a component,
   provide its matching corresponding source and build/install information.
   Do not select GPL-2.0-only for a GPL v3 combined work. If LGPL v3 is selected,
   provide its license plus incorporated GPL text, rights notices, corresponding
   library source and a proven section 4 mechanism for replacing/relinking and
   running modified libraries (or complete suitable application/rebuild code).
   An extract-to-temporary-directory one-file executable is not itself proof of
   a suitable shared-library replacement mechanism.
4. Provide hashed matching source bundles and build recipes/patches for PyQt
   and every applicable copyleft dependency at the binary download location,
   using a reviewed GPL/LGPL conveyance route. Rebuild with a modified library
   on an isolated machine and verify it runs without restrictions. Supply any
   installation information required for a User Product. Document exclusions
   and library exceptions with file-specific evidence.

PyInstaller's bootloader exception removes its own combined-executable GPL
restriction; the [official FAQ](https://pyinstaller.org/en/stable/license.html)
does not require its license or acknowledgements with the application. It does
not waive licenses on Python, Qt, PyQt, SIP or native libraries. Avoid collecting
licenses for unshipped build tools merely to make a larger notice bundle.

## D. Cloudflare assessment

**Verified technical facts:** Tracked payload contains no Cloudflare installer,
client binary, proprietary library, service unit, or binary patch. Package
dependencies remain external. `core/engine.py` executes `warp-cli` argument
arrays through `utils/process.py`; it probes CLI help and reads JSON/text
output. Service operations are delegated to separately installed system tools.
No direct proprietary daemon IPC, proprietary protocol implementation, patched
client, subscription bypass, or copied Cloudflare source was identified.
Named-file archive checks support this conclusion but cannot prove every
unidentified file's provenance. No live client/service/network/account action
was performed during this audit.

Consent: the UI checkbox starts unchecked and gates personal/organization
registration. `WarpEngine` defaults `accept_tos=False`; onboarding sets it true
after the UI action, and commands then carry `--accept-tos`. Successful personal **and organization**
registration persist the accepted revision keyed to 2024-10-18. The prior report
misread the organization signal: `request_register_with_org` emits the same
REGISTER action. A new signal-path test confirms persistence without changing
runtime code. Unchecked, legacy and stale-revision cases are already mock-tested. The official terms page still displays that date.
The engine's public registration method does not itself enforce a UI checkbox;
normal UI gating and mock tests are evidence of the current path, not a general
guarantee for external engine callers. Runtime behavior was not changed.

**Engineering interpretation:** invoking a separately installed documented CLI
supports technical independence. Cloudflare's [Linux documentation](https://developers.cloudflare.com/warp-client/get-started/linux/)
documents installation, help, registration, connect, modes and license setting.
It does not independently authorize every controller integration or establish
that all JSON schemas, tunnel/DNS/organization commands and legacy fallbacks
have stable, publicly documented contracts. No authorization for undocumented
mechanisms was found; map those capabilities to current official documentation
or obtain qualified review before claiming such authorization.

### CLI operation matrix

Sources checked 2026-10-14: [Linux guide](https://developers.cloudflare.com/warp-client/get-started/linux/),
[organization manual deployment](https://developers.cloudflare.com/cloudflare-one/team-and-resources/devices/cloudflare-one-client/deployment/manual-deployment/),
[client changelog](https://developers.cloudflare.com/cloudflare-one/changelog/cloudflare-one-client/).
“Website” means examples/command families verified there, not a blanket license
to integrate. “Code/probe” means QWarp uses it or contains a help probe; no real
installed-client help was collected. Exact live CLI compatibility is **NOT TESTED**.

| Operation in `core/engine.py` | Provenance and parsing/capability limits | Assessment |
| --- | --- | --- |
| `registration new [organization]`, `registration show`, `registration license <key>`, `connect` | Website examples; JSON/text registration variants mock-tested, sensitive argv redacted | Documented interfaces; contractual authorization REVIEW REQUIRED |
| `mode doh`, `mode warp+doh`; `tunnel protocol set MASQUE/WireGuard`; `dns families off/malware/full` | Website examples; protocol choices additionally parsed from `--help` | Examples verified; installed-version behavior NOT TESTED |
| `--version`; `tunnel protocol set --help`, `tunnel ip --help`, `dns fallback --help` | Code probes existence/help; missing CLI and failed probes modeled in tests | Local capability detection, not documented authorization |
| `status`, `disconnect`, `registration delete`, `registration organization`; `settings mode-switch-allowed` | Actual code; JSON bool/string/object and text/error fallbacks; exact schema not verified as stable website contract | REVIEW REQUIRED for interface/contract claims; no feature removed |
| Other `mode` values (`dot`, `warp+dot`, `warp`, `proxy`, `tunnel_only`); `proxy port`; `trusted ethernet/wifi enable/disable` | Code and mock cases; mode aliases/capabilities do not prove upstream guarantees | Exact support NOT TESTED; REVIEW REQUIRED |
| `settings list`, legacy `settings` | JSON plus legacy text parsing; known error markers; missing keys use explicit defaults, not proof of client state | Schema stability REVIEW REQUIRED |
| `debug network`, `tunnel stats`, `dns stats`, `override show` | Read-only JSON/text fallbacks; no captured live output in this audit | NOT TESTED live; interface REVIEW REQUIRED |
| `tunnel ip add/add-range/remove/remove-range/list/reset`; `tunnel host add/remove/list/reset` | Official changelog mentions these command families; exact variants/schema used in code not all independently verified; validates IP/CIDR/host inputs | Family evidence only; exact variant/contract REVIEW REQUIRED |
| `dns fallback add/remove/list` | Code/help-probed capability; domain validation and duplicate checks; no stable website schema established | REVIEW REQUIRED; live support NOT TESTED |

Execution uses argument arrays, bounded process output, cancellation/timeouts and
redaction of license keys, organization tokens and sensitive URLs/values.
Mock tests cover malformed JSON, known errors, legacy status/settings fallbacks,
missing registration, timeout/worker cleanup and secret redaction. A parser's
default is an engineering fallback, not independent evidence of Cloudflare state.
No undocumented proprietary IPC or circumvention implementation was identified.
The matrix identifies interface evidence gaps without removing existing features.

**Contractual questions:** [Application Terms](https://www.cloudflare.com/application/terms/)
section 2 reserves Cloudflare ownership and restricts modification, decompilation,
reverse engineering and derivative works; organization use can involve a
separate subscription agreement. Counsel/Cloudflare must assess any applicable
integration permission or statutory interoperability basis. QWarp's GPL cannot
override these agreements. No Cloudflare approval is recorded.

**Trademark concern—high:** [Trademark Guidelines](https://www.cloudflare.com/trademark/)
list WARP and WARP+ as registered marks and prohibit incorporation into
third-party product names. **QWarp remains an unresolved potential trademark
risk.** Its disclaimer does not cure that risk. Obtain qualified clearance,
express rights-holder permission. The maintainer has explicitly elected to
retain QWarp while acknowledging that independent legal clearance has not been
demonstrated. No rename or package-identity change is proposed.

Reviewed project/repository name, README, metadata, desktop/autostart launcher,
package descriptions, SVGs, screenshots, settings, UI strings, locale catalogs
and release docs. Brand references principally identify compatible products,
operating modes and subscriptions. Current SVGs show a blue multi-tone cloud
and key, not a copied Cloudflare orange cloud/sun logo; screenshots show this
artwork and prominent QWarp/WARP words. Visual inspection does not establish
non-infringement or eliminate confusion/trade-dress questions. Historical
Cloudflare-derived assets remain in Git history/old releases; the GPL migration
does not relicense those artifacts or certify earlier distributions.

`TRADEMARKS.md` preserves independent development, no affiliation/authorization/
sponsorship/endorsement, separately installed client, retained Cloudflare rights,
and the explicit naming warning. No claims of approval or blanket legal rights
were added. [Client legal information](https://developers.cloudflare.com/warp-client/legal/)
links the applicable terms and privacy policy; they were not modified.

## E. Outstanding questions and release decisions

| Priority/status | Finding | Disposition / genuinely external action |
| --- | --- | --- |
| P0 BLOCKED: frozen only | Matching vendor source, PDFium/Qt compiled-in correspondence, per-file terms and full library modification rights unverified | Public frozen channel disabled consistently. Supplier evidence/qualified compliance review required before a future re-enable change |
| P1 REVIEW REQUIRED: name | QWarp contains registered WARP; Cloudflare product-name restrictions remain relevant | Maintainer explicitly retains QWarp; qualified legal review/rights-holder permission remains external. No renaming proposed or clearance claimed |
| P1 REVIEW REQUIRED: integration | Technical CLI separation is not blanket contractual authorization; exact advanced schemas not fully documented | Cloudflare/counsel assessment where needed; no invented approval or lawful-basis opinion |
| P2 REVIEW REQUIRED: ownership | Git authorship does not exclude employer rights or undisclosed imports/translations | Complete factual checklist in B; identify files/owners and obtain permissions if needed |
| P2 RESOLVED: lock drift | Four already-constrained updates absent from old locks | Five locks regenerated from real wheels, drift check added, current/minimum test matrices run |
| P2 RESOLVED: package isolation | Install/removal and executable notices previously only inspected statically | Arch/Debian/RPM disposable transactions passed with synthetic WARP ownership and preserved state/services |
| P2 RESOLVED: automation | Frozen uploads remained possible; bare `! grep` could skip Bash errexit | Strict shared public allowlist; explicit failing conditionals and negative regression tests; actionlint/shellcheck pass |
| Next-release preparation | Version 0.10.1 and Arch source checksum still identify immutable older source | Deliberately preserved; choose a new version/checksum only in authorized release preparation |
| Asset records | Historical retrieval revision absent; independent reconstruction not established | Immutable upstream references recorded, original MIT/Apache notices retained; no artwork change |

### Readiness by format

READY here means verified **technical payload/packaging requirements**, conditional
on ownership and external legal review. It does not mean legal clearance or
permission to publish an unchanged v0.10.1 release.

| Format | Engineering status | External/legal or release-preparation status |
| --- | --- | --- |
| Python sdist | READY: built, metadata/notices/source inspected | REVIEW REQUIRED: maintainer ownership/integration/name; new release authorization |
| Python wheel | READY: built/inspected and isolated install/remove | REVIEW REQUIRED: same; separately installed dependencies keep their own terms |
| Arch | READY: built, notices/dependencies and install/remove verified | BLOCKED for next publication until authorized new source version/hash/.SRCINFO; legal REVIEW REQUIRED |
| Debian | READY: Ubuntu 26.04 build/install/remove and notices verified | REVIEW REQUIRED: same legal questions and authorized release preparation |
| RPM | READY: Fedora 44 build/install/remove and notices verified | REVIEW REQUIRED: same legal questions and authorized release preparation |
| Standalone PyInstaller | BLOCKED for distribution; local extraction/build-selection experiment passed | Supplier corresponding source/per-file terms/full modification mechanism missing; excluded from public automation |
| GitHub release automation | READY: local policy, archive checks, negative tests, actionlint/shellcheck verified | Actual hosted publishing/attestation NOT TESTED; protected QA/approval and new-version preparation required |
| AUR publication workflow | NOT TESTED live; existing external-client model preserved | BLOCKED pending authorized version/hash preparation and credentials; legal REVIEW REQUIRED. No SSH/push/publication performed |

## F. Validation record

Task-specific `uv` environment for Python 3.14.8 and disposable containers only;
pre-existing `.venv`, ignored `dist/` (including stale 0.10.2 artifacts), published
history and host WARP state preserved. Native tests used explicitly synthetic
`cloudflare-warp[-bin]` packages; their script exits immediately and contains no
Cloudflare software. Package probes used **only `qwarp --version`**, which exits
before runtime startup. No live WARP registration, terms, connection or service
control; no publishing or Git operations that change remote state.

Ignored reproducibility logs/evidence are under `build/remediation/`: `tests314.log`,
`lock-regeneration.log`, `lock-repeat-result.txt`, `production/`, and `native/`.
Evidence is not automatically public and the historical snapshot is not an
artifact-specific manifest. Native packages were built from the companion
candidate source; later audit-only edits do not change application payloads.

| Commands/check | Actual result |
| --- | --- |
| `ruff check src/ tests/` and changed Python validators; `ruff format src/ tests/ --check --diff` | Pass in isolated current-lock environments |
| `QT_QPA_PLATFORM=offscreen PYTHONPATH=src pytest tests/ -v --tb=short` | Python 3.14.8: **296 passed**; Ubuntu 22.04 / Actions Python 3.11.17: **296 passed** |
| Same full suite with `minimum-qt-py3.11.txt` (Qt 6.6) | **290 passed, 1 skipped**: six inventory tests reside in a module skipped because PyInstaller is deliberately absent from minimum/CI dependencies; all six ran in release environments |
| `uv run --no-project --with pip python scripts/lock_requirements.py`; repeat; `sha256sum -c` saved lock digests; `check_requirements.py` | Five real-wheel locks regenerated; deterministic repeat and drift checks pass |
| `bash scripts/build_artifacts.sh --output-dir FRESH --frozen-local` in production-target container; internal `python -m build --no-isolation` | Source, wheel, sdist built/inspected; all four canonical notices and PEP 639 Metadata 2.4 expression preserved; local frozen evidence separated from public bundle |
| `python scripts/check_locales.py` | Eight catalogs complete and compiled; tracked catalogs unchanged |
| Isolated `uv pip install --no-deps` wheel, `qwarp --version`, metadata/notice/locale checks, `uv pip uninstall` | Entry point resolves, four installed legal files match originals, eight `.qm` files present; removal preserves separately installed PyQt6 |
| `scripts/frozen_inventory.py generate/verify` against actual candidate | 594 hashed records / 165 native members; exact Analysis comparison and notice integrity pass; legal status remains BLOCKED; executable never run |
| Qt Core replacement-byte probe/rebuild, described in B | Copied library loaded in Qt-only probe; companion-source rebuild embeds exact modified bytes. Qt-source compilation and QWarp operation with modified libraries NOT TESTED |
| `makepkg --nodeps --noconfirm`; `.PKGINFO`/members; `pacman -U`, `pacman -R` in Arch container | Pass: four notices, desktop/icon/locales, external dependencies, synthetic-client ownership, preserved user/client state and service-directory hashes |
| `makepkg --printsrcinfo`, comparison with committed `.SRCINFO` | Exact match; immutable published checksum retained |
| `dpkg-buildpackage -us -uc -b`; `dpkg-deb`; `apt install/remove` in Ubuntu 26.04 | Same checks pass; backend supports PEP 639; no real WARP installed |
| `rpmbuild -bb`; `rpm -qp/-qlp`; `dnf install/remove` in Fedora 44 | Same checks pass; expression and `%license` paths correct |
| `actionlint` 1.7.11 on both workflows (including shellcheck); `shellcheck scripts/build_artifacts.sh scripts/build_source_archive.sh` | Pass; SHA-pinned actions/security gates preserved. `.github/actionlint.yaml` recognizes official ubuntu-26.04 label absent from tool's built-in catalogue |
| Focused release/inventory tests | Reject forbidden/stale artifacts, symlinks, incomplete/corrupt sums, renamed ELF, manifest/payload/notice tampering; demonstrate actual shell forbidden-member guard aborts |
| `scripts/check_build_artifacts.py 0.10.1 OUTPUT`; release policy with both actual native packages; checksum verification | Pass on generated public artifacts; no standalone member/checksum/upload input |
| `scripts/check_release.py --version 0.10.1` | Pass; version consistency preserved |
| Same with `--artifacts OUTPUT/release` | Expected failure: new source bytes do not match immutable v0.10.1 Arch checksum; no tracked checksum changed |
| `git diff --check`; application/asset diff review | Pass; no runtime source or SVG changes in this remediation pass |

Earlier baseline migration: 276 offscreen tests, canonical license hashes,
seven SVG pixel comparisons and four screenshot inspections passed (2026-10-13).
The first Ubuntu 24.04 Debian attempt failed on setuptools 68.1.2; runner selection
was corrected to 26.04, not a backend downgrade. Current minimal Ubuntu 22.04
container initially lacked hosted-runner tools (`objdump`, full system Python,
Git); after installing them **inside the disposable container**, build and tests
passed. Those setup failures were retained in logs, not treated as code passes.
No dedicated type-check command is configured; mypy/pyright not run. A real
hosted release, AUR SSH, actual Cloudflare help/live compatibility, normal QWarp
startup/desktop session and full supplier-source Qt rebuild were **NOT TESTED**.
Synthetic dependencies and offscreen mocks are not proof of real WARP integration.

## G. Ongoing maintenance

Re-audit when dependency versions/locks, Qt modules/plugins, interpreter/host
images, frozen hooks, native libraries, artwork, branding, contributor provenance,
or distribution formats change. Keep immutable upstream identities, original
notices and modification records. Regenerate the frozen inventory from every
candidate; the local snapshot is evidence for this build only. Inspect source
and installed legal files, not just metadata or tool exit codes. Confirm continued
matching-source availability and rights to run modified libraries. Review terms
and trademark guidance when upstream changes; never silently auto-accept new
terms or claim GPL grants Cloudflare rights.

Primary general references, retrieved 2026-10-13; Riverbank introduction,
PyInstaller 6.22.3, Qt PDF, Cloudflare terms and trademarks rechecked 2026-10-14:
[GNU GPL v3 canonical text](https://www.gnu.org/licenses/gpl-3.0.txt),
[GPL v3](https://www.gnu.org/licenses/gpl-3.0.en.html),
[GNU FAQ](https://www.gnu.org/licenses/gpl-faq.html),
[Riverbank license FAQ](https://riverbankcomputing.com/commercial/license-faq),
[Qt licensing](https://doc.qt.io/qt-6/licensing.html),
[Qt GPL/LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations),
[Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0.html),
[PEP 639 metadata guidance](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license-and-license-files).
GNU web extraction failed in the browser tool; canonical text and FAQ were
retrieved successfully with curl. Other per-component primary sources are linked
above; local wheel license files and package database evidence were also used.
