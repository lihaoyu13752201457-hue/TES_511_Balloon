#!/usr/bin/env python3
"""Build the PI-02 delayed selected-rate convergence artifact.

This script is intentionally scoped to PI-02.  It does not regenerate prompt,
signal, Step06--Step08, promotion, or authority outputs.  It parses delayed
transport SIMs, applies the same Step05 W2 active-veto and side-entry
Compton/FoV selection code, and combines independent exact-position samplings.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import importlib.util
import json
import math
import pickle
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "reports" / "fix5_immediate_fixes_20260623"
WORK_DIR = OUT_DIR / "pi02_work"
OUT_JSON = OUT_DIR / "delayed_selected_rate_convergence.json"
OUT_MD = OUT_DIR / "delayed_selected_rate_convergence.md"
OUT_CSV = OUT_DIR / "delayed_selected_rate_convergence.csv"
FIX5_GEO = (
    "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
BASE_LABEL = "fix5_fullstat_v2_exactpos_m50000_s260613"
PI02_RE = re.compile(r"^fix5_pi02_exactpos_m50000_s(?P<seed>\d+)$")
W2_LO_KEV = 510.58
W2_HI_KEV = 511.42
CONSISTENCY_K_SIGMA = 2.0


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_analysis_modules():
    old_tools = ROOT / "old" / "code" / "tools"
    if str(old_tools) not in sys.path:
        sys.path.insert(0, str(old_tools))
    adr = load_module("pi02_make_complete_day15_report_ADR", old_tools / "make_complete_day15_report_ADR.py")
    step05 = load_module("pi02_step05_l1_response", old_tools / "build_v3p5_centerfinger_step05_l1_response.py")

    # Both legacy modules compute ROOT from their old/ path.  Patch them back to
    # the live repository before calling any configured helpers.
    adr.ROOT = ROOT
    adr.WORKSPACE = ROOT
    step05.ROOT = ROOT
    step05.TOOLS = old_tools
    step05.configure_paths(BASE_LABEL)
    adr.is_active_veto_volume = step05.is_v3p5_active_veto_volume
    return adr, step05


def summary_path_for_label(label: str) -> Path:
    return ROOT / "outputs" / "reports" / label / "fix5_delayed_source_exactpos_summary.json"


def source_path_for_label(label: str, summary: dict[str, Any]) -> Path:
    return ROOT / str(summary["source"])


def command_for_label(label: str, source: str, seed: int) -> str:
    return (
        "source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh "
        f"&& cosima -s {seed} {source}"
    )


def parse_seed(label: str, summary: dict[str, Any]) -> int:
    match = PI02_RE.match(label)
    if match:
        return int(match.group("seed"))
    return int(summary.get("seed", 260613))


def source_geometry_status(source_path: Path) -> dict[str, Any]:
    text = source_path.read_text(encoding="utf-8", errors="ignore") if source_path.exists() else ""
    forbidden = "outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/" in text
    return {
        "source_card_path": rel(source_path),
        "exists": source_path.exists(),
        "contains_fix5_geometry": FIX5_GEO in text,
        "contains_forbidden_baseline_geometry": forbidden,
        "status": "PASS" if source_path.exists() and FIX5_GEO in text and not forbidden else "FAIL",
    }


def parse_delayed_catalog(adr, sim_path: Path, te_s: float, label: str, rebuild: bool):
    cache_dir = WORK_DIR / label / "file_catalogs"
    cache_dir.mkdir(parents=True, exist_ok=True)

    def event_rate_for_mode(path: str, mode: str, science_flux: float):
        if mode != "delayed":
            raise ValueError(mode)
        return "delayed", "activation", 1.0 / te_s

    adr.event_rate_for_mode = event_rate_for_mode
    cache = adr.parse_sim_catalog_to_cache((str(sim_path), "delayed", 1.0, str(cache_dir), rebuild))
    with Path(cache).open("rb") as handle:
        raw = pickle.load(handle)
    return adr.catalog_to_arrays(raw), rel(Path(cache))


def run_record(label: str, adr, step05, rebuild: bool) -> dict[str, Any]:
    summary_path = summary_path_for_label(label)
    summary = load_json(summary_path)
    transport = summary["delayed_transport"]
    sim_path = ROOT / str(transport["path"])
    source_path = source_path_for_label(label, summary)
    te_s = float(transport["TE_s"])
    seed = parse_seed(label, summary)

    cat, cache_path = parse_delayed_catalog(adr, sim_path, te_s, label, rebuild)
    disk = step05.side_entry_disk()
    selected = step05.summarize_window(cat, W2_LO_KEV, W2_HI_KEV, disk=disk, reject_policy="keep")
    delayed = selected["by_stream"]["delayed"]
    selected_events = int(delayed["side_compton_fov_pass_events"])
    selected_rate = float(delayed["side_compton_fov_pass_rate_s-1"])
    sigma = math.sqrt(selected_events) / te_s if selected_events > 0 else 0.0
    rel_unc = (1.0 / math.sqrt(selected_events)) if selected_events > 0 else None
    source_geo = source_geometry_status(source_path)
    sim_geometry = str(transport.get("geometry", "")).strip()
    sim_geometry_ok = sim_geometry.endswith(FIX5_GEO)
    provenance_ok = (
        source_geo["status"] == "PASS"
        and bool(transport.get("exists"))
        and int(transport.get("SE", 0)) == int(transport.get("ID", -1))
        and int(transport.get("SE", 0)) > 0
        and sim_geometry_ok
    )
    return {
        "run_id": label,
        "sampling_class": "production_position_exactpos_M50000",
        "generated_delayed_decays": int(transport.get("ID", 0)),
        "generated_decays": int(transport.get("ID", 0)),
        "selected_events": selected_events,
        "selected_rate_cps": selected_rate,
        "sigma_cps": sigma,
        "uncertainty_cps": sigma,
        "relative_uncertainty": rel_unc,
        "uncertainty_method": "Poisson sigma = sqrt(selected_events) / TE_s; relative = 1/sqrt(selected_events)",
        "source_activity_Bq": float(summary["fixed_total_activity_Bq"]),
        "sampling_id": f"M50000_exactpos_weighted_rpip_seed_{seed}",
        "seed_or_tag": str(seed),
        "geometry_path": FIX5_GEO,
        "source_card_path": source_geo["source_card_path"],
        "sim_header_geometry_path": sim_geometry,
        "command": command_for_label(label, source_geo["source_card_path"], seed),
        "output_path": rel(sim_path),
        "summary_path": rel(summary_path),
        "catalog_cache": cache_path,
        "TE_s": te_s,
        "raw_events": int(delayed["raw_events"]),
        "active_veto_pass_events": int(delayed["active_veto_pass_events"]),
        "raw_rate_cps": float(delayed["raw_rate_s-1"]),
        "active_veto_pass_rate_cps": float(delayed["active_veto_pass_rate_s-1"]),
        "side_compton_class_counts": delayed["side_compton_class_counts"],
        "source_geometry_status": source_geo,
        "sim_header_status": "PASS" if sim_geometry_ok else "FAIL",
        "provenance_status": "PASS" if provenance_ok else "FAIL",
        "sampling_audit_status": summary.get("sampling_audit", {}).get("status", "UNKNOWN"),
        "sampling_audit_problems": summary.get("sampling_audit", {}).get("problems", []),
    }


def between_sampling_check(runs: list[dict[str, Any]], combined_rate: float) -> dict[str, Any]:
    residuals = []
    failures = []
    for row in runs:
        sigma = float(row["uncertainty_cps"] or 0.0)
        if sigma <= 0.0:
            z = None
        else:
            z = (float(row["selected_rate_cps"]) - combined_rate) / sigma
            if abs(z) > CONSISTENCY_K_SIGMA:
                failures.append(row["run_id"])
        residuals.append(
            {
                "run_id": row["run_id"],
                "rate_cps": row["selected_rate_cps"],
                "sigma_cps": row["uncertainty_cps"],
                "z_vs_combined": z,
            }
        )
    return {
        "method": f"Each run rate compared with combined rate using explicit k={CONSISTENCY_K_SIGMA:g} sigma residuals.",
        "status": "PASS" if not failures and len(runs) >= 2 else "FAIL",
        "threshold_k_sigma": CONSISTENCY_K_SIGMA,
        "max_abs_z_vs_combined": max((abs(r["z_vs_combined"]) for r in residuals if r["z_vs_combined"] is not None), default=None),
        "residuals": residuals,
        "failures": failures,
    }


def build(labels: list[str], rebuild: bool) -> dict[str, Any]:
    adr, step05 = load_analysis_modules()
    runs = [run_record(label, adr, step05, rebuild) for label in labels]
    total_events = sum(int(row["selected_events"]) for row in runs)
    total_te = math.fsum(float(row["TE_s"]) for row in runs)
    combined_rate = total_events / total_te if total_te > 0.0 else 0.0
    combined_sigma = math.sqrt(total_events) / total_te if total_events > 0 else 0.0
    combined_rel = (1.0 / math.sqrt(total_events)) if total_events > 0 else None
    consistency = between_sampling_check(runs, combined_rate)
    provenance_ok = all(row["provenance_status"] == "PASS" and row["sampling_audit_status"] == "PASS" for row in runs)

    done = (
        len(runs) >= 2
        and total_events >= 100
        and combined_rel is not None
        and combined_rel <= 0.10
        and consistency["status"] == "PASS"
        and provenance_ok
    )
    reasons = []
    if len(runs) < 2:
        reasons.append("fewer than two production-position samplings")
    if total_events < 100:
        reasons.append(f"combined selected events {total_events} < 100")
    if combined_rel is None or combined_rel > 0.10:
        reasons.append(f"combined relative uncertainty {combined_rel} > 0.10")
    if consistency["status"] != "PASS":
        reasons.append("between-sampling consistency check failed")
    if not provenance_ok:
        reasons.append("one or more run provenance/sampling-audit checks failed")

    payload = {
        "artifact_type": "delayed_selected_rate_convergence",
        "created_utc": now_utc(),
        "scope": "PI-02 immediate-fixes convergence decision for fix5 delayed selected rate.",
        "done_contract": {
            "required_independent_production_position_samplings": 2,
            "required_combined_selected_events_min": 100,
            "required_relative_uncertainty_max": 0.10,
            "requires_run_provenance_for_each_sampling": True,
            "between_sampling_consistency_threshold_k_sigma": CONSISTENCY_K_SIGMA,
        },
        "runs": runs,
        "combined": {
            "independent_production_position_samplings": len(runs),
            "selected_events": total_events,
            "selected_rate_cps": combined_rate,
            "sigma_cps": combined_sigma,
            "uncertainty_cps": combined_sigma,
            "relative_uncertainty": combined_rel,
            "total_TE_s": total_te,
            "between_sampling_check": consistency["status"],
        },
        "between_sampling_check": consistency,
        "verdict": {
            "pi_status": "DONE" if done else "BLOCKED_WITH_EVIDENCE",
            "decision": "DONE" if done else "NOT_DONE",
            "reasons": [] if done else reasons,
            "allowed_manuscript_claim": (
                "The current delayed selected-rate estimate is supported by the PI-02 minimum convergence screen."
                if done
                else "The current delayed rate remains a low-statistics bookkeeping value, not a converged PI-02 delayed-rate claim."
            ),
        },
    }
    write_json(OUT_JSON, payload)
    write_csv(payload)
    write_md(payload)
    return payload


def write_csv(payload: dict[str, Any]) -> None:
    rows = payload["runs"]
    fields = [
        "run_id",
        "generated_decays",
        "selected_events",
        "selected_rate_cps",
        "uncertainty_cps",
        "relative_uncertainty",
        "source_activity_Bq",
        "sampling_id",
        "seed_or_tag",
        "geometry_path",
        "source_card_path",
        "sim_header_geometry_path",
        "command",
        "output_path",
        "provenance_status",
    ]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_md(payload: dict[str, Any]) -> None:
    lines = [
        "# Delayed Selected Rate Convergence",
        "",
        f"Created UTC: `{payload['created_utc']}`",
        "",
        f"PI-02 terminal status: `{payload['verdict']['pi_status']}`.",
        "",
        "| run | selected events | rate cps | sigma cps | rel sigma | provenance |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in payload["runs"]:
        rel_unc = row["relative_uncertainty"]
        lines.append(
            "| {run_id} | {selected_events} | {selected_rate_cps:.12g} | {uncertainty_cps:.12g} | {rel_unc} | {prov} |".format(
                run_id=row["run_id"],
                selected_events=row["selected_events"],
                selected_rate_cps=row["selected_rate_cps"],
                uncertainty_cps=row["uncertainty_cps"],
                rel_unc="" if rel_unc is None else f"{rel_unc:.6g}",
                prov=row["provenance_status"],
            )
        )
    combined = payload["combined"]
    lines.extend(
        [
            "",
            "## Combined",
            "",
            f"- independent samplings: `{combined['independent_production_position_samplings']}`",
            f"- selected events: `{combined['selected_events']}`",
            f"- selected rate: `{combined['selected_rate_cps']:.12g} cps`",
            f"- sigma: `{combined['sigma_cps']:.12g} cps`",
            f"- relative uncertainty: `{combined['relative_uncertainty']}`",
            f"- between-sampling check: `{payload['between_sampling_check']['status']}`",
            "",
            "## Verdict",
            "",
            f"- decision: `{payload['verdict']['decision']}`",
        ]
    )
    if payload["verdict"]["reasons"]:
        lines.append("- reasons:")
        lines.extend(f"  - {item}" for item in payload["verdict"]["reasons"])
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--labels",
        nargs="+",
        default=[BASE_LABEL],
        help="Delayed source/transport labels to combine.",
    )
    parser.add_argument("--rebuild-cache", action="store_true")
    args = parser.parse_args()
    payload = build(args.labels, args.rebuild_cache)
    print(
        json.dumps(
            {
                "status": payload["verdict"]["pi_status"],
                "decision": payload["verdict"]["decision"],
                "combined_selected_events": payload["combined"]["selected_events"],
                "combined_relative_uncertainty": payload["combined"]["relative_uncertainty"],
                "output": rel(OUT_JSON),
            },
            indent=2,
        )
    )
    return 0 if payload["verdict"]["decision"] == "DONE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
