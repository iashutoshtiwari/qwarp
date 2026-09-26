import json
import subprocess
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QCoreApplication, QSettings
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp(tmp_path_factory):
    app = QApplication.instance() or QApplication([])
    app.setOrganizationName("qwarp-tests")
    app.setApplicationName("qwarp-tests")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path_factory.mktemp("settings")))
    yield app


@pytest.fixture
def wait_until(qapp):
    def wait(predicate, timeout: float = 2.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            QCoreApplication.processEvents()
            if predicate():
                return
            time.sleep(0.01)
        QCoreApplication.processEvents()
        assert predicate(), "condition was not met before timeout"

    return wait


# ======================================================================
# Sanitized real-response fixtures
# These fixtures contain NO personal data, device IDs, organization secrets,
# license keys, auth URLs, or private tokens.
# ======================================================================

SANITIZED_STATUS_FIXTURES = {
    "connected": {"status": "Connected"},
    "disconnected": {"status": "Disconnected"},
    "connecting": {"status": "Connecting"},
    "unregistered": {
        "status": "Unable",
        "reason": {"RegistrationMissing": {"Invalidated": "ManualDeletion"}},
    },
    "no_network": {
        "code": "NetworkUnavailable",
        "error": "No network connection is available.",
    },
    "policy_restricted": {
        "code": "PolicyRestricted",
        "error": "This action is managed by your organization",
    },
    "auth_required": {
        "code": "AuthenticationRequired",
        "error": "Reauthentication required",
    },
    "daemon_unavailable": {
        "code": "DaemonUnavailable",
        "error": "daemon IPC unavailable",
    },
    "unknown_fields": {
        "status": "Connected",
        "future_protocol_feature": True,
        "unexpected_counters": [1, 2, 3],
    },
}

SANITIZED_SETTINGS_FIXTURES = {
    "personal": {
        "settings": {
            "operation_mode": "warp+doh",
            "families_mode": "off",
            "warp_tunnel_protocol": "MASQUE",
            "proxy_port": 40000,
            "always_on": False,
            "switch_locked": False,
            "split_tunnel_mode": "exclude",
            "disable_for_wifi": False,
            "disable_for_ethernet": False,
        },
        "sources": {"operation_mode": "user_set"},
    },
    "zero_trust": {
        "settings": {
            "operation_mode": "warp",
            "families_mode": "malware",
            "warp_tunnel_protocol": "WireGuard",
            "proxy_port": 40000,
            "always_on": True,
            "switch_locked": True,
            "split_tunnel_mode": "exclude",
            "disable_for_wifi": False,
            "disable_for_ethernet": False,
        },
        "sources": {"operation_mode": "organization"},
    },
}

SANITIZED_REGISTRATION_FIXTURES = {
    "personal": {
        "id": "synthetic-registration-id",
        "device_id": "synthetic-device-id",
        "account": {
            "type": "Free",
            "license": "masked-license-value",
            "quota": "Unlimited",
        },
    },
    "zero_trust": {
        "id": "synthetic-registration-id",
        "device_id": "synthetic-device-id",
        "account": {
            "type": "Teams",
            "license": "masked-license-value",
            "quota": "Unlimited",
        },
    },
}

SANITIZED_NETWORK_FIXTURES = {
    "network_info": {
        "v4_iface": {"name": "eth0", "address": "192.0.2.10", "kind": "ethernet"},
        "v6_iface": None,
        "dns_servers": ["1.1.1.1", "1.0.0.1"],
        "gateway": "192.0.2.1",
    },
    "split_tunnel": {
        "settings": {
            "split_tunnel_mode": "exclude",
            "split_tunnel_ips": [{"value": "192.0.2.0/24"}, {"value": "198.51.100.1"}],
            "split_tunnel_hosts": [{"value": "internal.example.org"}],
            "fallback_domains": [{"domain": "corp.example.org"}],
        },
        "sources": {},
    },
    "override": {"set": False, "ends_in_secs": 0},
}


def make_completed_process(stdout: str = "", stderr: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    """Create a CompletedProcess for mocking subprocess.run."""
    return subprocess.CompletedProcess(args=["fake"], returncode=returncode, stdout=stdout, stderr=stderr)


def make_json_process(data: Any, returncode: int = 0) -> subprocess.CompletedProcess:
    """Create a CompletedProcess containing serialized JSON stdout."""
    return make_completed_process(stdout=json.dumps(data), returncode=returncode)


class WarpCommandRouter:
    """Deterministic command router for mocking subprocess.run calls to warp-cli / systemctl.

    Routes invocations based on command line arguments rather than invocation order.
    """

    def __init__(self):
        self.routes: list[tuple[Any, Any]] = []
        self.calls: list[list[str]] = []
        self._setup_defaults()

    def _setup_defaults(self):
        # Default CLI probes
        self.register(["warp-cli", "--version"], make_completed_process(stdout="warp-cli 2026.7.1377.0\n"))
        self.register(
            ["tunnel", "protocol", "--help"],
            make_completed_process(stdout="  - MASQUE: default\n  - WireGuard: legacy\n"),
        )
        self.register(["tunnel", "ip", "--help"], make_completed_process(stdout="Commands:\n  list\n  add\n  remove\n"))
        self.register(
            ["dns", "fallback", "--help"], make_completed_process(stdout="Commands:\n  list\n  add\n  remove\n")
        )
        self.register(["--json", "mode-switch-allowed"], make_json_process({"allowed": True}))
        self.register(["--json", "registration", "organization"], make_json_process({"error": "No org"}, returncode=1))
        self.register(["--json", "status"], make_json_process(SANITIZED_STATUS_FIXTURES["connected"]))
        self.register(["status"], make_completed_process(stdout="Status update: Connected\nSuccess\n"))
        self.register(["--json", "settings"], make_json_process(SANITIZED_SETTINGS_FIXTURES["personal"]))
        self.register(
            ["--json", "registration", "show"], make_json_process(SANITIZED_REGISTRATION_FIXTURES["personal"])
        )
        self.register(["systemctl", "is-active"], make_completed_process(stdout="active\n"))

    def register(self, matcher: Any, response: Any):
        """Register a handler. Matcher can be a list/tuple of tokens, a substring, or callable.
        Response can be CompletedProcess, Exception, or callable(cmd_list, **kwargs).
        Newer registrations take precedence.
        """
        self.routes.insert(0, (matcher, response))

    def on(
        self,
        matcher: Any,
        *,
        text: str | None = None,
        json_data: Any = None,
        returncode: int = 0,
        side_effect: Any = None,
    ):
        """Convenience method to register a command handler."""
        if side_effect is not None:
            self.register(matcher, side_effect)
        elif json_data is not None:
            self.register(matcher, make_json_process(json_data, returncode=returncode))
        else:
            self.register(matcher, make_completed_process(stdout=text or "", returncode=returncode))

    def __call__(self, cmd, *args, **kwargs):
        cmd_list = [str(c) for c in (cmd if isinstance(cmd, (list, tuple)) else [cmd])]
        self.calls.append(cmd_list)

        for matcher, response in self.routes:
            matched = False
            if callable(matcher):
                matched = matcher(cmd_list)
            elif isinstance(matcher, (list, tuple)):
                matched = self._match_tokens(cmd_list, list(matcher))
            elif isinstance(matcher, str):
                matched = matcher in cmd_list

            if matched:
                if isinstance(response, type) and issubclass(response, Exception):
                    raise response()
                if isinstance(response, Exception):
                    raise response
                if callable(response) and not isinstance(response, (subprocess.CompletedProcess, MagicMock)):
                    return response(cmd_list, **kwargs)
                return response

        raise AssertionError(f"WarpCommandRouter received unexpected command: {cmd_list}")

    def _match_tokens(self, cmd_list: list[str], tokens: list[str]) -> bool:
        it = iter(cmd_list)
        return all(tok in it for tok in tokens)


@pytest.fixture
def warp_router():
    """Fixture providing a deterministic WarpCommandRouter."""
    return WarpCommandRouter()


@pytest.fixture(autouse=True)
def forbid_live_daemon_commands(monkeypatch):
    original = subprocess.Popen

    def guarded(command, *args, **kwargs):
        executable = command[0] if isinstance(command, (list, tuple)) else command
        if Path(str(executable)).name in {"warp-cli", "warp-svc", "systemctl", "pkexec"}:
            raise AssertionError("Tests must not execute live daemon or service commands")
        return original(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", guarded)
