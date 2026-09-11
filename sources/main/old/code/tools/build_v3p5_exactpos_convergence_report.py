#!/usr/bin/env python3
"""Build an exact-position delayed-source M/seed convergence report.

The report is intentionally conservative: source manifests are useful
diagnostics, but authority promotion requires transport-backed Step05/Step08
rows for more than one support size and more than one seed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "reports" / "v3p5_exactpos_convergence_20260614"
SUMMARY = OUT / "v3p5_exactpos_convergence_summary.json"
REPORT = OUT / "v3p5_exactpos_convergence_report.md"
TABLE = OUT / "v3p5_exactpos_convergence_cases.csv"

EXACT_PREFIX = "fullstat_v2_exactpos"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def f(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def discover_labels() -> list[str]:
    labels: set[str] = set()
    for manifest in ROOT.glob(f"runs/step02_delay_fix_v3p5_centerfinger_{EXACT_PREFIX}*/exactpos_delayed_source_manifest.json"):
        stem = manifest.parent.name.replace("step02_delay_fix_v3p5_centerfinger_", "", 1)
        if stem.startswith(EXACT_PREFIX):
            labels.add(stem)
    return sorted(labels, key=lambda label: (label != EXACT_PREFIX, label))


def case_paths(label: str) -> dict[str, Path]:
    return {
        "manifest": ROOT / "runs" / f"step02_delay_fix_v3p5_centerfinger_{label}" / "exactpos_delayed_source_manifest.json",
        "step02": ROOT / "stepwise_maintenance" / "step02_raw_background_simulation" / f"outputs_v3p5_centerfinger_{label}" / f"step02_v3p5_centerfinger_{label}_summary.json",
        "step05": ROOT / "stepwise_maintenance" / "step05_veto_time_axis" / f"outputs_v3p5_centerfinger_{label}_l1" / "step05_v3p5_centerfinger_l1_response_summary.json",
        "step08": ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{label}" / "step08_v3p5_centerfinger_time_dependent_summary.json",
    }


def read_case(label: str) -> dict[str, Any]:
    paths = case_paths(label)
    manifest = load_json(paths["manifest"]) or {}
    step02 = load_json(paths["step02"]) or {}
    step05 = load_json(paths["step05"]) or {}
    step08 = load_json(paths["step08"]) or {}
    audit = manifest.get("sampling_audit") or {}
    w2 = ((step05.get("windows") or {}).get("w2_510p58_511p42") or {}).get("by_stream") or {}
    prompt = w2.get("prompt") or {}
    delayed = w2.get("delayed") or {}
    science = w2.get("science") or {}
    science_norm = step05.get("science_physical_normalization") or {}
    step08_checks = step08.get("checks") or {}
    transport = step02.get("delayed_transport") or {}
    prompt_rate = f(prompt.get("side_compton_fov_pass_rate_s-1")) or 0.0
    delayed_rate = f(delayed.get("side_compton_fov_pass_rate_s-1")) or 0.0
    science_unit_rate = f(science.get("side_compton_fov_pass_rate_s-1"))
    science_scale = f(science_norm.get("scale_from_unit_eventlist_rate"))
    reference_flux = f(science_norm.get("reference_flux_ph_cm2_s")) or 1.0e-4
    science_physical_rate = (
        science_unit_rate * science_scale
        if science_unit_rate is not None and science_scale is not None
        else None
    )
    row = {
        "label": label,
        "manifest": rel(paths["manifest"]),
        "source_mode": manifest.get("source_mode", ""),
        "n_pointsource_blocks": int(manifest.get("n_pointsource_blocks") or 0),
        "seed": manifest.get("seed", ""),
        "sampling_rows": int(manifest.get("sampling_rows") or 0),
        "fixed_total_activity_Bq": f(manifest.get("fixed_total_activity_Bq")),
        "sum_flux_check_Bq": f(manifest.get("sum_flux_check_Bq")),
        "sampling_status": audit.get("status", ""),
        "top20_max_abs_sigma_delta": f(audit.get("top20_max_abs_sigma_delta")),
        "top20_expected_species_chi2": f(audit.get("top20_expected_species_chi2")),
        "transport_status": transport.get("status", ""),
        "transport_SE": transport.get("SE", ""),
        "transport_ID": transport.get("ID", ""),
        "transport_TE_s": f(transport.get("TE_s")),
        "step05_status": step05.get("status", ""),
        "w2_prompt_cps": prompt_rate,
        "w2_delayed_cps": delayed_rate,
        "w2_background_cps": prompt_rate + delayed_rate if step05 else None,
        "w2_signal_cps_at_1e_4": science_physical_rate,
        "w2_signal_response_cps_per_ph_cm2_s": (
            science_physical_rate / reference_flux
            if science_physical_rate is not None and reference_flux
            else None
        ),
        "w2_signal_unit_eventlist_pass_rate_s-1": science_unit_rate,
        "w2_signal_unit_area_proxy_cps_at_1e_4": (
            science_unit_rate * 1.0e-4 if science_unit_rate is not None else None
        ),
        "w2_final_events": (prompt.get("side_compton_fov_pass_events") or 0) + (delayed.get("side_compton_fov_pass_events") or 0) if step05 else "",
        "w2_delayed_events": delayed.get("side_compton_fov_pass_events", "") if step05 else "",
        "step08_status": step08.get("status", ""),
        "Z20d": f(step08_checks.get("A_reference_w2_Z20d_time_dependent")),
        "F3_20d": f(step08_checks.get("A_reference_w2_flux_3sigma_20d_ph_cm2_s")),
        "has_transport_backed_rate": bool(step05 and step08 and transport.get("status") == "PASS"),
    }
    return row


def rel_range(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    if mean == 0.0:
        return None
    return (max(values) - min(values)) / abs(mean)


def evaluate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    backed = [row for row in rows if row["has_transport_backed_rate"]]
    supports = sorted({int(row["n_pointsource_blocks"]) for row in backed})
    seeds_by_support: dict[int, set[int]] = {}
    for row in backed:
        seed = row.get("seed")
        if seed in ("", None):
            continue
        seeds_by_support.setdefault(int(row["n_pointsource_blocks"]), set()).add(int(seed))

    delayed_values = [float(row["w2_delayed_cps"]) for row in backed if row["w2_delayed_cps"] is not None]
    background_values = [float(row["w2_background_cps"]) for row in backed if row["w2_background_cps"] is not None]
    z_values = [float(row["Z20d"]) for row in backed if row["Z20d"] is not None]
    delayed_rel_range = rel_range(delayed_values)
    background_rel_range = rel_range(background_values)
    z_rel_range = rel_range(z_values)

    problems: list[str] = []
    if len(backed) < 3:
        problems.append("fewer than three transport-backed exactpos cases")
    if len(supports) < 2:
        problems.append("fewer than two PointSource support sizes with transport-backed rates")
    if not any(len(seeds) >= 2 for seeds in seeds_by_support.values()):
        problems.append("no support size has two or more transport-backed seeds")
    if delayed_rel_range is not None and delayed_rel_range > 0.20:
        problems.append(f"W2 delayed cps relative range is {delayed_rel_range:.4g}, above 0.20")
    if background_rel_range is not None and background_rel_range > 0.05:
        problems.append(f"W2 background cps relative range is {background_rel_range:.4g}, above 0.05")
    if z_rel_range is not None and z_rel_range > 0.05:
        problems.append(f"Z20d relative range is {z_rel_range:.4g}, above 0.05")

    status = "PASS_EXACTPOS_TRANSPORT_CONVERGENCE"
    authority_recommendation = "PROMOTE_EXACTPOS_TO_CURRENT_RATE_AUTHORITY"
    if problems:
        status = "PENDING_EXACTPOS_TRANSPORT_CONVERGENCE"
        authority_recommendation = "KEEP_FULLSTAT_V2_CONSERVATIVE_AUTHORITY_AND_EXACTPOS_PROVISIONAL"

    return {
        "status": status,
        "authority_recommendation": authority_recommendation,
        "transport_backed_cases": len(backed),
        "support_sizes_with_transport": supports,
        "seeds_by_support": {str(k): sorted(v) for k, v in seeds_by_support.items()},
        "w2_delayed_cps_relative_range": delayed_rel_range,
        "w2_background_cps_relative_range": background_rel_range,
        "Z20d_relative_range": z_rel_range,
        "problems": problems,
        "criteria": {
            "minimum_transport_backed_cases": 3,
            "minimum_support_sizes": 2,
            "minimum_repeated_seed_supports": 1,
            "max_w2_delayed_cps_relative_range": 0.20,
            "max_w2_background_cps_relative_range": 0.05,
            "max_Z20d_relative_range": 0.05,
        },
    }


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fmt(value: Any) -> str:
    if value in ("", None):
        return ""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(x):
        return "nan"
    if x == 0.0:
        return "0"
    if abs(x) < 1.0e-3 or abs(x) >= 1.0e5:
        return f"{x:.6e}"
    return f"{x:.6g}"


def markdown(payload: dict[str, Any]) -> str:
    evaluation = payload["evaluation"]
    lines = [
        "# v3p5 Exactpos M/Seed Convergence Report",
        "",
        f"Status: `{evaluation['status']}`.",
        f"Authority recommendation: `{evaluation['authority_recommendation']}`.",
        "",
        "This report separates source-level sampling diagnostics from transport-backed W2 rate convergence. Exactpos authority promotion requires transport-backed Step05/Step08 stability across support size and seed.",
        "",
        "## Evaluation",
        "",
        f"- Transport-backed cases: `{evaluation['transport_backed_cases']}`",
        f"- Support sizes with transport: `{evaluation['support_sizes_with_transport']}`",
        f"- Seeds by support: `{evaluation['seeds_by_support']}`",
        f"- W2 delayed cps relative range: `{fmt(evaluation['w2_delayed_cps_relative_range'])}`",
        f"- W2 background cps relative range: `{fmt(evaluation['w2_background_cps_relative_range'])}`",
        f"- Z20d relative range: `{fmt(evaluation['Z20d_relative_range'])}`",
        "",
        "## Problems",
        "",
    ]
    if evaluation["problems"]:
        lines.extend(f"- {problem}" for problem in evaluation["problems"])
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| label | M | seed | sampling | transport | W2 delayed cps | W2 bg cps | Z20d | F3 20d |",
            "| --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["cases"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["label"]),
                    str(row["n_pointsource_blocks"]),
                    str(row["seed"]),
                    str(row["sampling_status"]),
                    str(row["transport_status"]),
                    fmt(row["w2_delayed_cps"]),
                    fmt(row["w2_background_cps"]),
                    fmt(row["Z20d"]),
                    fmt(row["F3_20d"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Summary JSON: `{payload['outputs']['summary_json']}`",
            f"- Case table: `{payload['outputs']['case_table_csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="*", default=None, help="Exactpos labels to include; default discovers all exactpos manifests")
    args = ap.parse_args()

    labels = args.labels or discover_labels()
    rows = [read_case(label) for label in labels]
    rows.sort(key=lambda row: (int(row["n_pointsource_blocks"]), str(row["seed"]), row["label"]))
    OUT.mkdir(parents=True, exist_ok=True)
    evaluation = evaluate(rows)
    payload = {
        "status": evaluation["status"],
        "scope": "v3p5 exact-position delayed-source M/seed convergence",
        "cases": rows,
        "evaluation": evaluation,
        "outputs": {
            "summary_json": rel(SUMMARY),
            "report_md": rel(REPORT),
            "case_table_csv": rel(TABLE),
        },
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_csv_rows(TABLE, rows)
    REPORT.write_text(markdown(payload), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "report": rel(REPORT), "summary": rel(SUMMARY), "cases": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
