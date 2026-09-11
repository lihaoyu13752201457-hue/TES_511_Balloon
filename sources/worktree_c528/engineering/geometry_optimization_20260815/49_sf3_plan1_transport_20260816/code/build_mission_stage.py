#!/usr/bin/env python3
"""Build fresh-SF3 and frozen-SE3 full-envelope 20-day mission folds.

This is a small-table-only stage-06 adapter.  It combines:

* fresh SF3 stage-02 transported-ground activation inventory;
* fresh stage-04 SF3 prompt/delayed response and SF3 full-envelope signal rows;
* frozen package-47 SE3 stage-02/stage-04 small tables;
* the frozen 81-node PARMA family scales and atmosphere trajectory.

No fresh SE3/S3d transport or receipt is required.  The frozen SE3
full-envelope signal is the completed package-47 small-table authority.  No
transport is launched and no SIM/catalog is opened or hashed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

from sf3_plan1_common import FAMILIES, PACKAGE_ROOT, PROFILE_ID, REPO_ROOT, utc_now


CONFIG = PACKAGE_ROOT / "analysis_inputs.json"
OUTPUT_ROOT = PACKAGE_ROOT / "outputs/06_mission"
GEOMETRIES = ("SE3", "SF3")
DAY15 = 15.0
SECONDS_PER_DAY = 86_400.0
COINCIDENCE_WINDOW_S = 1.0e-6
SOURCE_ELEVATION_DEG = 45.0
EXPECTED_MISSION_DAYS = 20.0
EXPECTED_NODES = 81
EXPECTED_SIGNAL_TRIALS = 37_194
EXPECTED_INPUT_AEFF_CM2 = 20.08476
REFERENCE_FLUX = 1.0e-4
FINAL_STAGE = "side_compton_fov_pass"
FINAL_WINDOW = "w2_510p58_511p42"
FINAL_RESPONSE = "measured"
FRESH_SIGNAL_SCOPE = "FULL_ENVELOPE_SF3_ONLY"
FROZEN_SE3_SIGNAL_SCOPE = "FULL_ENVELOPE_SE3_ONLY"
RUN_DISPOSITION = "RUN_83334"
ZERO_DISPOSITION = "SKIP_ZERO_A15"

SE3_ANCHORS = {
    "constant_day15_prompt_cps": 0.0,
    "constant_day15_delayed_cps": 0.06011336205846697,
    "constant_day15_background_cps": 0.06011336205846697,
    "transported_ground_activity_Bq": 1348.1419924456227,
    "mission20_source_counts": 1279.2886580217926,
    "mission20_source_lower95_counts": 1268.2334027102597,
    "mission20_background_counts": 98257.66904712601,
    "mission20_background_upper95_proxy_counts": 3588937.5957535803,
    "F3_20d_ph_cm2_s": 7.350822463201115e-05,
    "F3_20d_componentwise_proxy_ph_cm2_s": 4.4813103398753603e-04,
    "signal_selected_events": 21657,
    "signal_aeff_cm2": 11.69478,
}


def load_json(path: Path) -> dict[str, Any]:
    def reject(token: str) -> None:
        raise ValueError(f"non-finite JSON token {token!r}")

    value = json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_text(value: Any) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ) + "\n"


def csv_text(rows: Sequence[dict[str, Any]], fields: Sequence[str] | None = None) -> str:
    if not rows and fields is None:
        raise RuntimeError("cannot serialize a schema-less empty CSV")
    names = list(fields or rows[0].keys())
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=names, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def small_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def small_record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": small_sha256(path),
    }


def assert_close(name: str, observed: float, expected: float, *, rel: float = 2.0e-11, absolute: float = 2.0e-11) -> None:
    if not math.isclose(observed, expected, rel_tol=rel, abs_tol=absolute):
        raise RuntimeError(f"frozen anchor drift {name}: observed={observed:.17g}, expected={expected:.17g}")


def configured_paths(config: dict[str, Any]) -> dict[str, Path]:
    fresh02 = Path(config["outputs"]["stage_02"])
    fresh04 = Path(config["outputs"]["stage_04"])
    frozen_config = config["frozen_se3"]
    frozen_outputs = Path(frozen_config.get("plan1_outputs") or frozen_config["m05_outputs"])
    scales = Path(config["analysis"]["family_scales"])
    atmosphere = Path(config["analysis"]["atmosphere"])
    return {
        "fresh02_summary": fresh02 / "day15_summary.json",
        "fresh02_inventory": fresh02 / "day15_inventory.csv",
        "fresh02_source_index": fresh02 / "delayed_source_index.csv",
        "fresh04_summary": fresh04 / "summary.json",
        "fresh04_cutflow": fresh04 / "common_cutflow.csv",
        "fresh04_occupancy": fresh04 / "common_fullband_occupancy.csv",
        "fresh04_lineage": fresh04 / "selected_background_w2_lineage.csv",
        "fresh04_signal": fresh04 / "signal_acceptance_effective_area.csv",
        "fresh04_zero_provenance": fresh04 / "delayed_zero_A15_provenance.csv",
        "frozen02_summary": frozen_outputs / "02_activation/day15_summary.json",
        "frozen02_inventory": frozen_outputs / "02_activation/day15_inventory.csv",
        "frozen02_source_index": frozen_outputs / "02_activation/delayed_source_index.csv",
        "frozen04_summary": frozen_outputs / "04_common_response/summary.json",
        "frozen04_cutflow": frozen_outputs / "04_common_response/common_cutflow.csv",
        "frozen04_occupancy": frozen_outputs / "04_common_response/common_fullband_occupancy.csv",
        "frozen04_lineage": frozen_outputs / "04_common_response/selected_background_w2_lineage.csv",
        "frozen04_signal": frozen_outputs / "04_common_response/signal_acceptance_effective_area.csv",
        "frozen04_zero_provenance": frozen_outputs / "04_common_response/delayed_zero_A15_provenance.csv",
        "frozen06_summary": frozen_outputs / "06_mission/summary.json",
        "scales": scales,
        "scales_metadata": scales.with_suffix(".json"),
        "atmosphere": atmosphere,
    }


def family_scale(row: dict[str, str], family: str) -> float:
    value = float(row[f"scale_{family}_to_parma_reference"])
    if not math.isfinite(value) or value < 0.0:
        raise RuntimeError(f"invalid family scale for {family}: {value}")
    return value


def load_mission_axes(paths: dict[str, Path]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, Any]]]:
    scales = sorted(read_csv(paths["scales"]), key=lambda row: int(row["time_bin_id"]))
    atmosphere = sorted(read_csv(paths["atmosphere"]), key=lambda row: int(row["time_bin_id"]))
    if len(scales) != EXPECTED_NODES or len(atmosphere) != EXPECTED_NODES:
        raise RuntimeError(f"mission authorities are not both {EXPECTED_NODES} nodes")
    base: list[dict[str, Any]] = []
    previous_day = -math.inf
    for index, (scale_row, atmosphere_row) in enumerate(zip(scales, atmosphere)):
        scale_id = int(scale_row["time_bin_id"])
        atmosphere_id = int(atmosphere_row["time_bin_id"])
        day_scale = float(scale_row["day_mid"])
        day_atmosphere = float(atmosphere_row["day_mid"])
        if scale_id != index or atmosphere_id != index or scale_id != atmosphere_id:
            raise RuntimeError(f"mission time-bin identity mismatch at row {index}")
        if not math.isclose(day_scale, day_atmosphere, rel_tol=0.0, abs_tol=1.0e-12):
            raise RuntimeError(f"mission day axis mismatch at row {index}")
        if day_scale <= previous_day:
            raise RuntimeError("mission day axis is not strictly increasing")
        previous_day = day_scale
        transmission = float(atmosphere_row["T_atm_511"])
        if not (0.0 <= transmission <= 1.0):
            raise RuntimeError(f"invalid atmospheric transmission at row {index}")
        for family in FAMILIES:
            family_scale(scale_row, family)
        base.append({
            "time_bin_id": index,
            "day_mid": day_scale,
            "dt_s": float(atmosphere_row["dt_s"]),
            "T_atm_511": transmission,
            "depth_g_cm2": float(atmosphere_row["depth_g_cm2"]),
        })
    if not math.isclose(float(base[0]["day_mid"]), 0.0, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError("mission trajectory does not begin at day 0")
    if not math.isclose(float(base[-1]["day_mid"]), EXPECTED_MISSION_DAYS, rel_tol=0.0, abs_tol=1.0e-12):
        raise RuntimeError("mission trajectory does not end at day 20")
    if sum(math.isclose(float(row["day_mid"]), DAY15, rel_tol=0.0, abs_tol=1.0e-12) for row in base) != 1:
        raise RuntimeError("mission trajectory does not contain exactly one day-15 node")
    return scales, atmosphere, base


def advance_linear_inventory(
    number: float,
    production_left: float,
    production_right: float,
    decay_constant: float,
    dt_s: float,
) -> float:
    """Exact decay convolution for production linear over one interval."""
    if number < 0.0 or production_left < 0.0 or production_right < 0.0:
        raise RuntimeError("negative inventory/production passed to activation fold")
    if decay_constant <= 0.0 or dt_s <= 0.0:
        raise RuntimeError("activation fold requires positive decay constant and interval")
    x = decay_constant * dt_s
    if x < 1.0e-5:
        phi1 = 1.0 - x / 2.0 + x * x / 6.0 - x**3 / 24.0 + x**4 / 120.0
        phi2 = 0.5 - x / 6.0 + x * x / 24.0 - x**3 / 120.0 + x**4 / 720.0
    else:
        phi1 = -math.expm1(-x) / x
        phi2 = (1.0 - phi1) / x
    result = (
        number * math.exp(-x)
        + dt_s * (production_left * phi1 + (production_right - production_left) * phi2)
    )
    if result < -1.0e-12 or not math.isfinite(result):
        raise RuntimeError(f"invalid exact activation-fold result: {result}")
    return max(0.0, result)


def crossing_trapezoid(
    days: list[float],
    signal_rates: list[float],
    background_rates: list[float],
    threshold: float,
) -> float | None:
    """Find S/sqrt(B)=threshold inside a piecewise-linear-rate integral."""
    source = 0.0
    background = 0.0
    threshold2 = threshold * threshold
    for index in range(1, len(days)):
        dt_s = (days[index] - days[index - 1]) * SECONDS_PER_DAY
        source_next = source + 0.5 * (signal_rates[index - 1] + signal_rates[index]) * dt_s
        background_next = background + 0.5 * (background_rates[index - 1] + background_rates[index]) * dt_s
        if background_next > 0.0 and source_next * source_next >= threshold2 * background_next:
            left = 0.0
            right = 1.0
            for _ in range(60):
                fraction = 0.5 * (left + right)
                source_at = source + dt_s * (
                    signal_rates[index - 1] * fraction
                    + 0.5 * (signal_rates[index] - signal_rates[index - 1]) * fraction * fraction
                )
                background_at = background + dt_s * (
                    background_rates[index - 1] * fraction
                    + 0.5 * (background_rates[index] - background_rates[index - 1]) * fraction * fraction
                )
                if background_at > 0.0 and source_at * source_at >= threshold2 * background_at:
                    right = fraction
                else:
                    left = fraction
            return days[index - 1] + right * (days[index] - days[index - 1])
        source = source_next
        background = background_next
    return None


def crossing_or_extrapolation(crossing: float | None, day_last: float, z_last: float, threshold: float) -> float:
    if crossing is not None:
        return crossing
    if z_last <= 0.0:
        raise RuntimeError("cannot extrapolate a significance with non-positive endpoint Z")
    return day_last * (threshold / z_last) ** 2


def aggregate_inventory(
    rows: list[dict[str, str]],
    geometry: str,
) -> dict[tuple[str, str, int], dict[str, float]]:
    inventory: dict[tuple[str, str, int], dict[str, float]] = {}
    for row in rows:
        if row.get("geometry") != geometry or row.get("source_disposition") != "transported_ground_state":
            continue
        family = str(row["incident_family"])
        if family not in FAMILIES:
            raise RuntimeError(f"unexpected activation incident family: {family}")
        za = int(row["source_parent_ZA"])
        half_life = float(row["half_life_s"])
        activity = float(row["day15_activity_Bq"])
        production = float(row["production_rate_s-1"])
        if not all(math.isfinite(value) for value in (half_life, activity, production)):
            raise RuntimeError(f"non-finite transported activation row: {geometry}/{family}/{za}")
        if half_life <= 0.0 or activity <= 0.0 or production <= 0.0:
            raise RuntimeError(f"non-positive transported activation row: {geometry}/{family}/{za}")
        key = (geometry, family, za)
        item = inventory.setdefault(key, {
            "day15_activity_Bq": 0.0,
            "production_rate_s-1": 0.0,
            "half_life_s": half_life,
        })
        if not math.isclose(item["half_life_s"], half_life, rel_tol=2.0e-12, abs_tol=1.0e-15):
            raise RuntimeError(f"inconsistent half-life within parent aggregate: {key}")
        item["day15_activity_Bq"] = math.fsum((item["day15_activity_Bq"], activity))
        item["production_rate_s-1"] = math.fsum((item["production_rate_s-1"], production))
    return inventory


def activity_curves(
    base: list[dict[str, Any]],
    scales: list[dict[str, str]],
    inventory: dict[tuple[str, str, int], dict[str, float]],
) -> dict[tuple[str, str, int], list[float]]:
    curves: dict[tuple[str, str, int], list[float]] = {}
    for key, item in inventory.items():
        _, family, _ = key
        decay_constant = math.log(2.0) / item["half_life_s"]
        production_reference = item["production_rate_s-1"]
        number = 0.0
        curve = [0.0]
        for index in range(1, len(base)):
            dt_s = (float(base[index]["day_mid"]) - float(base[index - 1]["day_mid"])) * SECONDS_PER_DAY
            production_left = production_reference * family_scale(scales[index - 1], family)
            production_right = production_reference * family_scale(scales[index], family)
            number = advance_linear_inventory(
                number,
                production_left,
                production_right,
                decay_constant,
                dt_s,
            )
            curve.append(decay_constant * number)
        curves[key] = curve
    return curves


def final_components(rows: list[dict[str, str]], geometry: str) -> dict[tuple[str, str], dict[str, str]]:
    selected: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        if (
            row.get("geometry") != geometry
            or row.get("stream") not in ("prompt", "delayed")
            or row.get("response_state") != FINAL_RESPONSE
            or row.get("stage") != FINAL_STAGE
            or row.get("window_id") != FINAL_WINDOW
        ):
            continue
        key = (str(row["stream"]), str(row["family"]))
        if key in selected:
            raise RuntimeError(f"duplicate final common-response component: {geometry}/{key}")
        selected[key] = row
    expected = {(stream, family) for stream in ("prompt", "delayed") for family in FAMILIES}
    if set(selected) != expected:
        raise RuntimeError(f"final common-response component coverage mismatch for {geometry}: {sorted(set(selected) ^ expected)}")
    for key, row in selected.items():
        for field in ("weighted_value", "weighted_stat_sigma", "weighted_upper95"):
            value = float(row[field])
            if not math.isfinite(value) or value < 0.0:
                raise RuntimeError(f"invalid {field} for {geometry}/{key}")
        if float(row["weighted_upper95"]) + 1.0e-15 < float(row["weighted_value"]):
            raise RuntimeError(f"upper endpoint below central value for {geometry}/{key}")
    return selected


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes")


def registered_source_contract(
    source_rows: list[dict[str, str]],
    zero_rows: list[dict[str, str]],
    inventory_rows: list[dict[str, str]],
    components: dict[tuple[str, str], dict[str, str]],
    geometry: str,
) -> dict[str, dict[str, Any]]:
    """Validate RUN/ZERO cells without requiring a fake isotope sentinel."""
    source_index: dict[str, dict[str, str]] = {}
    for row in source_rows:
        if row.get("geometry") != geometry:
            raise RuntimeError(f"delayed-source index is not {geometry}-only")
        family = str(row.get("incident_family", ""))
        if family not in FAMILIES or family in source_index:
            raise RuntimeError(f"fresh registered delayed family differs: {family!r}")
        source_index[family] = row
    if set(source_index) != set(FAMILIES):
        raise RuntimeError("fresh delayed-source index does not close eight families")

    zero_index: dict[str, dict[str, str]] = {}
    for row in zero_rows:
        if row.get("geometry") != geometry:
            raise RuntimeError(f"zero-A15 provenance is not {geometry}-only")
        family = str(row.get("family", ""))
        if family not in FAMILIES or family in zero_index:
            raise RuntimeError(f"fresh zero-A15 provenance family differs: {family!r}")
        zero_index[family] = row

    inventory_by_family: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in inventory_rows:
        if row.get("geometry") != geometry:
            raise RuntimeError(f"inventory contains a non-{geometry} row")
        family = str(row.get("incident_family", ""))
        if family not in FAMILIES:
            raise RuntimeError(f"fresh inventory contains an unregistered family: {family!r}")
        inventory_by_family[family].append(row)

    registry: dict[str, dict[str, Any]] = {}
    expected_zero: set[str] = set()
    for family in FAMILIES:
        source = source_index[family]
        disposition = str(source.get("execution_disposition", ""))
        activity = float(source.get("transported_ground_activity_Bq", "nan"))
        transported = [
            row for row in inventory_by_family.get(family, [])
            if row.get("source_disposition") == "transported_ground_state"
        ]
        component = components[("delayed", family)]
        if disposition == RUN_DISPOSITION:
            if not math.isfinite(activity) or activity <= 0.0 or not transported:
                raise RuntimeError(f"RUN_83334 family lacks transported inventory: {family}")
            inventory_activity = math.fsum(
                float(row["day15_activity_Bq"]) for row in transported
            )
            if not math.isclose(
                inventory_activity, activity, rel_tol=2.0e-12, abs_tol=1.0e-12
            ):
                raise RuntimeError(f"RUN_83334 source-index/inventory activity differs: {family}")
            if family in zero_index:
                raise RuntimeError(f"RUN_83334 family appears in zero provenance: {family}")
            registry[family] = {
                "execution_disposition": disposition,
                "finite_A15_upper95_Bq": None,
                "inventory_state_rows": len(inventory_by_family.get(family, [])),
            }
            continue
        if disposition != ZERO_DISPOSITION:
            raise RuntimeError(f"unknown fresh delayed disposition for {family}: {disposition!r}")
        expected_zero.add(family)
        if activity != 0.0 or transported:
            raise RuntimeError(f"SKIP_ZERO_A15 family has transported inventory: {family}")
        provenance = zero_index.get(family)
        if provenance is None:
            raise RuntimeError(f"SKIP_ZERO_A15 family lacks finite-upper provenance: {family}")
        rate_upper = float(provenance.get("transported_ground_rate_upper95_s-1", "nan"))
        a15_upper = float(
            provenance.get("transported_ground_A15_upper95_Bq_conservative", "nan")
        )
        if not all(math.isfinite(value) and value > 0.0 for value in (rate_upper, a15_upper)):
            raise RuntimeError(f"SKIP_ZERO_A15 finite upper is invalid: {family}")
        if not math.isclose(rate_upper, a15_upper, rel_tol=0.0, abs_tol=1.0e-18):
            raise RuntimeError(f"SKIP_ZERO_A15 rate/A15 upper differs: {family}")
        if not math.isclose(
            float(source.get("transported_ground_rate_upper95_s-1", "nan")),
            rate_upper,
            rel_tol=0.0,
            abs_tol=1.0e-18,
        ) or not math.isclose(
            float(source.get("transported_ground_A15_upper95_Bq_conservative", "nan")),
            a15_upper,
            rel_tol=0.0,
            abs_tol=1.0e-18,
        ):
            raise RuntimeError(f"stage02/stage04 zero upper binding differs: {family}")
        upper_provenance = str(provenance.get("zero_A15_upper_provenance", ""))
        if (
            float(provenance.get("central_delayed_rate_cps", "nan")) != 0.0
            or float(provenance.get("transported_ground_activity_Bq", "nan")) != 0.0
            or not upper_provenance
            or not truthy(provenance.get("upper_excludes_known_and_unresolved_holdout"))
            or truthy(provenance.get("stage03_catalog_opened"))
            or truthy(provenance.get("SIM_opened"))
        ):
            raise RuntimeError(f"SKIP_ZERO_A15 provenance contract differs: {family}")
        if (
            int(component["selected_events"]) != 0
            or float(component["weighted_value"]) != 0.0
            or float(component["event_weight"]) != 0.0
            or component.get("execution_disposition") != ZERO_DISPOSITION
            or not math.isclose(
                float(component["transported_ground_A15_upper95_Bq_conservative"]),
                a15_upper,
                rel_tol=0.0,
                abs_tol=1.0e-18,
            )
        ):
            raise RuntimeError(f"SKIP_ZERO_A15 common-response central-zero closure differs: {family}")
        registry[family] = {
            "execution_disposition": disposition,
            "finite_rate_upper95_s-1": rate_upper,
            "finite_A15_upper95_Bq": a15_upper,
            "zero_A15_upper_provenance": upper_provenance,
            "upper_excludes_known_and_unresolved_holdout": True,
            "inventory_state_rows": len(inventory_by_family.get(family, [])),
            "exact_empty_inventory_family": family not in inventory_by_family,
            "detector_acceptance_upper": 1.0,
        }
    if set(zero_index) != expected_zero:
        raise RuntimeError("registered zero families and stage04 provenance differ")
    return registry


def occupancy_map(rows: list[dict[str, str]], geometry: str) -> dict[tuple[str, str], float]:
    selected: dict[tuple[str, str], float] = {}
    for row in rows:
        if row.get("geometry") != geometry or row.get("stream") not in ("prompt", "delayed"):
            continue
        key = (str(row["stream"]), str(row["family"]))
        if key in selected:
            raise RuntimeError(f"duplicate occupancy component: {geometry}/{key}")
        value = float(row["weighted_occupancy"])
        if not math.isfinite(value) or value < 0.0:
            raise RuntimeError(f"invalid occupancy for {geometry}/{key}")
        selected[key] = value
    expected = {(stream, family) for stream in ("prompt", "delayed") for family in FAMILIES}
    if set(selected) != expected:
        raise RuntimeError(f"occupancy coverage mismatch for {geometry}: {sorted(set(selected) ^ expected)}")
    return selected


def delayed_lineage(
    rows: list[dict[str, str]],
    geometry: str,
) -> tuple[Counter[tuple[str, str, int]], dict[tuple[str, str], float]]:
    counts: Counter[tuple[str, str, int]] = Counter()
    weights: dict[tuple[str, str], float] = {}
    for row in rows:
        if row.get("geometry") != geometry or row.get("stream") != "delayed":
            continue
        family = str(row["family"])
        if family not in FAMILIES:
            raise RuntimeError(f"unexpected delayed lineage family: {family}")
        za = int(row["source_parent_ZA"])
        weight = float(row["event_weight_cps"])
        if not math.isfinite(weight) or weight <= 0.0:
            raise RuntimeError(f"invalid delayed event weight: {geometry}/{family}")
        key = (geometry, family, za)
        counts[key] += 1
        cell = (geometry, family)
        old = weights.get(cell)
        if old is not None and not math.isclose(old, weight, rel_tol=2.0e-12, abs_tol=1.0e-18):
            raise RuntimeError(f"multiple delayed event weights inside one cell: {cell}")
        weights[cell] = weight
    return counts, weights


def validate_lineage_closure(
    geometry: str,
    components: dict[tuple[str, str], dict[str, str]],
    counts: Counter[tuple[str, str, int]],
    weights: dict[tuple[str, str], float],
    inventory: dict[tuple[str, str, int], dict[str, float]],
) -> None:
    for key in counts:
        if key not in inventory:
            raise RuntimeError(f"selected delayed parent lacks transported inventory row: {key}")
    for family in FAMILIES:
        observed = math.fsum(
            count * weights[(geometry, family)]
            for (g, f, _), count in counts.items()
            if g == geometry and f == family
        ) if (geometry, family) in weights else 0.0
        expected = float(components[("delayed", family)]["weighted_value"])
        if not math.isclose(observed, expected, rel_tol=2.0e-11, abs_tol=2.0e-14):
            raise RuntimeError(
                f"delayed lineage/cutflow closure mismatch {geometry}/{family}: {observed} != {expected}"
            )


def scoped_strings(value: Any, key_hint: str = "") -> list[str]:
    output: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            output.extend(scoped_strings(child, str(key).lower()))
    elif isinstance(value, list):
        for child in value:
            output.extend(scoped_strings(child, key_hint))
    elif isinstance(value, str) and (
        "scope" in key_hint or "signal" in key_hint or "eventlist" in key_hint or "injection" in key_hint
    ):
        output.append(value)
    return output


def normalized_scope(value: str) -> str:
    return "_".join(value.upper().replace("-", "_").split())


def select_full_envelope_signal(
    rows: list[dict[str, str]],
    common_summary: dict[str, Any],
    geometry: str,
    expected_scope: str,
) -> dict[str, dict[str, str]]:
    if common_summary.get("signal_scope") != expected_scope:
        raise RuntimeError(
            "stage04 summary must declare "
            f"signal_scope={expected_scope}; got "
            f"{common_summary.get('signal_scope')!r}"
        )
    selected: dict[str, dict[str, str]] = {}
    for row in rows:
        if (
            row.get("geometry") != geometry
            or row.get("response_state") != FINAL_RESPONSE
            or row.get("stage") != FINAL_STAGE
            or row.get("window_id") != FINAL_WINDOW
        ):
            continue
        geometry = str(row["geometry"])
        if geometry in selected:
            raise RuntimeError(f"duplicate fresh W2 full-envelope signal row: {geometry}")
        selected[geometry] = row
    if set(selected) != {geometry}:
        raise RuntimeError(
            f"{geometry}-only full-envelope signal coverage mismatch: "
            f"{sorted(set(selected) ^ {geometry})}"
        )
    if any(row.get("geometry") != geometry for row in rows):
        raise RuntimeError(f"stage04 signal table is not {geometry}-only")
    summary_scope = normalized_scope(" ".join(scoped_strings(common_summary)))
    for geometry, row in selected.items():
        if row.get("signal_scope") != expected_scope:
            raise RuntimeError(
                f"{geometry}: signal row must declare {expected_scope}"
            )
        row_scope = normalized_scope(" ".join(str(value) for value in row.values()))
        if "FULL_ENVELOPE" not in row_scope and "FULL_ENVELOPE" not in summary_scope:
            raise RuntimeError(f"{geometry}: fresh signal row lacks FULL_ENVELOPE scope evidence")
        explicit_scope = " ".join(
            str(row.get(name, ""))
            for name in ("signal_scope", "source_scope", "injection_scope", "eventlist_scope")
        )
        explicit_scope = normalized_scope(explicit_scope)
        if explicit_scope and "POST_BE" in explicit_scope and "FULL_ENVELOPE" not in explicit_scope:
            raise RuntimeError(f"{geometry}: post-Be signal is forbidden in SF3 mission fold")
        trials = int(row["trials"])
        selected_events = int(row["selected_events"])
        acceptance = float(row["acceptance"])
        acceptance_lower = float(row["acceptance_lower95"])
        aeff_input = float(row["input_optics_aeff_cm2"])
        aeff = float(row["selected_effective_area_cm2"])
        aeff_lower = float(row["selected_effective_area_lower95_cm2"])
        if trials != EXPECTED_SIGNAL_TRIALS or not (0 <= selected_events <= trials):
            raise RuntimeError(f"{geometry}: full-envelope fixed-N contract mismatch")
        assert_close(f"{geometry} input optics Aeff", aeff_input, EXPECTED_INPUT_AEFF_CM2, rel=2.0e-12, absolute=2.0e-12)
        assert_close(f"{geometry} signal acceptance", acceptance, selected_events / trials, rel=2.0e-12, absolute=2.0e-12)
        assert_close(f"{geometry} signal Aeff", aeff, aeff_input * acceptance, rel=2.0e-12, absolute=2.0e-12)
        assert_close(f"{geometry} signal lower Aeff", aeff_lower, aeff_input * acceptance_lower, rel=2.0e-12, absolute=2.0e-12)
        if not (0.0 <= acceptance_lower <= acceptance <= 1.0) or aeff_lower > aeff:
            raise RuntimeError(f"{geometry}: invalid full-envelope Clopper-Pearson ordering")
    return selected


def frozen_se3_static_anchors(paths: dict[str, Path]) -> dict[str, Any]:
    cutflow = read_csv(paths["frozen04_cutflow"])
    inventory_rows = read_csv(paths["frozen02_inventory"])
    components = final_components(cutflow, "SE3")
    prompt = math.fsum(float(components[("prompt", family)]["weighted_value"]) for family in FAMILIES)
    delayed = math.fsum(float(components[("delayed", family)]["weighted_value"]) for family in FAMILIES)
    activity = math.fsum(
        float(row["day15_activity_Bq"])
        for row in inventory_rows
        if row.get("geometry") == "SE3" and row.get("source_disposition") == "transported_ground_state"
    )
    assert_close("SE3 day15 prompt", prompt, SE3_ANCHORS["constant_day15_prompt_cps"])
    assert_close("SE3 day15 delayed", delayed, SE3_ANCHORS["constant_day15_delayed_cps"])
    assert_close("SE3 day15 background", prompt + delayed, SE3_ANCHORS["constant_day15_background_cps"])
    assert_close("SE3 transported activity", activity, SE3_ANCHORS["transported_ground_activity_Bq"])

    mission_summary = load_json(paths["frozen06_summary"])
    frozen_se3 = mission_summary["geometries"]["SE3"]
    for field, expected in (
        ("source_counts_20d", SE3_ANCHORS["mission20_source_counts"]),
        ("source_lower95_counts_20d", SE3_ANCHORS["mission20_source_lower95_counts"]),
        ("background_counts_20d", SE3_ANCHORS["mission20_background_counts"]),
        ("background_upper95_proxy_counts_20d", SE3_ANCHORS["mission20_background_upper95_proxy_counts"]),
        ("F3_20d_ph_cm2_s", SE3_ANCHORS["F3_20d_ph_cm2_s"]),
        ("F3_20d_componentwise_proxy_ph_cm2_s", SE3_ANCHORS["F3_20d_componentwise_proxy_ph_cm2_s"]),
    ):
        assert_close(f"frozen SE3 {field}", float(frozen_se3[field]), float(expected))

    signal_rows = read_csv(paths["frozen04_signal"])
    frozen_signal = [
        row
        for row in signal_rows
        if row.get("geometry") == "SE3"
        and row.get("response_state") == FINAL_RESPONSE
        and row.get("stage") == FINAL_STAGE
        and row.get("window_id") == FINAL_WINDOW
    ]
    if len(frozen_signal) != 1 or frozen_signal[0].get("signal_scope") != "FULL_ENVELOPE_SE3_ONLY":
        raise RuntimeError("frozen full-envelope SE3 signal row is not unique")
    assert_close("frozen SE3 trials", float(frozen_signal[0]["trials"]), float(EXPECTED_SIGNAL_TRIALS), rel=0.0, absolute=0.0)
    assert_close("frozen SE3 selected", float(frozen_signal[0]["selected_events"]), float(SE3_ANCHORS["signal_selected_events"]), rel=0.0, absolute=0.0)
    assert_close(
        "frozen SE3 Aeff",
        float(frozen_signal[0]["selected_effective_area_cm2"]),
        float(SE3_ANCHORS["signal_aeff_cm2"]),
    )
    return {
        "status": "PASS__FROZEN_SE3_PLAN1_BACKGROUND_ACTIVATION_AND_FULL_ENVELOPE_SIGNAL_ANCHORS",
        "day15_prompt_cps": prompt,
        "day15_delayed_cps": delayed,
        "day15_background_cps": prompt + delayed,
        "transported_ground_activity_Bq": activity,
        "mission20_source_counts": float(frozen_se3["source_counts_20d"]),
        "mission20_background_counts": float(frozen_se3["background_counts_20d"]),
        "mission20_background_upper95_proxy_counts": float(frozen_se3["background_upper95_proxy_counts_20d"]),
        "F3_20d_ph_cm2_s": float(frozen_se3["F3_20d_ph_cm2_s"]),
        "F3_20d_componentwise_proxy_ph_cm2_s": float(frozen_se3["F3_20d_componentwise_proxy_ph_cm2_s"]),
        "signal_selected_events": int(frozen_signal[0]["selected_events"]),
        "signal_aeff_cm2": float(frozen_signal[0]["selected_effective_area_cm2"]),
    }


def check_prerequisites(config_path: Path = CONFIG) -> dict[str, Any]:
    missing: list[str] = []
    authority_missing: list[str] = []
    errors: list[str] = []
    frozen_anchor_status: dict[str, Any] | None = None
    try:
        config = load_json(config_path)
    except Exception as exc:
        return {
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "FAIL__SF3_MISSION_CONFIG",
            "ready": False,
            "missing": [],
            "errors": [str(exc)],
            "sim_access_policy": "NO_SIM_ACCESS",
        }
    paths = configured_paths(config)
    fresh_pending_keys = {
        "fresh02_summary", "fresh02_inventory", "fresh02_source_index", "fresh04_summary",
        "fresh04_cutflow", "fresh04_occupancy", "fresh04_lineage",
        "fresh04_signal", "fresh04_zero_provenance",
    }
    for key, path in paths.items():
        if not path.is_file() or path.stat().st_size <= 0:
            if key in fresh_pending_keys:
                missing.append(str(path))
            else:
                authority_missing.append(str(path))
    if authority_missing:
        errors.append(
            "required frozen/mission small-table authority missing: "
            + "; ".join(sorted(authority_missing))
        )
    analysis = config.get("analysis", {})
    if int(analysis.get("mission_nodes", -1)) != EXPECTED_NODES:
        errors.append("configured mission_nodes is not 81")
    if not math.isclose(float(analysis.get("mission_days", -1)), EXPECTED_MISSION_DAYS, rel_tol=0.0, abs_tol=0.0):
        errors.append("configured mission_days is not 20")
    if not math.isclose(float(analysis.get("reference_flux_ph_cm2_s", -1)), REFERENCE_FLUX, rel_tol=0.0, abs_tol=0.0):
        errors.append("configured reference flux is not 1e-4 ph cm-2 s-1")
    try:
        frozen_config = config["frozen_se3"]
        assert_close(
            "configured SE3 mission background",
            float(frozen_config["background_mission20_counts"]),
            SE3_ANCHORS["mission20_background_counts"],
        )
        assert_close(
            "configured SE3 mission background upper proxy",
            float(frozen_config["background_upper95_proxy"]),
            SE3_ANCHORS["mission20_background_upper95_proxy_counts"],
        )
        if not truthy(frozen_config.get("fresh_transport_forbidden", False)):
            errors.append("frozen SE3 authority must forbid fresh transport")
    except Exception as exc:
        errors.append(f"configured frozen SE3 anchor mismatch: {exc}")

    frozen_keys = [key for key in paths if key.startswith("frozen")]
    if all(paths[key].is_file() and paths[key].stat().st_size > 0 for key in frozen_keys):
        try:
            frozen_anchor_status = frozen_se3_static_anchors(paths)
        except Exception as exc:
            errors.append(f"frozen SE3 authority drift: {exc}")
    if paths["scales"].is_file() and paths["atmosphere"].is_file():
        try:
            load_mission_axes(paths)
        except Exception as exc:
            errors.append(f"81-node mission authority invalid: {exc}")

    fresh02_ready = all(
        paths[key].is_file()
        for key in ("fresh02_summary", "fresh02_inventory", "fresh02_source_index")
    )
    if fresh02_ready:
        try:
            summary02 = load_json(paths["fresh02_summary"])
            if not str(summary02.get("status", "")).startswith("PASS"):
                errors.append("fresh SF3 stage02 summary is not PASS")
            inventory02 = read_csv(paths["fresh02_inventory"])
            if any(row.get("geometry") != "SF3" for row in inventory02):
                raise RuntimeError("fresh stage02 inventory is not SF3-only")
            aggregate_inventory(inventory02, "SF3")
        except Exception as exc:
            errors.append(f"fresh SF3 stage02 invalid: {exc}")

    fresh04_keys = (
        "fresh04_summary", "fresh04_cutflow", "fresh04_occupancy", "fresh04_lineage",
        "fresh04_signal", "fresh04_zero_provenance",
    )
    if all(paths[key].is_file() and paths[key].stat().st_size > 0 for key in fresh04_keys):
        try:
            summary04 = load_json(paths["fresh04_summary"])
            if not str(summary04.get("status", "")).startswith("PASS"):
                errors.append("fresh common-response summary is not PASS")
            cutflow = read_csv(paths["fresh04_cutflow"])
            occupancy = read_csv(paths["fresh04_occupancy"])
            lineage = read_csv(paths["fresh04_lineage"])
            for label, rows in (
                ("cutflow", cutflow), ("occupancy", occupancy), ("lineage", lineage),
            ):
                if label == "lineage" and not rows:
                    continue
                if {row.get("geometry") for row in rows} != {"SF3"}:
                    raise RuntimeError(f"fresh stage04 {label} is not SF3-only")
            components = final_components(cutflow, "SF3")
            occupancy_map(occupancy, "SF3")
            counts, weights = delayed_lineage(lineage, "SF3")
            if fresh02_ready:
                inventory_rows = read_csv(paths["fresh02_inventory"])
                inventory = aggregate_inventory(inventory_rows, "SF3")
                registry = registered_source_contract(
                    read_csv(paths["fresh02_source_index"]),
                    read_csv(paths["fresh04_zero_provenance"]),
                    inventory_rows,
                    components,
                    "SF3",
                )
                validate_lineage_closure("SF3", components, counts, weights, inventory)
                if len(registry) != len(FAMILIES):
                    raise RuntimeError("fresh registered source-cell closure differs")
            select_full_envelope_signal(
                read_csv(paths["fresh04_signal"]), summary04, "SF3", FRESH_SIGNAL_SCOPE
            )
        except Exception as exc:
            errors.append(f"fresh stage04 invalid: {exc}")

    if OUTPUT_ROOT.exists():
        if not OUTPUT_ROOT.is_dir() or any(OUTPUT_ROOT.iterdir()):
            errors.append(f"write-once mission output already exists/non-empty: {OUTPUT_ROOT}")
    ready = not missing and not errors
    if ready:
        status = "PASS__SF3_MISSION_PREREQUISITES_READY"
    elif errors:
        status = "FAIL__SF3_MISSION_AUTHORITY_OR_CONTRACT"
    else:
        status = "WAITING__SF3_MISSION_SMALL_TABLE_INPUTS"
    return {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "checked_at": utc_now(),
        "status": status,
        "ready": ready,
        "missing": sorted(set(missing)),
        "authority_missing": sorted(set(authority_missing)),
        "errors": errors,
        "frozen_se3_anchor_status": frozen_anchor_status,
        "output_root": str(OUTPUT_ROOT),
        "required_small_tables": {key: str(path) for key, path in paths.items()},
        "signal_gate": (
            "FRESH_STAGE04_FULL_ENVELOPE_SF3_ONLY__FROZEN_STAGE04_"
            "FULL_ENVELOPE_SE3_ONLY__NO_FRESH_SE3_RECEIPT_REQUIRED"
        ),
        "sim_access_policy": "NO_SIM_OPEN_OR_HASH__SMALL_CSV_JSON_ONLY",
    }


def fold_geometry(
    geometry: str,
    base: list[dict[str, Any]],
    scales: list[dict[str, str]],
    inventory: dict[tuple[str, str, int], dict[str, float]],
    cutflow_rows: list[dict[str, str]],
    occupancy_rows: list[dict[str, str]],
    lineage_rows: list[dict[str, str]],
    signal_row: dict[str, str] | None,
    source_registry: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    components = final_components(cutflow_rows, geometry)
    occupancy = occupancy_map(occupancy_rows, geometry)
    selected_counts, selected_weights = delayed_lineage(lineage_rows, geometry)
    validate_lineage_closure(geometry, components, selected_counts, selected_weights, inventory)
    curves = activity_curves(base, scales, inventory)
    source_registry = source_registry or {
        family: {"execution_disposition": RUN_DISPOSITION} for family in FAMILIES
    }
    if set(source_registry) != set(FAMILIES):
        raise RuntimeError(f"{geometry}: registered delayed family closure differs")
    day15_index = next(index for index, row in enumerate(base) if math.isclose(float(row["day_mid"]), DAY15, rel_tol=0.0, abs_tol=1.0e-12))

    family_activity = {
        family: [
            math.fsum(
                curve[index]
                for (g, f, _), curve in curves.items()
                if g == geometry and f == family
            )
            for index in range(len(base))
        ]
        for family in FAMILIES
    }
    family_activity_reference = {
        family: math.fsum(
            item["day15_activity_Bq"]
            for (g, f, _), item in inventory.items()
            if g == geometry and f == family
        )
        for family in FAMILIES
    }
    family_delayed_rate = {family: [0.0] * len(base) for family in FAMILIES}
    family_delayed_variance = {family: [0.0] * len(base) for family in FAMILIES}
    for key, count in selected_counts.items():
        g, family, _ = key
        if g != geometry:
            continue
        weight = selected_weights[(geometry, family)]
        reference_activity = inventory[key]["day15_activity_Bq"]
        for index, activity in enumerate(curves[key]):
            scaled_weight = weight * activity / reference_activity
            family_delayed_rate[family][index] += count * scaled_weight
            family_delayed_variance[family][index] += count * scaled_weight * scaled_weight

    slant_factor = 1.0 / math.sin(math.radians(SOURCE_ELEVATION_DEG))
    signal_available = signal_row is not None
    signal_scope = (
        str(signal_row.get("signal_scope", ""))
        if signal_available else "FULL_ENVELOPE_SIGNAL_UNAVAILABLE"
    )
    signal_aeff = float(signal_row["selected_effective_area_cm2"]) if signal_row else 0.0
    signal_aeff_lower = (
        float(signal_row["selected_effective_area_lower95_cm2"]) if signal_row else 0.0
    )
    timeline: list[dict[str, Any]] = []
    cumulative_signal = 0.0
    cumulative_background = 0.0
    cumulative_signal_lower = 0.0
    cumulative_background_upper = 0.0
    previous: dict[str, float] | None = None
    days: list[float] = []
    central_signal_rates: list[float] = []
    central_background_rates: list[float] = []
    proxy_signal_rates: list[float] = []
    proxy_background_rates: list[float] = []
    running_max_family_scale = {family: 0.0 for family in FAMILIES}
    for index, base_row in enumerate(base):
        prompt_rate = 0.0
        prompt_variance = 0.0
        prompt_upper = 0.0
        prompt_occupancy = 0.0
        delayed_rate = 0.0
        delayed_variance = 0.0
        delayed_upper = 0.0
        delayed_zero_A15_upper = 0.0
        delayed_occupancy = 0.0
        family_columns: dict[str, Any] = {}
        for family in FAMILIES:
            scale = family_scale(scales[index], family)
            running_max_family_scale[family] = max(running_max_family_scale[family], scale)
            prompt_component = components[("prompt", family)]
            prompt_family = float(prompt_component["weighted_value"]) * scale
            prompt_rate += prompt_family
            prompt_variance += (float(prompt_component["weighted_stat_sigma"]) * scale) ** 2
            prompt_upper += float(prompt_component["weighted_upper95"]) * scale
            prompt_occupancy += occupancy[("prompt", family)] * scale

            delayed_component = components[("delayed", family)]
            delayed_family = family_delayed_rate[family][index]
            delayed_rate += delayed_family
            delayed_variance += family_delayed_variance[family][index]
            reference_activity = family_activity_reference[family]
            activity_scale = family_activity[family][index] / reference_activity if reference_activity > 0.0 else 0.0
            day15_selected = float(delayed_component["weighted_value"])
            disposition = source_registry[family].get("execution_disposition", RUN_DISPOSITION)
            zero_A15_endpoint = 0.0
            if disposition == ZERO_DISPOSITION:
                if day15_selected != 0.0 or reference_activity != 0.0 or delayed_family != 0.0:
                    raise RuntimeError(f"{geometry}/{family}: zero-source central fold differs")
                finite_a15_upper = float(source_registry[family]["finite_A15_upper95_Bq"])
                # With zero day-0 inventory and unknown half-life, activity at
                # t>0 is bounded by the supremum of the production-rate upper
                # over prior trajectory nodes.  Detector acceptance is bounded
                # by one, so this Bq endpoint is also a conservative final-W2
                # cps endpoint.  At the exact day-0 node the inventory is zero.
                zero_A15_endpoint = (
                    0.0 if index == 0
                    else finite_a15_upper * running_max_family_scale[family]
                )
                delayed_upper += zero_A15_endpoint
                delayed_zero_A15_upper += zero_A15_endpoint
                delayed_scale = 0.0
            elif day15_selected > 0.0:
                delayed_scale = delayed_family / day15_selected
            elif reference_activity > 0.0:
                delayed_scale = activity_scale
            else:
                # A zero-source screening cell must retain a finite statistical
                # endpoint instead of being converted into a physics zero.
                delayed_scale = scale
            delayed_upper += float(delayed_component["weighted_upper95"]) * delayed_scale
            delayed_occupancy += occupancy[("delayed", family)] * activity_scale
            family_columns[f"prompt_{family}_cps"] = prompt_family
            family_columns[f"delayed_{family}_cps"] = delayed_family
            family_columns[f"delayed_{family}_zero_A15_upper95_proxy_cps"] = zero_A15_endpoint

        transmission_vertical = float(base_row["T_atm_511"])
        transmission_slant = transmission_vertical**slant_factor
        signal_noacc = REFERENCE_FLUX * signal_aeff * transmission_slant
        signal_lower_noacc = REFERENCE_FLUX * signal_aeff_lower * transmission_slant
        live = math.exp(-(prompt_occupancy + delayed_occupancy) * COINCIDENCE_WINDOW_S)
        background_noacc = prompt_rate + delayed_rate
        background_upper_noacc = prompt_upper + delayed_upper
        current = {
            "signal": signal_noacc * live,
            "background": background_noacc * live,
            "signal_lower": signal_lower_noacc * live,
            "background_upper": background_upper_noacc * live,
        }
        day = float(base_row["day_mid"])
        interval_s = 0.0 if previous is None else (day - days[-1]) * SECONDS_PER_DAY
        if previous is not None:
            cumulative_signal += 0.5 * (previous["signal"] + current["signal"]) * interval_s
            cumulative_background += 0.5 * (previous["background"] + current["background"]) * interval_s
            cumulative_signal_lower += 0.5 * (previous["signal_lower"] + current["signal_lower"]) * interval_s
            cumulative_background_upper += 0.5 * (previous["background_upper"] + current["background_upper"]) * interval_s
        previous = current
        z = cumulative_signal / math.sqrt(cumulative_background) if cumulative_background > 0.0 else 0.0
        z_proxy = cumulative_signal_lower / math.sqrt(cumulative_background_upper) if cumulative_background_upper > 0.0 else 0.0
        days.append(day)
        central_signal_rates.append(current["signal"])
        central_background_rates.append(current["background"])
        proxy_signal_rates.append(current["signal_lower"])
        proxy_background_rates.append(current["background_upper"])
        timeline.append({
            "geometry": geometry,
            "signal_scope": signal_scope,
            "time_bin_id": int(base_row["time_bin_id"]),
            "day_mid": day,
            "elapsed_day": day,
            "trajectory_quadrature_weight_s": float(base_row["dt_s"]),
            "integration_interval_from_previous_s": interval_s,
            "altitude_km": float(scales[index]["altitude_km"]),
            "prompt_occupancy_cps": prompt_occupancy,
            "delayed_occupancy_cps": delayed_occupancy,
            "accidental_live_factor": live,
            "T_atm_511_vertical": transmission_vertical,
            "T_atm_511_slant45": transmission_slant,
            "prompt_final_cps_noacc": prompt_rate,
            "delayed_final_cps_noacc": delayed_rate,
            "background_final_cps_noacc": background_noacc,
            "background_mc_counting_sigma_cps": math.sqrt(prompt_variance + delayed_variance),
            "signal_final_cps_noacc_at_reference_flux": signal_noacc,
            "prompt_componentwise_upper95_proxy_cps_noacc": prompt_upper,
            "delayed_componentwise_upper95_proxy_cps_noacc": delayed_upper,
            "delayed_zero_A15_upper95_proxy_cps_noacc": delayed_zero_A15_upper,
            "background_componentwise_upper95_proxy_cps_noacc": background_upper_noacc,
            "signal_lower95_cps_noacc_at_reference_flux": signal_lower_noacc,
            "cumulative_source_counts": cumulative_signal,
            "cumulative_background_counts": cumulative_background,
            "cumulative_source_lower95_counts": cumulative_signal_lower,
            "cumulative_background_upper95_proxy_counts": cumulative_background_upper,
            "counting_Z": z,
            "counting_Z_componentwise_proxy": z_proxy,
            **family_columns,
        })

    static_prompt = math.fsum(float(components[("prompt", family)]["weighted_value"]) for family in FAMILIES)
    static_delayed = math.fsum(float(components[("delayed", family)]["weighted_value"]) for family in FAMILIES)
    static_activity = math.fsum(family_activity_reference.values())
    forward_activity_day15 = math.fsum(family_activity[family][day15_index] for family in FAMILIES)
    day15_row = timeline[day15_index]
    z20 = float(timeline[-1]["counting_Z"])
    z20_proxy = float(timeline[-1]["counting_Z_componentwise_proxy"])
    if signal_available and (z20 <= 0.0 or z20_proxy <= 0.0):
        raise RuntimeError(f"{geometry}: non-positive endpoint significance")
    t3 = crossing_trapezoid(days, central_signal_rates, central_background_rates, 3.0) if signal_available else None
    t5 = crossing_trapezoid(days, central_signal_rates, central_background_rates, 5.0) if signal_available else None
    t3_proxy = crossing_trapezoid(days, proxy_signal_rates, proxy_background_rates, 3.0) if signal_available else None
    t5_proxy = crossing_trapezoid(days, proxy_signal_rates, proxy_background_rates, 5.0) if signal_available else None
    summary = {
        "geometry": geometry,
        "signal_scope": signal_scope,
        "signal_absolute_eligible": signal_available,
        "signal_ratio_eligible": signal_available,
        "signal_trials": int(signal_row["trials"]) if signal_row else None,
        "signal_selected_events": int(signal_row["selected_events"]) if signal_row else None,
        "selected_effective_area_cm2": signal_aeff if signal_available else None,
        "selected_effective_area_lower95_cm2": signal_aeff_lower if signal_available else None,
        "constant_environment_day15_reference": {
            "transported_activity_Bq": static_activity,
            "prompt_final_cps": static_prompt,
            "delayed_final_cps": static_delayed,
            "background_final_cps": static_prompt + static_delayed,
        },
        "trajectory_day15_node": day15_row,
        "trajectory_day15_to_constant_environment_ratio": {
            "transported_activity": forward_activity_day15 / static_activity if static_activity > 0.0 else None,
            "prompt_final": float(day15_row["prompt_final_cps_noacc"]) / static_prompt if static_prompt > 0.0 else None,
            "delayed_final": float(day15_row["delayed_final_cps_noacc"]) / static_delayed if static_delayed > 0.0 else None,
            "background_final": float(day15_row["background_final_cps_noacc"]) / (static_prompt + static_delayed) if static_prompt + static_delayed > 0.0 else None,
        },
        "source_counts_20d": cumulative_signal,
        "background_counts_20d": cumulative_background,
        "source_lower95_counts_20d": cumulative_signal_lower,
        "background_upper95_proxy_counts_20d": cumulative_background_upper,
        "Z20d": z20,
        "Z20d_componentwise_proxy": z20_proxy,
        "T3_day": crossing_or_extrapolation(t3, days[-1], z20, 3.0) if signal_available else None,
        "T5_day": crossing_or_extrapolation(t5, days[-1], z20, 5.0) if signal_available else None,
        "T3_day_componentwise_proxy": crossing_or_extrapolation(t3_proxy, days[-1], z20_proxy, 3.0) if signal_available else None,
        "T5_day_componentwise_proxy": crossing_or_extrapolation(t5_proxy, days[-1], z20_proxy, 5.0) if signal_available else None,
        "T3_status": ("CROSSED_WITHIN_20D" if t3 is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY") if signal_available else "NO_SIGNAL",
        "T5_status": ("CROSSED_WITHIN_20D" if t5 is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY") if signal_available else "NO_SIGNAL",
        "T3_componentwise_proxy_status": ("CROSSED_WITHIN_20D" if t3_proxy is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY") if signal_available else "NO_SIGNAL",
        "T5_componentwise_proxy_status": ("CROSSED_WITHIN_20D" if t5_proxy is not None else "NOT_REACHED__SQRT_TIME_EXTRAPOLATION_ONLY") if signal_available else "NO_SIGNAL",
        "F3_20d_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20 if signal_available else None,
        "F3_20d_componentwise_proxy_ph_cm2_s": REFERENCE_FLUX * 3.0 / z20_proxy if signal_available else None,
        "zero_A15_proxy_contract": {
            "families": [
                family for family in FAMILIES
                if source_registry[family].get("execution_disposition") == ZERO_DISPOSITION
            ],
            "central_rate": "EXACT_ZERO",
            "endpoint": (
                "finite_A15_upper95_Bq * running_max_family_scale_through_node * "
                "detector_acceptance_upper_1"
            ),
            "day0_endpoint": 0.0,
            "inventory_sentinel_created": False,
            "provenance": {
                family: source_registry[family]
                for family in FAMILIES
                if source_registry[family].get("execution_disposition") == ZERO_DISPOSITION
            },
        },
        "accidental_loss_min": min(1.0 - float(row["accidental_live_factor"]) for row in timeline),
        "accidental_loss_max": max(1.0 - float(row["accidental_live_factor"]) for row in timeline),
    }
    return timeline, summary


def comparison_rows(summaries: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    se3 = summaries["SE3"]
    sf3 = summaries["SF3"]
    def ratio(numerator: float, denominator: float) -> float | None:
        return numerator / denominator if denominator > 0.0 else None

    f3_ratio = float(sf3["F3_20d_ph_cm2_s"]) / float(se3["F3_20d_ph_cm2_s"])
    f3_proxy_ratio = (
        float(sf3["F3_20d_componentwise_proxy_ph_cm2_s"])
        / float(se3["F3_20d_componentwise_proxy_ph_cm2_s"])
    )
    source_ratio = float(sf3["source_counts_20d"]) / float(se3["source_counts_20d"])
    source_lower_ratio = (
        float(sf3["source_lower95_counts_20d"])
        / float(se3["source_lower95_counts_20d"])
    )
    background_ratio = (
        float(sf3["background_counts_20d"]) / float(se3["background_counts_20d"])
    )
    background_upper_ratio = (
        float(sf3["background_upper95_proxy_counts_20d"])
        / float(se3["background_upper95_proxy_counts_20d"])
    )
    assert_close(
        "central F3 ratio identity",
        f3_ratio,
        math.sqrt(background_ratio) / source_ratio,
        rel=2.0e-12,
        absolute=2.0e-12,
    )
    assert_close(
        "proxy F3 ratio identity",
        f3_proxy_ratio,
        math.sqrt(background_upper_ratio) / source_lower_ratio,
        rel=2.0e-12,
        absolute=2.0e-12,
    )
    ratios = {
        "status": "PASS__FRESH_SF3_VS_FROZEN_SE3_FULL_ENVELOPE_RATIO",
        "F3_SF3_over_SE3_full_envelope": f3_ratio,
        "F3_componentwise_proxy_SF3_over_SE3_full_envelope": f3_proxy_ratio,
        "Z20_SF3_over_SE3_full_envelope": float(sf3["Z20d"]) / float(se3["Z20d"]),
        "Z20_componentwise_proxy_SF3_over_SE3_full_envelope": (
            float(sf3["Z20d_componentwise_proxy"])
            / float(se3["Z20d_componentwise_proxy"])
        ),
        "S20_SF3_over_SE3_full_envelope": source_ratio,
        "S20_lower_SF3_over_SE3_full_envelope": source_lower_ratio,
        "B20_SF3_over_SE3": background_ratio,
        "B20_upper_proxy_SF3_over_SE3": background_upper_ratio,
        "Aeff_SF3_over_SE3_full_envelope": (
            float(sf3["selected_effective_area_cm2"])
            / float(se3["selected_effective_area_cm2"])
        ),
        "day15_prompt_SF3_over_frozen_SE3": (
            ratio(
                float(sf3["constant_environment_day15_reference"]["prompt_final_cps"]),
                float(se3["constant_environment_day15_reference"]["prompt_final_cps"]),
            )
        ),
        "day15_delayed_SF3_over_frozen_SE3": (
            ratio(
                float(sf3["constant_environment_day15_reference"]["delayed_final_cps"]),
                float(se3["constant_environment_day15_reference"]["delayed_final_cps"]),
            )
        ),
        "fresh_se3_receipt_required": False,
        "fullstat_trigger_threshold": 0.75,
        "fullstat_triggered": f3_ratio <= 0.75,
    }
    fields = (
        "row_role", "geometry", "signal_scope", "ratio_eligible", "signal_trials",
        "signal_selected_events", "selected_effective_area_cm2", "selected_effective_area_lower95_cm2",
        "constant_day15_prompt_cps", "constant_day15_delayed_cps", "constant_day15_background_cps",
        "source_counts_20d", "source_lower95_counts_20d", "background_counts_20d",
        "background_upper95_proxy_counts_20d", "Z20d", "Z20d_componentwise_proxy",
        "F3_20d_ph_cm2_s", "F3_20d_componentwise_proxy_ph_cm2_s",
        "F3_ratio_to_frozen_full_envelope_SE3", "F3_proxy_ratio_to_frozen_full_envelope_SE3",
        "ratio_denominator_scope", "comparison_note",
    )
    rows: list[dict[str, Any]] = []
    for geometry in GEOMETRIES:
        item = summaries[geometry]
        static = item["constant_environment_day15_reference"]
        is_sf3 = geometry == "SF3"
        rows.append({
            "row_role": (
                "FROZEN_SE3_PLAN1_FULL_ENVELOPE_CONTROL"
                if geometry == "SE3"
                else "FRESH_SF3_PLAN1_FULL_ENVELOPE_CANDIDATE"
            ),
            "geometry": geometry,
            "signal_scope": item["signal_scope"],
            "ratio_eligible": True,
            "signal_trials": item["signal_trials"],
            "signal_selected_events": item["signal_selected_events"],
            "selected_effective_area_cm2": item["selected_effective_area_cm2"],
            "selected_effective_area_lower95_cm2": item["selected_effective_area_lower95_cm2"],
            "constant_day15_prompt_cps": static["prompt_final_cps"],
            "constant_day15_delayed_cps": static["delayed_final_cps"],
            "constant_day15_background_cps": static["background_final_cps"],
            "source_counts_20d": item["source_counts_20d"],
            "source_lower95_counts_20d": item["source_lower95_counts_20d"],
            "background_counts_20d": item["background_counts_20d"],
            "background_upper95_proxy_counts_20d": item["background_upper95_proxy_counts_20d"],
            "Z20d": item["Z20d"],
            "Z20d_componentwise_proxy": item["Z20d_componentwise_proxy"],
            "F3_20d_ph_cm2_s": item["F3_20d_ph_cm2_s"],
            "F3_20d_componentwise_proxy_ph_cm2_s": item["F3_20d_componentwise_proxy_ph_cm2_s"],
            "F3_ratio_to_frozen_full_envelope_SE3": f3_ratio if is_sf3 else 1.0,
            "F3_proxy_ratio_to_frozen_full_envelope_SE3": f3_proxy_ratio if is_sf3 else 1.0,
            "ratio_denominator_scope": FROZEN_SE3_SIGNAL_SCOPE,
            "comparison_note": (
                "Fresh SF3 candidate divided by frozen package-47 SE3 Plan-1 control."
                if is_sf3
                else "Frozen package-47 SE3 Plan-1 full-envelope control; no SE3 rerun."
            ),
        })
    for row in rows:
        if tuple(row) != fields:
            raise RuntimeError("internal comparison-row schema drift")
    return rows, ratios


def build(config_path: Path = CONFIG, output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    prereq = check_prerequisites(config_path)
    if not prereq["ready"]:
        raise RuntimeError(json.dumps(prereq, indent=2, ensure_ascii=False))
    config = load_json(config_path)
    paths = configured_paths(config)
    frozen_anchors = frozen_se3_static_anchors(paths)
    scales, _, base = load_mission_axes(paths)
    fresh02 = read_csv(paths["fresh02_inventory"])
    frozen02 = read_csv(paths["frozen02_inventory"])
    fresh04_summary = load_json(paths["fresh04_summary"])
    frozen04_summary = load_json(paths["frozen04_summary"])
    fresh_signal = select_full_envelope_signal(
        read_csv(paths["fresh04_signal"]), fresh04_summary, "SF3", FRESH_SIGNAL_SCOPE
    )
    frozen_signal = select_full_envelope_signal(
        read_csv(paths["frozen04_signal"]),
        frozen04_summary,
        "SE3",
        FROZEN_SE3_SIGNAL_SCOPE,
    )

    fresh_cutflow = read_csv(paths["fresh04_cutflow"])
    fresh_occupancy = read_csv(paths["fresh04_occupancy"])
    fresh_lineage = read_csv(paths["fresh04_lineage"])
    frozen_cutflow = read_csv(paths["frozen04_cutflow"])
    frozen_occupancy = read_csv(paths["frozen04_occupancy"])
    frozen_lineage = read_csv(paths["frozen04_lineage"])
    fresh_source_registry = registered_source_contract(
        read_csv(paths["fresh02_source_index"]),
        read_csv(paths["fresh04_zero_provenance"]),
        fresh02,
        final_components(fresh_cutflow, "SF3"),
        "SF3",
    )
    frozen_source_registry = registered_source_contract(
        read_csv(paths["frozen02_source_index"]),
        read_csv(paths["frozen04_zero_provenance"]),
        frozen02,
        final_components(frozen_cutflow, "SE3"),
        "SE3",
    )
    inventories = {
        "SF3": aggregate_inventory(fresh02, "SF3"),
        "SE3": aggregate_inventory(frozen02, "SE3"),
    }
    sources = {
        "SF3": (fresh_cutflow, fresh_occupancy, fresh_lineage),
        "SE3": (frozen_cutflow, frozen_occupancy, frozen_lineage),
    }
    source_registries = {
        "SF3": fresh_source_registry,
        "SE3": frozen_source_registry,
    }
    signals = {
        "SF3": fresh_signal["SF3"],
        "SE3": frozen_signal["SE3"],
    }
    timeline: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, Any]] = {}
    for geometry in GEOMETRIES:
        cutflow, occupancy, lineage = sources[geometry]
        rows, summary = fold_geometry(
            geometry,
            base,
            scales,
            inventories[geometry],
            cutflow,
            occupancy,
            lineage,
            signals[geometry],
            source_registries[geometry],
        )
        timeline.extend(rows)
        summaries[geometry] = summary

    se3 = summaries["SE3"]
    assert_close("folded SE3 background20", se3["background_counts_20d"], SE3_ANCHORS["mission20_background_counts"])
    assert_close(
        "folded SE3 background20 upper proxy",
        se3["background_upper95_proxy_counts_20d"],
        SE3_ANCHORS["mission20_background_upper95_proxy_counts"],
    )
    static_se3 = se3["constant_environment_day15_reference"]
    assert_close("folded SE3 static prompt", static_se3["prompt_final_cps"], SE3_ANCHORS["constant_day15_prompt_cps"])
    assert_close("folded SE3 static delayed", static_se3["delayed_final_cps"], SE3_ANCHORS["constant_day15_delayed_cps"])
    assert_close("folded SE3 static activity", static_se3["transported_activity_Bq"], SE3_ANCHORS["transported_ground_activity_Bq"])
    assert_close("folded SE3 source20", se3["source_counts_20d"], SE3_ANCHORS["mission20_source_counts"])
    assert_close(
        "folded SE3 source20 lower",
        se3["source_lower95_counts_20d"],
        SE3_ANCHORS["mission20_source_lower95_counts"],
    )
    assert_close("folded SE3 F3", se3["F3_20d_ph_cm2_s"], SE3_ANCHORS["F3_20d_ph_cm2_s"])
    assert_close(
        "folded SE3 F3 proxy",
        se3["F3_20d_componentwise_proxy_ph_cm2_s"],
        SE3_ANCHORS["F3_20d_componentwise_proxy_ph_cm2_s"],
    )

    comparison, ratios = comparison_rows(summaries)
    summary = {
        "schema_version": 1,
        "profile_id": PROFILE_ID,
        "status": "PASS__SF3_VS_FROZEN_SE3_FULL_ENVELOPE_81NODE_F3_COMPLETE",
        "created_at": utc_now(),
        "geometries": summaries,
        "fair_full_envelope_ratios": ratios,
        "ratio_contract": {
            "numerator": "fresh SF3 full-envelope signal plus fresh SF3 background/activation",
            "denominator": "frozen package-47 SE3 Plan-1 full-envelope signal plus background/activation",
            "status": "PASS__COMPARABLE_PLAN1_STATISTICS_AND_SHARED_MISSION_FOLD",
            "fresh_se3_receipt_required": False,
            "forbidden_denominator": "old post-Be conditional SE3 signal",
            "central_identity": "sqrt(B20_SF3/B20_SE3)/(S20_SF3/S20_SE3)",
            "componentwise_proxy_identity": (
                "sqrt(B20_upper_SF3/B20_upper_SE3)/(S20_lower_SF3/S20_lower_SE3)"
            ),
        },
        "fullstat_decision": {
            "metric": "F3_SF3_over_SE3_full_envelope",
            "threshold_max": 0.75,
            "observed": ratios["F3_SF3_over_SE3_full_envelope"],
            "triggered": ratios["fullstat_triggered"],
            "proxy_is_not_an_additional_trigger": True,
        },
        "frozen_se3_anchor_audit": frozen_anchors,
        "mission_contract": {
            "duration_days": EXPECTED_MISSION_DAYS,
            "time_nodes": EXPECTED_NODES,
            "reference_flux_ph_cm2_s": REFERENCE_FLUX,
            "reference_flux_surface": "top_of_atmosphere",
            "source_elevation_deg": SOURCE_ELEVATION_DEG,
            "coincidence_window_s": COINCIDENCE_WINDOW_S,
            "zero_inventory_at_day0": True,
            "activation_fold": "exact piecewise-linear-source decay convolution; no day15 reanchoring",
            "rate_integration": "trapezoidal over the 81 trajectory nodes",
            "family_scaling": "frozen energy-integrated PARMA ratios to the reference environment",
        },
        "uncertainty_contract": {
            "central": "fresh SF3 weighted transport-MC background and fixed-N full-envelope signal central Aeff",
            "componentwise_proxy": (
                "SF3 prompt family Garwood upper plus delayed parent/activity-mixture upper, "
                "SKIP_ZERO_A15 finite activation upper with detector acceptance<=1, and SF3 "
                "signal CP lower; not joint 95% coverage"
            ),
            "zero_A15": {
                "registered_families": [
                    family for family in FAMILIES
                    if fresh_source_registry[family]["execution_disposition"] == ZERO_DISPOSITION
                ],
                "central": "EXACT_ZERO__NO_INVENTORY_SENTINEL",
                "proxy_endpoint": (
                    "A15_upper95 * running maximum PARMA family scale through node * "
                    "detector acceptance upper 1"
                ),
                "holdout": "reported separately; excluded from zero-RP upper",
            },
            "not_propagated": [
                "time-correlated reuse of the same transport events across trajectory nodes",
                "full-band occupancy uncertainty in accidental live factor",
                "activation-yield, source-position mixture, optics, atmosphere, and trajectory systematics",
            ],
        },
        "known_exclusions": [
            "81-node trajectory is synthetic rather than flight telemetry",
            "zero day-0 inventory excludes pre-flight and ground activation",
            "family scalar fold fixes within-family spectrum, angular distribution, response, and activation yield",
            "PARMA driver W=114.6 versus source-contract W=118.3 is used only through driver-internal relative ratios",
            "historical post-Be signal is excluded from all geometry ratios",
            "SE3 is reused only from frozen package-47 small-table authorities; no SE3 transport rerun",
            "screening statistics are not publication-level/full-stat closure",
        ],
        "input_authorities": {
            key: small_record(path)
            for key, path in paths.items()
        },
        "sim_access_policy": "NO_SIM_OPEN_OR_HASH__SMALL_CSV_JSON_ONLY",
        "authority_boundary": "PLAN1_APPROX_ONE_THIRD_MISSION_SCREEN__NO_AUTOMATIC_GEOMETRY_PROMOTION",
    }
    timeline_text = csv_text(timeline)
    comparison_text = csv_text(comparison)
    summary_text = json_text(summary)
    output.parent.mkdir(parents=True, exist_ok=True)
    output_is_empty = output.is_dir() and not any(output.iterdir())
    if output.exists() and not output_is_empty:
        raise RuntimeError(f"refusing to overwrite mission output: {output}")
    work = output.parent / f".{output.name}.work-{os.getpid()}"
    if work.exists():
        raise RuntimeError(f"stale mission work directory: {work}")
    work.mkdir(parents=True, exist_ok=False)
    try:
        (work / "mission_timeline.csv").write_text(timeline_text, encoding="utf-8")
        (work / "se3_vs_sf3_mission.csv").write_text(comparison_text, encoding="utf-8")
        (work / "summary.json").write_text(summary_text, encoding="utf-8")
        if output_is_empty:
            output.rmdir()
        os.replace(work, output)
    finally:
        if work.exists():
            shutil.rmtree(work)
    return summary


def self_test() -> dict[str, Any]:
    half_life = 10.0
    decay = math.log(2.0) / half_life
    production = 3.0
    dt_s = 4.0
    observed = advance_linear_inventory(0.0, production, production, decay, dt_s)
    expected = production * (1.0 - math.exp(-decay * dt_s)) / decay
    assert_close("constant-production analytic fold", observed, expected, rel=2.0e-14, absolute=2.0e-14)
    days = [0.0, 1.0]
    crossing = crossing_trapezoid(days, [1.0, 1.0], [1.0, 1.0], 3.0)
    if crossing is None:
        raise AssertionError("constant-rate crossing was not found")
    assert_close("constant-rate crossing", crossing, 9.0 / SECONDS_PER_DAY, rel=2.0e-12, absolute=2.0e-12)
    if SIGNAL_RATIO_UNAVAILABLE != "UNAVAILABLE_BY_USER_SCOPE":
        raise AssertionError("machine-readable unavailable status drift")
    synthetic_fresh_signal_geometries = {"SF3"}
    if synthetic_fresh_signal_geometries != {"SF3"} or "SE3" in synthetic_fresh_signal_geometries:
        raise AssertionError("SF3-only fresh signal scope self-test failed")
    zero_family = FAMILIES[0]
    selected_family = FAMILIES[1]
    base = [
        {"time_bin_id": index, "day_mid": day, "dt_s": 0.0,
         "T_atm_511": 1.0, "depth_g_cm2": 0.0}
        for index, day in enumerate((0.0, 15.0, 20.0))
    ]
    scales = []
    for index, day in enumerate((0.0, 15.0, 20.0)):
        row: dict[str, str] = {
            "time_bin_id": str(index), "day_mid": str(day), "altitude_km": "35"
        }
        row.update({f"scale_{family}_to_parma_reference": "1" for family in FAMILIES})
        scales.append(row)
    cutflow: list[dict[str, str]] = []
    occupancy: list[dict[str, str]] = []
    for stream in ("prompt", "delayed"):
        for family in FAMILIES:
            is_selected = stream == "delayed" and family == selected_family
            central = 0.1 if is_selected else (0.01 if stream == "prompt" else 0.0)
            cutflow.append({
                "geometry": "SF3", "stream": stream, "family": family,
                "response_state": FINAL_RESPONSE, "stage": FINAL_STAGE,
                "window_id": FINAL_WINDOW, "selected_events": "1" if is_selected else "0",
                "event_weight": "0.1" if is_selected else ("0.01" if stream == "prompt" else "0"),
                "weighted_value": str(central), "weighted_stat_sigma": str(central),
                "weighted_upper95": str(central * 2.0),
                "execution_disposition": (
                    ZERO_DISPOSITION if stream == "delayed" and family == zero_family
                    else RUN_DISPOSITION
                ),
                "transported_ground_A15_upper95_Bq_conservative": (
                    "0.125" if stream == "delayed" and family == zero_family else ""
                ),
            })
            occupancy.append({
                "geometry": "SF3", "stream": stream, "family": family,
                "weighted_occupancy": "0",
            })
    inventory = {
        ("SF3", family, 26056 + index): {
            "day15_activity_Bq": 1.0,
            "production_rate_s-1": 1.0,
            "half_life_s": 10.0 * SECONDS_PER_DAY,
        }
        for index, family in enumerate(FAMILIES)
        if family != zero_family
    }
    inventory_rows = [{
        "geometry": "SF3", "incident_family": family,
        "source_disposition": "transported_ground_state",
        "day15_activity_Bq": "1",
    } for family in FAMILIES if family != zero_family]
    lineage = [{
        "geometry": "SF3", "stream": "delayed", "family": selected_family,
        "source_parent_ZA": str(next(key[2] for key in inventory if key[1] == selected_family)),
        "event_weight_cps": "0.1",
    }]
    signal = {
        "trials": str(EXPECTED_SIGNAL_TRIALS), "selected_events": "100",
        "selected_effective_area_cm2": "0.5",
        "selected_effective_area_lower95_cm2": "0.4",
    }
    source_rows = [{
        "geometry": "SF3", "incident_family": family,
        "execution_disposition": ZERO_DISPOSITION if family == zero_family else RUN_DISPOSITION,
        "transported_ground_activity_Bq": "0" if family == zero_family else "1",
        "transported_ground_rate_upper95_s-1": "0.125" if family == zero_family else "",
        "transported_ground_A15_upper95_Bq_conservative": (
            "0.125" if family == zero_family else ""
        ),
    } for family in FAMILIES]
    zero_rows = [{
        "geometry": "SF3", "family": zero_family,
        "central_delayed_rate_cps": "0", "transported_ground_activity_Bq": "0",
        "transported_ground_rate_upper95_s-1": "0.125",
        "transported_ground_A15_upper95_Bq_conservative": "0.125",
        "zero_A15_upper_provenance": "finite 3.688879/sumTT",
        "upper_excludes_known_and_unresolved_holdout": "true",
        "stage03_catalog_opened": "false", "SIM_opened": "false",
    }]
    zero_registry = fresh_registered_source_contract(
        source_rows, zero_rows, inventory_rows, final_components(cutflow, "SF3")
    )
    baseline_registry = {
        family: {"execution_disposition": RUN_DISPOSITION} for family in FAMILIES
    }
    _, with_zero = fold_geometry(
        "SF3", base, scales, inventory, cutflow, occupancy, lineage, signal, zero_registry
    )
    _, baseline = fold_geometry(
        "SF3", base, scales, inventory, cutflow, occupancy, lineage, signal, baseline_registry
    )
    if (
        any(key[1] == zero_family for key in inventory)
        or with_zero["background_counts_20d"] != baseline["background_counts_20d"]
        or with_zero["background_upper95_proxy_counts_20d"]
        <= baseline["background_upper95_proxy_counts_20d"]
        or with_zero["F3_20d_componentwise_proxy_ph_cm2_s"]
        <= baseline["F3_20d_componentwise_proxy_ph_cm2_s"]
        or not with_zero["zero_A15_proxy_contract"]["provenance"][zero_family][
            "exact_empty_inventory_family"
        ]
    ):
        raise AssertionError("RUN+exact-empty ZERO conservative mission proxy self-test failed")
    return {
        "schema_version": 1,
        "status": "PASS__SF3_MISSION_BUILDER_SELF_TEST",
        "checks": [
            "exact_piecewise_linear_activation_convolution",
            "piecewise_linear_rate_significance_crossing",
            "JSON_finite_output_contract",
            "SF3_only_fresh_signal_contract",
            "SE3_full_envelope_ratio_unavailable_by_user_scope",
            "RUN_plus_exact_empty_SKIPPED_ZERO_mission_fold",
            "zero_A15_central_unchanged",
            "zero_A15_finite_upper_acceptance_le_1_in_componentwise_proxy",
            "no_isotope_sentinel_for_exact_empty_family",
        ],
        "files_written": False,
        "sim_accessed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--check-prerequisites", action="store_true", help="read-only small-table readiness check")
    actions.add_argument("--status", action="store_true", help="alias of --check-prerequisites")
    actions.add_argument("--build", action="store_true", help="build stage06 small tables; no transport/SIM access")
    actions.add_argument("--self-test", action="store_true", help="run pure mission-math checks")
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.check_prerequisites or args.status:
            result = check_prerequisites(args.config.resolve())
        else:
            result = build(args.config.resolve(), args.output.resolve())
        print(json_text(result), end="")
        if (args.check_prerequisites or args.status) and not result.get("ready", False):
            return 2 if str(result.get("status", "")).startswith("WAITING__") else 1
        return 0
    except Exception as exc:
        print(json_text({
            "schema_version": 1,
            "profile_id": PROFILE_ID,
            "status": "FAIL__SF3_MISSION_BUILDER",
            "error": str(exc),
        }), end="")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
