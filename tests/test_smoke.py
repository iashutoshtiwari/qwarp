"""
QWarp Smoke Tests
-----------------
These tests validate the non-Qt core layer (engine, state) and the package
metadata without requiring a running Cloudflare WARP daemon or display server.

PyQt6 is available in the test environment but all Qt-dependent tests use
QT_QPA_PLATFORM=offscreen (set in ci.yml) so no display server is needed.
"""

import re
import subprocess
from unittest.mock import patch, MagicMock

import pytest

import qwarp
from qwarp.core.engine import WarpEngine, WarpState


# ─────────────────────────────────────────────────────────────────────────────
# Package metadata
# ─────────────────────────────────────────────────────────────────────────────

class TestPackageMetadata:
    def test_version_is_defined(self):
        """__version__ must exist and be a non-empty string."""
        assert isinstance(qwarp.__version__, str)
        assert len(qwarp.__version__) > 0

    def test_version_is_semver(self):
        """__version__ must follow MAJOR.MINOR.PATCH (optionally with pre-release suffix)."""
        pattern = r"^\d+\.\d+\.\d+([._-].+)?$"
        assert re.match(pattern, qwarp.__version__), (
            f"Version '{qwarp.__version__}' is not valid semver"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WarpState enum
# ─────────────────────────────────────────────────────────────────────────────

class TestWarpState:
    def test_all_states_defined(self):
        """All expected daemon states must be present in the WarpState enum."""
        expected = {
            "CONNECTED",
            "DISCONNECTED",
            "CONNECTING",
            "UNREGISTERED",
            "SERVICE_STOPPED",
            "DAEMON_ERROR",
            "UNKNOWN",
        }
        actual = {member.name for member in WarpState}
        assert expected == actual, f"Missing states: {expected - actual}"

    def test_states_are_unique(self):
        """Each WarpState member must have a unique value."""
        values = [s.value for s in WarpState]
        assert len(values) == len(set(values))


# ─────────────────────────────────────────────────────────────────────────────
# WarpEngine – unit tests with mocked subprocess
# ─────────────────────────────────────────────────────────────────────────────

class TestWarpEngine:
    def _make_engine(self) -> WarpEngine:
        return WarpEngine(timeout=2.0)

    def _make_proc(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
        proc = MagicMock()
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    # ── status() parsing ─────────────────────────────────────────────────────

    @patch("subprocess.run")
    def test_status_connected(self, mock_run):
        mock_run.return_value = self._make_proc(stdout="Status update: Connected")
        assert WarpEngine().status() == WarpState.CONNECTED

    @patch("subprocess.run")
    def test_status_disconnected(self, mock_run):
        mock_run.return_value = self._make_proc(stdout="Status update: Disconnected")
        assert WarpEngine().status() == WarpState.DISCONNECTED

    @patch("subprocess.run")
    def test_status_connecting(self, mock_run):
        mock_run.return_value = self._make_proc(stdout="Status update: Connecting")
        assert WarpEngine().status() == WarpState.CONNECTING

    @patch("subprocess.run")
    def test_status_unregistered(self, mock_run):
        mock_run.return_value = self._make_proc(stdout="Registration Missing")
        assert WarpEngine().status() == WarpState.UNREGISTERED

    @patch("subprocess.run")
    def test_status_service_stopped_when_inactive(self, mock_run):
        """When warp-cli fails AND systemctl reports inactive, return SERVICE_STOPPED."""
        # First call: warp-cli status → fails
        # Second call: systemctl is-active → "inactive"
        mock_run.side_effect = [
            self._make_proc(returncode=1, stderr="error"),
            self._make_proc(returncode=1, stdout="inactive"),  # is-active
        ]
        assert WarpEngine().status() == WarpState.SERVICE_STOPPED

    @patch("subprocess.run")
    def test_status_daemon_error_when_active(self, mock_run):
        """When warp-cli fails BUT systemctl reports active, return DAEMON_ERROR."""
        mock_run.side_effect = [
            self._make_proc(returncode=1, stderr="error"),
            self._make_proc(returncode=0, stdout="active"),  # is-active
        ]
        assert WarpEngine().status() == WarpState.DAEMON_ERROR

    # ── connect / disconnect ──────────────────────────────────────────────────

    @patch("subprocess.run")
    def test_connect_returns_true_on_success(self, mock_run):
        mock_run.return_value = self._make_proc(returncode=0, stdout="Success")
        assert WarpEngine().connect() is True

    @patch("subprocess.run")
    def test_connect_returns_false_on_failure(self, mock_run):
        mock_run.return_value = self._make_proc(returncode=1, stderr="error")
        assert WarpEngine().connect() is False

    @patch("subprocess.run")
    def test_disconnect_returns_true_on_success(self, mock_run):
        mock_run.return_value = self._make_proc(returncode=0, stdout="Success")
        assert WarpEngine().disconnect() is True

    # ── CLI not installed ─────────────────────────────────────────────────────

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_run_command_handles_missing_cli(self, _):
        """_run_command must not raise when warp-cli is not on PATH."""
        ok, msg = WarpEngine()._run_command("connect")
        assert ok is False
        assert "not installed" in msg.lower()

    # ── timeout ──────────────────────────────────────────────────────────────

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="warp-cli", timeout=2))
    def test_run_command_handles_timeout(self, _):
        """_run_command must not raise on daemon timeout."""
        ok, msg = WarpEngine()._run_command("connect")
        assert ok is False
        assert "timeout" in msg.lower()

    # ── set_mode ─────────────────────────────────────────────────────────────

    @patch("subprocess.run")
    def test_set_mode_passes_correct_args(self, mock_run):
        mock_run.return_value = self._make_proc(returncode=0, stdout="ok")
        WarpEngine().set_mode("doh")
        call_args = mock_run.call_args[0][0]
        assert "mode" in call_args
        assert "doh" in call_args

    # ── utils.system (non-Qt portion) ────────────────────────────────────────

    def test_get_asset_dir_returns_string(self):
        """get_asset_dir() should always return a path string regardless of env."""
        from qwarp.utils.system import get_asset_dir
        result = get_asset_dir()
        assert isinstance(result, str)
        assert len(result) > 0
