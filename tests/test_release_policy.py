import hashlib
import shlex
import shutil
import subprocess
import tarfile

import pytest

from scripts.check_release import (
    ROOT,
    check_no_bundled_native,
    check_source_checksum,
    public_files,
    verify_checksums,
    write_checksums,
)

VERSION = "0.10.1"


@pytest.fixture
def candidate(tmp_path):
    for name in (f"qwarp-{VERSION}-source.tar.gz", f"qwarp-{VERSION}.tar.gz", f"qwarp-{VERSION}-py3-none-any.whl"):
        (tmp_path / name).write_bytes(b"candidate")
    write_checksums(VERSION, tmp_path)
    return tmp_path


def test_checksums_cover_every_public_input(candidate):
    files = verify_checksums(VERSION, candidate)
    assert len(files) == 3
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() in (candidate / "SHA256SUMS").read_text() for p in files)
    with pytest.raises(ValueError, match=r"native|missing"):
        verify_checksums(VERSION, candidate, require_native=True)
    (candidate / "qwarp_0.10.1-1_all.deb").write_bytes(b"deb")
    (candidate / "qwarp-0.10.1-1.fc44.noarch.rpm").write_bytes(b"rpm")
    write_checksums(VERSION, candidate, require_native=True)
    assert len(verify_checksums(VERSION, candidate, require_native=True)) == 5


@pytest.mark.parametrize("name", ["unexpected.tar.gz", "qwarp-0.10.2-source.tar.gz", "notes.json"])
def test_forbidden_public_artifacts_fail_closed(candidate, name):
    (candidate / name).write_bytes(b"unapproved")
    with pytest.raises(ValueError, match="Unexpected release artifacts"):
        public_files(VERSION, candidate)
    with pytest.raises(ValueError, match="Unexpected release artifacts"):
        write_checksums(VERSION, candidate)


def test_corrupt_and_incomplete_checksums_are_rejected(candidate):
    source = candidate / f"qwarp-{VERSION}-source.tar.gz"
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="mismatch"):
        verify_checksums(VERSION, candidate)
    write_checksums(VERSION, candidate)
    checksum = candidate / "SHA256SUMS"
    checksum.write_text(checksum.read_text().splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="exactly cover"):
        verify_checksums(VERSION, candidate)


def test_release_rejects_symlinks_and_duplicate_checksums(candidate, tmp_path):
    checksum = candidate / "SHA256SUMS"
    content = checksum.read_text()
    checksum.write_text(content + content)
    with pytest.raises(ValueError, match="duplicate"):
        verify_checksums(VERSION, candidate)
    checksum.unlink()
    outside = tmp_path / "outside"
    outside.write_text("preserved")
    checksum.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        write_checksums(VERSION, candidate)
    assert outside.read_text() == "preserved"


@pytest.mark.parametrize("name,content", [("data/renamed", b"\x7fELFabc"), ("data/library.so.6", b"object")])
def test_application_archives_reject_bundled_native_code(name, content):
    with pytest.raises(ValueError, match="native object"):
        check_no_bundled_native([name], lambda _: content)


def test_source_archive_is_deterministic_and_preserves_existing_output(tmp_path):
    outputs = [tmp_path / "first.tar.gz", tmp_path / "second.tar.gz"]
    for output in outputs:
        subprocess.run(["bash", "scripts/build_source_archive.sh", VERSION, str(output)], cwd=ROOT, check=True)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    with tarfile.open(outputs[0]) as archive:
        names = set(archive.getnames())
        assert f"qwarp-{VERSION}/packaging/debian/rules" in names
        assert f"qwarp-{VERSION}/packaging/rpm/qwarp.spec" in names
        assert not any(name.endswith(("/PKGBUILD", "/.SRCINFO")) for name in names)
    result = subprocess.run(
        ["bash", "scripts/build_source_archive.sh", VERSION, str(outputs[0])], cwd=ROOT, capture_output=True
    )
    assert result.returncode != 0
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    symlink = tmp_path / "dangling.tar.gz"
    missing_target = tmp_path / "must-not-create"
    symlink.symlink_to(missing_target)
    result = subprocess.run(
        ["bash", "scripts/build_source_archive.sh", VERSION, str(symlink)], cwd=ROOT, capture_output=True
    )
    assert result.returncode != 0 and not missing_target.exists()


@pytest.fixture(params=["members", "arch-metadata"])
def package_shell_guard(request, tmp_path, monkeypatch):
    workflow = (ROOT / ".github/workflows/packages.yml").read_text()
    if request.param == "members":
        workflow_path = "/tmp/package-files"  # noqa: S108 - workflow literal is replaced with tmp_path below
        forbidden = ["usr/bin/warp-cli", "warp-svc", "usr/lib/systemd/system/warp-svc.service", "usr/lib/libwarp.so"]
        clean = "usr/bin/qwarp\nusr/bin/warp-cli-helper\nusr/lib/libwarp/subdir\n"
    else:
        workflow_path = "packaging/arch/.SRCINFO"
        forbidden = ["\tconflicts = cloudflare-warp-bin", "  install = qwarp.install"]
        clean = "\tdepends = cloudflare-warp-bin\n\tlicense = GPL-3.0-only\n"
    lines = workflow.splitlines()
    start = next(i for i, line in enumerate(lines) if "grep -E" in line and workflow_path in line) - 1
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "esac")
    guard = "\n".join(line.strip() for line in lines[start : end + 1])
    members = tmp_path / "members"
    command = guard.replace(workflow_path, shlex.quote(str(members))) + "\necho continued"

    # Reproduce the runner's lack of rg without adding a test dependency on it.
    grep = shutil.which("grep")
    assert grep is not None
    commands = tmp_path / "bin"
    commands.mkdir()
    (commands / "grep").symlink_to(grep)
    monkeypatch.setenv("PATH", str(commands))
    return command, members, forbidden, clean


def test_forbidden_member_shell_guard_actually_aborts(package_shell_guard):
    command, members, forbidden, clean = package_shell_guard
    for entry in forbidden:
        members.write_text(f"{entry}\n")
        result = subprocess.run(["/bin/bash", "-e", "-c", command], capture_output=True, text=True)
        assert result.returncode == 1 and "continued" not in result.stdout
    members.write_text(clean)
    result = subprocess.run(["/bin/bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode == 0 and "continued" in result.stdout


def test_package_shell_guard_fails_closed_on_unreadable_input(package_shell_guard):
    command, _members, _forbidden, _clean = package_shell_guard
    result = subprocess.run(["/bin/bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode == 2 and "continued" not in result.stdout


def test_package_shell_guard_fails_closed_without_grep(package_shell_guard, tmp_path, monkeypatch):
    command, members, _forbidden, clean = package_shell_guard
    members.write_text(clean)
    monkeypatch.setenv("PATH", str(tmp_path / "no-commands"))
    result = subprocess.run(["/bin/bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode == 127 and "continued" not in result.stdout


@pytest.mark.parametrize(
    "scenario,expected_status",
    [("existing", 1), ("unused", 0), ("empty", 0), ("missing", 2), ("unreadable", 2), ("no-grep", 127)],
)
def test_release_version_shell_guard_fails_closed(tmp_path, monkeypatch, scenario, expected_status):
    workflow = (ROOT / ".github/workflows/release.yml").read_text()
    lines = workflow.splitlines()
    start = next(i for i, line in enumerate(lines) if '"$RUNNER_TEMP/release-tags"' in line) + 1
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("      - name:"))
    command = "\n".join(line.strip() for line in lines[start:end]) + "\necho continued"
    tags = tmp_path / "release-tags"
    if scenario == "unreadable":
        tags.mkdir()  # A directory gives a read error even when tests run as root.
    elif scenario != "missing":
        tags.write_text(f"v{VERSION}\n" if scenario == "existing" else "" if scenario == "empty" else f"v{VERSION}0\n")
    grep = shutil.which("grep")
    assert grep is not None
    commands = tmp_path / "bin"
    commands.mkdir()
    if scenario != "no-grep":
        (commands / "grep").symlink_to(grep)
    monkeypatch.setenv("PATH", str(commands))
    monkeypatch.setenv("RUNNER_TEMP", str(tmp_path))
    monkeypatch.setenv("RELEASE_VERSION", VERSION)
    result = subprocess.run(["/bin/bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode == expected_status
    assert ("continued" in result.stdout) == (expected_status == 0)


@pytest.mark.parametrize("stale", ["PKGBUILD", ".SRCINFO"])
def test_release_checksum_must_match_both_arch_declarations(candidate, monkeypatch, stale):
    root = candidate / "checkout"
    arch = root / "packaging/arch"
    arch.mkdir(parents=True)
    digest = hashlib.sha256((candidate / f"qwarp-{VERSION}-source.tar.gz").read_bytes()).hexdigest()
    (arch / "PKGBUILD").write_text(f"sha256sums=('{digest}')\n")
    (arch / ".SRCINFO").write_text(f"\tsha256sums = {digest}\n")
    monkeypatch.setattr("scripts.check_release.ROOT", root)
    check_source_checksum(VERSION, candidate)
    path = arch / stale
    path.write_text(path.read_text().replace(digest, "0" * 64))
    with pytest.raises(ValueError, match="Source checksum mismatch"):
        check_source_checksum(VERSION, candidate)
