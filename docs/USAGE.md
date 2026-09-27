# Using QWarp on Linux

QWarp controls a separately installed official Cloudflare WARP client. Start with the
[requirements and installation instructions](../README.md#requirements).
For errors, see [troubleshooting](TROUBLESHOOTING.md).

## First launch and personal registration

1. Launch **QWarp** from your desktop application menu or run `qwarp` in a terminal.
2. If setup appears, read the linked Cloudflare Application Terms and Application Privacy Policy.
   Select the consent checkbox if you agree, then choose **Continue** for personal registration.
3. Once registration is ready, use the main connection toggle to connect or disconnect.
   Read the status and mode beneath it to confirm the result.

An existing registration may take you directly to the connection view; QWarp can still ask for
terms acceptance when needed. If **Enable service** appears, see
[daemon troubleshooting](TROUBLESHOOTING.md#the-warp-service-is-inactive).
Open settings with the gear button in the main window.

## Organization enrollment

During setup, choose **Connect to an organization**, enter the **Organization name** provided by
your administrator, review and accept the displayed terms, and choose **Continue**. Complete the
organization's authentication in your browser when QWarp shows **Complete organization sign-in**.
After enrollment, the main window displays the organization badge when its name is available.

These steps describe enrollment from setup, not switching an already registered device to a new
organization. Contact your administrator before changing an existing managed registration.
Organization policy can restrict connection and mode controls. QWarp does not override that policy.
Split-tunnel and fallback-domain editing are available only for personal registrations.

## Connection modes and protocols

Open **Settings → Connection** and use **Routing Mode**. Selection changes are applied immediately;
wait for the resulting status before making another change. Available controls depend on the
installed official client, current state, and organization policy.

| Routing Mode | Purpose |
| --- | --- |
| 1.1.1.1 with WARP | Route traffic through the WARP tunnel. |
| 1.1.1.1 (DNS over DoH) | Use DNS over HTTPS without routing general traffic through WARP. |
| 1.1.1.1 (DNS over DoT) | Use DNS over TLS without routing general traffic through WARP. |
| WARP + DoH | Combine the WARP tunnel with DNS over HTTPS. |
| WARP + DoT | Combine the WARP tunnel with DNS over TLS. |
| Local Proxy | Make WARP available through a local proxy; applications must use that proxy. |
| Tunnel Only | Route traffic through the tunnel without DNS changes. |

In DNS-only mode, **ACTIVE** means the DNS service is active, not that all traffic is tunneled.
For **Local Proxy**, configure **Proxy Port** and the applications that should use it.

**Tunnel Protocol** offers the protocols detected from the official client, such as
**MASQUE (Default)** and **WireGuard (Legacy)**. A protocol may be unavailable with your client version.
The same tab provides **DNS Content Filtering** and trusted-network auto-disconnect settings when
supported. Managed registrations can restrict these settings.

## Split tunneling

For a personal registration with a supported official client, open **Settings → Split Tunneling**.
Add an IP address or network under **IP addresses and networks**, or a hostname under **Hostnames**,
then choose the corresponding **Add** button. Select an existing rule and choose **Remove** to delete it.

The personal exclusion rules route matching traffic outside the WARP tunnel. Use only rules intended
for your network; examples such as `192.168.1.0/24` and `internal.example.com` are placeholders.
**Restore defaults** asks for confirmation before restoring the official default IP and hostname rules.
The **Diagnostics** tab shows the split-tunnel mode and rules. Editing is disabled for Zero Trust
registrations and when the installed client does not support the feature.

## Local fallback DNS

For a personal registration with a supported official client, open **Settings → DNS**.
Enter a domain that should use your local DNS resolver, then choose **Add domain**.
Select a rule and choose **Remove** to delete it. For example, a workplace might require local
resolution for its internal domain; use the actual domain supplied by its administrator.

Fallback DNS changes where names are resolved. To change how matching traffic is routed, use
[split tunneling](#split-tunneling). Fallback-domain editing is disabled for Zero Trust registrations
and when the installed client does not support it.

## Inspect status and diagnostics

The main window shows connection state and operating mode. **Settings → Account**, **Device**,
and **Diagnostics** provide account, device, daemon, policy, network, and tunnel information.

For a read-only status query that does not open the GUI:

```bash
qwarp --status-json
```

The JSON includes `schema_version`, `connection`, `mode`, `service`, `enrollment`, and
`organization_managed`. Inspect the fields rather than treating a successful exit code as proof of
an active tunnel. See the [CLI options](../README.md#command-line-options) and
[diagnostic-sharing guidance](TROUBLESHOOTING.md#collect-diagnostics-for-a-bug-report).

## Desktop and tray behavior

QWarp supports Wayland and X11. With an available system tray, closing the main window hides it;
use the tray menu's **Quit** action to exit. Without a tray, the main window stays accessible,
start-minimized is disabled, and closing the window exits QWarp.

Return to the [README](../README.md) or [FAQ](../README.md#faq).
