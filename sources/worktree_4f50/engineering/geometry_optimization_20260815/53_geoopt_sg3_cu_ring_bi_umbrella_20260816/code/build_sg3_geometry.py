#!/usr/bin/env python3
"""Build SG3 as a two-change, byte-reversible child of frozen SF3.

The only physical edits are (1) replacing the deepest solid Cu substrate
heat-sink plate with a 1 cm-wide square annulus extending 1 cm beyond the
nominal TES substrate edge and (2) replacing the three passive SF3 W pieces
with one compact 4.796 mm Bi MXC-to-TES shadow umbrella.  This program never
launches transport.
"""

from __future__ import annotations

import argparse
import csv
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

SF3_PACKAGE = Path(
    "/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/48_geoopt_sf3_windowed_w_nearfield_20260816"
)
SF3_GEOMETRY_DIR = SF3_PACKAGE / "geometry"

SF3_STEM = "DEMO2_DR_v3p5_SF3"
SG3_STEM = "DEMO2_DR_v3p5_SG3"

SOURCE_FILES = {
    "setup": SF3_GEOMETRY_DIR / f"{SF3_STEM}.geo.setup",
    "geo": SF3_GEOMETRY_DIR / f"{SF3_STEM}.geo",
    "det": SF3_GEOMETRY_DIR / f"{SF3_STEM}.det",
    "intro": SF3_GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": SF3_GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}
OUTPUT_FILES = {
    "setup": GEOMETRY_DIR / f"{SG3_STEM}.geo.setup",
    "geo": GEOMETRY_DIR / f"{SG3_STEM}.geo",
    "det": GEOMETRY_DIR / f"{SG3_STEM}.det",
    "intro": GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}

PINNED_SF3 = {
    "setup": (123, "9eb9ac18473ce516139e21983bc24c42906e066784a0e2a05e6b1d227029c0c3"),
    "geo": (697_978, "7d2a5ee19d118d8ecb2c095203d7a8c6046e3c0e0020a67ba63d77ba399d8b16"),
    "det": (56_538, "a7eb310ef3313533c33472a22a13bc18c87de25cde0984359b56a03d5d175580"),
    "intro": (500, "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52"),
    "materials": (1_897, "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf"),
}

SF3_W_BEGIN = "// BEGIN SF3_PASSIVE_NEARFIELD_WINDOWED_W_2P9MM"
SF3_W_END = "// END SF3_PASSIVE_NEARFIELD_WINDOWED_W_2P9MM"
INSERTION_MARKER = "// Fix5 magnetic/window panel: Win_MagShield_Al_foil_side; material=Aluminium"

OLD_DISK = """// Volume Cu_SubstrateSupport_SolidDisk_L0_deepest; material=Copper
Volume Cu_SubstrateSupport_SolidDisk_L0_deepest
Cu_SubstrateSupport_SolidDisk_L0_deepest.Material Copper
Cu_SubstrateSupport_SolidDisk_L0_deepest.Visibility 1
Cu_SubstrateSupport_SolidDisk_L0_deepest.Shape BRIK 0.175 2.2 2.2

Cu_SubstrateSupport_SolidDisk_L0_deepest.Position 3.42 0 -5.2
Cu_SubstrateSupport_SolidDisk_L0_deepest.Mother InstrumentFrame
"""

RING_BEGIN = "// BEGIN SG3_CU_L0_HEATSINK_RING"
RING_END = "// END SG3_CU_L0_HEATSINK_RING"
RING_VOLUME = "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm"
RING_OUTER_SHAPE = f"{RING_VOLUME}_OuterShape"
RING_CUT_SHAPE = f"{RING_VOLUME}_CenterCutShape"
RING_CUT_ORIENTATION = f"{RING_VOLUME}_CenterCutOrientation"
RING_SHAPE = f"{RING_VOLUME}_Shape"

TES_SUBSTRATE_HALF_CM = 1.8
RING_OUTER_HALF_CM = 2.8
RING_INNER_HALF_CM = 0.8
RING_HALF_X_CM = 0.175
RING_X_CM = 3.42
RING_Y_CM = 0.0
RING_Z_CM = -5.2

BI_BEGIN = "// BEGIN SG3_PASSIVE_BI_MXC_TES_SHADOW_UMBRELLA_4P796MM"
BI_END = "// END SG3_PASSIVE_BI_MXC_TES_SHADOW_UMBRELLA_4P796MM"
BI_VOLUME = "SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm"
BI_HALF_X_CM = 3.9
BI_HALF_Y_CM = 2.25
BI_HALF_Z_CM = 0.2398
BI_X_CM = 0.1
BI_Y_CM = 0.0
BI_Z_CM = -2.1502
BI_DENSITY_G_CM3 = 9.747

OLD_DET_BLOCK = """Scintillator Cu_SubstrateSupport_SolidDisk_L0_deepest_SD
Cu_SubstrateSupport_SolidDisk_L0_deepest_SD.SensitiveVolume Cu_SubstrateSupport_SolidDisk_L0_deepest
Cu_SubstrateSupport_SolidDisk_L0_deepest_SD.DetectorVolume Cu_SubstrateSupport_SolidDisk_L0_deepest
Cu_SubstrateSupport_SolidDisk_L0_deepest_SD.TriggerThreshold 0.001
Cu_SubstrateSupport_SolidDisk_L0_deepest_SD.EnergyResolution Gauss 0.001 0.001 1
Cu_SubstrateSupport_SolidDisk_L0_deepest_SD.EnergyResolution Gauss 3000 3000 1
"""
RING_SD = f"{RING_VOLUME}_SD"


def ring_det_block() -> str:
    return f"""Scintillator {RING_SD}
{RING_SD}.SensitiveVolume {RING_VOLUME}
{RING_SD}.DetectorVolume {RING_VOLUME}
{RING_SD}.TriggerThreshold 0.001
{RING_SD}.EnergyResolution Gauss 0.001 0.001 1
{RING_SD}.EnergyResolution Gauss 3000 3000 1
"""

BI_MATERIAL_BEGIN = "# BEGIN SG3_BISMUTH_MATERIAL"
BI_MATERIAL_END = "# END SG3_BISMUTH_MATERIAL"

CU_DENSITY_G_CM3 = 8.96
W_DENSITY_G_CM3 = 19.3
SF3_W_VOLUME_CM3 = 98.17139650161902


class BuildError(RuntimeError):
    """Fail-closed SG3 build error."""


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


def publish_json_idempotent(path: Path, payload: dict[str, Any]) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        compare = dict(payload)
        for item in (existing, compare):
            item.pop("generated_at_utc", None)
        if existing != compare:
            raise BuildError(f"write-once JSON exists with a different contract: {path}")
        return
    atomic_write_once(path, data)


def verify_pinned_sources() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for key, path in SOURCE_FILES.items():
        if not path.is_file():
            raise BuildError(f"missing pinned SF3 source {key}: {path}")
        record = file_record(path)
        expected_bytes, expected_sha = PINNED_SF3[key]
        if record["bytes"] != expected_bytes or record["sha256"] != expected_sha:
            raise BuildError(f"pinned SF3 {key} drift: {record}")
        records[key] = record
    return records


def extract_marked_block(text: str, begin: str, end: str) -> tuple[str, str]:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise BuildError(f"marked block is not exact-once: {begin}")
    start = text.index(begin)
    stop = text.index(end, start) + len(end)
    if text[stop : stop + 2] == "\n\n":
        stop += 2
    elif stop < len(text) and text[stop] == "\n":
        stop += 1
    return text[start:stop], text[:start] + text[stop:]


def ring_block() -> str:
    return f"""{RING_BEGIN}
// Replaces the SF3 solid L0 Cu plate.  The annulus overlaps the nominal
// 1.8 cm TES substrate projection by 1.0 cm and protrudes beyond it by 1.0 cm.
// The four inherited edge rods at y,z = +/-1.95 cm terminate inside this band.
Shape BRIK {RING_OUTER_SHAPE}
{RING_OUTER_SHAPE}.Parameters {RING_HALF_X_CM} {RING_OUTER_HALF_CM} {RING_OUTER_HALF_CM}
Shape BRIK {RING_CUT_SHAPE}
{RING_CUT_SHAPE}.Parameters 0.1751 {RING_INNER_HALF_CM} {RING_INNER_HALF_CM}
Orientation {RING_CUT_ORIENTATION}
{RING_CUT_ORIENTATION}.Position 0 0 0
Shape Subtraction {RING_SHAPE}
{RING_SHAPE}.Parameters {RING_OUTER_SHAPE} {RING_CUT_SHAPE} {RING_CUT_ORIENTATION}
Volume {RING_VOLUME}
{RING_VOLUME}.Material Copper
{RING_VOLUME}.Visibility 1
{RING_VOLUME}.Shape {RING_SHAPE}
{RING_VOLUME}.Position {RING_X_CM} {RING_Y_CM:g} {RING_Z_CM}
{RING_VOLUME}.Mother InstrumentFrame
{RING_END}
"""


def bi_block() -> str:
    return f"""{BI_BEGIN}
// Passive Bi only: this is not an active-veto volume.
// Compact canopy under the MXC and above the TES; it does not wrap the detector.
// Bounds in InstrumentFrame: x=[-3.8,4.0], y=[-2.25,2.25], z=[-2.39,-1.9104] cm.
Volume {BI_VOLUME}
{BI_VOLUME}.Material Bi
{BI_VOLUME}.Visibility 1
{BI_VOLUME}.Shape BRIK {BI_HALF_X_CM} {BI_HALF_Y_CM} {BI_HALF_Z_CM}
{BI_VOLUME}.Position {BI_X_CM} {BI_Y_CM:g} {BI_Z_CM}
{BI_VOLUME}.Mother InstrumentFrame
{BI_END}
"""


def bi_material_block() -> str:
    return f"""

{BI_MATERIAL_BEGIN}
# Natural bismuth engineering proxy (effectively 100% Bi-209).
Material Bi
Bi.Density {BI_DENSITY_G_CM3}
Bi.Component Bi 1
{BI_MATERIAL_END}
"""


def build_expected() -> tuple[dict[str, bytes], str]:
    parent_geo = SOURCE_FILES["geo"].read_text(encoding="utf-8")
    sf3_w_block, without_w = extract_marked_block(parent_geo, SF3_W_BEGIN, SF3_W_END)
    if without_w.count(OLD_DISK) != 1:
        raise BuildError("SF3 L0 solid Cu disk block is not exact-once")
    candidate_geo = without_w.replace(OLD_DISK, ring_block(), 1)
    if candidate_geo.count(INSERTION_MARKER) != 1:
        raise BuildError("Bi insertion marker is not unique")
    candidate_geo = candidate_geo.replace(
        INSERTION_MARKER, bi_block() + "\n" + INSERTION_MARKER, 1
    )

    setup = "\n".join(
        (
            f"Name {SG3_STEM}",
            "Version 1",
            f"Include {SG3_STEM}.geo",
            f"Include {SG3_STEM}.det",
            "SurroundingSphere 60 5 0 9 60",
            "",
        )
    )
    materials = SOURCE_FILES["materials"].read_text(encoding="utf-8") + bi_material_block()
    parent_det = SOURCE_FILES["det"].read_text(encoding="utf-8")
    if parent_det.count(OLD_DET_BLOCK) != 1:
        raise BuildError("SF3 L0 detector-map block is not exact-once")
    candidate_det = parent_det.replace(OLD_DET_BLOCK, ring_det_block(), 1)
    expected = {
        "setup": setup.encode(),
        "geo": candidate_geo.encode(),
        "det": candidate_det.encode(),
        "intro": SOURCE_FILES["intro"].read_bytes(),
        "materials": materials.encode(),
    }
    return expected, sf3_w_block


def reverse_to_sf3(candidate_geo: str, sf3_w_block: str) -> str:
    _, text = extract_marked_block(candidate_geo, BI_BEGIN, BI_END)
    if text.count(ring_block()) != 1:
        raise BuildError("SG3 ring block is not byte-exact for reversal")
    text = text.replace(ring_block(), OLD_DISK, 1)
    if text.count(INSERTION_MARKER) != 1:
        raise BuildError("SF3 W reinsertion marker is not unique")
    return text.replace(INSERTION_MARKER, sf3_w_block + INSERTION_MARKER, 1)


def volume_names(text: str) -> list[str]:
    return [line.split()[1] for line in text.splitlines() if line.startswith("Volume ")]


def mass_ledger() -> tuple[list[dict[str, Any]], dict[str, float]]:
    old_cu_volume = 2 * 0.175 * (2 * 2.2) * (2 * 2.2)
    ring_area = (2 * RING_OUTER_HALF_CM) ** 2 - (2 * RING_INNER_HALF_CM) ** 2
    ring_volume = 2 * RING_HALF_X_CM * ring_area
    bi_volume = (2 * BI_HALF_X_CM) * (2 * BI_HALF_Y_CM) * (2 * BI_HALF_Z_CM)
    rows = [
        {
            "change": "remove",
            "volume": "Cu_SubstrateSupport_SolidDisk_L0_deepest",
            "material": "Copper",
            "volume_cm3": old_cu_volume,
            "density_g_cm3": CU_DENSITY_G_CM3,
            "mass_kg": old_cu_volume * CU_DENSITY_G_CM3 / 1000.0,
        },
        {
            "change": "add",
            "volume": RING_VOLUME,
            "material": "Copper",
            "volume_cm3": ring_volume,
            "density_g_cm3": CU_DENSITY_G_CM3,
            "mass_kg": ring_volume * CU_DENSITY_G_CM3 / 1000.0,
        },
        {
            "change": "remove",
            "volume": "SF3_three_piece_passive_W_total",
            "material": "W",
            "volume_cm3": SF3_W_VOLUME_CM3,
            "density_g_cm3": W_DENSITY_G_CM3,
            "mass_kg": SF3_W_VOLUME_CM3 * W_DENSITY_G_CM3 / 1000.0,
        },
        {
            "change": "add",
            "volume": BI_VOLUME,
            "material": "Bi",
            "volume_cm3": bi_volume,
            "density_g_cm3": BI_DENSITY_G_CM3,
            "mass_kg": bi_volume * BI_DENSITY_G_CM3 / 1000.0,
        },
    ]
    summary = {
        "old_l0_cu_mass_kg": rows[0]["mass_kg"],
        "new_l0_cu_ring_mass_kg": rows[1]["mass_kg"],
        "l0_cu_mass_change_kg": rows[1]["mass_kg"] - rows[0]["mass_kg"],
        "sf3_W_removed_mass_kg": rows[2]["mass_kg"],
        "sg3_Bi_added_mass_kg": rows[3]["mass_kg"],
        "total_sg3_minus_sf3_mass_kg": (
            rows[1]["mass_kg"] + rows[3]["mass_kg"]
            - rows[0]["mass_kg"] - rows[2]["mass_kg"]
        ),
    }
    return rows, summary


def write_mass_csv(rows: list[dict[str, Any]]) -> None:
    path = DATA_DIR / "sg3_mass_delta_ledger.csv"
    fields = ("change", "volume", "material", "volume_cm3", "density_g_cm3", "mass_kg")
    lines = [",".join(fields)]
    for row in rows:
        lines.append(
            ",".join(
                str(row[field]) if not isinstance(row[field], float) else f"{row[field]:.12g}"
                for field in fields
            )
        )
    atomic_write_once(path, ("\n".join(lines) + "\n").encode())


def validate(expected: dict[str, bytes], sf3_w_block: str) -> dict[str, Any]:
    for key, data in expected.items():
        if OUTPUT_FILES[key].read_bytes() != data:
            raise BuildError(f"generated {key} differs from deterministic expectation")
    geo = OUTPUT_FILES["geo"].read_text(encoding="utf-8")
    materials = OUTPUT_FILES["materials"].read_text(encoding="utf-8")
    if reverse_to_sf3(geo, sf3_w_block) != SOURCE_FILES["geo"].read_text(encoding="utf-8"):
        raise BuildError("reversing the two SG3 geometry edits does not reconstruct SF3")
    if not materials.endswith(bi_material_block()):
        raise BuildError("Bi material block is not an exact suffix")
    if materials[: -len(bi_material_block())].encode() != SOURCE_FILES["materials"].read_bytes():
        raise BuildError("removing the Bi material block does not reconstruct SF3 materials")
    candidate_det = OUTPUT_FILES["det"].read_text(encoding="utf-8")
    if candidate_det.count(ring_det_block()) != 1:
        raise BuildError("SG3 ring detector-map block is not exact-once")
    if candidate_det.replace(ring_det_block(), OLD_DET_BLOCK, 1).encode() != SOURCE_FILES["det"].read_bytes():
        raise BuildError("reversing the required ring detector-map edit does not reconstruct SF3")
    if OUTPUT_FILES["intro"].read_bytes() != SOURCE_FILES["intro"].read_bytes():
        raise BuildError("intro drift")

    parent_volumes = volume_names(SOURCE_FILES["geo"].read_text(encoding="utf-8"))
    candidate_volumes = volume_names(geo)
    removed = sorted(set(parent_volumes) - set(candidate_volumes))
    added = sorted(set(candidate_volumes) - set(parent_volumes))
    expected_removed = sorted(
        [
            "Cu_SubstrateSupport_SolidDisk_L0_deepest",
            "SF3_W_NearField_FrontWindowPlate_2p9mm",
            "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
            "SF3_W_NearField_SideSleeve_2p9mm",
        ]
    )
    expected_added = sorted([RING_VOLUME, BI_VOLUME])
    if removed != expected_removed or added != expected_added:
        raise BuildError(f"physical volume delta drift: removed={removed}, added={added}")
    if any(".Material W" in line for line in geo.splitlines() if line.startswith("SF3_W_")):
        raise BuildError("SF3 W volume assignment survived in SG3")
    if geo.count(f"{BI_VOLUME}.Material Bi") != 1:
        raise BuildError("Bi umbrella material assignment is not exact-once")
    if geo.count(f"{RING_VOLUME}.Material Copper") != 1:
        raise BuildError("Cu ring material assignment is not exact-once")

    return {
        "parent_volume_count": len(parent_volumes),
        "candidate_volume_count": len(candidate_volumes),
        "removed_physical_volumes": removed,
        "added_physical_volumes": added,
        "sf3_geo_reconstructed_byte_exact": True,
        "sf3_materials_reconstructed_byte_exact": True,
        "sf3_detector_map_reconstructed_byte_exact": True,
        "detector_map_delta": {
            "reason": "removed physical disk cannot remain a detector volume",
            "old_sensitive_volume": "Cu_SubstrateSupport_SolidDisk_L0_deepest",
            "new_sensitive_volume": RING_VOLUME,
            "response_parameters_preserved": True,
        },
        "intro_byte_identical": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        sources = verify_pinned_sources()
        expected, sf3_w_block = build_expected()
        if not args.check_only:
            for key, data in expected.items():
                atomic_write_once(OUTPUT_FILES[key], data)
        missing = [str(path) for path in OUTPUT_FILES.values() if not path.is_file()]
        if missing:
            raise BuildError(f"missing SG3 output(s): {missing}")
        fidelity = validate(expected, sf3_w_block)
        rows, mass = mass_ledger()
        if not args.check_only:
            write_mass_csv(rows)
        report = {
            "status": "PASS__SG3_TWO_CHANGE_BYTE_REVERSIBLE_SF3_CHILD",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "model_identity": "SG3",
            "parent_identity": "SF3",
            "transport_launched": False,
            "physics_status": "GEOMETRY_ONLY__PHYSICS_UNKNOWN",
            "source_files": sources,
            "generated": {key: file_record(path) for key, path in OUTPUT_FILES.items()},
            "fidelity": fidelity,
            "geometry_contract": {
                "l0_heat_sink_ring": {
                    "volume": RING_VOLUME,
                    "axial_thickness_cm": 2 * RING_HALF_X_CM,
                    "outer_half_width_cm": RING_OUTER_HALF_CM,
                    "inner_half_width_cm": RING_INNER_HALF_CM,
                    "in_plane_total_band_width_cm": RING_OUTER_HALF_CM - RING_INNER_HALF_CM,
                    "nominal_tes_substrate_half_width_cm": TES_SUBSTRATE_HALF_CM,
                    "overlap_into_tes_substrate_projection_cm": TES_SUBSTRATE_HALF_CM - RING_INNER_HALF_CM,
                    "protrusion_beyond_tes_edge_cm": RING_OUTER_HALF_CM - TES_SUBSTRATE_HALF_CM,
                    "inherited_edge_rod_center_abs_yz_cm": 1.95,
                },
                "bi_shadow_umbrella": {
                    "volume": BI_VOLUME,
                    "thickness_cm": 2 * BI_HALF_Z_CM,
                    "bounds_instrument_cm": {
                        "x": [BI_X_CM - BI_HALF_X_CM, BI_X_CM + BI_HALF_X_CM],
                        "y": [BI_Y_CM - BI_HALF_Y_CM, BI_Y_CM + BI_HALF_Y_CM],
                        "z": [BI_Z_CM - BI_HALF_Z_CM, BI_Z_CM + BI_HALF_Z_CM],
                    },
                    "passive_not_veto": True,
                },
            },
            "mass_delta": mass,
            "hard_gates_remaining": [
                "static inherited-mesh clearance and frozen 37194-ray audit",
                "Geant4 CheckForOverlaps 10000 0.0001 without beamOn",
                "native SF3/SG3 frozen-bank navigation audit",
                "candidate-own corrected prompt to activation to actual-position delayed chain",
            ],
        }
        if not args.check_only:
            publish_json_idempotent(AUDIT_DIR / "sg3_geometry_validation.json", report)
        print(json.dumps({"status": report["status"], "mass_delta": mass}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL__SG3_BUILD", "error": str(exc)}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
