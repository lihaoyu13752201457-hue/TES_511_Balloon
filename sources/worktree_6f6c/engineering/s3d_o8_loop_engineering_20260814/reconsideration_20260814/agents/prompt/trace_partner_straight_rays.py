#!/usr/bin/env python3
"""Trace the initial, unscattered annihilation-partner ray in true geometry."""

from __future__ import annotations

import csv
import subprocess
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT = HERE / "annihilation_partner_paths.csv"
SEGMENTS = HERE / "partner_straight_ray_segments.csv"
SUMMARY = HERE / "partner_straight_ray_summary.csv"
TRACER = HERE.parents[2] / "agents" / "prompt" / "trace_true_geometry_rays"
GEOMETRIES = {
    "S3d_O8": Path(
        "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
        "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
        "geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
    ),
    "Mass_model_511": Path(
        "/home/ubuntu/TES_511_Balloon/outputs/geometry/"
        "DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_"
        "20260701_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_"
        "megalib_proxy.geo.setup"
    ),
}
S3D_ACTIVE = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}


def active(geometry: str, volume: str) -> bool:
    if geometry == "S3d_O8":
        return volume in S3D_ACTIVE
    return volume.startswith("CsI_")


def material_bucket(material: str) -> str:
    if material == "Copper": return "cu"
    if material == "Aluminium": return "al"
    if material == "Nb": return "nb"
    if material == "MuMetal": return "mumetal"
    if material == "SilverSinterProxy": return "agproxy"
    if material == "W": return "w"
    if material == "BGO": return "bgo"
    if material == "CsI": return "csi"
    if material == "PlasticScintillator": return "plastic"
    if material == "Vacuum": return "vacuum"
    return "other"


def main() -> None:
    with INPUT.open(newline="") as stream:
        cases = list(csv.DictReader(stream))
    by_ray = {f"r{i}": case for i, case in enumerate(cases)}
    all_segments: list[dict[str, str]] = []
    for geometry, setup in GEOMETRIES.items():
        feed: list[str] = []
        for ray_id, case in by_ray.items():
            if case["geometry"] != geometry:
                continue
            feed.append(" ".join([
                ray_id,
                case["annihilation_x_cm"], case["annihilation_y_cm"], case["annihilation_z_cm"],
                case["partner_511_dx"], case["partner_511_dy"], case["partner_511_dz"],
                "100", "0.005",
            ]))
        proc = subprocess.run(
            [str(TRACER), str(setup)], input="\n".join(feed) + "\n",
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        fieldnames = None
        for line in proc.stdout.splitlines():
            if line.startswith("ray_id,"):
                fieldnames = next(csv.reader([line]))
            elif line.startswith("r") and fieldnames is not None:
                row = dict(zip(fieldnames, next(csv.reader([line]))))
                row["geometry"] = geometry
                all_segments.append(row)
    segment_fields = ["geometry"] + [field for field in all_segments[0] if field != "geometry"]
    with SEGMENTS.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=segment_fields)
        writer.writeheader()
        writer.writerows(all_segments)

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for segment in all_segments:
        grouped[segment["ray_id"]].append(segment)
    summaries: list[dict[str, object]] = []
    for ray_id, case in by_ray.items():
        segments = sorted(grouped[ray_id], key=lambda row: int(row["segment_index"]))
        first_active = next((row for row in segments if active(case["geometry"], row["deepest_volume"])), None)
        first_active_t = float(first_active["t_entry_cm"]) if first_active else float("inf")
        pre_chord: dict[str, float] = defaultdict(float)
        active_chord: dict[str, float] = defaultdict(float)
        for row in segments:
            length = float(row["path_cm"])
            bucket = material_bucket(row["material"])
            if float(row["t_entry_cm"]) < first_active_t:
                pre_chord[bucket] += min(length, first_active_t - float(row["t_entry_cm"]))
            if active(case["geometry"], row["deepest_volume"]):
                active_chord[bucket] += length
        summaries.append({
            "geometry": case["geometry"],
            "family": case["family"],
            "event_id": case["event_id"],
            "pair_material": case["pair_material"],
            "annihilation_material": case["annihilation_material"],
            "unscattered_partner_reaches_active": first_active is not None,
            "distance_to_first_active_cm": first_active_t if first_active else "inf",
            "first_active_volume": first_active["deepest_volume"] if first_active else "NONE",
            "active_bgo_chord_cm": active_chord["bgo"],
            "active_csi_chord_cm": active_chord["csi"],
            "active_plastic_chord_cm": active_chord["plastic"],
            "pre_active_cu_chord_cm": pre_chord["cu"],
            "pre_active_al_chord_cm": pre_chord["al"],
            "pre_active_nb_chord_cm": pre_chord["nb"],
            "pre_active_mumetal_chord_cm": pre_chord["mumetal"],
            "pre_active_agproxy_chord_cm": pre_chord["agproxy"],
            "pre_active_w_chord_cm": pre_chord["w"],
            "pre_active_other_chord_cm": pre_chord["other"],
            "pre_active_vacuum_chord_cm": pre_chord["vacuum"],
        })
    fields = list(summaries[0])
    with SUMMARY.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(summaries)
    print(f"wrote {len(all_segments)} segments and {len(summaries)} summaries")


if __name__ == "__main__":
    main()
