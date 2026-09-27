import subprocess
from unittest.mock import patch

import pytest


class TestAutostart:
    """Tests for XDG autostart .desktop file management."""

    @pytest.mark.parametrize(
        ("content", "enabled"),
        [
            ("[Desktop Entry]\n# Hidden=true\nExec=qwarp\n", True),
            ("[Desktop Entry]\nComment=Hidden=true\nExec=qwarp\n", True),
            ("[Desktop Entry]\nHidden = true\n", False),
            ("[Desktop Entry]\nX-GNOME-Autostart-enabled = false\n", False),
            ("[Desktop Entry]\nExec=qwarp\n[Desktop Action Other]\nHidden=true\n", True),
            ("[Desktop Action Other]\nExec=qwarp\n", False),
        ],
    )
    def test_autostart_reads_only_desktop_entry_keys(self, tmp_path, monkeypatch, content, enabled):
        from qwarp.platform.autostart import DESKTOP_FILENAME, is_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        (tmp_path / DESKTOP_FILENAME).write_text(content)
        assert is_autostart_enabled() is enabled

    def test_autostart_invalid_encoding_is_unavailable(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, is_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        (tmp_path / DESKTOP_FILENAME).write_bytes(b"[Desktop Entry]\nName=\xff\n")
        assert is_autostart_enabled() is False

    def test_autostart_creates_desktop_file(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        with patch("qwarp.platform.autostart.resolve_executable", return_value="/usr/bin/qwarp"):
            success, _msg = set_autostart_enabled(True)
        assert success
        desktop_file = tmp_path / DESKTOP_FILENAME
        assert desktop_file.exists()
        content = desktop_file.read_text()
        assert 'Exec="/usr/bin/qwarp"' in content
        assert "Type=Application" in content
        assert "Name=QWarp" in content

    def test_autostart_with_minimize(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        with patch("qwarp.platform.autostart.resolve_executable", return_value="/usr/bin/qwarp"):
            success, _ = set_autostart_enabled(True, minimize=True)
        assert success
        content = (tmp_path / DESKTOP_FILENAME).read_text()
        assert "--start-minimized" in content

    def test_autostart_disable_removes_file(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        desktop_file = tmp_path / DESKTOP_FILENAME
        desktop_file.write_text("[Desktop Entry]\nType=Application\n")

        success, _ = set_autostart_enabled(False)
        assert success
        assert not desktop_file.exists()

    def test_autostart_disable_when_not_enabled(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        success, msg = set_autostart_enabled(False)
        assert success
        assert "already disabled" in msg.lower()

    def test_autostart_is_enabled_detects_hidden(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, is_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        desktop_file = tmp_path / DESKTOP_FILENAME
        desktop_file.write_text("[Desktop Entry]\nHidden=true\n")
        assert is_autostart_enabled() is False

    def test_autostart_is_enabled_detects_gnome_disabled(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, is_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        desktop_file = tmp_path / DESKTOP_FILENAME
        desktop_file.write_text("[Desktop Entry]\nX-GNOME-Autostart-enabled=false\n")
        assert is_autostart_enabled() is False

    def test_autostart_is_enabled_returns_true_for_valid(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, is_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        desktop_file = tmp_path / DESKTOP_FILENAME
        desktop_file.write_text("[Desktop Entry]\nType=Application\nExec=qwarp\n")
        assert is_autostart_enabled() is True

    def test_autostart_missing_executable_fails_safely(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        with patch("qwarp.platform.autostart.resolve_executable", side_effect=FileNotFoundError):
            success, _msg = set_autostart_enabled(True)
        assert success is False
        assert not (tmp_path / DESKTOP_FILENAME).exists()

    def test_autostart_idempotent_enable(self, tmp_path, monkeypatch):
        from qwarp.platform.autostart import DESKTOP_FILENAME, set_autostart_enabled

        monkeypatch.setattr("qwarp.platform.autostart.AUTOSTART_DIR", tmp_path)
        with patch("qwarp.platform.autostart.resolve_executable", return_value="/usr/bin/qwarp"):
            set_autostart_enabled(True)
            success, _ = set_autostart_enabled(True)
        assert success
        assert (tmp_path / DESKTOP_FILENAME).exists()


class TestTaskbar:
    """Tests for warp-taskbar systemd user-service suppression."""

    @patch("qwarp.utils.process.run_command")
    def test_is_taskbar_masked_true(self, mock_run):
        from qwarp.platform.taskbar import is_taskbar_masked

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="UnitFileState=masked\nActiveState=inactive\n", stderr=""
        )
        assert is_taskbar_masked() is True

    @patch("qwarp.utils.process.run_command")
    def test_is_taskbar_masked_false(self, mock_run):
        from qwarp.platform.taskbar import is_taskbar_masked

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="UnitFileState=enabled\nActiveState=inactive\n", stderr=""
        )
        assert is_taskbar_masked() is False

    @patch("qwarp.utils.process.run_command")
    def test_is_taskbar_running(self, mock_run):
        from qwarp.platform.taskbar import is_taskbar_running

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="UnitFileState=enabled\nActiveState=active\n", stderr=""
        )
        assert is_taskbar_running() is True

    @patch("qwarp.utils.process.run_command")
    def test_suppress_when_not_masked(self, mock_run):
        from qwarp.platform.taskbar import suppress_taskbar

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        success, msg = suppress_taskbar()
        assert success
        assert "suppressed" in msg.lower()
        assert mock_run.call_args.args[0] == [
            "systemctl",
            "--user",
            "mask",
            "--now",
            "warp-taskbar.service",
        ]

    @patch("qwarp.utils.process.run_command")
    def test_suppress_idempotent_when_already_masked(self, mock_run):
        from qwarp.platform.taskbar import suppress_taskbar

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        success, msg = suppress_taskbar()
        assert success
        assert "suppressed" in msg.lower()
        assert mock_run.call_count == 1

    @patch("qwarp.utils.process.run_command")
    def test_restore_when_masked(self, mock_run):
        from qwarp.platform.taskbar import restore_taskbar

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        success, msg = restore_taskbar()
        assert success
        assert "restored" in msg.lower()

    @patch("qwarp.utils.process.run_command")
    def test_restore_restarts_previously_running_taskbar(self, mock_run):
        from qwarp.platform.taskbar import restore_taskbar

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
            subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""),
        ]
        success, _message = restore_taskbar(start=True)
        assert success
        assert mock_run.call_args_list[-1].args[0] == [
            "systemctl",
            "--user",
            "start",
            "warp-taskbar.service",
        ]

    @patch("qwarp.utils.process.run_command")
    def test_restore_idempotent_when_not_masked(self, mock_run):
        from qwarp.platform.taskbar import restore_taskbar

        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="enabled\n", stderr="")
        success, msg = restore_taskbar()
        assert success
        assert "restored" in msg.lower()
        assert mock_run.call_count == 1

    @patch("qwarp.utils.process.run_command", side_effect=FileNotFoundError)
    def test_taskbar_operations_handle_missing_systemctl(self, _mock_run):
        from qwarp.platform.taskbar import is_taskbar_masked, suppress_taskbar

        assert is_taskbar_masked() is False
        success, msg = suppress_taskbar()
        assert success is False
        assert "exception" in msg.lower()

    @patch("qwarp.utils.process.run_command", side_effect=subprocess.TimeoutExpired(cmd="systemctl", timeout=10))
    def test_taskbar_handles_timeout(self, _mock_run):
        from qwarp.platform.taskbar import is_taskbar_masked

        assert is_taskbar_masked() is False
