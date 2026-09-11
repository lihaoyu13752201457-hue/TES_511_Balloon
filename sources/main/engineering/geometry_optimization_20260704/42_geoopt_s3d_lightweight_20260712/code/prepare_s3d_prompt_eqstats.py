#!/usr/bin/env python3
"""Prepare and audit the S3d equal-statistics e+/neutron source cards.

The retained S3c source cards are the statistical/provenance authority.  This
script copies only gamma (normalization anchor), e+, and neutron cards and
allows exactly one semantic change: the geometry setup path is repointed from
the retained S3c setup to the validated S3d setup.  It writes only inside the
new 42_ engineering package.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = ROOT / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
BASE_SOURCE_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/source_cards"
)
SOURCE_DIR = PACKAGE / "config/prompt_eqstats_eplus_n/source_cards"
DATA_DIR = PACKAGE / "data"
GEOMETRY_MANIFEST = DATA_DIR / "s3d_geometry_manifest.json"

BASE_GEOMETRY = (
    "engineering/geometry_optimization_20260704/"
    "29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
TARGET_GEOMETRY = (
    "engineering/geometry_optimization_20260704/"
    "42_geoopt_s3d_lightweight_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
TAGS = ("gamma", "eplus", "n")
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$", re.MULTILINE)
SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)\s*$", re.MULTILINE)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalized_payload(text: str, geometry: str) -> str:
    return text.replace(geometry, "<PINNED_GEOMETRY_SETUP>")


def source_name(tag: str) -> str:
    return f"Background_{tag}_fullsphere20.source"


def validate_geometry() -> dict[str, Any]:
    if not GEOMETRY_MANIFEST.exists():
        raise SystemExit(f"Missing S3d geometry manifest: {rel(GEOMETRY_MANIFEST)}")
    manifest = json.loads(GEOMETRY_MANIFEST.read_text(encoding="utf-8"))
    expected_status = "S3D_O9_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"
    if manifest.get("status") != expected_status:
        raise SystemExit(
            f"S3d geometry is not transport-ready: status={manifest.get('status')!r}; "
            f"expected={expected_status!r}"
        )
    if manifest.get("generated_geometry") != TARGET_GEOMETRY:
        raise SystemExit("S3d geometry manifest points to an unexpected setup")
    setup = ROOT / TARGET_GEOMETRY
    if not setup.is_file():
        raise SystemExit(f"Missing S3d geometry setup: {rel(setup)}")
    overlap = manifest.get("overlap_validation", {})
    if overlap.get("status") != "PASS" or not overlap.get("hash_match"):
        raise SystemExit("S3d overlap result is absent, failed, or stale")
    return {
        "manifest": rel(GEOMETRY_MANIFEST),
        "manifest_status": manifest["status"],
        "setup": TARGET_GEOMETRY,
        "setup_sha256": sha256_file(setup),
        "overlap_status": overlap.get("status"),
        "overlap_hash_match": overlap.get("hash_match"),
    }


def build_sources() -> list[dict[str, Any]]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for tag in TAGS:
        name = source_name(tag)
        base = BASE_SOURCE_DIR / name
        target = SOURCE_DIR / name
        if not base.is_file():
            raise SystemExit(f"Missing retained S3c source authority: {rel(base)}")

        base_text = base.read_text(encoding="utf-8")
        replacement_count = base_text.count(BASE_GEOMETRY)
        if replacement_count != 2:
            raise SystemExit(
                f"Expected exactly two S3c setup references in {rel(base)}, got {replacement_count}"
            )
        target_text = base_text.replace(BASE_GEOMETRY, TARGET_GEOMETRY)
        target.write_text(target_text, encoding="utf-8")

        geometry_lines = [
            line.strip() for line in target_text.splitlines() if line.strip().startswith("Geometry ")
        ]
        geometry_comments = [
            line.strip()
            for line in target_text.splitlines()
            if line.strip().startswith("# geometry_setup=")
        ]
        spectra = SPECTRUM_RE.findall(target_text)
        missing_spectra = [path for path in spectra if not (ROOT / path).is_file()]
        fluxes = [float(value) for value in FLUX_RE.findall(target_text)]
        payload_equal = normalized_payload(base_text, BASE_GEOMETRY) == normalized_payload(
            target_text, TARGET_GEOMETRY
        )
        checks = {
            "exactly_one_geometry_directive": geometry_lines == [f"Geometry {TARGET_GEOMETRY}"],
            "exactly_one_geometry_comment": geometry_comments
            == [f"# geometry_setup={TARGET_GEOMETRY}"],
            "retired_geometry_absent": BASE_GEOMETRY not in target_text,
            "non_geometry_payload_byte_identical": payload_equal,
            "twenty_equal_mu_spectra": len(spectra) == 20,
            "all_spectra_exist": not missing_spectra,
            "twenty_flux_bins": len(fluxes) == 20,
        }
        if not all(checks.values()):
            raise SystemExit(f"Source-card validation failed for {tag}: {checks}")
        rows.append(
            {
                "particle": tag,
                "source": rel(target),
                "template_source": rel(base),
                "template_sha256": sha256_file(base),
                "source_sha256": sha256_file(target),
                "normalized_payload_sha256": sha256_bytes(
                    normalized_payload(target_text, TARGET_GEOMETRY).encode("utf-8")
                ),
                "geometry_lines": geometry_lines,
                "geometry_comment": geometry_comments[0],
                "total_flux_cm2_s": sum(fluxes),
                "spectrum_files": len(spectra),
                "missing_spectrum_files": missing_spectra,
                "checks": checks,
                "status": "PASS_S3D_GEOMETRY_REPOINTED_ONLY",
            }
        )
    return rows


def write_manifest(geometry: dict[str, Any], rows: list[dict[str, Any]]) -> Path:
    manifest = {
        "status": "PASS_S3D_PROMPT_EQSTATS_SOURCE_COPY_PREPARED",
        "label": "s3d_lightweight_eqstats_prompt_eplus_n_20260712",
        "prepared_for": "S3d eplus/neutron equal-stat prompt transport and activation inventory",
        "change_scope": (
            "Copied retained S3c gamma/eplus/neutron cards; changed only the Geometry directive "
            "and geometry_setup comment from the retained S3c setup to the validated S3d setup."
        ),
        "source_dir": rel(SOURCE_DIR),
        "source_parent": rel(SOURCE_DIR),
        "template_source_dir": rel(BASE_SOURCE_DIR),
        "copied_from_source_parent": rel(BASE_SOURCE_DIR),
        "geometry_setup": TARGET_GEOMETRY,
        "geometry_status": geometry["manifest_status"],
        "geometry_manifest": geometry["manifest"],
        "geometry_setup_sha256": geometry["setup_sha256"],
        "geometry_overlap_status": geometry["overlap_status"],
        "farfield_radius_cm": 60.0,
        "surrounding_sphere": "SurroundingSphere 60 5 0 9 60",
        "pointing_policy": (
            "InstrumentFrame rotated 0 45 0 deg; local side-window -x looks 45 deg upward "
            "in global zenith frame"
        ),
        "statistics_reference": (
            "Retained S3c equal-stat source cards: gamma reference 10,000,000; "
            "eplus and neutron event counts scaled by gamma flux; eight independent replicas"
        ),
        "source_card_particles": list(TAGS),
        "transport_particles": ["eplus", "n"],
        "sources": rows,
        "problems": [],
    }
    path = SOURCE_DIR / "source_migration_manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def validate_only() -> list[dict[str, Any]]:
    manifest_path = SOURCE_DIR / "source_migration_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(f"Missing prepared source manifest: {rel(manifest_path)}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = manifest.get("sources", [])
    if manifest.get("status") != "PASS_S3D_PROMPT_EQSTATS_SOURCE_COPY_PREPARED":
        raise SystemExit("Prepared source manifest is not PASS")
    expected = {row["particle"]: row for row in rows}
    if set(expected) != set(TAGS):
        raise SystemExit("Prepared source manifest has an unexpected particle set")
    for tag in TAGS:
        path = SOURCE_DIR / source_name(tag)
        text = path.read_text(encoding="utf-8")
        if sha256_file(path) != expected[tag]["source_sha256"]:
            raise SystemExit(f"Prepared source hash is stale for {tag}")
        if [line.strip() for line in text.splitlines() if line.strip().startswith("Geometry ")] != [
            f"Geometry {TARGET_GEOMETRY}"
        ]:
            raise SystemExit(f"Prepared source geometry is invalid for {tag}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    geometry = validate_geometry()
    if args.validate_only:
        rows = validate_only()
        print(f"PASS validated {len(rows)} pinned source cards under {rel(SOURCE_DIR)}")
        return 0

    rows = build_sources()
    manifest = write_manifest(geometry, rows)
    print(f"PASS wrote {len(rows)} pinned source cards and {rel(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
