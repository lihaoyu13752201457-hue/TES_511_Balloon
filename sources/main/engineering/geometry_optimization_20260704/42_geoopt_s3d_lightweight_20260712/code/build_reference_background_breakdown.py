#!/usr/bin/env python3
"""Build a paper-facing breakdown of the retained reference background.

The retained Step05 event catalogue is reselected with the exact W2, active-
veto, and side-entry Compton/FoV definitions.  Prompt survivors are grouped by
atmospheric particle family.  Delayed survivors are reconciled against the
existing exact-position source audit so inventory activity is not confused
with the nuclides that survive detector selection.

This script reads retained reference products and writes only into the new 42_
engineering package.  It never modifies the reference Step05/Step08 authority.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import math
import pickle
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
WORK = Path(__file__).resolve().parents[1]
DATA = WORK / "data"

MASS_WRAPPER = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/run_step05_fullstat_response.py"
)
STEP05_OUT = (
    ROOT
    / "stepwise_maintenance/step05_veto_time_axis/outputs_Mass_model_511_fullstat_v1_l1"
)
STEP05_SUMMARY = STEP05_OUT / "step05_Mass_model_511_fullstat_v1_l1_response_summary.json"
EVENT_CATALOG = STEP05_OUT / "work/event_catalog.pkl"
STEP08_SUMMARY = (
    ROOT
    / "stepwise_maintenance/step08_significance/outputs_Mass_model_511_fullstat_v1/"
    "step08_Mass_model_511_fullstat_v1_time_dependent_summary.json"
)
DELAYED_SOURCE_SUMMARY = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/03_detector_transport/delayed/"
    "candidate_Mass_model_511/fullstat_v1/F1/delayed_source_exactpos_summary.json"
)
DELAYED_SELECTED_EVENTS = (
    ROOT
    / "engineering/Mass_model_511_nearfield_migration_20260701/14_replacement_review_20260703/"
    "mass_model_511_w_activation_selected_w2_events.csv"
)

OUT_JSON = DATA / "reference_baseline_background_breakdown.json"
OUT_PROMPT = DATA / "reference_baseline_prompt_particles.csv"
OUT_DELAYED = DATA / "reference_baseline_delayed_nuclides.csv"
OUT_VOLUMES = DATA / "reference_baseline_delayed_source_volumes.csv"
OUT_MD = WORK / "REFERENCE_BASELINE_BACKGROUND.md"

W2 = (510.58, 511.42)
NUCLIDE_NAMES = {29061: "Cu-61", 29062: "Cu-62", 29064: "Cu-64"}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mass_wrapper() -> Any:
    spec = importlib.util.spec_from_file_location("reference_mass_step05", MASS_WRAPPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {MASS_WRAPPER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def weighted_summary(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    rate = sum(float(row["rate_hz"]) for row in rows)
    sigma = math.sqrt(sum(float(row["rate_hz"]) ** 2 for row in rows))
    return {"events": len(rows), "rate_cps": rate, "mc_sigma_cps": sigma}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def select_reference_events() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    wrapper = load_mass_wrapper()
    step05 = wrapper.load_step05()
    wrapper.configure_step05(step05)
    with EVENT_CATALOG.open("rb") as handle:
        cat = pickle.load(handle)

    lengths = {key: len(value) for key, value in cat.items() if isinstance(value, np.ndarray)}
    event_lengths = {
        lengths[key]
        for key in ("stream", "tag", "source_file", "local_id", "rate_hz", "tes_total_keV", "bgo_total_keV")
    }
    if len(event_lengths) != 1:
        raise RuntimeError(f"event catalogue grain mismatch: {event_lengths}")

    disk = step05.side_entry_disk()
    prompt: list[dict[str, Any]] = []
    delayed: list[dict[str, Any]] = []
    background_mask = (
        (cat["stream"] != "science")
        & (cat["tes_total_keV"] >= W2[0])
        & (cat["tes_total_keV"] < W2[1])
        & (cat["bgo_total_keV"] < 50.0)
    )
    for idx in np.flatnonzero(background_mask):
        keep, side_class = step05.side_keep_from_hits(step05.event_hits(cat, int(idx)), disk, "keep")
        if not keep:
            continue
        row = {
            "catalog_index": int(idx),
            "stream": str(cat["stream"][idx]),
            "particle": str(cat["tag"][idx]),
            "local_id": int(cat["local_id"][idx]),
            "rate_hz": float(cat["rate_hz"][idx]),
            "tes_total_keV": float(cat["tes_total_keV"][idx]),
            "active_veto_keV": float(cat["bgo_total_keV"][idx]),
            "side_compton_class": str(side_class),
            "source_file": str(cat["source_file"][idx]),
        }
        (prompt if row["stream"] == "prompt" else delayed).append(row)
    return prompt, delayed


def group_prompt(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["particle"])].append(row)
    total = sum(float(row["rate_hz"]) for row in rows)
    output: list[dict[str, Any]] = []
    for particle, items in grouped.items():
        summary = weighted_summary(items)
        output.append(
            {
                "particle": particle,
                **summary,
                "fraction_of_prompt": float(summary["rate_cps"]) / total if total else 0.0,
            }
        )
    output.sort(key=lambda row: float(row["rate_cps"]), reverse=True)
    return output


def delayed_provenance(selected_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    with DELAYED_SELECTED_EVENTS.open("r", encoding="utf-8", newline="") as handle:
        authority_rows = list(csv.DictReader(handle))
    problems: list[str] = []
    selected_ids = {int(row["local_id"]) for row in selected_rows}
    authority_ids = {int(row["local_id"]) for row in authority_rows}
    if selected_ids != authority_ids:
        problems.append(
            f"delayed local-id mismatch: selected_only={sorted(selected_ids-authority_ids)[:5]} "
            f"authority_only={sorted(authority_ids-selected_ids)[:5]}"
        )

    by_nuclide: dict[tuple[int, str], list[dict[str, str]]] = defaultdict(list)
    by_volume: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in authority_rows:
        za = int(row["ZA"])
        by_nuclide[(za, NUCLIDE_NAMES.get(za, f"ZA={za}"))].append(row)
        by_volume[row["VN"]].append(row)

    total_rate = sum(float(row["rate_hz"]) for row in authority_rows)
    nuclides: list[dict[str, Any]] = []
    for (za, name), items in by_nuclide.items():
        rate = sum(float(row["rate_hz"]) for row in items)
        nuclides.append(
            {
                "ZA": za,
                "nuclide": name,
                "events": len(items),
                "rate_cps": rate,
                "fraction_of_delayed": rate / total_rate if total_rate else 0.0,
            }
        )
    nuclides.sort(key=lambda row: float(row["rate_cps"]), reverse=True)

    volumes: list[dict[str, Any]] = []
    for volume, items in by_volume.items():
        rate = sum(float(row["rate_hz"]) for row in items)
        volumes.append(
            {
                "source_volume": volume,
                "events": len(items),
                "rate_cps": rate,
                "fraction_of_delayed": rate / total_rate if total_rate else 0.0,
            }
        )
    volumes.sort(key=lambda row: float(row["rate_cps"]), reverse=True)
    return nuclides, volumes, problems


def build_markdown(payload: dict[str, Any]) -> str:
    baseline = payload["reference_baseline"]
    lines = [
        "# Reference baseline background breakdown",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This is an engineering provenance report. Manuscript text must use descriptive configuration names.",
        "",
        "## Selected W2 background",
        "",
        f"- Prompt: `{baseline['prompt']['rate_cps']:.9g} cps` from `{baseline['prompt']['events']}` weighted events.",
        f"- Delayed: `{baseline['delayed']['rate_cps']:.9g} cps` from `{baseline['delayed']['events']}` weighted events.",
        f"- Total: `{baseline['total']['rate_cps']:.9g} +/- {baseline['total']['mc_sigma_cps']:.3g} cps` (MC counting, 1 sigma).",
        f"- Prompt fraction: `{100.0 * baseline['prompt_fraction']:.3f}%`.",
        "",
        "## Prompt particles after the full selection",
        "",
        "| particle | events | rate (cps) | fraction of prompt |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in payload["prompt_particles"]:
        lines.append(
            f"| {row['particle']} | {row['events']} | {float(row['rate_cps']):.9g} | {float(row['fraction_of_prompt']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Delayed inventory versus selected survivors",
            "",
            f"The day-15 corrected inventory is `{payload['delayed_inventory']['total_activity_Bq']:.6g} Bq`. "
            "Its leading sampled inventory entries are iodine-128 in CsI shield volumes, followed by aluminium-28 and copper-64 entries. "
            "The final selected W2 survivors are different:",
            "",
            "| nuclide | events | rate (cps) | fraction of delayed |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for row in payload["delayed_selected_nuclides"]:
        lines.append(
            f"| {row['nuclide']} | {row['events']} | {float(row['rate_cps']):.9g} | {float(row['fraction_of_delayed']):.3f} |"
        )
    lines.extend(
        [
            "",
            "All 28 delayed W2 survivors trace to copper-bearing cold-stage structures; 25 are Cu-64. "
            "The distinction between total activity and selected background is therefore mandatory.",
            "",
            "## Mission fold",
            "",
            f"- 20-day Z at 1e-4 ph cm^-2 s^-1: `{baseline['mission']['Z20d']:.7g}`.",
            f"- 20-day 3-sigma flux threshold: `{baseline['mission']['F3_20d_ph_cm2_s']:.7g} ph cm^-2 s^-1`.",
            "",
            "## Provenance",
            "",
        ]
    )
    for key, value in payload["inputs"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    required = [
        MASS_WRAPPER,
        STEP05_SUMMARY,
        EVENT_CATALOG,
        STEP08_SUMMARY,
        DELAYED_SOURCE_SUMMARY,
        DELAYED_SELECTED_EVENTS,
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("missing reference authority: " + "; ".join(missing))

    prompt_rows, delayed_rows = select_reference_events()
    prompt_summary = weighted_summary(prompt_rows)
    delayed_summary = weighted_summary(delayed_rows)
    total_summary = {
        "events": int(prompt_summary["events"]) + int(delayed_summary["events"]),
        "rate_cps": float(prompt_summary["rate_cps"]) + float(delayed_summary["rate_cps"]),
        "mc_sigma_cps": math.hypot(
            float(prompt_summary["mc_sigma_cps"]), float(delayed_summary["mc_sigma_cps"])
        ),
    }

    step05 = load_json(STEP05_SUMMARY)
    authoritative = step05["windows"]["w2_510p58_511p42"]["by_stream"]
    problems: list[str] = []
    checks = [
        (len(prompt_rows), int(authoritative["prompt"]["side_compton_fov_pass_events"]), "prompt events"),
        (len(delayed_rows), int(authoritative["delayed"]["side_compton_fov_pass_events"]), "delayed events"),
    ]
    for observed, expected, label in checks:
        if observed != expected:
            problems.append(f"{label}: observed={observed} expected={expected}")
    rate_checks = [
        (float(prompt_summary["rate_cps"]), float(authoritative["prompt"]["side_compton_fov_pass_rate_s-1"]), "prompt rate"),
        (float(delayed_summary["rate_cps"]), float(authoritative["delayed"]["side_compton_fov_pass_rate_s-1"]), "delayed rate"),
    ]
    for observed, expected, label in rate_checks:
        if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=1e-12):
            problems.append(f"{label}: observed={observed:.17g} expected={expected:.17g}")

    delayed_nuclides, delayed_volumes, delayed_problems = delayed_provenance(delayed_rows)
    problems.extend(delayed_problems)
    inventory = load_json(DELAYED_SOURCE_SUMMARY)
    step08 = load_json(STEP08_SUMMARY)

    prompt_particles = group_prompt(prompt_rows)
    mission = {
        "Z20d": float(step08["checks"]["A_reference_w2_Z20d_time_dependent"]),
        "F3_20d_ph_cm2_s": float(
            step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]
        ),
    }
    payload = {
        "status": "PASS_REFERENCE_BASELINE_BACKGROUND_BREAKDOWN" if not problems else "FAIL_REFERENCE_BASELINE_BACKGROUND_BREAKDOWN",
        "generated_at_utc": now_utc(),
        "selection": {
            "window_keV": list(W2),
            "active_veto_threshold_keV": 50.0,
            "side_compton_fov_reject_policy": "keep",
        },
        "reference_baseline": {
            "prompt": prompt_summary,
            "delayed": delayed_summary,
            "total": total_summary,
            "prompt_fraction": float(prompt_summary["rate_cps"]) / float(total_summary["rate_cps"]),
            "delayed_fraction": float(delayed_summary["rate_cps"]) / float(total_summary["rate_cps"]),
            "mission": mission,
        },
        "prompt_particles": prompt_particles,
        "delayed_inventory": {
            "total_activity_Bq": float(inventory["fixed_total_activity_Bq"]),
            "top_activity_volumes": inventory["activity_slices"]["top_activity_volumes"][:20],
            "top_drawn_species": inventory["top_drawn_species"][:20],
            "sampling_status": inventory["sampling_audit"]["status"],
        },
        "delayed_selected_nuclides": delayed_nuclides,
        "delayed_selected_source_volumes": delayed_volumes,
        "problems": problems,
        "inputs": {
            "step05_summary": rel(STEP05_SUMMARY),
            "event_catalog": rel(EVENT_CATALOG),
            "step08_summary": rel(STEP08_SUMMARY),
            "delayed_source_summary": rel(DELAYED_SOURCE_SUMMARY),
            "delayed_selected_event_authority": rel(DELAYED_SELECTED_EVENTS),
        },
        "claim_boundary": (
            "Rates are retained reference-geometry detector-selected estimates. Inventory activity and selected delayed survivors "
            "are distinct quantities. The atmospheric-511 sidecar used by the optimized comparison is not retroactively added "
            "to this historical reference baseline."
        ),
    }

    DATA.mkdir(parents=True, exist_ok=True)
    write_csv(
        OUT_PROMPT,
        prompt_particles,
        ["particle", "events", "rate_cps", "mc_sigma_cps", "fraction_of_prompt"],
    )
    write_csv(
        OUT_DELAYED,
        delayed_nuclides,
        ["ZA", "nuclide", "events", "rate_cps", "fraction_of_delayed"],
    )
    write_csv(
        OUT_VOLUMES,
        delayed_volumes,
        ["source_volume", "events", "rate_cps", "fraction_of_delayed"],
    )
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(build_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "prompt_events": len(prompt_rows),
                "delayed_events": len(delayed_rows),
                "total_rate_cps": total_summary["rate_cps"],
                "outputs": [rel(OUT_JSON), rel(OUT_PROMPT), rel(OUT_DELAYED), rel(OUT_VOLUMES), rel(OUT_MD)],
                "problems": problems,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
