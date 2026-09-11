#!/usr/bin/env python3
"""Map previously skipped day-15 delayed-source nuclides to NUBASE ground states."""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path


FIX_ROOT = Path(__file__).resolve().parents[3]
STEP_DIR = FIX_ROOT / "stepwise_maintenance" / "step03_delay_source"
UNKNOWN_CSV = FIX_ROOT / "simulation" / "decay_from_buildup_equiv2602_cmfix" / "unknown_isotopes_day15.csv"
NUBASE = FIX_ROOT / "particle_sources" / "nubase_2020.txt"
BUILDUP_DIR = FIX_ROOT / "simulation" / "buildup_equiv2602_cmfix"
PROFILE_DIR = FIX_ROOT / "simulation" / "decay_from_buildup_equiv2602_cmfix" / "profiles"
OUT_CSV = STEP_DIR / "outputs" / "unknown_half_life_remap_day15.csv"
OUT_JSON = STEP_DIR / "outputs" / "unknown_half_life_remap_summary.json"


def load_build_fixed_module():
    path = FIX_ROOT / "code" / "particle_sources" / "build_fixed_delay_source.py"
    spec = importlib.util.spec_from_file_location("build_fixed_delay_source_for_remap", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def profile_zbins(vn: str, za: int, exc_keV: float) -> int:
    exc_token = int(round(exc_keV * 1.0e6))
    path = PROFILE_DIR / vn / f"ZA{za}_exc{exc_token}"
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob("radial_z*.dat"))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "tag",
        "VN",
        "ZA",
        "exc_keV",
        "nuclide",
        "old_reason",
        "old_detail",
        "resolved_status",
        "half_life_s",
        "nubase_why",
        "nubase_raw_value",
        "nubase_raw_unit",
        "nubase_line",
        "RP_yield",
        "TT_s",
        "estimated_activity_Bq_day15",
        "profile_zbins_present",
        "would_enter_source_if_regenerated",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    mod = load_build_fixed_module()
    unknown_rows = read_csv(UNKNOWN_CSV)
    nubase = mod.load_nubase_ground_half_lives(NUBASE)
    dat_files = sorted(BUILDUP_DIR.glob("Background_*_fullsphere20_rep*_part*.dat.inc1.dat"))
    tt_by_tag, rp = mod.parse_rp_from_dat(dat_files, non_gamma_div=8.0)

    out_rows: list[dict[str, object]] = []
    status_counter: Counter[str] = Counter()
    volume_counter: Counter[str] = Counter()
    profile_supported_activity = 0.0
    profile_supported_rows = 0
    unique_by_status: dict[str, set[str]] = defaultdict(set)

    for row in unknown_rows:
        tag = row["tag"]
        vn = row["VN"]
        za = int(row["ZA"])
        exc = float(row["exc_keV"])
        nuclide = row["nuclide"]
        info = nubase.get(za)
        rp_yield = rp.get((tag, vn, za, exc), 0.0)
        tt_s = tt_by_tag.get(tag, 0.0)
        zbins = profile_zbins(vn, za, exc)

        if info is None:
            status = "unmapped_in_local_nubase"
            half_life = ""
            why = ""
            raw_value = ""
            raw_unit = ""
            nubase_line = ""
            activity = 0.0
        else:
            half_life_float = float(info["half_life_s"])
            why = str(info["why"])
            raw_value = str(info["raw_value"])
            raw_unit = str(info["raw_unit"])
            nubase_line = int(info["line"])
            if math.isinf(half_life_float):
                status = "stable_ground_state"
                half_life = "inf"
                activity = 0.0
            else:
                status = "finite_ground_state_half_life"
                half_life = f"{half_life_float:.12e}"
                activity = mod.activity_after_exposure(rp_yield, tt_s, half_life_float, 15.0)

        would_enter = status == "finite_ground_state_half_life" and activity > 0.0 and zbins > 0
        if would_enter:
            profile_supported_rows += 1
            profile_supported_activity += activity

        status_counter[status] += 1
        volume_counter[vn] += 1
        unique_by_status[status].add(nuclide)
        out_rows.append(
            {
                "tag": tag,
                "VN": vn,
                "ZA": za,
                "exc_keV": f"{exc:.1f}",
                "nuclide": nuclide,
                "old_reason": row["reason"],
                "old_detail": row["detail"],
                "resolved_status": status,
                "half_life_s": half_life,
                "nubase_why": why,
                "nubase_raw_value": raw_value,
                "nubase_raw_unit": raw_unit,
                "nubase_line": nubase_line,
                "RP_yield": f"{rp_yield:.12e}",
                "TT_s": f"{tt_s:.12e}",
                "estimated_activity_Bq_day15": f"{activity:.12e}",
                "profile_zbins_present": zbins,
                "would_enter_source_if_regenerated": "yes" if would_enter else "no",
            }
        )

    write_csv(OUT_CSV, out_rows)
    summary = {
        "input_unknown_rows": len(unknown_rows),
        "input_unique_nuclides": len({row["nuclide"] for row in unknown_rows}),
        "all_input_exc_keV_values": sorted({float(row["exc_keV"]) for row in unknown_rows}),
        "status_rows": dict(sorted(status_counter.items())),
        "status_unique_nuclides": {key: len(value) for key, value in sorted(unique_by_status.items())},
        "status_unique_nuclide_names": {key: sorted(value) for key, value in sorted(unique_by_status.items())},
        "rows_by_volume": dict(volume_counter.most_common()),
        "profile_supported_finite_rows": profile_supported_rows,
        "profile_supported_estimated_activity_Bq_day15": profile_supported_activity,
        "outputs": {
            "csv": str(OUT_CSV.relative_to(FIX_ROOT)),
            "summary": str(OUT_JSON.relative_to(FIX_ROOT)),
        },
    }
    OUT_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
