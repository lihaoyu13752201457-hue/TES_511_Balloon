#!/usr/bin/env python3
"""Independently reconcile the O8 screening and mass evidence.

This validator reads only completed summaries/manifests.  It deliberately does
not reuse the event-selection implementation that created the screening JSON;
instead it checks arithmetic closure, paired margins, transport counts/seeds,
geometry authority, run-manifest agreement, and entry-surface bookkeeping.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scipy.stats import norm


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"

SCREEN = DATA / "s3d_o8_screening_analysis.json"
LEDGER = DATA / "s3d_o8_mass_ledger.json"
GEOMETRY = DATA / "s3d_o8_geometry_manifest.json"
GEOMETRY_VALIDATION = DATA / "s3d_o8_independent_geometry_validation.json"
PROMPT_DIR = ROOT / "runs/geometry_optimization_20260704/s3d_o8_eqstats_prompt_eplus_n_20260712"
PROMPT_SUMMARY = PROMPT_DIR / "run_summary.csv"
PROMPT_MANIFEST = PROMPT_DIR / "run_manifest.csv"
OUT_JSON = DATA / "s3d_o8_screening_independent_validation.json"
OUT_MD = PACKAGE / "SCREENING_DATA_VALIDATION.md"

EXPECTED_SCREEN_STATUS = "PASS_O8_SCREENING_PROMOTION_GATES"
EXPECTED_GEOMETRY_STATUS = "S3D_O8_FALLBACK_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS"
EXPECTED_PROMPT_EVENTS = 9_654_344
EXPECTED_SIGNAL_EVENTS = 37_194
DOMINANT_LIMIT_CPS = 0.0052
SIGNAL_LOSS_LIMIT = 0.02


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def close(a: float, b: float, *, atol: float = 1e-12, rtol: float = 1e-10) -> bool:
    return math.isclose(float(a), float(b), abs_tol=atol, rel_tol=rtol)


def main() -> int:
    required = (
        SCREEN,
        LEDGER,
        GEOMETRY,
        GEOMETRY_VALIDATION,
        PROMPT_SUMMARY,
        PROMPT_MANIFEST,
    )
    missing = [rel(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"missing validation input(s): {missing}")

    screen = load_json(SCREEN)
    ledger = load_json(LEDGER)
    geometry = load_json(GEOMETRY)
    geometry_validation = load_json(GEOMETRY_VALIDATION)
    prompt_summary = read_csv(PROMPT_SUMMARY)
    prompt_manifest = read_csv(PROMPT_MANIFEST)
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    checks["screening_final_pass"] = (
        screen.get("status") == EXPECTED_SCREEN_STATUS
        and not screen.get("pending_inputs")
        and not screen.get("audit_failures")
        and screen.get("no_zero_substitution") is True
    )
    checks["geometry_authority_pass"] = (
        geometry.get("status") == EXPECTED_GEOMETRY_STATUS
        and geometry.get("static_diff_status") == "PASS"
        and geometry.get("overlap_validation", {}).get("status") == "PASS"
        and geometry.get("overlap_validation", {}).get("hash_match") is True
        and geometry_validation.get("status") == "PASS"
    )

    baseline_mass = float(ledger["baseline_s3c_c0_shield_package_mass_kg"])
    optimized_mass = float(ledger["o8_shield_package_total_kg"])
    saved_mass = float(ledger["mass_saved_kg"])
    saved_fraction = float(ledger["mass_reduction_fraction"])
    checks["mass_arithmetic_closes"] = (
        close(baseline_mass - optimized_mass, saved_mass)
        and close(saved_mass / baseline_mass, saved_fraction)
        and close(optimized_mass, 309.77676671553456)
    )
    details["mass"] = {
        "baseline_kg": baseline_mass,
        "optimized_kg": optimized_mass,
        "saved_kg": saved_mass,
        "saved_fraction": saved_fraction,
    }

    manifest_by_job = {row["job_name"]: row for row in prompt_manifest}
    summary_by_job = {row["job_name"]: row for row in prompt_summary}
    checks["prompt_run_tables_close"] = (
        len(prompt_manifest) == 16
        and len(prompt_summary) == 16
        and len(manifest_by_job) == 16
        and set(manifest_by_job) == set(summary_by_job)
        and all(row["status"] in ("PASS", "SKIP") for row in prompt_summary)
        and sum(int(row["events"]) for row in prompt_summary) == EXPECTED_PROMPT_EVENTS
        and sum(int(row["generated_particles"]) for row in prompt_summary) == EXPECTED_PROMPT_EVENTS
        and all(
            summary_by_job[name]["particle"] == row["particle"]
            and int(summary_by_job[name]["events"]) == int(row["events"])
            and Path(summary_by_job[name]["sim_path"]).resolve() == Path(row["sim_path"]).resolve()
            for name, row in manifest_by_job.items()
        )
    )

    prompt_audit = screen["sections"]["prompt"]["run_audit"]
    audit_jobs = prompt_audit["headers"]
    checks["prompt_full_stream_headers_close"] = (
        prompt_audit.get("status") == "PASS"
        and len(audit_jobs) == 16
        and all(
            row.get("status") == "PASS"
            and int(row["sim_header"]["SE"]) == int(row["events"])
            and int(row["sim_header"]["ID"]) == int(row["events"])
            and int(row["sim_header"]["seed"]) == int(row["seed"])
            for row in audit_jobs
        )
    )

    gates = screen["promotion_gates"]
    dominant = gates["dominant_subset"]
    o8_components = dominant["components"]
    o8_rate = sum(float(row["o8_rate_cps"]) for row in o8_components)
    control_rate = sum(float(row["heavy_control_rate_cps"]) for row in o8_components)
    o8_sigma = math.sqrt(
        sum(int(row["o8_events"]) * float(row["o8_weight_cps"]) ** 2 for row in o8_components)
    )
    control_sigma = math.sqrt(
        sum(
            int(row["heavy_control_events"]) * float(row["heavy_control_weight_cps"]) ** 2
            for row in o8_components
        )
    )
    z = float(norm.ppf(0.975))
    expected_o8_interval = [max(0.0, o8_rate - z * o8_sigma), o8_rate + z * o8_sigma]
    expected_control_interval = [
        max(0.0, control_rate - z * control_sigma),
        control_rate + z * control_sigma,
    ]
    checks["dominant_gate_arithmetic_closes"] = (
        close(o8_rate, dominant["o8_rate_cps"])
        and close(control_rate, dominant["heavy_control_rate_cps"])
        and close(o8_rate / control_rate, dominant["o8_over_heavy_control"])
        and close(expected_o8_interval[0], dominant["o8_counting_95_gaussian_propagation"][0])
        and close(expected_o8_interval[1], dominant["o8_counting_95_gaussian_propagation"][1])
        and close(
            expected_control_interval[0],
            dominant["heavy_control_counting_95_gaussian_propagation"][0],
        )
        and close(
            expected_control_interval[1],
            dominant["heavy_control_counting_95_gaussian_propagation"][1],
        )
        and o8_rate <= DOMINANT_LIMIT_CPS
        and dominant.get("promotion_gate_pass") is True
        and dominant.get("evaluation_status") == "PASS"
    )
    details["dominant_gate"] = {
        "o8_rate_cps": o8_rate,
        "heavy_control_rate_cps": control_rate,
        "o8_over_heavy_control": o8_rate / control_rate,
        "limit_cps": DOMINANT_LIMIT_CPS,
        "margin_cps": DOMINANT_LIMIT_CPS - o8_rate,
        "recomputed_o8_gaussian_95": expected_o8_interval,
    }

    signal = gates["signal"]
    paired = signal["paired_acceptance_counts"]
    control_pass = int(paired["both_pass"]) + int(paired["heavy_control_only"])
    o8_pass = int(paired["both_pass"]) + int(paired["o8_only"])
    total = sum(int(value) for value in paired.values())
    ratio = o8_pass / control_pass
    loss = 1.0 - ratio
    checks["signal_pairing_closes"] = (
        total == EXPECTED_SIGNAL_EVENTS
        and control_pass == 29_703
        and o8_pass == 29_598
        and close(ratio, signal["o8_over_heavy_control_final_acceptance"])
        and close(loss, signal["relative_signal_loss"])
        and loss <= SIGNAL_LOSS_LIMIT
        and signal.get("promotion_gate_pass") is True
        and signal.get("evaluation_status") == "PASS"
    )
    details["signal_gate"] = {
        "heavy_control_pass": control_pass,
        "o8_pass": o8_pass,
        "total": total,
        "ratio": ratio,
        "relative_loss": loss,
        "limit": SIGNAL_LOSS_LIMIT,
    }

    atm = screen["sections"]["atm511"]
    atm_header = atm["sim_header"]
    atm_window = atm["windows"]["w2_510p58_511p42"]
    entries = atm["final_w2_entry_surface_audit"]
    o8_surfaces = entries["o8"]["surface_counts"]
    control_surfaces = entries["heavy_control"]["surface_counts"]
    checks["atmospheric_transport_and_entry_counts_close"] = (
        int(atm_header["SE"]) == 3_000_000
        and int(atm_header["ID"]) == 3_000_000
        and int(atm_header["seed"]) == 26_070_917
        and int(atm_window["side_compton_fov_pass_events"]) == 9
        and sum(int(value) for value in o8_surfaces.values()) == 9
        and o8_surfaces == {"bottom": 3, "side": 6}
        and sum(int(value) for value in control_surfaces.values()) == 6
        and control_surfaces == {"bottom": 1, "side": 5}
    )
    details["atmospheric_entry_surfaces"] = {
        "heavy_control": control_surfaces,
        "o8": o8_surfaces,
    }

    selection = screen["selection_contract"]
    checks["selection_contract_frozen"] = (
        selection.get("w2_window_keV") == [510.58, 511.42]
        and float(selection.get("active_veto_threshold_keV")) == 50.0
        and "reject_policy='keep'" in selection.get("side_compton_fov", "")
    )
    checks["promotion_metadata_closes"] = (
        gates.get("all_required_gates_evaluated") is True
        and gates.get("any_evaluated_gate_failed") is False
        and gates.get("decision_so_far") == "PASS_ALL_COMPLETED_GATES"
    )

    problems = [name for name, passed in checks.items() if not passed]
    status = "PASS_O8_SCREENING_INDEPENDENT_VALIDATION" if not problems else "FAIL"
    payload = {
        "status": status,
        "generated_at_utc": now_utc(),
        "checks": checks,
        "problems": problems,
        "details": details,
        "claim_boundary": (
            "Independent reconciliation of completed screening summaries, transport tables, "
            "geometry authority, and mass arithmetic; not an independent event-selection rerun "
            "and not the all-family/delayed mission closure."
        ),
        "inputs": {rel(path): sha256(path) for path in required},
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# O8 screening independent data validation",
                "",
                f"Status: `{status}`",
                "",
                f"- Shield-package mass: `{optimized_mass:.9f} kg`; saving `{saved_mass:.9f} kg` (`{100*saved_fraction:.5f}%`).",
                f"- Matched dominant subset: `{o8_rate:.12g} cps` versus limit `{DOMINANT_LIMIT_CPS:.12g} cps`.",
                f"- Matched signal: `{o8_pass}/{EXPECTED_SIGNAL_EVENTS}` versus `{control_pass}/{EXPECTED_SIGNAL_EVENTS}`; loss `{100*loss:.6f}%`.",
                f"- Atmospheric final-entry proxy: O8 `{o8_surfaces}`, heavy control `{control_surfaces}`.",
                f"- Failed checks: `{problems}`.",
                "",
                payload["claim_boundary"],
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "problems": problems, "json": rel(OUT_JSON)}, indent=2))
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
