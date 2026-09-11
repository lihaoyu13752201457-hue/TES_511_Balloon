#!/usr/bin/env python3
"""Build true source-block lineage tables for the delayed 511 keV audit.

This is metadata instrumentation at the analysis layer.  It does not modify
transport physics.  Source-block lineage is recovered by matching each SIM
event's ``IA INIT`` isotope ZA and source z coordinate to the delayed source
file's ``RadialProfileBeam`` source blocks.  For O-15 this match is exact in
the existing 1M delayed baseline SIM and is therefore usable for BGO-origin
class A-G accounting.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import json
import math
import os
import platform
import re
import socket
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
OUT_DEFAULT = ROOT / "reports2.0" / "99_O15_BGO_ROOT_CAUSE_AUDIT_LINEAGE_RERUN"
SOURCE_DEFAULT = ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "activation_decay_day15_groundstate_fixed.source"
BASELINE_SIM_CANDIDATES = [
    ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz",
    WORKSPACE / "cosmosray_bg_260516" / "production_runs" / "delay_fix_from_buildup_equiv2602" / "DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz",
]
BASELINE_LOG_CANDIDATES = [
    ROOT / "production_runs" / "delay_fix_from_buildup_equiv2602" / "cosima_full1m.log",
    WORKSPACE / "cosmosray_bg_260516" / "production_runs" / "delay_fix_from_buildup_equiv2602" / "cosima_full1m.log",
]
PREVIOUS_SUMMARY = ROOT / "reports2.0" / "03_NEXT_PHASE_SUPPORT" / "activation_511_diagnostics" / "activation_511_diagnostic_summary.json"
PREVIOUS_ABLATION = ROOT / "reports2.0" / "99_O15_BGO_ROOT_CAUSE_AUDIT" / "sensitivity_ablation_table.csv"

LINE_WINDOW = (510.3, 511.8)
BROAD_WINDOW = (480.0, 550.0)
THRESHOLDS = [30.0, 50.0, 70.0, 100.0, 150.0]
DEFAULT_THRESHOLD = 50.0
MATCH_TOL_MM = 1.0e-3

SOURCE_RE = re.compile(
    r"^(?P<block>S_(?P<volume>.+)_(?P<za>\d+)_z(?P<zbin>\d+))\."
    r"(?P<field>ParticleType|Flux|Beam)\s*(?P<value>.*)$"
)
ID_RE = re.compile(r"^ID\s+(\d+)")
IA_INIT_RE = re.compile(r"^IA INIT\s+(?P<body>.*)$")
IA_DECA_RE = re.compile(r"^IA DECA\s+(?P<body>.*)$")
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(?P<vol>\S+)\s+(?P<body>.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pix>\d+)$", re.IGNORECASE)

ELEMENTS = [
    "",
    "H",
    "He",
    "Li",
    "Be",
    "B",
    "C",
    "N",
    "O",
    "F",
    "Ne",
    "Na",
    "Mg",
    "Al",
    "Si",
    "P",
    "S",
    "Cl",
    "Ar",
    "K",
    "Ca",
    "Sc",
    "Ti",
    "V",
    "Cr",
    "Mn",
    "Fe",
    "Co",
    "Ni",
    "Cu",
    "Zn",
    "Ga",
    "Ge",
    "As",
    "Se",
    "Br",
    "Kr",
    "Rb",
    "Sr",
    "Y",
    "Zr",
    "Nb",
    "Mo",
    "Tc",
    "Ru",
    "Rh",
    "Pd",
    "Ag",
    "Cd",
    "In",
    "Sn",
    "Sb",
    "Te",
    "I",
    "Xe",
    "Cs",
    "Ba",
    "La",
    "Ce",
    "Pr",
    "Nd",
    "Pm",
    "Sm",
    "Eu",
    "Gd",
    "Tb",
    "Dy",
    "Ho",
    "Er",
    "Tm",
    "Yb",
    "Lu",
    "Hf",
    "Ta",
    "W",
    "Re",
    "Os",
    "Ir",
    "Pt",
    "Au",
    "Hg",
    "Tl",
    "Pb",
    "Bi",
    "Po",
]


@dataclass
class SourceBlock:
    name: str
    production_volume: str
    za: int
    z_bin: int
    z_mm: float
    activity_bq: float
    profile_file: str


@dataclass
class Hit:
    volume: str
    edep_kev: float
    x_mm: float
    y_mm: float
    z_mm: float
    tid: int
    pid: int
    sec: str
    prim: str
    cproc: str


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        try:
            return str(path.relative_to(WORKSPACE))
        except ValueError:
            return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def fval(value: Any, default: float = 0.0) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def za_to_nuclide(za: int) -> str:
    z = za // 1000
    a = za % 1000
    if 0 < z < len(ELEMENTS):
        return f"{ELEMENTS[z]}-{a}"
    return f"ZA-{za}"


def select_existing(paths: list[Path], label: str) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError(f"No {label} candidate exists: {[str(p) for p in paths]}")


def parse_source_blocks(path: Path) -> tuple[dict[str, SourceBlock], dict[int, list[SourceBlock]]]:
    scratch: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = SOURCE_RE.match(line.strip())
        if not match:
            continue
        block = match.group("block")
        rec = scratch.setdefault(
            block,
            {
                "name": block,
                "production_volume": match.group("volume"),
                "za": int(match.group("za")),
                "z_bin": int(match.group("zbin")),
                "activity_bq": 0.0,
                "z_mm": math.nan,
                "profile_file": "",
            },
        )
        field = match.group("field")
        value = match.group("value").strip()
        if field == "Flux":
            rec["activity_bq"] = float(value)
        elif field == "Beam":
            toks = value.split()
            if len(toks) >= 8:
                rec["z_mm"] = float(toks[3])
                rec["profile_file"] = toks[-1]
    blocks: dict[str, SourceBlock] = {}
    by_za: dict[int, list[SourceBlock]] = defaultdict(list)
    for rec in scratch.values():
        if math.isnan(float(rec["z_mm"])):
            continue
        block = SourceBlock(**rec)
        blocks[block.name] = block
        by_za[block.za].append(block)
    for rows in by_za.values():
        rows.sort(key=lambda r: (r.z_mm, r.name))
    return blocks, dict(by_za)


def match_source_block(by_za: dict[int, list[SourceBlock]], za: int | None, z_mm: float | None) -> tuple[SourceBlock | None, float | None, str]:
    if za is None or z_mm is None:
        return None, None, "missing_za_or_z"
    candidates = by_za.get(int(za), [])
    if not candidates:
        return None, None, "missing_za_in_source_file"
    ranked = sorted(((abs(block.z_mm - z_mm), block.name, block) for block in candidates), key=lambda item: (item[0], item[1]))
    best = ranked[0]
    if len(ranked) > 1 and abs(best[0] - ranked[1][0]) < 1.0e-9:
        return best[2], best[0], "ambiguous_equal_z_nearest"
    if best[0] <= MATCH_TOL_MM:
        return best[2], best[0], "exact_za_z_match"
    return best[2], best[0], "nearest_za_z_inferred"


def parse_ia_line(line: str, pattern: re.Pattern[str]) -> dict[str, Any] | None:
    match = pattern.match(line)
    if not match:
        return None
    parts = [part.strip() for part in match.group("body").split(";")]
    if len(parts) < 16:
        return None
    try:
        return {
            "x_mm": float(parts[4]),
            "y_mm": float(parts[5]),
            "z_mm": float(parts[6]),
            "za": int(float(parts[15])),
        }
    except ValueError:
        return None


def parse_cc_hit(line: str) -> Hit | None:
    match = CC_HIT_RE.match(line.strip())
    if not match:
        return None
    kv = dict(KV_RE.findall(match.group("body")))
    try:
        return Hit(
            volume=match.group("vol"),
            edep_kev=float(kv["edep_keV"]),
            x_mm=float(kv["x"]),
            y_mm=float(kv["y"]),
            z_mm=float(kv["z"]),
            tid=int(kv.get("tid", "-1")),
            pid=int(kv.get("pid", "-1")),
            sec=kv.get("sec", ""),
            prim=kv.get("prim", ""),
            cproc=kv.get("cproc", ""),
        )
    except (KeyError, ValueError):
        return None


def detector_kind(volume: str) -> str:
    if TP_RE.match(volume) or volume.upper().startswith("TES_"):
        return "TES"
    if "BGO" in volume.upper():
        return "BGO"
    if volume:
        return "passive_or_other"
    return ""


def open_text(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("r", encoding="utf-8", errors="ignore")


def empty_event() -> dict[str, Any]:
    return {
        "event_id": None,
        "za": None,
        "init_x_mm": None,
        "init_y_mm": None,
        "init_z_mm": None,
        "decay_x_mm": None,
        "decay_y_mm": None,
        "decay_z_mm": None,
        "first_hit_volume": "",
        "first_hit_detector_kind": "",
        "first_primary_hit_volume": "",
        "tes_total_edep_keV": 0.0,
        "bgo_total_edep_keV": 0.0,
        "pixels": {},
        "n_hits": 0,
        "n_tes_hits": 0,
        "n_bgo_hits": 0,
    }


def add_pixel(pixels: dict[str, dict[str, float]], hit: Hit) -> None:
    match = TP_RE.match(hit.volume)
    if not match:
        return
    rec = pixels.setdefault(hit.volume, {"e": 0.0, "wx": 0.0, "wy": 0.0, "wz": 0.0, "layer": float(match.group("layer"))})
    rec["e"] += hit.edep_kev
    rec["wx"] += hit.edep_kev * hit.x_mm
    rec["wy"] += hit.edep_kev * hit.y_mm
    rec["wz"] += hit.edep_kev * hit.z_mm


def event_hits_for_selection(ev: dict[str, Any]) -> list[Any]:
    # Import lazily so --help does not require the full analysis module.
    import make_complete_day15_report as complete

    hits = []
    for uid, rec in sorted(ev["pixels"].items()):
        e = float(rec["e"])
        if e <= 0.0:
            continue
        hits.append(
            complete.EventHit(
                x=float(rec["wx"] / e),
                y=float(rec["wy"] / e),
                z=float(rec["wz"] / e),
                e=e,
                pixel_uid=uid,
                layer=int(rec["layer"]),
            )
        )
    return hits


def final_selection_pass(ev: dict[str, Any], threshold_kev: float, lo: float, hi: float) -> bool:
    if not (lo <= float(ev["tes_total_edep_keV"]) < hi):
        return False
    if float(ev["bgo_total_edep_keV"]) >= threshold_kev:
        return False
    import make_complete_day15_report as complete

    keep, _cls = complete.classify_final(event_hits_for_selection(ev), "keep")
    return bool(keep)


def classify_o15(ev: dict[str, Any], block: SourceBlock | None, threshold_kev: float, use_final_selection: bool = True) -> str | None:
    if ev["za"] != 8015 or block is None:
        return None
    origin_is_bgo = block.production_volume == "BGO_Shield"
    tes = float(ev["tes_total_edep_keV"])
    bgo = float(ev["bgo_total_edep_keV"])
    line_hit = LINE_WINDOW[0] <= tes < LINE_WINDOW[1]
    broad_hit = BROAD_WINDOW[0] <= tes < BROAD_WINDOW[1]
    veto_pass = bgo < threshold_kev
    selected_line = final_selection_pass(ev, threshold_kev, *LINE_WINDOW) if use_final_selection and line_hit else line_hit
    selected_broad = final_selection_pass(ev, threshold_kev, *BROAD_WINDOW) if use_final_selection and broad_hit else broad_hit
    if origin_is_bgo:
        if selected_line and veto_pass:
            return "A"
        if line_hit and not veto_pass:
            return "B"
        if selected_broad and not line_hit and veto_pass:
            return "C"
        if bgo > 0.0 and not broad_hit:
            return "D"
        if bgo <= 0.0 and not broad_hit:
            return "E"
        return None
    if selected_line and veto_pass:
        return "F"
    if line_hit and not veto_pass:
        return "G"
    return None


def source_activity_summary(blocks: dict[str, SourceBlock]) -> dict[str, Any]:
    total = sum(block.activity_bq for block in blocks.values())
    by_volume: dict[str, float] = defaultdict(float)
    by_o15_volume: dict[str, float] = defaultdict(float)
    for block in blocks.values():
        by_volume[block.production_volume] += block.activity_bq
        if block.za == 8015:
            by_o15_volume[block.production_volume] += block.activity_bq
    return {
        "total_source_activity_Bq": total,
        "BGO_Shield_activity_Bq": by_volume.get("BGO_Shield", 0.0),
        "O15_total_source_activity_Bq": sum(by_o15_volume.values()),
        "O15_BGO_Shield_activity_Bq": by_o15_volume.get("BGO_Shield", 0.0),
        "O15_BGO_Shield_activity_fraction": by_o15_volume.get("BGO_Shield", 0.0) / sum(by_o15_volume.values()) if sum(by_o15_volume.values()) else None,
    }


def load_previous_baseline() -> dict[str, Any]:
    summary = read_json(PREVIOUS_SUMMARY, {})
    ablation = read_csv(PREVIOUS_ABLATION)
    selected: dict[str, Any] = {"summary": summary, "ablation_rows": ablation}
    for row in ablation:
        if row.get("scenario") == "baseline" and row.get("window_keV") == "510.3-511.8" and row.get("model") == "window_counting_same_events":
            selected["line_baseline"] = row
        if row.get("scenario") == "baseline" and row.get("window_keV") == "480-550" and row.get("model") == "window_counting_same_events":
            selected["broad_baseline"] = row
        if row.get("scenario") == "no_BGO_activation_keep_prompt_veto" and row.get("window_keV") == "510.3-511.8" and row.get("model") == "window_counting_same_events":
            selected["line_posthoc_no_bgo"] = row
        if row.get("scenario") == "no_BGO_activation_keep_prompt_veto" and row.get("window_keV") == "480-550" and row.get("model") == "window_counting_same_events":
            selected["broad_posthoc_no_bgo"] = row
    return selected


def parse_observation_time(log_path: Path | None, fallback_rate: float | None = None, n_events: int = 1_000_000) -> tuple[float | None, float | None]:
    if log_path and log_path.exists():
        for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if "Observation time:" in line:
                vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
                if vals:
                    obs = float(vals[0])
                    return obs, 1.0 / obs
    if fallback_rate:
        return n_events / (fallback_rate * n_events), fallback_rate
    return None, None


def run_capture(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(args, cwd=str(ROOT), text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return None


def build_manifest(outdir: Path, sim: Path, source: Path, log: Path | None, rate_per_event: float, observation_time_s: float | None, blocks: dict[str, SourceBlock]) -> dict[str, Any]:
    return {
        "audit_time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "metadata_lineage_parse_existing_transport",
        "git": {
            "commit": run_capture(["git", "rev-parse", "HEAD"]),
            "branch": run_capture(["git", "branch", "--show-current"]),
            "dirty": bool(run_capture(["git", "status", "--porcelain"])),
        },
        "platform": {
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "working_directory": str(ROOT),
        },
        "inputs": {
            "baseline_delayed_sim": rel(sim),
            "delayed_source_file": rel(source),
            "cosima_log": rel(log) if log else None,
            "previous_diagnostic_summary": rel(PREVIOUS_SUMMARY),
            "previous_ablation_table": rel(PREVIOUS_ABLATION),
        },
        "normalization": {
            "observation_time_s": observation_time_s,
            "rate_per_event_cps": rate_per_event,
            **source_activity_summary(blocks),
        },
        "lineage_method": {
            "source_block_match": "IA INIT isotope ZA plus IA INIT z_mm matched to delayed source RadialProfileBeam z_mm",
            "match_tolerance_mm": MATCH_TOL_MM,
            "class_A_basis": "true source_block_name/production_volume recovered from source file match; not source_volume_proxy",
            "transport_physics_changed": False,
            "new_geant4_transport_rerun": False,
        },
        "selection": {
            "line_window_keV": list(LINE_WINDOW),
            "broad_window_keV": list(BROAD_WINDOW),
            "default_bgo_threshold_keV": DEFAULT_THRESHOLD,
            "threshold_scan_keV": THRESHOLDS,
            "tes_measured_energy_policy": "same as true TES deposited energy; no detector smearing added in this metadata audit",
        },
        "outputs": {
            "lineage": rel(outdir / "delayed_final_event_lineage.csv"),
            "classes": rel(outdir / "o15_bgo_decay_veto_escape_classes_TRUE.csv"),
            "threshold_scan": rel(outdir / "bgo_origin_o15_threshold_scan_TRUE.csv"),
            "no_bgo_sensitivity": rel(outdir / "no_BGO_activation_keep_prompt_veto_TRUE_sensitivity.csv"),
            "checks": rel(outdir / "lineage_rate_closure_checks.json"),
            "summary": rel(outdir / "ROOT_CAUSE_LINEAGE_RERUN_SUMMARY.md"),
        },
    }


def event_to_row(
    ev: dict[str, Any],
    block: SourceBlock | None,
    match_dz: float | None,
    match_status: str,
    rate_per_event: float,
    input_file: Path,
    threshold_kev: float,
    line_final: bool,
    broad_final: bool,
) -> dict[str, Any]:
    nuclide = za_to_nuclide(int(ev["za"])) if ev["za"] else ""
    line_pass = LINE_WINDOW[0] <= float(ev["tes_total_edep_keV"]) < LINE_WINDOW[1]
    broad_pass = BROAD_WINDOW[0] <= float(ev["tes_total_edep_keV"]) < BROAD_WINDOW[1]
    return {
        "event_id": ev["event_id"],
        "source_event_id": ev["event_id"],
        "candidate_event_id": ev["event_id"],
        "stream_type": "delayed_activation",
        "nuclide": nuclide,
        "ZA_or_isotope_id": ev["za"] or "",
        "source_block_name": block.name if block else "",
        "production_volume": block.production_volume if block else "",
        "decay_volume": block.production_volume if block else "",
        "source_z_bin": block.z_bin if block else "",
        "source_z_mm": block.z_mm if block else "",
        "source_match_dz_mm": match_dz if match_dz is not None else "",
        "source_match_status": match_status,
        "decay_x_mm": ev["decay_x_mm"] if ev["decay_x_mm"] is not None else ev["init_x_mm"],
        "decay_y_mm": ev["decay_y_mm"] if ev["decay_y_mm"] is not None else ev["init_y_mm"],
        "decay_z_mm": ev["decay_z_mm"] if ev["decay_z_mm"] is not None else ev["init_z_mm"],
        "first_hit_volume": ev["first_hit_volume"],
        "first_hit_detector_kind": ev["first_hit_detector_kind"],
        "first_primary_hit_volume": ev["first_primary_hit_volume"],
        "tes_total_edep_keV": ev["tes_total_edep_keV"],
        "tes_measured_energy_keV": ev["tes_total_edep_keV"],
        "bgo_total_edep_keV": ev["bgo_total_edep_keV"],
        "bgo_veto_threshold_keV": threshold_kev,
        "bgo_veto_pass": float(ev["bgo_total_edep_keV"]) < threshold_kev,
        "line_window_pass": line_pass,
        "broad_window_pass": broad_pass,
        "line_final_selection_pass": line_final,
        "broad_final_selection_pass": broad_final,
        "event_weight": 1.0,
        "weighted_cps": rate_per_event,
        "input_file": rel(input_file),
    }


def update_class_accumulators(
    ev: dict[str, Any],
    block: SourceBlock | None,
    rate_per_event: float,
    class_acc: dict[float, dict[str, dict[str, Any]]],
    threshold_acc: dict[float, dict[str, Any]],
) -> None:
    if ev["za"] != 8015:
        return
    origin = block.production_volume if block else "unmatched"
    bgo_origin = origin == "BGO_Shield"
    tes = float(ev["tes_total_edep_keV"])
    bgo = float(ev["bgo_total_edep_keV"])
    line_hit = LINE_WINDOW[0] <= tes < LINE_WINDOW[1]
    broad_hit = BROAD_WINDOW[0] <= tes < BROAD_WINDOW[1]
    for thr in THRESHOLDS:
        line_final = final_selection_pass(ev, thr, *LINE_WINDOW) if line_hit else False
        broad_final = final_selection_pass(ev, thr, *BROAD_WINDOW) if broad_hit else False
        class_id = classify_o15(ev, block, thr, use_final_selection=True)
        tacc = threshold_acc[thr]
        tacc["all_o15_cps_total"] += rate_per_event
        if line_final:
            tacc["all_o15_final_line_cps"] += rate_per_event
        if broad_final:
            tacc["all_o15_final_broad_cps"] += rate_per_event
        if bgo_origin:
            tacc["bgo_origin_o15_cps_total"] += rate_per_event
            if line_final:
                tacc["bgo_origin_o15_final_line_cps"] += rate_per_event
            if broad_final:
                tacc["bgo_origin_o15_final_broad_cps"] += rate_per_event
        if class_id is None:
            tacc["unclassified_o15_cps"] += rate_per_event
            return
        rec = class_acc[thr].setdefault(
            class_id,
            {
                "class_id": class_id,
                "n_events": 0,
                "origin_volume_counts": Counter(),
                "weighted_cps_total": 0.0,
                "raw_line_cps": 0.0,
                "raw_broad_cps": 0.0,
                "final_line_cps": 0.0,
                "final_broad_cps": 0.0,
                "bgo_values": [],
                "tes_values": [],
                "decay_r_values": [],
                "decay_z_values": [],
            },
        )
        rec["n_events"] += 1
        rec["origin_volume_counts"][origin] += 1
        rec["weighted_cps_total"] += rate_per_event
        if line_hit:
            rec["raw_line_cps"] += rate_per_event
        if broad_hit:
            rec["raw_broad_cps"] += rate_per_event
        if line_final:
            rec["final_line_cps"] += rate_per_event
        if broad_final:
            rec["final_broad_cps"] += rate_per_event
        rec["bgo_values"].append(bgo)
        rec["tes_values"].append(tes)
        dx = fval(ev["decay_x_mm"], fval(ev["init_x_mm"]))
        dy = fval(ev["decay_y_mm"], fval(ev["init_y_mm"]))
        dz = fval(ev["decay_z_mm"], fval(ev["init_z_mm"]))
        rec["decay_r_values"].append(math.hypot(dx, dy))
        rec["decay_z_values"].append(dz)


def median(vals: list[float]) -> float | str:
    if not vals:
        return ""
    vals = sorted(vals)
    mid = len(vals) // 2
    if len(vals) % 2:
        return vals[mid]
    return 0.5 * (vals[mid - 1] + vals[mid])


CLASS_DESCRIPTION = {
    "A": "BGO-origin O-15, TES line hit, BGO veto pass, final selection pass",
    "B": "BGO-origin O-15, TES line hit, BGO veto fail",
    "C": "BGO-origin O-15, TES broad-only hit, BGO veto pass, final selection pass",
    "D": "BGO-origin O-15, BGO-only or BGO+out-of-window TES hit, no TES line/broad hit",
    "E": "BGO-origin O-15, escape/no relevant TES or BGO hit",
    "F": "non-BGO-origin O-15, TES line hit, BGO veto pass, final selection pass",
    "G": "non-BGO-origin O-15, TES line hit, BGO veto fail",
}


def build_class_rows(class_acc: dict[str, dict[str, Any]], threshold: float, totals: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for class_id in ["A", "B", "C", "D", "E", "F", "G"]:
        rec = class_acc.get(class_id)
        if rec is None:
            row = {
                "threshold_keV": threshold,
                "class_id": class_id,
                "class_description": CLASS_DESCRIPTION[class_id],
                "nuclide": "O-15",
                "origin_volume": "BGO_Shield" if class_id in "ABCDE" else "non-BGO",
                "n_events": 0,
                "weighted_cps_total": 0.0,
                "raw_line_cps": 0.0,
                "raw_broad_cps": 0.0,
                "final_line_cps": 0.0,
                "final_broad_cps": 0.0,
                "fraction_of_total_final_line": 0.0,
                "fraction_of_o15_final_line": 0.0,
                "fraction_of_bgo_origin_o15_final_line": 0.0,
                "median_decay_r_mm": "",
                "median_decay_z_mm": "",
                "median_bgo_edep_keV": "",
                "median_tes_edep_keV": "",
                "notes": "zero events",
            }
        else:
            final_line = float(rec["final_line_cps"])
            row = {
                "threshold_keV": threshold,
                "class_id": class_id,
                "class_description": CLASS_DESCRIPTION[class_id],
                "nuclide": "O-15",
                "origin_volume": ";".join(sorted(rec["origin_volume_counts"].keys())),
                "n_events": rec["n_events"],
                "weighted_cps_total": rec["weighted_cps_total"],
                "raw_line_cps": rec["raw_line_cps"],
                "raw_broad_cps": rec["raw_broad_cps"],
                "final_line_cps": final_line,
                "final_broad_cps": rec["final_broad_cps"],
                "fraction_of_total_final_line": final_line / totals["total_line_background_cps"] if totals["total_line_background_cps"] else "",
                "fraction_of_o15_final_line": final_line / totals["o15_final_line_cps"] if totals["o15_final_line_cps"] else "",
                "fraction_of_bgo_origin_o15_final_line": final_line / totals["bgo_origin_o15_final_line_cps"] if totals["bgo_origin_o15_final_line_cps"] else "",
                "median_decay_r_mm": median(rec["decay_r_values"]),
                "median_decay_z_mm": median(rec["decay_z_values"]),
                "median_bgo_edep_keV": median(rec["bgo_values"]),
                "median_tes_edep_keV": median(rec["tes_values"]),
                "notes": "class uses true source_block_name/production_volume recovered from IA INIT ZA+z",
            }
        rows.append(row)
    return rows


def scaled_f3_from_baseline(baseline_f3: float, baseline_total_cps: float, new_total_cps: float) -> float:
    if baseline_f3 <= 0.0 or baseline_total_cps <= 0.0:
        return 0.0
    return baseline_f3 * math.sqrt(new_total_cps / baseline_total_cps)


def parse_and_write(args: argparse.Namespace) -> dict[str, Any]:
    outdir: Path = args.outdir
    outdir.mkdir(parents=True, exist_ok=True)
    source = args.source_file
    sim = args.sim
    log = args.log if args.log and args.log.exists() else None
    blocks, by_za = parse_source_blocks(source)
    previous = load_previous_baseline()
    prev_summary = previous["summary"]
    fallback_rate = fval(prev_summary.get("audit", {}).get("rate_per_event_hz"))
    obs, rate_per_event = parse_observation_time(log, fallback_rate=fallback_rate)
    if not rate_per_event:
        raise RuntimeError("Could not determine delayed event rate")

    sys.path.insert(0, str(ROOT / "tools"))

    lineage_fields = [
        "event_id",
        "source_event_id",
        "candidate_event_id",
        "stream_type",
        "nuclide",
        "ZA_or_isotope_id",
        "source_block_name",
        "production_volume",
        "decay_volume",
        "source_z_bin",
        "source_z_mm",
        "source_match_dz_mm",
        "source_match_status",
        "decay_x_mm",
        "decay_y_mm",
        "decay_z_mm",
        "first_hit_volume",
        "first_hit_detector_kind",
        "first_primary_hit_volume",
        "tes_total_edep_keV",
        "tes_measured_energy_keV",
        "bgo_total_edep_keV",
        "bgo_veto_threshold_keV",
        "bgo_veto_pass",
        "line_window_pass",
        "broad_window_pass",
        "line_final_selection_pass",
        "broad_final_selection_pass",
        "event_weight",
        "weighted_cps",
        "input_file",
    ]

    counters = Counter()
    match_counters = Counter()
    event_rate_by_source_block: dict[str, float] = defaultdict(float)
    activity_by_seen_source_block: dict[str, float] = {}
    rates = {
        "line_raw_cps": 0.0,
        "line_bgo_cps": 0.0,
        "line_final_cps": 0.0,
        "broad_raw_cps": 0.0,
        "broad_bgo_cps": 0.0,
        "broad_final_cps": 0.0,
        "line_final_non_bgo_cps": 0.0,
        "broad_final_non_bgo_cps": 0.0,
        "line_final_bgo_origin_cps": 0.0,
        "broad_final_bgo_origin_cps": 0.0,
        "o15_final_line_cps": 0.0,
        "o15_final_broad_cps": 0.0,
        "bgo_origin_o15_final_line_cps": 0.0,
        "bgo_origin_o15_final_broad_cps": 0.0,
    }
    class_acc: dict[float, dict[str, dict[str, Any]]] = {thr: {} for thr in THRESHOLDS}
    threshold_acc: dict[float, dict[str, Any]] = {
        thr: defaultdict(float)
        for thr in THRESHOLDS
    }
    o15_exact_match_bad_examples: list[dict[str, Any]] = []
    sample_limit = int(args.max_lineage_rows) if args.max_lineage_rows else None
    rows_written = 0

    def flush(ev: dict[str, Any], writer: csv.DictWriter) -> None:
        nonlocal rows_written
        if ev["event_id"] is None:
            return
        counters["events_seen"] += 1
        block, dz, match_status = match_source_block(by_za, ev["za"], ev["init_z_mm"])
        match_counters[match_status] += 1
        if ev["za"] == 8015 and match_status != "exact_za_z_match":
            counters["o15_non_exact_source_match"] += 1
            if len(o15_exact_match_bad_examples) < 10:
                o15_exact_match_bad_examples.append(
                    {
                        "event_id": ev["event_id"],
                        "za": ev["za"],
                        "init_z_mm": ev["init_z_mm"],
                        "nearest_block": block.name if block else "",
                        "match_dz_mm": dz,
                        "match_status": match_status,
                    }
                )
        if block:
            event_rate_by_source_block[block.name] += rate_per_event
            activity_by_seen_source_block[block.name] = block.activity_bq
        line_raw = LINE_WINDOW[0] <= float(ev["tes_total_edep_keV"]) < LINE_WINDOW[1]
        broad_raw = BROAD_WINDOW[0] <= float(ev["tes_total_edep_keV"]) < BROAD_WINDOW[1]
        line_bgo = line_raw and float(ev["bgo_total_edep_keV"]) < DEFAULT_THRESHOLD
        broad_bgo = broad_raw and float(ev["bgo_total_edep_keV"]) < DEFAULT_THRESHOLD
        line_final = final_selection_pass(ev, DEFAULT_THRESHOLD, *LINE_WINDOW) if line_raw else False
        broad_final = final_selection_pass(ev, DEFAULT_THRESHOLD, *BROAD_WINDOW) if broad_raw else False
        if line_raw:
            rates["line_raw_cps"] += rate_per_event
        if broad_raw:
            rates["broad_raw_cps"] += rate_per_event
        if line_bgo:
            rates["line_bgo_cps"] += rate_per_event
        if broad_bgo:
            rates["broad_bgo_cps"] += rate_per_event
        if line_final:
            rates["line_final_cps"] += rate_per_event
        if broad_final:
            rates["broad_final_cps"] += rate_per_event
        if block and block.production_volume == "BGO_Shield":
            if line_final:
                rates["line_final_bgo_origin_cps"] += rate_per_event
            if broad_final:
                rates["broad_final_bgo_origin_cps"] += rate_per_event
        else:
            if line_final:
                rates["line_final_non_bgo_cps"] += rate_per_event
            if broad_final:
                rates["broad_final_non_bgo_cps"] += rate_per_event
        if ev["za"] == 8015:
            if line_final:
                rates["o15_final_line_cps"] += rate_per_event
            if broad_final:
                rates["o15_final_broad_cps"] += rate_per_event
            if block and block.production_volume == "BGO_Shield":
                if line_final:
                    rates["bgo_origin_o15_final_line_cps"] += rate_per_event
                if broad_final:
                    rates["bgo_origin_o15_final_broad_cps"] += rate_per_event
        update_class_accumulators(ev, block, rate_per_event, class_acc, threshold_acc)
        if sample_limit is None or rows_written < sample_limit:
            writer.writerow(event_to_row(ev, block, dz, match_status, rate_per_event, sim, DEFAULT_THRESHOLD, line_final, broad_final))
            rows_written += 1

    ev = empty_event()
    lineage_path = outdir / "delayed_final_event_lineage.csv"
    with lineage_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=lineage_fields)
        writer.writeheader()
        with open_text(sim) as sim_fh:
            for raw in sim_fh:
                line = raw.strip()
                if not line:
                    continue
                if line == "SE":
                    flush(ev, writer)
                    ev = empty_event()
                    continue
                id_match = ID_RE.match(line)
                if id_match:
                    ev["event_id"] = int(id_match.group(1))
                    continue
                if line.startswith("IA INIT"):
                    init = parse_ia_line(line, IA_INIT_RE)
                    if init:
                        ev["init_x_mm"] = init["x_mm"]
                        ev["init_y_mm"] = init["y_mm"]
                        ev["init_z_mm"] = init["z_mm"]
                        ev["za"] = init["za"]
                    continue
                if line.startswith("IA DECA") and ev["decay_z_mm"] is None:
                    deca = parse_ia_line(line, IA_DECA_RE)
                    if deca:
                        ev["decay_x_mm"] = deca["x_mm"]
                        ev["decay_y_mm"] = deca["y_mm"]
                        ev["decay_z_mm"] = deca["z_mm"]
                    continue
                if not line.startswith("CC HIT "):
                    continue
                hit = parse_cc_hit(line)
                if hit is None:
                    continue
                ev["n_hits"] += 1
                if not ev["first_hit_volume"]:
                    ev["first_hit_volume"] = hit.volume
                    ev["first_hit_detector_kind"] = detector_kind(hit.volume)
                if not ev["first_primary_hit_volume"] and hit.tid == 1 and hit.pid == 0:
                    ev["first_primary_hit_volume"] = hit.volume
                if "BGO" in hit.volume.upper():
                    ev["bgo_total_edep_keV"] += hit.edep_kev
                    ev["n_bgo_hits"] += 1
                if TP_RE.match(hit.volume):
                    ev["tes_total_edep_keV"] += hit.edep_kev
                    ev["n_tes_hits"] += 1
                    add_pixel(ev["pixels"], hit)
        flush(ev, writer)

    prev_totals = prev_summary.get("totals", {})
    prev_broad = prev_totals.get("broad_480_550", {})
    prev_line = prev_totals.get("line_510p3_511p8", {})
    line_baseline = previous.get("line_baseline", {})
    broad_baseline = previous.get("broad_baseline", {})
    line_posthoc = previous.get("line_posthoc_no_bgo", {})
    broad_posthoc = previous.get("broad_posthoc_no_bgo", {})
    total_line_background = fval(line_baseline.get("total_background_cps"))
    total_broad_background = fval(broad_baseline.get("total_background_cps"))

    checks = {
        "status": "PASS" if counters["o15_non_exact_source_match"] == 0 else "FAIL_O15_SOURCE_MATCH",
        "events_seen": counters["events_seen"],
        "lineage_rows_written": rows_written,
        "lineage_rows_policy": "all_events" if sample_limit is None else f"first_{sample_limit}_events",
        "source_match_counts": dict(match_counters),
        "o15_non_exact_source_match": counters["o15_non_exact_source_match"],
        "o15_non_exact_source_match_examples": o15_exact_match_bad_examples,
        "rate_per_event_cps": rate_per_event,
        "baseline_rates_from_lineage_parser_cps": rates,
        "previous_delayed_diagnostic_cps": {
            "line_raw_cps": fval(prev_line.get("raw_cps")),
            "line_bgo_cps": fval(prev_line.get("bgo_cps")),
            "line_final_cps": fval(prev_line.get("final_cps")),
            "broad_raw_cps": fval(prev_broad.get("raw_cps")),
            "broad_bgo_cps": fval(prev_broad.get("bgo_cps")),
            "broad_final_cps": fval(prev_broad.get("final_cps")),
        },
        "closure_abs_error_cps": {
            "line_raw": abs(rates["line_raw_cps"] - fval(prev_line.get("raw_cps"))),
            "line_bgo": abs(rates["line_bgo_cps"] - fval(prev_line.get("bgo_cps"))),
            "line_final": abs(rates["line_final_cps"] - fval(prev_line.get("final_cps"))),
            "broad_raw": abs(rates["broad_raw_cps"] - fval(prev_broad.get("raw_cps"))),
            "broad_bgo": abs(rates["broad_bgo_cps"] - fval(prev_broad.get("bgo_cps"))),
            "broad_final": abs(rates["broad_final_cps"] - fval(prev_broad.get("final_cps"))),
        },
        "source_activity_normalization": {
            **source_activity_summary(blocks),
            "sum_weighted_generated_event_cps": rate_per_event * counters["events_seen"],
            "note": "Existing delayed diagnostic normalizes event rates by Cosima observation time; source Flux sum is separately reported for source-block activity closure.",
        },
    }
    write_json(outdir / "lineage_rate_closure_checks.json", checks)

    class_totals = {
        "total_line_background_cps": total_line_background,
        "o15_final_line_cps": rates["o15_final_line_cps"],
        "bgo_origin_o15_final_line_cps": rates["bgo_origin_o15_final_line_cps"],
    }
    class_rows = build_class_rows(class_acc[DEFAULT_THRESHOLD], DEFAULT_THRESHOLD, class_totals)
    class_fields = [
        "threshold_keV",
        "class_id",
        "class_description",
        "nuclide",
        "origin_volume",
        "n_events",
        "weighted_cps_total",
        "raw_line_cps",
        "raw_broad_cps",
        "final_line_cps",
        "final_broad_cps",
        "fraction_of_total_final_line",
        "fraction_of_o15_final_line",
        "fraction_of_bgo_origin_o15_final_line",
        "median_decay_r_mm",
        "median_decay_z_mm",
        "median_bgo_edep_keV",
        "median_tes_edep_keV",
        "notes",
    ]
    write_csv(outdir / "o15_bgo_decay_veto_escape_classes_TRUE.csv", class_rows, class_fields)

    threshold_rows = []
    for thr in THRESHOLDS:
        totals_thr = {
            "total_line_background_cps": total_line_background,
            "o15_final_line_cps": threshold_acc[thr]["all_o15_final_line_cps"],
            "bgo_origin_o15_final_line_cps": threshold_acc[thr]["bgo_origin_o15_final_line_cps"],
        }
        rows_thr = build_class_rows(class_acc[thr], thr, totals_thr)
        row_by_class = {row["class_id"]: row for row in rows_thr}
        threshold_rows.append(
            {
                "threshold_keV": thr,
                "class_A_final_line_cps": row_by_class["A"]["final_line_cps"],
                "class_B_raw_line_cps": row_by_class["B"]["raw_line_cps"],
                "class_C_final_broad_cps": row_by_class["C"]["final_broad_cps"],
                "class_D_total_cps": row_by_class["D"]["weighted_cps_total"],
                "class_E_total_cps": row_by_class["E"]["weighted_cps_total"],
                "class_F_final_line_cps": row_by_class["F"]["final_line_cps"],
                "class_G_raw_line_cps": row_by_class["G"]["raw_line_cps"],
                "class_A_fraction_of_total_line": fval(row_by_class["A"]["final_line_cps"]) / total_line_background if total_line_background else "",
                "class_A_fraction_of_o15_final_line": fval(row_by_class["A"]["final_line_cps"]) / threshold_acc[thr]["all_o15_final_line_cps"] if threshold_acc[thr]["all_o15_final_line_cps"] else "",
                "all_o15_final_line_cps": threshold_acc[thr]["all_o15_final_line_cps"],
                "bgo_origin_o15_final_line_cps": threshold_acc[thr]["bgo_origin_o15_final_line_cps"],
                "unclassified_o15_cps": threshold_acc[thr]["unclassified_o15_cps"],
            }
        )
    threshold_fields = list(threshold_rows[0].keys())
    write_csv(outdir / "bgo_origin_o15_threshold_scan_TRUE.csv", threshold_rows, threshold_fields)

    exposure_line = fval(line_baseline.get("exposure_s"), 1_000_000.0)
    exposure_broad = fval(broad_baseline.get("exposure_s"), 1_000_000.0)
    prompt_line = fval(line_baseline.get("prompt_cps"))
    focused_line = fval(line_baseline.get("focused_cps"))
    response_line = fval(line_baseline.get("source_response_cps_per_flux"))
    prompt_broad = fval(broad_baseline.get("prompt_cps"))
    focused_broad = fval(broad_baseline.get("focused_cps"))
    response_broad = fval(broad_baseline.get("source_response_cps_per_flux"))
    line_baseline_total = prompt_line + rates["line_final_cps"] + focused_line
    broad_baseline_total = prompt_broad + rates["broad_final_cps"] + focused_broad
    line_no_bgo_total = prompt_line + rates["line_final_non_bgo_cps"] + focused_line
    broad_no_bgo_total = prompt_broad + rates["broad_final_non_bgo_cps"] + focused_broad
    f3_line = scaled_f3_from_baseline(fval(line_baseline.get("F3_ph_cm2_s")), line_baseline_total, line_no_bgo_total)
    f3_broad = scaled_f3_from_baseline(fval(broad_baseline.get("F3_ph_cm2_s")), broad_baseline_total, broad_no_bgo_total)
    no_bgo_rows = [
        {
            "scenario": "baseline",
            "run_status": "baseline_existing_transport_lineage_reparse",
            "window_keV": "510.3-511.8",
            "prompt_cps": prompt_line,
            "delayed_cps": rates["line_final_cps"],
            "focused_cps": focused_line,
            "total_background_cps": line_baseline_total,
            "source_response_cps_per_flux": response_line,
            "exposure_s": exposure_line,
            "F3_ph_cm2_s": fval(line_baseline.get("F3_ph_cm2_s")),
            "ratio_vs_baseline": 1.0,
            "previous_posthoc_proxy_ratio": fval(line_posthoc.get("ratio_vs_baseline")),
            "notes": "baseline delayed cps reproduced from metadata lineage parser",
        },
        {
            "scenario": "no_BGO_activation_keep_prompt_veto",
            "run_status": "TRUE_source_block_lineage_filter_existing_transport",
            "window_keV": "510.3-511.8",
            "prompt_cps": prompt_line,
            "delayed_cps": rates["line_final_non_bgo_cps"],
            "focused_cps": focused_line,
            "total_background_cps": line_no_bgo_total,
            "source_response_cps_per_flux": response_line,
            "exposure_s": exposure_line,
            "F3_ph_cm2_s": f3_line,
            "ratio_vs_baseline": f3_line / fval(line_baseline.get("F3_ph_cm2_s")) if fval(line_baseline.get("F3_ph_cm2_s")) else "",
            "previous_posthoc_proxy_ratio": fval(line_posthoc.get("ratio_vs_baseline")),
            "notes": "BGO source blocks removed by true recovered source_block_name; geometry, prompt shield/veto, and non-BGO delayed transport kept unchanged; not an independent Geant4 rerun",
        },
        {
            "scenario": "baseline",
            "run_status": "baseline_existing_transport_lineage_reparse",
            "window_keV": "480-550",
            "prompt_cps": prompt_broad,
            "delayed_cps": rates["broad_final_cps"],
            "focused_cps": focused_broad,
            "total_background_cps": broad_baseline_total,
            "source_response_cps_per_flux": response_broad,
            "exposure_s": exposure_broad,
            "F3_ph_cm2_s": fval(broad_baseline.get("F3_ph_cm2_s")),
            "ratio_vs_baseline": 1.0,
            "previous_posthoc_proxy_ratio": fval(broad_posthoc.get("ratio_vs_baseline")),
            "notes": "baseline delayed cps reproduced from metadata lineage parser",
        },
        {
            "scenario": "no_BGO_activation_keep_prompt_veto",
            "run_status": "TRUE_source_block_lineage_filter_existing_transport",
            "window_keV": "480-550",
            "prompt_cps": prompt_broad,
            "delayed_cps": rates["broad_final_non_bgo_cps"],
            "focused_cps": focused_broad,
            "total_background_cps": broad_no_bgo_total,
            "source_response_cps_per_flux": response_broad,
            "exposure_s": exposure_broad,
            "F3_ph_cm2_s": f3_broad,
            "ratio_vs_baseline": f3_broad / fval(broad_baseline.get("F3_ph_cm2_s")) if fval(broad_baseline.get("F3_ph_cm2_s")) else "",
            "previous_posthoc_proxy_ratio": fval(broad_posthoc.get("ratio_vs_baseline")),
            "notes": "BGO source blocks removed by true recovered source_block_name; geometry, prompt shield/veto, and non-BGO delayed transport kept unchanged; not an independent Geant4 rerun",
        },
    ]
    no_bgo_fields = list(no_bgo_rows[0].keys())
    write_csv(outdir / "no_BGO_activation_keep_prompt_veto_TRUE_sensitivity.csv", no_bgo_rows, no_bgo_fields)

    manifest = build_manifest(outdir, sim, source, log, rate_per_event, obs, blocks)
    manifest["lineage_rows_written"] = rows_written
    manifest["checks_status"] = checks["status"]
    write_json(outdir / "lineage_rerun_manifest.json", manifest)

    summary = build_summary(checks, class_rows, threshold_rows, no_bgo_rows)
    (outdir / "ROOT_CAUSE_LINEAGE_RERUN_SUMMARY.md").write_text(summary, encoding="utf-8")
    return {
        "manifest": manifest,
        "checks": checks,
        "class_rows": class_rows,
        "threshold_rows": threshold_rows,
        "no_bgo_rows": no_bgo_rows,
    }


def build_summary(checks: dict[str, Any], class_rows: list[dict[str, Any]], threshold_rows: list[dict[str, Any]], no_bgo_rows: list[dict[str, Any]]) -> str:
    class_a = next(row for row in class_rows if row["class_id"] == "A")
    class_b = next(row for row in class_rows if row["class_id"] == "B")
    line_no_bgo = next(row for row in no_bgo_rows if row["scenario"] == "no_BGO_activation_keep_prompt_veto" and row["window_keV"] == "510.3-511.8")
    line_base = next(row for row in no_bgo_rows if row["scenario"] == "baseline" and row["window_keV"] == "510.3-511.8")
    return f"""# ROOT CAUSE LINEAGE RERUN SUMMARY

## Scope

This packet recovers true delayed source-block lineage by matching each
baseline delayed SIM event's `IA INIT` isotope ZA and z coordinate to the
delayed source file's `RadialProfileBeam` source blocks.  It does not change
transport physics and does not use `source_volume_proxy` for class A.

## Validation

- Events parsed: `{checks['events_seen']}`
- O-15 non-exact source-block matches: `{checks['o15_non_exact_source_match']}`
- Delayed line final cps from parser: `{checks['baseline_rates_from_lineage_parser_cps']['line_final_cps']}`
- Delayed broad final cps from parser: `{checks['baseline_rates_from_lineage_parser_cps']['broad_final_cps']}`
- Line final closure abs error: `{checks['closure_abs_error_cps']['line_final']}`
- Broad final closure abs error: `{checks['closure_abs_error_cps']['broad_final']}`

## Class A Result At 50 keV

- Class A final line cps: `{class_a['final_line_cps']}`
- Class A raw line cps: `{class_a['raw_line_cps']}`
- Class A / total final line background: `{class_a['fraction_of_total_final_line']}`
- Class A / O-15 final line: `{class_a['fraction_of_o15_final_line']}`
- Class B raw line cps: `{class_b['raw_line_cps']}`

## no_BGO_activation_keep_prompt_veto

- Baseline line F3: `{line_base['F3_ph_cm2_s']}`
- TRUE source-block-filter line F3: `{line_no_bgo['F3_ph_cm2_s']}`
- TRUE source-block-filter ratio vs baseline: `{line_no_bgo['ratio_vs_baseline']}`
- Previous posthoc proxy ratio: `{line_no_bgo['previous_posthoc_proxy_ratio']}`

Important: the no-BGO row uses true recovered source-block lineage to remove
BGO-origin delayed events from the existing high-stat transport sample.  It is
stronger than the previous activity-fraction proxy, but it is still not an
independent Geant4 resampling run.

## Output Files

- `lineage_rerun_manifest.json`
- `delayed_final_event_lineage.csv`
- `o15_bgo_decay_veto_escape_classes_TRUE.csv`
- `bgo_origin_o15_threshold_scan_TRUE.csv`
- `no_BGO_activation_keep_prompt_veto_TRUE_sensitivity.csv`
- `lineage_rate_closure_checks.json`
- `ROOT_CAUSE_LINEAGE_RERUN_SUMMARY.md`
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=OUT_DEFAULT, help="Output directory for lineage audit products")
    parser.add_argument("--source-file", type=Path, default=SOURCE_DEFAULT, help="Delayed activation source file")
    parser.add_argument("--sim", type=Path, default=None, help="Baseline delayed SIM to parse")
    parser.add_argument("--log", type=Path, default=None, help="Cosima log for observation time")
    parser.add_argument("--max-lineage-rows", type=int, default=0, help="Debug option: only write the first N lineage rows, while still aggregating all events if omitted/0")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.sim is None:
        args.sim = select_existing(BASELINE_SIM_CANDIDATES, "baseline delayed SIM")
    if args.log is None:
        try:
            args.log = select_existing(BASELINE_LOG_CANDIDATES, "baseline cosima log")
        except FileNotFoundError:
            args.log = None
    print(f"Input SIM: {args.sim}")
    print(f"Input source: {args.source_file}")
    print(f"Output directory: {args.outdir}")
    result = parse_and_write(args)
    class_a = next(row for row in result["class_rows"] if row["class_id"] == "A")
    print(json.dumps({
        "status": result["checks"]["status"],
        "events_seen": result["checks"]["events_seen"],
        "class_A_final_line_cps": class_a["final_line_cps"],
        "class_A_fraction_total_final_line": class_a["fraction_of_total_final_line"],
    }, indent=2, ensure_ascii=False))
    return 0 if result["checks"]["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
