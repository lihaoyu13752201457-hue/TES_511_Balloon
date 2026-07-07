#!/usr/bin/env python3
"""Build a 10-file GPT-readable complement package for W2 ingress/veto/BPE evidence."""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
PREV = ROOT / "engineering/geometry_optimization_20260704/07_clue_1p5e5_20260707"
OUT = ROOT / "engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707"

RAY_EVENTS = WORK / "w2_all_particle_ray_overlay_events.csv"
ANGLE_EVENTS = WORK / "angle_depth_audit_20260707/w2_incident_angle_events.csv"
ENTRY_COUNTS = WORK / "angle_depth_audit_20260707/w2_entry_class_counts.csv"
NEUTRON_W2_DEPTH = WORK / "angle_depth_audit_20260707/w2_neutron_energy_depth_with_entry.csv"
ANGLE_SUMMARY = WORK / "angle_depth_audit_20260707/w2_angle_depth_summary.json"
VETO_SUMMARY = WORK / "veto_efficiency_summary.json"
NEUTRON_PLASTIC_SUMMARY = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/geo_opt_neutron_plastic_audit_summary.json"
PLASTIC_DIRECT = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_direct_rate_comparison.csv"
PLASTIC_BY_TAG = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_prompt_by_tag_comparison.csv"
ACTIVATION_CATEGORY = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/activation_category_comparison_groundstate_fixed.csv"
ACTIVATION_TOP_NUCLIDE = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/activation_top_nuclide_comparison_groundstate_fixed.csv"
ACTIVATION_TOP_VOLUME = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/activation_top_volume_comparison_groundstate_fixed.csv"

W2_WINDOW = "510.58-511.42 keV"
ACTIVE_THRESHOLD_KEV = 50.0

FILES = {
    "01_README_GPT_PARSE.md": "human-readable instructions and previous-package comparison",
    "02_fact_summary.json": "machine-readable headline facts, source definitions, and caveats",
    "03_w2_particle_trajectories_enriched.csv": "one row per W2 raw TES background event with geometry path and veto class",
    "04_w2_entry_geometry_counts.csv": "counts by particle and envelope-entry class, including window vs wall proxy",
    "05_w2_theta_phi_binned_counts.csv": "theta/phi histograms by particle and entry class",
    "06_w2_veto_cutflow_by_particle.csv": "plastic skin, non-plastic active, Compton/FoV, and final-pass counts by particle",
    "07_w2_event_veto_flags.csv": "one row per event with explicit veto flags and deposited veto energies",
    "08_plastic_skin_veto_effect.csv": "plastic-skin veto on/off and positron-hit evidence",
    "09_bpe_neutron_activation_effect.csv": "BPE/shield-stack neutron activation and neutron RPIP effect summary",
    "10_w2_neutron_energy_depth_events.csv": "W2 neutron energy versus first-hit depth proxy event table",
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def maybe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def maybe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def event_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (str(row.get("source_family") or ""), str(row.get("source_file") or ""), str(row.get("local_id") or ""))


def path_length_cm(row: dict[str, Any]) -> float | None:
    vals = [
        maybe_float(row.get("init_x_cm")),
        maybe_float(row.get("init_y_cm")),
        maybe_float(row.get("init_z_cm")),
        maybe_float(row.get("tes_x_cm")),
        maybe_float(row.get("tes_y_cm")),
        maybe_float(row.get("tes_z_cm")),
    ]
    if any(v is None for v in vals):
        return None
    ix, iy, iz, tx, ty, tz = [float(v) for v in vals]
    return math.sqrt((tx - ix) ** 2 + (ty - iy) ** 2 + (tz - iz) ** 2)


def veto_layer(row: dict[str, Any]) -> str:
    plastic = maybe_float(row.get("plastic_skin_keV")) or 0.0
    active = maybe_float(row.get("active_other_keV")) or 0.0
    side_pass = maybe_bool(row.get("side_compton_fov_pass"))
    if plastic >= ACTIVE_THRESHOLD_KEV:
        return "plastic_skin_veto"
    if active >= ACTIVE_THRESHOLD_KEV:
        return "non_plastic_active_veto"
    if side_pass is False:
        return "compton_fov_veto"
    return "final_pass"


def copy_selected_neutron_depth() -> None:
    rows = read_csv(NEUTRON_W2_DEPTH)
    fields = [
        "local_id",
        "status",
        "init_energy_keV",
        "depth_projection_cm",
        "depth_distance_cm",
        "entry_class",
        "entry_surface_proxy",
        "entry_region_proxy",
        "theta_local_deg",
        "phi_local_deg",
        "first_hit_category",
        "first_hit_volume",
        "plotted",
    ]
    write_csv(OUT / "10_w2_neutron_energy_depth_events.csv", rows, fields)


def build_trajectory_and_veto_files() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rays = read_csv(RAY_EVENTS)
    angles = {event_key(row): row for row in read_csv(ANGLE_EVENTS)}
    trajectories: list[dict[str, Any]] = []
    veto_flags: list[dict[str, Any]] = []

    for idx, row in enumerate(rays, start=1):
        angle = angles.get(event_key(row), {})
        merged = dict(row)
        merged.update(
            {
                "event_index": idx,
                "event_key": f"{row.get('source_family')}::{Path(str(row.get('source_file') or '')).name}::{row.get('local_id')}",
                "source_file_basename": Path(str(row.get("source_file") or "")).name,
                "entry_class": angle.get("entry_class"),
                "entry_surface_proxy": angle.get("entry_surface_proxy"),
                "entry_region_proxy": angle.get("entry_region_proxy"),
                "entry_phi_deg_local": angle.get("entry_phi_deg_local"),
                "theta_local_deg": angle.get("theta_local_deg"),
                "phi_local_deg": angle.get("phi_local_deg"),
                "xz_init_quadrant": angle.get("xz_init_quadrant"),
                "path_length_init_to_tes_cm": path_length_cm(row),
                "computed_veto_layer": veto_layer(row),
                "plastic_skin_veto_flag": (maybe_float(row.get("plastic_skin_keV")) or 0.0) >= ACTIVE_THRESHOLD_KEV,
                "non_plastic_active_veto_flag": (maybe_float(row.get("active_other_keV")) or 0.0) >= ACTIVE_THRESHOLD_KEV,
                "compton_fov_veto_flag": maybe_bool(row.get("side_compton_fov_pass")) is False,
                "final_pass_flag": veto_layer(row) == "final_pass",
            }
        )
        trajectories.append(merged)
        veto_flags.append(
            {
                "event_index": idx,
                "source_family": row.get("source_family"),
                "stream": row.get("stream"),
                "local_id": row.get("local_id"),
                "source_file_basename": merged["source_file_basename"],
                "tes_total_keV": row.get("tes_total_keV"),
                "entry_class": merged["entry_class"],
                "plastic_skin_keV": row.get("plastic_skin_keV"),
                "active_other_keV": row.get("active_other_keV"),
                "side_compton_class": row.get("side_compton_class"),
                "side_compton_fov_pass": row.get("side_compton_fov_pass"),
                "plastic_skin_veto_flag": merged["plastic_skin_veto_flag"],
                "non_plastic_active_veto_flag": merged["non_plastic_active_veto_flag"],
                "compton_fov_veto_flag": merged["compton_fov_veto_flag"],
                "veto_priority_layer": merged["computed_veto_layer"],
                "final_pass_flag": merged["final_pass_flag"],
                "note": "priority is plastic_skin, then non_plastic_active, then Compton/FoV, then final pass",
            }
        )

    trajectory_fields = [
        "event_index",
        "event_key",
        "source_family",
        "stream",
        "local_id",
        "source_file_basename",
        "tes_total_keV",
        "init_energy_keV",
        "init_x_cm",
        "init_y_cm",
        "init_z_cm",
        "dir_x",
        "dir_y",
        "dir_z",
        "theta_local_deg",
        "phi_local_deg",
        "entry_class",
        "entry_surface_proxy",
        "entry_region_proxy",
        "entry_phi_deg_local",
        "xz_init_quadrant",
        "first_hit_volume",
        "first_hit_category",
        "tes_x_cm",
        "tes_y_cm",
        "tes_z_cm",
        "path_length_init_to_tes_cm",
        "plastic_skin_keV",
        "active_other_keV",
        "side_compton_class",
        "side_compton_fov_pass",
        "computed_veto_layer",
        "final_pass_flag",
    ]
    veto_fields = [
        "event_index",
        "source_family",
        "stream",
        "local_id",
        "source_file_basename",
        "tes_total_keV",
        "entry_class",
        "plastic_skin_keV",
        "active_other_keV",
        "side_compton_class",
        "side_compton_fov_pass",
        "plastic_skin_veto_flag",
        "non_plastic_active_veto_flag",
        "compton_fov_veto_flag",
        "veto_priority_layer",
        "final_pass_flag",
        "note",
    ]
    write_csv(OUT / "03_w2_particle_trajectories_enriched.csv", trajectories, trajectory_fields)
    write_csv(OUT / "07_w2_event_veto_flags.csv", veto_flags, veto_fields)
    return trajectories, veto_flags


def build_entry_counts(trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base = read_csv(ENTRY_COUNTS)
    rows: list[dict[str, Any]] = []
    total_by_family = Counter(str(row["source_family"]) for row in trajectories)
    for row in base:
        family = row["source_family"]
        count = int(float(row["count"]))
        rows.append(
            {
                "source_family": family,
                "entry_class": row["entry_class"],
                "count": count,
                "share_within_particle": row["share"],
                "total_w2_raw_events_for_particle": total_by_family[family],
                "definition": "side_window is side-envelope entry within +/-15 deg of local negative-X side-window axis; side_wall is other side entry",
            }
        )
    write_csv(
        OUT / "04_w2_entry_geometry_counts.csv",
        rows,
        ["source_family", "entry_class", "count", "share_within_particle", "total_w2_raw_events_for_particle", "definition"],
    )
    return rows


def build_theta_phi_binned_counts(trajectories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    bins = {"theta_local_deg": list(range(0, 181, 10)), "phi_local_deg": list(range(0, 361, 30))}
    for angle_field, edges in bins.items():
        angle_kind = "theta" if angle_field.startswith("theta") else "phi"
        for family in sorted({str(r["source_family"]) for r in trajectories}):
            for entry in sorted({str(r.get("entry_class") or "unknown") for r in trajectories if str(r["source_family"]) == family}):
                vals = [
                    maybe_float(r.get(angle_field))
                    for r in trajectories
                    if str(r["source_family"]) == family and str(r.get("entry_class") or "unknown") == entry
                ]
                vals = [float(v) for v in vals if v is not None]
                for lo, hi in zip(edges[:-1], edges[1:]):
                    count = sum(1 for v in vals if lo <= v < hi or (hi == edges[-1] and lo <= v <= hi))
                    if count:
                        rows.append(
                            {
                                "angle_kind": angle_kind,
                                "source_family": family,
                                "entry_class": entry,
                                "bin_lo_deg": lo,
                                "bin_hi_deg": hi,
                                "count": count,
                            }
                        )
    write_csv(OUT / "05_w2_theta_phi_binned_counts.csv", rows, ["angle_kind", "source_family", "entry_class", "bin_lo_deg", "bin_hi_deg", "count"])
    return rows


def build_veto_cutflow(veto_flags: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for family in sorted({str(r["source_family"]) for r in veto_flags}):
        part = [r for r in veto_flags if str(r["source_family"]) == family]
        raw = len(part)
        plastic = sum(1 for r in part if r["veto_priority_layer"] == "plastic_skin_veto")
        active = sum(1 for r in part if r["veto_priority_layer"] == "non_plastic_active_veto")
        compton = sum(1 for r in part if r["veto_priority_layer"] == "compton_fov_veto")
        final_pass = sum(1 for r in part if r["veto_priority_layer"] == "final_pass")
        rows.append(
            {
                "source_family": family,
                "w2_raw_events": raw,
                "plastic_skin_veto_events": plastic,
                "non_plastic_active_veto_events": active,
                "compton_fov_veto_events": compton,
                "final_pass_events": final_pass,
                "plastic_skin_veto_fraction_of_raw": plastic / raw if raw else None,
                "non_plastic_active_veto_fraction_of_raw": active / raw if raw else None,
                "compton_fov_veto_fraction_of_raw": compton / raw if raw else None,
                "final_pass_fraction_of_raw": final_pass / raw if raw else None,
            }
        )
    write_csv(
        OUT / "06_w2_veto_cutflow_by_particle.csv",
        rows,
        [
            "source_family",
            "w2_raw_events",
            "plastic_skin_veto_events",
            "non_plastic_active_veto_events",
            "compton_fov_veto_events",
            "final_pass_events",
            "plastic_skin_veto_fraction_of_raw",
            "non_plastic_active_veto_fraction_of_raw",
            "compton_fov_veto_fraction_of_raw",
            "final_pass_fraction_of_raw",
        ],
    )
    return rows


def build_plastic_effect(veto_cutflow: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary = read_json(NEUTRON_PLASTIC_SUMMARY)
    rows: list[dict[str, Any]] = []
    for row in read_csv(PLASTIC_DIRECT):
        if row["window"] in {"w2", "w2_510p58_511p42"} or row["window"].startswith("w2"):
            rows.append(
                {
                    "topic": "plastic_on_off_direct_rate",
                    "metric": f"{row['window']} {row['stream']} {row['stage']}",
                    "value": row.get("relative_change_percent"),
                    "unit": "percent change plastic_on vs plastic_off",
                    "count_or_rate_context": f"on={row.get('plastic_on_rate_s-1')} cps/off={row.get('plastic_off_rate_s-1')} cps/delta={row.get('on_minus_off_rate_s-1')} cps",
                    "interpretation": "plastic_off excludes GeoOpt plastic from veto accounting but keeps material in transport",
                }
            )
    eplus = summary["plastic_veto"]["eplus_plastic_hits"]
    matched = summary["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]
    for metric, value in eplus["counts"].items():
        rows.append(
            {
                "topic": "eplus_plastic_hit_counts",
                "metric": metric,
                "value": value,
                "unit": "events",
                "count_or_rate_context": "",
                "interpretation": "prompt e+ SIM scan; all energies, not only W2 TES candidates",
            }
        )
    for metric, value in matched["counts"].items():
        rows.append(
            {
                "topic": "w2_eplus_matched_plastic_only_veto",
                "metric": metric,
                "value": value,
                "unit": "events",
                "count_or_rate_context": json.dumps(matched["rates"], sort_keys=True),
                "interpretation": "W2 prompt e+ TES candidates; plastic-only veto means vetoed only if plastic is counted active",
            }
        )
    for row in veto_cutflow:
        rows.append(
            {
                "topic": "current_w2_event_level_plastic_veto",
                "metric": f"{row['source_family']}_plastic_skin_veto_events",
                "value": row["plastic_skin_veto_events"],
                "unit": "W2 raw TES events",
                "count_or_rate_context": f"raw={row['w2_raw_events']}, fraction={row['plastic_skin_veto_fraction_of_raw']}",
                "interpretation": "event-level W2 priority veto classification in complement trajectory table",
            }
        )
    write_csv(OUT / "08_plastic_skin_veto_effect.csv", rows, ["topic", "metric", "value", "unit", "count_or_rate_context", "interpretation"])
    return rows


def build_bpe_effect() -> list[dict[str, Any]]:
    summary = read_json(NEUTRON_PLASTIC_SUMMARY)
    act = summary["activation"]["summary"]
    nsum = summary["neutron_energy_depth"]["summary"]
    rows: list[dict[str, Any]] = [
        {
            "topic": "activation_total",
            "metric": "fixed_total_activity",
            "mass_model_value": act["mass_fixed_total_activity_Bq"],
            "geo_opt_value": act["geo_fixed_total_activity_Bq"],
            "geo_over_mass": act["geo_fixed_total_activity_Bq"] / act["mass_fixed_total_activity_Bq"],
            "relative_change_percent": 100.0 * (act["geo_fixed_total_activity_Bq"] / act["mass_fixed_total_activity_Bq"] - 1.0),
            "unit": "Bq",
            "interpretation": "GeoOpt S1/BPE/W5 stack lowers fixed day-15 activation versus Mass_model_511",
        },
        {
            "topic": "activation_internal",
            "metric": "internal_activity_excluding_added_geoopt_layers",
            "mass_model_value": act["mass_internal_Bq"],
            "geo_opt_value": act["geo_internal_excluding_added_layers_Bq"],
            "geo_over_mass": act["geo_internal_excluding_added_layers_Bq"] / act["mass_internal_Bq"],
            "relative_change_percent": 100.0 * (act["geo_internal_excluding_added_layers_Bq"] / act["mass_internal_Bq"] - 1.0),
            "unit": "Bq",
            "interpretation": "Internal activation is reduced, but this is stack-level evidence, not isolated BPE-only causality",
        },
        {
            "topic": "activation_CsI",
            "metric": "CsI_activity",
            "mass_model_value": act["mass_CsI_Bq"],
            "geo_opt_value": act["geo_CsI_Bq"],
            "geo_over_mass": act["geo_CsI_Bq"] / act["mass_CsI_Bq"],
            "relative_change_percent": 100.0 * (act["geo_CsI_Bq"] / act["mass_CsI_Bq"] - 1.0),
            "unit": "Bq",
            "interpretation": "CsI activation reduction is consistent with neutron-shielding benefit",
        },
        {
            "topic": "added_layers_activity",
            "metric": "geo_added_layers_activity",
            "mass_model_value": "",
            "geo_opt_value": act["geo_added_layers_Bq"],
            "geo_over_mass": "",
            "relative_change_percent": "",
            "unit": "Bq",
            "interpretation": "Activity created inside added GeoOpt layers themselves",
        },
        {
            "topic": "neutron_rpip",
            "metric": "weighted_internal_rpip_points",
            "mass_model_value": nsum["mass"]["weighted_internal_rpip_points"],
            "geo_opt_value": nsum["geo"]["weighted_internal_rpip_points"],
            "geo_over_mass": nsum["geo"]["weighted_internal_rpip_points"] / nsum["mass"]["weighted_internal_rpip_points"],
            "relative_change_percent": 100.0 * (nsum["geo"]["weighted_internal_rpip_points"] / nsum["mass"]["weighted_internal_rpip_points"] - 1.0),
            "unit": "weighted RPIP points",
            "interpretation": "Neutron interaction proxy count in internal materials is lower in GeoOpt stack",
        },
        {
            "topic": "neutron_rpip",
            "metric": "weighted_CsI_rpip_points",
            "mass_model_value": nsum["mass"]["weighted_CsI_rpip_points"],
            "geo_opt_value": nsum["geo"]["weighted_CsI_rpip_points"],
            "geo_over_mass": nsum["geo"]["weighted_CsI_rpip_points"] / nsum["mass"]["weighted_CsI_rpip_points"],
            "relative_change_percent": 100.0 * (nsum["geo"]["weighted_CsI_rpip_points"] / nsum["mass"]["weighted_CsI_rpip_points"] - 1.0),
            "unit": "weighted RPIP points",
            "interpretation": "CsI neutron interaction proxy count is lower in GeoOpt stack",
        },
        {
            "topic": "causality_caveat",
            "metric": "BPE_only_AB_test",
            "mass_model_value": "",
            "geo_opt_value": "",
            "geo_over_mass": "",
            "relative_change_percent": "",
            "unit": "",
            "interpretation": "No otherwise-identical no-BPE transport was run; claim should be shield-stack effect, not pure BPE-only proof",
        },
    ]
    for row in read_csv(ACTIVATION_CATEGORY):
        rows.append(
            {
                "topic": "activation_category_csv",
                "metric": row["metric"],
                "mass_model_value": row["mass_model_Bq"],
                "geo_opt_value": row["geo_opt_Bq"],
                "geo_over_mass": row["geo_over_mass"],
                "relative_change_percent": row["relative_change_percent"],
                "unit": "Bq",
                "interpretation": "copied from activation_category_comparison_groundstate_fixed.csv",
            }
        )
    for source_name, topic in ((ACTIVATION_TOP_NUCLIDE, "activation_top_nuclides"), (ACTIVATION_TOP_VOLUME, "activation_top_volumes")):
        for row in read_csv(source_name)[:8]:
            rows.append(
                {
                    "topic": topic,
                    "metric": row.get("nuclide") or row.get("VN"),
                    "mass_model_value": row["mass_model_Bq"],
                    "geo_opt_value": row["geo_opt_Bq"],
                    "geo_over_mass": row["geo_over_mass"],
                    "relative_change_percent": row["relative_change_percent"],
                    "unit": "Bq",
                    "interpretation": row.get("category") or "top contributor",
                }
            )
    write_csv(
        OUT / "09_bpe_neutron_activation_effect.csv",
        rows,
        ["topic", "metric", "mass_model_value", "geo_opt_value", "geo_over_mass", "relative_change_percent", "unit", "interpretation"],
    )
    return rows


def build_fact_summary(
    trajectories: list[dict[str, Any]],
    entry_counts: list[dict[str, Any]],
    veto_cutflow: list[dict[str, Any]],
    bpe_rows: list[dict[str, Any]],
    plastic_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    angle_summary = read_json(ANGLE_SUMMARY)
    veto_summary = read_json(VETO_SUMMARY)
    previous_files = [p.name for p in sorted(PREV.iterdir()) if p.is_file()]
    package_files = [{"file": name, "purpose": purpose} for name, purpose in FILES.items()]
    return {
        "package": "09_gpt_complement_ingress_veto_bpe_20260707",
        "status": "PASS_GPT_COMPLEMENT_PACKAGE_BUILT",
        "created_for": "external GPT review",
        "scope": "W2 510.58-511.42 keV raw TES background candidates and post-processing audits; no new transport run.",
        "previous_10_file_package_reviewed": {
            "path": rel(PREV),
            "files": previous_files,
            "complement_strategy": "Previous package emphasized budget/levers/geometry images. This package emphasizes event-level trajectory, entry geometry, veto flags, and BPE/plastic audit tables.",
        },
        "package_file_count": len(package_files),
        "package_files": package_files,
        "w2_event_counts_by_particle": dict(sorted(Counter(str(r["source_family"]) for r in trajectories).items())),
        "veto_priority_definition": [
            "plastic_skin_veto if GeoOpt_S1_PlasticFullWrap* edep >= 50 keV",
            "non_plastic_active_veto if CsI/BGO/other active edep >= 50 keV and not plastic veto",
            "compton_fov_veto if side_compton_fov_pass is false and no active veto",
            "final_pass otherwise",
        ],
        "entry_definition": angle_summary["angle_definition"],
        "atm511_source_definition": angle_summary["atm511_source_definition"],
        "entry_counts_by_source_family": angle_summary["entry_counts_by_source_family"],
        "atm511_w2_conditional_diagnostics": angle_summary["atm511_w2_conditional_diagnostics"],
        "veto_summary_source": rel(VETO_SUMMARY),
        "veto_efficiency_summary": veto_summary,
        "bpe_effect_key_rows": [r for r in bpe_rows if r["topic"] in {"activation_total", "activation_internal", "activation_CsI", "neutron_rpip", "causality_caveat"}],
        "plastic_effect_key_rows": [r for r in plastic_rows if r["topic"] in {"w2_eplus_matched_plastic_only_veto", "current_w2_event_level_plastic_veto"}],
        "major_caveats": [
            "BPE effect is not isolated by a no-BPE A/B transport; current evidence is for the S1/BPE/W5 shield stack.",
            "Plastic-off means post-processing veto accounting off; plastic material remains in transport.",
            "Entry window is a proxy based on envelope crossing near local negative-X side-window axis, not a CAD boundary scorer.",
            "Neutron depth table uses first-hit depth proxy, not continuous energy-loss-vs-depth scoring.",
        ],
    }


def write_readme(summary: dict[str, Any]) -> None:
    lines = [
        "# GPT Complement Package: W2 Ingress, Veto, BPE Evidence",
        "",
        "This directory intentionally contains exactly 10 files for upload to GPT.",
        "It complements the previous `07_clue_1p5e5_20260707` 10-file package, which focused on the 20-day background budget, high-level levers, and geometry visuals.",
        "",
        "## What This Adds",
        "",
        "- Event-level W2 particle trajectory rows: source point, direction, first recorded volume, TES centroid, and entry proxy.",
        "- Explicit separation of `side_window` versus `side_wall` ingress proxy.",
        "- Event-level veto flags for plastic-skin veto, non-plastic active veto, and Compton/FoV veto.",
        "- Plastic-skin veto on/off evidence and e+ plastic-hit evidence.",
        "- BPE/shield-stack activation and neutron-interaction proxy evidence versus Mass_model_511.",
        "",
        "## Read Order For GPT",
        "",
        "1. `02_fact_summary.json` for headline facts and caveats.",
        "2. `03_w2_particle_trajectories_enriched.csv` for the event-level ingress geometry.",
        "3. `06_w2_veto_cutflow_by_particle.csv` and `07_w2_event_veto_flags.csv` for veto behavior.",
        "4. `08_plastic_skin_veto_effect.csv` and `09_bpe_neutron_activation_effect.csv` for the plastic/BPE shield evidence.",
        "5. `10_w2_neutron_energy_depth_events.csv` for W2 neutron energy-depth proxy.",
        "",
        "## Important Definitions",
        "",
        "- W2 window: `510.58-511.42 keV` TES total energy.",
        "- Active threshold: `50 keV` deposited in a veto volume.",
        "- `side_window`: side-envelope entry within +/-15 deg of the local negative-X side-window axis.",
        "- `side_wall`: side-envelope entry outside that side-window proxy.",
        "- Veto priority: plastic skin, then non-plastic active, then Compton/FoV, then final pass.",
        "",
        "## Caveats",
        "",
    ]
    for caveat in summary["major_caveats"]:
        lines.append(f"- {caveat}")
    lines.extend(
        [
            "",
            "## Files",
            "",
        ]
    )
    for item in summary["package_files"]:
        lines.append(f"- `{item['file']}`: {item['purpose']}")
    (OUT / "01_README_GPT_PARSE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    trajectories, veto_flags = build_trajectory_and_veto_files()
    entry_counts = build_entry_counts(trajectories)
    build_theta_phi_binned_counts(trajectories)
    veto_cutflow = build_veto_cutflow(veto_flags)
    plastic_rows = build_plastic_effect(veto_cutflow)
    bpe_rows = build_bpe_effect()
    copy_selected_neutron_depth()
    summary = build_fact_summary(trajectories, entry_counts, veto_cutflow, bpe_rows, plastic_rows)
    (OUT / "02_fact_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(summary)

    files = sorted(p.name for p in OUT.iterdir() if p.is_file())
    if files != sorted(FILES):
        raise RuntimeError(f"package file mismatch: expected {sorted(FILES)}, got {files}")
    print(json.dumps({"status": "PASS", "output_dir": rel(OUT), "file_count": len(files), "files": files}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
