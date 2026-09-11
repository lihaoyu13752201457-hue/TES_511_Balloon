#!/usr/bin/env python3
"""Prepare fail-closed equal-statistics e+/neutron source cards for O8.

The retained heavy-control cards are the source-model authority.  The only
allowed source-card change is the geometry setup path (both the executable
directive and its provenance comment).  Gamma is copied only as the
normalization anchor; production is restricted to e+ and neutron by the
companion runner.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _o8_replay_common import (
    AuditError,
    DATA,
    PACKAGE,
    ROOT,
    S3C_GEOMETRY_SETUP,
    S3D_GEOMETRY_SETUP,
    audit_geometry_authority,
    rel,
    safe_write_json,
    safe_write_text,
    sha256,
)


BASE_SOURCE_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709"
    / "source_cards"
)
O9_SOURCE_DIR = (
    ROOT
    / "engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712"
    / "config/prompt_eqstats_eplus_n/source_cards"
)
SOURCE_DIR = PACKAGE / "config/prompt_eqstats_eplus_n/source_cards"
MANIFEST = SOURCE_DIR / "source_migration_manifest.json"

TAGS = ("gamma", "eplus", "n")
TRANSPORT_TAGS = ("eplus", "n")
EXPECTED_EVENTS_PER_REPLICA = {"eplus": 243_727, "n": 963_066}
EXPECTED_SEEDS = {
    "eplus": [1_007_922, 1_015_841, 1_023_760, 1_031_679, 1_039_598, 1_047_517, 1_055_436, 1_063_355],
    "n": [1_071_274, 1_079_193, 1_087_112, 1_095_031, 1_102_950, 1_110_869, 1_118_788, 1_126_707],
}
FLUX_RE = re.compile(r"\.Flux\s+([-+0-9.eE]+)\s*$", re.M)
SPECTRUM_RE = re.compile(r"\.Spectrum\s+File\s+(\S+)\s*$", re.M)


def source_name(tag: str) -> str:
    return f"Background_{tag}_fullsphere20.source"


def normalized_payload(text: str, geometry: Path) -> str:
    """Normalize exactly the executable/comment geometry-path metadata."""
    geometry_rel = rel(geometry)
    if text.count(geometry_rel) != 2:
        raise AuditError(
            f"expected exactly two geometry-path occurrences for {geometry_rel}, "
            f"found {text.count(geometry_rel)}"
        )
    return text.replace(geometry_rel, "<PINNED_GEOMETRY_SETUP>")


def audit_card(tag: str, target: Path, base: Path, o9: Path) -> dict[str, Any]:
    base_text = base.read_text(encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    o9_text = o9.read_text(encoding="utf-8")
    geometry_lines = [
        line.strip() for line in text.splitlines() if line.strip().startswith("Geometry ")
    ]
    geometry_comments = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("# geometry_setup=")
    ]
    spectra = SPECTRUM_RE.findall(text)
    fluxes = [float(value) for value in FLUX_RE.findall(text)]
    missing_spectra = [value for value in spectra if not (ROOT / value).is_file()]
    normalized = normalized_payload(text, S3D_GEOMETRY_SETUP)
    normalized_base = normalized_payload(base_text, S3C_GEOMETRY_SETUP)
    # O9 is a second, independently retained realization of the same source
    # contract.  Agreement with both authorities detects accidental template
    # drift even if one path is later edited.
    o9_geometry = next(
        (
            Path(line.split(None, 1)[1].strip())
            for line in o9_text.splitlines()
            if line.strip().startswith("Geometry ")
        ),
        None,
    )
    if o9_geometry is None:
        raise AuditError(f"missing O9 Geometry directive: {rel(o9)}")
    normalized_o9 = normalized_payload(o9_text, ROOT / o9_geometry)
    checks = {
        "one_o8_geometry_directive": geometry_lines == [f"Geometry {rel(S3D_GEOMETRY_SETUP)}"],
        "one_o8_geometry_comment": geometry_comments
        == [f"# geometry_setup={rel(S3D_GEOMETRY_SETUP)}"],
        "heavy_control_geometry_absent": rel(S3C_GEOMETRY_SETUP) not in text,
        "canonical_equal_to_heavy_control": normalized == normalized_base,
        "canonical_equal_to_completed_o9": normalized == normalized_o9,
        "twenty_farfield_spectra": len(spectra) == 20,
        "twenty_flux_bins": len(fluxes) == 20,
        "all_spectrum_files_exist": not missing_spectra,
    }
    if not all(checks.values()):
        raise AuditError(f"O8 prompt source audit failed for {tag}: {checks}")
    return {
        "particle": tag,
        "status": "PASS_O8_GEOMETRY_METADATA_ONLY",
        "source": rel(target),
        "source_sha256": sha256(target),
        "heavy_control_source": rel(base),
        "heavy_control_source_sha256": sha256(base),
        "completed_o9_source": rel(o9),
        "completed_o9_source_sha256": sha256(o9),
        "canonical_payload_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "total_flux_cm2_s": sum(fluxes),
        "spectrum_files": len(spectra),
        "missing_spectrum_files": missing_spectra,
        "checks": checks,
    }


def prepare() -> dict[str, Any]:
    geometry = audit_geometry_authority()
    rows: list[dict[str, Any]] = []
    for tag in TAGS:
        base = BASE_SOURCE_DIR / source_name(tag)
        o9 = O9_SOURCE_DIR / source_name(tag)
        target = SOURCE_DIR / source_name(tag)
        if not base.is_file() or not o9.is_file():
            raise AuditError(
                f"missing retained prompt source authority for {tag}: "
                f"heavy={rel(base)}, o9={rel(o9)}"
            )
        base_text = base.read_text(encoding="utf-8")
        heavy_geometry = rel(S3C_GEOMETRY_SETUP)
        if base_text.count(heavy_geometry) != 2:
            raise AuditError(
                f"expected two heavy-control geometry references in {rel(base)}, "
                f"found {base_text.count(heavy_geometry)}"
            )
        target_text = base_text.replace(heavy_geometry, rel(S3D_GEOMETRY_SETUP))
        safe_write_text(target, target_text)
        rows.append(audit_card(tag, target, base, o9))

    payload = {
        "status": "PASS_O8_PROMPT_EQSTATS_SOURCE_COPY_PREPARED",
        "claim_boundary": "Source-card preparation only; no Cosima transport result is claimed.",
        "change_scope": (
            "Retained heavy-control gamma/eplus/neutron cards with only Geometry and "
            "geometry_setup metadata repointed to the validated O8 setup."
        ),
        "source_dir": rel(SOURCE_DIR),
        "template_source_dir": rel(BASE_SOURCE_DIR),
        "completed_o9_crosscheck_dir": rel(O9_SOURCE_DIR),
        "geometry_setup": rel(S3D_GEOMETRY_SETUP),
        "geometry_authority": geometry,
        "source_card_particles": list(TAGS),
        "transport_particles": list(TRANSPORT_TAGS),
        "statistics_contract": {
            "gamma_normalization_anchor_events": 10_000_000,
            "non_gamma_replicas": 8,
            "events_per_replica": EXPECTED_EVENTS_PER_REPLICA,
            "seeds": EXPECTED_SEEDS,
            "total_transport_events": 9_654_344,
        },
        "sources": rows,
        "source_write_states": {tag: "PRESENT_IDENTICAL" for tag in TAGS},
        "problems": [],
    }
    payload["manifest_write_state"] = safe_write_json(MANIFEST, payload)
    return payload


def validate_only() -> dict[str, Any]:
    audit_geometry_authority()
    if not MANIFEST.is_file():
        raise AuditError(f"missing O8 prompt source manifest: {rel(MANIFEST)}")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("status") != "PASS_O8_PROMPT_EQSTATS_SOURCE_COPY_PREPARED":
        raise AuditError(f"O8 prompt source manifest is not PASS: {manifest.get('status')}")
    by_tag = {row.get("particle"): row for row in manifest.get("sources", [])}
    if set(by_tag) != set(TAGS):
        raise AuditError(f"unexpected O8 source set: {sorted(by_tag)}")
    rows = []
    for tag in TAGS:
        target = SOURCE_DIR / source_name(tag)
        base = BASE_SOURCE_DIR / source_name(tag)
        o9 = O9_SOURCE_DIR / source_name(tag)
        if not target.is_file() or sha256(target) != by_tag[tag].get("source_sha256"):
            raise AuditError(f"missing or stale prepared O8 source: {rel(target)}")
        rows.append(audit_card(tag, target, base, o9))
    return {"status": "PASS", "sources": rows, "manifest": rel(MANIFEST)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    try:
        payload = validate_only() if args.validate_only else prepare()
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "manifest": rel(MANIFEST),
                    "source_dir": rel(SOURCE_DIR),
                    "production_launched": False,
                },
                indent=2,
            )
        )
        return 0
    except (AuditError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
