#!/usr/bin/env python3
"""Build response-convolved reference spectra and multiplicity diagnostics."""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
PACKAGE = Path(__file__).resolve().parents[1]
CLOSURE_SCRIPT = Path(__file__).resolve().with_name("build_o8_energy_response_closure.py")
SUMMARY = PACKAGE / "data/o8_energy_response_closure_summary.json"
OUT_SPECTRA = PACKAGE / "data/reference_response_spectra_480_550.csv"
OUT_MULTIPLICITY = PACKAGE / "data/reference_response_multiplicity.json"
BIN_WIDTH_KEV = 0.5


class SpectraError(RuntimeError):
    pass


def load_closure() -> Any:
    spec = importlib.util.spec_from_file_location("reference_response_spectra_closure", CLOSURE_SCRIPT)
    if spec is None or spec.loader is None:
        raise SpectraError(f"cannot import {CLOSURE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def bucket(multiplicity: np.ndarray) -> np.ndarray:
    return np.where(multiplicity == 1, "n1", np.where(multiplicity == 2, "n2", "n3plus"))


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS_O8_EVENT_LEVEL_420EV_FWHM_ENERGY_RESPONSE_CLOSURE":
        raise SpectraError(f"energy-response closure is not PASS: {summary.get('status')}")
    closure = load_closure()
    cat = closure.compact_event_catalog(closure.REFERENCE_CATALOG, "reference_spectra")
    step05, disk = closure.load_step05_selection()
    hits, totals, multiplicity = closure.measured_hits(
        cat,
        closure.PRIMARY_RESPONSE_SEED,
        apply_response=True,
        apply_threshold=True,
    )
    lo, hi = closure.WINDOWS["broad_480_550"]
    raw = (totals >= lo) & (totals < hi)
    active = raw & (cat.active_keV < closure.ACTIVE_VETO_THRESHOLD_KEV)
    keep = np.zeros(len(totals), dtype=bool)
    classes = np.full(len(totals), "not_evaluated", dtype=object)
    one = active & (multiplicity == 1)
    keep[one] = True
    classes[one] = "single"
    many = active & (multiplicity > int(step05.MAX_ENUM_HITS))
    keep[many] = True
    classes[many] = "reject_kept"
    for index in np.flatnonzero(
        active & (multiplicity >= 2) & (multiplicity <= int(step05.MAX_ENUM_HITS))
    ):
        accepted, classification = step05.side_keep_from_hits(
            closure._event_hits(cat, int(index), hits), disk, "keep"
        )
        keep[index] = bool(accepted)
        classes[index] = str(classification)
    final = active & keep

    edges = np.arange(lo, hi + BIN_WIDTH_KEV / 2.0, BIN_WIDTH_KEV)
    rows: list[dict[str, Any]] = []
    histograms: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    for stream in ("prompt", "delayed", "science"):
        smask = cat.stream == stream
        for stage, mask in (("raw", raw), ("active", active), ("compton", final)):
            selected = smask & mask
            rate_hist, _ = np.histogram(totals[selected], bins=edges, weights=cat.rate_hz[selected])
            event_hist, _ = np.histogram(totals[selected], bins=edges)
            histograms[(stream, stage)] = (rate_hist / BIN_WIDTH_KEV, event_hist)
    for index in range(len(edges) - 1):
        row: dict[str, Any] = {
            "energy_lo_keV": edges[index],
            "energy_hi_keV": edges[index + 1],
            "energy_center_keV": (edges[index] + edges[index + 1]) / 2.0,
        }
        for stream in ("prompt", "delayed", "science"):
            for stage in ("raw", "active", "compton"):
                rates, events = histograms[(stream, stage)]
                row[f"{stream}_{stage}_cps_per_keV"] = float(rates[index])
                row[f"{stream}_{stage}_events_per_bin"] = int(events[index])
        rows.append(row)

    OUT_SPECTRA.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SPECTRA.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    mult_payload: dict[str, Any] = {
        "status": "PASS_REFERENCE_RESPONSE_SPECTRA_MULTIPLICITY",
        "response_seed": closure.PRIMARY_RESPONSE_SEED,
        "window_keV": [lo, hi],
        "streams": {},
    }
    buckets = bucket(multiplicity)
    for stream in ("prompt", "delayed", "science"):
        smask = cat.stream == stream
        stage_payload: dict[str, Any] = {}
        for stage, mask in (("raw", raw), ("active", active), ("compton", final)):
            selected = smask & mask
            counts = {name: int(np.count_nonzero(selected & (buckets == name))) for name in ("n1", "n2", "n3plus")}
            counts["total"] = sum(counts.values())
            stage_payload[stage] = counts
        class_payload: dict[str, Any] = {}
        for name in ("n2", "n3plus"):
            selected = smask & active & (buckets == name)
            class_payload[name] = dict(sorted(Counter(str(value) for value in classes[selected]).items()))
        mult_payload["streams"][stream] = {
            "stages": stage_payload,
            "multi_hit_compton_class_after_active": class_payload,
        }
    OUT_MULTIPLICITY.write_text(
        json.dumps(mult_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": mult_payload["status"],
                "spectra": OUT_SPECTRA.relative_to(ROOT).as_posix(),
                "multiplicity": OUT_MULTIPLICITY.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
