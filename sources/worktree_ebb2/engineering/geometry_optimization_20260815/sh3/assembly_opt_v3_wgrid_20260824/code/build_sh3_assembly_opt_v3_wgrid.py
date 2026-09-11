#!/usr/bin/env python3
"""Build SH3 OptV3 plus one full-aperture W multihole collimator.

The canonical SH3 OptV3 package is a frozen input. This builder copies its
setup, detector map and materials byte-for-byte, appends one delimited geometry
block, and fails closed if any pre-existing OptV3 byte has changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEOMETRY = PACKAGE / "geometry"
DATA = PACKAGE / "data"
AUDIT = PACKAGE / "audit"

GEO_NAME = "SH3_Assembly_OptV3.geo"
SETUP_NAME = "SH3_Assembly_OptV3.geo.setup"
DET_NAME = "SH3_Assembly_OptV3.det"
MATERIALS_NAME = "Materials_SH3_Assembly_OptV3.geo"
SOURCE_NAME = "model_a_grid_source_DEMO2_DR_v3p5_SG3B.geo"

OUTPUT_GEO = GEOMETRY / GEO_NAME
OUTPUT_SETUP = GEOMETRY / SETUP_NAME
OUTPUT_DET = GEOMETRY / DET_NAME
OUTPUT_MATERIALS = GEOMETRY / MATERIALS_NAME
OUTPUT_STATIC = AUDIT / "assembly_opt_v3_wgrid_static_validation.json"
OUTPUT_MANIFEST = DATA / "assembly_opt_v3_wgrid_manifest.json"

BASE_STATUS = "PASS__SH3_ASSEMBLY_OPT_V3_BUILT"
STATIC_STATUS = "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_STATIC"
BUILD_STATUS = "PASS__SH3_ASSEMBLY_OPT_V3_WGRID_BUILT"

BASE_AUTHORITY = {
    GEO_NAME: {
        "bytes": 424261,
        "sha256": "a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934",
    },
    SETUP_NAME: {
        "bytes": 137,
        "sha256": "52397889d6ac0d08296549942633ff09216cf1494fedb985127c48120d46eaea",
    },
    DET_NAME: {
        "bytes": 3103,
        "sha256": "12d3a6831f3d00da6668f48487e5d83f7a0354419fdec75cfec211b28373cae9",
    },
    MATERIALS_NAME: {
        "bytes": 2065,
        "sha256": "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a",
    },
}

SOURCE_FILE_SHA256 = "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9"
SOURCE_START = "// User multiholeW revision: side-window embedded W grid collimator."
SOURCE_END = "// BEGIN XS400_TOP_300K_FEEDTHROUGH_PIPE_PROXY"
SOURCE_FRAGMENT_SHA256 = "8db82c4c107511a831fbbc9b2c7f115a26f0795945bf41bf1c972631a7e0cf98"

BLOCK_BEGIN = "// BEGIN SH3_OPTV3_WGRID_ADDITION"
BLOCK_END = "// END SH3_OPTV3_WGRID_ADDITION"

# Pitch, web and depth come from the frozen model-A grid. Only the cell count
# is extended to cover SH3's unchanged 5.40 cm square opening.
APERTURE_HALF_CM = 2.7
PITCH_CM = 0.155
WEB_CM = 0.013
GRID_HALF_DEPTH_CM = 0.4
BAR_HALF_DEPTH_CM = 0.399
GRID_CENTER_CM = (-44.7, 0.0, -2.8)
INNER_WEB_COUNT = 34
CHANNEL_COUNT = 35


class BuildError(RuntimeError):
    """Fail-closed build error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": sha256_bytes(data)}


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o644)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_text(path: Path, value: str) -> None:
    atomic_bytes(path, value.encode("utf-8"))


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-package",
        type=Path,
        default=PACKAGE.parent / "assembly_opt_v3",
        help="Frozen canonical SH3 assembly_opt_v3 package.",
    )
    return parser.parse_args()


def verify_base(base: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    manifest_path = base / "data/assembly_opt_v3_manifest.json"
    static_path = base / "audit/assembly_opt_v3_static_validation.json"
    paths = {
        GEO_NAME: base / "geometry" / GEO_NAME,
        SETUP_NAME: base / "geometry" / SETUP_NAME,
        DET_NAME: base / "geometry" / DET_NAME,
        MATERIALS_NAME: base / "geometry" / MATERIALS_NAME,
    }
    required = [manifest_path, static_path, *paths.values()]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise BuildError(f"missing canonical OptV3 input(s): {missing}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    static = json.loads(static_path.read_text(encoding="utf-8"))
    if manifest.get("status") != BASE_STATUS:
        raise BuildError(f"canonical OptV3 manifest is not {BASE_STATUS}")
    if static.get("status") != "PASS__SH3_ASSEMBLY_OPT_V3_STATIC":
        raise BuildError("canonical OptV3 static validation is not PASS")

    stale: list[str] = []
    for name, path in paths.items():
        frozen = BASE_AUTHORITY[name]
        current = file_record(path)
        manifest_hash = manifest.get("outputs", {}).get(name, {}).get("sha256")
        if (
            current["sha256"] != frozen["sha256"]
            or current["bytes"] != frozen["bytes"]
            or manifest_hash != frozen["sha256"]
        ):
            stale.append(name)
    if stale:
        raise BuildError(f"canonical OptV3 authority drift: {stale}")
    return manifest, paths


def verify_model_a_rule() -> dict[str, Any]:
    source = DATA / SOURCE_NAME
    if not source.is_file() or sha256(source) != SOURCE_FILE_SHA256:
        raise BuildError("copied model-A source geometry is missing or not frozen")
    text = source.read_text(encoding="utf-8")
    if text.count(SOURCE_START) != 1 or text.count(SOURCE_END) != 1:
        raise BuildError("model-A W-grid extraction markers are not unique")
    start = text.index(SOURCE_START)
    end = text.index(SOURCE_END, start)
    fragment = text[start:end]
    if sha256_bytes(fragment.encode("utf-8")) != SOURCE_FRAGMENT_SHA256:
        raise BuildError("model-A W-grid source fragment hash mismatch")
    required = (
        "W_Multihole_CollimatorVac.Shape BRIK 0.4 1.898 1.898",
        "W_Multihole_Collimator_HBar.Shape BRIK 0.399 1.894 0.0065",
        "W_Multihole_Collimator_VBar_Center.Shape BRIK 0.399 0.0065 0.07",
    )
    horizontal = len(re.findall(r"^W_Multihole_Collimator_HBar\.Copy\s+", fragment, re.M))
    vertical = len(re.findall(r"^W_Multihole_Collimator_VBar_(?:Center|Edge)\.Copy\s+", fragment, re.M))
    if not all(token in fragment for token in required) or (horizontal, vertical) != (24, 600):
        raise BuildError("frozen model-A grid rule is not the expected 624-copy authority")
    return {
        **file_record(source),
        "fragment_sha256": SOURCE_FRAGMENT_SHA256,
        "source_copy_counts": {"horizontal": horizontal, "vertical": vertical},
        "inherited_pitch_cm": PITCH_CM,
        "inherited_web_cm": WEB_CM,
        "inherited_w_depth_cm": 2.0 * BAR_HALF_DEPTH_CM,
    }


def number(value: float) -> str:
    if abs(value) < 0.5e-9:
        value = 0.0
    return f"{value:.6f}"


def web_positions() -> list[float]:
    return [
        (index - (INNER_WEB_COUNT - 1) / 2.0) * PITCH_CM
        for index in range(INNER_WEB_COUNT)
    ]


def grid_block() -> str:
    lines = [
        BLOCK_BEGIN,
        "// Grid-only OptV3 variant. The earlier 'no multihole/grid' comment describes",
        "// the retained four-bar frame; that frame and every pre-existing SH3 byte remain unchanged.",
        "// Pitch/web/depth follow the frozen model-A rule; 35 x 35 cells cover the",
        "// unchanged 5.40 cm SH3 clear square without an uncollimated perimeter bypass.",
        "Volume W_Multihole_CollimatorVac",
        "W_Multihole_CollimatorVac.Material Vacuum",
        "W_Multihole_CollimatorVac.Visibility 0",
        "W_Multihole_CollimatorVac.Shape BRIK 0.400000 2.700000 2.700000",
        "W_Multihole_CollimatorVac.Position -44.700000 0.000000 -2.800000",
        "W_Multihole_CollimatorVac.Mother InstrumentFrame",
        "",
        "Volume W_Multihole_Collimator_HBar",
        "W_Multihole_Collimator_HBar.Material W",
        "W_Multihole_Collimator_HBar.Visibility 1",
        "W_Multihole_Collimator_HBar.Shape BRIK 0.399000 2.696000 0.006500",
        "",
        "Volume W_Multihole_Collimator_VBar_Center",
        "W_Multihole_Collimator_VBar_Center.Material W",
        "W_Multihole_Collimator_VBar_Center.Visibility 1",
        "W_Multihole_Collimator_VBar_Center.Shape BRIK 0.399000 0.006500 0.070000",
        "",
        "Volume W_Multihole_Collimator_VBar_Edge",
        "W_Multihole_Collimator_VBar_Edge.Material W",
        "W_Multihole_Collimator_VBar_Edge.Visibility 1",
        "W_Multihole_Collimator_VBar_Edge.Shape BRIK 0.399000 0.006500 0.065000",
        "",
    ]

    positions = web_positions()
    for index, z_rel in enumerate(positions):
        name = f"W_Multihole_Collimator_HBar_{index:03d}"
        lines.extend(
            (
                f"W_Multihole_Collimator_HBar.Copy {name}",
                f"{name}.Position 0.000000 0.000000 {number(z_rel)}",
                f"{name}.Mother W_Multihole_CollimatorVac",
                f"{name}.Visibility 1",
                "",
            )
        )

    for column, y_rel in enumerate(positions):
        for segment in range(CHANNEL_COUNT):
            serial = column * CHANNEL_COUNT + segment
            if segment == 0:
                template = "W_Multihole_Collimator_VBar_Edge"
                z_rel = -2.63
            elif segment == CHANNEL_COUNT - 1:
                template = "W_Multihole_Collimator_VBar_Edge"
                z_rel = 2.63
            else:
                template = "W_Multihole_Collimator_VBar_Center"
                z_rel = (segment - 17) * PITCH_CM
            name = f"{template}_{serial:04d}"
            lines.extend(
                (
                    f"{template}.Copy {name}",
                    f"{name}.Position 0.000000 {number(y_rel)} {number(z_rel)}",
                    f"{name}.Mother W_Multihole_CollimatorVac",
                    f"{name}.Visibility 1",
                    "",
                )
            )

    lines.extend((BLOCK_END, ""))
    return "\n".join(lines)


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def validate(
    base_geometry: str,
    variant_geometry: str,
    block: str,
    base_paths: dict[str, Path],
) -> dict[str, Any]:
    horizontal = count(r"^W_Multihole_Collimator_HBar\.Copy\s+", block)
    vertical_center = count(r"^W_Multihole_Collimator_VBar_Center\.Copy\s+", block)
    vertical_edge = count(r"^W_Multihole_Collimator_VBar_Edge\.Copy\s+", block)
    copy_names = re.findall(r"\.Copy\s+(\S+)$", block, re.MULTILINE)
    expected_h = [f"W_Multihole_Collimator_HBar_{index:03d}" for index in range(34)]
    expected_v = []
    for column in range(34):
        for segment in range(35):
            template = (
                "W_Multihole_Collimator_VBar_Edge"
                if segment in (0, 34)
                else "W_Multihole_Collimator_VBar_Center"
            )
            expected_v.append(f"{template}_{column * 35 + segment:04d}")

    base_declared = count(r"^Volume\s+", base_geometry)
    base_copies = count(r"\.Copy\s+", base_geometry)
    variant_declared = count(r"^Volume\s+", variant_geometry)
    variant_copies = count(r"\.Copy\s+", variant_geometry)
    w_volume_cm3 = (
        34 * (2 * 0.399) * (2 * 2.696) * (2 * 0.0065)
        + 1122 * (2 * 0.399) * (2 * 0.0065) * (2 * 0.07)
        + 68 * (2 * 0.399) * (2 * 0.0065) * (2 * 0.065)
    )
    checks = {
        "base_geometry_is_exact_byte_prefix": variant_geometry.startswith(base_geometry)
        and variant_geometry[len(base_geometry) :] == "\n" + block,
        "one_delimited_grid_addition": variant_geometry.count(BLOCK_BEGIN) == 1
        and variant_geometry.count(BLOCK_END) == 1,
        "base_has_expected_219_volume_declarations": base_declared == 219,
        "base_has_expected_2496_copy_statements": base_copies == 2496,
        "variant_has_base_plus_four_volume_declarations": variant_declared == 223,
        "variant_has_base_plus_1224_copy_statements": variant_copies == 3720,
        "grid_has_one_vacuum_mother_and_three_w_templates": count(
            r"^Volume W_Multihole_Collimator", block
        ) == 4,
        "grid_copy_counts_are_34_1122_68": (
            horizontal,
            vertical_center,
            vertical_edge,
        ) == (34, 1122, 68),
        "grid_copy_names_are_unique_and_contiguous": len(copy_names)
        == len(set(copy_names))
        == 1224
        and copy_names == expected_h + expected_v,
        "all_grid_copies_use_grid_vacuum_mother": count(
            r"^W_Multihole_Collimator_(?:HBar|VBar_(?:Center|Edge))_[0-9]+\.Mother W_Multihole_CollimatorVac$",
            block,
        ) == 1224,
        "no_grid_name_preexists_in_base": "W_Multihole_Collimator" not in base_geometry,
        "grid_rule_dimensions_exact": all(
            token in block
            for token in (
                "W_Multihole_CollimatorVac.Shape BRIK 0.400000 2.700000 2.700000",
                "W_Multihole_Collimator_HBar.Shape BRIK 0.399000 2.696000 0.006500",
                "W_Multihole_Collimator_VBar_Center.Shape BRIK 0.399000 0.006500 0.070000",
                "W_Multihole_Collimator_VBar_Edge.Shape BRIK 0.399000 0.006500 0.065000",
            )
        ),
        "grid_centered_in_unchanged_w_frame": (
            "W_Multihole_CollimatorVac.Position -44.700000 0.000000 -2.800000"
            in block
        ),
        "setup_byte_identical_to_base": OUTPUT_SETUP.read_bytes()
        == base_paths[SETUP_NAME].read_bytes(),
        "detector_map_byte_identical_to_base": OUTPUT_DET.read_bytes()
        == base_paths[DET_NAME].read_bytes(),
        "materials_byte_identical_to_base": OUTPUT_MATERIALS.read_bytes()
        == base_paths[MATERIALS_NAME].read_bytes(),
        "existing_four_bar_frame_occurs_once_each": all(
            base_geometry.count(f"Volume {name}")
            == variant_geometry.count(f"Volume {name}")
            == 1
            for name in (
                "SH3_OptV2_W_Frame_Top",
                "SH3_OptV2_W_Frame_Bottom",
                "SH3_OptV2_W_Frame_PosY",
                "SH3_OptV2_W_Frame_NegY",
            )
        ),
        "instrument_rotation_unchanged": base_geometry.count(
            "InstrumentFrame.Rotation 0 45 0"
        )
        == variant_geometry.count("InstrumentFrame.Rotation 0 45 0"),
        "source_sphere_unchanged": base_geometry.count(
            "SurroundingSphere 95 0 0 8 95"
        )
        == variant_geometry.count("SurroundingSphere 95 0 0 8 95"),
        "analytic_x_containment_margin_0p001_cm": (
            BAR_HALF_DEPTH_CM < GRID_HALF_DEPTH_CM
        ),
        "analytic_hbar_y_margin_0p004_cm": abs(
            (APERTURE_HALF_CM - 2.696) - 0.004
        ) < 1e-12,
        "analytic_edge_vbar_z_margin_0p005_cm": abs(
            (APERTURE_HALF_CM - (2.63 + 0.065)) - 0.005
        ) < 1e-12,
        "analytic_web_intersection_gap_0p001_cm": abs(
            ((PITCH_CM - WEB_CM) / 2 - 0.07) - 0.001
        ) < 1e-12,
        "grid_parent_inside_bgo_square_recess": APERTURE_HALF_CM < 3.0,
        "grid_w_daughters_clear_existing_frame_inner_faces": 2.696 < 2.7
        and 2.63 + 0.065 < 2.7,
        "grid_clear_of_front_mechanical_al_by_0p65_cm": (
            GRID_CENTER_CM[0] - GRID_HALF_DEPTH_CM > -45.75
        ),
        "computed_w_volume_matches_contract": abs(w_volume_cm3 - 3.623098752)
        < 1e-12,
    }
    return {
        "status": STATIC_STATUS if all(checks.values()) else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_Chimney_DR_Assembly_OptV3_WGrid",
        "checks": checks,
        "counts": {
            "base_volume_declarations": base_declared,
            "base_copy_statements": base_copies,
            "variant_volume_declarations": variant_declared,
            "variant_copy_statements": variant_copies,
            "grid_horizontal_copies": horizontal,
            "grid_vertical_center_copies": vertical_center,
            "grid_vertical_edge_copies": vertical_edge,
            "grid_total_copies": horizontal + vertical_center + vertical_edge,
            "grid_channels": CHANNEL_COUNT * CHANNEL_COUNT,
        },
        "placement_contract": {
            "coordinate_frame": "InstrumentFrame; no additional rotation",
            "grid_center_cm": list(GRID_CENTER_CM),
            "vacuum_parent_half_extent_cm_xyz": [0.4, 2.7, 2.7],
            "w_daughter_x_range_cm": [-45.099, -44.301],
            "existing_w_frame_x_range_cm": [-45.7, -43.7],
            "existing_w_frame_clear_half_width_yz_cm": 2.7,
            "bgo_square_recess_half_width_yz_cm": 3.0,
            "front_mechanical_al_downstream_face_x_cm": -45.75,
            "minimum_analytic_positive_clearance_cm": 0.001,
        },
        "physical_summary": {
            "pitch_cm": PITCH_CM,
            "web_cm": WEB_CM,
            "w_depth_cm": 2 * BAR_HALF_DEPTH_CM,
            "channel_array": [CHANNEL_COUNT, CHANNEL_COUNT],
            "w_volume_cm3": w_volume_cm3,
            "w_mass_g_at_19p3_g_cm3": w_volume_cm3 * 19.3,
            "normal_incidence_open_fraction": 1.0
            - w_volume_cm3
            / (2.0 * BAR_HALF_DEPTH_CM)
            / (2.0 * APERTURE_HALF_CM) ** 2,
        },
    }


def main() -> int:
    args = parse_args()
    base = args.base_package.resolve()
    base_manifest, base_paths = verify_base(base)
    source_record = verify_model_a_rule()
    base_geometry = base_paths[GEO_NAME].read_bytes().decode("utf-8")
    if not base_geometry.endswith("\n"):
        raise BuildError("canonical OptV3 geometry does not end with a newline")
    block = grid_block()
    variant_geometry = base_geometry + "\n" + block

    atomic_text(OUTPUT_GEO, variant_geometry)
    atomic_bytes(OUTPUT_SETUP, base_paths[SETUP_NAME].read_bytes())
    atomic_bytes(OUTPUT_DET, base_paths[DET_NAME].read_bytes())
    atomic_bytes(OUTPUT_MATERIALS, base_paths[MATERIALS_NAME].read_bytes())

    static = validate(base_geometry, variant_geometry, block, base_paths)
    atomic_json(OUTPUT_STATIC, static)
    if static["status"] != STATIC_STATUS:
        failed = [name for name, passed in static["checks"].items() if not passed]
        raise BuildError(f"W-grid static validation failed: {failed}")

    outputs = (OUTPUT_GEO, OUTPUT_SETUP, OUTPUT_DET, OUTPUT_MATERIALS)
    manifest = {
        "status": BUILD_STATUS,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": "SH3_Chimney_DR_Assembly_OptV3_WGrid",
        "scope": (
            "Frozen SH3 OptV3 plus one full-aperture 35 x 35 W multihole "
            "grid; no pre-existing byte changed."
        ),
        "base_package": str(base),
        "base_manifest_status": base_manifest["status"],
        "base_inputs": {name: file_record(path) for name, path in base_paths.items()},
        "model_a_grid_rule_authority": source_record,
        "outputs": {path.name: file_record(path) for path in outputs},
        "static_validation": file_record(OUTPUT_STATIC),
        "grid_contract": static["physical_summary"],
        "not_claimed": [
            "transport, activation, response, timing, background or sensitivity",
            "structural, fabrication or thermal qualification",
        ],
    }
    atomic_json(OUTPUT_MANIFEST, manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "static": static["status"],
                "manifest": str(OUTPUT_MANIFEST),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
