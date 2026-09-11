from __future__ import annotations

import csv
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

PHASE_SPACE_REQUIRED = ("event_id", "E_keV", "x_mm", "y_mm", "z_mm", "weight", "source_tag")


def read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def direction_columns(row: dict[str, str]) -> tuple[str, str, str]:
    if {"dx", "dy", "dz"}.issubset(row):
        return ("dx", "dy", "dz")
    return ("ux", "uy", "uz")


def validate_phase_space(path: str | Path) -> dict[str, object]:
    rows = read_rows(path)
    if not rows:
        return {"ok": False, "n_rows": 0, "errors": ["empty phase-space file"]}
    errors: list[str] = []
    columns = set(rows[0])
    missing = [col for col in PHASE_SPACE_REQUIRED if col not in columns]
    if missing:
        errors.append("missing columns: " + ",".join(missing))
    try:
        dcols = direction_columns(rows[0])
    except Exception:
        errors.append("missing direction columns dx/dy/dz or ux/uy/uz")
        dcols = ("", "", "")
    for idx, row in enumerate(rows):
        if dcols[0]:
            dx, dy, dz = (float(row[col]) for col in dcols)
            mag = math.sqrt(dx * dx + dy * dy + dz * dz)
            if abs(mag - 1.0) > 1.0e-6:
                errors.append(f"row {idx} direction norm={mag:g}")
                break
        if "weight" in row and float(row["weight"]) <= 0.0:
            errors.append(f"row {idx} non-positive weight")
            break
    return {"ok": not errors, "n_rows": len(rows), "errors": errors}


def summarize_history(path: str | Path) -> dict[str, object]:
    rows = read_rows(path)
    counts: Counter[str] = Counter()
    per_ring: dict[int, Counter[str]] = defaultdict(Counter)
    prob_sums: dict[int, dict[str, float]] = defaultdict(lambda: {"p_diff": 0.0, "p_abs": 0.0, "p_trans": 0.0, "n": 0.0})
    for row in rows:
        stage = row.get("stage") or row.get("branch") or row.get("mode") or ""
        ring_id = int(row.get("ring_id", -1))
        counts[stage] += 1
        per_ring[ring_id][stage] += 1
        p_diff = _float_field(row, "p_reflect", "p_diff", "p_diff_raw")
        p_abs = _float_field(row, "p_absorb", "p_abs", "p_abs_raw")
        p_trans = _float_field(row, "p_transmit", "p_trans", "p_trans_raw")
        prob_sums[ring_id]["p_diff"] += p_diff
        prob_sums[ring_id]["p_abs"] += p_abs
        prob_sums[ring_id]["p_trans"] += p_trans
        prob_sums[ring_id]["n"] += 1.0
    mean_probs = {}
    for ring_id, sums in prob_sums.items():
        n = sums["n"] or 1.0
        mean_probs[str(ring_id)] = {
            "p_diff": sums["p_diff"] / n,
            "p_abs": sums["p_abs"] / n,
            "p_trans": sums["p_trans"] / n,
        }
    return {
        "n_rows": len(rows),
        "branch_counts": dict(counts),
        "per_ring_counts": {str(k): dict(v) for k, v in sorted(per_ring.items())},
        "mean_recorded_probabilities": mean_probs,
        "columns": list(rows[0]) if rows else [],
    }


def _float_field(row: dict[str, str], *names: str) -> float:
    for name in names:
        if name in row and row[name] != "":
            return float(row[name])
    return 0.0
