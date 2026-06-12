#!/usr/bin/env python3
"""Shared Step06 time-axis fold for the Step08 sidecars.

Single implementation of the day-15 -> Step06 time-dependent counting fold
used by both ``build_line_window_sensitivity.py`` (per energy window, curve id
column ``selection_id``) and ``build_spatial_line_proxy.py`` (per spatial cut,
curve id column ``cut_id``). Output formatting is kept identical to the
previous duplicated copies so regenerated CSV/JSON values do not change.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

SECONDS_PER_DAY = 86400.0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def crossing_time(days: list[float], zvals: list[float], threshold: float) -> float | None:
    for i, value in enumerate(zvals):
        if value < threshold:
            continue
        if i == 0:
            return days[0]
        x0, x1 = days[i - 1], days[i]
        y0, y1 = zvals[i - 1], zvals[i]
        if y1 == y0:
            return x1
        return x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def extrapolated_time_days(final_day: float, final_z: float, threshold: float) -> float:
    if final_z <= 0.0:
        return math.inf
    if final_z >= threshold:
        return final_day
    return final_day * (threshold / final_z) ** 2


def time_dependent_fold(
    selection_id: str,
    prompt_cps_day15: float,
    delayed_cps_day15: float,
    science_cps_day15: float,
    reference_flux: float,
    *,
    id_field: str,
    step06_bg_csv: Path,
    day15_summary_json: Path,
) -> tuple[dict[str, float | str], list[dict[str, Any]]]:
    """Fold a day-15 detector response through the Step06 time-axis scales."""
    bg_rows = _read_csv(step06_bg_csv)
    summary = json.loads(day15_summary_json.read_text(encoding="utf-8"))
    catalog = summary["catalog"]["by_stream"]
    prompt_event_rate = float(catalog["prompt"]["rate_hz"])
    delayed_event_rate = float(catalog["delayed"]["rate_hz"])
    tau = float(summary["normalization"]["coincidence_window_s"])
    cumulative_source = 0.0
    cumulative_background = 0.0
    elapsed = 0.0
    days: list[float] = []
    zvals: list[float] = []
    curve_rows: list[dict[str, Any]] = []
    for row in bg_rows:
        dt_s = float(row["dt_s"])
        elapsed += dt_s
        prompt_scale = float(row["prompt_scale_to_day15"])
        delayed_scale = float(row["delayed_activity_scale_to_day15"])
        science_scale = float(row["science_atm_scale_to_day15"])
        live = math.exp(-(prompt_event_rate * prompt_scale + delayed_event_rate * delayed_scale) * tau)
        source = science_cps_day15 * science_scale * live
        background = (prompt_cps_day15 * prompt_scale + delayed_cps_day15 * delayed_scale) * live
        cumulative_source += source * dt_s
        cumulative_background += background * dt_s
        z = cumulative_source / math.sqrt(cumulative_background) if cumulative_background > 0.0 else 0.0
        elapsed_day = elapsed / SECONDS_PER_DAY
        days.append(elapsed_day)
        zvals.append(z)
        curve_rows.append(
            {
                id_field: selection_id,
                "time_bin_id": row["time_bin_id"],
                "day_mid": row["day_mid"],
                "elapsed_stop_day": f"{elapsed_day:.12g}",
                "dt_s": row["dt_s"],
                "prompt_scale_to_day15": f"{prompt_scale:.12e}",
                "delayed_activity_scale_to_day15": f"{delayed_scale:.12e}",
                "science_atm_scale_to_day15": f"{science_scale:.12e}",
                "accidental_live_factor": f"{live:.12e}",
                "source_cps": f"{source:.12e}",
                "background_cps": f"{background:.12e}",
                "cumulative_source_counts": f"{cumulative_source:.12e}",
                "cumulative_background_counts": f"{cumulative_background:.12e}",
                "counting_Z": f"{z:.12e}",
            }
        )
    final_day = days[-1] if days else 0.0
    final_z = zvals[-1] if zvals else 0.0
    t3 = crossing_time(days, zvals, 3.0)
    status = "mission_internal_crossing" if t3 is not None else "extrapolated_beyond_20d"
    t3_used = t3 if t3 is not None else extrapolated_time_days(final_day, final_z, 3.0)
    flux3 = reference_flux * 3.0 / final_z if final_z > 0.0 else math.inf
    return (
        {
            "Z20d_time_dependent_at_reference_flux": final_z,
            "T3_day_time_dependent": t3_used,
            "T3_time_dependent_status": status,
            "flux_3sigma_20d_time_dependent_ph_cm2_s": flux3,
            "total_source_counts_time_dependent": cumulative_source,
            "total_background_counts_time_dependent": cumulative_background,
        },
        curve_rows,
    )
