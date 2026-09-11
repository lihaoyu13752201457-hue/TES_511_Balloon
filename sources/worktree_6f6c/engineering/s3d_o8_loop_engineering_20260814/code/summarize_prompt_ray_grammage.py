#!/usr/bin/env python3
"""Aggregate exact MEGAlib ray segments into active/passive grammage."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path


DENSITY_G_CM3 = {
    "Vacuum": 0.0,
    "PlasticScintillator": 1.03,
    "BoratedPolyethylene5wtB": 0.95,
    "Aluminium": 2.7,
    "Kapton": 1.42,
    "BGO": 7.1,
    "W": 19.3,
    "Copper": 8.954,
    "MuMetal": 8.7,
    "Nb": 8.57,
}

ACTIVE_VOLUMES = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("segments", type=Path)
    parser.add_argument("--material-output", type=Path, required=True)
    parser.add_argument("--event-output", type=Path, required=True)
    args = parser.parse_args()

    by_material = defaultdict(lambda: {"length_cm": 0.0, "grammage_g_cm2": 0.0})
    with args.segments.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            material = row["material"]
            if material not in DENSITY_G_CM3:
                raise KeyError(f"No audited density for material {material!r}")
            length = float(row["length_cm"])
            density = DENSITY_G_CM3[material]
            category = "vacuum" if material == "Vacuum" else ("active" if row["volume"] in ACTIVE_VOLUMES else "passive")
            key = (int(row["ray_id"]), category, material)
            by_material[key]["length_cm"] += length
            by_material[key]["grammage_g_cm2"] += length * density

    material_rows = []
    by_event = defaultdict(lambda: defaultdict(float))
    for (ray_id, category, material), values in sorted(by_material.items()):
        material_rows.append(
            {
                "ray_id": ray_id,
                "category": category,
                "material": material,
                "density_g_cm3": DENSITY_G_CM3[material],
                **values,
            }
        )
        by_event[ray_id][f"{category}_length_cm"] += values["length_cm"]
        by_event[ray_id][f"{category}_grammage_g_cm2"] += values["grammage_g_cm2"]

    event_rows = []
    for ray_id, values in sorted(by_event.items()):
        active = values["active_grammage_g_cm2"]
        passive = values["passive_grammage_g_cm2"]
        event_rows.append(
            {
                "ray_id": ray_id,
                "active_length_cm": values["active_length_cm"],
                "active_grammage_g_cm2": active,
                "passive_length_cm": values["passive_length_cm"],
                "passive_grammage_g_cm2": passive,
                "total_nonvacuum_length_cm": values["active_length_cm"] + values["passive_length_cm"],
                "total_nonvacuum_grammage_g_cm2": active + passive,
            }
        )

    args.material_output.parent.mkdir(parents=True, exist_ok=True)
    with args.material_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(material_rows[0]))
        writer.writeheader()
        writer.writerows(material_rows)
    with args.event_output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(event_rows[0]))
        writer.writeheader()
        writer.writerows(event_rows)


if __name__ == "__main__":
    main()
