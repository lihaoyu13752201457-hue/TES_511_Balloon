#!/usr/bin/env python3
"""Build Step01 geometry audit artifacts for NEW_GEO_RE.

The authoritative transport geometry remains the MEGAlib ``.geo`` generated
under ``outputs/geometry``.  This script adds maintenance-facing artifacts:

* a cavity/window z-position audit table;
* a lightweight WRL visualization generated from ``bounds.json``.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


STEP_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
OUT = STEP_DIR / "outputs"


def fmt(value: float | str | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if abs(value) < 5.0e-13:
        value = 0.0
    return f"{value:.9g}"


def load_bounds() -> dict:
    return json.loads(BOUNDS.read_text(encoding="utf-8"))


def z_span(center: float, thick: float) -> tuple[float, float]:
    return center - thick / 2.0, center + thick / 2.0


def window_desc(window_names: list[str], win_by_name: dict[str, dict]) -> dict[str, str]:
    if not window_names:
        return {
            "window": "",
            "window_material": "",
            "window_z_center_cm": "",
            "window_z_min_cm": "",
            "window_z_max_cm": "",
            "window_radius_cm": "",
            "window_thickness_cm": "",
        }
    pieces = []
    materials = []
    centers = []
    zmins = []
    zmaxs = []
    radii = []
    thicks = []
    for name in window_names:
        w = win_by_name[name]
        z0, z1 = z_span(float(w["z_center"]), float(w["thick"]))
        pieces.append(name)
        materials.append(str(w.get("material", "")))
        centers.append(fmt(float(w["z_center"])))
        zmins.append(fmt(z0))
        zmaxs.append(fmt(z1))
        radii.append(fmt(float(w["r_max"])))
        thicks.append(fmt(float(w["thick"])))
    return {
        "window": "; ".join(pieces),
        "window_material": "; ".join(materials),
        "window_z_center_cm": "; ".join(centers),
        "window_z_min_cm": "; ".join(zmins),
        "window_z_max_cm": "; ".join(zmaxs),
        "window_radius_cm": "; ".join(radii),
        "window_thickness_cm": "; ".join(thicks),
    }


def row_for(
    cavity: str,
    kind: str,
    z_inner_bot: float,
    z_inner_top: float,
    top_cap_z0: float,
    top_cap_z1: float,
    hole_radius: float,
    window_names: list[str],
    win_by_name: dict[str, dict],
    note: str,
) -> dict[str, str]:
    w = window_desc(window_names, win_by_name)
    status = "OK"
    if window_names:
        for name in window_names:
            win = win_by_name[name]
            zc = float(win["z_center"])
            if not (top_cap_z0 <= zc <= top_cap_z1):
                status = "CHECK"
                break
    else:
        status = "NO_WINDOW"
    return {
        "cavity": cavity,
        "kind": kind,
        "z_inner_bot_cm": fmt(z_inner_bot),
        "z_inner_top_cm": fmt(z_inner_top),
        "top_cap_z0_cm": fmt(top_cap_z0),
        "top_cap_z1_cm": fmt(top_cap_z1),
        "hole_radius_cm": fmt(hole_radius),
        **w,
        "status": status,
        "note": note,
    }


def build_z_audit(bounds: dict) -> list[dict[str, str]]:
    win_by_name = {w["name"]: w for w in bounds["WINDOWS"]}
    rows: list[dict[str, str]] = []

    s = bounds["SAMPLE_BOX"]
    rows.append(
        row_for(
            s["name"],
            "sample-box top aperture",
            float(s["z_in_bot"]),
            float(s["z_in_top"]),
            float(s["z_in_top"]),
            float(s["z_out_top"]),
            float(s["hole"]),
            ["SampleBox_Al_Window"],
            win_by_name,
            "Window is centered in the Cu sample-box top cap.",
        )
    )

    for can in bounds["OPEN_BOTTOM_CANS"]:
        windows = [str(can["window"])] if can.get("window") else []
        rows.append(
            row_for(
                can["name"],
                "open-bottom detector/magnetic can top aperture",
                float(can["z_in_bot"]),
                float(can["z_in_top"]),
                float(can["z_in_top"]),
                float(can["z_out_top"]),
                float(can["hole"]),
                windows,
                win_by_name,
                "Thin can-window center lies inside the removable can top-cap z interval.",
            )
        )

    shell_to_windows = {
        "Thermal_4K_Al_Shield": ["Win_4K_Al_Shield"],
        "Thermal_50K_Al_Shield": ["Win_50K_Al_Shield"],
        "Vacuum_Jacket_Al": ["Win_Be_Cryostat"],
    }
    for shell in bounds["CRYOSTAT_SHELLS"]:
        rows.append(
            row_for(
                shell["name"],
                "cryostat shell top aperture",
                float(shell["z_in_bot"]),
                float(shell["z_in_top"]),
                float(shell["z_in_top"]),
                float(shell["z_out_top"]),
                float(shell["hole"]),
                shell_to_windows.get(shell["name"], []),
                win_by_name,
                "Thin window center lies inside the shell top-cap z interval.",
            )
        )

    active = bounds["ACTIVE_SHIELD"]
    rows.append(
        row_for(
            active["name"],
            "active-shield entrance tunnel",
            float(active["z_in_bot"]),
            float(active["z_in_top"]),
            float(active["z_in_top"]),
            float(active["z_out_top"]),
            float(active["hole"]),
            [],
            win_by_name,
            "Opening is Be-window matched; the scintillator shield is not closed by a separate thin window.",
        )
    )

    outer = bounds["OUTER_MECHANICAL_SHELL"]
    rows.append(
        row_for(
            outer["name"],
            "outer mechanical shell entrance opening",
            float(outer["z_in_bot"]),
            float(outer["z_in_top"]),
            float(outer["z_in_top"]),
            float(outer["z_out_top"]),
            float(outer["hole"]),
            [],
            win_by_name,
            "Opening is Be-window matched; no separate foil is currently assigned to the outer cover.",
        )
    )

    return rows


def write_z_audit(rows: list[dict[str, str]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = OUT / "cavity_window_z_audit.csv"
    md_path = OUT / "cavity_window_z_audit.md"
    fields = list(rows[0])
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Step01 Cavity/Window Z Audit",
        "",
        "All lengths are in cm. Window status `OK` means the window center lies within the corresponding top-cap z interval.",
        "",
        "| cavity | top cap z cm | hole r cm | window | window z cm | window r/thick cm | status |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        top_span = f"{row['top_cap_z0_cm']} to {row['top_cap_z1_cm']}" if row["top_cap_z0_cm"] else ""
        win_span = row["window_z_center_cm"]
        radii = row["window_radius_cm"].split("; ") if row["window_radius_cm"] else []
        thicks = row["window_thickness_cm"].split("; ") if row["window_thickness_cm"] else []
        win_rt = "; ".join(f"{r}/{t}" for r, t in zip(radii, thicks))
        lines.append(
            f"| `{row['cavity']}` | {top_span} | {row['hole_radius_cm']} | {row['window']} | {win_span} | {win_rt} | {row['status']} |"
        )
    lines.append("")
    lines.append("Notes:")
    for row in rows:
        lines.append(f"- `{row['cavity']}`: {row['note']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {csv_path.relative_to(ROOT)}")
    print(f"[OK] wrote {md_path.relative_to(ROOT)}")


def vrml_color(material: str, name: str) -> tuple[float, float, float, float]:
    if "Window" in name or name.startswith("Win_"):
        return 0.70, 0.35, 0.64, 0.25
    if material == "Copper":
        return 0.75, 0.43, 0.18, 0.35
    if material == "Aluminium":
        return 0.70, 0.70, 0.70, 0.72
    if material == "Nb":
        return 0.30, 0.78, 0.85, 0.55
    if material == "CeBr3":
        return 0.40, 0.70, 0.32, 0.75
    if material == "Be":
        return 0.82, 0.76, 0.42, 0.15
    if material == "Ta":
        return 0.85, 0.20, 0.20, 0.40
    return 0.55, 0.55, 0.55, 0.60


def cylinder_node(name: str, radius: float, z0: float, z1: float, material: str) -> str:
    zc = 0.5 * (z0 + z1)
    height = max(z1 - z0, 1.0e-5)
    r, g, b, t = vrml_color(material, name)
    return f"""# {name}
Transform {{
  translation 0 0 {fmt(zc)}
  rotation 1 0 0 1.57079632679
  children [
    Shape {{
      appearance Appearance {{
        material Material {{ diffuseColor {r:.3f} {g:.3f} {b:.3f} transparency {t:.3f} }}
      }}
      geometry Cylinder {{ radius {fmt(radius)} height {fmt(height)} }}
    }}
  ]
}}
"""


def write_wrl(bounds: dict) -> None:
    lines = [
        "#VRML V2.0 utf8",
        'WorldInfo { title "NEW_GEO_RE Step01 geometry audit" }',
        "",
    ]
    active = bounds["ACTIVE_SHIELD"]
    outer = bounds["OUTER_MECHANICAL_SHELL"]
    lines.append(cylinder_node(active["name"], active["r_out"], active["z_out_bot"], active["z_out_top"], active["mat"]))
    lines.append(cylinder_node(outer["name"], outer["r_out"], outer["z_out_bot"], outer["z_out_top"], outer["mat"]))
    for shell in bounds["CRYOSTAT_SHELLS"]:
        lines.append(cylinder_node(shell["name"], shell["r_out"], shell["z_out_bot"], shell["z_out_top"], shell["mat"]))
    for can in bounds["OPEN_BOTTOM_CANS"]:
        lines.append(cylinder_node(can["name"], can["r_out"], can["z_in_bot"], can["z_out_top"], can["mat"]))
    s = bounds["SAMPLE_BOX"]
    lines.append(cylinder_node(s["name"], s["r_out"], s["z_out_bot"], s["z_out_top"], s["mat"]))
    for p in bounds["COLD_PLATES"]:
        lines.append(cylinder_node(p["name"], p["r"], p["zc"] - p["h"] / 2.0, p["zc"] + p["h"] / 2.0, p["mat"]))
    for i, layer in enumerate(bounds["TES_LAYERS"]):
        lines.append(cylinder_node(f"TES_L{i}_active_envelope", layer["r_max"], layer["z_center"] - layer["hz"], layer["z_center"] + layer["hz"], "Ta"))
    for window in bounds["WINDOWS"]:
        z0, z1 = z_span(float(window["z_center"]), float(window["thick"]))
        lines.append(cylinder_node(window["name"], float(window["r_max"]), z0, z1, str(window.get("material", ""))))
    col = bounds["COLLIMATOR"]
    lines.append(cylinder_node("W_Collimator_envelope", col["r_max"], col["z_center"] - col["hz"], col["z_center"] + col["hz"], "W"))

    out = OUT / "TibetTES_ADR_v4c_mkflange_step01.wrl"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] wrote {out.relative_to(ROOT)}")


def main() -> int:
    bounds = load_bounds()
    rows = build_z_audit(bounds)
    write_z_audit(rows)
    write_wrl(bounds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
