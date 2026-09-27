import subprocess

import pytest

from scripts.clean_build import cleanup


@pytest.fixture
def checkout(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for name in (
        "build/output",
        "dist/output",
        "src/qwarp/__pycache__/code.pyc",
        ".venv/keep",
        "src/qwarp.egg-info/keep",
        "src/qwarp/assets/locales/qwarp_en.qm",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    return tmp_path


def test_cleanup_preserves_environment_and_local_assets(checkout):
    cleanup(checkout, dry_run=True)
    assert (checkout / "dist/output").exists()
    cleanup(checkout)
    assert not (checkout / "dist").exists()
    assert not (checkout / "build").exists()
    assert not (checkout / "src/qwarp/__pycache__").exists()
    for name in (".venv/keep", "src/qwarp.egg-info/keep", "src/qwarp/assets/locales/qwarp_en.qm"):
        assert (checkout / name).exists()


def test_cleanup_checks_all_tracked_targets_before_deleting(checkout):
    subprocess.run(["git", "add", "dist/output"], cwd=checkout, check=True)
    with pytest.raises(RuntimeError, match="tracked files"):
        cleanup(checkout)
    assert (checkout / "build/output").exists()
    assert (checkout / "dist/output").exists()


def test_cleanup_refuses_symlink_targets(checkout, tmp_path):
    external = tmp_path / "preserved"
    external.mkdir()
    (external / "keep").touch()
    (checkout / ".pytest_cache").symlink_to(external, target_is_directory=True)
    with pytest.raises(RuntimeError, match="symlinked cleanup target"):
        cleanup(checkout)
    assert (external / "keep").exists()
    assert (checkout / "build/output").exists()
