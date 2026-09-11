#!/usr/bin/env python3
"""Independent arithmetic and provenance validation of the O8 full-chain result.

This validator intentionally does not import the Step05--Step08 production
runner.  It reloads the durable JSON/CSV products, reconstructs the 20-day
reference fold, and writes a compact machine-readable and human-readable audit.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
FULLCHAIN = PACKAGE / "fullchain"

STEP05 = FULLCHAIN / "step05/step05_s3d_o8_fullchain_l1_response_summary.json"
STEP06 = FULLCHAIN / "step06/step06_s3d_o8_fullchain_summary.json"
STEP06_BG = FULLCHAIN / "step06/background_time_variation.csv"
STEP07 = FULLCHAIN / "step07/source_case_summary.json"
STEP07_RATES = FULLCHAIN / "step07/source_case_rates.csv"
STEP08 = FULLCHAIN / "step08/step08_s3d_o8_fullchain_time_dependent_summary.json"
STEP08_CASES = FULLCHAIN / "step08/t3_t5_summary.csv"
DELAY_CAMPAIGN = DATA / "s3d_o8_delayed_activation_campaign.json"
SCREENING = DATA / "s3d_o8_screening_analysis.json"
MASS = DATA / "s3d_o8_mass_ledger.json"

OUT_JSON = DATA / "s3d_o8_fullchain_independent_validation.json"
OUT_MD = PACKAGE / "FULLCHAIN_DATA_VALIDATION.md"

REFERENCE_CASE = "A_point_w2_510p58_511p42_F0.0001"
REFERENCE_FLUX = 1.0e-4


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def close(a: float, b: float, *, rtol: float = 2.0e-10, atol: float = 1.0e-14) -> bool:
    return math.isclose(float(a), float(b), rel_tol=rtol, abs_tol=atol)


def now_utc() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def main() -> int:
    required = [
        STEP05,
        STEP06,
        STEP06_BG,
        STEP07,
        STEP07_RATES,
        STEP08,
        STEP08_CASES,
        DELAY_CAMPAIGN,
        SCREENING,
        MASS,
    ]
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("missing full-chain authority: " + ", ".join(missing))

    step05 = load_json(STEP05)
    step06 = load_json(STEP06)
    step07 = load_json(STEP07)
    step08 = load_json(STEP08)
    delay = load_json(DELAY_CAMPAIGN)
    screening = load_json(SCREENING)
    mass = load_json(MASS)
    background = read_csv(STEP06_BG)
    source_cases = read_csv(STEP07_RATES)
    folded_cases = read_csv(STEP08_CASES)

    problems: list[str] = []

    expected_statuses = {
        "step05": "PASS_S3D_O8_STEP05_FULLCHAIN_ALL8_PROMPT_NEUTRON_DELAYED_ATM511_MATCHED_SIGNAL",
        "step06": "PASS_S3D_O8_STEP06_FULLCHAIN_TIME_AXIS",
        "step07": "PASS_S3D_O8_STEP07_MATCHED_SIGNAL_SOURCE_CASES",
        "step08": "PASS_S3D_O8_STEP08_FULLCHAIN_TIME_DEPENDENT",
        "delay": "PASS_S3D_O8_NEUTRON_DELAYED_TRANSPORT",
        "delay_transport": "PASS",
        "screening": "PASS_O8_SCREENING_PROMOTION_GATES",
    }
    observed_statuses = {
        "step05": step05.get("status"),
        "step06": step06.get("status"),
        "step07": step07.get("status"),
        "step08": step08.get("status"),
        "delay": delay.get("status"),
        "delay_transport": delay.get("delayed_transport", {}).get("status"),
        "screening": screening.get("status"),
    }
    for name, expected in expected_statuses.items():
        if observed_statuses[name] != expected:
            problems.append(f"{name} status={observed_statuses[name]!r}, expected={expected!r}")

    groundstate = delay.get("groundstate_fix", {})
    exact_source = delay.get("exact_position_source", {})
    if groundstate.get("status") != "PASS":
        problems.append(f"ground-state correction status={groundstate.get('status')!r}")
    if exact_source.get("status") != "PASS":
        problems.append(f"exact-position source status={exact_source.get('status')!r}")
    if exact_source.get("sampling_status") != "PASS":
        problems.append(
            f"exact-position sampling status={exact_source.get('sampling_status')!r}"
        )
    if int(exact_source.get("m_pointsource_blocks") or 0) != 50000:
        problems.append(
            f"exact-position source blocks={exact_source.get('m_pointsource_blocks')!r}"
        )
    if delay.get("neutron_buildup", {}).get("problems"):
        problems.append(
            "neutron-buildup provenance problems="
            + repr(delay["neutron_buildup"]["problems"])
        )

    if mass.get("status") != "PRE_RELIEF_GEOMETRY_LEDGER_NOT_STRUCTURAL_QUALIFICATION":
        problems.append(f"mass-ledger status={mass.get('status')!r}")
    if not close(float(mass["o8_shield_package_total_kg"]), 309.77676671553456):
        problems.append("optimized shield-package mass changed")
    if not close(float(mass["mass_saved_kg"]), 81.42208058416543):
        problems.append("shield-package mass saving changed")

    window = step05["windows"]["w2_510p58_511p42"]
    physical = window["physical_reference_flux"]
    component_sum = (
        float(physical["prompt_background_cps"])
        + float(physical["delayed_background_cps"])
        + float(physical["atm511_sidecar_background_cps"])
    )
    if not close(component_sum, float(physical["background_cps"])):
        problems.append("Step05 final background does not equal prompt+delayed+atmospheric-line")
    uncertainty = physical["uncertainty_95"]
    upper_sum = (
        float(uncertainty["prompt_background_upper95_cps"])
        + float(uncertainty["delayed_background_upper95_cps"])
        + float(uncertainty["atm511_background_upper95_cps"])
    )
    if not close(upper_sum, float(uncertainty["background_upper95_cps"])):
        problems.append("Step05 95% background upper bound does not close by component")
    if float(uncertainty["signal_acceptance_lower95"]) > float(uncertainty["signal_acceptance"]):
        problems.append("signal lower confidence bound exceeds central acceptance")

    ref_sources = [row for row in source_cases if row["analysis_case_id"] == REFERENCE_CASE]
    ref_folded = [row for row in folded_cases if row["analysis_case_id"] == REFERENCE_CASE]
    if len(ref_sources) != 1 or len(ref_folded) != 1:
        problems.append(
            f"reference-case cardinality source/folded={len(ref_sources)}/{len(ref_folded)}"
        )
        ref_source: dict[str, str] = {}
        ref_case: dict[str, str] = {}
    else:
        ref_source = ref_sources[0]
        ref_case = ref_folded[0]

    w2_rows = [row for row in background if row["selection_id"] == "w2_510p58_511p42"]
    w2_rows.sort(key=lambda row: int(row["time_bin_id"]))
    if len(w2_rows) != int(step06["trajectory"]["bins"]):
        problems.append(
            f"trajectory-row count={len(w2_rows)}, expected={step06['trajectory']['bins']}"
        )

    fold: dict[str, float] = {}
    if ref_source and w2_rows:
        coincidence_window = float(step05["normalization"]["coincidence_window_s"])
        source_day15 = float(ref_source["final_rate_day15_cps"])
        source_day15_low = float(ref_source["final_rate_lower95_day15_cps"])
        signal_counts = background_counts = 0.0
        signal_counts_low = background_counts_up = 0.0
        live_min, live_max = 1.0, 0.0
        for row in w2_rows:
            dt = float(row["dt_s"])
            occupancy = (
                float(row["prompt_event_rate_hz"])
                + float(row["delayed_event_rate_hz"])
                + float(row["atm511_event_rate_hz"])
            )
            live = math.exp(-occupancy * coincidence_window)
            scale = float(row["science_atm_scale_to_day15"])
            signal_counts += source_day15 * scale * live * dt
            signal_counts_low += source_day15_low * scale * live * dt
            background_counts += float(row["background_final_cps"]) * live * dt
            background_counts_up += float(row["background_final_upper95_cps"]) * live * dt
            live_min = min(live_min, live)
            live_max = max(live_max, live)
        z = signal_counts / math.sqrt(background_counts)
        z_conservative = signal_counts_low / math.sqrt(background_counts_up)
        f3 = REFERENCE_FLUX * 3.0 / z
        f3_conservative = REFERENCE_FLUX * 3.0 / z_conservative
        fold = {
            "trajectory_rows": len(w2_rows),
            "integrated_live_time_s": sum(float(row["dt_s"]) for row in w2_rows),
            "accidental_live_factor_min": live_min,
            "accidental_live_factor_max": live_max,
            "source_counts": signal_counts,
            "background_counts": background_counts,
            "source_lower95_counts": signal_counts_low,
            "background_upper95_counts": background_counts_up,
            "Z20d": z,
            "Z20d_conservative95": z_conservative,
            "F3_20d_ph_cm2_s": f3,
            "F3_20d_conservative95_ph_cm2_s": f3_conservative,
        }

        comparisons = {
            "source_counts": (signal_counts, float(ref_case["total_source_counts"])),
            "background_counts": (background_counts, float(ref_case["total_background_counts"])),
            "source_lower95_counts": (
                signal_counts_low,
                float(ref_case["total_source_lower95_counts"]),
            ),
            "background_upper95_counts": (
                background_counts_up,
                float(ref_case["total_background_upper95_counts"]),
            ),
            "Z20d": (z, float(step08["checks"]["A_reference_w2_Z20d_time_dependent"])),
            "Z20d_conservative95": (
                z_conservative,
                float(step08["checks"]["A_reference_w2_Z20d_conservative95"]),
            ),
            "F3": (
                f3,
                float(step08["checks"]["A_reference_w2_flux_3sigma_20d_ph_cm2_s"]),
            ),
            "F3_conservative95": (
                f3_conservative,
                float(
                    step08["checks"][
                        "A_reference_w2_flux_3sigma_20d_conservative95_ph_cm2_s"
                    ]
                ),
            ),
        }
        for name, (recomputed, reported) in comparisons.items():
            if not close(recomputed, reported):
                problems.append(
                    f"independent fold mismatch {name}: recomputed={recomputed}, reported={reported}"
                )
        if z_conservative > z:
            problems.append("conservative significance exceeds central significance")
        if f3_conservative < f3:
            problems.append("conservative flux threshold is smaller than central threshold")

    files = {
        name: {"path": rel(path), "sha256": sha256(path)}
        for name, path in {
            "step05": STEP05,
            "step06": STEP06,
            "step06_background": STEP06_BG,
            "step07": STEP07,
            "step07_rates": STEP07_RATES,
            "step08": STEP08,
            "step08_cases": STEP08_CASES,
            "delayed_campaign": DELAY_CAMPAIGN,
            "screening": SCREENING,
            "mass_ledger": MASS,
        }.items()
    }
    payload = {
        "status": "PASS_O8_FULLCHAIN_INDEPENDENT_VALIDATION" if not problems else "FAIL",
        "generated_at_utc": now_utc(),
        "scope": (
            "Independent durable-product validation: status/provenance gates, Step05 rate "
            "closure, shield-package mass ledger, and a fresh Step06/07 CSV integration of "
            "the 20-day central and conservative Step08 reference metrics."
        ),
        "observed_statuses": observed_statuses,
        "delayed_provenance": {
            "groundstate_fix_status": groundstate.get("status"),
            "nubase": groundstate.get("nubase"),
            "nubase_sha256": groundstate.get("nubase_sha256"),
            "exact_position_source_status": exact_source.get("status"),
            "sampling_status": exact_source.get("sampling_status"),
            "m_pointsource_blocks": exact_source.get("m_pointsource_blocks"),
            "seed": exact_source.get("seed"),
        },
        "step05_primary_window": {
            "prompt_background_cps": physical["prompt_background_cps"],
            "delayed_background_cps": physical["delayed_background_cps"],
            "atm511_background_cps": physical["atm511_sidecar_background_cps"],
            "background_cps": physical["background_cps"],
            "signal_cps_at_reference_flux": physical["signal_cps_at_reference_flux"],
            "low_stat_final_background_events": physical["low_stat_final_background_events"],
            "background_upper95_cps": uncertainty["background_upper95_cps"],
            "signal_cps_lower95_at_reference_flux": uncertainty[
                "signal_cps_lower95_at_reference_flux"
            ],
        },
        "independent_mission_fold": fold,
        "mass_ledger": {
            "baseline_shield_package_kg": mass["baseline_s3c_c0_shield_package_mass_kg"],
            "optimized_shield_package_kg": mass["o8_shield_package_total_kg"],
            "mass_saved_kg": mass["mass_saved_kg"],
            "mass_reduction_fraction": mass["mass_reduction_fraction"],
            "boundary": mass["convention"],
        },
        "files": files,
        "problems": problems,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    mission = payload["independent_mission_fold"]
    lines = [
        "# O8 full-chain independent data validation",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This audit reloads the durable JSON/CSV products and independently reconstructs "
        "the 20-day reference fold; it does not import the production runner.",
        "",
    ]
    if mission:
        lines.extend(
            [
                "## Recomputed primary result",
                "",
                f"- Day-15 final background: `{physical['background_cps']:.12g} cps`",
                f"- Day-15 signal at the reference flux: `{physical['signal_cps_at_reference_flux']:.12g} cps`",
                f"- 20-day central Z / F3: `{mission['Z20d']:.12g}` / `{mission['F3_20d_ph_cm2_s']:.12g} ph cm^-2 s^-1`",
                f"- 20-day conservative-95 Z / F3: `{mission['Z20d_conservative95']:.12g}` / `{mission['F3_20d_conservative95_ph_cm2_s']:.12g} ph cm^-2 s^-1`",
                "",
            ]
        )
    lines.extend(["## Problems", ""])
    lines.extend([f"- {item}" for item in problems] or ["- None."])
    lines.extend(["", f"Machine-readable audit: `{rel(OUT_JSON)}`", ""])
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print(json.dumps({"status": payload["status"], "output": rel(OUT_JSON), "problems": problems}, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
