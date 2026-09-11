#!/usr/bin/env python3
"""Build a separate SH3 OptV3 variant with a physically smaller BGO aperture.

The front active-BGO subtraction cut is reduced from 6.00 cm to 3.796 cm,
the four obsolete W bars occupying the old recess are removed, and the exact
SG3 25 x 25 multihole grid is placed in the new opening.  All other frozen SH3
geometry text and all setup/detector/material files remain unchanged.  This
builder launches no transport and refuses drift in every copied authority.
"""

from __future__ import annotations

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
DATA = PACKAGE / "data"
BASE = DATA / "base_authority"
GEOMETRY = PACKAGE / "geometry"
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
OUTPUT_STATIC = AUDIT / "bgo_smallap_sg3grid_static_validation.json"
OUTPUT_MANIFEST = DATA / "bgo_smallap_sg3grid_manifest.json"

STATIC_STATUS = "PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_STATIC"
BUILD_STATUS = "PASS__SH3_OPTV3_BGO_SMALLAP_SG3GRID_BUILT"
COMPONENT = "SH3_Chimney_DR_Assembly_OptV3_BGO_SmallAp_SG3Grid"

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

SOURCE_SHA256 = "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9"
SOURCE_START = "// User multiholeW revision: side-window embedded W grid collimator."
SOURCE_END = "// BEGIN XS400_TOP_300K_FEEDTHROUGH_PIPE_PROXY"
SOURCE_FRAGMENT_SHA256 = "8db82c4c107511a831fbbc9b2c7f115a26f0795945bf41bf1c972631a7e0cf98"

BLOCK_BEGIN = "// BEGIN SH3_OPTV3_BGO_SMALLAP_SG3GRID_ADDITION"
BLOCK_END = "// END SH3_OPTV3_BGO_SMALLAP_SG3GRID_ADDITION"

GRID_CENTER_CM = (-44.7, 0.0, -2.8)
GRID_HALF_WIDTH_CM = 1.898
W_HALF_DEPTH_CM = 0.399
W_DENSITY_G_CM3 = 19.3

CENTRAL_GRID_W_VOLUME_CM3 = 1.796112864
OLD_W_FRAME_VOLUME_CM3 = 13.68
BGO_FRONT_DEPTH_CM = 4.0
BGO_INFILL_VOLUME_CM3 = (
    6.0**2 - (2.0 * GRID_HALF_WIDTH_CM) ** 2
) * BGO_FRONT_DEPTH_CM

BGO_RECESS_OLD = (
    "SH3_OptV2_BGOFront_SquareRecessCutShape.Parameters "
    "3.000000 3.000000 2.100000"
)
BGO_RECESS_NEW = (
    "SH3_OptV2_BGOFront_SquareRecessCutShape.Parameters "
    "1.898000 1.898000 2.100000"
)
FRAME_BEGIN = "// BEGIN SH3_OPTV2_SIMPLE_W_SQUARE_FRAME"
FRAME_END = "// END SH3_OPTV2_SIMPLE_W_SQUARE_FRAME"
FRAME_SHA256 = "41739777b8b1ee7b8c25085bf578155974126895089db98590b64f388c480985"
FILTER_POSITION_OLD = "SH3_Outer_Al_OpticalFilter.Position -42.15 0 -2.8"
FILTER_POSITION_NEW = "SH3_Outer_Al_OpticalFilter.Position -41.65 0 -2.8"


class BuildError(RuntimeError):
    """Fail-closed geometry build error."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def record(path: Path) -> dict[str, Any]:
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


def atomic_text(path: Path, text: str) -> None:
    atomic_bytes(path, text.encode("utf-8"))


def atomic_json(path: Path, payload: Any) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def verify_base() -> dict[str, Path]:
    paths = {
        name: BASE / name
        for name in (GEO_NAME, SETUP_NAME, DET_NAME, MATERIALS_NAME)
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise BuildError(f"missing copied frozen base input(s): {missing}")
    stale = []
    for name, path in paths.items():
        authority = BASE_AUTHORITY[name]
        if path.stat().st_size != authority["bytes"] or sha256(path) != authority["sha256"]:
            stale.append(name)
    if stale:
        raise BuildError(f"copied frozen SH3 authority drift: {stale}")
    return paths


def extract_adapted_sg3_grid() -> tuple[str, dict[str, Any]]:
    source = DATA / SOURCE_NAME
    if not source.is_file() or sha256(source) != SOURCE_SHA256:
        raise BuildError("frozen SG3 grid source is missing or stale")
    text = source.read_text(encoding="utf-8")
    if text.count(SOURCE_START) != 1 or text.count(SOURCE_END) != 1:
        raise BuildError("SG3 grid extraction markers are not unique")
    start = text.index(SOURCE_START)
    end = text.index(SOURCE_END, start)
    fragment = text[start:end]
    if sha256_bytes(fragment.encode("utf-8")) != SOURCE_FRAGMENT_SHA256:
        raise BuildError("SG3 grid source fragment hash mismatch")
    old_position = "W_Multihole_CollimatorVac.Position -25.9 0 -5.2"
    new_position = "W_Multihole_CollimatorVac.Position -44.7 0 -2.8"
    if fragment.count(old_position) != 1 or new_position in fragment:
        raise BuildError("unexpected SG3 grid placement contract")
    adapted = fragment.replace(old_position, new_position, 1).rstrip() + "\n"
    counts = {
        "horizontal_copies": len(re.findall(r"^W_Multihole_Collimator_HBar\.Copy ", adapted, re.M)),
        "vertical_center_copies": len(re.findall(r"^W_Multihole_Collimator_VBar_Center\.Copy ", adapted, re.M)),
        "vertical_edge_copies": len(re.findall(r"^W_Multihole_Collimator_VBar_Edge\.Copy ", adapted, re.M)),
    }
    if counts != {
        "horizontal_copies": 24,
        "vertical_center_copies": 552,
        "vertical_edge_copies": 48,
    }:
        raise BuildError(f"unexpected SG3 grid copy counts: {counts}")
    return adapted, {
        **record(source),
        "fragment_sha256": SOURCE_FRAGMENT_SHA256,
        "adaptation": {"from_position_cm": [-25.9, 0.0, -5.2], "to_position_cm": list(GRID_CENTER_CM)},
        "counts": counts,
    }


def shrink_bgo_and_remove_old_frame(base: str) -> tuple[str, str]:
    """Apply the aperture edits plus the required filter clearance move."""
    if base.count(BGO_RECESS_OLD) != 1 or BGO_RECESS_NEW in base:
        raise BuildError("unexpected frozen BGO recess contract")
    if base.count(FRAME_BEGIN) != 1 or base.count(FRAME_END) != 1:
        raise BuildError("old W-frame markers are not unique")
    frame_start = base.index(FRAME_BEGIN)
    frame_end = base.index(FRAME_END, frame_start) + len(FRAME_END)
    if frame_end < len(base) and base[frame_end] == "\n":
        frame_end += 1
    old_frame = base[frame_start:frame_end]
    if sha256_bytes(old_frame.encode("utf-8")) != FRAME_SHA256:
        raise BuildError("old W-frame block hash mismatch")
    expected_names = (
        "SH3_OptV2_W_Frame_Top",
        "SH3_OptV2_W_Frame_Bottom",
        "SH3_OptV2_W_Frame_PosY",
        "SH3_OptV2_W_Frame_NegY",
    )
    if any(old_frame.count(f"Volume {name}") != 1 for name in expected_names):
        raise BuildError("old W-frame block does not contain the expected four bars")
    if base.count(FILTER_POSITION_OLD) != 1 or FILTER_POSITION_NEW in base:
        raise BuildError("unexpected outer-filter placement contract")
    modified = base.replace(BGO_RECESS_OLD, BGO_RECESS_NEW, 1)
    modified = modified.replace(old_frame, "", 1)
    modified = modified.replace(FILTER_POSITION_OLD, FILTER_POSITION_NEW, 1)
    return modified, old_frame


def count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def validate(
    base: str,
    modified_base: str,
    variant: str,
    addition: str,
    old_frame: str,
    paths: dict[str, Path],
) -> dict[str, Any]:
    base_volumes = count(r"^Volume\s+", base)
    base_copies = count(r"\.Copy\s+", base)
    modified_volumes = count(r"^Volume\s+", modified_base)
    modified_copies = count(r"\.Copy\s+", modified_base)
    variant_volumes = count(r"^Volume\s+", variant)
    variant_copies = count(r"\.Copy\s+", variant)
    grid_copies = count(r"^W_Multihole_Collimator_(?:HBar|VBar_(?:Center|Edge))\.Copy\s+", addition)
    copy_names = re.findall(r"\.Copy\s+(\S+)$", addition, re.MULTILINE)
    frame_names = (
        "SH3_OptV2_W_Frame_Top",
        "SH3_OptV2_W_Frame_Bottom",
        "SH3_OptV2_W_Frame_PosY",
        "SH3_OptV2_W_Frame_NegY",
    )
    checks = {
        "variant_is_exact_authorized_base_edit_plus_grid": (
            variant.startswith(modified_base)
            and variant[len(modified_base):] == "\n" + addition
        ),
        "one_delimited_bgo_smallap_addition": (
            variant.count(BLOCK_BEGIN) == 1 and variant.count(BLOCK_END) == 1
        ),
        "base_counts_match_frozen_authority": base_volumes == 219 and base_copies == 2496,
        "only_four_old_w_frame_volumes_removed_before_grid": (
            modified_volumes == 215 and modified_copies == 2496
        ),
        "variant_volume_count_closes": variant_volumes == 219,
        "variant_adds_exactly_624_grid_copies": (
            variant_copies == 3120 and grid_copies == 624
        ),
        "grid_copy_names_unique": len(copy_names) == len(set(copy_names)) == 624,
        "sg3_grid_dimensions_exact": all(
            token in addition
            for token in (
                "W_Multihole_CollimatorVac.Shape BRIK 0.4 1.898 1.898",
                "W_Multihole_Collimator_HBar.Shape BRIK 0.399 1.894 0.0065",
                "W_Multihole_Collimator_VBar_Center.Shape BRIK 0.399 0.0065 0.07",
                "W_Multihole_Collimator_VBar_Edge.Shape BRIK 0.399 0.0065 0.0515",
            )
        ),
        "sg3_grid_recentered_to_sh3_front": "W_Multihole_CollimatorVac.Position -44.7 0 -2.8" in addition,
        "bgo_recess_changed_once_from_6cm_to_3p796cm": (
            base.count(BGO_RECESS_OLD) == 1
            and variant.count(BGO_RECESS_OLD) == 0
            and variant.count(BGO_RECESS_NEW) == 1
        ),
        "outer_filter_relocated_once_for_bgo_clearance": (
            base.count(FILTER_POSITION_OLD) == 1
            and variant.count(FILTER_POSITION_OLD) == 0
            and variant.count(FILTER_POSITION_NEW) == 1
        ),
        "outer_filter_fits_between_bgo_and_layer05": (
            -41.7 + 0.0015 < -41.65 < -41.6 - 0.0015
        ),
        "grid_envelope_exactly_matches_bgo_recess": abs(GRID_HALF_WIDTH_CM - 1.898) < 1e-12,
        "old_w_frame_block_removed_exactly": (
            old_frame.startswith(FRAME_BEGIN)
            and FRAME_BEGIN not in variant
            and FRAME_END not in variant
            and all(base.count(f"Volume {name}") == 1 for name in frame_names)
            and all(variant.count(f"Volume {name}") == 0 for name in frame_names)
        ),
        "no_passive_perimeter_mask_added": "W_SmallAperture_Mask_" not in variant,
        "grid_clear_of_front_mechanical_al": (
            GRID_CENTER_CM[0] - W_HALF_DEPTH_CM > -45.75
        ),
        "grid_axially_inside_bgo_front": (
            GRID_CENTER_CM[0] - W_HALF_DEPTH_CM > -45.7
            and GRID_CENTER_CM[0] + W_HALF_DEPTH_CM < -41.7
        ),
        "central_grid_volume_matches_sg3_contract": (
            abs(CENTRAL_GRID_W_VOLUME_CM3 - 1.796112864) < 1e-12
        ),
        "bgo_infill_volume_matches_square_difference": (
            abs(BGO_INFILL_VOLUME_CM3 - 86.361536) < 1e-12
        ),
        "setup_byte_identical_to_base": OUTPUT_SETUP.read_bytes() == paths[SETUP_NAME].read_bytes(),
        "detector_map_byte_identical_to_base": OUTPUT_DET.read_bytes() == paths[DET_NAME].read_bytes(),
        "materials_byte_identical_to_base": OUTPUT_MATERIALS.read_bytes() == paths[MATERIALS_NAME].read_bytes(),
        "tes_l0_unchanged": base.count("TES_L0.Shape BRIK 0.15 1.8 1.8") == variant.count("TES_L0.Shape BRIK 0.15 1.8 1.8") == 1,
        "active_bgo_detector_volume_identity_retained": (
            base.count("Volume SH3_BGO40_FrontOpticalAnnulus")
            == variant.count("Volume SH3_BGO40_FrontOpticalAnnulus")
            == 1
        ),
        "instrument_rotation_unchanged": base.count("InstrumentFrame.Rotation 0 45 0") == variant.count("InstrumentFrame.Rotation 0 45 0"),
        "source_sphere_unchanged": base.count("SurroundingSphere 95 0 0 8 95") == variant.count("SurroundingSphere 95 0 0 8 95"),
    }
    return {
        "status": STATIC_STATUS if all(checks.values()) else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": COMPONENT,
        "checks": checks,
        "counts": {
            "base_volume_declarations": base_volumes,
            "modified_base_volume_declarations": modified_volumes,
            "variant_volume_declarations": variant_volumes,
            "base_copy_statements": base_copies,
            "modified_base_copy_statements": modified_copies,
            "variant_copy_statements": variant_copies,
            "central_grid_copies": grid_copies,
            "central_grid_channels": 625,
            "old_w_frame_volumes_removed": 4,
        },
        "aperture_contract": {
            "old_active_bgo_square_opening_cm": 6.0,
            "new_active_bgo_square_opening_cm": 3.796,
            "perforated_grid_square_cm": 3.796,
            "grid_to_tes_l0_center_distance_cm": 6.15,
            "central_grid_pitch_cm": 0.155,
            "central_grid_web_cm": 0.013,
            "central_grid_w_depth_cm": 0.798,
            "central_grid_normal_open_area_cm2": 12.158848,
            "required_outer_filter_position_change_cm": {
                "from_x": -42.15,
                "to_x": -41.65,
                "reason": "avoid overlap with active BGO restored outside the 3.796 cm square cut",
            },
        },
        "mass_contract": {
            "central_grid_w_volume_cm3": CENTRAL_GRID_W_VOLUME_CM3,
            "old_w_frame_volume_removed_cm3": OLD_W_FRAME_VOLUME_CM3,
            "net_w_volume_change_cm3": CENTRAL_GRID_W_VOLUME_CM3 - OLD_W_FRAME_VOLUME_CM3,
            "net_w_mass_change_g_at_19p3": (
                CENTRAL_GRID_W_VOLUME_CM3 - OLD_W_FRAME_VOLUME_CM3
            ) * W_DENSITY_G_CM3,
            "active_bgo_infill_volume_cm3": BGO_INFILL_VOLUME_CM3,
        },
        "scope": "Geometry construction and static closure only; no response, background, activation, or sensitivity claim.",
    }


def main() -> int:
    paths = verify_base()
    sg3_grid, source_record = extract_adapted_sg3_grid()
    base = paths[GEO_NAME].read_text(encoding="utf-8")
    if not base.endswith("\n"):
        raise BuildError("frozen base geometry does not end with newline")
    modified_base, old_frame = shrink_bgo_and_remove_old_frame(base)
    addition = "\n".join(
        (
            BLOCK_BEGIN,
            "// Physical small-aperture variant: the active-BGO cut and this exact",
            "// SG3 grid share a 3.796 cm square footprint.",
            sg3_grid.rstrip(),
            BLOCK_END,
            "",
        )
    )
    variant = modified_base + "\n" + addition

    atomic_text(OUTPUT_GEO, variant)
    atomic_bytes(OUTPUT_SETUP, paths[SETUP_NAME].read_bytes())
    atomic_bytes(OUTPUT_DET, paths[DET_NAME].read_bytes())
    atomic_bytes(OUTPUT_MATERIALS, paths[MATERIALS_NAME].read_bytes())

    static = validate(base, modified_base, variant, addition, old_frame, paths)
    atomic_json(OUTPUT_STATIC, static)
    if static["status"] != STATIC_STATUS:
        failed = [name for name, passed in static["checks"].items() if not passed]
        raise BuildError(f"small-aperture static validation failed: {failed}")

    outputs = (OUTPUT_GEO, OUTPUT_SETUP, OUTPUT_DET, OUTPUT_MATERIALS)
    manifest = {
        "status": BUILD_STATUS,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "component_identity": COMPONENT,
        "scope": (
            "Separate frozen-SH3 derivative: active-BGO front square opening reduced "
            "to 3.796 cm, obsolete four-bar W frame removed, exact SG3 25 x 25 grid "
            "inserted, and the outer Al filter shifted 0.50 cm downstream solely to "
            "clear the restored BGO. Old packages are untouched."
        ),
        "base_inputs": {name: record(path) for name, path in paths.items()},
        "sg3_grid_source": source_record,
        "outputs": {path.name: record(path) for path in outputs},
        "static_validation": record(OUTPUT_STATIC),
        "aperture_contract": static["aperture_contract"],
        "mass_contract": static["mass_contract"],
        "not_claimed": [
            "particle transport, detector response, background, activation, or sensitivity",
            "structural, fabrication, thermal, or launch qualification",
            "unchanged signal response; the same EventList must be replayed before using Aeff or Fmin",
        ],
    }
    atomic_json(OUTPUT_MANIFEST, manifest)
    print(json.dumps({"status": BUILD_STATUS, "static": static["status"], "manifest": str(OUTPUT_MANIFEST)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
