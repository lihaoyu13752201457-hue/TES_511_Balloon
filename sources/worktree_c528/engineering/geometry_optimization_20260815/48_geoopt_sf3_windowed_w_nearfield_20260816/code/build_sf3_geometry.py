#!/usr/bin/env python3
"""Build and statically validate SF3 as a strict additive delta on SE3.

SF3 is the hash-pinned SE3 geometry plus one passive, windowed, near-field
tungsten enclosure.  The physical addition consists of exactly three W
volumes: a 2.9 mm side sleeve, a 2.9 mm front plate with the frozen square
focused aperture, and a 2.9 mm rear cold-finger annulus.  The detector map,
materials, and included intro remain byte-identical to SE3; only the setup
identity changes.  No transport is launched by this program.
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

SE3_PACKAGE = Path(
    "/home/ubuntu/.codex/worktrees/626c/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/44_geoopt_se3_minimal_20260815"
)
SE3_GEOMETRY_DIR = SE3_PACKAGE / "geometry"

SE3_STEM = "DEMO2_DR_v3p5_SE3"
SF3_STEM = "DEMO2_DR_v3p5_SF3"

SOURCE_FILES = {
    "setup": SE3_GEOMETRY_DIR / f"{SE3_STEM}.geo.setup",
    "geo": SE3_GEOMETRY_DIR / f"{SE3_STEM}.geo",
    "det": SE3_GEOMETRY_DIR / f"{SE3_STEM}.det",
    "intro": SE3_GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": SE3_GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}
OUTPUT_FILES = {
    "setup": GEOMETRY_DIR / f"{SF3_STEM}.geo.setup",
    "geo": GEOMETRY_DIR / f"{SF3_STEM}.geo",
    "det": GEOMETRY_DIR / f"{SF3_STEM}.det",
    "intro": GEOMETRY_DIR
    / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": GEOMETRY_DIR / "Materials_DEMO2_DR_v3p5.geo",
}

PINNED_SE3 = {
    "setup": (123, "3e32bcd555a3c83cf8144949ad0bb31594f14f5204deb3784b2eb4cdd982ca98"),
    "geo": (695_607, "65ba13b39cc581bcf92fe5ab597a364fd0414ee0e09b766b9e8833893359a814"),
    "det": (56_538, "a7eb310ef3313533c33472a22a13bc18c87de25cde0984359b56a03d5d175580"),
    "intro": (500, "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52"),
    "materials": (1_897, "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf"),
}

BEGIN = "// BEGIN SF3_PASSIVE_NEARFIELD_WINDOWED_W_2P9MM"
END = "// END SF3_PASSIVE_NEARFIELD_WINDOWED_W_2P9MM"
INSERTION_MARKER = "// Fix5 magnetic/window panel: Win_MagShield_Al_foil_side; material=Aluminium"

W_DENSITY_G_CM3 = 19.3
WINDOW_HALF_WIDTH_CM = 1.9
FROZEN_PORT_HALF_WIDTH_CM = 1.898
AXIS_ROTATION_DEG = 45.0

SIDE_Z0 = -4.3575
SIDE_Z1 = 4.305
SIDE_RIN = 4.205
SIDE_ROUT = 4.495
FRONT_Z0 = -4.6475
FRONT_Z1 = -4.3575
REAR_Z0 = 4.305
REAR_Z1 = 4.595
CAP_ROUT = 4.495
REAR_RIN = 1.85

VOLUME_NAMES = (
    "SF3_W_NearField_SideSleeve_2p9mm",
    "SF3_W_NearField_FrontWindowPlate_2p9mm",
    "SF3_W_NearField_RearColdFingerAnnulus_2p9mm",
)
SHAPE_NAMES = (
    "SF3_W_NearField_FrontWindowPlate_2p9mm_FullDiskShape",
    "SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutShape",
    "SF3_W_NearField_FrontWindowPlate_2p9mm_WindowedShape",
)
ORIENTATION_NAMES = (
    "SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutOrientation",
)


class BuildError(RuntimeError):
    """Fail-closed SF3 build or validation error."""


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
        raise BuildError(f"write-once target already exists with different bytes: {path}")
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


def atomic_json_once(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_once(
        path,
        (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
            "utf-8"
        ),
    )


def publish_json_idempotent(
    path: Path, payload: dict[str, Any], *, volatile_keys: tuple[str, ...]
) -> None:
    """Publish once, or accept an existing payload differing only in timestamps."""
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BuildError(f"existing JSON is unreadable: {path}: {exc}") from exc
        expected_compare = dict(payload)
        existing_compare = dict(existing)
        for key in volatile_keys:
            expected_compare.pop(key, None)
            existing_compare.pop(key, None)
        if existing_compare != expected_compare:
            raise BuildError(f"write-once JSON exists with a different contract: {path}")
        return
    atomic_json_once(path, payload)


def verify_pinned_sources() -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for key, path in SOURCE_FILES.items():
        if not path.is_file():
            raise BuildError(f"missing pinned SE3 source {key}: {path}")
        record = file_record(path)
        expected_bytes, expected_sha = PINNED_SE3[key]
        if record["bytes"] != expected_bytes or record["sha256"] != expected_sha:
            raise BuildError(
                f"pinned SE3 {key} drift: got bytes={record['bytes']} sha={record['sha256']}"
            )
        records[key] = record
    return records


def sf3_block() -> str:
    return f"""{BEGIN}
// SF3 is a strict add-only child of SE3.  W is passive and is not an active-veto volume.
// InstrumentFrame already carries Rotation 0 45 0; these PCON axes only rotate onto x-prime.
// All nearest inherited solids retain 0.005 cm (50 micrometre) clearance.

Volume {VOLUME_NAMES[0]}
{VOLUME_NAMES[0]}.Material W
{VOLUME_NAMES[0]}.Visibility 1
{VOLUME_NAMES[0]}.Shape PCON 0 360 2 {SIDE_Z0} {SIDE_RIN} {SIDE_ROUT} {SIDE_Z1} {SIDE_RIN} {SIDE_ROUT}
{VOLUME_NAMES[0]}.Position 0 0 -5.2
{VOLUME_NAMES[0]}.Rotation 0 90 0
{VOLUME_NAMES[0]}.Mother InstrumentFrame

Shape PCON SF3_W_NearField_FrontWindowPlate_2p9mm_FullDiskShape
SF3_W_NearField_FrontWindowPlate_2p9mm_FullDiskShape.Parameters 0 360 2 {FRONT_Z0} 0 {CAP_ROUT} {FRONT_Z1} 0 {CAP_ROUT}
Shape BRIK SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutShape
SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutShape.Parameters {WINDOW_HALF_WIDTH_CM} {WINDOW_HALF_WIDTH_CM} 0.1451
Orientation SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutOrientation
SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutOrientation.Position 0 0 -4.5025
Shape Subtraction SF3_W_NearField_FrontWindowPlate_2p9mm_WindowedShape
SF3_W_NearField_FrontWindowPlate_2p9mm_WindowedShape.Parameters SF3_W_NearField_FrontWindowPlate_2p9mm_FullDiskShape SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutShape SF3_W_NearField_FrontWindowPlate_2p9mm_WindowCutOrientation
Volume {VOLUME_NAMES[1]}
{VOLUME_NAMES[1]}.Material W
{VOLUME_NAMES[1]}.Visibility 1
{VOLUME_NAMES[1]}.Shape SF3_W_NearField_FrontWindowPlate_2p9mm_WindowedShape
{VOLUME_NAMES[1]}.Position 0 0 -5.2
{VOLUME_NAMES[1]}.Rotation 0 90 0
{VOLUME_NAMES[1]}.Mother InstrumentFrame

Volume {VOLUME_NAMES[2]}
{VOLUME_NAMES[2]}.Material W
{VOLUME_NAMES[2]}.Visibility 1
{VOLUME_NAMES[2]}.Shape PCON 0 360 2 {REAR_Z0} {REAR_RIN} {CAP_ROUT} {REAR_Z1} {REAR_RIN} {CAP_ROUT}
{VOLUME_NAMES[2]}.Position 0 0 -5.2
{VOLUME_NAMES[2]}.Rotation 0 90 0
{VOLUME_NAMES[2]}.Mother InstrumentFrame

{END}
"""


def build_expected() -> dict[str, bytes]:
    base_geo = SOURCE_FILES["geo"].read_text(encoding="utf-8")
    if base_geo.count(INSERTION_MARKER) != 1:
        raise BuildError("SE3 insertion marker is not unique")
    if BEGIN in base_geo or END in base_geo:
        raise BuildError("SE3 parent unexpectedly contains the SF3 block")
    candidate_geo = base_geo.replace(
        INSERTION_MARKER, sf3_block() + "\n" + INSERTION_MARKER, 1
    )
    setup = "\n".join(
        (
            f"Name {SF3_STEM}",
            "Version 1",
            f"Include {SF3_STEM}.geo",
            f"Include {SF3_STEM}.det",
            "SurroundingSphere 60 5 0 9 60",
            "",
        )
    )
    return {
        "setup": setup.encode("utf-8"),
        "geo": candidate_geo.encode("utf-8"),
        "det": SOURCE_FILES["det"].read_bytes(),
        "intro": SOURCE_FILES["intro"].read_bytes(),
        "materials": SOURCE_FILES["materials"].read_bytes(),
    }


def strip_sf3_block(candidate: str) -> str:
    if candidate.count(BEGIN) != 1 or candidate.count(END) != 1:
        raise BuildError("candidate must contain exactly one complete SF3 block")
    start = candidate.index(BEGIN)
    end = candidate.index(END, start) + len(END)
    # ``sf3_block`` is newline-terminated and the insertion keeps one blank
    # separator before the inherited marker.  Remove that exact separator so
    # the parent bytes are reconstructed, rather than normalising whitespace.
    if candidate[end : end + 2] == "\n\n":
        end += 2
    elif end < len(candidate) and candidate[end] == "\n":
        end += 1
    return candidate[:start] + candidate[end:]


def declared_names(text: str, keyword: str) -> list[str]:
    prefix = keyword + " "
    names: list[str] = []
    for line in text.splitlines():
        fields = line.split()
        if not line.startswith(prefix):
            continue
        # Geomega shape declarations are ``Shape <type> <name>``; Volume and
        # Orientation declarations are ``<keyword> <name>``.
        index = 2 if keyword == "Shape" else 1
        if len(fields) > index:
            names.append(fields[index])
    return names


def mass_rows() -> list[dict[str, Any]]:
    side_volume = math.pi * (SIDE_ROUT**2 - SIDE_RIN**2) * (SIDE_Z1 - SIDE_Z0)
    front_volume = (
        math.pi * CAP_ROUT**2 - (2.0 * WINDOW_HALF_WIDTH_CM) ** 2
    ) * (FRONT_Z1 - FRONT_Z0)
    rear_volume = math.pi * (CAP_ROUT**2 - REAR_RIN**2) * (REAR_Z1 - REAR_Z0)
    specs = (
        (
            VOLUME_NAMES[0],
            "side_sleeve",
            side_volume,
            SIDE_Z0,
            SIDE_Z1,
            SIDE_RIN,
            SIDE_ROUT,
            "none",
        ),
        (
            VOLUME_NAMES[1],
            "front_square_window_plate",
            front_volume,
            FRONT_Z0,
            FRONT_Z1,
            0.0,
            CAP_ROUT,
            f"square_half_width_cm={WINDOW_HALF_WIDTH_CM}",
        ),
        (
            VOLUME_NAMES[2],
            "rear_cold_finger_annulus",
            rear_volume,
            REAR_Z0,
            REAR_Z1,
            REAR_RIN,
            CAP_ROUT,
            "circular_service_aperture",
        ),
    )
    rows = []
    for name, role, volume, z0, z1, rin, rout, aperture in specs:
        rows.append(
            {
                "volume_name": name,
                "role": role,
                "material": "W",
                "density_g_cm3": W_DENSITY_G_CM3,
                "xprime_min_cm": z0,
                "xprime_max_cm": z1,
                "inner_radius_cm": rin,
                "outer_radius_cm": rout,
                "aperture": aperture,
                "volume_cm3": volume,
                "mass_kg": volume * W_DENSITY_G_CM3 / 1000.0,
            }
        )
    return rows


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        raise BuildError("mass ledger cannot be empty")
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        handle.flush()
        handle.seek(0)
        return handle.read().encode("utf-8")


def validate_outputs(expected: dict[str, bytes]) -> dict[str, Any]:
    failures: list[str] = []
    for key, path in OUTPUT_FILES.items():
        if not path.is_file():
            failures.append(f"missing generated {key}: {path}")
        elif path.read_bytes() != expected[key]:
            failures.append(f"generated {key} differs from deterministic build")
    if failures:
        raise BuildError("; ".join(failures))

    parent_geo = SOURCE_FILES["geo"].read_text(encoding="utf-8")
    candidate_geo = OUTPUT_FILES["geo"].read_text(encoding="utf-8")
    reconstructed = strip_sf3_block(candidate_geo)
    if reconstructed != parent_geo:
        raise BuildError("removing the one SF3 block does not reconstruct SE3 byte-for-byte")

    parent_volumes = set(declared_names(parent_geo, "Volume"))
    candidate_volumes = set(declared_names(candidate_geo, "Volume"))
    added_volumes = sorted(candidate_volumes - parent_volumes)
    removed_volumes = sorted(parent_volumes - candidate_volumes)
    if added_volumes != sorted(VOLUME_NAMES) or removed_volumes:
        raise BuildError(
            f"physical delta is not exactly the three SF3 W volumes: added={added_volumes}, removed={removed_volumes}"
        )
    parent_shapes = set(declared_names(parent_geo, "Shape"))
    candidate_shapes = set(declared_names(candidate_geo, "Shape"))
    added_shapes = sorted(candidate_shapes - parent_shapes)
    removed_shapes = sorted(parent_shapes - candidate_shapes)
    parent_orientations = set(declared_names(parent_geo, "Orientation"))
    candidate_orientations = set(declared_names(candidate_geo, "Orientation"))
    added_orientations = sorted(candidate_orientations - parent_orientations)
    removed_orientations = sorted(parent_orientations - candidate_orientations)
    if added_shapes != sorted(SHAPE_NAMES) or removed_shapes:
        raise BuildError(
            f"shape delta is not exact: added={added_shapes}, removed={removed_shapes}"
        )
    if added_orientations != sorted(ORIENTATION_NAMES) or removed_orientations:
        raise BuildError(
            "orientation delta is not exact: "
            f"added={added_orientations}, removed={removed_orientations}"
        )
    count_contract = {
        "parent_volume_declarations": len(declared_names(parent_geo, "Volume")),
        "sf3_volume_declarations": len(declared_names(candidate_geo, "Volume")),
        "parent_shape_declarations": len(declared_names(parent_geo, "Shape")),
        "sf3_shape_declarations": len(declared_names(candidate_geo, "Shape")),
        "parent_orientation_declarations": len(declared_names(parent_geo, "Orientation")),
        "sf3_orientation_declarations": len(declared_names(candidate_geo, "Orientation")),
        "detector_declarations": sum(
            line.startswith(("MDCalorimeter ", "Scintillator "))
            for line in det_text.splitlines()
        ) if 'det_text' in locals() else None,
    }
    for name in VOLUME_NAMES:
        required = (
            f"Volume {name}",
            f"{name}.Material W",
            f"{name}.Position 0 0 -5.2",
            f"{name}.Rotation 0 90 0",
            f"{name}.Mother InstrumentFrame",
        )
        for line in required:
            if candidate_geo.count(line) != 1:
                raise BuildError(f"SF3 volume contract is not exact-once: {line}")

    intro = OUTPUT_FILES["intro"].read_text(encoding="utf-8")
    materials = OUTPUT_FILES["materials"].read_text(encoding="utf-8")
    if intro.count("InstrumentFrame.Rotation 0 45 0") != 1:
        raise BuildError("the inherited 45-degree InstrumentFrame rotation is not exact-once")
    if materials.count("Material W\n") != 1 or "W.Density 19.3" not in materials:
        raise BuildError("pinned W material definition is missing or duplicated")

    setup_expected = expected["setup"].decode("utf-8")
    if OUTPUT_FILES["setup"].read_text(encoding="utf-8") != setup_expected:
        raise BuildError("SF3 setup identity is not exact")
    if OUTPUT_FILES["det"].read_bytes() != SOURCE_FILES["det"].read_bytes():
        raise BuildError("detector map drifted; SF3 W must remain passive")
    det_text = OUTPUT_FILES["det"].read_text(encoding="utf-8")
    leaked_to_det = sorted(name for name in VOLUME_NAMES if name in det_text)
    if leaked_to_det:
        raise BuildError(f"passive SF3 W leaked into detector map: {leaked_to_det}")
    count_contract["detector_declarations"] = sum(
        line.startswith(("MDCalorimeter ", "Scintillator "))
        for line in det_text.splitlines()
    )
    expected_counts = {
        "parent_volume_declarations": 235,
        "sf3_volume_declarations": 238,
        "parent_shape_declarations": 256,
        "sf3_shape_declarations": 259,
        "parent_orientation_declarations": 116,
        "sf3_orientation_declarations": 117,
        "detector_declarations": 125,
    }
    if count_contract != expected_counts:
        raise BuildError(
            f"declaration-count contract drift: got={count_contract}, expected={expected_counts}"
        )

    rows = mass_rows()
    total_volume = math.fsum(float(row["volume_cm3"]) for row in rows)
    total_mass = math.fsum(float(row["mass_kg"]) for row in rows)
    return {
        "status": "PASS__SF3_STRICT_ADDITIVE_GEOMETRY_DELTA",
        "model_identity": "SF3",
        "parent_identity": "SE3",
        "physics_status": "UNKNOWN__TRANSPORT_NOT_RUN",
        "transport_launched": False,
        "checks": {
            "pinned_se3_parent": True,
            "parent_reconstructed_byte_for_byte_after_block_removal": True,
            "setup_identity_only_renamed": True,
            "intro_byte_identical": True,
            "materials_byte_identical": True,
            "detector_map_byte_identical": True,
            "exactly_three_added_physical_volumes": True,
            "exactly_three_added_shapes_and_one_orientation": True,
            "no_removed_physical_volumes": True,
            "all_added_volumes_are_passive_W": True,
            "all_added_volumes_are_InstrumentFrame_daughters": True,
            "instrument_rotation_0_45_0_frozen": True,
            "sf3_volumes_absent_from_detector_map": True,
            "front_square_window_covers_frozen_1p898cm_port": WINDOW_HALF_WIDTH_CM
            >= FROZEN_PORT_HALF_WIDTH_CM,
        },
        "coordinate_contract": {
            "world_plus_Z": "sky/up",
            "sky_facing_axis": "-xprime",
            "focused_photon_direction": "+xprime",
            "instrument_rotation_y_deg": AXIS_ROTATION_DEG,
            "sf3_volume_axis_rotation": [0.0, 90.0, 0.0],
            "sf3_volume_position_in_InstrumentFrame_cm": [0.0, 0.0, -5.2],
            "front_square_window_half_width_cm": WINDOW_HALF_WIDTH_CM,
            "frozen_upstream_port_half_width_cm": FROZEN_PORT_HALF_WIDTH_CM,
        },
        "delta": {
            "added_volumes": added_volumes,
            "removed_volumes": removed_volumes,
            "added_shapes": added_shapes,
            "removed_shapes": removed_shapes,
            "added_orientations": added_orientations,
            "removed_orientations": removed_orientations,
            "declaration_counts": count_contract,
            "material": "W",
            "passive_only": True,
            "total_W_volume_cm3": total_volume,
            "total_W_mass_kg": total_mass,
            "minimum_inherited_clearance_cm": 0.005,
        },
        "generated": {key: file_record(path) for key, path in OUTPUT_FILES.items()},
        "parent": {key: file_record(path) for key, path in SOURCE_FILES.items()},
    }


def write_products(expected: dict[str, bytes], parent_records: dict[str, dict[str, Any]]) -> None:
    for key, data in expected.items():
        atomic_write_once(OUTPUT_FILES[key], data)
    rows = mass_rows()
    atomic_write_once(DATA_DIR / "sf3_mass_ledger.csv", csv_bytes(rows))
    manifest = {
        "status": "PASS__SF3_SOURCE_MANIFEST",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_identity": "SF3",
        "parent_identity": "SE3",
        "parent": parent_records,
        "generated": {key: file_record(path) for key, path in OUTPUT_FILES.items()},
        "geometry_contract": {
            "operation": "COPY_PINNED_SE3_THEN_INSERT_EXACTLY_ONE_ADDITIVE_BLOCK",
            "added_volumes": list(VOLUME_NAMES),
            "material": "W",
            "passive_only": True,
            "instrument_rotation_y_deg": AXIS_ROTATION_DEG,
            "physics_status": "UNKNOWN__TRANSPORT_NOT_RUN",
        },
    }
    publish_json_idempotent(
        DATA_DIR / "sf3_source_manifest.json",
        manifest,
        volatile_keys=("created_at_utc",),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="publish deterministic write-once products")
    mode.add_argument("--check", action="store_true", help="validate existing products without modifying them")
    args = parser.parse_args()

    try:
        parent_records = verify_pinned_sources()
        expected = build_expected()
        if args.write:
            write_products(expected, parent_records)
        report = validate_outputs(expected)
        report["validated_at_utc"] = datetime.now(timezone.utc).isoformat()
        if args.write:
            publish_json_idempotent(
                AUDIT_DIR / "sf3_geometry_validation.json",
                report,
                volatile_keys=("validated_at_utc",),
            )
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL__SF3_GEOMETRY_BUILD_OR_STATIC_VALIDATION",
                    "error": str(exc),
                    "transport_launched": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
