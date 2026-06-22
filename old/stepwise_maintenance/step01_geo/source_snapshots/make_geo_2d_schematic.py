#!/usr/bin/env python3
"""Generate a 2D schematic for the NEW_GEO_RE ADR v4c cm geometry."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/new_geo_re_matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Patch, Rectangle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BOUNDS = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "bounds.json"
GEO = ROOT / "outputs" / "geometry" / "XZTES_ADR_v4c_mkflange_cm" / "TibetTES_ADR_v4c_mkflange_cm.geo"
OUT = HERE / "geo.png"

FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"
POS_RE = re.compile(rf"^(?P<name>\S+)\.Position\s+(?P<x>{FLOAT})\s+(?P<y>{FLOAT})\s+(?P<z>{FLOAT})$")

COLORS = {
    "TES": "#D64B4B",
    "Substrate": "#333333",
    "Copper": "#C7813A",
    "Nb": "#5AC8D8",
    "Al": "#BBBBBB",
    "CeBr3": "#76B35B",
    "Outer": "#D8B39B",
    "Window": "#B279A2",
    "Collimator": "#202020",
    "Source": "#D62728",
}


def rect(ax, x: float, z: float, w: float, h: float, color: str, alpha: float = 0.45, zorder: int = 1) -> None:
    ax.add_patch(Rectangle((x, z), w, h, facecolor=color, edgecolor=color, lw=0.6, alpha=alpha, zorder=zorder))


def shell(ax, rec: dict, name: str, color: str, alpha: float = 0.35, label_right: bool = True) -> None:
    rin = float(rec["r_in"])
    rout = float(rec["r_out"])
    z0 = float(rec.get("z_out_bot", rec.get("z_in_bot")))
    z1 = float(rec.get("z_out_top", rec.get("z_in_top")))
    zin0 = float(rec.get("z_in_bot", z0))
    zin1 = float(rec.get("z_in_top", z1))
    hole = float(rec.get("hole", rin))
    rect(ax, -rout, z0, rout - rin, z1 - z0, color, alpha)
    rect(ax, rin, z0, rout - rin, z1 - z0, color, alpha)
    if zin0 > z0:
        rect(ax, -rout, z0, 2 * rout, zin0 - z0, color, alpha)
    if z1 > zin1:
        rect(ax, -rout, zin1, rout - hole, z1 - zin1, color, alpha)
        rect(ax, hole, zin1, rout - hole, z1 - zin1, color, alpha)
    if label_right:
        ax.text(rout + 0.4, 0.5 * (z0 + z1), name, fontsize=7, va="center")


def parse_positions() -> dict[str, tuple[float, float, float]]:
    out = {}
    for line in GEO.read_text(encoding="utf-8").splitlines():
        m = POS_RE.match(line.strip())
        if m:
            out[m.group("name")] = (float(m.group("x")), float(m.group("y")), float(m.group("z")))
    return out


def layer0_pixels(positions: dict[str, tuple[float, float, float]]) -> list[tuple[float, float]]:
    return sorted((x, y) for name, (x, y, _z) in positions.items() if name.startswith("TP_L0_"))


def main() -> int:
    bounds = json.loads(BOUNDS.read_text(encoding="utf-8"))
    positions = parse_positions()
    pixels = layer0_pixels(positions)
    fig = plt.figure(figsize=(12.5, 8.8), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.6, 1.0])
    ax = fig.add_subplot(gs[:, 0])
    ax_xy = fig.add_subplot(gs[0, 1])
    ax_col = fig.add_subplot(gs[1, 1])

    ax.set_title("NEW_GEO_RE ADR v4c cm geometry: X-Z projection")
    ax.set_xlabel("X / cm")
    ax.set_ylabel("Z / cm")

    shell(ax, bounds["ACTIVE_SHIELD"], "CeBr3 active shield", COLORS["CeBr3"], 0.28)
    shell(ax, bounds["OUTER_MECHANICAL_SHELL"], "outer Al shell", COLORS["Outer"], 0.24)
    for rec in bounds["CRYOSTAT_SHELLS"]:
        shell(ax, rec, rec["name"], COLORS["Al"], 0.28)
    for rec in bounds["OPEN_BOTTOM_CANS"]:
        shell(ax, rec, rec["name"], COLORS["Nb"], 0.42)
    shell(ax, bounds["SAMPLE_BOX"], "TES sample box", COLORS["Copper"], 0.55)

    for p in bounds["COLD_PLATES"]:
        r = float(p["r"])
        h = float(p["h"])
        zc = float(p["zc"])
        rect(ax, -r, zc - h / 2, 2 * r, h, COLORS["Copper"] if p.get("mat") == "Copper" else COLORS["Al"], 0.55, 8)
        ax.text(r + 0.35, zc, p["name"], fontsize=7, va="center")

    for sub in bounds["SUBSTRATES"]:
        r = float(sub["r_max"])
        z = float(sub["z_center"])
        hz = float(sub["hz"])
        rect(ax, -r, z - hz, 2 * r, 2 * hz, COLORS["Substrate"], 0.50, 10)
    for i, layer in enumerate(bounds["TES_LAYERS"]):
        r = float(layer["r_max"])
        z = float(layer["z_center"])
        hz = float(layer["hz"])
        rect(ax, -r, z - hz, 2 * r, 2 * hz, COLORS["TES"], 0.35, 11)
        ax.text(r + 0.25, z, f"TES L{i}", fontsize=7, color="#8E2F2E", va="center")

    for win in bounds["WINDOWS"]:
        r = float(win["r_max"])
        z = float(win["z_center"])
        h = max(float(win["thick"]), 0.035)
        rect(ax, -r, z - h / 2, 2 * r, h, COLORS["Window"], 0.60, 12)
        ax.text(r + 0.3, z, win["name"], fontsize=7, va="center")

    col = bounds["COLLIMATOR"]
    rect(ax, -float(col["r_max"]), float(col["z_center"]) - float(col["hz"]), 2 * float(col["r_max"]), 2 * float(col["hz"]), COLORS["Collimator"], 0.65, 13)
    ax.text(float(col["r_max"]) + 0.35, float(col["z_center"]), "W collimator", fontsize=7, va="center")

    meta = bounds["META"]
    src_z = float(meta["science_beam_z_cm"])
    src_r = float(meta["science_beam_radius_cm"])
    ax.plot([-src_r, src_r], [src_z, src_z], color=COLORS["Source"], lw=2.2, zorder=20)
    ax.annotate(f"511 keV source\nz={src_z:g} cm, r={src_r:g} cm", xy=(src_r, src_z), xytext=(src_r + 1.0, src_z + 1.0),
                arrowprops={"arrowstyle": "->", "lw": 0.9, "color": COLORS["Source"]}, fontsize=7, color=COLORS["Source"])

    ax.axvline(0, color="0.45", lw=0.5, ls=":")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-16, 18)
    ax.set_ylim(-22.5, 17.5)
    ax.grid(True, lw=0.35, alpha=0.22)
    ax.legend(handles=[
        Patch(facecolor=COLORS["TES"], alpha=0.4, label="Ta TES"),
        Patch(facecolor=COLORS["CeBr3"], alpha=0.3, label="CeBr3 active shield"),
        Patch(facecolor=COLORS["Copper"], alpha=0.5, label="Cu plates/sample box"),
        Patch(facecolor=COLORS["Window"], alpha=0.6, label="windows"),
    ], loc="lower left", fontsize=7)

    ax_xy.set_title("TES L0 pixel footprint")
    sub_r = float(bounds["SUBSTRATES"][0]["r_max"])
    eff_r = float(bounds["TES_LAYERS"][0]["r_max"])
    ax_xy.add_patch(Circle((0, 0), sub_r, facecolor="#E6E6E6", edgecolor="#333", lw=0.8))
    ax_xy.add_patch(Circle((0, 0), eff_r, fill=False, edgecolor=COLORS["TES"], lw=1.0, ls="--"))
    for x, y in pixels:
        rect(ax_xy, x - 0.075, y - 0.075, 0.15, 0.15, COLORS["TES"], 0.55, 3)
    ax_xy.set_xlim(-2.5, 2.5)
    ax_xy.set_ylim(-2.5, 2.5)
    ax_xy.set_aspect("equal")
    ax_xy.grid(True, lw=0.3, alpha=0.2)
    ax_xy.set_xlabel("X / cm")
    ax_xy.set_ylabel("Y / cm")

    ax_col.set_title("W collimator grid")
    rmax = float(col["r_max"])
    ax_col.add_patch(Circle((0, 0), rmax, facecolor="#F3F3F3", edgecolor="#333", lw=0.8))
    pitch = float(col["pitch"])
    web = float(col["web"])
    n = int(rmax / pitch) + 2
    for k in range(-n, n + 1):
        pos = (k + 0.5) * pitch
        if abs(pos) <= rmax:
            rect(ax_col, -rmax, pos - web / 2, 2 * rmax, web, COLORS["Collimator"], 0.55, 3)
            rect(ax_col, pos - web / 2, -rmax, web, 2 * rmax, COLORS["Collimator"], 0.55, 4)
    ax_col.set_xlim(-3.4, 3.4)
    ax_col.set_ylim(-3.4, 3.4)
    ax_col.set_aspect("equal")
    ax_col.grid(True, lw=0.3, alpha=0.2)
    ax_col.set_xlabel("X / cm")
    ax_col.set_ylabel("Y / cm")

    fig.suptitle("NEW_GEO_RE ADR v4c mK-flange mass model, cm-scaled for Cosima")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220)
    print(f"[OK] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
