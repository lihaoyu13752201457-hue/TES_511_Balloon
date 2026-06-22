#!/usr/bin/env python3
"""Audit W/collimator-origin delayed events selected in the fix5 W2 window."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import pickle
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
COORD_MATCH_DECIMALS = 5
COORD_NEAREST_TOLERANCE_CM = 1.0e-5
REPORT_DIR = ROOT / "outputs" / "reports" / LABEL
OUT_JSON = REPORT_DIR / "fix5_w_activation_selected_w2_audit.json"
OUT_CSV = REPORT_DIR / "fix5_w_activation_selected_w2_events.csv"
STEP05_SCRIPT = ROOT / "code" / "tools" / "build_v3p5_centerfinger_step05_l1_response.py"
STEP05_SUMMARY = (
    ROOT
    / "stepwise_maintenance"
    / "step05_veto_time_axis"
    / f"outputs_{LABEL}_l1"
    / f"step05_{LABEL}_l1_response_summary.json"
)
CATALOG = ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_{LABEL}_l1" / "work" / "event_catalog.pkl"
DELAYED_SIM = (
    ROOT
    / "runs"
    / "step02_delayed_transport_fix5_fullstat_v2_exactpos_m50000_s260613"
    / "DelayedDecayFix5FullstatV2ExactposM50000S260613.inc1.id1.sim.gz"
)
EXACTPOS_TABLE = ROOT / "runs" / "step02_delay_fix_fix5_fullstat_v2" / "exactpos_weighted_rpip_table_m50000_s260613.csv"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def coord_key(za: str | int, x: float, y: float, z: float) -> tuple[str, str, str, str]:
    fmt = f"{{:.{COORD_MATCH_DECIMALS}f}}"
    return (str(int(za)), fmt.format(x), fmt.format(y), fmt.format(z))


def is_w_or_collimator_volume(volume: str) -> bool:
    lower = volume.lower()
    return lower.startswith("passive_w") or "collimator" in lower or "tungsten" in lower


def load_step05_module():
    spec = importlib.util.spec_from_file_location("fix5_step05_module", STEP05_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {STEP05_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.configure_paths(LABEL)
    return mod


def selected_delayed_w2_events(step05_mod, cat: dict[str, Any]) -> list[dict[str, Any]]:
    disk = step05_mod.side_entry_disk()
    selected: list[dict[str, Any]] = []
    stream = np.asarray(cat["stream"], dtype=object)
    energy = np.asarray(cat["tes_total_keV"], dtype=float)
    bgo = np.asarray(cat["bgo_total_keV"], dtype=float)
    mask = (stream == "delayed") & (energy >= 510.58) & (energy < 511.42) & (bgo < float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV))
    for idx in np.flatnonzero(mask):
        keep, cls = step05_mod.side_keep_from_hits(step05_mod.event_hits(cat, int(idx)), disk, "keep")
        if not keep:
            continue
        selected.append(
            {
                "catalog_index": int(idx),
                "local_id": int(cat["local_id"][idx]),
                "tes_total_keV": float(cat["tes_total_keV"][idx]),
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "rate_hz": float(cat["rate_hz"][idx]),
                "side_compton_class": cls,
                "pix_count": int(cat["pix_count"][idx]),
            }
        )
    return selected


def parse_ia_init_for_ids(wanted: set[int]) -> dict[int, dict[str, Any]]:
    out: dict[int, dict[str, Any]] = {}
    current_id: int | None = None
    with gzip.open(DELAYED_SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            if raw.startswith("ID "):
                parts = raw.split()
                if len(parts) >= 2:
                    current_id = int(parts[1])
                else:
                    current_id = None
                continue
            if current_id not in wanted:
                continue
            if raw.startswith("IA INIT"):
                parts = [part.strip() for part in raw.split(";")]
                if len(parts) < 16:
                    raise ValueError(f"bad IA INIT line for ID {current_id}: {raw[:120]}")
                x = float(parts[4])
                y = float(parts[5])
                z = float(parts[6])
                za = int(float(parts[15]))
                out[current_id] = {"source_x_cm": x, "source_y_cm": y, "source_z_cm": z, "ZA": za}
                if len(out) == len(wanted):
                    break
    return out


def load_exactpos_index() -> tuple[dict[tuple[str, str, str, str], list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    by_za: dict[str, list[dict[str, Any]]] = defaultdict(list)
    with EXACTPOS_TABLE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            row["_x_cm_float"] = float(row["x_cm"])
            row["_y_cm_float"] = float(row["y_cm"])
            row["_z_cm_float"] = float(row["z_cm"])
            key = coord_key(row["ZA"], float(row["x_cm"]), float(row["y_cm"]), float(row["z_cm"]))
            za_key = str(int(row["ZA"]))
            lookup[key].append(row)
            by_za[za_key].append(row)
    return lookup, by_za


def source_distance_cm(init: dict[str, Any], row: dict[str, Any]) -> float:
    dx = float(init["source_x_cm"]) - float(row["_x_cm_float"])
    dy = float(init["source_y_cm"]) - float(row["_y_cm_float"])
    dz = float(init["source_z_cm"]) - float(row["_z_cm_float"])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def match_exactpos_source(
    init: dict[str, Any],
    lookup: dict[tuple[str, str, str, str], list[dict[str, Any]]],
    by_za: dict[str, list[dict[str, Any]]],
) -> tuple[dict[str, Any] | None, str, int, float | None]:
    key = coord_key(init["ZA"], init["source_x_cm"], init["source_y_cm"], init["source_z_cm"])
    keyed = lookup.get(key, [])
    if len(keyed) == 1:
        return keyed[0], "KEY_MATCH", 1, source_distance_cm(init, keyed[0])
    if len(keyed) > 1:
        return None, "AMBIGUOUS_KEY_MATCH", len(keyed), None

    candidates: list[tuple[float, dict[str, Any]]] = []
    for candidate in by_za.get(str(int(init["ZA"])), []):
        distance_cm = source_distance_cm(init, candidate)
        if distance_cm <= COORD_NEAREST_TOLERANCE_CM:
            candidates.append((distance_cm, candidate))
    candidates.sort(key=lambda item: item[0])
    if len(candidates) == 1:
        return candidates[0][1], "NEAREST_MATCH_WITHIN_TOLERANCE", 1, candidates[0][0]
    if not candidates:
        return None, "NO_MATCH_WITHIN_TOLERANCE", 0, None
    return None, "AMBIGUOUS_NEAREST_MATCH_WITHIN_TOLERANCE", len(candidates), candidates[0][0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def build() -> dict[str, Any]:
    step05_summary = load_json(STEP05_SUMMARY)
    step05_mod = load_step05_module()
    with CATALOG.open("rb") as handle:
        cat = pickle.load(handle)
    selected = selected_delayed_w2_events(step05_mod, cat)
    ids = {row["local_id"] for row in selected}
    ia = parse_ia_init_for_ids(ids)
    lookup, by_za = load_exactpos_index()

    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for row in selected:
        local_id = int(row["local_id"])
        init = ia.get(local_id)
        if init is None:
            problems.append(f"missing_IA_INIT_for_ID_{local_id}")
            enriched = {**row, "source_match_status": "MISSING_IA_INIT"}
            rows.append(enriched)
            continue
        match, match_status, match_count, match_distance_cm = match_exactpos_source(init, lookup, by_za)
        if match is None:
            problems.append(f"exactpos_{match_status}_{match_count}_for_ID_{local_id}")
            match = {}
        volume = str(match.get("VN", ""))
        enriched = {
            **row,
            **init,
            "source_match_status": match_status,
            "source_match_count": match_count,
            "source_match_distance_cm": match_distance_cm,
            "VN": volume,
            "source_ZA": match.get("ZA", ""),
            "source_sim": match.get("source_sim", ""),
            "sample_weight": match.get("sample_weight", ""),
            "is_w_or_collimator_origin": is_w_or_collimator_volume(volume),
        }
        rows.append(enriched)

    write_csv(OUT_CSV, rows)

    total_rate = sum(float(row.get("rate_hz", 0.0)) for row in rows)
    w_rate = sum(float(row.get("rate_hz", 0.0)) for row in rows if row.get("is_w_or_collimator_origin") is True)
    volume_counts = Counter(str(row.get("VN", "")) for row in rows)
    volume_rates: dict[str, float] = defaultdict(float)
    for row in rows:
        volume_rates[str(row.get("VN", ""))] += float(row.get("rate_hz", 0.0))
    top_volumes = [
        {"VN": volume, "events": volume_counts[volume], "rate_hz": volume_rates[volume]}
        for volume, _count in volume_counts.most_common(20)
    ]
    expected_delayed = float(
        step05_summary["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_rate_s-1"]
    )
    expected_events = int(
        step05_summary["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]["side_compton_fov_pass_events"]
    )
    close_rate = abs(total_rate - expected_delayed) <= 1.0e-15
    close_events = len(rows) == expected_events
    dominant_threshold = 0.5
    payload = {
        "status": "PASS_FIX5_SELECTED_W_ACTIVATION_W2_AUDIT" if not problems and close_rate and close_events else "FAIL_FIX5_SELECTED_W_ACTIVATION_W2_AUDIT",
        "label": LABEL,
        "generated_at_utc": now_utc(),
        "method": "Recompute the Step05 W2 delayed final selection from event_catalog.pkl, parse IA INIT for those delayed SIM event IDs, and match source ZA/x/y/z back to exactpos_weighted_rpip_table_m50000_s260613.csv.",
        "source_position_match": {
            "key": ["ZA", "x_cm", "y_cm", "z_cm"],
            "coordinate_decimals": COORD_MATCH_DECIMALS,
            "rationale": "Cosima IA INIT lines round the exactpos source coordinates to approximately five decimal places, while exactpos_weighted_rpip_table stores six decimal places.",
            "nearest_tolerance_cm": COORD_NEAREST_TOLERANCE_CM,
        },
        "inputs": {
            "step05_summary": rel(STEP05_SUMMARY),
            "event_catalog": rel(CATALOG),
            "delayed_sim": rel(DELAYED_SIM),
            "exactpos_table": rel(EXACTPOS_TABLE),
        },
        "selection": {
            "stream": "delayed",
            "window_keV": [510.58, 511.42],
            "active_veto_threshold_keV": float(step05_mod.ACTIVE_VETO_THRESHOLD_KEV),
            "side_compton_fov_policy": "same side_keep_from_hits/event_hits/side_entry_disk implementation as Step05",
        },
        "checks": {
            "selected_events": len(rows),
            "expected_step05_delayed_selected_events": expected_events,
            "selected_rate_hz": total_rate,
            "expected_step05_delayed_rate_hz": expected_delayed,
            "rate_abs_delta_hz": total_rate - expected_delayed,
            "events_match_step05": close_events,
            "rate_matches_step05": close_rate,
            "ia_init_matches": len(ia),
            "exactpos_match_failures": len(problems),
            "w_or_collimator_selected_events": sum(1 for row in rows if row.get("is_w_or_collimator_origin") is True),
            "w_or_collimator_selected_rate_hz": w_rate,
            "w_or_collimator_fraction_of_delayed_selected_rate": w_rate / total_rate if total_rate > 0 else None,
            "w_or_collimator_dominant_threshold_fraction": dominant_threshold,
            "w_or_collimator_is_dominant_component": (w_rate / total_rate) >= dominant_threshold if total_rate > 0 else False,
        },
        "top_source_volumes": top_volumes,
        "event_table": rel(OUT_CSV),
        "problems": problems,
    }
    write_json(OUT_JSON, payload)
    return payload


def main() -> int:
    payload = build()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_events": payload["checks"]["selected_events"],
                "selected_rate_hz": payload["checks"]["selected_rate_hz"],
                "w_or_collimator_selected_rate_hz": payload["checks"]["w_or_collimator_selected_rate_hz"],
                "w_or_collimator_fraction": payload["checks"]["w_or_collimator_fraction_of_delayed_selected_rate"],
                "out": rel(OUT_JSON),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if str(payload["status"]).startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
