#!/usr/bin/env python3
"""Derive RP volume/material authority from the two canonical geometry bundles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from manifest_discovery import load_authority, verify_geometry_bundle
from preflight_common import PACKAGE, ROOT, canonical_json_bytes, rel, repo_path, sha256, strict_json


SCHEMA_VERSION = "m05-geometry-classification-v1"
WHITELIST = PACKAGE / "schema/active_volume_whitelist_v1.json"
CONSTRUCTION_SOURCE = Path(
    "/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCDetectorConstruction.cc"
)
CONSTRUCTION_SOURCE_SHA256 = "c136aad77d866eb7882c0279c766928a50ac5fe072d54a61dc88fca986b85e7d"


def _artifact_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo_path(value)


def _classify(physical: str, material: str, whitelist: dict[str, Any]) -> tuple[str, str | None]:
    mass = set(whitelist["mass_csi_physical_volumes"])
    bgo = set(whitelist["o8_bgo_physical_volumes"])
    plastic = set(whitelist["o8_plastic_physical_volumes"])
    if re.fullmatch(whitelist["tes_physical_volume_regex"], physical):
        return "tes", "tes"
    if physical in mass:
        return "active_veto", "mass_csi"
    if physical in bgo:
        return "active_veto", "o8_bgo"
    if physical in plastic:
        return "active_veto", "o8_plastic"
    upper = physical.upper()
    if "KAPTON" in upper:
        return "passive_activation_diagnostic", None
    if "BPE" in upper or material.upper() in {"BPE", "BORATEDPOLYETHYLENE"}:
        return "passive_activation", None
    if material.upper() in {"W", "AL"}:
        return "passive_activation", None
    return "passive_or_structural", None


def _parse_bundle(geometry: str, bundle: dict[str, Any], whitelist: dict[str, Any]) -> dict[str, Any]:
    verify_geometry_bundle(bundle)
    volumes: dict[str, dict[str, str]] = {}
    copies: dict[str, dict[str, str]] = {}
    for authority in bundle["files"]:
        path = _artifact_path(authority["path"])
        text = path.read_text(encoding="utf-8")
        for name in re.findall(r"^\s*Volume\s+(\S+)\s*$", text, re.MULTILINE):
            if name in volumes:
                raise ValueError(f"{geometry}: duplicate Volume {name}")
            volumes[name] = {"defined_in": authority["path"]}
        for source, copy in re.findall(r"^\s*(\S+)\.Copy\s+(\S+)\s*$", text, re.MULTILINE):
            if copy in copies or copy in volumes:
                raise ValueError(f"{geometry}: duplicate/conflicting Copy {copy}")
            copies[copy] = {"source_volume": source, "defined_in": authority["path"]}
        for name, material in re.findall(r"^\s*(\S+)\.Material\s+(\S+)\s*$", text, re.MULTILINE):
            if name not in volumes or "material" in volumes[name]:
                raise ValueError(f"{geometry}: orphan/duplicate Material for {name}")
            volumes[name]["material"] = material
    if any("material" not in record for record in volumes.values()):
        raise ValueError(f"{geometry}: source volume lacks material")
    if any(record["source_volume"] not in volumes for record in copies.values()):
        raise ValueError(f"{geometry}: copy source lacks Volume definition")

    records: list[dict[str, Any]] = []
    for physical, source in [(name, name) for name in volumes] + [
        (name, record["source_volume"]) for name, record in copies.items()
    ]:
        material = volumes[source]["material"]
        role, detector_type = _classify(physical, material, whitelist)
        records.append(
            {
                "physical_volume": physical,
                "source_volume": source,
                "runtime_logical_volume": f"{source}Log",
                "native_dat_volume": source,
                "material": material,
                "copy_number": 0,
                "role": role,
                "active_detector_type": detector_type,
                "defined_in": (copies.get(physical) or volumes[source])["defined_in"],
            }
        )
    records.sort(key=lambda row: row["physical_volume"])
    if len({row["physical_volume"] for row in records}) != len(records):
        raise ValueError(f"{geometry}: physical-volume index is not unique")

    active = {
        detector_type: sorted(
            row["physical_volume"] for row in records if row["active_detector_type"] == detector_type
        )
        for detector_type in ("mass_csi", "o8_bgo", "o8_plastic")
    }
    expected = {
        "mass_model_511": {
            "mass_csi": whitelist["mass_csi_physical_volumes"],
            "o8_bgo": [],
            "o8_plastic": [],
        },
        "s3d_o8": {
            "mass_csi": [],
            "o8_bgo": whitelist["o8_bgo_physical_volumes"],
            "o8_plastic": whitelist["o8_plastic_physical_volumes"],
        },
    }[geometry]
    if active != {name: sorted(values) for name, values in expected.items()}:
        raise ValueError(f"{geometry}: canonical geometry active-veto classification drift")
    return {
        "geometry": geometry,
        "geometry_setup": bundle["setup"],
        "geometry_bundle_sha256": bundle["bundle_sha256"],
        "geometry_bundle_files": bundle["files"],
        "source_volume_count": len(volumes),
        "copy_volume_count": len(copies),
        "physical_volume_count": len(records),
        "active_volume_counts": {name: len(values) for name, values in active.items()},
        "records": records,
    }


def build_geometry_classification() -> dict[str, Any]:
    if sha256(CONSTRUCTION_SOURCE) != CONSTRUCTION_SOURCE_SHA256:
        raise ValueError("installed MCDetectorConstruction source hash drift")
    whitelist = strict_json(WHITELIST)
    if whitelist.get("schema_version") != "m05-active-volume-whitelist-v1":
        raise ValueError("active-volume whitelist schema drift")
    bundles = load_authority("batch0001").get("geometry_bundles")
    if not isinstance(bundles, dict) or set(bundles) != {"mass_model_511", "s3d_o8"}:
        raise ValueError("canonical geometry bundle set drift")
    geometries = [_parse_bundle(name, bundles[name], whitelist) for name in ("mass_model_511", "s3d_o8")]
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS__DERIVED_FROM_CANONICAL_GEOMETRY_BUNDLES__NO_TRANSPORT",
        "transport_events_launched": 0,
        "active_volume_whitelist_path": rel(WHITELIST),
        "active_volume_whitelist_sha256": sha256(WHITELIST),
        "runtime_naming_authority": {
            "path": str(CONSTRUCTION_SOURCE),
            "sha256": CONSTRUCTION_SOURCE_SHA256,
            "source_lines": "PositionVolumes creates logical name source_volume+'Log', physical name volume/copy name, copy number 0",
        },
        "native_dat_semantics": "MCRun removes the final three characters 'Log' from runtime logical volume",
        "touchable_semantics": "level-0 must equal physical_volume:runtime_logical_volume:copy_number",
        "classification_semantics": (
            "active detector roles are exact whitelist intersections with canonical geometry definitions; "
            "Kapton/BPE/W/Al are never active veto"
        ),
        "geometries": geometries,
    }


def validate_geometry_classification(
    manifest: dict[str, Any], *, verify_canonical_authority: bool = True
) -> dict[str, Any]:
    """Validate the manifest structure and, by default, rebuild its authority.

    The rebuild is intentional: an RP sidecar must not be allowed to join a
    self-consistent but invented volume/material table.  Unit fixtures can
    disable the expensive authority rebuild while still exercising the exact
    structural/foreign-key rules.
    """

    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("transport_events_launched") != 0
    ):
        raise ValueError("wrong geometry-classification manifest")
    geometries = manifest.get("geometries")
    if not isinstance(geometries, list) or not geometries:
        raise ValueError("geometry classification lacks geometry records")
    names: set[str] = set()
    total_records = 0
    for geometry in geometries:
        name = geometry.get("geometry")
        records = geometry.get("records")
        if not isinstance(name, str) or not name or name in names or not isinstance(records, list):
            raise ValueError("geometry classification has duplicate/malformed geometry records")
        names.add(name)
        physical_names: set[str] = set()
        for row in records:
            if not isinstance(row, dict) or set(row) != {
                "physical_volume", "source_volume", "runtime_logical_volume", "native_dat_volume",
                "material", "copy_number", "role", "active_detector_type", "defined_in",
            }:
                raise ValueError("geometry classification record schema drift")
            physical = row["physical_volume"]
            if (
                not isinstance(physical, str)
                or not physical
                or physical in physical_names
                or not isinstance(row["copy_number"], int)
                or row["copy_number"] < 0
                or any(not isinstance(row[field], str) or not row[field] for field in (
                    "source_volume", "runtime_logical_volume", "native_dat_volume", "material",
                    "role", "defined_in",
                ))
                or row["active_detector_type"] not in {None, "tes", "mass_csi", "o8_bgo", "o8_plastic"}
            ):
                raise ValueError("geometry classification field/type/key drift")
            physical_names.add(physical)
        total_records += len(records)
    if verify_canonical_authority:
        expected = build_geometry_classification()
        if canonical_json_bytes(manifest) != canonical_json_bytes(expected):
            raise ValueError("geometry classification differs from rebuilt canonical bundle authority")
    return {
        "status": "PASS",
        "geometry_count": len(geometries),
        "record_count": total_records,
        "canonical_authority_rebuilt": verify_canonical_authority,
    }


def classification_index(manifest: dict[str, Any], geometry: str) -> dict[str, dict[str, Any]]:
    validate_geometry_classification(manifest, verify_canonical_authority=False)
    matches = [row for row in manifest.get("geometries", []) if row.get("geometry") == geometry]
    if len(matches) != 1:
        raise ValueError("geometry classification does not resolve uniquely")
    records = matches[0].get("records")
    if not isinstance(records, list):
        raise ValueError("geometry classification lacks records")
    result = {row.get("physical_volume"): row for row in records}
    if None in result or len(result) != len(records):
        raise ValueError("geometry classification has duplicate/missing physical keys")
    return result
