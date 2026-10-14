# QWarp licensing audit

Verification date: **2026-10-13**. Baseline: `4d6237ee4088d4e1dee0773cfcd2a9fb524004ec`
(master, application version 0.10.1). This is an engineering compliance record,
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
Application version, dependency pins, package identifiers, published checksums,
runtime behavior, translations, and artwork geometry are unchanged.
The Debian CI build environment moves to Ubuntu 26.04 because its setuptools
78.1.1 supports PEP 639; the reproduced Ubuntu 24.04 build failed with 68.1.2.
This changes the build environment, not application runtime dependencies.
Verified [Ubuntu package metadata](https://packages.ubuntu.com/resolute/python3-setuptools)
and the [GitHub runner image list](https://github.com/actions/runner-images).

**Public frozen releases remain blocked**: exact dependency notices,
corresponding source, and library modification/rebuild rights are unproven.
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
| PyQt6-sip 13.12.0 (locks); 13.13.0 (constraints) | Phil Thompson; [13.12.0 metadata](https://pypi.org/pypi/PyQt6-sip/13.12.0/json), [13.13.0 metadata](https://pypi.org/pypi/PyQt6-sip/13.13.0/json) | BSD-2-Clause; inspected 13.12.0 license says copyright 2025 Phil Thompson; unmodified by QWarp | External/frozen; retain copyright, conditions and disclaimer in binary materials | Frozen archive lacks notice; high for inspected wheel, medium newer metadata |
| CPython 3.14.8 locally; 3.11 in release CI | Python Software Foundation and historical contributors; [3.14 license history](https://docs.python.org/3.14/license.html), installed Arch metadata | PSF-2.0 plus historical/component notices; upstream/distro patches not inventoried | External/frozen; preserve applicable Python notices and licenses, summarize modifications if applicable | Local interpreter and extension inventory recorded; release interpreter patch version unpinned, frozen notices missing; high observed/low production identity |
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
| iniconfig 2.3.0; constraints 2.3.1 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/iniconfig/2.3.0/json) | MIT; retain notice | Test only; high locked/medium newer metadata |
| packaging 26.3 | Donald Stufft and contributors/PyPA; [metadata](https://pypi.org/pypi/packaging/26.3/json) | Apache-2.0 OR BSD-2-Clause; retain selected text and notices | Build/test only; high |
| pluggy 1.6.0 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/pluggy/1.6.0/json) | MIT; retain notice | Test only; high |
| Pygments 2.21.0 | Respective authors listed in AUTHORS; [metadata](https://pypi.org/pypi/Pygments/2.21.0/json) | BSD-2-Clause; retain copyright/conditions/disclaimer | Test only; high |
| pyproject-hooks 1.3.3 | Thomas Kluyver/PyPA contributors; [metadata](https://pypi.org/pypi/pyproject-hooks/1.3.3/json) | MIT; retain notice | Build only; high |
| pytest 9.1.1 | Holger Krekel and contributors; [metadata](https://pypi.org/pypi/pytest/9.1.1/json) | MIT; retain notice | Test only; high |
| ruff 0.16.7; constraints 0.16.10 | Charles Marsh/Astral contributors; [metadata](https://pypi.org/pypi/ruff/0.16.7/json) | MIT; retain notice | Development only; high locked/medium newer metadata |
| setuptools 84.0.0 | Python Packaging Authority/contributors; [metadata](https://pypi.org/pypi/setuptools/84.0.0/json) | MIT; vendored components have separate notices | Build only; high; no evidence vendored components frozen |
| wheel 0.48.0 | Daniel Holth and contributors/PyPA; [metadata](https://pypi.org/pypi/wheel/0.48.0/json) | MIT; retain notice | Build only; high |
| pyinstaller-hooks-contrib 2026.7; constraints 2026.8 | Community contributors; [metadata](https://pypi.org/pypi/pyinstaller-hooks-contrib/2026.7/json) | Standard hooks GPL-2.0-or-later; runtime hooks Apache-2.0, per installed LICENSE | Build only in inspected build; 2026.8 file-level licensing not independently inspected; high locked/medium newer metadata |
| PyQt6/PyQt6-Qt6 6.6.0 | Riverbank/Qt; [binding metadata](https://pypi.org/pypi/PyQt6/6.6.0/json), [Qt metadata](https://pypi.org/pypi/PyQt6-Qt6/6.6.0/json) | GPL v3 / LGPL v3 labels | Minimum-version CI only; no 6.6 binary redistributed here; medium |

All five locks and both constraint files were examined. Locks still use
13.12.0/2026.7/2.3.0/0.16.7 while current constraints use
13.13.0/2026.8/2.3.1/0.16.10. They were not regenerated during this task.
Python 3.11 and 3.14 SIP wheels have different hashes. Workflow actions,
Qt translation tools, Python installer, compiler, and distribution packaging
tools are build infrastructure, not bundled just because they run in CI.
Their separate licensing applies if they are ever redistributed. Local pip
and installer are environment tools, not additional application dependencies.

### Frozen libraries and Qt third-party code

The local audited executable was built without running it, using Python 3.14.8,
release-py3.14 locked wheels, PyInstaller 6.22.3, and Arch host libraries.
It is **not** the Ubuntu/Python 3.11 published release. See
[FROZEN-INVENTORY.tsv](FROZEN-INVENTORY.tsv) for every native binary/extension,
provider/version, package-declared licenses, source URL and review status.
Package-level license lists are not independently verified per-file selections.
Qt/wheel-native third-party version gaps remain explicitly unverified.

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

Host-native providers are inventoried individually (90 native entries). These
include Python, OpenSSL, GLib/GTK/Pango/GDK, AT-SPI, cairo, systemd-libs,
libseccomp, libcloudproviders, tinysparql, fontconfig, FreeType, HarfBuzz,
Graphite, ICU 78, X11/XCB libraries, xkbcommon, DBus, compression libraries,
libffi, libxml2, pixman, SQLite, Kerberos, keyutils, util-linux, and GCC runtime
libraries. Their permissive/copyleft/custom terms vary. No local modifications
by QWarp were identified; distribution/vendor patches are unverified.
Do not call every bundled library a GPL “System Library” exemption merely
because it originated in `/usr/lib`. Inspect applicable exceptions and exact
files, including GCC runtime exceptions and permissive notices. Native package
declarations containing `custom`, LicenseRef, or broad GPL/LGPL names need
original-text review. No frozen dependency is marked legally compliant.

## C. Distribution audit and required mechanisms

| Format | Contents, declaration and notice locations | Remaining verification |
| --- | --- | --- |
| Python wheel | QWarp source, SVGs and locale source/compiled catalogs; PEP 639 expression; four legal files under `.dist-info/licenses/`; no PyQt/Qt/Python binaries | Actual metadata and members checked; separate dependency installation remains governed by upstream terms |
| Python sdist | Same legal files, source `.ts` catalogs, build scripts/locks and legal/development/release documentation; same expression | Built and inspected; GPL-owned program source/build information retained |
| Release source archive | Existing source/docs/scripts/tests/requirements structure; legal files retained; deliberately excludes recursive Arch checksum metadata | Source and build instructions must match each actual binary; not a substitute for dependency corresponding source |
| Arch | License list GPL-3.0-only, MIT, Apache-2.0; `/usr/share/licenses/qwarp/` texts, `/usr/share/doc/qwarp/TRADEMARKS.md`; wheel legal files | External python/PyQt6/cloudflare-warp-bin unchanged; published source checksum still points to old release—new release preparation required |
| Debian | DEP-5 GPL-3 (version 3 only), scoped MIT/Apache assets; `/usr/share/doc/qwarp/` LICENSE, copyright, artwork texts and TRADEMARKS (may be compressed) | External Python/PyQt6/cloudflare-warp unchanged; build backend must support PEP 639 (setuptools >=77.0.3) |
| RPM | SPDX AND expression; `%license` preserves all four legal files even with docs excluded; wheel license metadata retained | External Python/PyQt6/cloudflare-warp unchanged; both workflow inspections updated for `%license` notice path |
| Standalone archive/executable | Outer GPL/artwork/independence files, audit and generated recursive `FROZEN-COMPONENTS.txt`; one-file executable embeds dependencies | **Release blocker:** no dependency notice bundle/source/rebuild mechanism. Structural checks are not legal approval |
| GitHub release | Existing manual publishing workflow, source/binary/.deb/.rpm artifacts and checksums | Not run. Source adjacency must satisfy chosen GPL conveyance route; blocked frozen redistribution must be resolved before publication |

For QWarp object code, publish the exact matching source archive and necessary
build scripts/instructions beside the binary at the same release/download
location (GPL v3 section 6(d)); identify the binary/source hashes and ensure
continued access. The current build creates a companion application source
archive. It does not include all dependency source or vendor patches.

For frozen release readiness, a concrete implementation and evidence are still
required; none is claimed here:

1. Inventory the **actual Ubuntu/Python 3.11 release artifact**, its embedded PYZ,
   native binaries and compiled-in Qt components. Record versions, hashes,
   supplier patches/build options, per-file licenses and mandatory notices.
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
after the UI action, and commands then carry `--accept-tos`. Personal successful
registration persists a revision keyed to 2024-10-18; organization consent is
not persisted by that helper. The official terms page still displays that date.
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
express rights-holder permission, or plan an independently reviewed rebrand as
a separate change. No rename or package-identity change was made.

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

| Severity | Question/evidence gap | Required action |
| --- | --- | --- |
| Blocker for frozen distribution | Missing dependency notices, exact matching source and proven Qt/native-library user modification mechanism | Implement and verify the artifact-specific mechanism in C; do not publish an uncleared frozen artifact |
| High, naming | QWarp incorporates registered WARP; guidelines prohibit product-name incorporation | Rights-holder permission/qualified legal clearance or separate independent rebrand |
| High, integration | Documented CLI use is not blanket contractual authorization; advanced schemas/commands not all verified | Document supported interface provenance and obtain Cloudflare/counsel assessment where necessary |
| Medium, ownership | One human Git author does not prove absence of employer/third-party contributions | Maintainer confirms independently owned source/translation provenance; get any discovered owner's consent before blanket relicensing |
| Medium, build/release consistency | Constraint/lock drift; older distro setuptools; new metadata still paired with old published Arch source hash | Review/regenerate locks separately if desired, verify supported build backend in target distro, prepare a new version/checksum only in authorized release work |
| Medium, asset records | Exact historical import revisions not recorded; no removal of third-party material established | Preserve MIT/Apache notices and record immutable upstream identifiers for future imports |

## F. Validation record

Baseline: 262 offscreen tests passed; Ruff lint/format passed. Migration metadata
acceptance was false before edits (`license` was a legacy MIT/Apache text table).
New focused tests exercise notice preservation, canonical GPL hash, SPDX
metadata, native package declarations, attribution, and negative archive cases.

Commands used the existing project `.venv` (Python 3.14.8; release-py3.14
locked dependencies). Build isolation installed setuptools 84.0.0. Long builds
ran in dedicated tmux sessions; package dependencies were installed only inside
task-specific containers. No host global packages or WARP state were changed.

| Check | Actual result |
| --- | --- |
| `.venv/bin/ruff check src/ tests/` (also changed validators) | Pass |
| `.venv/bin/ruff format src/ tests/ --check --diff` (also validators) | Pass |
| `QT_QPA_PLATFORM=offscreen PYTHONPATH=src .venv/bin/pytest tests/ -v --tb=short` | 276 passed; WARP/system boundaries mocked |
| `.venv/bin/python -m build` | Pass; actual wheel METADATA and sdist PKG-INFO use Metadata-Version 2.4, correct License-Expression and four License-File entries; root GPL and asset notices verified |
| `.venv/bin/python scripts/check_locales.py` | Pass; eight catalogs complete/compiled; tracked translations unchanged |
| `shellcheck scripts/build_artifacts.sh`; `bash -n scripts/build_artifacts.sh scripts/build_source_archive.sh`; `git diff --check` | Pass |
| `makepkg --printsrcinfo`, comparison with committed `.SRCINFO` | Exact match; published checksum retained |
| `makepkg --nodeps --noconfirm` in isolated build directory | Pass; temporary source checksum only, not tracked checksum. `.PKGINFO`, installed legal contents and external dependencies verified with bsdtar |
| `dpkg-buildpackage -us -uc -b` in Ubuntu 24.04 container | Failed: setuptools 68.1.2 rejects PEP 639 string license; reproduced and corrected by Debian CI runner change |
| Same Debian build in Ubuntu 26.04 container | Pass with setuptools 78.1.1; dpkg-deb inspected required notices (including compression), copyright, Python/PyQt/Cloudflare dependencies and absence of client binaries |
| `rpmbuild -bb` in Fedora 44 container; `rpm -qp`, `rpm -qlp` | Pass; actual SPDX expression, all `%license` notices, external dependencies, no Cloudflare members |
| PyInstaller `--onefile --noconsole` with existing assets, separate build paths | Pass; executable not run. CArchiveReader/embedded PYZ inspected: 344 members, 199 native binaries/extensions, 50 Qt plugins, no recognized Cloudflare runtime filenames; no dependency license files embedded |
| Seven SVG before/after QSvgRenderer pixel comparisons | Identical renders; comments do not change artwork |
| Four existing screenshot inspections | Completed; branding observations in D |
| `check_build_artifacts.py 0.10.1 build/legal-artifacts`; `sha256sum --check SHA256SUMS` | Pass. Direct assembly uses existing source/archive inputs in an isolated output directory; canonical legal files, matching metadata, inventory, nested frozen filenames and notice inclusion verified |
| `check_release.py --version 0.10.1` | Pass; versions unchanged |
| Same validator with `--artifacts build/legal-artifacts/release` | Expected failure: changed source archive does not match immutable v0.10.1 Arch checksum (`c8d03b...`). Tracked checksum unchanged; authorized new-version preparation must regenerate it |

The full destructive-cleanup build wrapper was not invoked; its component
builds and assembly steps were exercised in separate task directories. Package
install transactions, live QWarp UI/CLI, WARP commands, publishing workflows,
Python 3.11/minimum-Qt test execution, and rights to run modified frozen libraries
were not tested. No configured type-check command exists, and mypy/pyright,
`actionlint`, and preferred `yq` are unavailable. Install those tools if dedicated
type/workflow validation is required; YAML workflow lint was not claimed.
Initial frozen build attempt failed because a relative asset path resolved under
the spec directory; rebuilding with the wrapper's absolute paths succeeded.
Frozen licensing compliance **failed evidence review** despite successful builds.

Pre-existing ignored `dist/` outputs include a 0.10.2 wheel/source/binary and
installer artifacts that do not match tracked version 0.10.1. Their wheel still
declares MIT/Apache. They were not migrated, published, or treated as matching
source for the changed tree. The old `dist/release/` and `dist/qwarp-build/`
outputs were preserved; new frozen audit work uses `build/legal-frozen/`.

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

Primary general references, retrieved 2026-10-13:
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
