import hashlib
import shlex
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


def test_forbidden_member_shell_guard_actually_aborts(tmp_path):
    workflow = (ROOT / ".github/workflows/packages.yml").read_text()
    workflow_path = "/tmp/package-files"  # noqa: S108 - workflow literal is replaced with tmp_path below
    lines = workflow.splitlines()
    start = next(i for i, line in enumerate(lines) if "if rg" in line and workflow_path in line)
    end = next(i for i in range(start, len(lines)) if lines[i].strip() == "fi")
    guard = "\n".join(line.strip() for line in lines[start : end + 1])
    members = tmp_path / "members"
    command = guard.replace(workflow_path, shlex.quote(str(members))) + "\necho continued"
    members.write_text("usr/bin/warp-cli\n")
    result = subprocess.run(["bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode != 0 and "continued" not in result.stdout
    members.write_text("usr/bin/qwarp\n")
    result = subprocess.run(["bash", "-e", "-c", command], capture_output=True, text=True)
    assert result.returncode == 0 and "continued" in result.stdout


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
