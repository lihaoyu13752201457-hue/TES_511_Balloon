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
    "CsI": "#76B35B",
    "Outer": "#D8B39B",
    "Window": "#B279A2",
    "Collimator": "#202020",
    "Source": "#D62728",
    "Cryoperm": "#6066AA",
    "ADR": "#D8842D",
    "Steel": "#68707A",
    "Salt": "#59A8A0",
    "PassiveW": "#756A61",
    "Kapton": "#B36B2C",
    "G10": "#6B8E5A",
}

MATERIAL_COLORS = {
    "Aluminium": COLORS["Al"],
    "Copper": COLORS["Copper"],
    "Cryoperm": COLORS["Cryoperm"],
    "G10": COLORS["G10"],
    "Kapton": COLORS["Kapton"],
    "LowCarbonSteel": COLORS["Steel"],
    "Nb": COLORS["Nb"],
    "SaltProxy": COLORS["Salt"],
    "StainlessSteel": COLORS["Steel"],
    "W": COLORS["PassiveW"],
}

KEY_PROXY_LABELS = {
    "Cryoperm_Inner_Mag_Shield": "Cryoperm magnetic shield",
    "ADR_Magnet_Coil_Cu": "ADR magnet coil (Cu eq.)",
    "ADR_Magnet_Yoke_Fe": "ADR magnet yoke (Fe)",
    "ADR_SaltPill_Proxy": "ADR salt pill proxy",
    "ADR_SaltPill_Cu_Can": "salt-pill Cu can",
    "Thermal_Bus_Cu": "Cu thermal bus",
    "ADR_HeatSwitch_Stainless_Link": "SS heat-switch link",
    "PulseTube_ColdHead_Interface_Cu": "pulse-tube cold-head Cu",
    "Passive_Bottom_W_Shield": "bottom W shield",
    "Passive_Top_W_Aperture_Annulus": "top W aperture stop",
}

KEY_PROXY_TEXT_X = {
    "Cryoperm_Inner_Mag_Shield": -11.8,
    "ADR_Magnet_Coil_Cu": -11.6,
    "ADR_Magnet_Yoke_Fe": 10.9,
    "ADR_SaltPill_Proxy": -7.4,
    "ADR_SaltPill_Cu_Can": 3.4,
    "Thermal_Bus_Cu": 6.0,
    "ADR_HeatSwitch_Stainless_Link": -8.0,
    "PulseTube_ColdHead_Interface_Cu": 10.7,
    "Passive_Bottom_W_Shield": 10.8,
    "Passive_Top_W_Aperture_Annulus": 10.8,
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


def proxy_color(rec: dict) -> str:
    category = rec.get("category", "")
    if category == "adr_passive":
        return MATERIAL_COLORS.get(rec.get("mat", ""), COLORS["ADR"])
    if category == "passive_shield":
        return MATERIAL_COLORS.get(rec.get("mat", ""), COLORS["PassiveW"])
    if category == "magnetic_shield":
        return COLORS["Cryoperm"]
    if category == "shield_packaging":
        return MATERIAL_COLORS.get(rec.get("mat", ""), COLORS["Al"])
    return MATERIAL_COLORS.get(rec.get("mat", ""), "#999999")


def annular_proxy(ax, rec: dict, color: str, alpha: float = 0.48, zorder: int = 4) -> tuple[float, float]:
    z0 = float(rec.get("z0", rec.get("z_out_bot", rec.get("z_in_bot"))))
    z1 = float(rec.get("z1", rec.get("z_out_top", rec.get("z_in_top"))))
    if "r" in rec:
        r = float(rec["r"])
        rect(ax, -r, z0, 2 * r, z1 - z0, color, alpha, zorder)
        return 0.0, 0.5 * (z0 + z1)
    rin = float(rec.get("r_in", 0.0))
    rout = float(rec["r_out"])
    if rin <= 0.0:
        rect(ax, -rout, z0, 2 * rout, z1 - z0, color, alpha, zorder)
    else:
        rect(ax, -rout, z0, rout - rin, z1 - z0, color, alpha, zorder)
        rect(ax, rin, z0, rout - rin, z1 - z0, color, alpha, zorder)
    return rout, 0.5 * (z0 + z1)


def box_proxy(ax, rec: dict, color: str, alpha: float = 0.50, zorder: int = 5) -> tuple[float, float] | None:
    y = float(rec.get("y", 0.0))
    hy = float(rec.get("hy", 0.0))
    if abs(y) > hy:
        return None
    x = float(rec.get("x", 0.0))
    z = float(rec.get("z", 0.0))
    hx = float(rec["hx"])
    hz = float(rec["hz"])
    rect(ax, x - hx, z - hz, 2 * hx, 2 * hz, color, alpha, zorder)
    return x, z


def label_proxy(ax, rec: dict, anchor: tuple[float, float], color: str) -> None:
    label = KEY_PROXY_LABELS.get(rec.get("name", ""))
    if not label:
        return
    ax.annotate(
        label,
        xy=anchor,
        xytext=(KEY_PROXY_TEXT_X.get(rec["name"], anchor[0] + 0.6), anchor[1]),
        arrowprops={"arrowstyle": "-", "lw": 0.55, "color": color, "alpha": 0.75},
        fontsize=6.5,
        color="#2F2F2F",
        va="center",
        zorder=30,
    )


def draw_proxy_records(ax, records: list[dict]) -> None:
    for rec in records:
        name = rec.get("name", "")
        color = proxy_color(rec)
        if name == "Cryoperm_Inner_Mag_Shield":
            shell(ax, rec, "", color, 0.32, label_right=False)
            z0 = float(rec["z_out_bot"])
            z1 = float(rec["z_out_top"])
            anchor = (float(rec["r_out"]), 0.5 * (z0 + z1))
        elif "r_out" in rec or "r" in rec:
            anchor = annular_proxy(ax, rec, color, 0.45, 4)
        elif all(k in rec for k in ("hx", "hy", "hz", "x", "y", "z")):
            maybe_anchor = box_proxy(ax, rec, color, 0.45, 5)
            if maybe_anchor is None:
                continue
            anchor = maybe_anchor
        else:
            continue
        label_proxy(ax, rec, anchor, color)


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

    active_mat = bounds["ACTIVE_SHIELD"].get("mat", "CsI")
    active_color = COLORS.get(active_mat, COLORS["CsI"])

    ax.set_title("NEW_GEO_RE DEMO2 ADR/passive mass model: X-Z projection")
    ax.set_xlabel("X / cm")
    ax.set_ylabel("Z / cm")

    shell(ax, bounds["ACTIVE_SHIELD"], f"{active_mat} active shield", active_color, 0.28, label_right=False)
    shell(ax, bounds["OUTER_MECHANICAL_SHELL"], "outer Al shell", COLORS["Outer"], 0.24, label_right=False)
    for rec in bounds["CRYOSTAT_SHELLS"]:
        shell(ax, rec, rec["name"], COLORS["Al"], 0.28)
    for rec in bounds["OPEN_BOTTOM_CANS"]:
        shell(ax, rec, rec["name"], COLORS["Nb"], 0.42, label_right=False)

    proxy_records = []
    seen_proxy_names = set()
    for rec in bounds.get("MIDMASS_PROXIES", []) + bounds.get("SHIELD_PACKAGING_PROXIES", []):
        name = rec.get("name", "")
        if name in seen_proxy_names:
            continue
        seen_proxy_names.add(name)
        proxy_records.append(rec)
    draw_proxy_records(ax, proxy_records)

    shell(ax, bounds["SAMPLE_BOX"], "TES sample box", COLORS["Copper"], 0.55, label_right=False)
    ax.text(3.0, 8.25, "Cu TES sample box", fontsize=7, va="center", color="#5E3F24")
    ax.text(4.95, 9.25, "Nb detector can", fontsize=7, va="center", color="#2C6570")

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
    col_rmax = float(col["r_max"])
    col_rin = float(col.get("r_inner", 0.0))
    col_z = float(col["z_center"])
    col_hz = float(col["hz"])
    if col_rin > 0.0:
        rect(ax, -col_rmax, col_z - col_hz, col_rmax - col_rin, 2 * col_hz, COLORS["Collimator"], 0.65, 13)
        rect(ax, col_rin, col_z - col_hz, col_rmax - col_rin, 2 * col_hz, COLORS["Collimator"], 0.65, 13)
    else:
        rect(ax, -col_rmax, col_z - col_hz, 2 * col_rmax, 2 * col_hz, COLORS["Collimator"], 0.65, 13)
    ax.text(col_rmax + 0.35, col_z, "W aperture stop", fontsize=7, va="center")

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
        Patch(facecolor=active_color, alpha=0.3, label=f"{active_mat} active shield"),
        Patch(facecolor=COLORS["Outer"], alpha=0.35, label="outer Al cover"),
        Patch(facecolor=COLORS["Copper"], alpha=0.5, label="Cu plates/sample box"),
        Patch(facecolor=COLORS["Nb"], alpha=0.45, label="Nb detector can"),
        Patch(facecolor=COLORS["Cryoperm"], alpha=0.35, label="Cryoperm magnetic shield"),
        Patch(facecolor=COLORS["Steel"], alpha=0.45, label="ADR Fe/SS proxies"),
        Patch(facecolor=COLORS["Salt"], alpha=0.45, label="ADR salt pill proxy"),
        Patch(facecolor=COLORS["PassiveW"], alpha=0.45, label="W passive shield"),
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

    ax_col.set_title("W entrance aperture")
    rmax = float(col["r_max"])
    ax_col.add_patch(Circle((0, 0), rmax, facecolor="#F3F3F3", edgecolor="#333", lw=0.8))
    if all(k in col for k in ("pitch", "web")):
        pitch = float(col["pitch"])
        web = float(col["web"])
        n = int(rmax / pitch) + 2
        for k in range(-n, n + 1):
            pos = (k + 0.5) * pitch
            if abs(pos) <= rmax:
                rect(ax_col, -rmax, pos - web / 2, 2 * rmax, web, COLORS["Collimator"], 0.55, 3)
                rect(ax_col, pos - web / 2, -rmax, web, 2 * rmax, COLORS["Collimator"], 0.55, 4)
    else:
        rin = float(col.get("r_inner", 0.0))
        ax_col.patches[-1].set_facecolor(COLORS["Collimator"])
        ax_col.patches[-1].set_alpha(0.55)
        if rin > 0.0:
            ax_col.add_patch(Circle((0, 0), rin, facecolor="white", edgecolor="#333", lw=0.9, zorder=5))
            ax_col.text(0.0, 0.0, f"open\nr={rin:g} cm", fontsize=7, ha="center", va="center", zorder=6)
    ax_col.set_xlim(-3.4, 3.4)
    ax_col.set_ylim(-3.4, 3.4)
    ax_col.set_aspect("equal")
    ax_col.grid(True, lw=0.3, alpha=0.2)
    ax_col.set_xlabel("X / cm")
    ax_col.set_ylabel("Y / cm")

    fig.suptitle("NEW_GEO_RE DEMO2 ADR/CsI geometry, cm-scaled for Cosima")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220)
    print(f"[OK] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
