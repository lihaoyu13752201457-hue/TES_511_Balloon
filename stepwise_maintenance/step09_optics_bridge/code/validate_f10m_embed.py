#!/usr/bin/env python3
"""Validate that the f10m A1 optics profile is embeddable in new_geo_re."""

from __future__ import annotations

import gzip
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
STEP04 = ROOT / "stepwise_maintenance" / "step04_opticsim"
STEP09 = ROOT / "stepwise_maintenance" / "step09_optics_bridge"
AUTHORITY = STEP04 / "optics_aeff_authority_f10m_a1.json"
PROFILE_RUN = STEP04 / "outputs" / "opticsim_laue_bfull_f10m_a1_r2_3seed"
SUMMARY = STEP09 / "outputs_f10m_a1" / "step09_optics_bridge_summary.json"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def count_csv_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def count_sim_events(path: Path) -> int:
    n = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("SE"):
                n += 1
    return n


def first_eventlist_row(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                return line.split()
    return []


def main() -> int:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    authority = load_json(AUTHORITY)
    checks["authority_status"] = authority.get("status") == "RUN_AVAILABLE_F10M_PHASE0_EMBED_READY"
    checks["authority_aeff_range"] = 19.4 <= float(authority.get("aeff_511_cm2", 0.0)) <= 21.4
    checks["authority_strict_diffraction_gate"] = bool(authority.get("run_summary", {}).get("pass_strict_0p01_gate"))

    focal = PROFILE_RUN / "focal_crossings.csv"
    focal_rows = count_csv_data_rows(focal)
    focal_stats = authority.get("focal_stats", {})
    checks["profile_focal_crossings_exists"] = focal.exists() and focal_rows == int(focal_stats.get("diffracted_focal_rows", -1))

    summary = load_json(SUMMARY)
    bridge = summary.get("bridge", {})
    smoke = summary.get("smoke_transport", {})
    checks["bridge_status"] = summary.get("status") == "PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED"
    checks["bridge_profile"] = summary.get("profile") == "f10m_a1"
    checks["bridge_rows_match_authority"] = int(bridge.get("rows_written", 0)) == int(focal_stats.get("within_be_rows", -1))
    checks["bridge_radius_within_be"] = float(bridge.get("max_radius_cm", math.inf)) <= float(bridge.get("be_radius_cm", -math.inf)) + 1.0e-9
    checks["bridge_direction_to_detector"] = float(bridge.get("direction_uz_max", 1.0)) < 0.0

    eventlist = ROOT / bridge.get("eventlist", "")
    source = ROOT / bridge.get("source", "")
    smoke_source = ROOT / bridge.get("smoke_source", "")
    checks["eventlist_exists"] = eventlist.exists()
    checks["source_exists"] = source.exists()
    checks["smoke_source_exists"] = smoke_source.exists()

    first = first_eventlist_row(eventlist) if eventlist.exists() else []
    checks["eventlist_first_row_shape"] = len(first) >= 15
    if len(first) >= 11:
        details["first_eventlist_z_cm"] = float(first[7])
        details["first_eventlist_uz"] = float(first[10])
        checks["eventlist_z_plane"] = abs(float(first[7]) - float(bridge.get("z_plane_cm", math.nan))) <= 1.0e-9
        checks["eventlist_uz_negative"] = float(first[10]) < 0.0
    else:
        checks["eventlist_z_plane"] = False
        checks["eventlist_uz_negative"] = False

    sim = ROOT / smoke.get("sim", "")
    sim_events = count_sim_events(sim) if sim.exists() else 0
    checks["smoke_sim_exists"] = sim.exists()
    checks["smoke_sim_events_1000"] = sim_events == 1000

    details.update(
        {
            "authority": rel(AUTHORITY),
            "profile_run": rel(PROFILE_RUN),
            "bridge_summary": rel(SUMMARY),
            "aeff_511_cm2": authority.get("aeff_511_cm2"),
            "focal_rows": focal_rows,
            "within_be_rows": bridge.get("rows_written"),
            "eventlist": rel(eventlist),
            "source": rel(source),
            "smoke_source": rel(smoke_source),
            "smoke_sim": rel(sim),
            "smoke_sim_events": sim_events,
        }
    )

    ok = all(checks.values())
    out = {
        "status": "PASS_F10M_EMBED_READY" if ok else "FAIL_F10M_EMBED_NOT_READY",
        "claim_level": "L1_F10M_OPTICS_EMBED_READY",
        "checks": checks,
        "details": details,
    }
    out_path = STEP09 / "outputs_f10m_a1" / "f10m_embed_validation.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
