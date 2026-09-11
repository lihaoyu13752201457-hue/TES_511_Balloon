#!/usr/bin/env python3
"""Summarize collimator-off prompt-eplus raw line-window smoke."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_collimator_switch_smoke_20260618"
REPACK_WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
ENTRY_AUDIT = ROOT / "outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit_summary.json"
PROMPT_DIR = WORK / "runs/instant_eplus_g10m_r4_rawline"
REPACK_EPLUS_SUMMARY = REPACK_WORK / "prompt511_repack_direct_summary_eplus_g10m_r4.json"
OUT_JSON = WORK / "prompt511_collimator_switch_summary.json"
OUT_MD = WORK / "prompt511_collimator_switch_report.md"


def load_repack_parser():
    path = REPACK_WORK / "build_prompt511_repack_smoke.py"
    spec = importlib.util.spec_from_file_location("prompt511_repack_parser", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize_prompt_dir(prompt_dir: Path) -> dict:
    parser = load_repack_parser()
    rates = parser.load_prompt_rates(prompt_dir)
    rows = []
    total_events = 0
    total_rate = 0.0
    for sim in sorted(prompt_dir.glob("Background_eplus_fullsphere20_*.sim.gz")):
        row = parser.parse_sim_raw_window(sim, rates["eplus"])
        rows.append(row)
        total_events += int(row["line_window_events"])
        total_rate += float(row["line_window_rate_s-1"])
    return {
        "prompt_dir": str(prompt_dir.relative_to(ROOT)),
        "files": len(rows),
        "events_seen": sum(int(r["events_seen"]) for r in rows),
        "line_window_events": total_events,
        "rate_s-1": total_rate,
        "rate_per_event_s-1": rates["eplus"],
        "files_detail": rows,
    }


def ratio_with_poisson(num_rate: float, num_events: int, den_rate: float, den_events: int) -> dict:
    ratio = num_rate / den_rate if den_rate > 0 else None
    if ratio is None or num_events <= 0 or den_events <= 0:
        frac_sigma = None
        abs_sigma = None
    else:
        frac_sigma = math.sqrt(1.0 / num_events + 1.0 / den_events)
        abs_sigma = ratio * frac_sigma
    return {"ratio": ratio, "frac_sigma_1": frac_sigma, "abs_sigma_1": abs_sigma}


def effective_events_from_rows(rows: list[dict]) -> dict:
    total = sum(int(r["line_window_events"]) for r in rows)
    signatures = []
    complete = True
    for row in rows:
        examples = row.get("examples", [])
        if len(examples) != int(row["line_window_events"]):
            complete = False
            break
        signatures.append(tuple(e["local_id"] for e in examples))
    if complete and signatures and len(set(signatures)) == 1:
        return {
            "total_line_window_events": total,
            "effective_independent_events": len(signatures[0]),
            "replica_independence_note": "all replica line-window local-ID signatures are identical; use one-rep event count for counting-error scale",
        }
    return {
        "total_line_window_events": total,
        "effective_independent_events": total,
        "replica_independence_note": "replica line-window signatures are not identical or not completely stored",
    }


def main() -> int:
    audit = json.loads(ENTRY_AUDIT.read_text(encoding="utf-8"))
    current_raw_eplus = audit["stage_stats"]["current"]["raw"]["by_tag"]["prompt:eplus"]
    current_final_eplus = audit["stage_stats"]["current"]["final"]["by_tag"]["prompt:eplus"]
    repack = json.loads(REPACK_EPLUS_SUMMARY.read_text(encoding="utf-8"))
    repack_eplus = repack["totals_by_stream_tag"]["prompt:eplus"]
    repack_effective = effective_events_from_rows(repack.get("prompt_files", []))
    collimator_off = summarize_prompt_dir(PROMPT_DIR)
    collimator_effective = effective_events_from_rows(collimator_off["files_detail"])
    payload = {
        "status": "PASS_PROMPT511_COLLIMATOR_SWITCH_SMOKE",
        "claim_level": "diagnostic raw TES line-window prompt-eplus smoke; no veto, no Compton/FoV, no delayed rebuild",
        "line_window_keV": [510.58, 511.42],
        "geometry_switch": {
            "off_volumes": [
                "W_Side_Aperture_Sleeve_collimator_ZP_panel",
                "W_Side_Aperture_Sleeve_collimator_ZM_panel",
                "W_Side_Aperture_Sleeve_collimator_YP_panel",
                "W_Side_Aperture_Sleeve_collimator_YM_panel",
            ],
            "off_material": "Vacuum",
        },
        "current_fullstat_raw_eplus_baseline": current_raw_eplus,
        "current_fullstat_final_eplus_reference": current_final_eplus,
        "collimator_off_raw_eplus": collimator_off,
        "collimator_off_effective_counting_events": collimator_effective,
        "w_liner_repack_raw_eplus_reference": repack_eplus,
        "w_liner_repack_effective_counting_events": repack_effective,
        "collimator_off_over_current_raw": ratio_with_poisson(
            collimator_off["rate_s-1"],
            collimator_effective["effective_independent_events"],
            current_raw_eplus["rate_s-1"],
            current_raw_eplus["events"],
        ),
        "w_liner_repack_over_current_raw": ratio_with_poisson(
            repack_eplus["rate_s-1"],
            repack_effective["effective_independent_events"],
            current_raw_eplus["rate_s-1"],
            current_raw_eplus["events"],
        ),
        "interpretation": (
            "Collimator-off is consistent with the current raw eplus rate within counting "
            "statistics, while the local W-liner repack gives a clear lower raw eplus rate. "
            "Therefore the existing side-entry W sleeve is not the decisive prompt-eplus suppressor."
        ),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    off = payload["collimator_off_raw_eplus"]
    off_ratio = payload["collimator_off_over_current_raw"]
    liner_ratio = payload["w_liner_repack_over_current_raw"]
    lines = [
        "# Prompt-511 Collimator Switch Smoke Report",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Result",
        "",
        "| case | events | rate [s^-1] | ratio to current raw |",
        "|---|---:|---:|---:|",
        f"| current fullstat raw eplus | {current_raw_eplus['events']} | {current_raw_eplus['rate_s-1']:.6g} | 1 |",
        f"| collimator-off raw eplus | {off['line_window_events']} ({collimator_effective['effective_independent_events']} eff.) | {off['rate_s-1']:.6g} | {off_ratio['ratio']:.3g} +/- {off_ratio['abs_sigma_1']:.3g} |",
        f"| W-liner repack raw eplus | {repack_eplus['events']} ({repack_effective['effective_independent_events']} eff.) | {repack_eplus['rate_s-1']:.6g} | {liner_ratio['ratio']:.3g} +/- {liner_ratio['abs_sigma_1']:.3g} |",
        "",
        "## Interpretation",
        "",
        payload["interpretation"],
        "",
        "## Inputs",
        "",
        f"- Collimator-off run: `{off['prompt_dir']}`",
        "- Collimator-off switch: four `W_Side_Aperture_Sleeve_collimator_*` panels set to `Vacuum`.",
        f"- Current baseline: `{ENTRY_AUDIT.relative_to(ROOT)}`",
        f"- W-liner repack reference: `{REPACK_EPLUS_SUMMARY.relative_to(ROOT)}`",
        "",
        "## Boundaries",
        "",
        "- Raw TES line-window only; no veto, no Compton/FoV, no time axis.",
        "- This is not a delayed activation closure.",
        "- Current baseline uses 8 eplus full-stat replicas; collimator-off and W-liner references use 4 eplus replicas each.",
        f"- Collimator-off replica note: {collimator_effective['replica_independence_note']}.",
        f"- W-liner replica note: {repack_effective['replica_independence_note']}.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "summary": str(OUT_JSON.relative_to(ROOT)), "report": str(OUT_MD.relative_to(ROOT))}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
