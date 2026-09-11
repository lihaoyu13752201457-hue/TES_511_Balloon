#!/usr/bin/env python3
"""Build the manuscript-facing exact-position delayed-source distribution figure."""

from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
STEP = Path(__file__).resolve().parents[1]
OUT = STEP / "outputs"
PAPER_FIG = ROOT / "core_md" / "balloon511_nima_latex_drafts" / "paper_source_figure_table"
TABLE = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2" / "exactpos_weighted_rpip_table_m50000_s260613.csv"
TABLE_SUMMARY = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2" / "fix5_fullstat_v2_exactpos_m50000_s260613_delayed_source_manifest.json"
BOUNDS = (
    ROOT
    / "outputs"
    / "geometry"
    / "DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_bounds.json"
)

SAMPLE_SEED = 260616
SCATTER_MAX = 60000


def read_rows() -> list[dict]:
    rows: list[dict] = []
    with TABLE.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            w = float(row["sample_weight"])
            if w <= 0.0:
                continue
            rows.append(
                {
                    "x": float(row["x_cm"]),
                    "y": float(row["y_cm"]),
                    "z": float(row["z_cm"]),
                    "weight": w,
                    "VN": row["VN"],
                    "ZA": int(row["ZA"]),
                    "source_file": row.get("source_file") or row.get("source_sim", ""),
                }
            )
    return rows


def split_za(za: int) -> tuple[int, int]:
    return za // 1000, za % 1000


SYMBOLS = [
    None, "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg",
    "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr",
    "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf",
    "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po",
    "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U",
]


def nuclide_label(za: int) -> str:
    z, a = split_za(za)
    if 0 < z < len(SYMBOLS):
        return f"{SYMBOLS[z]}-{a}"
    return str(za)


def compact_volume_label(name: str) -> str:
    replacements = {
        "CsI_Bottom_Quadrant_": "CsI bottom ",
        "CsI_Side_Segment_": "CsI side ",
        "CsI_TopAnnulus_Segment_": "CsI top ",
        "Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port": "Al jacket side-port wall",
        "Passive_W_Bottom_Plate_detector_bay": "W bottom plate",
        "Plate_300K_Top_Service_Lid": "300 K service lid",
        "ColdPlate_Still_0p7K": "still cold plate",
        "ColdPlate_4K": "4 K cold plate",
    }
    for old, new in replacements.items():
        if name.startswith(old):
            return name.replace(old, new)
    if len(name) <= 32:
        return name
    return name[:29] + "..."


def category_for_volume(vn: str) -> str:
    lower = vn.lower()
    if "csi" in lower:
        return "CsI active shield"
    if "tes" in lower or "absorber" in lower:
        return "TES/absorber"
    if "cu" in lower or "copper" in lower or "coldfinger" in lower or "support" in lower:
        return "Cu/support"
    if "w_" in lower or "tungsten" in lower or "collimator" in lower or "liner" in lower:
        return "W/collimator"
    if "al" in lower or "vacuum_jacket" in lower or "outer" in lower:
        return "Al shells"
    if "window" in lower or "be_" in lower:
        return "window"
    return "other"


def component_bbox_xz(component: dict) -> tuple[float, float, float, float] | None:
    p = component.get("params", {})
    shape = component.get("shape", "")

    def maybe(*names: str) -> float | None:
        for name in names:
            if name in p:
                return float(p[name])
        return None

    if shape == "x_disc_stack":
        xs = [float(x) for x in p.get("x_centers_cm", [])]
        if not xs:
            return None
        half_t = float(p.get("disc_t_cm", p.get("pixel_size_cm", [0, 0, 0.0])[2])) / 2.0
        r = float(p.get("disc_r_cm", 0.0))
        zc = float(p.get("axis_z_cm", 0.0))
        return min(xs) - half_t, max(xs) + half_t, zc - r, zc + r
    if shape in {"x_disc", "x_annulus", "x_can", "x_tube"}:
        xc = maybe("x_center_cm")
        if xc is None:
            return None
        half_t = maybe("thickness_cm", "t_cm", "length_cm")
        r = maybe("r_cm", "r_out_cm", "outer_r_cm")
        zc = maybe("axis_z_cm", "z_center_cm")
        if half_t is None or r is None or zc is None:
            return None
        return xc - half_t / 2.0, xc + half_t / 2.0, zc - r, zc + r
    if shape == "x_cylinder_offaxis":
        x0 = maybe("x0_cm")
        x1 = maybe("x1_cm")
        zc = maybe("z_center_cm")
        r = maybe("r_cm")
        if x0 is None or x1 is None or zc is None or r is None:
            return None
        return min(x0, x1), max(x0, x1), zc - r, zc + r
    if shape == "z_cylinder_offaxis":
        xc = maybe("x_center_cm")
        z0 = maybe("z0_cm")
        z1 = maybe("z1_cm")
        r = maybe("r_cm")
        if xc is None or z0 is None or z1 is None or r is None:
            return None
        return xc - r, xc + r, min(z0, z1), max(z0, z1)
    if shape in {"z_cylinder", "z_annulus", "z_annulus_phi", "z_annulus_phi_segment", "z_can_open_top", "z_shell_top_annulus"}:
        r = maybe("r_cm", "r_out_cm", "outer_r_cm")
        z0 = maybe("z0_cm", "z_bot_cm", "z_out_bot", "z_in_bot")
        z1 = maybe("z1_cm", "z_top_cm", "z_out_top")
        if r is None:
            return None
        if z0 is None or z1 is None:
            zc = maybe("z_center_cm")
            h = maybe("height_cm", "thickness_cm")
            if zc is None or h is None:
                return None
            z0, z1 = zc - h / 2.0, zc + h / 2.0
        return -r, r, min(z0, z1), max(z0, z1)
    if shape == "box":
        xc = maybe("x_center_cm")
        zc = maybe("z_center_cm")
        hx = maybe("hx_cm", "x_half_cm")
        hz = maybe("hz_cm", "z_half_cm")
        if xc is None or zc is None or hx is None or hz is None:
            return None
        return xc - hx, xc + hx, zc - hz, zc + hz
    return None


def draw_geometry(ax) -> None:
    from matplotlib.patches import Rectangle

    bounds = json.loads(BOUNDS.read_text(encoding="utf-8"))
    category_style = {
        "detector": ("#cf2f2f", 0.34),
        "substrate": ("#cf2f2f", 0.18),
        "thermal_link": ("#b87333", 0.18),
        "passive_shield": ("#545454", 0.16),
        "collimator": ("#222222", 0.18),
        "active_shield_side": ("#5aa06a", 0.12),
        "active_shield_bottom": ("#5aa06a", 0.12),
        "active_shield_top": ("#5aa06a", 0.12),
        "cryostat_shell": ("#6688aa", 0.09),
        "vacuum_jacket": ("#6688aa", 0.09),
        "outer_shell": ("#999999", 0.08),
        "window": ("#4fb6c6", 0.22),
    }
    seen: set[str] = set()
    for comp in bounds.get("COMPONENTS", []):
        bbox = component_bbox_xz(comp)
        if bbox is None:
            continue
        x0, x1, z0, z1 = bbox
        if x1 <= x0 or z1 <= z0:
            continue
        cat = comp.get("category", "")
        color, alpha = category_style.get(cat, ("#aaaaaa", 0.045))
        label = cat if cat in category_style and cat not in seen else None
        if label:
            seen.add(cat)
        ax.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, facecolor=color, edgecolor=color, alpha=alpha, lw=0.3, label=label))


def weighted_sample(rows: list[dict], max_rows: int) -> list[dict]:
    if len(rows) <= max_rows:
        return rows
    rng = random.Random(SAMPLE_SEED)
    weights = [r["weight"] for r in rows]
    return rng.choices(rows, weights=weights, k=max_rows)


def write_summary(rows: list[dict], sampled: list[dict], out: Path) -> None:
    by_volume: defaultdict[str, float] = defaultdict(float)
    by_category: defaultdict[str, float] = defaultdict(float)
    by_nuclide: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        by_volume[row["VN"]] += row["weight"]
        by_category[category_for_volume(row["VN"])] += row["weight"]
        by_nuclide[nuclide_label(row["ZA"])] += row["weight"]
    table_summary = json.loads(TABLE_SUMMARY.read_text(encoding="utf-8"))
    payload = {
        "status": "PASS_EXACTPOS_RPIP_ACTIVITY_DISTRIBUTION_FIGURE",
        "source_table": str(TABLE.relative_to(ROOT)),
        "source_table_summary": str(TABLE_SUMMARY.relative_to(ROOT)),
        "rows": len(rows),
        "sampled_points_for_scatter": len(sampled),
        "sample_seed": SAMPLE_SEED,
        "total_activity_Bq_from_weights": sum(r["weight"] for r in rows),
        "authority_summary": table_summary,
        "top_activity_volumes": sorted(by_volume.items(), key=lambda kv: kv[1], reverse=True)[:20],
        "top_activity_categories": sorted(by_category.items(), key=lambda kv: kv[1], reverse=True),
        "top_activity_nuclides": sorted(by_nuclide.items(), key=lambda kv: kv[1], reverse=True)[:20],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_plot(rows: list[dict], sampled: list[dict], out_png: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.gridspec import GridSpec
    from matplotlib.patches import Circle

    by_volume: defaultdict[str, float] = defaultdict(float)
    by_nuclide: defaultdict[str, float] = defaultdict(float)
    for row in rows:
        by_volume[row["VN"]] += row["weight"]
        by_nuclide[nuclide_label(row["ZA"])] += row["weight"]

    fig = plt.figure(figsize=(15.6, 9.2), constrained_layout=True)
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.42, 1.0, 1.0])
    ax_xz = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_vol = fig.add_subplot(gs[0, 2])
    ax_nuc = fig.add_subplot(gs[1, 1:])

    draw_geometry(ax_xz)
    xs = [r["x"] for r in rows]
    zs = [r["z"] for r in rows]
    ws = [r["weight"] for r in rows]
    hb = ax_xz.hexbin(xs, zs, C=ws, reduce_C_function=sum, gridsize=90, mincnt=1, cmap="magma", norm=LogNorm())
    fig.colorbar(hb, ax=ax_xz, label="day-15 activity weight / Bq")
    ax_xz.set_xlabel("x / cm")
    ax_xz.set_ylabel("z / cm")
    ax_xz.set_xlim(-30, 38)
    ax_xz.set_ylim(-30, 40)
    ax_xz.grid(alpha=0.18)
    ax_xz.set_title("Activity-weighted X-Z production map")

    sx = [r["x"] for r in sampled]
    sy = [r["y"] for r in sampled]
    colors = [r["weight"] for r in sampled]
    ax_xy.scatter(sx, sy, c=colors, s=2.2, cmap="magma", norm=LogNorm(), alpha=0.35, linewidths=0)
    for r, c, label in [(1.898, "#59c5d8", "Be aperture"), (18.6, "#5aa06a", "shield envelope")]:
        ax_xy.add_patch(Circle((0, 0), r, fill=False, edgecolor=c, lw=1.0, alpha=0.85, label=label))
    ax_xy.set_xlim(-20, 20)
    ax_xy.set_ylim(-20, 20)
    ax_xy.set_aspect("equal", adjustable="box")
    ax_xy.grid(alpha=0.18)
    ax_xy.set_xlabel("x / cm")
    ax_xy.set_ylabel("y / cm")
    ax_xy.set_title(f"Activity-weighted X-Y footprint (sample n={len(sampled)})")
    ax_xy.legend(loc="upper right", fontsize=7, frameon=False)

    top_v = sorted(by_volume.items(), key=lambda kv: kv[1], reverse=True)[:12]
    ax_vol.barh([compact_volume_label(k) for k, _ in reversed(top_v)], [v for _, v in reversed(top_v)], color="#666666")
    ax_vol.set_xlabel("activity weight / Bq")
    ax_vol.set_title("Top production volumes")
    ax_vol.tick_params(axis="y", labelsize=8)

    top_n = sorted(by_nuclide.items(), key=lambda kv: kv[1], reverse=True)[:14]
    ax_nuc.barh([k for k, _ in reversed(top_n)], [v for _, v in reversed(top_n)], color="#4b6f9f")
    ax_nuc.set_xlabel("activity weight / Bq")
    ax_nuc.set_title("Top delayed-source nuclides")

    fig.suptitle("Exact-position delayed-source distribution", fontsize=14)
    fig.savefig(out_png, dpi=180)
    plt.close(fig)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PAPER_FIG.mkdir(parents=True, exist_ok=True)
    rows = read_rows()
    sampled = weighted_sample(rows, SCATTER_MAX)
    out_png = OUT / "exactpos_rpip_activity_distribution.png"
    out_summary = OUT / "exactpos_rpip_activity_distribution_summary.json"
    paper_png = PAPER_FIG / "fig_delayed_exactpos_rpip_distribution.png"
    make_plot(rows, sampled, out_png)
    make_plot(rows, sampled, paper_png)
    write_summary(rows, sampled, out_summary)
    print(f"[OK] rows={len(rows)} total_activity={sum(r['weight'] for r in rows):.12g} Bq")
    print(f"[OK] wrote {out_png}")
    print(f"[OK] wrote {out_summary}")
    print(f"[OK] wrote {paper_png}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
