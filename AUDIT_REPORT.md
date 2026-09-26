# QWarp Performance, Security, Bug, and Privacy Audit

**Audit date:** 2026-09-26  
**Audited repository:** `iashutoshtiwari/qwarp`  
**Baseline commit:** `dcfe09ea6bc0acf8fb76196b3803bd26134037ee` (`master`)  
**Scope:** QWarp application code, local IPC, subprocess execution, settings/privacy handling, desktop integration, packaging, CI, and release automation.

## Executive summary

QWarp has a comparatively small and well-contained attack surface. It does not implement its own VPN protocol or transport; it acts as a PyQt6 controller around the separately installed official Cloudflare WARP client. The audit found **no Critical or High severity application vulnerability**, no telemetry implementation, no direct application network client, and no obvious command-injection path.

The subprocess boundary is generally strong: commands are passed as explicit argument vectors without a shell, WARP operations are serialized, timeouts are bounded, privileged service repair resolves `pkexec` and `systemctl` from trusted system paths, and known sensitive values are redacted from command/error diagnostics. License keys are masked by default in the UI and cleared from dialog fields when the dialog closes.

One concrete bug was identified and fixed in the accompanying audit branch: the current `master` source archive checksum no longer matched `PKGBUILD` / `.SRCINFO`, causing the package/release CI gate to fail.

The remaining findings below are intentionally **report-only** because addressing them would change compatibility, execution policy, or startup/locking semantics rather than merely correct an unambiguous defect.

## Methodology and limits

This was a static repository audit plus review of the repository's existing automated-test and GitHub Actions evidence. The current `master` CI run was inspected, including the failed package job and passing Python/Qt test jobs.

The audit did **not** perform live registration, live Zero Trust enrollment, a real Cloudflare account login, packet-level VPN testing, fuzzing of `warp-cli`, or live polkit/systemd mutation on a disposable Linux host. Those operations require an external client/account/system environment and are intentionally excluded from the deterministic repository tests.

## Fixed finding

### BUG-01 — stale Arch source checksum blocks release/package validation

**Severity:** Medium (release reliability / package integrity)  
**Status:** Fixed in audit branch  
**Affected:** `PKGBUILD`, `.SRCINFO`

The deterministic source archive generated from the current `master` hashes to:

`66800ee48cea39612fe3cdde9312768109f5e3dfeaa9a26bfb7f8a379d571319`

but both Arch metadata files still contained:

`8477bdf4322a6b0459aaa7ba2a5a7184ce6ab25db817fe1de8a42bd5e472b53c`

GitHub Actions run `36126257026` therefore failed in **Verify locales and release metadata** with a source checksum mismatch. Python 3.11, Python 3.14, and the minimum-supported-Qt test jobs passed in the same run.

**Fix:** synchronized `PKGBUILD` and `.SRCINFO` to the current deterministic source archive SHA-256. No application behavior is changed.

## Security findings

### SEC-01 — normal executable discovery trusts PATH

**Severity:** Low  
**Status:** Report only  
**Affected:** `src/qwarp/core/engine.py`, `src/qwarp/platform/taskbar.py`, `src/qwarp/platform/autostart.py`

Normal `warp-cli` and some `systemctl` invocations are resolved through `PATH`. Autostart also falls back to `Exec="qwarp"` when `shutil.which("qwarp")` cannot resolve an absolute executable.

This is **not shell injection**: QWarp uses argument arrays and does not invoke a shell. The risk is executable shadowing if an attacker can place a malicious executable earlier in the user's PATH. In practice, an attacker who can already write executable files into a trusted user PATH directory has substantial same-user execution capability, so this is a defense-in-depth issue rather than a privilege-escalation vulnerability.

The privileged repair path is stronger: it explicitly resolves `pkexec` and `systemctl` from `/usr/bin` or `/bin`.

**Recommendation:** if compatibility permits in a future hardening release, resolve `warp-cli` and `systemctl` once to validated absolute paths, or validate ownership/mode of non-system paths before execution.

### SEC-02 — stale local-socket recovery has a transient ownership race

**Severity:** Low  
**Status:** Report only  
**Affected:** `src/qwarp/core/instance.py`

When the first `QLocalServer.listen()` attempt fails, QWarp tries to notify the existing instance for 500 ms. If that notification fails, it calls `QLocalServer.removeServer()` and retries listening.

A transiently unresponsive but still-live primary instance could therefore have its socket pathname removed and a second instance could subsequently become a listener. This is mainly a reliability/single-instance integrity issue; the IPC message itself is only `WAKEUP` and does not expose privileged actions or credentials.

The repository's own architecture guidance says stale ownership should be proven before the socket is removed, so the current implementation is weaker than the documented contract.

**Recommendation:** redesign recovery around a per-user lock/PID ownership record, or use socket error classification plus retry/revalidation before unlinking. This should be exercised under real Unix-domain-socket races before merging, so it was not changed in this audit.

### SEC-03 — release Python dependencies are version-pinned but not hash-pinned

**Severity:** Low  
**Status:** Report only  
**Affected:** `requirements/ci.txt`, `requirements/release.txt`

Release/CI dependencies are pinned to exact versions, and GitHub Actions are pinned to immutable action commit SHAs. Release artifacts are checksum-verified and provenance-attested. However, Python dependency constraints do not include per-wheel/source hashes.

That leaves a small residual supply-chain dependency on package-index integrity and the selected artifact for each pinned version.

**Recommendation:** for the release builder, consider a hash-locked requirements file (for example, `pip --require-hashes`) generated for the supported runner/platform. Keep the more flexible development dependency declaration separate.

## Dependency security review

The release constraints currently use `PyQt6-Qt6==6.11.2`. Qt's September 2026 advisories for CVE-2026-76151, CVE-2026-78253, and CVE-2026-19248 identify Qt versions through 6.11.1 as affected and recommend 6.11.2 or later. The standalone release runtime is therefore on the fixed Qt patch level for those advisories.

Distribution-native packages intentionally depend on the distribution's `python3-pyqt6` / `python-pyqt6`, so the distro controls the final Qt security patch level. QWarp also does not fetch untrusted XML/SVG/network content through the affected Qt APIs: its SVGs are bundled project assets, and network operation is delegated to the official WARP client. This materially reduces practical exposure even on older system Qt builds.

Reference advisories:

- https://www.qt.io/blog/security-advisory-cve-2026-76151
- https://www.qt.io/blog/security-advisory-cve-2026-78253
- https://www.qt.io/blog/security-advisory-cve-2026-19248
- https://www.qt.io/blog/security-advisory-type-confusion-and-heap-buffer-overflow-vulnerability-in-qt-svg-marker-handling

## Privacy review

### PRIV-01 — no QWarp telemetry or direct application network client found

**Severity:** Informational / positive assurance  
**Status:** No change required

No runtime `requests`, `urllib`, analytics SDK, telemetry endpoint, or custom HTTP client was found. QWarp delegates WARP networking and enrollment to the official `warp-cli`. The UI contains fixed HTTPS links to Cloudflare legal/install documentation and the project's GitHub pages, which open in the user's external browser.

### PRIV-02 — sensitive WARP values are handled locally and mostly minimized

**Severity:** Informational / positive assurance  
**Status:** No change required

Observed protections:

- License keys are entered through a password-style field.
- The saved/displayed license value is masked by default, with only an explicit reveal action showing it.
- License input and cached display values are cleared when the settings dialog closes.
- License values and organization names are explicitly passed as sensitive values to the subprocess redaction layer.
- Error sanitization redacts URLs, bearer tokens, JWT-like strings, license/token fields, device IDs, organization values, private-key material, and long opaque credentials.
- `--status-json` intentionally reports enrollment state without emitting the organization name.
- QSettings persists preferences and a versioned Terms-consent marker; it does not persist the WARP+ license key.
- Device ID and organization are displayed only in the local diagnostics/settings UI as an explicit product feature.

Residual note: an uncaught Python exception traceback can expose local filesystem paths and implementation details to the terminal. No subprocess stdout/stderr is automatically appended to such tracebacks, and no secret-bearing exception path was identified.

## Performance review

### PERF-01 — no material hot loop or UI-thread blocking found

**Severity:** Informational / positive assurance  
**Status:** No change required

The performance architecture is conservative:

- `warp-cli` calls run outside the Qt UI thread.
- Mutating actions, read queries, and status polling use bounded workers.
- WARP subprocess access is serialized to avoid overlapping CLI operations.
- Status polling is approximately every 10 seconds while the UI is visible, every 30 seconds while hidden, and every 1 second during connection transitions.
- Duplicate expensive queries are coalesced with pending flags.
- Diagnostics and connection statistics are loaded on demand rather than continuously.
- The tray and main window react to signals instead of polling independently.

The main trade-off is intentional serialization: a slow diagnostic CLI call can delay the next status query. Parallelizing `warp-cli` calls could improve latency but would weaken the current reliability contract and is not recommended without profiling and upstream CLI concurrency guarantees.

### PERF-02 — symbolic SVG icons are re-rendered on demand

**Severity:** Informational  
**Status:** No change required

Theme-aware symbolic icons create SVG renderer/pixmap work when icons are requested or the palette changes. The assets are tiny and updates are event-driven, so this is not a meaningful performance concern in the current UI. Caching would add state/invalidation complexity for negligible expected gain.

## Bug and robustness review

### BUG-02 — stale IPC recovery can permit duplicate primaries under a rare race

This is the correctness aspect of **SEC-02** above. It is report-only because a correct fix requires changing the ownership protocol rather than a local one-line repair.

### BUG-03 — autostart state detection is intentionally simplistic

**Severity:** Low  
**Status:** Report only  
**Affected:** `src/qwarp/platform/autostart.py`

`is_autostart_enabled()` uses substring checks for `Hidden=true` and `X-GNOME-Autostart-enabled=false` rather than parsing Desktop Entry key/value syntax. Unusual but valid whitespace/casing, or the same text inside a comment, can be misclassified.

QWarp writes its own canonical file, so this normally affects only hand-edited or externally modified autostart entries.

**Recommendation:** if this becomes user-visible, parse the Desktop Entry section/key-value pairs rather than matching raw substrings. No change was made because it is an edge case and altering parsing behavior was outside the minimal bug-fix set.

## Release and CI posture

Strong controls already present:

- GitHub Actions are pinned to commit SHAs.
- Workflow permissions default to none and are granted per job.
- Release publication verifies that the checked-out commit still matches `origin/master`.
- Release artifacts are checksummed, smoke-tested, package-inspected, and provenance-attested.
- AUR SSH credentials are kept in the protected release environment and written with restrictive permissions.
- Release tags/assets are treated as immutable.
- CI tests Python 3.11 and 3.14 plus the minimum supported PyQt6 binding.
- Ruff includes Bandit-style `S` rules along with correctness/performance rules.

At the audited baseline, application/unit tests passed; the overall current `master` CI failure was caused by **BUG-01**, not by a runtime test failure.

## Final assessment

For a desktop wrapper around a privileged networking client, QWarp's boundaries are sensibly designed. The application itself does not enlarge the network attack surface much beyond the official WARP client, and it avoids several common desktop-wrapper mistakes: shell execution, blocking GUI subprocess calls, raw credential logging, hidden telemetry, and broad CI permissions.

After the checksum repair, the remaining items are best treated as future hardening work rather than immediate behavior-changing patches. The highest-value future engineering item is the single-instance ownership protocol, followed by executable-path hardening and hash-locked release dependencies.
