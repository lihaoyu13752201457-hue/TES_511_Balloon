#!/usr/bin/env python3
"""Run and parse the bounded G7 delayed-source pilot transport matrix.

This is explicitly a pilot diagnostic. It runs only the prepared 1000-trigger
source cards in the WP07 engineering directory and writes selected-rate
evidence for comparing transport/source semantics. It does not promote full
rates and does not touch authority runs.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

import numpy as np


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "07_transport"
PILOT_INPUTS = OUT / "pilot_inputs"
PILOT_RUNS = OUT / "pilot_runs"
MANIFEST_JSON = OUT / "pilot_input_manifest.json"
RUN_SUMMARY_JSON = OUT / "pilot_transport_run_summary.json"
RUN_SUMMARY_MD = OUT / "pilot_transport_run_summary.md"
SELECTION_CSV = OUT / "pilot_selected_rate_diagnostics.csv"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"

WP05_HELPER = PHASE_DIR / "scripts/wp05_native_activation_oracle.py"
STEP05_CODE = ROOT / "old/code/tools/build_v3p5_centerfinger_step05_l1_response.py"
STEP05_LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
FIX5_GEOMETRY = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

PILOTS = {
    "legacy_l0": {
        "label": "legacy L0 delayed source",
        "source_manifest_key": "legacy_l0",
        "source_rel": "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/legacy_l0_pilot1000.source",
        "log_name": "legacy_l0_pilot1000.log",
        "normalization": "source_flux_sum_over_triggers",
    },
    "v2_weighted_eventlist": {
        "label": "source-v2 weighted exact-position EventList",
        "source_manifest_key": "v2_weighted_eventlist",
        "source_rel": "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/v2_eventlist_pilot1000.source",
        "log_name": "v2_eventlist_pilot1000.log",
        "normalization": "pilot_event_weight_sidecar",
    },
    "native_volume_activation": {
        "label": "native volume-level ActivationSources",
        "source_manifest_key": "native_volume_activation",
        "source_rel": "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_inputs/native_activation_sources_pilot1000.source",
        "log_name": "native_activation_pilot1000.log",
        "normalization": "native_isotope_store_activity_over_triggers",
    },
}
PILOT_ORDER = ("v2_weighted_eventlist", "native_volume_activation", "legacy_l0")

WINDOW_ORDER = ("broad_480_550", "w2_510p58_511p42")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except Exception:
        return str(path)


def resolve(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def dec(text: str | Decimal | None) -> Decimal:
    if isinstance(text, Decimal):
        return text
    if text is None or text == "":
        return Decimal(0)
    return Decimal(str(text))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_helper_module() -> Any:
    spec = importlib.util.spec_from_file_location("wp07_wp05_helper", WP05_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {WP05_HELPER}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_step05_module() -> Any:
    spec = importlib.util.spec_from_file_location("wp07_step05_fix5", STEP05_CODE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {STEP05_CODE}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.ROOT = ROOT
    mod.configure_paths(STEP05_LABEL)
    return mod


def source_meta(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, Any] = {
        "source": rel(path),
        "exists": path.exists(),
        "geometry": "",
        "detector_time_constant_s": "",
        "triggers": None,
        "file_base": "",
        "flux_sum_Bq": "",
    }
    flux_sum = Decimal(0)
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] == "Geometry":
            meta["geometry"] = parts[1]
        elif len(parts) >= 2 and parts[0] == "DetectorTimeConstant":
            meta["detector_time_constant_s"] = parts[1]
        elif len(parts) >= 2 and parts[0].endswith(".Triggers"):
            meta["triggers"] = int(float(parts[1]))
        elif len(parts) >= 2 and parts[0].endswith(".FileName"):
            meta["file_base"] = parts[1]
        elif len(parts) >= 2 and parts[0].endswith(".Flux"):
            flux_sum += dec(parts[1])
    meta["flux_sum_Bq"] = fmt_dec(flux_sum)
    return meta


def native_store_total(path: Path) -> Decimal:
    total = Decimal(0)
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            parts = line.split()
            if parts and parts[0] == "RP" and len(parts) >= 4:
                total += dec(parts[3])
    return total


def load_v2_weights(path: Path) -> dict[int, Decimal]:
    weights: dict[int, Decimal] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            weights[int(row["pilot_event_id"])] = dec(row["pilot_event_weight_Bq"])
    return weights


def pilot_normalization(name: str, manifest: dict[str, Any], meta: dict[str, Any]) -> dict[str, Any]:
    triggers = int(meta["triggers"] or 0)
    if triggers <= 0:
        return {"status": "FAIL", "activity_Bq": "0", "event_rate_hz": 0.0, "rule": "missing_triggers"}

    if name == "legacy_l0":
        activity = dec(meta["flux_sum_Bq"])
        rule = "sum(Source.Flux)/Triggers"
    elif name == "v2_weighted_eventlist":
        activity = dec(manifest["v2_weighted_eventlist"]["represented_total_activity_Bq"])
        rule = "pilot_event_weight_Bq from weighted PPS ledger"
    elif name == "native_volume_activation":
        store = resolve(manifest["native_volume_activation"]["activation_store"])
        activity = native_store_total(store)
        rule = "sum(RP activity in native ActivationSources store)/Triggers"
    else:
        raise ValueError(name)

    return {
        "status": "PASS" if activity > 0 else "FAIL",
        "activity_Bq": fmt_dec(activity),
        "triggers": triggers,
        "event_rate_hz": float(activity / Decimal(triggers)),
        "rule": rule,
    }


def validate_inputs(manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    problems: list[str] = []
    for name, spec in PILOTS.items():
        source = resolve(spec["source_rel"])
        if not source.exists():
            problems.append(f"{name}: missing source {rel(source)}")
            rows.append({"name": name, "status": "FAIL", "source": rel(source)})
            continue
        meta = source_meta(source)
        status = "PASS"
        if meta["geometry"] != FIX5_GEOMETRY:
            status = "FAIL"
            problems.append(f"{name}: geometry is {meta['geometry']!r}, expected {FIX5_GEOMETRY!r}")
        if str(meta["detector_time_constant_s"]) != "1e-9":
            status = "FAIL"
            problems.append(f"{name}: DetectorTimeConstant is {meta['detector_time_constant_s']!r}")
        if int(meta["triggers"] or 0) != 1000:
            status = "FAIL"
            problems.append(f"{name}: triggers are {meta['triggers']!r}, expected 1000")
        if "engineering/delayed_source_authority_v2_20260624/07_transport/pilot_runs/" not in str(meta["file_base"]):
            status = "FAIL"
            problems.append(f"{name}: FileName is outside the WP07 pilot_runs directory")
        norm = pilot_normalization(name, manifest, meta)
        if norm["status"] != "PASS":
            status = "FAIL"
            problems.append(f"{name}: invalid normalization")
        rows.append({"name": name, "status": status, "meta": meta, "normalization": norm})
    return rows, problems


def output_base_for(meta: dict[str, Any]) -> Path:
    return resolve(str(meta["file_base"]))


def clean_expected_outputs(base: Path) -> list[str]:
    removed: list[str] = []
    base.parent.mkdir(parents=True, exist_ok=True)
    for path in sorted(base.parent.glob(base.name + "*")):
        if path.is_file():
            path.unlink()
            removed.append(rel(path))
    return removed


def run_cosima(source: Path, log: Path, timeout_s: int) -> dict[str, Any]:
    helper = load_helper_module()
    cosima = helper.COSIMA
    if not cosima.exists():
        log.write_text(f"ERROR: missing cosima executable: {cosima}\n", encoding="utf-8")
        return {"status": "MISSING_COSIMA", "returncode": None, "log": rel(log)}
    with log.open("w", encoding="utf-8", errors="replace") as handle:
        handle.write(f"[wp07] started_at={now_utc()} source={rel(source)}\n")
        handle.flush()
        try:
            proc = subprocess.run(
                [str(cosima), str(source)],
                cwd=ROOT,
                env=helper.cosima_env(),
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout_s,
                text=True,
            )
            handle.write(f"\n[wp07] finished_at={now_utc()} returncode={proc.returncode}\n")
            return {"status": "PASS" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode, "log": rel(log)}
        except subprocess.TimeoutExpired:
            handle.write(f"\n[wp07] timed_out_at={now_utc()} timeout_s={timeout_s}\n")
            return {"status": "TIMEOUT", "returncode": None, "log": rel(log)}


def collect_sim_outputs(base: Path) -> list[Path]:
    candidates: list[Path] = []
    for pattern in (base.name + ".inc*.id*.sim.gz", base.name + ".inc*.id*.sim"):
        candidates.extend(base.parent.glob(pattern))
    return sorted({p.resolve() for p in candidates})


def open_sim(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
    return path.open("rt", encoding="utf-8", errors="ignore")


def sim_file_stats(path: Path) -> dict[str, Any]:
    stats = {
        "path": rel(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "ID": 0,
        "SE": 0,
        "TS": 0,
        "TE_s": None,
        "first_id": None,
        "last_id": None,
    }
    with open_sim(path) as handle:
        for raw in handle:
            if raw.startswith("ID "):
                stats["ID"] += 1
                parts = raw.split()
                if len(parts) > 1 and parts[1].isdigit():
                    val = int(parts[1])
                    if stats["first_id"] is None:
                        stats["first_id"] = val
                    stats["last_id"] = val
            elif raw.startswith("SE"):
                stats["SE"] += 1
            elif raw.startswith("TS"):
                stats["TS"] += 1
            elif raw.startswith("TE "):
                vals = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", raw)
                if vals:
                    stats["TE_s"] = float(vals[0])
    return stats


def parse_catalog_for_pilot(
    adr: Any,
    name: str,
    sim_files: list[Path],
    event_rate_hz: float,
    manifest: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    def event_rate_for_mode(path: str, mode: str, science_flux: float):
        return "delayed", name, event_rate_hz

    adr.event_rate_for_mode = event_rate_for_mode
    cats = [adr.parse_sim_catalog((str(path), "delayed", 1.0)) for path in sim_files]
    merged = adr.merge_catalogs(cats)
    cat = adr.catalog_to_arrays(merged)

    mapping = {"status": "NOT_NEEDED", "rule": "constant event rate", "mapped_events": int(len(cat["local_id"]))}
    if name == "v2_weighted_eventlist":
        weight_path = resolve(manifest["v2_weighted_eventlist"]["weights"])
        weights = load_v2_weights(weight_path)
        ids = [int(x) for x in cat["local_id"]]
        if all(i in weights for i in ids):
            mapped = np.asarray([float(weights[i]) for i in ids], dtype=np.float64)
            mapping = {"status": "PASS_ZERO_BASED", "rule": "local_id -> pilot_event_id", "mapped_events": len(ids)}
        elif all((i - 1) in weights for i in ids):
            mapped = np.asarray([float(weights[i - 1]) for i in ids], dtype=np.float64)
            mapping = {"status": "PASS_ONE_BASED", "rule": "local_id - 1 -> pilot_event_id", "mapped_events": len(ids)}
        else:
            missing = [i for i in ids[:20] if i not in weights and (i - 1) not in weights]
            mapping = {
                "status": "FAIL",
                "rule": "could not map parsed SIM local_id values to pilot EventList weights",
                "mapped_events": 0,
                "sample_unmatched_ids": missing,
            }
            mapped = np.asarray(cat["rate_hz"], dtype=np.float64)
        cat["rate_hz"] = mapped
    return cat, mapping


def selected_diagnostics(step05: Any, adr: Any, run_rows: list[dict[str, Any]], manifest: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    disk = step05.side_entry_disk()
    diagnostics: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    problems: list[str] = []

    adr.is_active_veto_volume = step05.is_v3p5_active_veto_volume
    for row in run_rows:
        name = row["name"]
        sim_files = [resolve(p["path"]) for p in row.get("sim_outputs", [])]
        if not sim_files or row["run"]["status"] != "PASS":
            diagnostics.append({"name": name, "status": "NOT_PARSED", "reason": "transport did not produce a PASS SIM output"})
            continue
        norm = row["normalization"]
        try:
            cat, mapping = parse_catalog_for_pilot(adr, name, sim_files, float(norm["event_rate_hz"]), manifest)
            windows = {
                win: step05.summarize_window(cat, *step05.WINDOWS[win], disk=disk, reject_policy="keep")
                for win in WINDOW_ORDER
            }
            diag = {
                "name": name,
                "label": PILOTS[name]["label"],
                "status": "PASS" if mapping["status"] != "FAIL" else "FAIL_WEIGHT_MAPPING",
                "normalization": norm,
                "event_weight_mapping": mapping,
                "catalog": {
                    "generated_events_seen": int(cat["n_generated_events_seen"]),
                    "kept_events": int(len(cat["stream"])),
                    "tes_events": int(np.count_nonzero(cat["tes_total_keV"] > 0)),
                    "pixel_hits_kept": int(len(cat["pix_e"])),
                },
                "windows": windows,
            }
            diagnostics.append(diag)
            if diag["status"] != "PASS":
                problems.append(f"{name}: selected-rate weight mapping failed")
            for win, payload in windows.items():
                delayed = payload["by_stream"]["delayed"]
                for stage, event_key, rate_key in (
                    ("raw", "raw_events", "raw_rate_s-1"),
                    ("active_veto_pass", "active_veto_pass_events", "active_veto_pass_rate_s-1"),
                    ("side_compton_fov_pass", "side_compton_fov_pass_events", "side_compton_fov_pass_rate_s-1"),
                ):
                    csv_rows.append(
                        {
                            "pilot": name,
                            "window": win,
                            "stage": stage,
                            "events": delayed[event_key],
                            "rate_s-1": f"{float(delayed[rate_key]):.12g}",
                            "normalization_rule": norm["rule"],
                            "activity_Bq": norm["activity_Bq"],
                            "triggers": norm["triggers"],
                            "event_weight_mapping": mapping["status"],
                        }
                    )
        except Exception as exc:
            diagnostics.append({"name": name, "status": "FAIL_PARSE", "error": repr(exc)})
            problems.append(f"{name}: parse failed: {exc!r}")
    return diagnostics, csv_rows, problems


def write_selection_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "pilot",
        "window",
        "stage",
        "events",
        "rate_s-1",
        "normalization_rule",
        "activity_Bq",
        "triggers",
        "event_weight_mapping",
    ]
    with SELECTION_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# WP07 Pilot Transport",
        "",
        f"status: `{payload['status']}`",
        "",
        "Claim boundary: 1000-trigger pilot transport and selected-rate diagnostic only; no full-stat promotion.",
        "",
        "| pilot | run | generated IDs | kept events | W2 final events | W2 final cps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    diag_by_name = {d["name"]: d for d in payload.get("selection_diagnostics", [])}
    for row in payload["runs"]:
        name = row["name"]
        diag = diag_by_name.get(name, {})
        w2 = diag.get("windows", {}).get("w2_510p58_511p42", {}).get("by_stream", {}).get("delayed", {})
        catalog = diag.get("catalog", {})
        lines.append(
            "| {pilot} | `{run}` | {ids} | {kept} | {events} | {rate:.6g} |".format(
                pilot=name,
                run=row["run"]["status"],
                ids=catalog.get("generated_events_seen", ""),
                kept=catalog.get("kept_events", ""),
                events=w2.get("side_compton_fov_pass_events", ""),
                rate=float(w2.get("side_compton_fov_pass_rate_s-1", 0.0) or 0.0),
            )
        )
    lines.extend(["", "Outputs:"])
    for path in payload["outputs"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "Findings:"])
    for finding in payload["findings"]:
        lines.append(f"- {finding}")
    return "\n".join(lines) + "\n"


def run_or_collect(
    manifest: dict[str, Any],
    validation_rows: list[dict[str, Any]],
    timeout_s_by_name: dict[str, int],
    reparse_only: bool,
) -> list[dict[str, Any]]:
    run_rows: list[dict[str, Any]] = []
    validation_by_name = {row["name"]: row for row in validation_rows}
    for name in PILOT_ORDER:
        validation = validation_by_name[name]
        name = validation["name"]
        if validation["status"] != "PASS":
            run_rows.append({**validation, "run": {"status": "SKIPPED_INVALID_INPUT"}, "sim_outputs": []})
            continue
        meta = validation["meta"]
        source = resolve(meta["source"])
        base = output_base_for(meta)
        removed: list[str] = []
        if not reparse_only:
            removed = clean_expected_outputs(base)
            log = PILOT_RUNS / PILOTS[name]["log_name"]
            run = run_cosima(source, log, timeout_s_by_name[name])
        else:
            log = PILOT_RUNS / PILOTS[name]["log_name"]
            run = {"status": "REPARSE_ONLY", "returncode": None, "log": rel(log)}
        sims = collect_sim_outputs(base)
        sim_outputs = [sim_file_stats(path) for path in sims]
        if run["status"] == "REPARSE_ONLY" and sim_outputs:
            run["status"] = "PASS"
        elif run["status"] == "REPARSE_ONLY":
            log_path = resolve(run["log"])
            if log_path.exists() and "timed_out_at" in log_path.read_text(encoding="utf-8", errors="replace"):
                run["status"] = "TIMEOUT_PREVIOUS"
            elif not sim_outputs:
                run["status"] = "NO_SIM_OUTPUT_REPARSE_ONLY"
        if run["status"] == "PASS" and not sim_outputs:
            run["status"] = "FAIL_NO_SIM_OUTPUT"
        run_rows.append({**validation, "removed_previous_outputs": removed, "run": run, "sim_outputs": sim_outputs})
    return run_rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout-s", type=int, default=600)
    parser.add_argument("--legacy-timeout-s", type=int, default=300)
    parser.add_argument("--v2-timeout-s", type=int, default=None)
    parser.add_argument("--native-timeout-s", type=int, default=None)
    parser.add_argument("--reparse-only", action="store_true", help="Do not run Cosima; parse existing pilot outputs")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    PILOT_RUNS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    validation_rows, input_problems = validate_inputs(manifest)

    if input_problems:
        status = "BLOCKED_PILOT_INPUT_INVALID"
        payload = {
            "status": status,
            "generated_at": now_utc(),
            "claim_boundary": "pilot transport not launched because inputs failed validation",
            "input_validation": validation_rows,
            "problems": input_problems,
            "runs": [],
            "selection_diagnostics": [],
            "findings": input_problems,
            "outputs": [rel(RUN_SUMMARY_JSON), rel(SUMMARY_MD)],
            "next_gate": "fix WP07 pilot input validation before transport",
            "user_decision_required": False,
        }
        write_json(RUN_SUMMARY_JSON, payload)
        write_json(SUMMARY_JSON, payload)
        SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
        return 1

    timeout_s_by_name = {
        "legacy_l0": int(args.legacy_timeout_s),
        "v2_weighted_eventlist": int(args.v2_timeout_s if args.v2_timeout_s is not None else args.timeout_s),
        "native_volume_activation": int(args.native_timeout_s if args.native_timeout_s is not None else args.timeout_s),
    }
    run_rows = run_or_collect(manifest, validation_rows, timeout_s_by_name, args.reparse_only)
    transport_issues = [
        f"{row['name']}: transport status {row['run']['status']}"
        for row in run_rows
        if row["run"]["status"] != "PASS"
    ]

    selection_diagnostics: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    parse_problems: list[str] = []
    step05 = load_step05_module()
    adr = step05.load_adr_module()
    selection_diagnostics, selection_rows, parse_problems = selected_diagnostics(step05, adr, run_rows, manifest)
    write_selection_csv(selection_rows)

    problems = parse_problems
    legacy_only_transport_issue = bool(transport_issues) and all(item.startswith("legacy_l0:") for item in transport_issues)
    source_v2_native_parsed = {
        diag["name"]: diag.get("status")
        for diag in selection_diagnostics
        if diag.get("name") in ("v2_weighted_eventlist", "native_volume_activation")
    } == {"v2_weighted_eventlist": "PASS", "native_volume_activation": "PASS"}
    if not problems and not transport_issues:
        status = "PASS_PILOT_TRANSPORT_SELECTION_DIAGNOSTIC_NOT_PROMOTION"
    elif not problems and legacy_only_transport_issue and source_v2_native_parsed:
        status = "PARTIAL_PILOT_TRANSPORT_SOURCE_V2_NATIVE_SELECTION_DIAGNOSTIC_LEGACY_TIMEOUT_NOT_PROMOTION"
    else:
        status = "FAIL_PILOT_TRANSPORT_OR_PARSE"
    w2_findings = []
    for diag in selection_diagnostics:
        if diag.get("status") != "PASS":
            continue
        w2 = diag["windows"]["w2_510p58_511p42"]["by_stream"]["delayed"]
        w2_findings.append(
            "{name}: W2 side-Compton/FoV pass {events} events, {rate:.6g} cps ({rule})".format(
                name=diag["name"],
                events=w2["side_compton_fov_pass_events"],
                rate=float(w2["side_compton_fov_pass_rate_s-1"]),
                rule=diag["normalization"]["rule"],
            )
        )
    findings = [
        "Ran only the prepared 1000-trigger WP07 pilot matrix; no full-stat transport or promotion was launched.",
        *w2_findings,
    ]
    if problems:
        findings.extend(problems)
    if transport_issues:
        findings.extend(transport_issues)
    if not problems and all(
        (diag.get("windows", {}).get("w2_510p58_511p42", {}).get("by_stream", {}).get("delayed", {}).get("side_compton_fov_pass_events", 0) == 0)
        for diag in selection_diagnostics
        if diag.get("status") == "PASS"
    ):
        findings.append("All pilots have zero W2 final events at 1000-trigger statistics; this is a transport smoke diagnostic, not a rate bound.")

    outputs = [
        rel(RUN_SUMMARY_JSON),
        rel(RUN_SUMMARY_MD),
        rel(SELECTION_CSV),
        rel(SUMMARY_MD),
    ]
    for row in run_rows:
        outputs.extend(p["path"] for p in row.get("sim_outputs", []))
        if row.get("run", {}).get("log"):
            outputs.append(row["run"]["log"])

    payload = {
        "status": status,
        "generated_at": now_utc(),
        "claim_boundary": "1000-trigger pilot transport and selected-rate diagnostic only; no promotion or final rate claim",
        "reparse_only": bool(args.reparse_only),
        "timeout_s_by_name": timeout_s_by_name,
        "input_validation": validation_rows,
        "runs": run_rows,
        "selection_diagnostics": selection_diagnostics,
        "selection_csv_rows": len(selection_rows),
        "problems": problems,
        "transport_issues": transport_issues,
        "findings": findings,
        "outputs": outputs,
        "next_gate": "G8 promotion remains blocked until full-stat promotion criteria and downstream regeneration are explicitly released",
        "user_decision_required": False,
    }
    write_json(RUN_SUMMARY_JSON, payload)
    write_json(SUMMARY_JSON, payload)
    RUN_SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    SUMMARY_MD.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": status, "summary": rel(SUMMARY_JSON), "run_summary": rel(RUN_SUMMARY_JSON)}, indent=2))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
