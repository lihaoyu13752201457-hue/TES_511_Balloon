#!/usr/bin/env python3
"""Rebuild the final S3d mission fold from retained evidence only.

This is an analysis-only closure.  It does not launch Cosima or generate new
Monte Carlo events.  It replaces the historical one-scalar Step06 fold with
the particle-family and nuclide-response equations stated in the manuscript:

* all eight prompt families use live-PARMA flux ratios in each of 81 bins;
* neutron-produced inventories are integrated nuclide by nuclide;
* the selected delayed rate is the sum of nuclide activities times the
  day-15 S3d selection response inferred from the retained delayed events;
* the atmospheric-511 sidecar and focused signal retain their independent
  trajectory scales; and
* accidental-coincidence live time uses family-resolved prompt occupancy.

The day-15 detector response, event selection, finite-count intervals, source
normalizations, and all transport products remain unchanged.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import json
import math
import pickle
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
OUTPUTS = PACKAGE / "outputs"

RESPONSE_SUMMARY = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/data/"
    "o8_energy_response_closure_summary.json"
)
RESPONSE_CODE = (
    ROOT
    / "engineering/ea_detector_response_closure_20260713/code/"
    "build_o8_energy_response_closure.py"
)
O8 = (
    ROOT
    / "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712"
)
EVENT_CATALOG = O8 / "fullchain/step05/work/event_catalog.pkl"
BASE_STEP06 = O8 / "fullchain/step06/background_time_variation.csv"
GROUNDSTATE = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delay_fix_s3d_o8_neutron_delayed_m50000_20260712/"
    "groundstate_activity_corrections.csv"
)
DELAYED_SIM = (
    ROOT
    / "runs/geometry_optimization_20260704/"
    "step02_delayed_transport_s3d_o8_neutron_delayed_m50000_20260712/"
    "DelayedDecayS3dO8NeutronM50000.inc1.id1.sim.gz"
)
TRAJECTORY_PROFILE = (
    ROOT
    / "engineering/trajectory_transport_validation_20260709/01_points/"
    "trajectory_profile_frozen.csv"
)
THREE_FAMILY_CURVE = (
    ROOT
    / "engineering/trajectory_transport_validation_20260709/"
    "11_analytic_agreement_20260709/claude_source_response_curve_by_time.csv"
)
TARGETED_AUDIT = (
    ROOT
    / "engineering/trajectory_transport_validation_20260709/"
    "11_analytic_agreement_20260709/analytic_agreement_summary.json"
)
PARMA_EXE = Path(
    "/home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/"
    "external/expacs_parma/phase2_parma_grid_driver"
)
PARMA_CWD = PARMA_EXE.parent / "parma_cpp"

ALL8_SCALES = DATA / "live_parma_all8_scales_81bins.csv"
SELECTED_DELAYED = DATA / "selected_delayed_nuclides_primary_seed.json"
ACTIVITY_TIMELINE = OUTPUTS / "nuclide_activity_by_time.csv"
MISSION_TIMELINE = OUTPUTS / "w2_family_nuclide_mission_timeline.csv"
SUMMARY = DATA / "s3d_family_nuclide_mission_summary.json"
README = PACKAGE / "README.md"

PROMPT_TAGS = (
    "alpha",
    "eminus",
    "eplus",
    "gamma",
    "muminus",
    "muplus",
    "n",
    "p",
)
SECONDS_PER_DAY = 86_400.0
DAY15 = 15.0
MU_BIN_SOLID_ANGLE_SR = 2.0 * math.pi * 0.1
COINCIDENCE_WINDOW_S = 1.0e-6
REFERENCE_FLUX = 1.0e-4


class FoldError(RuntimeError):
    """An input authority or closure invariant failed."""


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise FoldError(f"cannot import {rel(path)}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require_close(
    actual: float,
    expected: float,
    label: str,
    *,
    atol: float = 1.0e-12,
    rtol: float = 1.0e-10,
) -> None:
    if not math.isclose(actual, expected, rel_tol=rtol, abs_tol=atol):
        raise FoldError(f"{label}: {actual:.17g} != {expected:.17g}")


def run_parma(lat: float, lon: float, alt: float) -> tuple[dict[str, float], list[dict[str, str]]]:
    command = [
        str(PARMA_EXE),
        "2025",
        "8",
        "31",
        f"{lat:.12g}",
        f"{lon:.12g}",
        f"{alt:.12g}",
        "10.0",
    ]
    process = subprocess.run(
        command,
        cwd=PARMA_CWD,
        check=True,
        text=True,
        capture_output=True,
    )
    lines = [line for line in process.stdout.splitlines() if line]
    try:
        start = next(index for index, line in enumerate(lines) if line.startswith("particle,"))
        meta_line = next(line for line in lines if line.startswith("META,"))
    except StopIteration as exc:
        raise FoldError("PARMA output is missing its table or META row") from exc
    _, w_index, rigidity, depth = meta_line.split(",")
    rows = list(csv.DictReader(lines[start:]))
    return {
        "W_index": float(w_index),
        "Rc_GV": float(rigidity),
        "depth_g_cm2": float(depth),
    }, rows


def particle_totals(rows: list[dict[str, str]]) -> dict[str, float]:
    totals = {tag: 0.0 for tag in PROMPT_TAGS}
    for row in rows:
        tag = row["particle"]
        if tag not in totals:
            continue
        value = max(float(row["differential_flux_cm2_s_sr_MeV"]), 0.0)
        totals[tag] += value * MU_BIN_SOLID_ANGLE_SR
    if any(value <= 0.0 for value in totals.values()):
        raise FoldError(f"non-positive PARMA family total: {totals}")
    return totals


def build_all8_scales() -> list[dict[str, str]]:
    profile = read_csv(TRAJECTORY_PROFILE)
    if len(profile) != 81:
        raise FoldError(f"trajectory profile has {len(profile)} rows, expected 81")
    if ALL8_SCALES.is_file():
        cached = read_csv(ALL8_SCALES)
        required = {
            "time_bin_id",
            "day_mid",
            *(f"flux_{tag}" for tag in PROMPT_TAGS),
            *(f"scale_{tag}" for tag in PROMPT_TAGS),
        }
        if len(cached) == 81 and cached and required <= set(cached[0]):
            return cached

    if not PARMA_EXE.is_file():
        raise FoldError(f"PARMA evaluator is absent: {PARMA_EXE}")

    raw: list[dict[str, Any]] = []
    for index, row in enumerate(profile, start=1):
        meta, parma_rows = run_parma(
            float(row["latitude_deg"]),
            float(row["longitude_deg"]),
            float(row["altitude_km"]),
        )
        raw.append({
            **row,
            **meta,
            "totals": particle_totals(parma_rows),
        })
        if index == 1 or index % 20 == 0 or index == len(profile):
            print(f"PARMA analytic bins: {index}/{len(profile)}", flush=True)

    day15 = next(row for row in raw if math.isclose(float(row["day_mid"]), DAY15))
    reference = day15["totals"]
    out: list[dict[str, Any]] = []
    for row in raw:
        record: dict[str, Any] = {
            "time_bin_id": row["time_bin_id"],
            "day_mid": row["day_mid"],
            "altitude_km": row["altitude_km"],
            "latitude_deg": row["latitude_deg"],
            "longitude_deg": row["longitude_deg"],
            "Rc_GV_parma": f"{row['Rc_GV']:.12g}",
            "depth_g_cm2_parma": f"{row['depth_g_cm2']:.12g}",
            "W_index": f"{row['W_index']:.12g}",
        }
        for tag in PROMPT_TAGS:
            record[f"flux_{tag}"] = f"{row['totals'][tag]:.12e}"
            record[f"scale_{tag}"] = f"{row['totals'][tag] / reference[tag]:.12g}"
        out.append(record)

    fields = [
        "time_bin_id",
        "day_mid",
        "altitude_km",
        "latitude_deg",
        "longitude_deg",
        "Rc_GV_parma",
        "depth_g_cm2_parma",
        "W_index",
        *(f"flux_{tag}" for tag in PROMPT_TAGS),
        *(f"scale_{tag}" for tag in PROMPT_TAGS),
    ]
    write_csv(ALL8_SCALES, out, fields)
    return read_csv(ALL8_SCALES)


def validate_three_family_parity(all8_rows: list[dict[str, str]]) -> dict[str, Any]:
    old_rows = read_csv(THREE_FAMILY_CURVE)
    old = {int(row["time_bin_id"]): row for row in old_rows}
    maximum = 0.0
    for row in all8_rows:
        index = int(row["time_bin_id"])
        for tag in ("eplus", "n", "gamma"):
            delta = abs(float(row[f"scale_{tag}"]) - float(old[index][f"scale_{tag}"]))
            maximum = max(maximum, delta)
    if maximum > 5.0e-10:
        raise FoldError(f"all-eight PARMA curve does not reproduce retained 3-family curve: {maximum}")
    audit = read_json(TARGETED_AUDIT)
    return {
        "status": "PASS_ALL8_CURVE_REPRODUCES_RETAINED_EPLUS_N_GAMMA",
        "max_abs_scale_delta": maximum,
        "targeted_audit": rel(TARGETED_AUDIT),
        "targeted_audit_status": audit.get("status"),
        "validation_scope": (
            "The retained direct-transport comparison validates e+, n, and gamma "
            "modulation in the 480--550 keV diagnostic band; the final W2 response "
            "coefficients remain anchored to the day-15 S3d event selection."
        ),
    }


def compact_from_raw(raw: dict[str, Any], closure: Any) -> Any:
    counts_all = np.asarray(raw["pix_count"], dtype=np.int64)
    tes_mask = counts_all > 0
    counts = counts_all[tes_mask]
    starts = np.asarray(raw["pix_start"], dtype=np.int64)[tes_mask]
    expected_starts = np.zeros(len(counts), dtype=np.int64)
    if len(counts) > 1:
        expected_starts[1:] = np.cumsum(counts[:-1])
    if not np.array_equal(starts, expected_starts):
        raise FoldError("TES pixel-hit offsets are not compact and ordered")

    stream_all = np.asarray(raw["stream"], dtype=object)
    rate_all = np.asarray(raw["rate_hz"], dtype=np.float64)
    active_all = np.asarray(raw["bgo_total_keV"], dtype=np.float64)
    active_only = (~tes_mask) & (active_all > 0.0)
    active_only_rates = closure._group_sum(rate_all[active_only], stream_all[active_only])
    active_only_counts = closure._group_count(active_only, stream_all)

    local_ids = np.asarray(raw["local_id"], dtype=np.int64)[tes_mask]
    return closure.CompactCatalog(
        label="o8_fullchain_with_source_local_ids",
        event_id=local_ids.copy(),
        stream=stream_all[tes_mask].copy(),
        tag=np.asarray(raw["tag"], dtype=object)[tes_mask].copy(),
        rate_hz=rate_all[tes_mask].copy(),
        active_keV=active_all[tes_mask].copy(),
        raw_total_keV=np.asarray(raw["tes_total_keV"], dtype=np.float64)[tes_mask].copy(),
        hit_start=expected_starts,
        hit_count=counts.copy(),
        hit_uid=np.asarray(raw["pix_uid"], dtype=object).copy(),
        hit_layer=np.asarray(raw["pix_layer"], dtype=np.int64).copy(),
        hit_e_keV=np.asarray(raw["pix_e"], dtype=np.float64).copy(),
        hit_x_cm=np.asarray(raw["pix_x"], dtype=np.float64).copy(),
        hit_y_cm=np.asarray(raw["pix_y"], dtype=np.float64).copy(),
        hit_z_cm=np.asarray(raw["pix_z"], dtype=np.float64).copy(),
        active_only_rate_by_stream=active_only_rates,
        active_only_events_by_stream=active_only_counts,
        generated_events=int(raw.get("n_generated_events_seen", 0)),
    )


def prompt_occupancy_by_family(raw: dict[str, Any]) -> dict[str, dict[str, float | int]]:
    stream = np.asarray(raw["stream"], dtype=object)
    tag = np.asarray(raw["tag"], dtype=object)
    rate = np.asarray(raw["rate_hz"], dtype=np.float64)
    has_detector_record = (
        (np.asarray(raw["pix_count"], dtype=np.int64) > 0)
        | (np.asarray(raw["bgo_total_keV"], dtype=np.float64) > 0.0)
    )
    out: dict[str, dict[str, float | int]] = {}
    for family in PROMPT_TAGS:
        mask = has_detector_record & (stream == "prompt") & (tag == family)
        out[family] = {
            "events": int(np.count_nonzero(mask)),
            "rate_hz_day15": float(np.sum(rate[mask])),
        }
    return out


def selected_delayed_event_ids(cat: Any, closure: Any) -> tuple[list[int], dict[str, Any]]:
    step05, disk = closure.load_step05_selection()
    hits, totals, multiplicity = closure.measured_hits(
        cat,
        closure.PRIMARY_RESPONSE_SEED,
        apply_response=True,
        apply_threshold=True,
    )
    broad_lo, broad_hi = closure.WINDOWS["broad_480_550"]
    broad_active = (
        (totals >= broad_lo)
        & (totals < broad_hi)
        & (cat.active_keV < closure.ACTIVE_VETO_THRESHOLD_KEV)
    )
    keep = np.zeros(len(totals), dtype=bool)
    one = broad_active & (multiplicity == 1)
    keep[one] = True
    many = broad_active & (multiplicity > int(step05.MAX_ENUM_HITS))
    keep[many] = True
    complex_indices = np.flatnonzero(
        broad_active
        & (multiplicity >= 2)
        & (multiplicity <= int(step05.MAX_ENUM_HITS))
    )
    for index in complex_indices:
        accepted, _classification = step05.side_keep_from_hits(
            closure._event_hits(cat, int(index), hits), disk, "keep"
        )
        keep[index] = bool(accepted)

    lo, hi = closure.WINDOWS["w2_510p58_511p42"]
    final = (
        (totals >= lo)
        & (totals < hi)
        & (cat.active_keV < closure.ACTIVE_VETO_THRESHOLD_KEV)
        & keep
    )
    delayed = final & (cat.stream == "delayed")
    ids = [int(value) for value in cat.event_id[delayed]]
    rates = cat.rate_hz[delayed]
    unique_weights = np.unique(rates)
    if len(ids) != 29 or len(unique_weights) != 1:
        raise FoldError(
            f"primary-seed delayed selection: events={len(ids)}, weights={unique_weights}"
        )
    return ids, {
        "events": len(ids),
        "rate_cps": float(np.sum(rates)),
        "event_weight_cps": float(unique_weights[0]),
    }


def scan_selected_initial_za(event_ids: list[int]) -> dict[int, int]:
    wanted = set(event_ids)
    found: dict[int, int] = {}
    current: int | None = None
    with gzip.open(DELAYED_SIM, "rt", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.startswith("ID "):
                fields = line.split()
                current = int(fields[1]) if len(fields) >= 2 else None
                continue
            if current not in wanted or not line.startswith("IA INIT"):
                continue
            parts = [field.strip() for field in line[7:].split(";")]
            if len(parts) < 16:
                raise FoldError(f"malformed IA INIT for delayed event {current}")
            found[current] = int(parts[15])
            if len(found) == len(wanted):
                break
    missing = sorted(wanted.difference(found))
    if missing:
        raise FoldError(f"missing IA INIT nuclides for delayed events: {missing}")
    return found


def build_selected_delayed_authority(
    response: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, dict[str, float | int]]]:
    closure = load_module("s3d_response_closure", RESPONSE_CODE)
    with EVENT_CATALOG.open("rb") as handle:
        raw = pickle.load(handle)
    occupancy = prompt_occupancy_by_family(raw)
    cat = compact_from_raw(raw, closure)
    del raw
    event_ids, selected = selected_delayed_event_ids(cat, closure)
    del cat

    cache_valid = False
    cache: dict[str, Any] = {}
    if SELECTED_DELAYED.is_file():
        cache = read_json(SELECTED_DELAYED)
        cache_valid = (
            cache.get("response_seed") == int(closure.PRIMARY_RESPONSE_SEED)
            and cache.get("selected_event_ids") == event_ids
            and cache.get("delayed_sim_size_bytes") == DELAYED_SIM.stat().st_size
        )
    if cache_valid:
        za_by_id = {int(key): int(value) for key, value in cache["initial_za_by_event_id"].items()}
    else:
        za_by_id = scan_selected_initial_za(event_ids)

    ground_rows = read_csv(GROUNDSTATE)
    names: dict[int, str] = {}
    for row in ground_rows:
        za = int(row["ZA"])
        name = row["nuclide"]
        if za in names and names[za] != name:
            raise FoldError(f"ZA {za} has inconsistent names: {names[za]} vs {name}")
        names[za] = name
    counts = Counter(za_by_id.values())
    rows = [
        {
            "ZA": za,
            "nuclide": names.get(za, str(za)),
            "selected_events": count,
            "day15_selected_rate_cps": count * float(selected["event_weight_cps"]),
        }
        for za, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    payload = {
        "status": "PASS_PRIMARY_SEED_DELAYED_NUCLIDE_LINEAGE",
        "generated_at_utc": now_utc(),
        "response_seed": int(closure.PRIMARY_RESPONSE_SEED),
        "event_catalog": rel(EVENT_CATALOG),
        "event_catalog_sha256": response["input_authorities"]["o8_event_catalog_sha256"],
        "delayed_sim": rel(DELAYED_SIM),
        "delayed_sim_size_bytes": DELAYED_SIM.stat().st_size,
        "selected_event_ids": event_ids,
        "initial_za_by_event_id": {str(key): value for key, value in sorted(za_by_id.items())},
        "selected_summary": selected,
        "by_nuclide": rows,
        "method": (
            "Replayed the fixed 420 eV FWHM response seed on the retained event "
            "catalog, then read the IA INIT isotope code for each selected delayed "
            "event from the retained S3d delayed SIM."
        ),
    }
    write_json(SELECTED_DELAYED, payload)
    return payload, occupancy


def groundstate_inventory() -> dict[int, dict[str, Any]]:
    inventory: dict[int, dict[str, Any]] = {}
    for row in read_csv(GROUNDSTATE):
        activity = float(row["new_groundstate_activity_Bq"])
        half_life = float(row["nubase_half_life_s"])
        if activity <= 0.0 or half_life <= 0.0 or not math.isfinite(half_life):
            continue
        za = int(row["ZA"])
        record = inventory.setdefault(
            za,
            {
                "ZA": za,
                "nuclide": row["nuclide"],
                "half_life_s": half_life,
                "day15_activity_Bq": 0.0,
            },
        )
        require_close(record["half_life_s"], half_life, f"half-life for ZA={za}")
        if record["nuclide"] != row["nuclide"]:
            raise FoldError(f"nuclide-name mismatch for ZA={za}")
        record["day15_activity_Bq"] += activity
    return inventory


def integrate_nuclides(
    scales: list[dict[str, str]],
    base_rows: list[dict[str, str]],
    selected: dict[str, Any],
) -> tuple[dict[int, list[float]], list[dict[str, Any]], dict[str, Any]]:
    inventory = groundstate_inventory()
    selected_counts = {
        int(row["ZA"]): int(row["selected_events"])
        for row in selected["by_nuclide"]
    }
    event_weight = float(selected["selected_summary"]["event_weight_cps"])
    day15_index = next(
        index for index, row in enumerate(base_rows)
        if math.isclose(float(row["day_mid"]), DAY15)
    )
    driver = [float(row["scale_n"]) for row in scales]
    activities: dict[int, list[float]] = {}
    output_rows: list[dict[str, Any]] = []
    for za, item in sorted(inventory.items()):
        activity_ref = float(item["day15_activity_Bq"])
        half_life = float(item["half_life_s"])
        lam = math.log(2.0) / half_life
        build_factor = 1.0 - math.exp(-lam * DAY15 * SECONDS_PER_DAY)
        production_ref = activity_ref / max(build_factor, 1.0e-300)
        number = 0.0
        raw_activity: list[float] = []
        for index, row in enumerate(base_rows):
            dt_s = float(row["dt_s"])
            production = production_ref * driver[index]
            half = 0.5 * dt_s
            mid_number = (
                number * math.exp(-lam * half)
                + (production / lam) * (1.0 - math.exp(-lam * half))
            )
            raw_activity.append(lam * mid_number)
            number = (
                number * math.exp(-lam * dt_s)
                + (production / lam) * (1.0 - math.exp(-lam * dt_s))
            )
        anchor = raw_activity[day15_index]
        anchor_scale = activity_ref / anchor if anchor > 0.0 else 1.0
        curve = [value * anchor_scale for value in raw_activity]
        activities[za] = curve
        epsilon = selected_counts.get(za, 0) * event_weight / activity_ref
        for index, value in enumerate(curve):
            output_rows.append({
                "time_bin_id": int(base_rows[index]["time_bin_id"]),
                "day_mid": float(base_rows[index]["day_mid"]),
                "ZA": za,
                "nuclide": item["nuclide"],
                "half_life_s": half_life,
                "day15_activity_Bq": activity_ref,
                "activity_Bq": value,
                "activity_scale_to_day15": value / activity_ref,
                "selected_events_day15": selected_counts.get(za, 0),
                "selection_response_cps_per_Bq": epsilon,
                "selected_rate_cps": value * epsilon,
            })

    day15_total = sum(curve[day15_index] for curve in activities.values())
    delayed_day15 = sum(
        activities[za][day15_index]
        * selected_counts.get(za, 0)
        * event_weight
        / float(inventory[za]["day15_activity_Bq"])
        for za in activities
    )
    require_close(
        delayed_day15,
        float(selected["selected_summary"]["rate_cps"]),
        "nuclide-response delayed day-15 rate",
    )
    audit = {
        "status": "PASS_NEUTRON_DRIVER_NUCLIDE_ACTIVITY_AND_SELECTION_RESPONSE",
        "nuclides_in_inventory": len(inventory),
        "day15_total_activity_Bq": day15_total,
        "selected_nuclides": [
            {
                **row,
                "day15_activity_Bq": inventory[int(row["ZA"])]["day15_activity_Bq"],
                "selection_response_cps_per_Bq": (
                    int(row["selected_events"])
                    * event_weight
                    / inventory[int(row["ZA"])]["day15_activity_Bq"]
                ),
            }
            for row in selected["by_nuclide"]
        ],
        "day15_selected_rate_cps": delayed_day15,
        "production_driver": "live-PARMA neutron flux ratio in each trajectory bin",
        "day15_anchor": (
            "Each NUBASE-corrected nuclide inventory is anchored to its retained "
            "day-15 S3d activity before applying its selected-event response."
        ),
    }
    return activities, output_rows, audit


def crossing(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def time_or_extrapolate(days: list[float], values: list[float], threshold: float) -> float:
    value = crossing(days, values, threshold)
    if value is not None:
        return value
    return days[-1] * (threshold / values[-1]) ** 2


def mission_fold(
    response: dict[str, Any],
    scales: list[dict[str, str]],
    base_rows: list[dict[str, str]],
    activities: dict[int, list[float]],
    selected: dict[str, Any],
    prompt_occupancy: dict[str, dict[str, float | int]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    primary = response["primary_authority"]
    w2 = primary["step05"]["windows"]["w2_510p58_511p42"]
    physical = w2["physical_reference_flux"]
    uncertainty = physical["uncertainty_95"]
    prompt_components = {
        row["tag"]: row for row in uncertainty["prompt_components"]
    }
    if set(prompt_components) != set(PROMPT_TAGS):
        raise FoldError(f"prompt component set changed: {sorted(prompt_components)}")

    day15_index = next(
        index for index, row in enumerate(base_rows)
        if math.isclose(float(row["day_mid"]), DAY15)
    )
    selected_counts = {
        int(row["ZA"]): int(row["selected_events"])
        for row in selected["by_nuclide"]
    }
    inventory = groundstate_inventory()
    event_weight = float(selected["selected_summary"]["event_weight_cps"])

    delayed_curve: list[float] = []
    for index in range(len(base_rows)):
        rate = 0.0
        for za, curve in activities.items():
            count = selected_counts.get(za, 0)
            if count == 0:
                continue
            epsilon = count * event_weight / float(inventory[za]["day15_activity_Bq"])
            rate += curve[index] * epsilon
        delayed_curve.append(rate)

    delayed_day15 = float(physical["delayed_background_cps"])
    require_close(delayed_curve[day15_index], delayed_day15, "delayed fold day-15 anchor")

    prompt_day15 = float(physical["prompt_background_cps"])
    atm_day15 = float(physical["atm511_background_cps"])
    signal_day15 = float(physical["signal_cps_at_reference_flux"])
    delayed_upper_day15 = float(uncertainty["delayed_background_upper95_cps"])
    atm_upper_day15 = float(uncertainty["atm511_background_upper95_cps"])
    signal_lower_day15 = float(uncertainty["signal_cps_lower95_at_reference_flux"])

    base_day15 = base_rows[day15_index]
    delayed_occ_ratio = (
        float(primary["step05"]["occupancy_day15"]["delayed"]["rate_hz"])
        / float(base_day15["delayed_event_rate_hz"])
    )
    atm_occ_ratio = (
        float(primary["step05"]["occupancy_day15"]["atm511_sidecar"]["rate_hz"])
        / float(base_day15["atm511_event_rate_hz"])
    )

    cumulative_signal = 0.0
    cumulative_background = 0.0
    cumulative_signal_lower = 0.0
    cumulative_background_upper = 0.0
    elapsed_s = 0.0
    days: list[float] = []
    central_z: list[float] = []
    conservative_z: list[float] = []
    timeline: list[dict[str, Any]] = []

    for index, base in enumerate(base_rows):
        family_scale = {
            tag: float(scales[index][f"scale_{tag}"])
            for tag in PROMPT_TAGS
        }
        prompt_rate = sum(
            float(prompt_components[tag]["rate_cps"]) * family_scale[tag]
            for tag in PROMPT_TAGS
        )
        prompt_upper = sum(
            float(prompt_components[tag]["rate_upper95_cps"]) * family_scale[tag]
            for tag in PROMPT_TAGS
        )
        prompt_occ = sum(
            float(prompt_occupancy[tag]["rate_hz_day15"]) * family_scale[tag]
            for tag in PROMPT_TAGS
        )
        delayed_rate = delayed_curve[index]
        delayed_scale = delayed_rate / delayed_day15
        delayed_upper = delayed_upper_day15 * delayed_scale
        total_activity = sum(curve[index] for curve in activities.values())
        total_activity_day15 = sum(curve[day15_index] for curve in activities.values())
        delayed_occ = (
            float(base_day15["delayed_event_rate_hz"])
            * (total_activity / total_activity_day15)
            * delayed_occ_ratio
        )
        atm_scale = float(base["atm511_phi_4pi_scale_to_day15"])
        science_scale = float(base["science_atm_scale_to_day15"])
        atm_rate = atm_day15 * atm_scale
        atm_upper = atm_upper_day15 * atm_scale
        signal_rate = signal_day15 * science_scale
        signal_lower = signal_lower_day15 * science_scale
        atm_occ = float(base["atm511_event_rate_hz"]) * atm_occ_ratio
        occupancy = prompt_occ + delayed_occ + atm_occ
        live = math.exp(-occupancy * COINCIDENCE_WINDOW_S)
        background = prompt_rate + delayed_rate + atm_rate
        background_upper = prompt_upper + delayed_upper + atm_upper
        dt_s = float(base["dt_s"])

        cumulative_signal += signal_rate * live * dt_s
        cumulative_background += background * live * dt_s
        cumulative_signal_lower += signal_lower * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        elapsed_s += dt_s
        z = cumulative_signal / math.sqrt(cumulative_background)
        z_conservative = cumulative_signal_lower / math.sqrt(cumulative_background_upper)
        day = elapsed_s / SECONDS_PER_DAY
        days.append(day)
        central_z.append(z)
        conservative_z.append(z_conservative)

        record: dict[str, Any] = {
            "time_bin_id": int(base["time_bin_id"]),
            "day_mid": float(base["day_mid"]),
            "elapsed_stop_day": day,
            "dt_s": dt_s,
            "prompt_old_scalar": float(base["prompt_scale_to_day15"]),
            "prompt_family_response_scale": prompt_rate / prompt_day15,
            "delayed_selected_response_scale": delayed_scale,
            "atm511_scale": atm_scale,
            "science_scale": science_scale,
            "prompt_event_rate_hz": prompt_occ,
            "delayed_event_rate_hz": delayed_occ,
            "atm511_event_rate_hz": atm_occ,
            "coincidence_occupancy_rate_hz": occupancy,
            "accidental_live_factor": live,
            "prompt_final_cps_noacc": prompt_rate,
            "delayed_final_cps_noacc": delayed_rate,
            "atm511_final_cps_noacc": atm_rate,
            "background_final_cps_noacc": background,
            "signal_final_cps_noacc": signal_rate,
            "prompt_final_upper95_cps_noacc": prompt_upper,
            "delayed_final_upper95_cps_noacc": delayed_upper,
            "atm511_final_upper95_cps_noacc": atm_upper,
            "background_final_upper95_cps_noacc": background_upper,
            "signal_final_lower95_cps_noacc": signal_lower,
            "cumulative_source_counts": cumulative_signal,
            "cumulative_background_counts": cumulative_background,
            "cumulative_source_lower95_counts": cumulative_signal_lower,
            "cumulative_background_upper95_counts": cumulative_background_upper,
            "counting_Z": z,
            "counting_Z_conservative95": z_conservative,
        }
        for tag in PROMPT_TAGS:
            record[f"prompt_scale_{tag}"] = family_scale[tag]
        timeline.append(record)

    day15_row = timeline[day15_index]
    require_close(day15_row["prompt_final_cps_noacc"], prompt_day15, "prompt fold day-15 anchor")
    require_close(day15_row["atm511_final_cps_noacc"], atm_day15, "atmospheric fold day-15 anchor")
    require_close(day15_row["signal_final_cps_noacc"], signal_day15, "signal fold day-15 anchor")

    z20 = central_z[-1]
    z20_conservative = conservative_z[-1]
    summary = {
        "status": "PASS_S3D_W2_FAMILY_NUCLIDE_MISSION_FOLD",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "day15_selected_rates_cps": {
            "prompt": prompt_day15,
            "delayed": delayed_day15,
            "atm511": atm_day15,
            "background": prompt_day15 + delayed_day15 + atm_day15,
            "signal": signal_day15,
            "background_upper95": float(physical["background_cps"]) * 0.0
            + float(uncertainty["background_upper95_cps"]),
            "signal_lower95": signal_lower_day15,
        },
        "source_counts_20d": cumulative_signal,
        "background_counts_20d": cumulative_background,
        "source_lower95_counts_20d": cumulative_signal_lower,
        "background_upper95_counts_20d": cumulative_background_upper,
        "Z20d": z20,
        "Z20d_conservative95": z20_conservative,
        "flux_3sigma_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20,
        "flux_3sigma_20d_conservative95_ph_cm2_s": (
            REFERENCE_FLUX * 3.0 / z20_conservative
        ),
        "T3_day": time_or_extrapolate(days, central_z, 3.0),
        "T5_day": time_or_extrapolate(days, central_z, 5.0),
        "T3_day_conservative95": time_or_extrapolate(days, conservative_z, 3.0),
        "T5_day_conservative95": time_or_extrapolate(days, conservative_z, 5.0),
        "accidental_loss_min": min(1.0 - row["accidental_live_factor"] for row in timeline),
        "accidental_loss_max": max(1.0 - row["accidental_live_factor"] for row in timeline),
        "model": {
            "prompt": "sum of eight day-15 S3d selected family rates times live-PARMA family flux ratios",
            "delayed": "sum of neutron-driven nuclide activities times day-15 selected nuclide responses",
            "atm511": "independent semi-empirical 4pi line-flux scale retained from S3d Step06",
            "signal": "independent 511-keV atmospheric-transmission scale retained from S3d Step06",
            "coincidence": "prompt family occupancy plus total delayed activity occupancy plus atmospheric-line occupancy",
        },
    }
    return summary, timeline


def write_readme(payload: dict[str, Any]) -> None:
    mission = payload["mission"]
    delayed = payload["delayed_nuclide_response"]
    selected_text = ", ".join(
        f"{row['selected_events']} {row['nuclide']}"
        for row in delayed["selected_nuclides"]
    )
    README.write_text(
        "\n".join(
            [
                "# S3d family/nuclide mission-fold closure",
                "",
                f"Status: `{payload['status']}`",
                "",
                "This package performs no new Monte Carlo transport. It rebuilds only the",
                "81-bin mission-time analysis from retained S3d detector-response events,",
                "retained NUBASE-corrected neutron inventory, and live-PARMA analytic fluxes.",
                "",
                "## Closed implementation",
                "",
                "- Prompt: all eight day-15 S3d family response coefficients are modulated",
                "  independently by their live-PARMA trajectory flux ratios.",
                "- Delayed: each nuclide inventory is advanced with the neutron driver and",
                "  converted to a selected rate with its day-15 event response.",
                "- Atmospheric 511 and focused signal retain independent line-flux and",
                "  transmission scales; family-resolved prompt occupancy enters the live factor.",
                f"- The primary response seed selects {selected_text} in the final delayed stream.",
                "",
                "## Headline",
                "",
                f"- 20 d source counts: `{mission['source_counts_20d']:.12g}`",
                f"- 20 d background counts: `{mission['background_counts_20d']:.12g}`",
                f"- central Z20: `{mission['Z20d']:.12g}`",
                f"- finite-count conservative Z20: `{mission['Z20d_conservative95']:.12g}`",
                f"- central 3-sigma flux: `{mission['flux_3sigma_20d_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
                f"- conservative 3-sigma flux: `{mission['flux_3sigma_20d_conservative95_ph_cm2_s']:.12g}` ph cm^-2 s^-1",
                "",
                "The direct trajectory transports validate the e+, neutron, and gamma",
                "environmental modulation in the 480--550 keV diagnostic band. The final",
                "510.58--511.42 keV response coefficients remain the retained day-15 S3d",
                "selection; this package changes the time modulation, not the transport.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    required = [
        RESPONSE_SUMMARY,
        RESPONSE_CODE,
        EVENT_CATALOG,
        BASE_STEP06,
        GROUNDSTATE,
        DELAYED_SIM,
        TRAJECTORY_PROFILE,
        THREE_FAMILY_CURVE,
        TARGETED_AUDIT,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise FoldError(f"missing authorities: {missing}")

    response = read_json(RESPONSE_SUMMARY)
    if response.get("status") != "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE":
        raise FoldError(f"response authority status={response.get('status')!r}")
    scales = build_all8_scales()
    curve_audit = validate_three_family_parity(scales)
    selected, prompt_occupancy = build_selected_delayed_authority(response)

    base_rows = [
        row for row in read_csv(BASE_STEP06)
        if row["selection_id"] == "w2_510p58_511p42"
    ]
    base_rows.sort(key=lambda row: int(row["time_bin_id"]))
    if len(base_rows) != 81:
        raise FoldError(f"retained W2 Step06 has {len(base_rows)} bins")
    for scale, base in zip(scales, base_rows):
        if int(scale["time_bin_id"]) != int(base["time_bin_id"]):
            raise FoldError("PARMA and Step06 time-bin order differs")
        require_close(float(scale["day_mid"]), float(base["day_mid"]), "trajectory day")

    activities, activity_rows, activity_audit = integrate_nuclides(
        scales, base_rows, selected
    )
    mission, timeline = mission_fold(
        response,
        scales,
        base_rows,
        activities,
        selected,
        prompt_occupancy,
    )

    activity_fields = [
        "time_bin_id",
        "day_mid",
        "ZA",
        "nuclide",
        "half_life_s",
        "day15_activity_Bq",
        "activity_Bq",
        "activity_scale_to_day15",
        "selected_events_day15",
        "selection_response_cps_per_Bq",
        "selected_rate_cps",
    ]
    timeline_fields = list(timeline[0])
    write_csv(ACTIVITY_TIMELINE, activity_rows, activity_fields)
    write_csv(MISSION_TIMELINE, timeline, timeline_fields)

    old_mission = response["primary_authority"]["mission_fold"]
    payload = {
        "status": "PASS_S3D_EXISTING_DATA_FAMILY_NUCLIDE_MISSION_CLOSURE",
        "generated_at_utc": now_utc(),
        "claim": (
            "Existing-data replacement of the historical one-scalar S3d mission "
            "fold by the manuscript's family-resolved prompt and nuclide-response "
            "delayed equations; no new transport."
        ),
        "inputs": {
            rel(path): {
                "sha256": sha256(path) if path.stat().st_size < 600_000_000 else None,
                "bytes": path.stat().st_size,
            }
            for path in required
        },
        "curve_parity": curve_audit,
        "selected_delayed_lineage": {
            "authority": rel(SELECTED_DELAYED),
            "status": selected["status"],
            "response_seed": selected["response_seed"],
            "selected_summary": selected["selected_summary"],
            "by_nuclide": selected["by_nuclide"],
        },
        "prompt_occupancy_day15_by_family": prompt_occupancy,
        "delayed_nuclide_response": activity_audit,
        "mission": mission,
        "comparison_to_retired_scalar_fold": {
            "retired_status": old_mission["status"],
            "old_Z20d": old_mission["Z20d"],
            "new_Z20d": mission["Z20d"],
            "old_Z20d_conservative95": old_mission["Z20d_conservative95"],
            "new_Z20d_conservative95": mission["Z20d_conservative95"],
            "old_background_counts_20d": old_mission["background_counts_20d"],
            "new_background_counts_20d": mission["background_counts_20d"],
            "interpretation": (
                "Day-15 detector rates are unchanged; differences come only from "
                "the corrected trajectory response and occupancy scales."
            ),
        },
        "outputs": {
            "all8_scales": rel(ALL8_SCALES),
            "selected_delayed_nuclides": rel(SELECTED_DELAYED),
            "nuclide_activity_timeline": rel(ACTIVITY_TIMELINE),
            "mission_timeline": rel(MISSION_TIMELINE),
        },
        "scope": {
            "new_monte_carlo_transport": False,
            "day15_response_changed": False,
            "trajectory_modulation_changed": True,
            "optics_hardware_background_included": False,
        },
    }
    write_json(SUMMARY, payload)
    write_readme(payload)
    print(json.dumps({
        "status": payload["status"],
        "summary": rel(SUMMARY),
        "Z20d": mission["Z20d"],
        "Z20d_conservative95": mission["Z20d_conservative95"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
