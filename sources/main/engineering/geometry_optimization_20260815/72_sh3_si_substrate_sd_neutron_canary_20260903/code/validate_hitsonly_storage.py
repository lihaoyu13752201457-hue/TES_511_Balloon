#!/usr/bin/env python3
"""Validate everyeventwithhits against the same-seed full first 10k histories."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
BASELINE = (
    PACKAGE / "run/sh3_sisd_n_canary100k_20260903/pass/"
    "sh3_sisd_n_canary100k_20260903.inc1.id1.sim.gz"
)
CANDIDATE = (
    PACKAGE / "validation_run/sh3_sisd_n_hitsonly_validation10k_20260903/pass/"
    "sh3_sisd_n_hitsonly_validation10k_20260903.inc1.id1.sim.gz"
)
OUTPUT = PACKAGE / "HITSONLY_VALIDATION.json"
ID_RE = re.compile(r"^ID\s+(\d+)\s+(\d+)")
TES_RE = re.compile(r"^CC HIT TP_L[0-5]_\d+\s")
SI_PREFIX = "CC HIT Si_Substrate_Stack_side_entry_L"
BGO_PREFIXES = (
    "CC HIT SH3_BGO40_SideShield ",
    "CC HIT SH3_BGO40_FrontOpticalAnnulus ",
    "CC HIT SH3_BGO40_RearColdPortAnnulus ",
)


def active_hit(line: str) -> bool:
    return bool(
        TES_RE.match(line)
        or line.startswith(SI_PREFIX)
        or line.startswith(BGO_PREFIXES)
    )


def parse(path: Path, *, max_simulation_id: int | None = None) -> tuple[dict, int]:
    events: dict[int, dict[str, object]] = {}
    current_id: int | None = None
    current: dict[str, object] | None = None
    stored = 0
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as stream:
        for raw in stream:
            line = raw.strip()
            match = ID_RE.match(line)
            if match:
                simulation_id = int(match.group(2))
                if max_simulation_id is not None and simulation_id > max_simulation_id:
                    break
                current_id = simulation_id
                current = {"init": None, "hits": []}
                stored += 1
                continue
            if current is None or current_id is None:
                continue
            if line.startswith("IA INIT"):
                current["init"] = line
            elif active_hit(line):
                current["hits"].append(line)
            elif line == "SE":
                if current["hits"]:
                    events[current_id] = current
                current_id = None
                current = None
    # Cosima closes the last stored event with EN rather than a final SE.
    if current is not None and current_id is not None and current["hits"]:
        events[current_id] = current
    return events, stored


def main() -> int:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    baseline, baseline_stored = parse(BASELINE, max_simulation_id=10000)
    candidate, candidate_stored = parse(CANDIDATE)
    missing = sorted(set(baseline) - set(candidate))
    extra = sorted(set(candidate) - set(baseline))
    mismatches = []
    for event_id in sorted(set(baseline) & set(candidate)):
        if baseline[event_id] != candidate[event_id]:
            mismatches.append(event_id)
    result = {
        "schema_version": 1,
        "status": "PASS__EVERYEVENTWITHHITS_PRESERVES_ACTIVE_CC" if not (missing or extra or mismatches) else "FAIL__STORAGE_DRIFT",
        "same_seed": 209030031,
        "histories_compared": 10000,
        "baseline_records_scanned": baseline_stored,
        "candidate_records_stored": candidate_stored,
        "active_events": len(baseline),
        "si_positive_events": sum(
            any(hit.startswith(SI_PREFIX) for hit in event["hits"])
            for event in baseline.values()
        ),
        "missing_active_events": missing[:20],
        "extra_active_events": extra[:20],
        "mismatched_active_events": mismatches[:20],
        "comparison": "exact IA INIT and exact CC HIT lines for six TES, six Si, and three BGO volumes",
        "baseline_sim_bytes": BASELINE.stat().st_size,
        "candidate_sim_bytes": CANDIDATE.stat().st_size,
    }
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
