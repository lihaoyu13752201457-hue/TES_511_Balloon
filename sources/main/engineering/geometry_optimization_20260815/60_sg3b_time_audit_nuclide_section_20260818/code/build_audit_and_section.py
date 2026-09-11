#!/usr/bin/env python3
"""Receipt-only SG3B exposure audit plus an annotated activation-origin section.

No SIM payload is opened.  The section reuses the compact selected-route product
and the exact-y'=0 geometry renderer already retained by package 59.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/sg3b_time_audit_section_mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
ROOT = PACKAGE.parents[2]
CONFIG = PACKAGE / "analysis_inputs.json"
OUT = PACKAGE / "outputs"
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
ELEMENTS = (
    "n", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P",
    "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh",
    "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
    "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re",
    "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
    "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db",
    "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def nuclide_label(za: int) -> str:
    z, a = divmod(int(za), 1000)
    return f"{ELEMENTS[z] if 0 <= z < len(ELEMENTS) else f'Z{z}'}-{a}"


def source_flux_contract(source: Path) -> tuple[float, float]:
    # Only the small source-card header is read.  This is not a SIM scan.
    text = source.read_text(encoding="utf-8")
    flux_match = re.search(r"total_flux_cm2_s=([0-9.eE+-]+)", text)
    radius_match = re.search(r"farfield_radius_cm=([0-9.eE+-]+)", text)
    if not flux_match or not radius_match:
        raise RuntimeError(f"source flux/radius contract missing: {source}")
    return float(flux_match.group(1)), float(radius_match.group(1))


def prompt_receipt_audit(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_campaign: dict[str, dict[str, dict[str, Any]]] = {}
    receipt_paths: list[str] = []
    for label, root_text in config["prompt_campaigns"].items():
        receipt_dir = Path(root_text) / "receipts"
        grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {"jobs": 0, "events": 0, "TT_s": 0.0})
        paths = sorted(receipt_dir.glob("sg3b_instant_*_shard*.json"))
        if len(paths) != 11:
            raise RuntimeError(f"{label}: expected 11 instant receipts, found {len(paths)}")
        for path in paths:
            receipt = load_json(path)
            if receipt["status"] != "PASS" or receipt["mode"] != "instant":
                raise RuntimeError(f"non-PASS or non-instant receipt: {path}")
            tt = float(receipt["isotope_dat"]["TT_s"])
            if not math.isclose(tt, float(receipt["log"]["observation_time_s"]), rel_tol=0.0, abs_tol=1e-12):
                raise RuntimeError(f"DAT/log TT mismatch: {path}")
            family = receipt["family"]
            cell = grouped[family]
            cell["jobs"] += 1
            cell["events"] += int(receipt["events"])
            cell["TT_s"] += tt
            cell.setdefault("source", Path(receipt["source_path"]))
            receipt_paths.append(str(path))
        if set(grouped) != set(FAMILIES):
            raise RuntimeError(f"{label}: family closure differs")
        by_campaign[label] = grouped

    rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        base = by_campaign["base_1x"][family]
        extra = by_campaign["extra_2x"][family]
        flux, radius = source_flux_contract(base["source"])
        rate = flux * math.pi * radius * radius
        for label, cell in (("base_1x", base), ("extra_2x", extra)):
            rows.append({
                "campaign": label,
                "family": family,
                "jobs": cell["jobs"],
                "accepted_events": cell["events"],
                "receipt_sum_TT_s": cell["TT_s"],
                "total_flux_cm-2_s-1": flux,
                "farfield_radius_cm": radius,
                "analytic_generation_rate_s-1": rate,
                "analytic_expected_TT_s": cell["events"] / rate,
                "TT_minus_analytic_s": cell["TT_s"] - cell["events"] / rate,
                "event_multiplier_vs_base": cell["events"] / base["events"],
                "TT_multiplier_vs_base": cell["TT_s"] / base["TT_s"],
            })
        events = base["events"] + extra["events"]
        tt = base["TT_s"] + extra["TT_s"]
        rows.append({
            "campaign": "combined_3x",
            "family": family,
            "jobs": base["jobs"] + extra["jobs"],
            "accepted_events": events,
            "receipt_sum_TT_s": tt,
            "total_flux_cm-2_s-1": flux,
            "farfield_radius_cm": radius,
            "analytic_generation_rate_s-1": rate,
            "analytic_expected_TT_s": events / rate,
            "TT_minus_analytic_s": tt - events / rate,
            "event_multiplier_vs_base": events / base["events"],
            "TT_multiplier_vs_base": tt / base["TT_s"],
        })

    combined = [row for row in rows if row["campaign"] == "combined_3x"]
    if sum(row["accepted_events"] for row in combined) != 3_842_079:
        raise RuntimeError("combined prompt instant event closure differs")
    gamma = next(row for row in combined if row["family"] == "gamma")
    if gamma["accepted_events"] != 3_207_738 or not math.isclose(gamma["receipt_sum_TT_s"], 59.10547, abs_tol=1e-9):
        raise RuntimeError("combined gamma receipt closure differs")
    return rows, {
        "receipt_paths": receipt_paths,
        "combined_instant_jobs": sum(row["jobs"] for row in combined),
        "combined_instant_events": sum(row["accepted_events"] for row in combined),
        "gamma_combined_events": gamma["accepted_events"],
        "gamma_combined_TT_s": gamma["receipt_sum_TT_s"],
        "gamma_analytic_generation_rate_s-1": gamma["analytic_generation_rate_s-1"],
        "gamma_analytic_10m_TT_s": 10_000_000 / gamma["analytic_generation_rate_s-1"],
        "gamma_events_in_1000s": 1000 * gamma["analytic_generation_rate_s-1"],
    }


def m05_gamma_audit(config: dict[str, Any], sg3b_gamma: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = read_csv(resolve(config["m05_prompt_manifest"]))
    grouped: dict[str, dict[str, float]] = defaultdict(lambda: {"jobs": 0, "events": 0, "TT_s": 0.0})
    for row in manifest:
        if row["family"] == "gamma" and row["mode"] == "instant":
            cell = grouped[row["geometry"]]
            cell["jobs"] += 1
            cell["events"] += int(row["events"])
            cell["TT_s"] += float(row["TT_s"])
    rows: list[dict[str, Any]] = []
    for geometry, cell in sorted(grouped.items()):
        rate = cell["events"] / cell["TT_s"]
        rows.append({
            "authority": "M05 corrected reanalysis accepted prompt manifest",
            "geometry": geometry,
            "jobs": int(cell["jobs"]),
            "accepted_or_target_events": int(cell["events"]),
            "TT_s": cell["TT_s"],
            "event_rate_s-1": rate,
            "10m_equivalent_TT_s": 10_000_000 / rate,
            "authority_state": "accepted",
        })
    prefix = load_json(resolve(config["m05_gamma_prefix_ledger"]))
    for campaign in prefix["campaigns"]:
        rows.append({
            "authority": "batch0003 committed prefix shard0076 ledger",
            "geometry": campaign["geometry"],
            "jobs": len(campaign["jobs"]),
            "accepted_or_target_events": int(campaign["cumulative_events"]),
            "TT_s": float(campaign["TT_s_new_sum"]),
            "event_rate_s-1": int(campaign["cumulative_events"]) / float(campaign["TT_s_new_sum"]),
            "10m_equivalent_TT_s": 10_000_000 / (int(campaign["cumulative_events"]) / float(campaign["TT_s_new_sum"])),
            "authority_state": "accepted partial prefix",
        })
    target = load_json(resolve(config["m05_gamma_target_normalization"]))
    rows.append({
        "authority": "batch0003 normalization target",
        "geometry": target["geometry"],
        "jobs": target["jobs"],
        "accepted_or_target_events": target["final_cumulative_events"],
        "TT_s": "",
        "event_rate_s-1": "",
        "10m_equivalent_TT_s": sg3b_gamma["gamma_analytic_10m_TT_s"],
        "authority_state": "planned ceiling, not a completed 10m receipt set",
    })
    return rows


def delayed_audit(config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest = load_json(Path(config["activation_manifest"]))
    if manifest["status"] != "PASS__SG3B_M05_DAY15_ACTIVATION_AND_DELAYED_SOURCES_READY":
        raise RuntimeError("activation manifest status differs")
    receipts = []
    for path in sorted((Path(config["delayed_campaign"]) / "run/receipts").glob("*.json")):
        row = load_json(path)
        if row["status"] != "PASS":
            raise RuntimeError(f"non-PASS delayed receipt: {path}")
        receipts.append(row)
    events_by_family: dict[str, int] = defaultdict(int)
    jobs_by_family: dict[str, int] = defaultdict(int)
    for row in receipts:
        events_by_family[row["family"]] += int(row["events"])
        jobs_by_family[row["family"]] += 1
    activities = {row["family"]: float(row["transported_ground_activity_Bq"]) for row in manifest["activation_cells"]}
    rows = []
    for family in FAMILIES:
        if events_by_family[family] != 1_000_000:
            raise RuntimeError(f"delayed trigger closure differs for {family}")
        activity = activities[family]
        rows.append({
            "family": family,
            "jobs": jobs_by_family[family],
            "transport_triggers": events_by_family[family],
            "day15_transported_ground_activity_Bq": activity,
            "per_trigger_weight_cps": activity / events_by_family[family],
            "constant_day15_activity_equivalent_time_s": events_by_family[family] / activity if activity else "inf",
            "constant_day15_activity_equivalent_time_days": events_by_family[family] / activity / 86400 if activity else "inf",
            "interpretation": "constant day-15 activity-equivalent sampling time; not elapsed mission time",
        })
    if len(receipts) != 33 or sum(events_by_family.values()) != 8_000_000:
        raise RuntimeError("delayed receipt total differs")
    return rows, {"jobs": len(receipts), "triggers": sum(events_by_family.values())}


def short_volume(volume: str) -> str:
    aliases = {
        "Cu_SubstrateSupport_OpenRing_L2_ZP_panel": "L2 Cu open-ring +z' panel",
        "ColdPlate_MXC_50mK_SD_anchor": "MXC 50 mK Cu cold plate",
        "SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm": "SG3B L0 Cu heat-sink ring",
        "SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm": "SG3B Bi upper half-cylinder",
        "Cu_SubstrateSupport_OpenRing_L4_YP_panel": "L4 Cu open-ring +y' panel",
        "SE3_Al_Shield_Inner_Cylinder_2mm": "inner Al shield cylinder",
        "Passive_W_Bottom_Plate_detector_bay": "passive W bottom plate",
        "GeoOpt_S2B_CryoShell_BPE5_SideShell_20mm": "BPE5 cryoshell side",
        "SG3A_Al_50mK_StillLike_Can_bottom_cap_2mm": "50 mK Al can bottom cap",
    }
    if volume in aliases:
        return aliases[volume]
    return textwrap.shorten(volume.replace("_", " "), width=38, placeholder="…")


def origin_groups(lineage_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    delayed = [row for row in lineage_rows if row["stream"] == "delayed"]
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in delayed:
        groups[(row["source_nuclide"], row["source_volume"], row["source_material"])].append(row)
    total_counts = math.fsum(float(row["mission20_live_counts"]) for row in delayed)
    output = []
    for (nuclide, volume, material), rows in groups.items():
        weights = np.asarray([float(row["mission20_live_counts"]) for row in rows])
        xp = np.asarray([float(row["source_xprime_cm"]) for row in rows])
        yp = np.asarray([float(row["source_yprime_cm"]) for row in rows])
        zp = np.asarray([float(row["source_zprime_cm"]) for row in rows])
        counts = float(weights.sum())
        output.append({
            "group_id": "",
            "nuclide": nuclide,
            "source_material": material,
            "source_volume": volume,
            "source_volume_short": short_volume(volume),
            "selected_events": len(rows),
            "day15_noacc_cps": math.fsum(float(row["day15_noacc_cps"]) for row in rows),
            "mission20_live_counts": counts,
            "mission20_count_share": counts / total_counts,
            "xprime_weighted_centroid_cm": float(np.average(xp, weights=weights)),
            "yprime_weighted_centroid_cm": float(np.average(yp, weights=weights)),
            "zprime_weighted_centroid_cm": float(np.average(zp, weights=weights)),
            "xprime_min_cm": float(xp.min()), "xprime_max_cm": float(xp.max()),
            "yprime_min_cm": float(yp.min()), "yprime_max_cm": float(yp.max()),
            "zprime_min_cm": float(zp.min()), "zprime_max_cm": float(zp.max()),
        })
    output.sort(key=lambda row: (-row["mission20_live_counts"], row["nuclide"], row["source_volume"]))
    for index, row in enumerate(output, 1):
        row["group_id"] = f"P{index:02d}"
    if len(delayed) != 394 or len(output) != 35 or len({row["nuclide"] for row in output}) != 16:
        raise RuntimeError("selected-origin count closure differs")
    return output, delayed


def save_figure(fig: plt.Figure, stem: str) -> list[str]:
    paths = []
    for suffix in ("png", "svg", "pdf"):
        path = OUT / f"{stem}.{suffix}"
        fig.savefig(path, dpi=260 if suffix == "png" else None, bbox_inches="tight", pad_inches=0.08)
        paths.append(str(path))
    plt.close(fig)
    return paths


def draw_group_points(ax: plt.Axes, delayed: list[dict[str, str]], groups: list[dict[str, Any]], colors: dict[str, Any]) -> None:
    max_counts = max(float(row["mission20_live_counts"]) for row in delayed)
    for row in delayed:
        ax.scatter(
            float(row["source_xprime_cm"]), float(row["source_zprime_cm"]),
            s=8 + 28 * math.sqrt(float(row["mission20_live_counts"]) / max_counts),
            color=colors[row["source_nuclide"]], alpha=0.52, edgecolor="white", linewidth=0.25, zorder=14,
        )
    for row in groups:
        x = row["xprime_weighted_centroid_cm"]
        z = row["zprime_weighted_centroid_cm"]
        ax.scatter(x, z, s=35, color=colors[row["nuclide"]], edgecolor="#17212B", linewidth=0.55, zorder=16)
        ax.annotate(
            row["group_id"], (x, z), xytext=(3, 3), textcoords="offset points",
            fontsize=5.7, weight="bold", color="#17212B", zorder=18,
            bbox={"boxstyle": "round,pad=0.10", "fc": "white", "ec": colors[row["nuclide"]], "alpha": 0.88, "lw": 0.45},
        )


def add_table_panel(ax: plt.Axes, groups: list[dict[str, Any]], title: str) -> None:
    ax.axis("off")
    ax.text(0.0, 1.0, title, va="top", ha="left", fontsize=10, weight="bold")
    split = math.ceil(len(groups) / 2)
    columns = (groups[:split], groups[split:])
    for column, rows in enumerate(columns):
        x = 0.0 if column == 0 else 0.51
        y = 0.96
        for row in rows:
            line1 = f"{row['group_id']}  {row['nuclide']}  {row['source_material']}  N={row['selected_events']}"
            line2 = f"{row['source_volume_short']}  |  20 d={row['mission20_live_counts']:.1f}"
            ax.text(x, y, line1, va="top", ha="left", fontsize=6.0, weight="bold", color="#182431")
            ax.text(x + 0.012, y - 0.020, line2, va="top", ha="left", fontsize=5.35, color="#465463")
            y -= 0.051


def section_figures(config: dict[str, Any], groups: list[dict[str, Any]], delayed_rows: list[dict[str, str]]) -> list[str]:
    package59 = resolve(config["package59"])
    inputs59 = load_json(package59 / "analysis_inputs.json")
    coupling = load_module("sg3b_package59_plot_reuse", package59 / "code/analyze_and_plot_coupling.py")
    visual = load_module(
        "sg3b_section_adapter_reuse",
        Path(inputs59["section_tool"]) / "se3_section_adapter.py",
    )
    visual.configure_matplotlib()
    mesh = visual.load_mesh(Path(inputs59["section_mesh"]))
    route_data = load_json(package59 / "outputs/01_selected_routes/sg3b_selected_w2_routes.json")
    delayed_routes = [event for event in route_data["events"] if event["stream"] == "delayed"]
    prompt = next(event for event in route_data["events"] if event["stream"] == "prompt")
    nuclides = sorted({row["nuclide"] for row in groups})
    palette = plt.get_cmap("tab20")(np.linspace(0.02, 0.96, len(nuclides)))
    colors = dict(zip(nuclides, palette, strict=True))
    paths: list[str] = []

    for stem, limits, title in (
        (
            "sg3b_nuclide_origins_detailed_side_section",
            ((-9.0, 10.5), (-12.0, 2.5)),
            "SG3B detailed side section: activation nuclides feeding final W2",
        ),
        (
            "sg3b_nuclide_origins_global_side_section",
            ((-24.0, 24.0), (-22.0, 34.0)),
            "SG3B global side section: all audited activation-origin groups feeding final W2",
        ),
    ):
        fig = plt.figure(figsize=(22, 12.5 if "detailed" in stem else 14.5))
        grid = fig.add_gridspec(1, 2, width_ratios=[1.55, 1.0], wspace=0.04)
        ax = fig.add_subplot(grid[0, 0])
        table_ax = fig.add_subplot(grid[0, 1])
        visual.draw_exact_if_section(ax, mesh, include_holes=True, limits=limits)
        coupling.draw_sg3b_overlays_xz(ax)
        lines = [segment for event in delayed_routes for segment, _ in coupling.segments(event)]
        ax.add_collection(LineCollection(lines, colors="#71808D", linewidths=0.22, alpha=0.025, zorder=9, rasterized=True))
        coupling.draw_routes_xz(ax, [], prompt)
        visible_groups = [
            row for row in groups
            if limits[0][0] <= row["xprime_weighted_centroid_cm"] <= limits[0][1]
            and limits[1][0] <= row["zprime_weighted_centroid_cm"] <= limits[1][1]
        ]
        visible_rows = [
            row for row in delayed_rows
            if limits[0][0] <= float(row["source_xprime_cm"]) <= limits[0][1]
            and limits[1][0] <= float(row["source_zprime_cm"]) <= limits[1][1]
        ]
        draw_group_points(ax, visible_rows, visible_groups, colors)
        visual.axes_style(ax, "InstrumentFrame x' [cm]", "InstrumentFrame z' [cm]")
        ax.set_xlim(*limits[0]); ax.set_ylim(*limits[1]); ax.set_title(title, fontsize=14, weight="bold")
        ax.text(
            0.01, 0.99,
            "Colored dots: exact delayed source-nucleus positions for the 394 selected final-W2 events.\n"
            "Pxx: nuclide+mother-volume group at its 20-day-count-weighted centroid. Gray: delayed routes; red: sole prompt route.",
            transform=ax.transAxes, va="top", ha="left", fontsize=7.1,
            bbox={"boxstyle": "round,pad=0.3", "fc": "white", "ec": "#B8C4CE", "alpha": 0.94}, zorder=30,
        )
        ax.text(3.55, -1.48, "SG3B Bi upper half-cylinder", fontsize=6.2, rotation=0, color="#5D3378", ha="left", va="center", zorder=25)
        ax.text(3.50, -3.55, "L0 Cu ring", fontsize=6.2, rotation=90, color="#8B3E13", ha="center", va="center", zorder=25)
        add_table_panel(table_ax, visible_groups, f"Origin key ({len(visible_groups)} groups visible; full names in CSV)")
        handles = [
            Line2D([0], [0], color="#D00000", lw=1.3, label="prompt survivor IA tree"),
            Line2D([0], [0], color="#71808D", lw=0.8, alpha=0.5, label="delayed decay-to-TES routes"),
            Patch(facecolor="#8B5FA8", label="passive Bi overlay"),
            Patch(facecolor="#D66A2C", label="L0 Cu ring overlay"),
        ]
        ax.legend(handles=handles, loc="lower left", fontsize=6.4, frameon=True, framealpha=0.9)
        fig.text(
            0.01, 0.006,
            "Scope: these are audited exact-position delayed sources that survive the package-58 W2 response. "
            "They are not a map of every activation nucleus and do not reconstruct the earlier BUILDUP production track. "
            "Geometry background is the exact inherited y'=0 mesh plus SG3B analytic overlays; source tracks are x'-z' projections.",
            fontsize=7.0, color="#344453",
        )
        paths.extend(save_figure(fig, stem))
    return paths


def sha256_small(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    config = load_json(CONFIG)
    prompt_rows, prompt_summary = prompt_receipt_audit(config)
    write_csv(OUT / "prompt_receipt_time_audit.csv", prompt_rows)
    m05_rows = m05_gamma_audit(config, prompt_summary)
    write_csv(OUT / "m05_gamma_time_reference.csv", m05_rows)
    delayed_rows, delayed_summary = delayed_audit(config)
    write_csv(OUT / "delayed_day15_equivalent_time_audit.csv", delayed_rows)

    package59 = resolve(config["package59"])
    lineage_path = package59 / "outputs/02_coupling_analysis/selected_event_lineage.csv"
    origin_rows, delayed_lineage = origin_groups(read_csv(lineage_path))
    write_csv(OUT / "selected_w2_activation_origin_groups.csv", origin_rows)
    figures = section_figures(config, origin_rows, delayed_lineage)

    gamma_row = next(row for row in prompt_rows if row["campaign"] == "combined_3x" and row["family"] == "gamma")
    base_gamma = next(row for row in prompt_rows if row["campaign"] == "base_1x" and row["family"] == "gamma")
    m05_final = [row for row in m05_rows if row["authority"].startswith("M05 corrected")]
    total_selected_counts = math.fsum(row["mission20_live_counts"] for row in origin_rows)
    summary = {
        "status": "PASS__SG3B_RECEIPT_TIME_AND_SELECTED_NUCLIDE_SECTION_AUDIT",
        "authority_boundary": {
            "SIM_payloads_opened_or_hashed": 0,
            "new_transport_started": False,
            "detector_response_rerun": False,
            "paper_modified": False,
            "prompt_time": "sum of canonical PASS receipt isotope-DAT TT within family+instant mode",
            "delayed_time": "N_transport/A_family(day15), a constant-day15 activity-equivalent sampling time",
            "origin_map": "394 final-W2 selected delayed source positions from package59 compact lineage; not all produced activation nuclei",
        },
        "prompt": prompt_summary,
        "prompt_gamma": {
            "base_events": base_gamma["accepted_events"],
            "base_TT_s": base_gamma["receipt_sum_TT_s"],
            "extra2x_events": 2_138_492,
            "extra2x_TT_s": gamma_row["receipt_sum_TT_s"] - base_gamma["receipt_sum_TT_s"],
            "combined_events": gamma_row["accepted_events"],
            "combined_TT_s": gamma_row["receipt_sum_TT_s"],
            "event_multiplier_vs_base": gamma_row["event_multiplier_vs_base"],
            "TT_multiplier_vs_base": gamma_row["TT_multiplier_vs_base"],
            "analytic_10m_TT_s": prompt_summary["gamma_analytic_10m_TT_s"],
        },
        "m05_final_gamma": m05_final,
        "delayed": delayed_summary,
        "selected_activation_origins": {
            "events": len(delayed_lineage),
            "nuclides": len({row["nuclide"] for row in origin_rows}),
            "nuclide_volume_groups": len(origin_rows),
            "mission20_live_counts": total_selected_counts,
        },
        "figures": figures,
        "small_input_sha256": {
            "analysis_inputs": sha256_small(CONFIG),
            "selected_event_lineage": sha256_small(lineage_path),
            "activation_manifest": sha256_small(Path(config["activation_manifest"])),
        },
    }
    write_json(OUT / "summary.json", summary)

    delayed_lines = "\n".join(
        f"| {row['family']} | {row['transport_triggers']:,} | {row['day15_transported_ground_activity_Bq']:.9g} | "
        f"{float(row['constant_day15_activity_equivalent_time_s']):,.3f} |"
        for row in delayed_rows
    )
    m05_lines = "\n".join(
        f"| {row['geometry']} | {row['accepted_or_target_events']:,} | {float(row['TT_s']):.6f} | {row['10m_equivalent_TT_s']:.3f} |"
        for row in m05_final
    )
    report = f"""# SG3B prompt TT and activation-origin audit

## Result

The SG3B INSTANT exposure used by package 58 already includes the retained base batch and the
independent extra-2x add-on.  For gamma it is {base_gamma['accepted_events']:,} events / 
{base_gamma['receipt_sum_TT_s']:.6f} s plus 2,138,492 events / 
{gamma_row['receipt_sum_TT_s'] - base_gamma['receipt_sum_TT_s']:.6f} s, hence
**{gamma_row['accepted_events']:,} events / {gamma_row['receipt_sum_TT_s']:.6f} s**.  The event
multiplier is exactly {gamma_row['event_multiplier_vs_base']:.6f}x and the receipt-TT multiplier is
{gamma_row['TT_multiplier_vs_base']:.6f}x.  Package 58 therefore did not normalize only one copy.

For a full-sphere FarFieldAreaSource, the analytic generation rate is
`sum(Flux) * pi * R^2`.  With gamma flux {gamma_row['total_flux_cm-2_s-1']:.12g} cm^-2 s^-1 and
R={gamma_row['farfield_radius_cm']:.1f} cm, the rate is
{gamma_row['analytic_generation_rate_s-1']:.6f} primaries/s.  The same source would make 10,000,000
gamma equivalent to **{prompt_summary['gamma_analytic_10m_TT_s']:.3f} s**, while 1000 s would contain
about {prompt_summary['gamma_events_in_1000s']:,.0f} gamma.

The remembered M05 10-million run is not present as a completed accepted authority.  Batch0003's
10-million value is a planned ceiling; its committed shard-0076 prefix is 2,001,000 events per
geometry.  The final corrected M05 accepted prompt manifest contains:

| geometry | accepted gamma | sum TT [s] | inferred TT for 10m [s] |
|---|---:|---:|---:|
{m05_lines}

Thus the corrected M05 authority agrees with SG3B at about 184 s per 10 million gamma.  A 1000-s
number must belong to a different source flux/surface contract or to a historical/non-authoritative
normalization; it cannot be reproduced from these corrected-keV receipts.

## Delayed equivalent-time convention

Each family has 1,000,000 delayed triggers.  Its equivalent time is `N/A_family(day15)`, not a
single shared mission exposure:

| family | triggers | A15 [Bq] | constant-day15 equivalent time [s] |
|---|---:|---:|---:|
{delayed_lines}

These times describe Monte Carlo sampling at the day-15 activity mixture.  The 20-day result is
obtained by the nuclide-resolved activity curves and Poisson common-time live factor; it must not be
computed by treating the delayed triggers as prompt atmospheric primaries.

## Activation-origin section

The detailed and global side sections label 35 nuclide+mother-volume groups covering all 394
delayed events that survive the final W2 response.  Sixteen nuclides are present.  Every plotted
colored point is the exact delayed source position carried by the audited source/position lineage;
the gray curves are their decay-to-TES routes, and the red curve is the sole prompt survivor.

This is deliberately a selected-background origin map.  It does not claim to show every produced
activation nucleus and does not reconstruct the earlier BUILDUP production track.  Full volume
names, coordinate ranges, event counts, day-15 rate, and 20-day contribution are in
`selected_w2_activation_origin_groups.csv`.
"""
    (OUT / "AUDIT_REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
