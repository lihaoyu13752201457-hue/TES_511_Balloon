#!/usr/bin/env python3
"""Smoke-test the delayed-activation distribution invariance assumption.

The current mission-time fold varies the delayed activation with a scalar
production driver and per-nuclide half-life ODE.  This script tests one
necessary condition for that approximation: when the local EXPACS/PARMA
environment moves along the synthetic balloon trajectory, particle-family
changes should not strongly remix the day-15 isotope/volume distribution.

This is intentionally a smoke test.  It does not rerun Geant4 activation
transport at every trajectory point.  Instead, it:

1. parses the existing full-stat activation-buildup isotope store by incident
   particle family;
2. maps the per-family RP yields to the fixed day-15 activity inventory;
3. evaluates local PARMA particle fluxes at the low-altitude, day-15, and
   high-altitude trajectory probes; and
4. reweights the per-family isotope/volume contribution by the PARMA family
   scale, then compares normalized nuclide and volume distributions.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
OUT_DIR = SCRIPT.parent
ROOT = SCRIPT.parents[3]

SECONDS_PER_DAY = 86400.0
DAY15 = 15.0
MISSION_DAYS = 20.0
STEP_DAY = 0.25
ALT_REF_KM = 38.75
LAT_REF_DEG = 34.0
LON_REF_DEG = 100.0
ALT_AMP_KM = 2.5
LAT_AMP_DEG = 0.25
LON_AMP_DEG = 0.25
SCALE_HEIGHT_KM = 6.8
DEPTH_AT_38KM_G_CM2 = 3.86509853156
PARMA_SOLAR_DATE = (2025, 8, 31)
PARMA_MU_BIN_WIDTH = 0.1
PARTICLES = ["gamma", "n", "p", "alpha", "eminus", "eplus", "muminus", "muplus"]

BUILDUP_DIR = ROOT / "runs" / "step02_buildup_v3p5_centerfinger_fullstat_v2"
GROUNDSTATE = ROOT / "runs" / "step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613" / "groundstate_activity_corrections.csv"
PARMA_EXE_CANDIDATES = [
    ROOT.parent / "COSMOSRAY_BALLOON_SIM" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
    ROOT.parent / "cosmosray_bg_2605" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
    ROOT.parent / "codex_tes_511_sim" / "COSMOSRAY_BALLOON_SIM" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
    ROOT.parent / "codex_tes_511_sim" / "cosmosray_bg_2605" / "external" / "expacs_parma" / "phase2_parma_grid_driver",
]

TT_RE = re.compile(r"^\s*TT\s+([-+0-9.eE]+)\s*$")
VN_RE = re.compile(r"^\s*VN\s+(\S+)\s*$")
RP_RE = re.compile(r"^\s*RP\s+(\d+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")
TAG_RE = re.compile(r"Background_(alpha|eminus|eplus|gamma|muminus|muplus|n|p)_")


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_tag(path: Path) -> str:
    match = TAG_RE.search(path.name)
    if not match:
        raise ValueError(f"Cannot parse particle tag from {path}")
    return match.group(1)


def is_gamma(tag: str) -> bool:
    return tag == "gamma"


def normalization_divisor(tag: str, gamma_file_count: int, non_gamma_div: float = 8.0) -> float:
    return float(max(1, gamma_file_count)) if is_gamma(tag) else float(non_gamma_div)


def vertical_depth_g_cm2(altitude_km: float) -> float:
    return DEPTH_AT_38KM_G_CM2 * math.exp(-(altitude_km - 38.0) / SCALE_HEIGHT_KM)


def bin_centers() -> list[float]:
    n = int(round(MISSION_DAYS / STEP_DAY))
    return [i * STEP_DAY for i in range(n + 1)]


def trajectory_row(day: float, idx: int) -> dict[str, float]:
    phase = 2.0 * math.pi * (day - DAY15)
    alt_offset = ALT_AMP_KM * math.sin(phase / 5.0)
    lat_offset = LAT_AMP_DEG * math.sin(phase / 7.0)
    lon_offset = LON_AMP_DEG * math.sin(phase / 9.0)
    altitude = ALT_REF_KM + alt_offset
    latitude = LAT_REF_DEG + lat_offset
    longitude = LON_REF_DEG + lon_offset
    return {
        "time_bin_id": float(idx),
        "day_mid": day,
        "altitude_km": altitude,
        "latitude_deg": latitude,
        "longitude_deg": longitude,
        "altitude_offset_km": alt_offset,
        "latitude_offset_deg": lat_offset,
        "longitude_offset_deg": lon_offset,
        "depth_g_cm2": vertical_depth_g_cm2(altitude),
    }


def trajectory_probes() -> list[dict[str, float | str]]:
    rows = [trajectory_row(day, idx) for idx, day in enumerate(bin_centers())]
    low = min(rows, key=lambda row: float(row["altitude_km"]))
    high = max(rows, key=lambda row: float(row["altitude_km"]))
    ref = min(rows, key=lambda row: abs(float(row["day_mid"]) - DAY15))
    out = [
        {"probe": "low_altitude", **low},
        {"probe": "day15_reference", **ref},
        {"probe": "high_altitude", **high},
    ]
    return out


def parma_driver() -> Path:
    for exe in PARMA_EXE_CANDIDATES:
        if exe.exists() and os.access(exe, os.X_OK):
            return exe
    raise FileNotFoundError("No local phase2_parma_grid_driver found")


def run_parma(exe: Path, row: dict[str, Any]) -> tuple[dict[str, float], list[dict[str, Any]]]:
    year, month, day = PARMA_SOLAR_DATE
    cmd = [
        str(exe),
        str(year),
        str(month),
        str(day),
        str(float(row["latitude_deg"])),
        str(float(row["longitude_deg"])),
        str(float(row["altitude_km"])),
        "10.0",
    ]
    proc = subprocess.run(cmd, cwd=str(exe.parent / "parma_cpp"), text=True, capture_output=True, check=True)
    meta: dict[str, float] = {}
    lines = [line for line in proc.stdout.splitlines() if line]
    reader: csv.DictReader[str] | None = None
    for idx, line in enumerate(lines):
        if line.startswith("META,"):
            _tag, w_index, rc_gv, depth = line.split(",")
            meta = {"W_index": float(w_index), "Rc_GV_parma": float(rc_gv), "depth_g_cm2_parma": float(depth)}
        if line.startswith("particle,"):
            reader = csv.DictReader(lines[idx:])
            break
    if reader is None:
        raise RuntimeError("PARMA driver returned no particle table")
    rows: list[dict[str, Any]] = []
    for item in reader:
        particle = item["particle"]
        angle_bin = int(item["angle_bin"])
        flux = max(float(item["differential_flux_cm2_s_sr_MeV"]), 0.0) * 2.0 * math.pi * PARMA_MU_BIN_WIDTH
        rows.append(
            {
                "particle": particle,
                "angle_bin": angle_bin,
                "direction": "down" if angle_bin < 10 else "up",
                "energy_bin": int(item["energy_bin"]),
                "energy_MeV": float(item["energy_MeV"]),
                "flux_proxy": flux,
            }
        )
    if not meta:
        raise RuntimeError("PARMA driver returned no META line")
    return meta, rows


def distribution(rows: list[dict[str, Any]], key_fields: tuple[str, ...]) -> dict[str, float]:
    vals: dict[str, float] = defaultdict(float)
    for row in rows:
        key = "|".join(str(row[field]) for field in key_fields)
        vals[key] += float(row["flux_proxy"])
    total = sum(vals.values())
    if total <= 0.0:
        return {}
    return {key: value / total for key, value in vals.items()}


def particle_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in rows:
        totals[str(row["particle"])] += float(row["flux_proxy"])
    return dict(totals)


def total_variation(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    return 0.5 * sum(abs(float(a.get(key, 0.0)) - float(b.get(key, 0.0))) for key in keys)


def classify_volume(vn: str) -> str:
    if vn.startswith("CsI"):
        return "CsI_active_shield"
    if vn.startswith("Ta_") or "Absorber" in vn:
        return "Ta_absorber_or_TES_plane"
    if vn.startswith("W_") or "_W_" in vn or "Tungsten" in vn:
        return "W_passive_collimator_or_liner"
    if vn.startswith("Cu") or "_Cu_" in vn or "Copper" in vn:
        return "Cu_cold_mass_or_liner"
    if vn.startswith("Al") or "_Al_" in vn:
        return "Al_shell_or_window"
    if "Kapton" in vn:
        return "Kapton_flex"
    if "ColdPlate" in vn or "Cryoperm" in vn or "Thermal" in vn:
        return "cryogenic_service_mass"
    return "other"


def parse_buildup_dat() -> tuple[dict[tuple[str, str, int], float], dict[str, Any]]:
    files = sorted(BUILDUP_DIR.glob("*.dat.inc1.dat"))
    if not files:
        raise FileNotFoundError(f"No buildup dat files in {BUILDUP_DIR}")
    gamma_files = sum(1 for path in files if parse_tag(path) == "gamma")
    by_particle_key: dict[tuple[str, str, int], float] = defaultdict(float)
    audit_by_tag: dict[str, dict[str, Any]] = {}
    for tag in PARTICLES:
        audit_by_tag[tag] = {"files": 0, "division": normalization_divisor(tag, gamma_files), "rp_scaled_total": 0.0}
    for path in files:
        tag = parse_tag(path)
        div = normalization_divisor(tag, gamma_files)
        audit_by_tag[tag]["files"] += 1
        cur_vn: str | None = None
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if TT_RE.match(line):
                    continue
                m_vn = VN_RE.match(line)
                if m_vn:
                    cur_vn = m_vn.group(1)
                    continue
                m_rp = RP_RE.match(line)
                if not m_rp or cur_vn is None:
                    continue
                za = int(m_rp.group(1))
                exc = float(m_rp.group(2))
                if abs(exc) > 1.0e-6:
                    continue
                val = float(m_rp.group(3)) / div
                by_particle_key[(tag, cur_vn, za)] += val
                audit_by_tag[tag]["rp_scaled_total"] += val
    return by_particle_key, {"dat_files": len(files), "gamma_files": gamma_files, "by_tag": audit_by_tag}


def load_activity_scale(by_particle_key: dict[tuple[str, str, int], float]) -> tuple[dict[tuple[str, int], float], dict[str, Any]]:
    total_yield: dict[tuple[str, int], float] = defaultdict(float)
    for (_tag, vn, za), value in by_particle_key.items():
        total_yield[(vn, za)] += value
    scale: dict[tuple[str, int], float] = {}
    matched_activity = 0.0
    unmatched_activity = 0.0
    rows = read_csv(GROUNDSTATE)
    for row in rows:
        key = (row["VN"], int(row["ZA"]))
        activity = float(row["new_groundstate_activity_Bq"])
        y = total_yield.get(key, 0.0)
        if y > 0.0 and activity > 0.0:
            scale[key] = activity / y
            matched_activity += activity
        else:
            unmatched_activity += activity
    return scale, {
        "groundstate_rows": len(rows),
        "matched_activity_Bq": matched_activity,
        "unmatched_activity_Bq": unmatched_activity,
        "matched_fraction": matched_activity / (matched_activity + unmatched_activity) if matched_activity + unmatched_activity > 0.0 else 0.0,
    }


def activity_contributions(
    by_particle_key: dict[tuple[str, str, int], float],
    scale: dict[tuple[str, int], float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (tag, vn, za), value in by_particle_key.items():
        factor = scale.get((vn, za))
        if factor is None:
            continue
        activity = value * factor
        if activity <= 0.0:
            continue
        rows.append(
            {
                "particle": tag,
                "VN": vn,
                "volume_class": classify_volume(vn),
                "ZA": za,
                "activity_Bq": activity,
            }
        )
    return rows


def reweighted_activity_distribution(rows: list[dict[str, Any]], particle_scale: dict[str, float], fields: tuple[str, ...]) -> dict[str, float]:
    vals: dict[str, float] = defaultdict(float)
    for row in rows:
        key = "|".join(str(row[field]) for field in fields)
        vals[key] += float(row["activity_Bq"]) * float(particle_scale.get(str(row["particle"]), 1.0))
    total = sum(vals.values())
    if total <= 0.0:
        return {}
    return {key: value / total for key, value in vals.items()}


def scaled_total_activity(rows: list[dict[str, Any]], particle_scale: dict[str, float]) -> float:
    return sum(float(row["activity_Bq"]) * float(particle_scale.get(str(row["particle"]), 1.0)) for row in rows)


def top_items(dist: dict[str, float], n: int = 10) -> list[dict[str, Any]]:
    return [{"key": key, "fraction": value} for key, value in sorted(dist.items(), key=lambda item: item[1], reverse=True)[:n]]


def main() -> int:
    exe = parma_driver()
    probes = trajectory_probes()
    parma_payload: dict[str, dict[str, Any]] = {}
    all_parma_rows: list[dict[str, Any]] = []
    for probe in probes:
        meta, rows = run_parma(exe, probe)
        name = str(probe["probe"])
        parma_payload[name] = {"probe": probe, "meta": meta, "rows": rows}
        for row in rows:
            all_parma_rows.append({**{k: probe[k] for k in ("probe", "day_mid", "altitude_km", "latitude_deg", "longitude_deg")}, **row})

    by_particle_key, dat_audit = parse_buildup_dat()
    scale_to_activity, activity_match = load_activity_scale(by_particle_key)
    contrib_rows = activity_contributions(by_particle_key, scale_to_activity)

    ref_name = "day15_reference"
    ref_rows = parma_payload[ref_name]["rows"]
    ref_particle_totals = particle_totals(ref_rows)
    ref_particle_dist = distribution(ref_rows, ("particle",))
    ref_angle_dist = distribution(ref_rows, ("particle", "direction", "angle_bin"))
    ref_energy_dist = distribution(ref_rows, ("particle", "energy_bin"))
    ref_activity_dists = {
        "nuclide": reweighted_activity_distribution(contrib_rows, {p: 1.0 for p in PARTICLES}, ("ZA",)),
        "volume_class": reweighted_activity_distribution(contrib_rows, {p: 1.0 for p in PARTICLES}, ("volume_class",)),
        "volume": reweighted_activity_distribution(contrib_rows, {p: 1.0 for p in PARTICLES}, ("VN",)),
        "nuclide_volume": reweighted_activity_distribution(contrib_rows, {p: 1.0 for p in PARTICLES}, ("ZA", "VN")),
        "particle": reweighted_activity_distribution(contrib_rows, {p: 1.0 for p in PARTICLES}, ("particle",)),
    }

    metric_rows: list[dict[str, Any]] = []
    probe_summaries: dict[str, Any] = {}
    for name, payload in parma_payload.items():
        rows = payload["rows"]
        totals = particle_totals(rows)
        particle_scale = {
            particle: totals.get(particle, 0.0) / ref_particle_totals.get(particle, 1.0)
            for particle in PARTICLES
            if ref_particle_totals.get(particle, 0.0) > 0.0
        }
        activity_dists = {
            "nuclide": reweighted_activity_distribution(contrib_rows, particle_scale, ("ZA",)),
            "volume_class": reweighted_activity_distribution(contrib_rows, particle_scale, ("volume_class",)),
            "volume": reweighted_activity_distribution(contrib_rows, particle_scale, ("VN",)),
            "nuclide_volume": reweighted_activity_distribution(contrib_rows, particle_scale, ("ZA", "VN")),
            "particle": reweighted_activity_distribution(contrib_rows, particle_scale, ("particle",)),
        }
        metrics = {
            "particle_family_TV": total_variation(ref_particle_dist, distribution(rows, ("particle",))),
            "particle_angle_direction_TV": total_variation(ref_angle_dist, distribution(rows, ("particle", "direction", "angle_bin")),
            ),
            "particle_energy_bin_TV": total_variation(ref_energy_dist, distribution(rows, ("particle", "energy_bin"))),
            "activity_nuclide_TV_particle_reweighted": total_variation(ref_activity_dists["nuclide"], activity_dists["nuclide"]),
            "activity_volume_class_TV_particle_reweighted": total_variation(ref_activity_dists["volume_class"], activity_dists["volume_class"]),
            "activity_volume_TV_particle_reweighted": total_variation(ref_activity_dists["volume"], activity_dists["volume"]),
            "activity_nuclide_volume_TV_particle_reweighted": total_variation(ref_activity_dists["nuclide_volume"], activity_dists["nuclide_volume"]),
            "activity_particle_TV_particle_reweighted": total_variation(ref_activity_dists["particle"], activity_dists["particle"]),
            "total_activity_scale_particle_reweighted": scaled_total_activity(contrib_rows, particle_scale) / scaled_total_activity(contrib_rows, {p: 1.0 for p in PARTICLES}),
        }
        for key, value in metrics.items():
            metric_rows.append({"probe": name, "metric": key, "value": value})
        probe_summaries[name] = {
            "probe": payload["probe"],
            "meta": payload["meta"],
            "particle_scale_to_day15": particle_scale,
            "metrics": metrics,
            "top_activity_nuclides": top_items(activity_dists["nuclide"]),
            "top_activity_volume_classes": top_items(activity_dists["volume_class"]),
        }

    non_ref_metrics = [row for row in metric_rows if row["probe"] != ref_name]
    max_activity_tv = max(float(row["value"]) for row in non_ref_metrics if str(row["metric"]).startswith("activity_") and str(row["metric"]).endswith("reweighted"))
    max_particle_family_tv = max(float(row["value"]) for row in non_ref_metrics if row["metric"] == "particle_family_TV")
    max_energy_tv = max(float(row["value"]) for row in non_ref_metrics if row["metric"] == "particle_energy_bin_TV")
    if max_activity_tv < 0.02 and max_particle_family_tv < 0.05:
        status = "PASS_PARTICLE_FAMILY_REWEIGHTING_SMOKE"
    elif max_activity_tv < 0.05 and max_particle_family_tv < 0.10:
        status = "PASS_LIMITED_PARTICLE_FAMILY_REWEIGHTING_SMOKE"
    else:
        status = "INCONCLUSIVE_OR_FAIL_PARTICLE_FAMILY_REWEIGHTING_SMOKE"
    if max_energy_tv > 0.20:
        status = "INCONCLUSIVE_ENERGY_SHAPE_CHANGES_REQUIRE_TRANSPORT_SMOKE"

    summary = {
        "status": status,
        "scope": "PARMA trajectory probes plus particle-family reweighting of existing fullstat activation inventory; no new Geant4 activation transport",
        "parma_driver": str(exe),
        "trajectory_model": {
            "day15": DAY15,
            "alt_ref_km": ALT_REF_KM,
            "lat_ref_deg": LAT_REF_DEG,
            "lon_ref_deg": LON_REF_DEG,
            "alt_amp_km": ALT_AMP_KM,
            "lat_amp_deg": LAT_AMP_DEG,
            "lon_amp_deg": LON_AMP_DEG,
        },
        "inputs": {
            "buildup_dir": rel(BUILDUP_DIR),
            "groundstate_activity_corrections": rel(GROUNDSTATE),
        },
        "dat_audit": dat_audit,
        "activity_match": activity_match,
        "activity_contribution_rows": len(contrib_rows),
        "reference_top_activity_nuclides": top_items(ref_activity_dists["nuclide"]),
        "reference_top_activity_volume_classes": top_items(ref_activity_dists["volume_class"]),
        "max_nonreference_metrics": {
            "max_activity_TV_particle_reweighted": max_activity_tv,
            "max_particle_family_TV": max_particle_family_tv,
            "max_particle_energy_bin_TV": max_energy_tv,
        },
        "probe_summaries": probe_summaries,
        "claim_boundary": (
            "This smoke supports only the particle-family reweighting layer of the distribution-invariance assumption. "
            "It does not test same-particle energy/angle-dependent activation cross sections or transport-position shifts; "
            "a stronger proof requires low/high/reference Geant4 activation-production reruns with generated PARMA source cards."
        ),
        "outputs": {
            "summary_json": rel(OUT_DIR / "delayed_distribution_invariance_smoke_20260617.json"),
            "metrics_csv": rel(OUT_DIR / "delayed_distribution_invariance_smoke_metrics_20260617.csv"),
            "parma_rows_csv": rel(OUT_DIR / "delayed_distribution_invariance_smoke_parma_rows_20260617.csv"),
            "report_md": rel(OUT_DIR / "delayed_distribution_invariance_smoke_20260617.md"),
        },
    }

    write_csv(OUT_DIR / "delayed_distribution_invariance_smoke_metrics_20260617.csv", metric_rows)
    write_csv(OUT_DIR / "delayed_distribution_invariance_smoke_parma_rows_20260617.csv", all_parma_rows)
    write_json(OUT_DIR / "delayed_distribution_invariance_smoke_20260617.json", summary)

    lines = [
        "# Delayed Distribution Invariance Smoke",
        "",
        f"Status: `{status}`.",
        "",
        "This is a particle-family reweighting smoke test for the mission-time delayed-activation approximation. It uses local PARMA trajectory probes and the existing full-stat activation-buildup isotope store; it does not rerun Geant4 activation transport.",
        "",
        "## Main Metrics",
        "",
        f"- max activity-distribution TV after particle-family reweighting: `{max_activity_tv:.6g}`",
        f"- max PARMA particle-family TV: `{max_particle_family_tv:.6g}`",
        f"- max PARMA particle-energy-bin TV: `{max_energy_tv:.6g}`",
        f"- ground-state activity matched to parsed DAT yields: `{activity_match['matched_fraction']:.8g}`",
        "",
        "## Probe Results",
        "",
    ]
    for name in ("low_altitude", "day15_reference", "high_altitude"):
        p = probe_summaries[name]
        probe = p["probe"]
        metrics = p["metrics"]
        lines.extend(
            [
                f"### {name}",
                "",
                f"- day `{float(probe['day_mid']):.6g}`, altitude `{float(probe['altitude_km']):.6g} km`, latitude `{float(probe['latitude_deg']):.6g} deg`, longitude `{float(probe['longitude_deg']):.6g} deg`.",
                f"- particle-family TV: `{metrics['particle_family_TV']:.6g}`.",
                f"- particle-angle/direction TV: `{metrics['particle_angle_direction_TV']:.6g}`.",
                f"- particle-energy-bin TV: `{metrics['particle_energy_bin_TV']:.6g}`.",
                f"- nuclide TV after particle reweighting: `{metrics['activity_nuclide_TV_particle_reweighted']:.6g}`.",
                f"- volume-class TV after particle reweighting: `{metrics['activity_volume_class_TV_particle_reweighted']:.6g}`.",
                f"- nuclide-volume TV after particle reweighting: `{metrics['activity_nuclide_volume_TV_particle_reweighted']:.6g}`.",
                f"- total activity scale from particle-family reweighting: `{metrics['total_activity_scale_particle_reweighted']:.6g}`.",
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary",
            "",
            summary["claim_boundary"],
            "",
            "This means the scalar delayed-production fold is smoke-tested at the particle-family remixing layer only. The result should not be worded as a full physical proof that isotope/material/position distributions are invariant under all altitude and geomagnetic changes.",
            "",
        ]
    )
    (OUT_DIR / "delayed_distribution_invariance_smoke_20260617.md").write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"status": status, "summary": summary["outputs"]["summary_json"], "max_activity_tv": max_activity_tv}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
