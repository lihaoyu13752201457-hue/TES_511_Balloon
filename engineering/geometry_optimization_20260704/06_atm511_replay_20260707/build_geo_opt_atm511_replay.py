#!/usr/bin/env python3
"""Analyze the geo-opt atmospheric 511-keV lower-hemisphere replay."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs/geometry_optimization_20260704/p2_atm511_unit_geo_opt_s1_bpe_w5_fullstat_v1"
P2_SOURCE = RUN_DIR / "Atm511LowerUnit3M_GeoOptS1BpeW5.source"
P2_LOG = RUN_DIR / "cosima_Atm511LowerUnit3M_GeoOptS1BpeW5.log"
P2_SIM = RUN_DIR / "Atm511LowerUnit3M_GeoOptS1BpeW5.inc1.id1.sim.gz"
STEP05_SCRIPT = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1"
    / "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_response_summary.json"
)
STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1"
    / "step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json"
)
STEP09_BRIDGE = (
    ROOT
    / "stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5"
    / "step09_optics_bridge_summary.json"
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    fields = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_step05_module():
    spec = importlib.util.spec_from_file_location("geo_opt_atm511_step05", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.STEP09_SUMMARY = STEP09_BRIDGE
    return mod


def p2_observation_time_s() -> float:
    for line in P2_LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"cannot locate Observation time in {P2_LOG}")


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    if upper.startswith("CSI_") or "ACTIVE_SHIELD" in upper or "CEBR3" in upper or "BGO" in upper:
        return True
    return upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")


def parse_p2_catalog() -> dict[str, Any]:
    cc_re = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
    kv_re = re.compile(r"(\w+)=([^\s]+)")
    id_re = re.compile(r"^ID\s+(\d+)")
    tp_re = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)
    cat: dict[str, Any] = {
        "local_id": [],
        "tes_total_keV": [],
        "bgo_total_keV": [],
        "pix_start": [],
        "pix_count": [],
        "pix_uid": [],
        "pix_layer": [],
        "pix_e": [],
        "pix_x": [],
        "pix_y": [],
        "pix_z": [],
    }
    generated = 0
    kept = 0
    cur_id: int | None = None
    bgo_total = 0.0
    pix: dict[str, dict[str, float]] = {}

    def flush() -> None:
        nonlocal cur_id, bgo_total, pix, kept
        if cur_id is None:
            return
        pix_start = len(cat["pix_e"])
        tes_total = 0.0
        for uid, rec in sorted(pix.items()):
            e = float(rec["e"])
            if e <= 0:
                continue
            tes_total += e
            cat["pix_uid"].append(uid)
            cat["pix_layer"].append(int(rec["layer"]))
            cat["pix_e"].append(e)
            cat["pix_x"].append(float(rec["wx"] / e))
            cat["pix_y"].append(float(rec["wy"] / e))
            cat["pix_z"].append(float(rec["wz"] / e))
        pix_count = len(cat["pix_e"]) - pix_start
        if pix_count > 0 or bgo_total > 0:
            cat["local_id"].append(int(cur_id))
            cat["tes_total_keV"].append(float(tes_total))
            cat["bgo_total_keV"].append(float(bgo_total))
            cat["pix_start"].append(int(pix_start))
            cat["pix_count"].append(int(pix_count))
            kept += 1
        cur_id = None
        bgo_total = 0.0
        pix = {}

    with gzip.open(P2_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if line == "SE":
                flush()
                continue
            match_id = id_re.match(line)
            if match_id:
                cur_id = int(match_id.group(1))
                generated += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            match_hit = cc_re.match(line)
            if match_hit is None:
                continue
            vol = match_hit.group(1)
            kv = dict(kv_re.findall(match_hit.group(2)))
            try:
                edep = float(kv["edep_keV"])
                x = float(kv["x"])
                y = float(kv["y"])
                z = float(kv["z"])
            except Exception:
                continue
            match_tp = tp_re.match(vol)
            if match_tp:
                rec = pix.setdefault(vol, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": float(match_tp.group("layer"))})
                rec["e"] += edep
                rec["wx"] += edep * x
                rec["wy"] += edep * y
                rec["wz"] += edep * z
            elif is_active_veto_volume(vol):
                bgo_total += edep
    flush()

    for key in ("local_id", "pix_start", "pix_count", "pix_layer"):
        cat[key] = np.asarray(cat[key], dtype=np.int64)
    for key in ("tes_total_keV", "bgo_total_keV", "pix_e", "pix_x", "pix_y", "pix_z"):
        cat[key] = np.asarray(cat[key], dtype=np.float64)
    cat["pix_uid"] = np.asarray(cat["pix_uid"], dtype=object)
    cat["generated_events"] = generated
    cat["kept_events_tes_or_active"] = kept
    return cat


def p2_event_hits(cat: dict[str, Any], idx: int) -> list[Any]:
    start = int(cat["pix_start"][idx])
    count = int(cat["pix_count"][idx])
    hits = []
    for j in range(start, start + count):
        hit = type("Hit", (), {})()
        hit.x = float(cat["pix_x"][j])
        hit.y = float(cat["pix_y"][j])
        hit.z = float(cat["pix_z"][j])
        hit.e = float(cat["pix_e"][j])
        hit.pixel_uid = str(cat["pix_uid"][j])
        hit.layer = int(cat["pix_layer"][j])
        hits.append(hit)
    return hits


def summarize_p2_window(cat: dict[str, Any], step05: Any, emin: float, emax: float) -> dict[str, Any]:
    tes = cat["tes_total_keV"]
    bgo = cat["bgo_total_keV"]
    mask = (tes >= emin) & (tes < emax)
    active = mask & (bgo < 50.0)
    classes: Counter[str] = Counter()
    final_indices: list[int] = []
    disk = step05.side_entry_disk()
    for idx in np.flatnonzero(active):
        keep, cls = step05.side_keep_from_hits(p2_event_hits(cat, int(idx)), disk, "keep")
        classes[cls] += 1
        if keep:
            final_indices.append(int(idx))
    event_weight = 1.0 / float(cat["observation_time_s"])
    return {
        "window_keV": [emin, emax],
        "raw_events": int(np.sum(mask)),
        "active_veto_pass_events": int(np.sum(active)),
        "side_compton_fov_pass_events": int(len(final_indices)),
        "raw_rate_per_unit_flux_cps_per_ph_cm2_s": float(np.sum(mask) * event_weight),
        "active_rate_per_unit_flux_cps_per_ph_cm2_s": float(np.sum(active) * event_weight),
        "final_rate_per_unit_flux_cps_per_ph_cm2_s": float(len(final_indices) * event_weight),
        "final_relative_poisson_sigma": float(1.0 / math.sqrt(len(final_indices))) if final_indices else None,
        "side_compton_class_counts": dict(sorted(classes.items())),
        "final_event_ids": [int(cat["local_id"][i]) for i in final_indices],
        "final_energies_keV": [float(cat["tes_total_keV"][i]) for i in final_indices],
        "final_bgo_keV": [float(cat["bgo_total_keV"][i]) for i in final_indices],
        "final_pix_counts": [int(cat["pix_count"][i]) for i in final_indices],
    }


def sim_header() -> dict[str, Any]:
    header: dict[str, Any] = {}
    with gzip.open(P2_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry"):
                header["geometry"] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("Seed"):
                header["seed"] = int(line.split()[1])
            elif line == "SE":
                break
    return header


def build() -> dict[str, Any]:
    step05_mod = load_step05_module()
    step05 = load_json(STEP05_SUMMARY)
    step08 = load_json(STEP08_SUMMARY)
    cat = parse_p2_catalog()
    cat["observation_time_s"] = p2_observation_time_s()
    w2 = summarize_p2_window(cat, step05_mod, 510.58, 511.42)
    broad = summarize_p2_window(cat, step05_mod, 480.0, 550.0)

    b_current = float(step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]["background_cps"])
    f3_current = float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"])
    transfer = float(w2["final_rate_per_unit_flux_cps_per_ph_cm2_s"])
    scenarios = [
        ("Harris_Rc_11_13_total_disk_no_alt_scale", 4.38e-2 * 0.532, "Harris 2003 Table 2 normalized to <7 GV; no payload-altitude rescaling"),
        ("lower_hemisphere_brightness_3e-3_sr", 3e-3 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("lower_hemisphere_brightness_6e-3_sr", 6e-3 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("lower_hemisphere_brightness_1e-2_sr", 1e-2 * 2.0 * math.pi, "Stress brightness integrated over 2pi sr"),
        ("MEGAlib_SMM_500km_to_34km_stress", 22.7e-3 * (500.0 / 34.0) ** 2, "MEGAlib BackgroundGenerator-style altitude scaling; stress test only"),
    ]
    scenario_rows = []
    for name, flux, note in scenarios:
        r_atm = transfer * flux
        b_new = b_current + r_atm
        f3_new = f3_current * math.sqrt(b_new / b_current)
        scenario_rows.append(
            {
                "scenario": name,
                "atm511_flux_ph_cm2_s": flux,
                "atm511_added_cps": r_atm,
                "background_new_cps": b_new,
                "background_fractional_increase": r_atm / b_current,
                "F3_20d_new_ph_cm2_s": f3_new,
                "note": note,
            }
        )

    scenario_csv = OUT / "p2_geo_opt_s1_bpe_w5_atm511_flux_scenarios.csv"
    write_csv(scenario_csv, scenario_rows)
    payload = {
        "status": "PASS_GEO_OPT_S1_BPE_W5_P2_ATM511_TRANSFER_REPLAY",
        "generated_at_utc": now_utc(),
        "inputs": {
            "p2_source": rel(P2_SOURCE),
            "p2_log": rel(P2_LOG),
            "p2_sim": rel(P2_SIM),
            "step05_summary": rel(STEP05_SUMMARY),
            "step08_summary": rel(STEP08_SUMMARY),
            "step05_veto_algorithm": rel(STEP05_SCRIPT),
            "side_entry_bridge_summary": rel(STEP09_BRIDGE),
        },
        "sim_header": sim_header(),
        "normalization": {
            "source_total_lower_hemisphere_flux_ph_cm2_s": 1.0,
            "observation_time_s": float(cat["observation_time_s"]),
            "rate_weight_per_generated_event_s-1": 1.0 / float(cat["observation_time_s"]),
            "active_veto_threshold_keV": 50.0,
            "active_veto_volume_rule": "CsI/BGO/legacy active tokens plus GeoOpt_S1_PlasticFullWrap* plastic skin.",
        },
        "catalog": {
            "generated_events": int(cat["generated_events"]),
            "kept_events_tes_or_active": int(cat["kept_events_tes_or_active"]),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0)),
            "active_veto_events": int(np.sum(cat["bgo_total_keV"] > 0)),
        },
        "windows": {
            "w2_510p58_511p42": w2,
            "broad_480_550": broad,
        },
        "baseline_without_atm511": {
            "geo_opt_step05_w2_background_cps": b_current,
            "geo_opt_step08_w2_F3_20d_ph_cm2_s": f3_current,
        },
        "scenario_csv": rel(scenario_csv),
        "scenario_rows": scenario_rows,
        "interpretation": {
            "limitation": "Detector-response transfer for an idealized lower-hemisphere mono-line field; atmospheric-line normalization and angular model remain external assumptions.",
            "promotion": "Not a geometry promotion; this is the geo-opt branch P2 replay to quantify the 5 mm W bottom baffle/plastic/BPE stack effect on atmospheric 511.",
        },
    }
    write_json(OUT / "p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json", payload)
    return payload


def write_readme(payload: dict[str, Any]) -> None:
    harris = next(row for row in payload["scenario_rows"] if row["scenario"] == "Harris_Rc_11_13_total_disk_no_alt_scale")
    w2 = payload["windows"]["w2_510p58_511p42"]
    text = f"""# Geo-opt S1/BPE/W5 Atmospheric 511 Replay

Status: `{payload['status']}`

Scope: lower-hemisphere mono-511 P2 replay for the geo-opt S1/BPE/W5 geometry. This is not a geometry promotion.

## Result

- Generated events: `{payload['catalog']['generated_events']}`
- Observation time: `{payload['normalization']['observation_time_s']:.6g} s`
- W2 final events: `{w2['side_compton_fov_pass_events']}`
- W2 final unit transfer: `{w2['final_rate_per_unit_flux_cps_per_ph_cm2_s']:.12g} cps / (ph cm^-2 s^-1)`
- Harris Rc~11--13 GV added background: `{harris['atm511_added_cps']:.12g} cps`
- Harris-included W2 background: `{harris['background_new_cps']:.12g} cps`
- Harris-included W2 F3(20d): `{harris['F3_20d_new_ph_cm2_s']:.12g} ph cm^-2 s^-1`

## Files

- Source: `{payload['inputs']['p2_source']}`
- SIM: `{payload['inputs']['p2_sim']}`
- Summary: `engineering/geometry_optimization_20260704/06_atm511_replay_20260707/p2_geo_opt_s1_bpe_w5_atm511_transfer_summary.json`
- Scenarios: `{payload['scenario_csv']}`
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main() -> int:
    payload = build()
    write_readme(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "generated_events": payload["catalog"]["generated_events"],
                "w2_final_events": payload["windows"]["w2_510p58_511p42"]["side_compton_fov_pass_events"],
                "w2_transfer": payload["windows"]["w2_510p58_511p42"]["final_rate_per_unit_flux_cps_per_ph_cm2_s"],
                "harris_added_cps": next(
                    row for row in payload["scenario_rows"] if row["scenario"] == "Harris_Rc_11_13_total_disk_no_alt_scale"
                )["atm511_added_cps"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
