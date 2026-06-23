#!/usr/bin/env python3
"""Analyze a scratch old new_geo_re delayed SIM in the W2 line window.

The selection intentionally reuses the old new_geo_re Step05 parser and
Compton/FoV classification helpers. This script only evaluates one delayed SIM
and writes a compact JSON/CSV summary; it does not touch the old repo outputs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OLD_ROOT = Path("/home/ubuntu/codex_tes_511_sim/new_geo_re")
OLD_TOOLS = OLD_ROOT / "code" / "tools"
DEFAULT_LABEL = "old_new_geo_re_div8_exactpos_m50000_s260623"
W2_MIN_KEV = 510.58
W2_MAX_KEV = 511.42
WIDE_MIN_KEV = 480.0
WIDE_MAX_KEV = 550.0


def paths_for(label: str) -> dict[str, Path]:
    transport_dir = ROOT / "runs" / f"step02_delayed_transport_{label}"
    source_dir = ROOT / "runs" / f"step02_delay_fix_{label}"
    prefix = transport_dir / f"DelayedDecayOldNewGeoReDiv8Exactpos_{label}"
    return {
        "transport_dir": transport_dir,
        "source_dir": source_dir,
        "sim": prefix.with_suffix(".inc1.id1.sim.gz"),
        "source": source_dir / "activation_decay_day15_groundstate_fixed_exactpos.source",
        "manifest": source_dir / "exactpos_delayed_source_manifest.json",
        "summary": transport_dir / "old_new_geo_re_div8_exactpos_w2_delayed_summary.json",
        "events_csv": transport_dir / "old_new_geo_re_div8_exactpos_w2_selected_events.csv",
    }


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def parse_te(path: Path) -> float | None:
    if not path.exists():
        return None
    with open_text(path) as handle:
        for raw in handle:
            if raw.startswith("TE"):
                parts = raw.split()
                if len(parts) >= 2:
                    return float(parts[1])
    return None


def parse_source_activity_and_triggers(path: Path) -> tuple[float, int | None]:
    activity = 0.0
    triggers = None
    flux_re = re.compile(r"^\S+\.Flux\s+([-+0-9.eE]+)\s*$")
    trig_re = re.compile(r"^DecayRun\.Triggers\s+(\d+)\s*$")
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        fm = flux_re.match(line)
        if fm:
            activity += float(fm.group(1))
        tm = trig_re.match(line)
        if tm:
            triggers = int(tm.group(1))
    return activity, triggers


def load_old_step05_module():
    sys.path.insert(0, str(OLD_TOOLS))
    import make_complete_day15_report_ADR as old_step05  # type: ignore

    return old_step05


def event_stage(old_step05, cat: dict, idx: int, reject_policy: str, emin: float, emax: float) -> tuple[str | None, str | None]:
    e = float(cat["tes_total_keV"][idx])
    if not (emin <= e <= emax):
        return None, None
    if e <= 0.0:
        return None, None
    if float(cat["bgo_total_keV"][idx]) >= old_step05.BGO_THR_KEV:
        return "raw", "bgo_veto"
    keep, cls = old_step05.classify_final(old_step05.event_hits(cat, idx), reject_policy)
    if keep:
        return "final", cls
    return "bgo", cls


def analyze_window(old_step05, cat: dict, reject_policy: str, emin: float, emax: float) -> dict[str, Any]:
    rate = {"raw": 0.0, "bgo": 0.0, "final": 0.0}
    counts = {"raw": 0, "bgo": 0, "final": 0}
    classes: Counter[str] = Counter()
    selected: list[dict[str, Any]] = []
    for idx in range(len(cat["stream"])):
        e = float(cat["tes_total_keV"][idx])
        if not (emin <= e <= emax) or e <= 0.0:
            continue
        r = float(cat["rate_hz"][idx])
        rate["raw"] += r
        counts["raw"] += 1
        bgo = float(cat["bgo_total_keV"][idx])
        if bgo >= old_step05.BGO_THR_KEV:
            classes["bgo_veto"] += 1
            continue
        rate["bgo"] += r
        counts["bgo"] += 1
        keep, cls = old_step05.classify_final(old_step05.event_hits(cat, idx), reject_policy)
        classes[str(cls)] += 1
        if keep:
            rate["final"] += r
            counts["final"] += 1
            selected.append(
                {
                    "local_id": int(cat["local_id"][idx]),
                    "tes_total_keV": e,
                    "bgo_total_keV": bgo,
                    "pix_count": int(cat["pix_count"][idx]),
                    "class": str(cls),
                    "rate_hz": r,
                }
            )
    return {
        "energy_window_keV": [float(emin), float(emax)],
        "counts": counts,
        "rates_cps": rate,
        "compton_class_counts_after_bgo": dict(classes),
        "selected_events": selected,
    }


def top_energy_rows(cat: dict, rate_hz: float, n: int = 20) -> list[dict[str, Any]]:
    rows = []
    for idx in range(len(cat["stream"])):
        e = float(cat["tes_total_keV"][idx])
        if e <= 0.0:
            continue
        rows.append(
            {
                "local_id": int(cat["local_id"][idx]),
                "tes_total_keV": e,
                "bgo_total_keV": float(cat["bgo_total_keV"][idx]),
                "pix_count": int(cat["pix_count"][idx]),
                "rate_hz": rate_hz,
            }
        )
    rows.sort(key=lambda row: abs(row["tes_total_keV"] - 511.0))
    return rows[:n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=DEFAULT_LABEL)
    ap.add_argument("--sim", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--te-s", type=float, default=0.0)
    ap.add_argument("--reject-policy", choices=["keep", "drop"], default="keep")
    args = ap.parse_args()

    out = paths_for(args.label)
    sim = Path(args.sim) if args.sim else out["sim"]
    source = Path(args.source) if args.source else out["source"]
    if not sim.exists():
        raise SystemExit(f"missing SIM: {sim}")
    if not source.exists():
        raise SystemExit(f"missing source: {source}")

    te_s = float(args.te_s) if args.te_s > 0.0 else parse_te(sim)
    activity, triggers = parse_source_activity_and_triggers(source)
    if te_s is None:
        if triggers and activity > 0.0:
            te_s = float(triggers) / activity
        else:
            raise SystemExit("cannot determine delayed live time from SIM TE or source triggers/activity")
    rate_hz = 1.0 / float(te_s)

    old_step05 = load_old_step05_module()
    old_step05.delayed_time_s = lambda: float(te_s)
    cat_raw = old_step05.parse_sim_catalog((str(sim), "delayed", 1.0e-4))
    cat = old_step05.catalog_to_arrays(cat_raw)

    w2 = analyze_window(old_step05, cat, args.reject_policy, W2_MIN_KEV, W2_MAX_KEV)
    wide = analyze_window(old_step05, cat, args.reject_policy, WIDE_MIN_KEV, WIDE_MAX_KEV)
    by_energy_near_511 = top_energy_rows(cat, rate_hz)
    generated = int(cat.get("n_generated_events_seen", 0))
    kept = int(cat.get("n_kept_events", len(cat["stream"])))

    summary = {
        "status": "PASS_OLD_NEW_GEO_RE_DIV8_EXACTPOS_DELAYED_W2_ANALYSIS",
        "label": args.label,
        "sim": rel(sim),
        "source": rel(source),
        "method": "old_new_geo_re_Step05_parser_delayed_only_direct_expectation",
        "normalization": {
            "TE_s": float(te_s),
            "per_generated_event_rate_hz": rate_hz,
            "source_activity_Bq": activity,
            "source_triggers": triggers,
            "primary_activity_time_s_if_no_daughters": (float(triggers) / activity) if triggers and activity > 0.0 else None,
            "bgo_threshold_keV": float(old_step05.BGO_THR_KEV),
            "reject_policy": args.reject_policy,
        },
        "catalog": {
            "generated_events_seen": generated,
            "events_kept_with_tes_or_bgo": kept,
            "events_with_tes": int(sum(1 for x in cat["tes_total_keV"] if float(x) > 0.0)),
            "events_with_bgo": int(sum(1 for x in cat["bgo_total_keV"] if float(x) > 0.0)),
        },
        "w2": w2,
        "wide_480_550": wide,
        "nearest_tes_events_to_511keV": by_energy_near_511,
    }
    write_json(out["summary"], summary)

    with out["events_csv"].open("w", encoding="utf-8", newline="") as handle:
        fields = ["local_id", "tes_total_keV", "bgo_total_keV", "pix_count", "class", "rate_hz"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in w2["selected_events"]:
            writer.writerow({k: row.get(k, "") for k in fields})

    print(json.dumps({"status": summary["status"], "summary": rel(out["summary"]), "w2": w2["rates_cps"], "w2_counts": w2["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
