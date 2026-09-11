#!/usr/bin/env python3
"""Build SG3A as the strict material-only aluminium-can child of SG3.

The four 50 mK Still-like can pieces are renamed for unambiguous future
activation lineage and changed from Copper to Aluminium.  Their shapes,
positions, hierarchy, visibility, detector telemetry, and response parameters
are otherwise inherited byte-for-byte.  This program never launches transport.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEOMETRY_DIR = PACKAGE / "geometry"
DATA_DIR = PACKAGE / "data"
AUDIT_DIR = PACKAGE / "audit"

SG3_PACKAGE = SCRIPT.parents[2] / "53_geoopt_sg3_cu_ring_bi_umbrella_20260816"
SG3_GEOMETRY_DIR = SG3_PACKAGE / "geometry"
SG3_STEM = "DEMO2_DR_v3p5_SG3"
SG3A_STEM = "DEMO2_DR_v3p5_SG3A"

SOURCE_FILES = {
    "setup": SG3_GEOMETRY_DIR / f"{SG3_STEM}.geo.setup",
    "geo": SG3_GEOMETRY_DIR / f"{SG3_STEM}.geo",
    "det": SG3_GEOMETRY_DIR / f"{SG3_STEM}.det",
    "intro": SG3_GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": SG3_GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}
OUTPUT_FILES = {
    "setup": GEOMETRY_DIR / f"{SG3A_STEM}.geo.setup",
    "geo": GEOMETRY_DIR / f"{SG3A_STEM}.geo",
    "det": GEOMETRY_DIR / f"{SG3A_STEM}.det",
    "intro": GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}

PINNED_SG3 = {
    "setup": (123, "91fcdbfd74fca4f7a261e1ec27b39fcf2adc49f91ca9d7d1dff02591b26c16e6"),
    "geo": (697_331, "f0bb7f993b6804522fb0ad239b629405949ac70d4a6b0476ecd942d73bb887c5"),
    "det": (56_570, "d6c2d047a50eea93fe8d73a47f5f9b1b9a03837ef7a7fc14bb4586d3803b3b29"),
    "intro": (500, "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52"),
    "materials": (2_065, "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a"),
}

VOLUME_MAP = {
    "Cu_50mK_StillLike_Can_bottom_cap_2mm":
        "SG3A_Al_50mK_StillLike_Can_bottom_cap_2mm",
    "Cu_50mK_StillLike_Can_side_wall_below_side_port":
        "SG3A_Al_50mK_StillLike_Can_side_wall_below_side_port",
    "Cu_50mK_StillLike_Can_side_wall_above_side_port":
        "SG3A_Al_50mK_StillLike_Can_side_wall_above_side_port",
    "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band":
        "SG3A_Al_50mK_StillLike_Can_side_wall_rectcut_window_band",
}

HEADER_OLD = (
    "// Fix5: 50 mK Cu can is modeled as a full-azimuth z-axis Still-like local cold shield."
)
HEADER_NEW = (
    "// SG3A: 50 mK Al can preserves the SG3 full-azimuth Still-like cold-shield geometry."
)

CU_DENSITY_G_CM3 = 8.96
AL_DENSITY_G_CM3 = 2.699


class BuildError(RuntimeError):
    """Fail-closed SG3A build error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256_bytes(data)}


def atomic_write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_file() and path.read_bytes() == data:
            return
        raise BuildError(f"write-once target exists with different bytes: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def publish_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        expected = dict(payload)
        for item in (existing, expected):
            item.pop("generated_at_utc", None)
        if existing != expected:
            raise BuildError(f"write-once JSON differs from current contract: {path}")
        return
    atomic_write_once(path, encoded)


def verify_pinned_sources() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for key, path in SOURCE_FILES.items():
        if not path.is_file():
            raise BuildError(f"missing pinned SG3 source {key}: {path}")
        record = file_record(path)
        expected_bytes, expected_sha = PINNED_SG3[key]
        if record["bytes"] != expected_bytes or record["sha256"] != expected_sha:
            raise BuildError(f"pinned SG3 {key} drift: {record}")
        records[key] = record
    return records


def replace_exact_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise BuildError(f"expected exact-once text not found: {old}")
    return text.replace(old, new, 1)


def transform_geo(parent: str) -> str:
    text = replace_exact_once(parent, HEADER_OLD, HEADER_NEW)
    for old, new in VOLUME_MAP.items():
        if old not in text:
            raise BuildError(f"missing SG3 can lineage token: {old}")
        text = text.replace(old, new)
        text = replace_exact_once(
            text, f"{new}.Material Copper", f"{new}.Material Aluminium"
        )
        old_comment = f"// Fix5: {new}; material=Copper"
        if old_comment in text:
            text = replace_exact_once(
                text, old_comment, f"// SG3A material-only: {new}; material=Aluminium"
            )
    return text


def reverse_geo(candidate: str) -> str:
    text = candidate
    for old, new in reversed(tuple(VOLUME_MAP.items())):
        new_comment = f"// SG3A material-only: {new}; material=Aluminium"
        if new_comment in text:
            text = replace_exact_once(text, new_comment, f"// Fix5: {new}; material=Copper")
        text = replace_exact_once(
            text, f"{new}.Material Aluminium", f"{new}.Material Copper"
        )
        if new not in text:
            raise BuildError(f"missing SG3A can lineage token during reversal: {new}")
        text = text.replace(new, old)
    return replace_exact_once(text, HEADER_NEW, HEADER_OLD)


def transform_det(parent: str) -> str:
    text = parent
    for old, new in VOLUME_MAP.items():
        if old not in text:
            raise BuildError(f"missing SG3 detector lineage token: {old}")
        text = text.replace(old, new)
    return text


def reverse_det(candidate: str) -> str:
    text = candidate
    for old, new in reversed(tuple(VOLUME_MAP.items())):
        if new not in text:
            raise BuildError(f"missing SG3A detector lineage token: {new}")
        text = text.replace(new, old)
    return text


def build_expected() -> dict[str, bytes]:
    setup = "\n".join(
        (
            f"Name {SG3A_STEM}",
            "Version 1",
            f"Include {SG3A_STEM}.geo",
            f"Include {SG3A_STEM}.det",
            "SurroundingSphere 60 5 0 9 60",
            "",
        )
    )
    return {
        "setup": setup.encode(),
        "geo": transform_geo(SOURCE_FILES["geo"].read_text(encoding="utf-8")).encode(),
        "det": transform_det(SOURCE_FILES["det"].read_text(encoding="utf-8")).encode(),
        "intro": SOURCE_FILES["intro"].read_bytes(),
        "materials": SOURCE_FILES["materials"].read_bytes(),
    }


def can_volume_cm3() -> dict[str, float]:
    outer_radius = 15.3
    inner_radius = 15.1
    window_half_width = 1.898
    annular_area = math.pi * (outer_radius**2 - inner_radius**2)

    def integral(radius: float) -> float:
        a = window_half_width
        return a * math.sqrt(radius**2 - a**2) + radius**2 * math.asin(a / radius)

    removed_window_area = integral(outer_radius) - integral(inner_radius)
    parts = {
        "bottom_cap": math.pi * outer_radius**2 * 0.2,
        "side_wall_below": annular_area * 2.602,
        "side_wall_above": annular_area * 3.002,
        "window_band": annular_area * 3.796 - removed_window_area * 3.796,
    }
    parts["total"] = sum(parts.values())
    return parts


def volume_names(text: str) -> set[str]:
    return {
        line.split()[1]
        for line in text.splitlines()
        if line.startswith("Volume ") and len(line.split()) == 2
    }


def validate(expected: dict[str, bytes]) -> dict[str, Any]:
    for key, data in expected.items():
        if OUTPUT_FILES[key].read_bytes() != data:
            raise BuildError(f"generated {key} differs from deterministic expectation")

    parent_geo = SOURCE_FILES["geo"].read_text(encoding="utf-8")
    candidate_geo = OUTPUT_FILES["geo"].read_text(encoding="utf-8")
    parent_det = SOURCE_FILES["det"].read_text(encoding="utf-8")
    candidate_det = OUTPUT_FILES["det"].read_text(encoding="utf-8")
    if reverse_geo(candidate_geo) != parent_geo:
        raise BuildError("reversing SG3A material/lineage edits does not reconstruct SG3 geo")
    if reverse_det(candidate_det) != parent_det:
        raise BuildError("reversing SG3A lineage edits does not reconstruct SG3 det")
    if OUTPUT_FILES["intro"].read_bytes() != SOURCE_FILES["intro"].read_bytes():
        raise BuildError("intro drift")
    if OUTPUT_FILES["materials"].read_bytes() != SOURCE_FILES["materials"].read_bytes():
        raise BuildError("materials drift")

    parent_volumes = volume_names(parent_geo)
    candidate_volumes = volume_names(candidate_geo)
    removed = sorted(parent_volumes - candidate_volumes)
    added = sorted(candidate_volumes - parent_volumes)
    if removed != sorted(VOLUME_MAP) or added != sorted(VOLUME_MAP.values()):
        raise BuildError(f"unexpected physical-volume identity delta: {removed=}, {added=}")
    for old, new in VOLUME_MAP.items():
        if old in candidate_geo or old in candidate_det:
            raise BuildError(f"stale SG3 can token remains: {old}")
        if candidate_geo.count(f"{new}.Material Aluminium") != 1:
            raise BuildError(f"Al material assignment is not exact-once: {new}")

    return {
        "sg3_geo_reconstructed_byte_exact": True,
        "sg3_detector_map_reconstructed_byte_exact": True,
        "intro_byte_identical": True,
        "materials_byte_identical": True,
        "parent_volume_count": len(parent_volumes),
        "candidate_volume_count": len(candidate_volumes),
        "renamed_physical_volumes": VOLUME_MAP,
        "shape_pose_hierarchy_delta": "NONE__BYTE_EXACT_AFTER_MATERIAL_LINEAGE_REVERSAL",
        "detector_response_parameter_delta": "NONE__ONLY_LINEAGE_NAMES_CHANGED",
        "active_veto_policy_delta": "NONE__PASSIVE_CAN_REMAINS_OUTSIDE_WHITELIST",
    }


def mass_ledger(parts: dict[str, float]) -> str:
    lines = ["part,volume_cm3,cu_mass_kg,al_mass_kg,mass_change_kg"]
    for part in ("bottom_cap", "side_wall_below", "side_wall_above", "window_band", "total"):
        volume = parts[part]
        cu_mass = volume * CU_DENSITY_G_CM3 / 1000.0
        al_mass = volume * AL_DENSITY_G_CM3 / 1000.0
        lines.append(f"{part},{volume:.12g},{cu_mass:.12g},{al_mass:.12g},{al_mass-cu_mass:.12g}")
    return "\n".join(lines) + "\n"


def main() -> int:
    try:
        sources = verify_pinned_sources()
        expected = build_expected()
        for key, data in expected.items():
            atomic_write_once(OUTPUT_FILES[key], data)
        fidelity = validate(expected)
        parts = can_volume_cm3()
        atomic_write_once(
            DATA_DIR / "sg3a_al_can_mass_delta.csv", mass_ledger(parts).encode()
        )
        total_volume = parts["total"]
        report = {
            "status": "PASS__SG3A_STRICT_SG3_MATERIAL_ONLY_AL_CAN_CHILD",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_identity": "SG3A",
            "parent_identity": "SG3",
            "transport_launched": False,
            "physics_status": "GEOMETRY_ONLY__PHYSICS_UNKNOWN",
            "source_files": sources,
            "generated": {key: file_record(path) for key, path in OUTPUT_FILES.items()},
            "fidelity": fidelity,
            "only_physical_change": {
                "description": "four-piece 50 mK Still-like cold can Copper to Aluminium",
                "old_material": "Copper",
                "new_material": "Aluminium",
                "geometry_changed": False,
                "passive_not_veto": True,
                "volume_cm3": total_volume,
                "old_mass_kg": total_volume * CU_DENSITY_G_CM3 / 1000.0,
                "new_mass_kg": total_volume * AL_DENSITY_G_CM3 / 1000.0,
                "mass_change_kg": total_volume
                * (AL_DENSITY_G_CM3 - CU_DENSITY_G_CM3)
                / 1000.0,
            },
            "inherited_without_change": [
                "SG3 L0 10 mm-contact-band Cu heat-sink ring",
                "four inherited off-axis Cu cold-finger link chains",
                "SG3 compact passive Bi MXC-to-TES umbrella",
                "all plates, holes, active BGO/plastic volumes, thresholds, and Step05 policy",
                "all shapes, positions, rotations, mothers, and focused-ray geometry",
            ],
            "remaining_physics_gate": (
                "candidate-own corrected prompt, activation/inventory, actual-position delayed, "
                "37194-ray signal, common response/veto/Step05, and 81-node mission fold"
            ),
        }
        publish_json(AUDIT_DIR / "sg3a_geometry_validation.json", report)
        print(json.dumps({"status": report["status"], "only_physical_change": report["only_physical_change"]}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL__SG3A_BUILD", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
