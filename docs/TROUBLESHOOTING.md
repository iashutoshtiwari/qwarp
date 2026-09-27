# Troubleshooting QWarp

Start with the [requirements](../README.md#requirements) and [installation instructions](../README.md#installation).
For normal operation, see the [usage guide](USAGE.md). QWarp controls the official client; it does not
bundle or replace `warp-cli` or `warp-svc`.

## Official Cloudflare client not found

Install the official client using the links in the [requirements](../README.md#requirements), then
restart QWarp. This dependency is required even for the standalone QWarp binary.

Check that your terminal can find it:

```bash
command -v warp-cli
warp-cli --version
```

QWarp validates executable locations and permissions. A command working in your terminal does not
necessarily mean a desktop-launched QWarp can discover or trust the same executable. Use the official
package's system installation, and include its path in a bug report if detection still fails.
Do not copy client binaries into QWarp or work around executable validation.

## The WARP service is inactive

Inspect the service first:

```bash
systemctl status warp-svc --no-pager
```

Use QWarp's **Enable service** button when offered and complete the system authorization prompt.
Alternatively, use the service-start command in [usage and verification](../README.md#usage-and-verification).
If authorization fails, check that your session has a working polkit authentication agent and that
your account is permitted to control the service. If the service unit is missing, check the official
client installation. Reinstalling the QWarp GUI does not install a missing official service unit.

## Registration or browser authentication does not complete

For personal setup, the **Continue** button requires the displayed terms checkbox to be selected.
Read any inline error and confirm the official service is running and your network is reachable.

For organization setup, use the organization name provided by your administrator. When QWarp shows
**Complete organization sign-in**, finish the browser authentication and allow the status to refresh.
If authentication does not finish, contact your administrator about enrollment permissions and
identity-provider access. Follow the [enrollment steps](USAGE.md#organization-enrollment).
Do not post authentication URLs, tokens, or license keys in an issue.

## Settings are disabled or controlled by the organization

Some controls remain disabled while settings load or an action is running. Wait for that action to
finish and check the displayed status. Available features also depend on the installed official CLI.

For Zero Trust registrations, organization policy can restrict mode switching and connection controls.
Split-tunnel and fallback-domain editing are personal-only features in QWarp. Their disabled state
on a managed device is expected; ask your administrator to change organization policy when needed.
See [connection modes](USAGE.md#connection-modes-and-protocols) for the control locations.

## No system tray icon

Some desktop sessions do not expose a system tray to Qt. QWarp remains usable through its main window.
When no tray is detected, **Start minimized to system tray** and close-to-hide are disabled; closing
the window exits QWarp. Launch `qwarp` or use the application menu to reopen it.

If you expected a tray icon, check your desktop's tray configuration. Report the desktop environment,
session type (Wayland or X11), and whether QWarp's main window opens. A missing tray alone does not
mean the WARP tunnel has failed.

## Collect diagnostics for a bug report

Record your distribution and version, desktop environment, Wayland/X11 session type, installation
method, steps to reproduce, and expected versus actual behavior. Collect version and status output:

```bash
qwarp --version
warp-cli --version
qwarp --status-json
```

For diagnostic logging, quit the existing QWarp instance first, then launch:

```bash
qwarp --debug
```

Reproduce the problem and copy the relevant terminal messages. QWarp sanitizes diagnostic logging,
but review output and screenshots before sharing: remove license keys, tokens, account/device
identifiers, organization details, and private network information. The Account tab can reveal
license information, so leave it hidden in screenshots.

Use [GitHub Issues](https://github.com/iashutoshtiwari/qwarp/issues) and include only the relevant,
reviewed output. See [contributing](../CONTRIBUTING.md#report-a-bug-or-propose-a-change) for reporting guidance.

Return to the [README](../README.md) or [usage guide](USAGE.md).
