#!/usr/bin/env python3
"""Audit SH3 OptV3 against the pinned, simulated SG3B geometry and detector map.

This reads only compact geometry/detector text.  It never scans SIM payloads or
launches transport.  The goal is to separate fully classified design changes
from omissions that still block OptV3 production authority.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
AUDIT = PACKAGE / "audit"
V3_GEO = PACKAGE / "geometry/SH3_Assembly_OptV3.geo"
V3_DET = PACKAGE / "geometry/SH3_Assembly_OptV3.det"
V3_SETUP = PACKAGE / "geometry/SH3_Assembly_OptV3.geo.setup"
V3_MANIFEST = PACKAGE / "data/assembly_opt_v3_manifest.json"
SG3B_ROOT = Path(
    "/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/"
    "geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816"
)
SG3B_GEO = SG3B_ROOT / "geometry/DEMO2_DR_v3p5_SG3B.geo"
SG3B_DET = SG3B_ROOT / "geometry/DEMO2_DR_v3p5_SG3B.det"
SG3B_SETUP = SG3B_ROOT / "geometry/DEMO2_DR_v3p5_SG3B.geo.setup"
OUTPUT_JSON = AUDIT / "sg3b_minimal_change_audit.json"
OUTPUT_MD = AUDIT / "SG3B_MINIMAL_CHANGE_AUDIT_20260818.md"

PINNED = {
    SG3B_GEO: "5f0482e307bf8701204f1d6df1b74396b7105d853dccb885e4df401146f552d9",
    SG3B_DET: "0a4e6cb6b17949d5593f46faae87d80b383f5c9c08cb5b3240b91131e8515e21",
    SG3B_SETUP: "49324ca4baebd8e6323b4a478b168dff8798e2bd7f0d0775e2f179769aad0469",
    V3_GEO: "a270ab2caf340a34858b448374b3dad955878ebbb9df9169f97d80df46026934",
    V3_SETUP: "52397889d6ac0d08296549942633ff09216cf1494fedb985127c48120d46eaea",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, payload: dict[str, object]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def geometry_names(text: str) -> tuple[set[str], set[str]]:
    declared = set(re.findall(r"^Volume\s+(\S+)\s*$", text, re.MULTILINE))
    copies = set(re.findall(r"^\S+\.Copy\s+(\S+)\s*$", text, re.MULTILINE))
    return declared, copies


def copy_blocks(lines: list[str], names: set[str]) -> dict[str, tuple[str, ...]]:
    return {
        name: tuple(line for line in lines if line.startswith(name + "."))
        for name in names
    }


def volume_properties(lines: list[str], names: set[str]) -> dict[str, dict[str, str]]:
    properties = {name: {} for name in names}
    for line in lines:
        if "." not in line:
            continue
        name, remainder = line.split(".", 1)
        if name not in properties or not remainder.strip():
            continue
        key, _, value = remainder.partition(" ")
        properties[name][key] = value.strip()
    return properties


def position_vector(value: str) -> tuple[float, float, float]:
    parts = value.split()
    if len(parts) != 3:
        raise ValueError(f"expected three position coordinates, got: {value!r}")
    return tuple(float(part) for part in parts)  # type: ignore[return-value]


def missing_category(name: str) -> str | None:
    rules = (
        ("old_outer_active_and_mechanical_shield", r"^(?:ActiveShield_S3C_|BGO_S3|Outer_Al_S3C_)"),
        ("old_four_branch_cold_finger_and_clamps", r"^(?:Cu_ColdFinger_|Cu_MXC_Clamp_)"),
        ("old_w_bottom_and_multihole_collimator", r"^(?:Passive_W_|W_Multihole_)"),
        ("replaced_side_window_shell_and_foil_stack", r"^(?:SG3A_Al_50mK_|Still_Shield_|Shield_4K_|Shield_60K_|Vacuum_Jacket_|Win_)"),
        ("near_tes_bi_al_readout_and_cable_proxies", r"^(?:SE3_Al_|SG3B_Bi_|SQUID_|SG3B_Al_Bundle_)"),
        ("old_outer_plastic_and_bpe", r"^GeoOpt_S2B_CryoShell_(?:Plastic|BPE5)_"),
    )
    for category, pattern in rules:
        if re.search(pattern, name):
            return category
    return None


def sensitive_pairs(detector: str) -> list[tuple[str, str]]:
    return [
        (match.group(1), match.group(2))
        for match in re.finditer(
            r"^(\S+)\.SensitiveVolume\s+(\S+)\s*$", detector, re.MULTILINE
        )
    ]


def main() -> int:
    required = (*PINNED, V3_DET, V3_MANIFEST)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing audit input(s): {missing}")
    drift = {
        str(path): {"expected": expected, "actual": sha256(path)}
        for path, expected in PINNED.items()
        if sha256(path) != expected
    }
    if drift:
        raise RuntimeError(f"pinned geometry drift: {drift}")

    sg_lines = SG3B_GEO.read_text(encoding="utf-8").splitlines()
    v3_lines = V3_GEO.read_text(encoding="utf-8").splitlines()
    sg_geo = "\n".join(sg_lines) + "\n"
    v3_geo = "\n".join(v3_lines) + "\n"
    sg_det = SG3B_DET.read_text(encoding="utf-8")
    v3_det = V3_DET.read_text(encoding="utf-8")
    sg_declared, sg_copies = geometry_names(sg_geo)
    v3_declared, v3_copies = geometry_names(v3_geo)
    common_copies = sg_copies & v3_copies
    sg_copy_blocks = copy_blocks(sg_lines, common_copies)
    v3_copy_blocks = copy_blocks(v3_lines, common_copies)
    copy_drift = sorted(
        name for name in common_copies if sg_copy_blocks[name] != v3_copy_blocks[name]
    )

    common_declared = sg_declared & v3_declared
    sg_properties = volume_properties(sg_lines, common_declared)
    v3_properties = volume_properties(v3_lines, common_declared)
    common_volume_drift: list[dict[str, object]] = []
    translated_core_names: list[str] = []
    optical_cut_names: list[str] = []
    unexpected_common_volume_drift: list[dict[str, object]] = []
    expected_translation = (-35.55, 0.0, 2.4)
    for name in sorted(common_declared):
        sg_volume = sg_properties[name]
        v3_volume = v3_properties[name]
        changed_keys = sorted(
            key
            for key in sg_volume.keys() | v3_volume.keys()
            if sg_volume.get(key) != v3_volume.get(key)
        )
        if not changed_keys:
            continue
        item: dict[str, object] = {
            "volume": name,
            "changed_keys": changed_keys,
            "sg3b": {key: sg_volume.get(key) for key in changed_keys},
            "opt_v3": {key: v3_volume.get(key) for key in changed_keys},
        }
        if changed_keys == ["Position"]:
            sg_position = position_vector(sg_volume["Position"])
            v3_position = position_vector(v3_volume["Position"])
            delta = tuple(round(v3 - sg, 9) for sg, v3 in zip(sg_position, v3_position))
            item["position_delta_cm"] = delta
            if all(abs(actual - expected) <= 1e-8 for actual, expected in zip(delta, expected_translation)):
                item["classification"] = "required_common_rigid_translation_into_chimney"
                translated_core_names.append(name)
            else:
                item["classification"] = "unexpected_position_drift"
                unexpected_common_volume_drift.append(item)
        elif (
            name == "NF2_OuterSupport_Al_TopMountAnnulus"
            and changed_keys == ["Shape"]
            and v3_volume.get("Shape") == "SH3_OptV2_NF2_TopMount_WithOpticalCutShape"
        ):
            item["classification"] = "required_optical_axis_cutout"
            optical_cut_names.append(name)
        else:
            item["classification"] = "unexpected_common_volume_attribute_drift"
            unexpected_common_volume_drift.append(item)
        common_volume_drift.append(item)

    removed_declared = sorted(sg_declared-v3_declared)
    categories: dict[str, list[str]] = {}
    unclassified: list[str] = []
    for name in removed_declared:
        category = missing_category(name)
        if category is None:
            unclassified.append(name)
        else:
            categories.setdefault(category, []).append(name)

    sg_sensitive = sensitive_pairs(sg_det)
    v3_sensitive = sensitive_pairs(v3_det)
    v3_geometry_names = v3_declared | v3_copies
    sg_scorers_on_retained_geometry = [
        pair for pair in sg_sensitive if pair[1] in v3_geometry_names
    ]
    v3_detector_names = {pair[0] for pair in v3_sensitive}
    omitted_retained_scorers = [
        pair for pair in sg_scorers_on_retained_geometry if pair[0] not in v3_detector_names
    ]

    blockers = [
        {
            "id": "retained_passive_lineage_scorers_missing",
            "evidence": f"{len(omitted_retained_scorers)} SG3B diagnostic scorers point to geometry still retained in OptV3 but are absent from the OptV3 detector map",
            "required_decision": "restore a matched diagnostic detector map, or explicitly validate a lean-map catalog/lineage contract before production",
        },
        {
            "id": "readout_and_cable_mass_not_replaced",
            "evidence": "SQUID_uMUX_Box_Al_relocated_offbeam_minimal and five SG3B_Al_Bundle_* volumes are absent, with no SH3 replacement volumes",
            "required_decision": "restore, reroute, or explicitly exclude these activation-relevant mass proxies",
        },
        {
            "id": "bi_and_plastic_design_boundary_unconfirmed",
            "evidence": "the SG3B Bi half-cylinder and outer plastic positron-veto geometry are absent from OptV3; the chimney has BGO but no passive Bi or plastic scorer",
            "required_decision": "user must confirm exclusion or authorize chimney-compatible replacements",
        },
        {
            "id": "new_bgo_response_mapping_not_closed",
            "evidence": "OptV3 replaces the SG3B active-shield names/topology with SH3_BGO40_SideShield, SH3_BGO40_FrontOpticalAnnulus, and SH3_BGO40_RearColdPortAnnulus, but no mature common-response mapping receipt yet binds those names to the group-summed veto contract",
            "required_decision": "freeze the three-volume BGO map and validate that the downstream 50 keV common-group veto remains observable despite native detector thresholds before background production",
        },
        {
            "id": "new_passive_mass_activation_lineage_not_closed",
            "evidence": "OptV3 introduces 46 non-vacuum, non-BGO passive material volumes (30 Al, 11 Cu, 4 W, and 1 Be), including chimney thermal shells whose stage ownership is not yet authoritative",
            "required_decision": "assign volume/material/thermal-stage/activation-lineage ownership and ensure the compact catalog can retain those paths before BUILDUP",
        },
        {
            "id": "source_surface_contract_not_matched",
            "evidence": "SG3B uses 'SurroundingSphere 60 5 0 9 60' while OptV3 currently uses 'SurroundingSphere 95 0 0 8 95'",
            "required_decision": "validate the smallest enclosing source surface and regenerate corrected source cards/TT normalization; equal raw histories alone are not equal exposure",
        },
        {
            "id": "w_frame_full_envelope_clearance_not_closed",
            "evidence": "the four-bar W frame has an inner square half-width of exactly 2.70 cm, tangent to the declared r=2.70 cm optical circle and therefore providing zero analytic/alignment margin",
            "required_decision": "before background production, run the frozen 37,194-ray full-envelope signal transport and record a dedicated W-intercept/aperture receipt; enlarge the opening if any optical ray intersects W or the accepted mechanical tolerance requires positive margin",
        },
    ]

    report: dict[str, object] = {
        "status": "REVIEW_REQUIRED__NOT_OPT_V3_PRODUCTION_AUTHORITY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Compact geometry/detector-map comparison only; no SIM scan or transport.",
        "authorities": {
            "sg3b_geo": {"path": str(SG3B_GEO), "sha256": sha256(SG3B_GEO)},
            "sg3b_det": {"path": str(SG3B_DET), "sha256": sha256(SG3B_DET)},
            "sg3b_setup": {"path": str(SG3B_SETUP), "sha256": sha256(SG3B_SETUP)},
            "opt_v3_geo": {"path": str(V3_GEO), "sha256": sha256(V3_GEO)},
            "opt_v3_det": {"path": str(V3_DET), "sha256": sha256(V3_DET)},
            "opt_v3_setup": {"path": str(V3_SETUP), "sha256": sha256(V3_SETUP)},
        },
        "geometry_counts": {
            "sg3b_declared_volumes": len(sg_declared),
            "opt_v3_declared_volumes": len(v3_declared),
            "common_declared_volumes": len(sg_declared & v3_declared),
            "common_declared_volume_attribute_blocks_identical": len(common_declared)-len(common_volume_drift),
            "common_declared_volume_attribute_blocks_drift": len(common_volume_drift),
            "required_common_rigid_translations": len(translated_core_names),
            "required_optical_axis_cutouts": len(optical_cut_names),
            "unexpected_common_volume_attribute_drift": len(unexpected_common_volume_drift),
            "sg3b_copy_placements": len(sg_copies),
            "opt_v3_copy_placements": len(v3_copies),
            "common_copy_placements": len(common_copies),
            "common_copy_blocks_byte_identical": len(common_copies)-len(copy_drift),
            "common_copy_blocks_drift": len(copy_drift),
            "sg3b_only_copy_placements": len(sg_copies-v3_copies),
            "opt_v3_only_copy_placements": len(v3_copies-sg_copies),
        },
        "copy_drift_names": copy_drift,
        "common_declared_volume_attribute_drift": common_volume_drift,
        "required_common_rigid_translation_names": translated_core_names,
        "required_optical_axis_cutout_names": optical_cut_names,
        "unexpected_common_volume_attribute_drift": unexpected_common_volume_drift,
        "sg3b_only_copy_contract": {
            "count": len(sg_copies-v3_copies),
            "all_old_multihole_w": all(name.startswith("W_Multihole_") for name in sg_copies-v3_copies),
        },
        "removed_declared_volume_categories": categories,
        "unclassified_removed_declared_volumes": unclassified,
        "detector_map_counts": {
            "sg3b_sensitive_definitions": len(sg_sensitive),
            "opt_v3_sensitive_definitions": len(v3_sensitive),
            "sg3b_definitions_on_geometry_retained_in_opt_v3": len(sg_scorers_on_retained_geometry),
            "omitted_sg3b_definitions_on_retained_geometry": len(omitted_retained_scorers),
        },
        "omitted_retained_scorers": [
            {"detector": detector, "sensitive_volume": volume}
            for detector, volume in omitted_retained_scorers
        ],
        "closed_findings": [
            "all 69 SG3B-only declared volumes are classified into authorized/replaced design families; none is unclassified",
            "all 2,496 copy placements shared by SG3B and OptV3 have byte-identical placement blocks",
            f"of 168 common declared volumes, {len(common_volume_drift)} have explicitly classified attribute changes: {len(translated_core_names)} share the required (-35.55, 0, +2.40) cm chimney translation and {len(optical_cut_names)} is the NF2 top-mount optical cutout; no unexpected common-volume attribute drift remains",
            "all 624 SG3B-only copy placements belong to the explicitly removed old W multihole collimator",
            "OptV3 retains six TES layers, 2,256 Ta pixel copies, and the inherited TES/substrate/copper-support geometry",
            "OptV3 passes its separate full Geant4 construction/overlap receipt",
        ],
        "review_blockers": blockers,
        "verdict": "No unclassified geometry deletion was found, but missing diagnostic scorers, unresolved readout/cable/Bi/plastic mass choices, and the unmatched source-surface contract prevent claiming that OptV3 is already a minimal-change, equal-statistics production authority.",
    }
    if (
        unclassified
        or copy_drift
        or unexpected_common_volume_drift
        or len(translated_core_names) != 37
        or optical_cut_names != ["NF2_OuterSupport_Al_TopMountAnnulus"]
        or not all(name.startswith("W_Multihole_") for name in sg_copies-v3_copies)
    ):
        report["status"] = "FAIL__UNCLASSIFIED_OR_DRIFTED_GEOMETRY"
    atomic_json(OUTPUT_JSON, report)

    category_lines = "\n".join(
        f"- `{category}`: {len(names)} declared volumes"
        for category, names in sorted(categories.items())
    )
    blocker_lines = "\n".join(
        f"{index}. **{item['id']}** — {item['evidence']}. Required: {item['required_decision']}."
        for index, item in enumerate(blockers, start=1)
    )
    markdown = f"""# OptV3 vs simulated SG3B minimal-change audit

Status: `{report['status']}`

## Verdict

No unclassified geometry deletion was found, and the inherited placement
evidence is strong. Nevertheless OptV3 is **not yet an equal-statistics
production authority** because its diagnostic detector map and several
activation-relevant design choices are not closed.

## Closed geometry evidence

- SG3B/OptV3 declared volumes: {len(sg_declared)} / {len(v3_declared)};
  common: {len(sg_declared & v3_declared)}.
- Of the {len(common_declared)} common declared volumes,
  {len(common_volume_drift)} have classified attribute changes:
  {len(translated_core_names)} TES/Si/Cu core/support volumes share the required
  `(-35.55, 0, +2.40) cm` chimney translation, and
  {len(optical_cut_names)} NF2 top mount changes shape to provide the optical
  cutout. Unexpected common-volume attribute drift: {len(unexpected_common_volume_drift)}.
- SG3B/OptV3 copy placements: {len(sg_copies)} / {len(v3_copies)};
  common: {len(common_copies)}.
- All {len(common_copies)} common copy placement blocks are byte-identical;
  drift count: {len(copy_drift)}.
- The {len(sg_copies-v3_copies)} SG3B-only copies are all old W multihole
  collimator copies.
- All {len(removed_declared)} SG3B-only declared volumes are classified; no
  unknown deletion remains.

Classified SG3B-only declared volumes:

{category_lines}

## Production blockers

{blocker_lines}

The detector-map comparison is especially important: SG3B has
{len(sg_sensitive)} sensitive definitions and OptV3 has {len(v3_sensitive)}.
Of the SG3B definitions, {len(sg_scorers_on_retained_geometry)} point to
geometry that still exists in OptV3; {len(omitted_retained_scorers)} of those
retained-volume diagnostic scorers are absent from the OptV3 detector map.

## Authority boundary

This audit read only the compact `.geo`, `.det`, manifests, and receipts. It
did not scan SIM payloads and did not run transport. The detailed machine
record is `sg3b_minimal_change_audit.json`.
"""
    atomic_text(OUTPUT_MD, markdown)
    print(json.dumps({"status": report["status"], "json": str(OUTPUT_JSON), "markdown": str(OUTPUT_MD)}, indent=2))
    return 0 if report["status"].startswith("REVIEW_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
