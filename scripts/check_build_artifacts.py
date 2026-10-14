#!/usr/bin/env python3
import hashlib
import re
import sys
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path

if __package__:
    from .release_policy import verify_checksums
else:
    from release_policy import verify_checksums

LICENSE_EXPRESSION = "GPL-3.0-only AND MIT AND Apache-2.0"
LEGAL_FILES = {"LICENSE", "LICENSES/Apache-2.0.txt", "LICENSES/Glyphs-Poly-MIT.txt", "TRADEMARKS.md"}
# Complete, unmodified https://www.gnu.org/licenses/gpl-3.0.txt, verified 2026-10-13.
GPL_SHA256 = "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986"
THIRD_PARTY_SHA256 = {
    "LICENSES/Apache-2.0.txt": "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30",
    "LICENSES/Glyphs-Poly-MIT.txt": "9ea8a12deea1b232d639881e35b0540f8678315ebcc27053a9d8359bd78ad040",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def check_license_metadata(content: bytes) -> None:
    metadata = BytesParser().parsebytes(content)
    require(metadata["License-Expression"] == LICENSE_EXPRESSION, "Incorrect SPDX License-Expression")
    require(set(metadata.get_all("License-File", [])) == LEGAL_FILES, "Incorrect License-File metadata")
    require(metadata["License"] is None, "Obsolete free-text License metadata")


def check_legal_files(read_file) -> None:
    require(hashlib.sha256(read_file("LICENSE")).hexdigest() == GPL_SHA256, "Root GPL text changed or missing")
    for name in LEGAL_FILES - {"LICENSE"}:
        require(bool(read_file(name).strip()), f"Empty legal notice: {name}")
    for name, digest in THIRD_PARTY_SHA256.items():
        require(hashlib.sha256(read_file(name)).hexdigest() == digest, f"Third-party license changed: {name}")


def check_no_cloudflare_files(names) -> None:
    for name in names:
        basename = Path(name).name.lower()
        require(
            not (basename in {"warp-cli", "warp-svc", "warp-svc.service"} or basename.startswith("libwarp")),
            f"Artifact contains Cloudflare runtime material: {name}",
        )


def check_frozen_contents(executable: Path) -> set[str]:
    # Inspect the archive without executing the application or any WARP command.
    from PyInstaller.archive.readers import CArchiveReader

    frozen = CArchiveReader(str(executable))
    check_no_cloudflare_files(frozen.toc)
    check_no_cloudflare_files(frozen.open_embedded_archive("PYZ.pyz").toc)
    return set(frozen.toc)


def check_no_bundled_native(names, read_file) -> None:
    for name in names:
        suffix = Path(name).name.lower()
        header = read_file(name)[:4]
        require(
            not (
                re.search(r"\.so(?:\.|$)", suffix)
                or suffix.endswith((".dll", ".dylib"))
                or header == b"\x7fELF"
                or header[:2] == b"MZ"
                or header in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe"}
            ),
            f"Bundled native object is forbidden in unfrozen application archives: {name}",
        )


def check_no_ai_files(names) -> None:
    forbidden = {
        ".agents",
        ".codex",
        ".claude",
        ".cursor",
        ".windsurf",
        ".continue",
        ".gemini",
        ".cline",
        ".roo",
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "GEMINI.md",
        ".cursorrules",
        ".windsurfrules",
        ".clinerules",
        ".roorules",
        ".mcp.json",
        "mcp.json",
        "skills-lock.json",
    }
    for name in names:
        parts = Path(name).parts
        require(
            not any(part in forbidden or part.startswith(".aider") for part in parts),
            "Artifact contains AI configuration",
        )
        require(
            not any(
                value in name
                for value in (".github/copilot-instructions.md", ".github/instructions/", ".github/prompts/")
            ),
            "Artifact contains AI instructions",
        )


def main() -> None:
    version = sys.argv[1]
    root = Path(__file__).resolve().parent.parent
    # Optional isolated output directory lets audits avoid replacing local release artifacts.
    dist = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else root / "dist"
    release = dist / "release"

    wheel = release / f"qwarp-{version}-py3-none-any.whl"
    sdist = release / f"qwarp-{version}.tar.gz"
    source = release / f"qwarp-{version}-source.tar.gz"
    for path in (wheel, sdist, source, release / "SHA256SUMS"):
        require(path.is_file() and path.stat().st_size > 0, f"Missing or empty artifact: {path}")

    verify_checksums(version, release)
    check_legal_files(lambda name: (root / name).read_bytes())

    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        check_no_ai_files(names)
        check_no_cloudflare_files(names)
        check_no_bundled_native((name for name in names if not name.endswith("/")), archive.read)
        info = f"qwarp-{version}.dist-info"
        check_license_metadata(archive.read(f"{info}/METADATA"))
        check_legal_files(lambda name: archive.read(f"{info}/licenses/{name}"))
        require("qwarp/main.py" in names, "Wheel does not contain qwarp/main.py")
        require("qwarp/assets/app-icon.svg" in names, "Wheel does not contain application assets")
        require(
            all(
                f"qwarp/assets/locales/qwarp_{language}.qm" in names
                for language in ("en", "es", "pt", "de", "it", "zh", "ja", "hi")
            ),
            "Wheel does not contain every compiled locale",
        )
        license_names = {name.rsplit("/", 1)[-1] for name in names if ".dist-info/licenses/" in name}
        require(
            {"LICENSE", "Apache-2.0.txt", "Glyphs-Poly-MIT.txt", "TRADEMARKS.md"}.issubset(license_names),
            "Wheel does not contain every legal notice",
        )

    with tarfile.open(sdist, "r:gz") as archive:
        names = set(archive.getnames())
        check_no_ai_files(names)
        check_no_cloudflare_files(names)
        check_no_bundled_native(
            (m.name for m in archive.getmembers() if m.isfile()), lambda name: archive.extractfile(name).read()
        )
        check_license_metadata(archive.extractfile(f"qwarp-{version}/PKG-INFO").read())
        check_legal_files(lambda name: archive.extractfile(f"qwarp-{version}/{name}").read())
        require(f"qwarp-{version}/pyproject.toml" in names, "sdist does not contain pyproject.toml")
        require(f"qwarp-{version}/src/qwarp/main.py" in names, "sdist does not contain application source")
        for recipe in ("packaging/debian/rules", "packaging/debian/copyright", "packaging/rpm/qwarp.spec"):
            require(f"qwarp-{version}/{recipe}" in names, f"sdist is missing build recipe {recipe}")
        require(f"qwarp-{version}/TRADEMARKS.md" in names, "sdist does not contain the trademark notice")
        require(
            f"qwarp-{version}/LICENSES/Apache-2.0.txt" in names,
            "sdist does not contain the Material Symbols license",
        )
        require(
            f"qwarp-{version}/LICENSES/Glyphs-Poly-MIT.txt" in names,
            "sdist does not contain the Glyphs Poly license",
        )

    with tarfile.open(source, "r:gz") as archive:
        names = set(archive.getnames())
        check_no_ai_files(names)
        check_no_cloudflare_files(names)
        check_no_bundled_native(
            (m.name for m in archive.getmembers() if m.isfile()), lambda name: archive.extractfile(name).read()
        )
        check_legal_files(lambda name: archive.extractfile(f"qwarp-{version}/{name}").read())
        require(
            f"qwarp-{version}/CONTRIBUTING.md" in names,
            "Source archive does not contain contributor guidance",
        )
        require(
            f"qwarp-{version}/TRADEMARKS.md" in names,
            "Source archive does not contain the trademark notice",
        )
        require(
            f"qwarp-{version}/LICENSES/Apache-2.0.txt" in names,
            "Source archive does not contain the Material Symbols license",
        )
        require(
            f"qwarp-{version}/LICENSES/Glyphs-Poly-MIT.txt" in names,
            "Source archive does not contain the Glyphs Poly license",
        )
        for document in (
            "docs/legal/LICENSING-AUDIT.md",
            "docs/RELEASING.md",
            "scripts/build_artifacts.sh",
            "scripts/release_policy.py",
            "packaging/debian/rules",
            "packaging/debian/copyright",
            "packaging/rpm/qwarp.spec",
            "requirements/locks/release-py3.11.txt",
            "docs/audits/2026-09-26.md",
            "docs/screenshots/connected.png",
            "docs/screenshots/disconnected.png",
        ):
            require(f"qwarp-{version}/{document}" in names, f"Source archive is missing {document}")
        require(
            not any(Path(name).name in {"PKGBUILD", ".SRCINFO"} for name in names),
            "Source archive must not contain recursive Arch metadata",
        )
        require(not any(".egg-info/" in name for name in names), "Source archive contains generated egg-info")
        require(not any(name.endswith((".pyc", ".qm")) for name in names), "Source archive contains generated files")

    print(f"QWarp {version} unfrozen artifact checks passed; standalone publication disabled")


if __name__ == "__main__":
    main()
