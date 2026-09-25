#!/usr/bin/env python3
"""Localization validation script for QWarp.

Ensures that all supported translation catalogs exist, are parseable XML,
contain no unfinished or empty translations (for non-English locales),
preserve all placeholders and HTML links, and compile cleanly with lrelease.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

SUPPORTED_LOCALES = ["en", "de", "es", "pt", "it", "zh", "ja", "hi"]
NON_ENGLISH_LOCALES = [loc for loc in SUPPORTED_LOCALES if loc != "en"]
LOCALES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src",
    "qwarp",
    "assets",
    "locales",
)

PLACEHOLDER_RE = re.compile(r"%[0-9]+|%s")
HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]")


def resolve_lrelease() -> str:
    candidates = [
        "/usr/lib/qt6/bin/lrelease",
        "lrelease-qt6",
        "lrelease6",
        "lrelease",
    ]
    for cand in candidates:
        if os.path.isabs(cand) and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        import shutil

        resolved = shutil.which(cand)
        if resolved:
            return resolved
    return ""


def validate_catalog(filepath: str, is_english: bool) -> list[str]:
    errors = []
    basename = os.path.basename(filepath)
    try:
        tree = ET.parse(filepath)  # noqa: S314
    except Exception as exc:
        return [f"{basename}: Failed to parse XML: {exc}"]

    root = tree.getroot()
    contexts = root.findall("context")
    if not contexts:
        errors.append(f"{basename}: No <context> elements found.")

    for ctx in contexts:
        ctx_name_el = ctx.find("name")
        ctx_name = ctx_name_el.text if ctx_name_el is not None else "UnknownContext"
        for msg in ctx.findall("message"):
            source_el = msg.find("source")
            trans_el = msg.find("translation")
            source_text = source_el.text if (source_el is not None and source_el.text) else ""

            if trans_el is None:
                errors.append(f"{basename} [{ctx_name}]: Missing <translation> tag for '{source_text}'")
                continue

            trans_type = trans_el.get("type")
            trans_text = trans_el.text or ""

            if is_english:
                # English is the base/fallback catalog; unfinished or empty is acceptable
                continue

            if trans_type == "unfinished":
                errors.append(f"{basename} [{ctx_name}]: Unfinished translation for '{source_text}'")
            elif not trans_text.strip():
                errors.append(f"{basename} [{ctx_name}]: Empty translation for '{source_text}'")
            else:
                # Check placeholders
                src_placeholders = sorted(PLACEHOLDER_RE.findall(source_text))
                trans_placeholders = sorted(PLACEHOLDER_RE.findall(trans_text))
                if src_placeholders != trans_placeholders:
                    errors.append(
                        f"{basename} [{ctx_name}]: Placeholder mismatch for '{source_text}'. "
                        f"Expected {src_placeholders}, got {trans_placeholders}"
                    )

                # Check href URLs
                src_hrefs = sorted(HREF_RE.findall(source_text))
                trans_hrefs = sorted(HREF_RE.findall(trans_text))
                if src_hrefs != trans_hrefs:
                    errors.append(
                        f"{basename} [{ctx_name}]: Link href mismatch for '{source_text}'. "
                        f"Expected {src_hrefs}, got {trans_hrefs}"
                    )

                # Check for matching tag balance for <a> and </a>
                if "<a " in source_text and "</a>" in source_text:
                    if "<a " not in trans_text or "</a>" not in trans_text:
                        errors.append(
                            f"{basename} [{ctx_name}]: Missing <a> or </a> link tag in translation for '{source_text}'"
                        )

    return errors


def main() -> int:
    print("Checking QWarp translation catalogs...")
    all_errors = []

    for loc in SUPPORTED_LOCALES:
        ts_path = os.path.join(LOCALES_DIR, f"qwarp_{loc}.ts")
        if not os.path.isfile(ts_path):
            all_errors.append(f"Missing expected catalog file: {ts_path}")
            continue

        is_en = loc == "en"
        catalog_errors = validate_catalog(ts_path, is_english=is_en)
        all_errors.extend(catalog_errors)

    lrelease = resolve_lrelease()
    if not lrelease:
        all_errors.append("Could not locate lrelease executable to verify compilation.")
    else:
        ts_files = glob.glob(os.path.join(LOCALES_DIR, "*.ts"))
        proc = subprocess.run(
            [lrelease, *ts_files],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            all_errors.append(f"lrelease failed (code {proc.returncode}): {proc.stderr}")
        else:
            print(f"✅ lrelease successfully compiled {len(ts_files)} catalogs.")

    if all_errors:
        print(f"❌ Localization check failed with {len(all_errors)} error(s):")
        for err in all_errors[:20]:
            print(f"  - {err}")
        if len(all_errors) > 20:
            print(f"  ... and {len(all_errors) - 20} more errors.")
        return 1

    print("✅ All supported localization catalogs are complete and valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
