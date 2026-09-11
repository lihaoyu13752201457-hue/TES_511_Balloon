#!/usr/bin/env python3
"""Build the SE3 near-field high-energy-gamma/shield trade-off audit.

The builder opens only retained small CSV/JSON/PKL tables and corrected source
spectra.  Production SIM discovery, opening, stat-for-progress, and hashing are
outside this analysis contract.
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import math
import os
import pickle
import re
import runpy
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path("/home/ubuntu/.codex/worktrees/c528/TES_511_Balloon")
PACKAGE_REL = Path(
    "engineering/geometry_optimization_20260815/"
    "47_se3_plan1_transport_20260815"
)
PACKAGE = REPO / PACKAGE_REL

SOURCE_CARD_REL = PACKAGE_REL / "config/source_cards/se3_instant_gamma_shard0001.source"
CUTFLOW_REL = PACKAGE_REL / "outputs/04_common_response/common_cutflow.csv"
LINEAGE_REL = PACKAGE_REL / "outputs/04_common_response/selected_background_w2_lineage.csv"
COMMON_SUMMARY_REL = PACKAGE_REL / "outputs/04_common_response/summary.json"
MISSION_SUMMARY_REL = PACKAGE_REL / "outputs/06_mission/summary.json"
PROMPT_CATALOG_REL = PACKAGE_REL / "outputs/01_prompt/catalog/SE3"
DELAYED_CATALOG_REL = PACKAGE_REL / "outputs/03_delayed/catalog/SE3"
OUTPUT_REL = PACKAGE_REL / "outputs/09_nearfield_high_energy_gamma_tradeoff"

FINAL_OUTPUT = REPO / OUTPUT_REL
BUILDER_REL = PACKAGE_REL / "code/build_nearfield_high_energy_gamma_tradeoff.py"

PAIR_THRESHOLD_KEV = 1022.0
TRIPLET_THRESHOLD_KEV = 2044.0
SECONDS_20D = 20.0 * 86400.0


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_spectrum(path: Path) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            parts = raw.split()
            if len(parts) == 3 and parts[0] == "DP":
                points.append((float(parts[1]), float(parts[2])))
    if len(points) < 2 or any(points[i][0] >= points[i + 1][0] for i in range(len(points) - 1)):
        raise RuntimeError(f"invalid spectrum grid: {path}")
    return points


def y_at(x0: float, y0: float, x1: float, y1: float, x: float) -> float:
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def integrate_linear(points: list[tuple[float, float]], lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    total = 0.0
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        a = max(lo, x0)
        b = min(hi, x1)
        if b <= a:
            continue
        ya = y_at(x0, y0, x1, y1, a)
        yb = y_at(x0, y0, x1, y1, b)
        total += 0.5 * (ya + yb) * (b - a)
    return total


def parse_gamma_sources(repo: Path) -> list[dict[str, Any]]:
    card = repo / SOURCE_CARD_REL
    spectra: dict[str, str] = {}
    fluxes: dict[str, float] = {}
    spectrum_re = re.compile(r"^(\S+)\.Spectrum File (\S+)$")
    flux_re = re.compile(r"^(\S+)\.Flux ([0-9eE+\-.]+)$")
    with card.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            match = spectrum_re.match(line)
            if match:
                spectra[match.group(1)] = match.group(2)
            match = flux_re.match(line)
            if match:
                fluxes[match.group(1)] = float(match.group(2))
    if set(spectra) != set(fluxes) or len(spectra) != 20:
        raise RuntimeError("gamma source card does not close to 20 spectrum/flux pairs")
    rows = []
    for name in sorted(spectra):
        spectrum_path = repo / spectra[name]
        points = parse_spectrum(spectrum_path)
        norm = integrate_linear(points, points[0][0], points[-1][0])
        if not math.isclose(norm, 1.0, rel_tol=2e-7, abs_tol=2e-7):
            raise RuntimeError(f"spectrum is not unit-normalized: {spectrum_path} -> {norm}")
        rows.append(
            {
                "source": name,
                "direction_label": "up" if name.endswith("_up") else "down",
                "spectrum_rel": spectra[name],
                "flux_cm2_s": fluxes[name],
                "points": points,
                "p_gt_1022": integrate_linear(points, PAIR_THRESHOLD_KEV, points[-1][0]),
            }
        )
    return rows


def source_spectrum_analysis(repo: Path, gamma_histories: int) -> dict[str, Any]:
    sources = parse_gamma_sources(repo)
    total_flux = sum(row["flux_cm2_s"] for row in sources)
    high_flux = sum(row["flux_cm2_s"] * row["p_gt_1022"] for row in sources)
    high_fraction = high_flux / total_flux
    boundaries = [0.0, 511.0, 1022.0, 2000.0, 5000.0, 10000.0, math.inf]
    labels = ["<511 keV", "511–1022 keV", "1.022–2 MeV", "2–5 MeV", "5–10 MeV", ">10 MeV"]
    bands: list[dict[str, Any]] = []
    cumulative = 0.0
    for label, lo, hi in zip(labels, boundaries, boundaries[1:]):
        flux = 0.0
        for row in sources:
            points = row["points"]
            upper = points[-1][0] if math.isinf(hi) else hi
            flux += row["flux_cm2_s"] * integrate_linear(points, lo, upper)
        cumulative += flux
        bands.append(
            {
                "energy_band": label,
                "lower_keV": lo,
                "upper_keV": None if math.isinf(hi) else hi,
                "flux_cm2_s": flux,
                "share_total": flux / total_flux,
                "is_pair_capable": lo >= PAIR_THRESHOLD_KEV,
                "cumulative_flux_cm2_s": cumulative,
            }
        )
    direction_flux = defaultdict(float)
    for row in sources:
        direction_flux[row["direction_label"]] += row["flux_cm2_s"] * row["p_gt_1022"]
    return {
        "total_gamma_flux_cm2_s": total_flux,
        "high_gamma_flux_cm2_s": high_flux,
        "high_gamma_fraction": high_fraction,
        "gamma_histories": gamma_histories,
        "expected_high_gamma_primaries": gamma_histories * high_fraction,
        "expected_high_gamma_sampling_sigma": math.sqrt(gamma_histories * high_fraction * (1.0 - high_fraction)),
        "high_flux_by_card_direction_cm2_s": dict(direction_flux),
        "bands": bands,
        "source_rows": [
            {k: v for k, v in row.items() if k != "points"}
            for row in sources
        ],
    }


def load_catalog(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        payload = pickle.load(handle)
    required = {"local_id", "rate_hz", "has_pair_ia", "has_annihilation_ia"}
    if not required.issubset(payload):
        raise RuntimeError(f"catalog schema missing {sorted(required - set(payload))}: {path}")
    return payload


def select_cutflow(rows: list[dict[str, str]], **wanted: str) -> dict[str, float]:
    selected = [row for row in rows if all(row.get(key) == value for key, value in wanted.items())]
    return {
        "rows": len(selected),
        "selected_events": sum(int(row["selected_events"]) for row in selected),
        "weighted_cps": sum(float(row["weighted_value"]) for row in selected),
    }


def event_evidence(repo: Path) -> dict[str, Any]:
    prompt_catalogs = {}
    for path in sorted((repo / PROMPT_CATALOG_REL).glob("*.pkl")):
        prompt_catalogs[path.stem] = load_catalog(path)
    delayed_catalogs = {}
    for path in sorted((repo / DELAYED_CATALOG_REL).glob("*.pkl")):
        delayed_catalogs[path.stem] = load_catalog(path)
    if len(prompt_catalogs) != 8 or len(delayed_catalogs) != 7:
        raise RuntimeError("expected 8 prompt and 7 transported delayed catalogs")

    def catalog_summary(catalogs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        kept = pair = anni = 0
        pair_rate = anni_rate = 0.0
        by_family = {}
        for family, data in catalogs.items():
            n = len(data["local_id"])
            if not (n == len(data["rate_hz"]) == len(data["has_pair_ia"]) == len(data["has_annihilation_ia"])):
                raise RuntimeError(f"catalog vector length mismatch: {family}")
            fp = sum(bool(x) for x in data["has_pair_ia"])
            fa = sum(bool(x) for x in data["has_annihilation_ia"])
            fpr = sum(float(w) for w, flag in zip(data["rate_hz"], data["has_pair_ia"]) if flag)
            far = sum(float(w) for w, flag in zip(data["rate_hz"], data["has_annihilation_ia"]) if flag)
            by_family[family] = {"tes_positive": n, "pair": fp, "annihilation": fa, "pair_rate_cps": fpr, "annihilation_rate_cps": far}
            kept += n
            pair += fp
            anni += fa
            pair_rate += fpr
            anni_rate += far
        return {"tes_positive": kept, "pair": pair, "annihilation": anni, "pair_rate_cps": pair_rate, "annihilation_rate_cps": anni_rate, "by_family": by_family}

    cutflow = read_csv(repo / CUTFLOW_REL)
    prompt_raw_pre = select_cutflow(cutflow, geometry="SE3", stream="prompt", response_state="raw", stage="pre_veto", window_id="w2_510p58_511p42")
    prompt_raw_veto = select_cutflow(cutflow, geometry="SE3", stream="prompt", response_state="raw", stage="active_veto50", window_id="w2_510p58_511p42")
    prompt_gamma_pre = select_cutflow(cutflow, geometry="SE3", stream="prompt", family="gamma", response_state="raw", stage="pre_veto", window_id="w2_510p58_511p42")
    delayed_raw_pre = select_cutflow(cutflow, geometry="SE3", stream="delayed", response_state="raw", stage="pre_veto", window_id="w2_510p58_511p42")

    lineage = read_csv(repo / LINEAGE_REL)
    delayed_index = {}
    for family, data in delayed_catalogs.items():
        delayed_index[family] = {
            int(local_id): (bool(pair), bool(anni))
            for local_id, pair, anni in zip(data["local_id"], data["has_pair_ia"], data["has_annihilation_ia"])
        }
    final_pair = final_anni = 0
    family_rates = defaultdict(float)
    volume_rates = defaultdict(float)
    for row in lineage:
        family = row["family"]
        local_id = int(row["local_event_id"])
        if family not in delayed_index or local_id not in delayed_index[family]:
            raise RuntimeError(f"lineage row missing from delayed catalog: {family}/{local_id}")
        pair, anni = delayed_index[family][local_id]
        final_pair += int(pair)
        final_anni += int(anni)
        weight = float(row["event_weight_cps"])
        family_rates[family] += weight
        volume_rates[row["source_volume"]] += weight
    final_rate = sum(family_rates.values())
    volume_labels = {
        "ColdPlate_MXC_50mK_SD_anchor": "MXC 50 mK cold plate",
        "Cu_50mK_StillLike_Can_bottom_cap_2mm": "Cu 50 mK bottom cap",
        "ColdPlate_4K": "4 K cold plate",
        "Cu_SubstrateSupport_SolidDisk_L0_deepest": "Cu substrate disk",
        "ColdPlate_CP_100mK_intercept": "100 mK intercept plate",
        "NbTi_Bundle_Still_4K": "NbTi Still–4 K bundle",
        "Cu_SubstrateSupport_OpenRing_L3_ZM_panel": "Cu support ring L3",
        "Cu_50mK_StillLike_Can_side_wall_rectcut_window_band": "Cu 50 mK window band",
        "ColdPlate_Still_0p7K": "0.7 K Still plate",
        "XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K": "Cu lower open collar",
    }
    volume_rows = [
        {"source_volume": volume, "display_volume": volume_labels.get(volume, volume), "rate_cps": rate, "share_final": rate / final_rate, "selected_event_rows": sum(1 for row in lineage if row["source_volume"] == volume)}
        for volume, rate in sorted(volume_rates.items(), key=lambda item: -item[1])
    ]
    family_rows = [
        {"family": family, "rate_cps": rate, "share_final": rate / final_rate}
        for family, rate in sorted(family_rates.items(), key=lambda item: -item[1])
    ]
    gamma_generated = int(prompt_catalogs["gamma"]["generated_events"])
    return {
        "gamma_generated_histories": gamma_generated,
        "prompt_catalog": catalog_summary(prompt_catalogs),
        "delayed_catalog": catalog_summary(delayed_catalogs),
        "prompt_raw_w2_pre_veto": prompt_raw_pre,
        "prompt_raw_w2_after_active_veto": prompt_raw_veto,
        "prompt_gamma_raw_w2_pre_veto": prompt_gamma_pre,
        "delayed_raw_w2_pre_veto": delayed_raw_pre,
        "final_delayed_rows": len(lineage),
        "final_delayed_rate_cps": final_rate,
        "final_pair_events": final_pair,
        "final_annihilation_events": final_anni,
        "family_rows": family_rows,
        "volume_rows": volume_rows,
    }


def diffuse_transmission(mu_linear_cm: float, thickness_mm: float, intervals: int = 20000) -> float:
    """Lambert-flux-weighted transmission: 2*integral_0^1 u exp(-tau/u) du."""
    if thickness_mm <= 0:
        return 1.0
    if intervals % 2:
        intervals += 1
    tau = mu_linear_cm * thickness_mm / 10.0
    step = 1.0 / intervals
    acc = 0.0
    for index in range(intervals + 1):
        u = index * step
        value = 0.0 if u == 0.0 else 2.0 * u * math.exp(-tau / u)
        weight = 1 if index in (0, intervals) else (4 if index % 2 else 2)
        acc += weight * value
    return acc * step / 3.0


def material_rows() -> list[dict[str, Any]]:
    # 0.511 MeV attenuation and pair probabilities are derived from NIST XCOM;
    # density values are from PDG material tables. Pair probabilities are first-
    # interaction probabilities for a normally incident 1 mm layer.
    raw = [
        ("W", 19.30, 0.1338, 2.68, 0.00866, 0.03694, 0.06394, 0.09376, 0.1725),
        ("Ta", 16.65, 0.1314, 3.17, 0.00737, 0.03169, 0.05502, 0.08087, 0.1515),
        ("Bi", 9.747, 0.1602, 4.44, 0.00532, 0.02087, 0.03562, 0.05222, 0.1022),
        ("Al", 2.699, 0.08367, 30.69, 0.00018, 0.00114, 0.00224, 0.00346, None),
        ("BGO", 7.130, 0.1350, 7.20, 0.00287, 0.01178, 0.02045, 0.03021, None),
    ]
    rows = []
    for material, density, mu_rho, hvl, p2, p5, p10, p20, pavg3 in raw:
        mu = density * mu_rho
        rows.append(
            {
                "material": material,
                "density_g_cm3": density,
                "mu_over_rho_511_cm2_g": mu_rho,
                "mu_linear_511_cm-1": mu,
                "hvl_511_mm": hvl,
                "normal_511_attenuation_1mm": 1.0 - math.exp(-mu / 10.0),
                "diffuse_511_transmission_1mm": diffuse_transmission(mu, 1.0),
                "pair_first_2MeV_1mm": p2,
                "pair_first_5MeV_1mm": p5,
                "pair_first_10MeV_1mm": p10,
                "pair_first_20MeV_1mm": p20,
                "source_spectrum_avg_pair_3mm": pavg3,
            }
        )
    return rows


def find_threshold_mm(mu: float, intercept: float, signal_survival: float, target_ratio: float = 0.75) -> float | None:
    if math.sqrt(max(0.0, 1.0 - intercept)) / signal_survival > target_ratio:
        return None
    lo, hi = 0.0, 30.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        t = diffuse_transmission(mu, mid, intervals=4000)
        ratio = math.sqrt(1.0 - intercept * (1.0 - t)) / signal_survival
        if ratio <= target_ratio:
            hi = mid
        else:
            lo = mid
    return hi


def shield_model(event: dict[str, Any], mission: dict[str, Any]) -> dict[str, Any]:
    volume_share = {row["source_volume"]: row["share_final"] for row in event["volume_rows"]}
    inside_sleeve = {
        "Cu_SubstrateSupport_SolidDisk_L0_deepest",
        "Cu_SubstrateSupport_OpenRing_L3_ZM_panel",
    }
    umbrella_sources = {
        "ColdPlate_MXC_50mK_SD_anchor",
        "Cu_50mK_StillLike_Can_bottom_cap_2mm",
        "ColdPlate_4K",
        "ColdPlate_CP_100mK_intercept",
    }
    external_share = 1.0 - sum(volume_share.get(name, 0.0) for name in inside_sleeve)
    umbrella_source_share = sum(volume_share.get(name, 0.0) for name in umbrella_sources)
    full_coverage = 0.90
    umbrella_view_coverage = 0.66
    full_intercept = external_share * full_coverage
    umbrella_intercept = umbrella_source_share * umbrella_view_coverage
    b20 = float(mission["geometries"]["SE3"]["background_counts_20d"])
    b0_average_cps = b20 / SECONDS_20D
    mats = {row["material"]: row for row in material_rows()}
    w_mu = mats["W"]["mu_linear_511_cm-1"]
    curve = []
    for step in range(0, 21):
        thickness = step * 0.25
        trans = diffuse_transmission(w_mu, thickness)
        normal = math.exp(-w_mu * thickness / 10.0)
        full_bratio = 1.0 - full_intercept * (1.0 - trans)
        umbrella_bratio = 1.0 - umbrella_intercept * (1.0 - trans)
        curve.append(
            {
                "thickness_mm": thickness,
                "material": "W",
                "diffuse_transmission_511": trans,
                "normal_transmission_511": normal,
                "full_windowed_intercept_fraction": full_intercept,
                "umbrella_intercept_fraction": umbrella_intercept,
                "full_windowed_background_ratio_no_new": full_bratio,
                "umbrella_background_ratio_no_new": umbrella_bratio,
                "full_windowed_f3_ratio_no_new": math.sqrt(full_bratio),
                "umbrella_f3_ratio_no_new": math.sqrt(umbrella_bratio),
                "full_25pct_new511_budget_counts20d": b20 * (0.5625 - full_bratio),
                "umbrella_25pct_new511_budget_counts20d": b20 * (0.5625 - umbrella_bratio),
            }
        )
    thresholds = []
    for material in ("W", "Ta", "Bi"):
        mu = mats[material]["mu_linear_511_cm-1"]
        for survival in (1.0, 0.98, 0.95):
            thresholds.append(
                {
                    "material": material,
                    "signal_survival": survival,
                    "layout": "windowed_full_sleeve",
                    "thickness_for_25pct_mm": find_threshold_mm(mu, full_intercept, survival),
                }
            )
    budgets = []
    for material in ("W", "Ta", "Bi"):
        mu = mats[material]["mu_linear_511_cm-1"]
        for thickness in (1.0, 2.0, 3.0, 4.0):
            trans = diffuse_transmission(mu, thickness)
            for layout, intercept in (("windowed_full_sleeve", full_intercept), ("mxc_pole_umbrella", umbrella_intercept)):
                bratio = 1.0 - intercept * (1.0 - trans)
                budget = b20 * (0.5625 - bratio)
                budgets.append(
                    {
                        "layout": layout,
                        "layout_label": "Windowed full sleeve" if layout == "windowed_full_sleeve" else "MXC/pole umbrella",
                        "material": material,
                        "thickness_mm": thickness,
                        "diffuse_transmission_511": trans,
                        "ideal_f3_ratio_no_new": math.sqrt(bratio),
                        "ideal_improvement": 1.0 - math.sqrt(bratio),
                        "new511_budget_counts20d_for_25pct": budget,
                        "new511_budget_average_cps_if_same_time_shape": budget / SECONDS_20D,
                        "budget_status": "POSITIVE_MARGIN" if budget > 0 else "IDEAL_SHIELDING_ALONE_BELOW_25PCT_TARGET",
                    }
                )
    gamma_share = next(row["share_final"] for row in event["family_rows"] if row["family"] == "gamma")
    bgo_outer_best_ratio = math.sqrt(1.0 - gamma_share)
    candidates = [
        {
            "layout": "MXC/pole umbrella",
            "placement": "BGO内侧，遮挡MXC冷盘下表面与铜pole方向；不跨信号开窗",
            "intercept_assumption": umbrella_intercept,
            "signal_risk": "低到中；取决于边缘散射和支撑遮挡",
            "pair_veto_position": "不利：pair顶点在BGO内侧",
            "expected_role": "低质量、低风险首轮定向筛选；现实厚度多为10–20%级上限",
            "decision": "First test",
        },
        {
            "layout": "Windowed full sleeve",
            "placement": "复用已移除MuMetal近场包络；TES灵敏方向保留开窗",
            "intercept_assumption": full_intercept,
            "signal_risk": "中到高；近TES回散、荧光、pair和材料活化均在主动层内侧",
            "pair_veto_position": "最不利：新增pair可能绕过BGO/plastic veto",
            "expected_role": "达到25%目标的唯一解析候选，但需约数毫米W并留严格新511预算",
            "decision": "Second after scorer",
        },
        {
            "layout": "BGO外被动层",
            "placement": "BGO外侧，仅补缝隙、薄区或开孔旁collar；不建议完整全包",
            "intercept_assumption": 0.0,
            "signal_risk": "低（若避开光路），但质量、活化和veto死时间可能高",
            "pair_veto_position": "较有利：向内二次粒子仍需穿主动BGO",
            "expected_role": f"不拦当前内部Cu延迟511；即使清零gamma族，F3理想仅改善{1.0-bgo_outer_best_ratio:.2%}",
            "decision": "Gap fill only",
        },
    ]
    return {
        "background_counts_20d": b20,
        "background_average_cps_20d": b0_average_cps,
        "day15_background_cps": event["final_delayed_rate_cps"],
        "external_source_share_day15": external_share,
        "umbrella_target_source_share_day15": umbrella_source_share,
        "full_coverage_assumption": full_coverage,
        "umbrella_view_coverage_assumption": umbrella_view_coverage,
        "full_effective_intercept_fraction": full_intercept,
        "umbrella_effective_intercept_fraction": umbrella_intercept,
        "bgo_outer_gamma_family_share_bound": gamma_share,
        "bgo_outer_best_f3_ratio_if_gamma_family_eliminated": bgo_outer_best_ratio,
        "curve": curve,
        "thresholds": thresholds,
        "budgets": budgets,
        "candidates": candidates,
    }


def compute_analysis(repo: Path = REPO) -> dict[str, Any]:
    event = event_evidence(repo)
    source = source_spectrum_analysis(repo, event["gamma_generated_histories"])
    common = read_json(repo / COMMON_SUMMARY_REL)
    mission = read_json(repo / MISSION_SUMMARY_REL)
    model = shield_model(event, mission)
    materials = material_rows()
    analysis = {
        "schema_version": 1,
        "analysis_scope": "SE3_PLAN1_SMALL_TABLE_AND_CORRECTED_SOURCE_SPECTRUM_TRADEOFF",
        "sim_access_policy": "FORBIDDEN__NO_PRODUCTION_SIM_DISCOVERY_OPEN_STAT_OR_HASH",
        "source_spectrum": source,
        "event_evidence": event,
        "shield_model": model,
        "materials": materials,
        "current_se3": {
            "aeff_cm2": common["final_measured_w2"]["SE3_signal"]["selected_effective_area_cm2"],
            "f3_20d": mission["geometries"]["SE3"]["F3_20d_ph_cm2_s"],
            "f3_proxy_20d": mission["geometries"]["SE3"]["F3_20d_componentwise_proxy_ph_cm2_s"],
            "background_counts_20d": mission["geometries"]["SE3"]["background_counts_20d"],
        },
        "data_quality": {
            "nearfield_surface_crossing_count_available": False,
            "reason": "compact catalogs omit gamma track energy/direction/position and boundary crossings",
            "exact_measurement_required": "paired baseline/candidate lightweight stepping scorer",
            "final_delayed_lineage_rows": event["final_delayed_rows"],
            "final_pair_events": event["final_pair_events"],
            "final_annihilation_events": event["final_annihilation_events"],
        },
        "provenance": [
            SOURCE_CARD_REL.as_posix(),
            "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/",
            CUTFLOW_REL.as_posix(),
            LINEAGE_REL.as_posix(),
            COMMON_SUMMARY_REL.as_posix(),
            MISSION_SUMMARY_REL.as_posix(),
        ],
    }
    validate_analysis(analysis)
    return analysis


def validate_analysis(a: dict[str, Any]) -> None:
    source = a["source_spectrum"]
    event = a["event_evidence"]
    if not math.isclose(source["total_gamma_flux_cm2_s"], 4.7996615777852, rel_tol=2e-12):
        raise RuntimeError("gamma source flux anchor drift")
    if not math.isclose(source["high_gamma_fraction"], 0.23429582858976464, rel_tol=2e-10):
        raise RuntimeError("high-energy gamma fraction anchor drift")
    if event["prompt_raw_w2_pre_veto"]["selected_events"] != 126:
        raise RuntimeError("prompt raw W2 anchor drift")
    if event["prompt_raw_w2_after_active_veto"]["selected_events"] != 0:
        raise RuntimeError("prompt active-veto W2 anchor drift")
    if event["final_delayed_rows"] != 47 or event["final_pair_events"] != 0 or event["final_annihilation_events"] != 47:
        raise RuntimeError("final delayed lineage anchor drift")
    if not math.isclose(event["final_delayed_rate_cps"], 0.06011336205846697, rel_tol=2e-12):
        raise RuntimeError("day15 background anchor drift")


def markdown_table(rows: list[dict[str, Any]], fields: list[str], limit: int = 20) -> str:
    selected = rows[:limit]
    head = "| " + " | ".join(fields) + " |"
    sep = "|" + "|".join("---" for _ in fields) + "|"
    body = []
    for row in selected:
        values = []
        for field in fields:
            value = row.get(field)
            if isinstance(value, float):
                values.append(f"{value:.6g}")
            else:
                values.append(str(value))
        body.append("| " + " | ".join(values) + " |")
    return "\n".join([head, sep, *body])


def execute_notebook_cells(code_cells: list[str]) -> list[dict[str, Any]]:
    namespace: dict[str, Any] = {}
    result = []
    for execution_count, source in enumerate(code_cells, start=1):
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(compile(source, f"<se3-nearfield-cell-{execution_count}>", "exec"), namespace)
        except Exception as exc:
            result.append(
                {
                    "cell_type": "code",
                    "execution_count": execution_count,
                    "metadata": {},
                    "source": source.splitlines(keepends=True),
                    "outputs": [{"output_type": "error", "ename": type(exc).__name__, "evalue": str(exc), "traceback": []}],
                }
            )
            raise
        result.append(
            {
                "cell_type": "code",
                "execution_count": execution_count,
                "metadata": {},
                "source": source.splitlines(keepends=True),
                "outputs": [{"output_type": "stream", "name": "stdout", "text": stdout.getvalue().splitlines(keepends=True)}],
            }
        )
    return result


def build_notebook(output: Path) -> None:
    module_abs = (REPO / BUILDER_REL).as_posix()
    code_cells = [
        f'''from pathlib import Path\nimport runpy\nREPO = Path("{REPO.as_posix()}")\nMODULE = Path("{module_abs}")\nns = runpy.run_path(str(MODULE))\ncompute_analysis = ns["compute_analysis"]\nmarkdown_table = ns["markdown_table"]\nprint("Small-table-only contract loaded; production SIM access is forbidden.")''',
        '''analysis = compute_analysis(REPO)\ns = analysis["source_spectrum"]\nprint({k: s[k] for k in ["total_gamma_flux_cm2_s", "high_gamma_flux_cm2_s", "high_gamma_fraction", "gamma_histories", "expected_high_gamma_primaries", "expected_high_gamma_sampling_sigma"]})\nprint(markdown_table(s["bands"], ["energy_band", "flux_cm2_s", "share_total", "is_pair_capable"]))''',
        '''e = analysis["event_evidence"]\nprint({\n "prompt_raw_W2_pre_veto": e["prompt_raw_w2_pre_veto"],\n "prompt_raw_W2_after_veto": e["prompt_raw_w2_after_active_veto"],\n "final_delayed_rows": e["final_delayed_rows"],\n "final_delayed_rate_cps": e["final_delayed_rate_cps"],\n "final_pair_events": e["final_pair_events"],\n "final_annihilation_events": e["final_annihilation_events"],\n})\nprint(markdown_table(e["family_rows"], ["family", "rate_cps", "share_final"]))''',
        '''e = analysis["event_evidence"]\nprint(markdown_table(e["volume_rows"], ["source_volume", "rate_cps", "share_final", "selected_event_rows"]))''',
        '''m = analysis["materials"]\nprint(markdown_table(m, ["material", "normal_511_attenuation_1mm", "pair_first_2MeV_1mm", "pair_first_5MeV_1mm", "pair_first_10MeV_1mm", "pair_first_20MeV_1mm"]))''',
        '''model = analysis["shield_model"]\nprint({k: model[k] for k in ["background_counts_20d", "external_source_share_day15", "umbrella_target_source_share_day15", "full_effective_intercept_fraction", "umbrella_effective_intercept_fraction", "bgo_outer_gamma_family_share_bound"]})\nchosen = [r for r in model["budgets"] if r["material"] == "W" and r["thickness_mm"] in (1.0, 2.0, 3.0, 4.0)]\nprint(markdown_table(chosen, ["layout", "material", "thickness_mm", "ideal_f3_ratio_no_new", "new511_budget_counts20d_for_25pct", "budget_status"]))''',
        '''assert analysis["data_quality"]["nearfield_surface_crossing_count_available"] is False\nassert analysis["event_evidence"]["final_pair_events"] == 0\nassert analysis["event_evidence"]["final_annihilation_events"] == 47\nassert analysis["sim_access_policy"].startswith("FORBIDDEN")\nprint("PASS: source spectrum, cutflow, delayed lineage, material table, and shield model anchors close.")''',
    ]
    executed = execute_notebook_cells(code_cells)
    markdown_cells = [
        "# SE3 TES近场高能γ与被动屏蔽 trade-off\n\n本 notebook 只读取 corrected source spectra 与 stage01/03/04/06 小表；禁止发现、打开、stat-for-progress 或哈希 production SIM。",
        "## 1. 源级高能γ边界\n\n这里的比例是大气 gamma **源级**分布，不是穿过 TES 近场表面的 crossing tally。",
        "## 2. 当前 prompt pair 与最终 delayed 511\n\n事件级 PAIR/ANNI 标志没有顶点材料/位置；最终 lineage 可判断残余是否带这些标志。",
        "## 3. 最终 delayed 本底的源体积分布\n\n只有47条低统计幸存，体积分数仅用于 screening 和布局优先级。",
        "## 4. 材料层的511衰减与pair代价\n\nPAIR概率是 XCOM 派生的法向1 mm首相互作用概率；它不等于最终被TES接受的511率。",
        "## 5. 套筒/伞形模型与新增511预算\n\n模型采用漫射入射透过、day15 lineage源份额、全套90%覆盖、伞形66%视因子/覆盖，且先令信号存活s=1。",
        "## 6. QA与缺失测量\n\n精确 trade-off 仍需要 baseline/candidate paired stepping scorer 与新材料 activation→delayed。",
    ]
    cells: list[dict[str, Any]] = []
    for index, code in enumerate(executed):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": markdown_cells[index].splitlines(keepends=True)})
        cells.append(code)
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3 (stdlib)", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "se3_nearfield_tradeoff": {
                "executed_top_to_bottom": True,
                "execution_error_count": 0,
                "execution_engine": "stdlib exec capture",
                "sim_access_policy": "FORBIDDEN__NO_PRODUCTION_SIM_DISCOVERY_OPEN_STAT_OR_HASH",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    write_json(output / "nearfield_high_energy_gamma_tradeoff.ipynb", notebook)


def artifact_sources() -> list[dict[str, Any]]:
    evidence_db = (OUTPUT_REL / "report_evidence.sqlite").as_posix()
    return [
        {"id": "src_analysis", "label": "SE3 near-field headline metrics", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM kpis ORDER BY row_order;", "description": "Headline metrics reconciled from corrected spectra, cutflow, lineage, and mission small tables.", "tables_used": ["kpis", SOURCE_CARD_REL.as_posix(), CUTFLOW_REL.as_posix(), LINEAGE_REL.as_posix(), MISSION_SUMMARY_REL.as_posix()], "filters": ["SE3 only", "W2 510.58–511.42 keV", "production SIM access forbidden"], "metric_definitions": ["High-gamma fraction = flux-weighted integral above 1022 keV", "F3 ratio = sqrt(Bnew/B0)/(Aeff_new/Aeff_0)"]}},
        {"id": "src_spectrum", "label": "Corrected atmospheric gamma energy bands", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM energy_bands ORDER BY row_order;", "description": "Flux-weighted energy bands from 20 corrected-keV spectra.", "tables_used": ["energy_bands", SOURCE_CARD_REL.as_posix(), "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"], "filters": ["ParticleType gamma", "pair threshold 1022 keV"], "metric_definitions": ["Band flux = sum_i Flux_i × integral_band PDF_i(E)dE"]}},
        {"id": "src_lineage", "label": "SE3 selected W2 delayed lineage by source volume", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM source_volumes ORDER BY share_final DESC, row_order;", "description": "Weighted contribution of the 47 final delayed W2 lineage rows by source volume.", "tables_used": ["source_volumes", LINEAGE_REL.as_posix()], "filters": ["geometry=SE3", "stream=delayed", "measured W2", "active veto plus Step05"]}},
        {"id": "src_cutflow", "label": "SE3 common response cutflow", "path": CUTFLOW_REL.as_posix()},
        {"id": "src_tradeoff", "label": "Shield layout screening curve", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM shield_curve ORDER BY thickness_mm, row_order;", "description": "Diffuse-transmission ideal screen with explicit source interception.", "tables_used": ["shield_curve"], "filters": ["W thickness 0–5 mm", "signal survival=1", "no new pair/activation in ideal curve"], "metric_definitions": ["Tdiff=2 integral_0^1 u exp(-mu*t/u)du", "Bnew/B0=1-f(1-Tdiff)+r_new/B0", "F3new/F3old=sqrt(Bnew/B0)/s"]}},
        {"id": "src_budgets", "label": "25-percent new-511 budget points", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM selected_budgets ORDER BY new511_budget_counts20d_for_25pct DESC, row_order;", "description": "Selected material/thickness points with signed new accepted-W2 budgets.", "tables_used": ["selected_budgets"]}},
        {"id": "src_xcom", "label": "NIST XCOM-derived material screen", "path": evidence_db, "href": "https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html", "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM materials ORDER BY normal_511_attenuation_1mm DESC, row_order;", "description": "Official attenuation and pair coefficients transformed into 1-mm first-interaction probabilities.", "tables_used": ["materials"], "metric_definitions": ["Ppair_first=(mu_pair/mu_total)*(1-exp(-mu_total*rho*t))"]}},
        {"id": "src_candidates", "label": "Shield layout decision matrix", "path": evidence_db, "query": {"engine": "SQLite", "language": "sql", "sql": "SELECT * FROM candidates ORDER BY decision, row_order;", "description": "Layout ranking combining residual coverage, signal risk, and pair-veto topology.", "tables_used": ["candidates"]}},
        {"id": "src_notebook", "label": "Executed SE3 near-field trade-off notebook", "path": (OUTPUT_REL / "nearfield_high_energy_gamma_tradeoff.ipynb").as_posix()},
    ]


def report_datasets(analysis: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    source = analysis["source_spectrum"]
    event = analysis["event_evidence"]
    model = analysis["shield_model"]
    return {
        "kpis": [{
            "high_gamma_fraction": source["high_gamma_fraction"],
            "high_gamma_flux_cm2_s": source["high_gamma_flux_cm2_s"],
            "prompt_pair_pre_veto_cps": event["prompt_raw_w2_pre_veto"]["weighted_cps"],
            "prompt_pair_post_veto_cps": event["prompt_raw_w2_after_active_veto"]["weighted_cps"],
            "day15_final_background_cps": event["final_delayed_rate_cps"],
            "final_lineage_events": event["final_delayed_rows"],
            "background_counts_20d": model["background_counts_20d"],
            "current_f3": analysis["current_se3"]["f3_20d"],
        }],
        "energy_bands": source["bands"],
        "source_volumes": event["volume_rows"],
        "shield_curve": model["curve"],
        "selected_budgets": [row for row in model["budgets"] if row["material"] in ("W", "Ta", "Bi") and row["thickness_mm"] in (2.0, 3.0, 4.0)],
        "materials": analysis["materials"],
        "candidates": model["candidates"],
    }


def build_report_db(output: Path, analysis: dict[str, Any]) -> None:
    path = output / "report_evidence.sqlite"
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        for table, rows in report_datasets(analysis).items():
            if not rows:
                raise RuntimeError(f"empty report dataset: {table}")
            fields = list(rows[0])
            def sql_type(field: str) -> str:
                values = [row.get(field) for row in rows if row.get(field) is not None]
                if any(isinstance(value, str) for value in values):
                    return "TEXT"
                if any(isinstance(value, float) for value in values):
                    return "REAL"
                if any(isinstance(value, (int, bool)) for value in values):
                    return "INTEGER"
                return "TEXT"
            columns = ["row_order INTEGER NOT NULL"] + [f'"{field}" {sql_type(field)}' for field in fields]
            connection.execute(f'CREATE TABLE "{table}" ({", ".join(columns)})')
            placeholders = ",".join("?" for _ in range(len(fields) + 1))
            for index, row in enumerate(rows):
                values = [index] + [int(value) if isinstance(value := row.get(field), bool) else value for field in fields]
                connection.execute(f'INSERT INTO "{table}" VALUES ({placeholders})', values)
        connection.commit()
    finally:
        connection.close()


def load_report_datasets(output: Path) -> dict[str, list[dict[str, Any]]]:
    connection = sqlite3.connect(output / "report_evidence.sqlite")
    connection.row_factory = sqlite3.Row
    try:
        result = {}
        for table in ("kpis", "energy_bands", "source_volumes", "shield_curve", "selected_budgets", "materials", "candidates"):
            result[table] = [dict(row) for row in connection.execute(f'SELECT * FROM "{table}" ORDER BY row_order')]
        return result
    finally:
        connection.close()


def build_artifact(output: Path, analysis: dict[str, Any]) -> None:
    source = analysis["source_spectrum"]
    event = analysis["event_evidence"]
    model = analysis["shield_model"]
    datasets = load_report_datasets(output)
    sources = artifact_sources()
    title = "SE3 TES近场高能γ与屏蔽权衡"
    summary_body = f"""## 技术结论\n\n**现有产物不能给出“穿过 TES 近场表面的 >1.022 MeV γ 精确数量”。** 能确定的是：corrected 大气 gamma 源中 **{source['high_gamma_fraction']:.2%}** 高于阈值（{source['high_gamma_flux_cm2_s']:.4f} cm⁻² s⁻¹），对应 fresh gamma {source['gamma_histories']:,} histories 的源级期望约 {source['expected_high_gamma_primaries']:,.0f} 个；这不是近场 crossing。\n\n**当前最终残余不是 prompt pair 泄漏。** raw prompt W2 有 {event['prompt_raw_w2_pre_veto']['selected_events']} 个 PAIR+ANNI 事件（{event['prompt_raw_w2_pre_veto']['weighted_cps']:.3f} cps），现有 BGO+plastic veto 后中央值为 0；最终 {event['final_delayed_rows']} 个 delayed W2 幸存全部带 ANNI、0 个带 PAIR，总率 {event['final_delayed_rate_cps']:.5f} cps。\n\n**布局优先级：MXC/pole 伞形片先做低风险筛选；若硬目标是 F3 改善≥25%，再评估带信号开窗的数毫米 W 全套筒；BGO 外完整被动层不优先。** 全套筒的解析收益上限较大，但新增 pair/活化发生在主动 veto 内侧，必须用 paired scorer 和新材料 activation 链裁决。"""
    findings_body = """## 源级高能γ不少，但近场 crossing 仍未测量\n\n高能尾部并非只贴着阈值：源谱中约四成的 >1.022 MeV flux 位于 10 MeV 以上，高 Z pair 与光核风险因此不能忽略。图中是 corrected source-card 的源级 flux 分解；它给出输入边界，不代表到达 sleeve、MXC 或 BGO 表面的通量。"""
    lineage_body = """## 最终残余集中在近场冷盘与铜支撑\n\n日15中央值的47条 delayed 幸存由少数源体积主导。这个分布支持“定向遮挡优先于盲目加整层材料”，但每个主要体积只有1–数个 Monte Carlo 幸存，份额仅可用于筛选，不能用于材料晋升。"""
    budget_body = f"""## 25% 改善需要同时满足屏蔽、信号和新增511预算\n\n筛选式为 `F3_new/F3_0 = sqrt(1 - f(1-T511) + r_new/B0) / s`。主曲线先取 s=1、r_new=0；全套筒把外部源份额与90%覆盖折成 f={model['full_effective_intercept_fraction']:.3f}，伞形把目标源份额与66%视因子/覆盖折成 f={model['umbrella_effective_intercept_fraction']:.3f}。因此曲线是**物理上限**，任何 Aeff 损失、开窗泄漏、pair 或材料活化只会变差。"""
    material_body = """## 不存在“高 Z 且天然弱 pair”的捷径\n\n511 keV 低于核场 pair 阈值，本身不会成对；但大气中更高能的γ会。XCOM显示，同一毫米材料里 W/Ta/Bi 的511衰减越强，2–20 MeV 的pair概率也不可忽略。表中pair数是首相互作用概率，不是最终TES接受率；后者取决于顶点在BGO内外、511自吸收、主动veto和Step05。"""
    layout_body = """## 三种布局不是同一个问题\n\n伞形片用较少质量遮挡已知方向，适合作为第一轮；全套筒能截获更多外部近场511，但把最高风险的被动材料放在BGO内侧；BGO外层更容易让二次粒子被主动BGO标记，却拦不住从内部Cu到TES的主导延迟511。"""
    scope_body = """## 口径、数据与定义\n\n- **高能γ**：源谱总能量 >1.022 MeV；triplet阈值为2.044 MeV。\n- **最终本底**：SE3、measured W2 510.58–511.42 keV、3个BGO+3个plastic阈值veto、TES侧康普顿/FoV Step05。\n- **F3筛选**：固定观测时间时 `F3 ∝ sqrt(B)/Aeff`；20日B0取fresh SE3 mission fold。\n- **全套筒/伞形份额**：来自day15 final-lineage中心值并乘显式覆盖/视因子假设。\n- **统计层级**：Plan1约1/3 transport screen；不是几何自动晋升权威。"""
    methods_body = """## 方法：把可测量量和模型假设分开\n\n20个 corrected-keV gamma PDF 以 source-card Flux 加权并在阈值处线性插值、梯形积分。prompt/delayed compact catalogs只用于事件级 PAIR/ANNI 标志；47条最终 lineage 用事件权重重建族与源体积分布。材料衰减和首pair概率来自XCOM。屏蔽曲线采用Lambert通量权重的漫射透过；normal-incidence值保留在数据表中作为几何敏感性参考。"""
    limitation_body = """## 限制、不确定性与稳健性\n\n- compact PKL没有γ track能量、方向、顶点材料或边界crossing；因此不报告虚假的“TES近场高能γ数量”。\n- 47条最终 delayed lineage 的体积分数受低统计波动支配；componentwise上界远宽于中央值。\n- 新壳的 `r_new` 包含 prompt pair、荧光、光核次级和材料activation→delayed，解析XCOM不能替代全链。\n- BGO外层的中央收益上界只用“gamma族全部消失”估算；它没有量化缝隙补偿或veto deadtime。\n- 曲线假设新增结构不损失Aeff；即使2–5%的信号损失，也会显著提高达到25%改善所需厚度并压缩新增511预算。"""
    next_body = """## 推荐试验顺序\n\n1. 先在 baseline 与候选几何加入**轻量 stepping scorer**：sleeve内/外面、MXC下表面、pole伞面、BGO内/外面；记录首次inward γ crossing、E/方向/权重/track lineage、PAIR顶点和母γ能量、ANNI子光子及最终cut。\n2. 首轮跑 **W伞形 1/2/3 mm**，完全避开信号开窗；用同一37194-ray bank做Aeff canary，并用prompt gamma统计新增pair是否仍被veto。\n3. 若伞形实测视因子不足以达到目标，再跑 **windowed W full sleeve 2/3/4 mm**；进入全链前要求 s≥0.98，且由20日fold给出的新增accepted-W2预算为正。\n4. 只有通过prompt门的候选才跑新材料 buildup→actual-position activation→delayed→81-node mission F3；任何旧SE3 inventory都不能迁移到新增材料。\n5. BGO外只做缝隙/薄区/collar补强，不做完整高Z全包；同时审计活化、光核中子和veto deadtime。"""
    questions_body = """## 仍需回答的问题\n\n- 各候选面真实的 >1.022 MeV γ crossing率与能谱是多少？\n- 伞形片对MXC/pole源的实际视因子，而不是66%假设，是多少？\n- 每次壳内pair最终产生一个accepted W2事件的概率是多少，BGO内/外差多少？\n- W、Bi或主动高Z方案的自身活化与511线贡献能否守住新增预算？\n- 近场被动层是否应改为可读出的anticoincidence或add-back，而不是无源壳？"""

    artifact = {
        "surface": "report",
        "manifest": {
            "version": 1,
            "surface": "report",
            "title": title,
            "description": "Technical screening report for SE3 TES-nearfield high-energy gamma and passive-shield trade-offs.",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "sources": sources,
            "cards": [
                {"id": "card_high_gamma", "dataset": "kpis", "sourceId": "src_analysis", "description": "Flux-weighted share of corrected atmospheric gamma source above the nuclear-field pair threshold.", "metrics": [{"label": ">1.022 MeV源级占比", "field": "high_gamma_fraction", "format": "percent"}, {"label": "高能γ flux (cm⁻² s⁻¹)", "field": "high_gamma_flux_cm2_s", "format": "number"}]},
                {"id": "card_prompt_pair", "dataset": "kpis", "sourceId": "src_analysis", "description": "Raw prompt W2 pair/annihilation background before and after the existing active veto.", "metrics": [{"label": "prompt pair veto后 (cps)", "field": "prompt_pair_post_veto_cps", "format": "number"}, {"label": "veto前 (cps)", "field": "prompt_pair_pre_veto_cps", "format": "number"}]},
                {"id": "card_final_background", "dataset": "kpis", "sourceId": "src_analysis", "description": "Day-15 final delayed W2 central rate; all retained lineage events are annihilation-tagged and none are pair-tagged.", "metrics": [{"label": "day15最终本底 (cps)", "field": "day15_final_background_cps", "format": "number"}, {"label": "lineage事件数", "field": "final_lineage_events", "format": "number"}]},
                {"id": "card_f3", "dataset": "kpis", "sourceId": "src_analysis", "description": "Current SE3 Plan1 20-day central minimum distinguishable flux and folded background denominator.", "metrics": [{"label": "SE3 F3 (ph cm⁻² s⁻¹)", "field": "current_f3", "format": "number"}, {"label": "20日本底counts", "field": "background_counts_20d", "format": "number"}]},
            ],
            "charts": [
                {"id": "chart_energy_bands", "title": "Corrected atmospheric gamma source flux by energy band", "subtitle": "Source-level flux; not a TES-nearfield surface tally", "showDescription": True, "intent": "composition", "question": "How much of the corrected atmospheric gamma source is pair-capable, and where is it in energy?", "rationale": "A category bar makes the broad energy-tail composition visible without implying a measured nearfield spectrum.", "type": "bar", "dataset": "energy_bands", "sourceId": "src_spectrum", "encodings": {"x": {"field": "energy_band", "type": "ordinal", "label": "Energy band"}, "y": {"field": "flux_cm2_s", "type": "quantitative", "label": "Flux", "unit": "cm⁻² s⁻¹"}, "tooltip": [{"field": "share_total", "type": "quantitative", "format": "percent", "label": "Share of total"}, {"field": "is_pair_capable", "type": "nominal", "label": "Pair-capable"}]}, "valueFormat": "number", "unit": "cm⁻² s⁻¹", "layout": "full", "palette": {"kind": "sequential", "name": "blue"}, "settings": {"sort": "none", "showValues": True, "categoryLabelPolicy": "wrap"}, "surface": {"surface": "card", "viewMode": "visualization"}},
                {"id": "chart_volume_share", "title": "Final delayed W2 background share by source volume", "subtitle": "Day-15 central rate; 47 selected lineage rows, sorted by contribution", "showDescription": True, "intent": "composition", "question": "Which nearfield structures source the accepted delayed 511-keV background?", "rationale": "A ranked horizontal bar supports source-shadow layout decisions while retaining the low-count denominator.", "type": "horizontalBar", "dataset": "source_volumes", "sourceId": "src_lineage", "encodings": {"x": {"field": "display_volume", "type": "nominal", "label": "Source volume"}, "y": {"field": "share_final", "type": "quantitative", "format": "percent", "label": "Share of final background"}, "tooltip": [{"field": "rate_cps", "type": "quantitative", "label": "Rate", "unit": "cps"}, {"field": "selected_event_rows", "type": "quantitative", "label": "Selected rows"}]}, "valueFormat": "percent", "layout": "full", "palette": {"kind": "sequential", "name": "blue"}, "settings": {"sort": "descending", "showValues": True, "categoryLabelPolicy": "wrap"}, "surface": {"surface": "card", "viewMode": "visualization"}},
                {"id": "chart_w_tradeoff", "title": "Ideal W-shield F3 ratio by thickness", "subtitle": "Diffuse 511 transmission, s=1 and no new pair/activation; 0.75 line marks 25% improvement", "showDescription": True, "intent": "comparison", "question": "Can a windowed full sleeve or directional umbrella reach a 25% F3 improvement before new backgrounds?", "rationale": "An ordered multi-series line exposes thickness sensitivity and the target crossing.", "type": "line", "dataset": "shield_curve", "sourceId": "src_tradeoff", "encodings": {"x": {"field": "thickness_mm", "type": "quantitative", "label": "W thickness", "unit": "mm"}, "y": {"fields": ["full_windowed_f3_ratio_no_new", "umbrella_f3_ratio_no_new"], "type": "quantitative", "label": "F3 new / F3 current"}, "tooltip": [{"field": "diffuse_transmission_511", "type": "quantitative", "format": "percent", "label": "Diffuse 511 transmission"}, {"field": "full_25pct_new511_budget_counts20d", "type": "quantitative", "label": "Full-sleeve new-511 budget", "unit": "counts/20d"}]}, "valueFormat": "number", "layout": "full", "palette": {"kind": "categorical", "name": "blue-orange"}, "legend": {"position": "bottom", "sort": "spec", "title": "Layout"}, "referenceLines": [{"axis": "y", "value": 0.75, "label": "25% improvement target", "color": "neutral", "lineStyle": "dashed"}], "settings": {"showPoints": "always"}, "surface": {"surface": "card", "viewMode": "visualization"}},
            ],
            "tables": [
                {"id": "table_budgets", "title": "Selected shield points and 25% new-511 budget", "subtitle": "Positive budget leaves room for accepted pair/activation background; negative means ideal shielding alone misses the target", "showDescription": True, "dataset": "selected_budgets", "sourceId": "src_budgets", "density": "dense", "defaultSort": {"field": "new511_budget_counts20d_for_25pct", "direction": "desc"}, "columns": [{"field": "layout_label", "label": "Layout", "type": "text"}, {"field": "material", "label": "Material", "type": "text"}, {"field": "thickness_mm", "label": "mm", "format": "number"}, {"field": "ideal_f3_ratio_no_new", "label": "Ideal F3 ratio", "format": "number"}, {"field": "new511_budget_counts20d_for_25pct", "label": "New-511 budget / 20d", "format": "number"}]},
                {"id": "table_materials", "title": "511 attenuation and high-energy pair probability", "subtitle": "Normal-incidence 1 mm layer; pair is the probability that the first interaction is pair production", "showDescription": True, "dataset": "materials", "sourceId": "src_xcom", "density": "dense", "defaultSort": {"field": "normal_511_attenuation_1mm", "direction": "desc"}, "columns": [{"field": "material", "label": "Material", "type": "text"}, {"field": "hvl_511_mm", "label": "511 HVL (mm)", "format": "number"}, {"field": "normal_511_attenuation_1mm", "label": "511 atten. / 1 mm", "format": "percent"}, {"field": "pair_first_10MeV_1mm", "label": "Pair @10 MeV", "format": "percent"}, {"field": "pair_first_20MeV_1mm", "label": "Pair @20 MeV", "format": "percent"}]},
                {"id": "table_candidates", "title": "Layout decision matrix", "subtitle": "Ranking separates pair-veto topology from expected role", "showDescription": True, "dataset": "candidates", "sourceId": "src_candidates", "density": "spacious", "defaultSort": {"field": "decision", "direction": "asc"}, "columns": [{"field": "layout", "label": "Layout", "type": "text"}, {"field": "pair_veto_position", "label": "Pair/veto topology", "type": "text"}, {"field": "decision", "label": "Decision", "type": "text"}]},
            ],
            "blocks": [
                {"id": "title", "type": "markdown", "body": f"# {title}"},
                {"id": "technical_summary", "type": "markdown", "body": summary_body, "sourceId": "src_analysis"},
                {"id": "headline_metrics", "type": "metric-strip", "cardIds": ["card_high_gamma", "card_prompt_pair", "card_final_background", "card_f3"]},
                {"id": "finding_source_spectrum", "type": "markdown", "body": findings_body, "sourceId": "src_analysis"},
                {"id": "energy_bands_visual", "type": "chart", "chartId": "chart_energy_bands"},
                {"id": "finding_lineage", "type": "markdown", "body": lineage_body, "sourceId": "src_analysis"},
                {"id": "volume_visual", "type": "chart", "chartId": "chart_volume_share"},
                {"id": "finding_budget", "type": "markdown", "body": budget_body, "sourceId": "src_analysis"},
                {"id": "tradeoff_visual", "type": "chart", "chartId": "chart_w_tradeoff"},
                {"id": "budget_table", "type": "table", "tableId": "table_budgets"},
                {"id": "finding_material", "type": "markdown", "body": material_body, "sourceId": "src_analysis"},
                {"id": "material_table", "type": "table", "tableId": "table_materials"},
                {"id": "finding_layout", "type": "markdown", "body": layout_body, "sourceId": "src_analysis"},
                {"id": "candidate_table", "type": "table", "tableId": "table_candidates"},
                {"id": "scope", "type": "markdown", "body": scope_body, "sourceId": "src_analysis"},
                {"id": "methods", "type": "markdown", "body": methods_body, "sourceId": "src_notebook"},
                {"id": "limitations", "type": "markdown", "body": limitation_body, "sourceId": "src_analysis"},
                {"id": "next_steps", "type": "markdown", "body": next_body, "sourceId": "src_analysis"},
                {"id": "further_questions", "type": "markdown", "body": questions_body},
            ],
        },
        "snapshot": {
            "version": 1,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "status": "ready",
            "datasets": {
                **datasets,
            },
        },
        "sources": sources,
    }
    write_json(output / "artifact.json", artifact)


def build_source_notes(output: Path, analysis: dict[str, Any]) -> None:
    notes = f"""# Source and QA notes\n\n- Audience: technical.\n- Delivery mode: portable HTML fallback because no MCP artifact validator/renderer tool is callable in this runtime.\n- Production SIM access: forbidden; opened inputs are corrected source spectra and retained small CSV/JSON/PKL artifacts only.\n- Requested but unavailable metric: exact >1.022 MeV gamma crossing count/rate/spectrum at TES-nearfield surfaces. Required follow-up: paired lightweight stepping scorer.\n- Report sections map the technical specification as follows: title; technical summary; three visual-evidence findings; scope/definitions; methodology; limitations/robustness; recommended next steps; further questions.\n\n## Chart map\n\n1. Source-spectrum finding — bar — energy band vs flux; supports the source-level high-energy boundary, not a nearfield claim. Palette: single blue root.\n2. Final delayed lineage — horizontal bar — source volume vs final-rate share; supports directional shielding priority. Palette: single blue root.\n3. Shield trade-off — two-series line with 0.75 reference — W thickness vs ideal F3 ratio; supports full-sleeve versus umbrella screening. Palette: blue/orange with dashed neutral target.\n\n## Modeling assumptions\n\n- Full sleeve external source share: {analysis['shield_model']['external_source_share_day15']:.6f}; coverage factor 0.90.\n- Umbrella target source share: {analysis['shield_model']['umbrella_target_source_share_day15']:.6f}; view/coverage factor 0.66.\n- Main curves set signal survival to 1 and new pair/activation background to zero.\n- Diffuse transmission is a Lambert-flux-weighted slab model; normal-incidence transmission is retained in the CSV as a sensitivity reference.\n- New-511 cps budgets assume the new component follows the same 20-day temporal normalization only for compact screening; final decisions require explicit mission folding.\n\n## External physics sources\n\n- NIST XCOM: https://physics.nist.gov/PhysRefData/Xcom/html/xcom1.html\n- NIST pair thresholds/high-energy notes: https://www.physics.nist.gov/PhysRefData/FFast/Text2000/sec08.html\n- Geant4 gamma conversion model: https://geant4.web.cern.ch/documentation/pipelines/master/prm_html/PhysicsReferenceManual/electromagnetic/gamma_incident/gammaconversion/conv.html\n"""
    (output / "SOURCE_NOTES.md").write_text(notes, encoding="utf-8")


def build(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    output.mkdir(parents=True)
    analysis = compute_analysis(REPO)
    write_json(output / "analysis_summary.json", analysis)
    write_csv(output / "source_energy_bands.csv", analysis["source_spectrum"]["bands"])
    write_csv(output / "material_pair_tradeoff.csv", analysis["materials"])
    write_csv(output / "shield_layout_tradeoff.csv", analysis["shield_model"]["curve"])
    write_csv(output / "shield_budget_points.csv", analysis["shield_model"]["budgets"])
    write_csv(output / "source_volume_shares.csv", analysis["event_evidence"]["volume_rows"])
    write_csv(output / "candidate_matrix.csv", analysis["shield_model"]["candidates"])
    build_notebook(output)
    build_report_db(output, analysis)
    build_artifact(output, analysis)
    build_source_notes(output, analysis)
    return analysis


def self_test() -> None:
    assert math.isclose(diffuse_transmission(0.0, 1.0), 1.0)
    assert diffuse_transmission(2.5, 2.0) < diffuse_transmission(2.5, 1.0) < 1.0
    points = [(0.0, 0.0), (1.0, 2.0), (2.0, 0.0)]
    assert math.isclose(integrate_linear(points, 0.0, 2.0), 2.0)
    assert math.isclose(integrate_linear(points, 0.5, 1.5), 1.5)
    analysis = compute_analysis(REPO)
    assert analysis["data_quality"]["nearfield_surface_crossing_count_available"] is False
    print(json.dumps({"status": "PASS__SE3_NEARFIELD_TRADEOFF_SELF_TEST", "SIM_accessed": False, "high_gamma_fraction": analysis["source_spectrum"]["high_gamma_fraction"], "final_pair_events": analysis["event_evidence"]["final_pair_events"]}, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--build", action="store_true")
    action.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=FINAL_OUTPUT)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    analysis = build(args.output.resolve())
    print(json.dumps({"status": "PASS__SE3_NEARFIELD_HIGH_ENERGY_GAMMA_TRADEOFF_BUILT", "output": str(args.output.resolve()), "SIM_accessed": False, "high_gamma_fraction": analysis["source_spectrum"]["high_gamma_fraction"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
