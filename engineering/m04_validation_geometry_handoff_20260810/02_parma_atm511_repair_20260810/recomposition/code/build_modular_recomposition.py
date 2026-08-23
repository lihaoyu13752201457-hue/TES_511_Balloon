#!/usr/bin/env python3
"""Offline replacement of only the retained atmospheric 511-keV line module.

This program deliberately has no Cosima/transport interface.  It reads the
retained 81-bin W2 mission fold, deletes the legacy atmospheric-line sidecar
terms, applies the audited zero selected-rate W2 broadband-gamma line-de-dup
delta, removes the misplaced prompt-gamma line term from accidental-coincidence
occupancy, inserts a corrected PARMA mono-line response, and recomputes live
factors/counting metrics.  Prompt selected rates and every delayed, signal,
response, topology, and geometry term remain frozen.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[5]
PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PACKAGE / "config/modular_recomposition_config.json"
DEFAULT_OUTPUT = PACKAGE / "outputs/diagnostic_existing_line"

OUTPUT_NAMES = (
    "parma511_line_flux_by_time.csv",
    "w2_modular_recomposition_by_time.csv",
    "day15_modular_recomposition.json",
    "mission_20d_modular_recomposition.json",
    "RECOMPOSITION_RESULT.md",
    "recomposition_manifest.json",
)


class RecompositionError(RuntimeError):
    """An input authority, scope, or arithmetic invariant failed."""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def rel(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecompositionError(f"cannot read JSON {rel(path)}: {exc}") from exc
    if not isinstance(value, dict):
        raise RecompositionError(f"JSON authority is not an object: {rel(path)}")
    return value


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise RecompositionError(f"cannot read CSV {rel(path)}: {exc}") from exc


def close(a: float, b: float, *, atol: float = 1.0e-12, rtol: float = 2.0e-10) -> bool:
    return abs(a - b) <= atol + rtol * max(abs(a), abs(b))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RecompositionError(message)


def require_close(a: float, b: float, message: str, *, atol: float = 1.0e-12) -> None:
    if not close(a, b, atol=atol):
        raise RecompositionError(f"{message}: {a!r} != {b!r}")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def csv_text(rows: list[dict[str, Any]], fields: list[str]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def validate_hash_group(group: dict[str, Any], label: str) -> dict[str, Any]:
    records: dict[str, Any] = {}
    for name, item in group.items():
        path = resolve_path(item["path"])
        require(path.is_file(), f"missing {label} {name}: {rel(path)}")
        actual = sha256(path)
        expected = str(item["sha256"])
        require(actual == expected, f"{label} hash mismatch for {name}: {actual} != {expected}")
        records[name] = {
            "path": rel(path),
            "sha256": actual,
            "matches_config": True,
        }
    return records


def authority_path(config: dict[str, Any], name: str) -> Path:
    return resolve_path(config["authorities"][name]["path"])


def validate_scope_contract(config: dict[str, Any]) -> None:
    contract = config["scope_contract"]
    require(contract["only_replaced_module"] == "atmospheric annihilation 510.99895-keV mono line", "scope contract changed")
    for key in (
        "cosima_or_transport_allowed",
        "continuum_rerun_allowed",
        "m_sampling_transport_allowed",
        "retained_products_writable",
        "m04_writable",
    ):
        require(contract[key] is False, f"unsafe scope flag enabled: {key}")


def load_and_validate_authorities(config: dict[str, Any]) -> dict[str, Any]:
    authority_hashes = validate_hash_group(config["authorities"], "authority")
    protected_hashes = validate_hash_group(config["protected_files"], "protected file")
    mission_rows = read_csv(authority_path(config, "mission_timeline"))
    trajectory_rows = read_csv(authority_path(config, "trajectory"))
    mission_cfg = config["mission"]
    expected_bins = int(mission_cfg["expected_time_bins"])
    require(len(mission_rows) == expected_bins, f"mission timeline has {len(mission_rows)} rows, expected {expected_bins}")
    require(len(trajectory_rows) == expected_bins, f"trajectory has {len(trajectory_rows)} rows, expected {expected_bins}")
    require([int(row["time_bin_id"]) for row in mission_rows] == list(range(expected_bins)), "mission time-bin IDs are not 0..80")
    require([int(row["time_bin_id"]) for row in trajectory_rows] == list(range(expected_bins)), "trajectory time-bin IDs are not 0..80")

    elapsed_s = 0.0
    day15_matches: list[int] = []
    for index, (mission_row, trajectory_row) in enumerate(zip(mission_rows, trajectory_rows)):
        require_close(float(mission_row["day_mid"]), float(trajectory_row["day_mid"]), f"day_mid alignment at bin {index}")
        require_close(float(mission_row["dt_s"]), float(trajectory_row["dt_s"]), f"dt alignment at bin {index}")
        require_close(float(mission_row["vertical_depth_g_cm2"]), float(trajectory_row["depth_g_cm2"]), f"depth alignment at bin {index}")
        elapsed_s += float(mission_row["dt_s"])
        require_close(float(mission_row["elapsed_stop_day"]), elapsed_s / float(mission_cfg["seconds_per_day"]), f"elapsed day at bin {index}", atol=2.0e-12)
        if close(float(mission_row["day_mid"]), float(mission_cfg["day15_day_mid"])):
            day15_matches.append(index)
    require(day15_matches == [int(mission_cfg["expected_day15_index_zero_based"])], f"day-15 index mismatch: {day15_matches}")
    require_close(elapsed_s / float(mission_cfg["seconds_per_day"]), float(mission_cfg["expected_elapsed_days"]), "mission exposure")
    day15_index = day15_matches[0]
    day15 = mission_rows[day15_index]

    response = read_json(authority_path(config, "o8_response_summary"))
    try:
        primary_step05 = response["primary_authority"]["step05"]
        physical = primary_step05["windows"]["w2_510p58_511p42"]["physical_reference_flux"]
        prompt_occupancy_by_family = primary_step05["occupancy_day15_by_family"]["prompt"]
    except KeyError as exc:
        raise RecompositionError(f"O8 response-summary schema changed at {exc}") from exc
    require_close(float(day15["prompt_final_cps_noacc"]), float(physical["prompt_background_cps"]), "day-15 retained prompt vs O8 response")
    require_close(float(day15["delayed_final_cps_noacc"]), float(physical["delayed_background_cps"]), "day-15 retained delayed vs O8 response")
    require_close(float(day15["atm511_final_cps_noacc"]), float(physical["atm511_background_cps"]), "day-15 legacy sidecar vs O8 response")
    prompt_families = ("alpha", "eminus", "eplus", "gamma", "muminus", "muplus", "n", "p")
    require(set(prompt_occupancy_by_family) == set(prompt_families), "prompt occupancy family set changed")
    for index, mission_row in enumerate(mission_rows):
        expected_prompt_occupancy = sum(
            float(prompt_occupancy_by_family[family]["rate_hz"])
            * float(mission_row[f"prompt_scale_{family}"])
            for family in prompt_families
        )
        require_close(
            float(mission_row["prompt_event_rate_hz"]),
            expected_prompt_occupancy,
            f"prompt occupancy family-scale semantics at bin {index}",
            atol=5.0e-10,
        )
    require_close(float(day15["prompt_scale_gamma"]), 1.0, "day-15 prompt gamma scale")

    mission_summary = read_json(authority_path(config, "mission_summary"))
    require(mission_summary.get("status") == "PASS_EA_P02_FIXED_45DEG_SLANT_SIGNAL_REFOLD", "slant mission summary is not the retained PASS authority")
    require_close(float(day15["signal_final_cps_noacc"]), float(mission_summary["day15_selected_rates_cps"]["signal"]), "day-15 signal vs slant summary")

    dedup = read_json(authority_path(config, "prompt_gamma_line_dedup"))
    require(str(dedup.get("status", "")).startswith("PASS_OFFLINE_LINE_TERM_DEDUP"), "prompt-gamma line de-dup audit is not PASS")
    broad_delta = float(dedup["affected_events"]["selected_windows"]["broad_480_550"]["rate_delta_cps"])
    w2_delta = float(dedup["affected_events"]["selected_windows"]["w2_510p58_511p42"]["rate_delta_cps"])
    require(broad_delta == 0.0 and w2_delta == 0.0, f"line de-dup is not exactly zero: broad={broad_delta}, W2={w2_delta}")
    require(dedup["decision"]["entire_legacy_prompt_gamma_energy_axis_is_a_scientific_blocker"] is True, "factor-1000 prompt-gamma blocker disappeared")
    occupancy_cfg = config["prompt_gamma_line_occupancy_dedup"]
    step05_catalog = dedup["affected_events"]["step05_catalog"]
    removed_day15_hz = float(step05_catalog["removed_rate_sum_cps"])
    require_close(
        removed_day15_hz,
        float(occupancy_cfg["day15_removed_event_rate_hz"]),
        "prompt-gamma misplaced-line occupancy authority",
        atol=2.0e-12,
    )
    require(
        int(step05_catalog["affected_rows"])
        == int(occupancy_cfg["affected_rows_expected"]),
        "misplaced-line affected-row count changed",
    )
    require(
        int(step05_catalog["tes_nonzero_rows"])
        == int(occupancy_cfg["tes_nonzero_rows_expected"]),
        "misplaced-line audit unexpectedly has TES deposits",
    )
    require(
        int(step05_catalog["active_volume_nonzero_rows"])
        == int(occupancy_cfg["active_volume_nonzero_rows_expected"]),
        "misplaced-line active-only row closure changed",
    )
    require(occupancy_cfg["mission_scale_field"] == "prompt_scale_gamma", "prompt-gamma occupancy must use the gamma-family scale")
    gamma_prompt_day15_hz = float(prompt_occupancy_by_family["gamma"]["rate_hz"])
    require(0.0 < removed_day15_hz < gamma_prompt_day15_hz, "removed line occupancy is outside the day-15 prompt-gamma occupancy")
    scaled_removals = [
        removed_day15_hz * float(row["prompt_scale_gamma"])
        for row in mission_rows
    ]
    corrected_prompt_occupancies = [
        float(row["prompt_event_rate_hz"]) - removal
        for row, removal in zip(mission_rows, scaled_removals)
    ]
    require(all(value >= 0.0 for value in corrected_prompt_occupancies), "prompt occupancy became negative after line-term removal")
    occupancy_dedup_audit = {
        "status": "PASS_PROMPT_GAMMA_LINE_TERM_OCCUPANCY_SCALE_SEMANTICS",
        "provenance_path": "affected_events.step05_catalog.removed_rate_sum_cps",
        "affected_rows": int(step05_catalog["affected_rows"]),
        "tes_nonzero_rows": int(step05_catalog["tes_nonzero_rows"]),
        "active_volume_nonzero_rows": int(step05_catalog["active_volume_nonzero_rows"]),
        "removed_event_rate_day15_hz": removed_day15_hz,
        "day15_prompt_gamma_occupancy_before_dedup_hz": gamma_prompt_day15_hz,
        "removed_fraction_of_day15_prompt_gamma_occupancy": removed_day15_hz / gamma_prompt_day15_hz,
        "scale_field": "prompt_scale_gamma",
        "scale_min": min(float(row["prompt_scale_gamma"]) for row in mission_rows),
        "scale_max": max(float(row["prompt_scale_gamma"]) for row in mission_rows),
        "scaled_removal_min_hz": min(scaled_removals),
        "scaled_removal_max_hz": max(scaled_removals),
        "corrected_prompt_occupancy_min_hz": min(corrected_prompt_occupancies),
        "formula": occupancy_cfg["corrected_total_occupancy_formula"],
        "sidecar_subtracted_from_prompt": False,
    }

    environment = read_json(authority_path(config, "day15_environment"))
    env = environment["authority"]
    fold = config["parma_line_fold"]
    require_close(float(env["solar_modulation_MV"]), float(fold["solar_modulation_MV"]), "line W authority")
    require_close(float(env["cutoff_rigidity_GV"]), float(fold["cutoff_rigidity_GV"]), "line Rc authority")
    require_close(float(env["line_energy_keV"]), float(fold["line_energy_keV"]), "line energy authority")
    require_close(float(env["atmospheric_depth_g_cm2"]), float(trajectory_rows[day15_index]["depth_g_cm2"]), "day-15 line depth vs trajectory")
    require(not close(float(env["cutoff_rigidity_GV"]), float(trajectory_rows[day15_index]["Rc_GV"])), "expected documented line-Rc/legacy-trajectory-Rc distinction disappeared")

    line_closure = read_json(authority_path(config, "parma_line_source_closure"))
    require(line_closure.get("status") == "PASS_PARMA_511_SOURCE_LEVEL_ONLY", "PARMA line source closure is not PASS")
    require_close(float(line_closure["line_flux_ph_cm2_s"]), float(fold["expected_day15_flux_ph_cm2_s"]), "source closure line flux")
    require(int(line_closure["component_accounting"]["discrete_line_families_generated"]) == 1, "line source is not single-counted")
    require(int(line_closure["component_accounting"]["continuum_line_terms_modified"]) == 0, "continuum was modified by the line source package")

    return {
        "authority_hashes": authority_hashes,
        "protected_hashes": protected_hashes,
        "mission_rows": mission_rows,
        "trajectory_rows": trajectory_rows,
        "day15_index": day15_index,
        "dedup": dedup,
        "environment": environment,
        "mission_summary": mission_summary,
        "o8_response": response,
        "occupancy_dedup_audit": occupancy_dedup_audit,
    }


def identity_regression(config: dict[str, Any], mission_rows: list[dict[str, str]]) -> dict[str, Any]:
    coincidence_window = float(config["mission"]["coincidence_window_s"])
    cumulative_source = 0.0
    cumulative_background = 0.0
    cumulative_source_lower = 0.0
    cumulative_background_upper = 0.0
    max_residuals = {
        "live_factor": 0.0,
        "cumulative_source_counts": 0.0,
        "cumulative_background_counts": 0.0,
        "cumulative_source_lower_counts": 0.0,
        "cumulative_background_upper_counts": 0.0,
        "counting_Z": 0.0,
        "conditional_Z": 0.0,
    }
    for row in mission_rows:
        occupancy = sum(float(row[name]) for name in ("prompt_event_rate_hz", "delayed_event_rate_hz", "atm511_event_rate_hz"))
        live = math.exp(-occupancy * coincidence_window)
        background = sum(float(row[name]) for name in ("prompt_final_cps_noacc", "delayed_final_cps_noacc", "atm511_final_cps_noacc"))
        background_upper = sum(float(row[name]) for name in ("prompt_final_upper95_cps_noacc", "delayed_final_upper95_cps_noacc", "atm511_final_upper95_cps_noacc"))
        dt_s = float(row["dt_s"])
        cumulative_source += float(row["signal_final_cps_noacc"]) * live * dt_s
        cumulative_background += background * live * dt_s
        cumulative_source_lower += float(row["signal_final_lower95_cps_noacc"]) * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        z = cumulative_source / math.sqrt(cumulative_background)
        z_conditional = cumulative_source_lower / math.sqrt(cumulative_background_upper)
        comparisons = {
            "live_factor": (live, float(row["accidental_live_factor"])),
            "cumulative_source_counts": (cumulative_source, float(row["cumulative_source_counts"])),
            "cumulative_background_counts": (cumulative_background, float(row["cumulative_background_counts"])),
            "cumulative_source_lower_counts": (cumulative_source_lower, float(row["cumulative_source_transport_counting_lower_endpoint_counts"])),
            "cumulative_background_upper_counts": (cumulative_background_upper, float(row["cumulative_background_componentwise_transport_counting_upper_endpoint_counts"])),
            "counting_Z": (z, float(row["counting_Z"])),
            "conditional_Z": (z_conditional, float(row["counting_Z_componentwise_transport_counting_endpoint_conditional"])),
        }
        for name, (actual, expected) in comparisons.items():
            residual = abs(actual - expected)
            max_residuals[name] = max(max_residuals[name], residual)
            require_close(actual, expected, f"retained identity regression {name} at bin {row['time_bin_id']}", atol=5.0e-8)
    return {
        "status": "PASS_RETAINED_81BIN_FORMULA_IDENTITY",
        "max_absolute_residuals": max_residuals,
        "final": {
            "source_counts": cumulative_source,
            "background_counts": cumulative_background,
            "source_lower_counts": cumulative_source_lower,
            "background_upper_counts": cumulative_background_upper,
        },
    }


def parse_driver_flux(stdout: str) -> float:
    rows = list(csv.DictReader(io.StringIO(stdout)))
    matches = [row for row in rows if row.get("record") == "line" and row.get("key") == "integrated_flux"]
    require(len(matches) == 1, "PARMA line driver did not emit one integrated_flux record")
    value = float(matches[0]["value"])
    require(math.isfinite(value) and value > 0.0, f"invalid PARMA line flux: {value}")
    return value


def evaluate_line_fluxes(config: dict[str, Any], trajectory_rows: list[dict[str, str]], day15_index: int) -> tuple[list[float], dict[str, Any]]:
    fold = config["parma_line_fold"]
    driver_cfg = fold["driver"]
    driver = resolve_path(driver_cfg["path"])
    cwd = resolve_path(driver_cfg["working_directory"])
    require(driver.is_file() and os.access(driver, os.X_OK), f"PARMA line driver is not executable: {rel(driver)}")
    require(sha256(driver) == driver_cfg["sha256"], "PARMA line driver hash changed")
    require(cwd.is_dir(), f"PARMA vendor working directory missing: {rel(cwd)}")
    unique: dict[str, float] = {}
    stdout_hashes: dict[str, str] = {}
    for row in trajectory_rows:
        depth = float(row["depth_g_cm2"])
        key = repr(depth)
        if key in unique:
            continue
        command = [
            str(driver),
            "--s", repr(float(fold["solar_modulation_MV"])),
            "--rc", repr(float(fold["cutoff_rigidity_GV"])),
            "--depth", repr(depth),
            "--g", repr(float(fold["local_geometry_g"])),
            "--bins", "1",
            "--quadrature-order", "8",
        ]
        completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise RecompositionError(f"PARMA line driver failed at depth={depth}: {completed.stderr.strip()}")
        unique[key] = parse_driver_flux(completed.stdout)
        stdout_hashes[key] = hashlib.sha256(completed.stdout.encode("utf-8")).hexdigest()
    fluxes = [unique[repr(float(row["depth_g_cm2"]))] for row in trajectory_rows]
    expected = float(fold["expected_day15_flux_ph_cm2_s"])
    require_close(fluxes[day15_index], expected, "PARMA driver day-15 flux", atol=2.0e-13)
    return fluxes, {
        "status": "PASS_OFFICIAL_PARMA_LINE_FLUX_EVALUATION",
        "subprocess_allowlist": "only the hash-locked local parma511_driver; no Cosima/transport executable",
        "driver": rel(driver),
        "driver_sha256": sha256(driver),
        "working_directory": rel(cwd),
        "unique_depth_calls": len(unique),
        "stdout_sha256_by_depth": stdout_hashes,
        "day15_flux_ph_cm2_s": fluxes[day15_index],
    }


def poisson_upper_95(count: int) -> float:
    try:
        from scipy.stats import chi2
    except ImportError as exc:
        raise RecompositionError("SciPy is required for a high-stat Garwood endpoint") from exc
    return float(0.5 * chi2.ppf(0.975, 2.0 * (count + 1)))


def bool_field(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def resolve_receipt_response(receipt_path: Path, receipt: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    response_ref = receipt["response"]
    response_path = resolve_path(response_ref["summary"])
    require(response_path.is_file(), f"campaign response summary missing: {rel(response_path)}")
    require(sha256(response_path) == response_ref["summary_sha256"], "campaign response summary hash mismatch")
    complete = not receipt.get("incomplete_batch_indices") and not bool(receipt.get("allow_partial", False))
    meta = {
        "aggregate_receipt": rel(receipt_path),
        "aggregate_receipt_sha256": sha256(receipt_path),
        "aggregate_complete": complete,
        "included_batch_indices": receipt.get("included_batch_indices", []),
        "incomplete_batch_indices": receipt.get("incomplete_batch_indices", []),
        "allow_partial": bool(receipt.get("allow_partial", False)),
        "receipt_primary_gate": response_ref.get("primary_gate"),
    }
    return response_path, meta


def parse_highstat_response(
    config: dict[str, Any],
    input_path: Path,
    response_path: Path,
    response: dict[str, Any],
    receipt_meta: dict[str, Any] | None,
) -> dict[str, Any]:
    require(response.get("schema") == "o8-parma511-line-step05-response-v1", "line response schema changed")
    require(response.get("proposal") == "parma80", "final line response must use the physical parma80 proposal")
    detector_response = response["detector_response"]
    frozen_selection_hash = config["authorities"]["frozen_step05_selection"]["sha256"]
    require(detector_response["step05_sha256"] == frozen_selection_hash, "line response did not reuse the frozen Step05 selection")
    naming_blocker = str(detector_response.get("active_veto_predicate_blocker", ""))
    require("passive Kapton" in naming_blocker, "line response does not record the frozen passive-Kapton veto blocker")
    primary = response["primary_420eV"]
    weighted = primary["paired_reweight"]["80"]
    count = int(weighted["selected_events"])
    require(count == int(primary["w2_frozen_step05_pass_events"]), "line W2 count disagrees inside response summary")
    rate = float(weighted["importance_weighted_rate_cps"])
    sigma = float(weighted["mc_stat_sigma_cps"])
    ess = float(weighted["importance_effective_sample_size"])
    gate = response["primary_detector_rate_gate"]

    provenance_path = resolve_path(response["input_parse"]["path"])
    require(provenance_path.is_file(), f"line compact provenance missing: {rel(provenance_path)}")
    require(sha256(provenance_path) == response["input_parse"]["sha256"], "line compact provenance hash mismatch")
    provenance = read_json(provenance_path)
    te_s = float(provenance["sim_footer"]["TE_s"])
    require(te_s > 0.0, "non-positive line transport TE")
    require_close(rate, count / te_s, "parma80 W2 rate must equal count/TE", atol=2.0e-15)
    occupancy_events = int(provenance["counts"]["tes_or_active_events"])
    occupancy_rate = occupancy_events / te_s

    primary_csv = response_path.parent / "primary_event_response.csv"
    require(primary_csv.is_file(), f"primary response event table missing: {rel(primary_csv)}")
    artifact_candidates = [item for key, item in response.get("artifacts", {}).items() if Path(key).name == primary_csv.name]
    if artifact_candidates:
        require(sha256(primary_csv) == artifact_candidates[0]["sha256"], "primary response event table hash mismatch")
    event_rows = read_csv(primary_csv)
    w2_csv_count = sum(bool_field(row["final_w2"]) for row in event_rows)
    require(w2_csv_count == count, "primary response CSV W2 count disagrees with summary")
    accepted_topologies = {"single", "keep", "reject_kept"}
    broad_count = sum(
        1
        for row in event_rows
        if 480.0 <= float(row["measured_total_keV"]) < 550.0
        and float(row["active_total_keV"]) < 50.0
        and row["topology_class"] in accepted_topologies
    )
    aggregate_complete = bool(receipt_meta and receipt_meta["aggregate_complete"])
    detector_gate_pass = bool(gate["passes_detector_rate_gate"])
    if receipt_meta and receipt_meta.get("receipt_primary_gate") is not None:
        receipt_gate = receipt_meta["receipt_primary_gate"]
        require(
            bool(receipt_gate["passes_detector_rate_gate"]) == detector_gate_pass,
            "campaign receipt response.primary_gate disagrees with response-summary primary_detector_rate_gate",
        )
    final_input_gate = aggregate_complete and detector_gate_pass
    return {
        "input_kind": "final_line_campaign_aggregate" if receipt_meta else "direct_line_response_summary",
        "input_path": rel(input_path),
        "input_sha256": sha256(input_path),
        "response_summary_path": rel(response_path),
        "response_summary_sha256": sha256(response_path),
        "response_grade": "CAMPAIGN_RATE_GATE_PASS" if final_input_gate else "DIAGNOSTIC_OR_INCOMPLETE_LINE_RESPONSE",
        "passes_detector_rate_gate": detector_gate_pass,
        "passes_final_input_gate": final_input_gate,
        "campaign_receipt": receipt_meta,
        "w2_rate_day15_cps": rate,
        "w2_mc_sigma_day15_cps": sigma,
        "w2_upper95_day15_cps": poisson_upper_95(count) / te_s,
        "w2_upper95_method": "two-sided 95% Garwood upper endpoint on primary transported count divided by TE",
        "w2_selected_events": count,
        "w2_importance_effective_sample_size": ess,
        "broad_rate_day15_cps": broad_count / te_s,
        "broad_upper95_day15_cps": poisson_upper_95(broad_count) / te_s,
        "broad_selected_events": broad_count,
        "line_occupancy_day15_hz": occupancy_rate,
        "line_occupancy_events": occupancy_events,
        "line_occupancy_method": "exact merged tes_or_active_events/TE from the line-only campaign compact provenance",
        "transport_TE_s": te_s,
        "detector_gate": gate,
        "selection_frozen": True,
        "active_veto_kapton_blocker_preserved": True,
    }


def parse_line_input(config: dict[str, Any], input_path: Path, day15_base: dict[str, str]) -> dict[str, Any]:
    require(input_path.suffix.lower() == ".json", "line input must be a JSON diagnostic, response summary, or campaign aggregate receipt")
    require(input_path.is_file(), f"line input missing: {rel(input_path)}")
    value = read_json(input_path)
    if value.get("schema") == "o8-parma511-line-campaign-aggregate-v1":
        response_path, receipt_meta = resolve_receipt_response(input_path, value)
        response = read_json(response_path)
        return parse_highstat_response(config, input_path, response_path, response, receipt_meta)
    if value.get("schema") == "o8-parma511-line-step05-response-v1":
        return parse_highstat_response(config, input_path, input_path, value, None)
    if "offline_reweight" not in value or "parma_module" not in value:
        raise RecompositionError(f"unsupported line-input schema: {rel(input_path)}")

    weighted = value["offline_reweight"]["primary_420eV_8"]["80"]
    rate = float(weighted["rate_cps"])
    sigma = float(weighted["mc_sigma_cps"])
    parma_flux = float(value["parma_module"]["total_flux_ph_cm2_s"])
    old_flux = float(value["old_module"]["total_flux_ph_cm2_s"])
    require_close(parma_flux, float(config["parma_line_fold"]["expected_day15_flux_ph_cm2_s"]), "diagnostic PARMA flux")
    old_occ = float(day15_base["atm511_event_rate_hz"])
    z = float(config["mission"]["diagnostic_gaussian_z_two_sided_95"])
    return {
        "input_kind": "existing_low_stat_angular_reweight_diagnostic",
        "input_path": rel(input_path),
        "input_sha256": sha256(input_path),
        "response_summary_path": None,
        "response_summary_sha256": None,
        "response_grade": "DIAGNOSTIC_ONLY_FAILS_PARMA511_RATE_STATISTICS",
        "passes_detector_rate_gate": False,
        "passes_final_input_gate": False,
        "campaign_receipt": None,
        "w2_rate_day15_cps": rate,
        "w2_mc_sigma_day15_cps": sigma,
        "w2_upper95_day15_cps": rate + z * sigma,
        "w2_upper95_method": "diagnostic normal approximation rate + 1.95996*importance-weighted MC sigma; not an exact coverage endpoint",
        "w2_selected_events": int(value["gate"]["actual_primary_events"]),
        "w2_importance_effective_sample_size": float(weighted["ess"]),
        "broad_rate_day15_cps": None,
        "broad_upper95_day15_cps": None,
        "broad_selected_events": None,
        "line_occupancy_day15_hz": old_occ * parma_flux / old_flux,
        "line_occupancy_events": None,
        "line_occupancy_method": "DIAGNOSTIC scalar old-sidecar occupancy multiplied by total PARMA/legacy flux; angular occupancy reweight is unavailable in the compact cache",
        "transport_TE_s": float(value["old_module"]["observation_time_s"]),
        "detector_gate": value["gate"],
        "selection_frozen": True,
        "active_veto_kapton_blocker_preserved": True,
    }


def crossing(days: list[float], values: list[float], threshold: float) -> float | None:
    for index, value in enumerate(values):
        if value < threshold:
            continue
        if index == 0:
            return days[0]
        x0, x1 = days[index - 1], days[index]
        y0, y1 = values[index - 1], values[index]
        return x1 if y1 == y0 else x0 + (threshold - y0) * (x1 - x0) / (y1 - y0)
    return None


def time_or_extrapolate(days: list[float], values: list[float], threshold: float) -> float:
    value = crossing(days, values, threshold)
    require(values[-1] > 0.0, "cannot extrapolate a non-positive significance curve")
    return value if value is not None else days[-1] * (threshold / values[-1]) ** 2


def scientific_blockers(config: dict[str, Any], line: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = [dict(item) for item in config["scientific_blockers"]]
    if not line["passes_final_input_gate"]:
        blockers.append(
            {
                "id": "LINE_RESPONSE_INPUT_NOT_FINAL_RATE_GATE_AUTHORITY",
                "severity": "DIAGNOSTIC_BLOCKER",
                "statement": "The supplied line response is low-stat, direct-without-complete-aggregate, partial, or fails the detector-rate gate.",
                "scope_action": "Keep every reported number labeled DIAGNOSTIC; replace only this JSON input with the completed line campaign aggregate when available.",
            }
        )
    return blockers


def validate_recomposed_occupancy_formula(
    config: dict[str, Any], output_rows: list[dict[str, Any]], day15_index: int
) -> dict[str, Any]:
    removed_day15 = float(
        config["prompt_gamma_line_occupancy_dedup"]["day15_removed_event_rate_hz"]
    )
    coincidence_window = float(config["mission"]["coincidence_window_s"])
    max_residuals = {
        "scaled_line_term_removal_hz": 0.0,
        "prompt_after_dedup_hz": 0.0,
        "total_occupancy_hz": 0.0,
        "pre_fix_total_occupancy_hz": 0.0,
        "live_factor": 0.0,
        "pre_fix_live_factor": 0.0,
    }
    minimum_prompt_after = math.inf
    minimum_total = math.inf
    sidecar_rates: list[float] = []
    for row in output_rows:
        scale = float(row["prompt_scale_gamma"])
        prompt_before = float(
            row["prompt_event_rate_hz_retained_before_line_occupancy_dedup"]
        )
        removed = float(row["prompt_gamma_misplaced_line_event_rate_hz_removed"])
        prompt_after = float(row["prompt_event_rate_hz_after_line_occupancy_dedup"])
        delayed = float(row["delayed_event_rate_hz_retained"])
        corrected_line = float(row["corrected_parma511_event_rate_hz"])
        total = float(row["coincidence_occupancy_rate_hz_recomposed"])
        pre_fix_total = float(
            row["coincidence_occupancy_rate_hz_pre_fix_no_prompt_gamma_occupancy_dedup"]
        )
        live = float(row["accidental_live_factor_recomposed"])
        pre_fix_live = float(
            row["accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup"]
        )
        expected_removed = removed_day15 * scale
        expected_prompt_after = prompt_before - expected_removed
        expected_total = expected_prompt_after + delayed + corrected_line
        expected_pre_fix_total = prompt_before + delayed + corrected_line
        expected_live = math.exp(-expected_total * coincidence_window)
        expected_pre_fix_live = math.exp(-expected_pre_fix_total * coincidence_window)
        comparisons = {
            "scaled_line_term_removal_hz": (removed, expected_removed),
            "prompt_after_dedup_hz": (prompt_after, expected_prompt_after),
            "total_occupancy_hz": (total, expected_total),
            "pre_fix_total_occupancy_hz": (pre_fix_total, expected_pre_fix_total),
            "live_factor": (live, expected_live),
            "pre_fix_live_factor": (pre_fix_live, expected_pre_fix_live),
        }
        for name, (actual, expected) in comparisons.items():
            residual = abs(actual - expected)
            max_residuals[name] = max(max_residuals[name], residual)
            require_close(
                actual,
                expected,
                f"recomposed occupancy formula {name} at bin {row['time_bin_id']}",
                atol=5.0e-12,
            )
        require(prompt_after >= 0.0, f"negative corrected prompt occupancy at bin {row['time_bin_id']}")
        require(total >= 0.0, f"negative total occupancy at bin {row['time_bin_id']}")
        minimum_prompt_after = min(minimum_prompt_after, prompt_after)
        minimum_total = min(minimum_total, total)
        sidecar_rates.append(float(row["legacy_sidecar_event_rate_hz_removed"]))
    require(len(output_rows) == int(config["mission"]["expected_time_bins"]), "occupancy formula was not checked over all 81 bins")
    require_close(
        float(output_rows[day15_index]["prompt_gamma_misplaced_line_event_rate_hz_removed"]),
        removed_day15,
        "day-15 prompt-gamma occupancy removal",
        atol=2.0e-12,
    )
    require(all(value > 0.0 for value in sidecar_rates), "legacy sidecar occupancy provenance unexpectedly vanished")
    return {
        "status": "PASS_81BIN_PROMPT_GAMMA_LINE_OCCUPANCY_DEDUP_FORMULA",
        "checked_bins": len(output_rows),
        "max_absolute_residuals": max_residuals,
        "minimum_prompt_occupancy_after_dedup_hz": minimum_prompt_after,
        "minimum_total_occupancy_hz": minimum_total,
        "day15_removed_prompt_gamma_line_occupancy_hz": removed_day15,
        "legacy_sidecar_occupancy_omitted_separately_once": True,
        "legacy_sidecar_subtracted_from_prompt_occupancy": False,
        "formula": config["prompt_gamma_line_occupancy_dedup"]["corrected_total_occupancy_formula"],
    }


def recompose(
    config: dict[str, Any],
    validated: dict[str, Any],
    fluxes: list[float],
    line: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    mission_rows = validated["mission_rows"]
    trajectory_rows = validated["trajectory_rows"]
    day15_index = int(validated["day15_index"])
    day15_flux = fluxes[day15_index]
    coincidence_window = float(config["mission"]["coincidence_window_s"])
    reference_flux = float(config["mission"]["reference_flux_ph_cm2_s"])
    w2_dedup_delta = float(validated["dedup"]["affected_events"]["selected_windows"]["w2_510p58_511p42"]["rate_delta_cps"])
    broad_dedup_delta = float(validated["dedup"]["affected_events"]["selected_windows"]["broad_480_550"]["rate_delta_cps"])
    require(w2_dedup_delta == 0.0 and broad_dedup_delta == 0.0, "nonzero line de-dup cannot enter the frozen W2 fold")
    removed_prompt_gamma_line_occ_day15 = float(
        validated["occupancy_dedup_audit"]["removed_event_rate_day15_hz"]
    )

    output_rows: list[dict[str, Any]] = []
    flux_rows: list[dict[str, Any]] = []
    cumulative_source = cumulative_background = 0.0
    cumulative_source_lower = cumulative_background_upper = 0.0
    prefixed_bug_source = prefixed_bug_background = 0.0
    prefixed_bug_source_lower = prefixed_bug_background_upper = 0.0
    elapsed_s = 0.0
    days: list[float] = []
    z_curve: list[float] = []
    z_conditional_curve: list[float] = []
    for base, trajectory, flux in zip(mission_rows, trajectory_rows, fluxes):
        scale = flux / day15_flux
        prompt_occ = float(base["prompt_event_rate_hz"])
        prompt_gamma_scale = float(base["prompt_scale_gamma"])
        removed_prompt_gamma_line_occ = (
            removed_prompt_gamma_line_occ_day15 * prompt_gamma_scale
        )
        prompt_occ_after_line_dedup = prompt_occ - removed_prompt_gamma_line_occ
        require(
            prompt_occ_after_line_dedup >= 0.0,
            f"negative de-duplicated prompt occupancy at bin {base['time_bin_id']}",
        )
        delayed_occ = float(base["delayed_event_rate_hz"])
        old_line_occ = float(base["atm511_event_rate_hz"])
        new_line_occ = float(line["line_occupancy_day15_hz"]) * scale
        total_occ = prompt_occ_after_line_dedup + delayed_occ + new_line_occ
        prefixed_bug_total_occ = prompt_occ + delayed_occ + new_line_occ
        live = math.exp(-total_occ * coincidence_window)
        prefixed_bug_live = math.exp(-prefixed_bug_total_occ * coincidence_window)

        prompt = float(base["prompt_final_cps_noacc"])
        delayed = float(base["delayed_final_cps_noacc"])
        old_line = float(base["atm511_final_cps_noacc"])
        new_line = float(line["w2_rate_day15_cps"]) * scale
        background = prompt + delayed - w2_dedup_delta + new_line
        signal = float(base["signal_final_cps_noacc"])
        prompt_upper = float(base["prompt_final_upper95_cps_noacc"])
        delayed_upper = float(base["delayed_final_upper95_cps_noacc"])
        old_line_upper = float(base["atm511_final_upper95_cps_noacc"])
        new_line_upper = float(line["w2_upper95_day15_cps"]) * scale
        background_upper = prompt_upper + delayed_upper + new_line_upper
        signal_lower = float(base["signal_final_lower95_cps_noacc"])

        dt_s = float(base["dt_s"])
        cumulative_source += signal * live * dt_s
        cumulative_background += background * live * dt_s
        cumulative_source_lower += signal_lower * live * dt_s
        cumulative_background_upper += background_upper * live * dt_s
        prefixed_bug_source += signal * prefixed_bug_live * dt_s
        prefixed_bug_background += background * prefixed_bug_live * dt_s
        prefixed_bug_source_lower += signal_lower * prefixed_bug_live * dt_s
        prefixed_bug_background_upper += background_upper * prefixed_bug_live * dt_s
        elapsed_s += dt_s
        elapsed_day = elapsed_s / float(config["mission"]["seconds_per_day"])
        z_value = cumulative_source / math.sqrt(cumulative_background)
        z_conditional = cumulative_source_lower / math.sqrt(cumulative_background_upper)
        days.append(elapsed_day)
        z_curve.append(z_value)
        z_conditional_curve.append(z_conditional)

        output_rows.append(
            {
                "time_bin_id": int(base["time_bin_id"]),
                "day_mid": float(base["day_mid"]),
                "elapsed_stop_day": elapsed_day,
                "dt_s": dt_s,
                "altitude_km": float(trajectory["altitude_km"]),
                "latitude_deg": float(trajectory["latitude_deg"]),
                "longitude_deg": float(trajectory["longitude_deg"]),
                "trajectory_Rc_GV_retained_prompt_delayed_only": float(trajectory["Rc_GV"]),
                "depth_g_cm2": float(trajectory["depth_g_cm2"]),
                "corrected_line_Rc_GV_fixed": float(config["parma_line_fold"]["cutoff_rigidity_GV"]),
                "corrected_line_flux_ph_cm2_s": flux,
                "corrected_line_flux_scale_to_day15": scale,
                "prompt_scale_gamma": prompt_gamma_scale,
                "prompt_event_rate_hz_retained_before_line_occupancy_dedup": prompt_occ,
                "prompt_gamma_misplaced_line_event_rate_hz_removed": removed_prompt_gamma_line_occ,
                "prompt_event_rate_hz_after_line_occupancy_dedup": prompt_occ_after_line_dedup,
                "delayed_event_rate_hz_retained": delayed_occ,
                "legacy_sidecar_event_rate_hz_removed": old_line_occ,
                "corrected_parma511_event_rate_hz": new_line_occ,
                "coincidence_occupancy_rate_hz_recomposed": total_occ,
                "coincidence_occupancy_rate_hz_pre_fix_no_prompt_gamma_occupancy_dedup": prefixed_bug_total_occ,
                "accidental_live_factor_recomposed": live,
                "accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup": prefixed_bug_live,
                "prompt_final_cps_noacc_retained": prompt,
                "delayed_final_cps_noacc_retained": delayed,
                "legacy_sidecar_final_cps_noacc_removed": old_line,
                "prompt_gamma_line_dedup_delta_cps": w2_dedup_delta,
                "corrected_parma511_final_cps_noacc": new_line,
                "background_final_cps_noacc_recomposed": background,
                "signal_final_cps_noacc_retained": signal,
                "prompt_final_upper95_cps_noacc_retained": prompt_upper,
                "delayed_final_upper95_cps_noacc_retained": delayed_upper,
                "legacy_sidecar_final_upper95_cps_noacc_removed": old_line_upper,
                "corrected_parma511_final_upper95_cps_noacc": new_line_upper,
                "background_componentwise_endpoint_cps_noacc_recomposed": background_upper,
                "signal_final_lower95_cps_noacc_retained": signal_lower,
                "cumulative_source_counts": cumulative_source,
                "cumulative_background_counts": cumulative_background,
                "cumulative_source_transport_counting_lower_endpoint_counts": cumulative_source_lower,
                "cumulative_background_componentwise_endpoint_counts": cumulative_background_upper,
                "counting_Z": z_value,
                "counting_Z_componentwise_endpoint_conditional": z_conditional,
            }
        )
        flux_rows.append(
            {
                "time_bin_id": int(base["time_bin_id"]),
                "day_mid": float(base["day_mid"]),
                "depth_g_cm2": float(trajectory["depth_g_cm2"]),
                "solar_modulation_MV_fixed": float(config["parma_line_fold"]["solar_modulation_MV"]),
                "cutoff_rigidity_GV_fixed": float(config["parma_line_fold"]["cutoff_rigidity_GV"]),
                "trajectory_Rc_GV_not_used_for_line": float(trajectory["Rc_GV"]),
                "parma511_flux_ph_cm2_s": flux,
                "scale_to_day15": scale,
            }
        )

    occupancy_formula_audit = validate_recomposed_occupancy_formula(
        config, output_rows, day15_index
    )
    day15_base = mission_rows[day15_index]
    day15_row = output_rows[day15_index]
    blockers = scientific_blockers(config, line)
    diagnostic = not bool(line["passes_final_input_gate"])
    status = (
        "DIAGNOSTIC_ONLY_MODULAR_RECOMPOSITION__NOT_PAPER_AUTHORITY"
        if diagnostic
        else "MODULAR_RECOMPOSITION_COMPLETE__SCIENTIFIC_BLOCKERS_REMAIN__NOT_PUBLICATION_AUTHORITY"
    )
    old_background_day15 = float(day15_base["background_final_cps_noacc"])
    new_background_day15 = float(day15_row["background_final_cps_noacc_recomposed"])
    day15_summary = {
        "schema": "o8-parma511-day15-modular-recomposition-v1",
        "status": status,
        "selection_id": config["mission"]["selection_id"],
        "window_keV": config["mission"]["window_keV"],
        "day15_index_zero_based": day15_index,
        "composition": {
            "formula": "R_new = R_old - R_legacy_sidecar - Delta_R_prompt_gamma_line + R_PARMA511_corrected",
            "occupancy_formula": config["prompt_gamma_line_occupancy_dedup"]["corrected_total_occupancy_formula"],
            "legacy_sidecar_removed": True,
            "legacy_sidecar_subtracted_from_prompt_occupancy": False,
            "prompt_gamma_line_dedup_delta_W2_cps": w2_dedup_delta,
            "prompt_gamma_line_dedup_delta_broad_480_550_cps": broad_dedup_delta,
            "prompt_gamma_misplaced_line_occupancy_removed": True,
            "all_other_modules_reused": True,
        },
        "retained_and_replaced_rates_cps": {
            "prompt_retained": float(day15_row["prompt_final_cps_noacc_retained"]),
            "delayed_retained": float(day15_row["delayed_final_cps_noacc_retained"]),
            "signal_retained_slant45": float(day15_row["signal_final_cps_noacc_retained"]),
            "legacy_atm511_sidecar_removed": float(day15_row["legacy_sidecar_final_cps_noacc_removed"]),
            "corrected_PARMA511_added": float(day15_row["corrected_parma511_final_cps_noacc"]),
            "old_background": old_background_day15,
            "recomposed_background": new_background_day15,
            "recomposed_minus_old_background": new_background_day15 - old_background_day15,
        },
        "endpoint_rates_cps": {
            "prompt_retained_componentwise_upper95": float(day15_row["prompt_final_upper95_cps_noacc_retained"]),
            "delayed_retained_componentwise_upper95": float(day15_row["delayed_final_upper95_cps_noacc_retained"]),
            "legacy_sidecar_upper95_removed": float(day15_row["legacy_sidecar_final_upper95_cps_noacc_removed"]),
            "corrected_line_endpoint_added": float(day15_row["corrected_parma511_final_upper95_cps_noacc"]),
            "recomposed_background_componentwise_endpoint": float(day15_row["background_componentwise_endpoint_cps_noacc_recomposed"]),
            "corrected_line_endpoint_method": line["w2_upper95_method"],
        },
        "occupancy_and_live_factor": {
            "prompt_hz_retained_before_line_occupancy_dedup": float(day15_row["prompt_event_rate_hz_retained_before_line_occupancy_dedup"]),
            "prompt_gamma_scale": float(day15_row["prompt_scale_gamma"]),
            "prompt_gamma_misplaced_line_hz_removed": float(day15_row["prompt_gamma_misplaced_line_event_rate_hz_removed"]),
            "prompt_hz_after_line_occupancy_dedup": float(day15_row["prompt_event_rate_hz_after_line_occupancy_dedup"]),
            "delayed_hz_retained": float(day15_row["delayed_event_rate_hz_retained"]),
            "legacy_sidecar_hz_removed": float(day15_row["legacy_sidecar_event_rate_hz_removed"]),
            "legacy_sidecar_subtracted_from_prompt_occupancy": False,
            "corrected_line_hz_added": float(day15_row["corrected_parma511_event_rate_hz"]),
            "old_live_factor": float(day15_base["accidental_live_factor"]),
            "pre_fix_recomposition_live_factor_without_prompt_gamma_occupancy_dedup": float(day15_row["accidental_live_factor_pre_fix_no_prompt_gamma_occupancy_dedup"]),
            "recomposed_live_factor": float(day15_row["accidental_live_factor_recomposed"]),
            "line_occupancy_method": line["line_occupancy_method"],
            "dedup_provenance": validated["occupancy_dedup_audit"],
            "formula_validation": occupancy_formula_audit,
        },
        "line_input": line,
        "broad_window_corrected_line": {
            "rate_day15_cps": line["broad_rate_day15_cps"],
            "upper95_day15_cps": line["broad_upper95_day15_cps"],
            "note": "Unavailable from the compact low-stat W2 diagnostic; populated from primary_event_response.csv for a campaign aggregate.",
        },
        "scientific_blockers": blockers,
        "no_rerun_attestation": {
            "cosima_launched": False,
            "transport_launched": False,
            "continuum_rerun": False,
            "other_particle_rerun": False,
            "m_sampling_rerun": False,
            "retained_product_modified": False,
            "m04_modified": False,
        },
    }

    z20 = z_curve[-1]
    z20_conditional = z_conditional_curve[-1]
    prefixed_bug_z20 = prefixed_bug_source / math.sqrt(prefixed_bug_background)
    prefixed_bug_z20_conditional = prefixed_bug_source_lower / math.sqrt(
        prefixed_bug_background_upper
    )
    old_final = mission_rows[-1]
    mission_summary = {
        "schema": "o8-parma511-20d-modular-recomposition-v1",
        "status": status,
        "scope": "W2-only offline mission recomposition; only the atmospheric mono-line module is replaced",
        "time_bins": len(output_rows),
        "elapsed_days": elapsed_s / float(config["mission"]["seconds_per_day"]),
        "reference_flux_ph_cm2_s": reference_flux,
        "metrics_20d": {
            "source_counts": cumulative_source,
            "background_counts": cumulative_background,
            "source_transport_counting_lower_endpoint_counts": cumulative_source_lower,
            "background_componentwise_endpoint_counts": cumulative_background_upper,
            "Z20d": z20,
            "Z20d_componentwise_endpoint_conditional": z20_conditional,
            "flux_3sigma_20d_ph_cm2_s": reference_flux * 3.0 / z20,
            "flux_3sigma_20d_componentwise_endpoint_conditional_ph_cm2_s": reference_flux * 3.0 / z20_conditional,
            "T3_day": time_or_extrapolate(days, z_curve, 3.0),
            "T5_day": time_or_extrapolate(days, z_curve, 5.0),
            "T3_day_componentwise_endpoint_conditional": time_or_extrapolate(days, z_conditional_curve, 3.0),
            "T5_day_componentwise_endpoint_conditional": time_or_extrapolate(days, z_conditional_curve, 5.0),
            "accidental_loss_min": min(1.0 - float(row["accidental_live_factor_recomposed"]) for row in output_rows),
            "accidental_loss_max": max(1.0 - float(row["accidental_live_factor_recomposed"]) for row in output_rows),
        },
        "comparison_to_retained_old_sidecar_fold": {
            "old_source_counts_20d": float(old_final["cumulative_source_counts"]),
            "old_background_counts_20d": float(old_final["cumulative_background_counts"]),
            "old_Z20d": float(old_final["counting_Z"]),
            "old_conditional_Z20d": float(old_final["counting_Z_componentwise_transport_counting_endpoint_conditional"]),
            "delta_source_counts_20d_from_live_factor_only": cumulative_source - float(old_final["cumulative_source_counts"]),
            "delta_background_counts_20d": cumulative_background - float(old_final["cumulative_background_counts"]),
            "delta_Z20d": z20 - float(old_final["counting_Z"]),
        },
        "comparison_to_pre_fix_recomposition_without_prompt_gamma_occupancy_dedup": {
            "pre_fix_source_counts_20d": prefixed_bug_source,
            "pre_fix_background_counts_20d": prefixed_bug_background,
            "pre_fix_source_lower_endpoint_counts_20d": prefixed_bug_source_lower,
            "pre_fix_background_upper_endpoint_counts_20d": prefixed_bug_background_upper,
            "pre_fix_Z20d": prefixed_bug_z20,
            "pre_fix_Z20d_componentwise_endpoint_conditional": prefixed_bug_z20_conditional,
            "corrected_minus_pre_fix_source_counts_20d": cumulative_source - prefixed_bug_source,
            "corrected_minus_pre_fix_background_counts_20d": cumulative_background - prefixed_bug_background,
            "corrected_minus_pre_fix_Z20d": z20 - prefixed_bug_z20,
        },
        "formula_audit": identity,
        "prompt_gamma_line_occupancy_dedup_audit": validated["occupancy_dedup_audit"],
        "recomposed_occupancy_formula_validation": occupancy_formula_audit,
        "line_flux_time_policy": config["parma_line_fold"]["time_policy"],
        "trajectory_Rc_policy": config["parma_line_fold"]["trajectory_Rc_policy"],
        "frozen_modules": config["frozen_modules"],
        "line_input_grade": line["response_grade"],
        "scientific_blockers": blockers,
        "claim_boundary": "These values are diagnostic/conditional and are not paper authority while any listed blocker remains.",
    }
    return output_rows, flux_rows, day15_summary, mission_summary


def prepare_output_dir(output_dir: Path, *, force: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = [output_dir / name for name in OUTPUT_NAMES if (output_dir / name).exists()]
    if existing and not force:
        raise RecompositionError("refusing to overwrite existing recomposition outputs without --force: " + ", ".join(rel(path) for path in existing))


def result_markdown(day15: dict[str, Any], mission: dict[str, Any]) -> str:
    rates = day15["retained_and_replaced_rates_cps"]
    occupancy = day15["occupancy_and_live_factor"]
    metrics = mission["metrics_20d"]
    comparison = mission[
        "comparison_to_pre_fix_recomposition_without_prompt_gamma_occupancy_dedup"
    ]
    line = day15["line_input"]
    return f"""# Atmospheric-511 modular recomposition result

Status: `{day15['status']}`

This is an offline W2 recomposition. No Cosima/transport, continuum, other-particle,
M-sampling, geometry, detector-response, selection, or signal run was launched.

Day 15 keeps prompt `{rates['prompt_retained']:.12g}` cps, delayed
`{rates['delayed_retained']:.12g}` cps, and the 45-degree slant signal
`{rates['signal_retained_slant45']:.12g}` cps. It removes the legacy sidecar
`{rates['legacy_atm511_sidecar_removed']:.12g}` cps and adds the corrected PARMA
line `{rates['corrected_PARMA511_added']:.12g}` cps. The recomposed background is
`{rates['recomposed_background']:.12g}` cps.

The selected-rate de-dup delta remains exactly zero in W2 and Broad480-550.
Separately, the active-only/TES-zero misplaced prompt-gamma line contributes to
accidental occupancy, so day 15 removes
`{occupancy['prompt_gamma_misplaced_line_hz_removed']:.12g}` Hz from retained
prompt occupancy using `prompt_scale_gamma`. Prompt occupancy changes from
`{occupancy['prompt_hz_retained_before_line_occupancy_dedup']:.12g}` to
`{occupancy['prompt_hz_after_line_occupancy_dedup']:.12g}` Hz, and the live factor
changes from the pre-fix `{occupancy['pre_fix_recomposition_live_factor_without_prompt_gamma_occupancy_dedup']:.12g}`
to `{occupancy['recomposed_live_factor']:.12g}`. The legacy sidecar occupancy is
omitted separately once; it is not subtracted from the prompt term.

The 20-day central fold gives S=`{metrics['source_counts']:.12g}`,
B=`{metrics['background_counts']:.12g}`, and Z=`{metrics['Z20d']:.12g}`.
Relative to the pre-fix recomposition, the occupancy correction changes these by
`{comparison['corrected_minus_pre_fix_source_counts_20d']:.12g}` source counts,
`{comparison['corrected_minus_pre_fix_background_counts_20d']:.12g}` background
counts, and `{comparison['corrected_minus_pre_fix_Z20d']:.12g}` in Z.
The supplied line-response grade is `{line['response_grade']}`.

These numbers are not publication authority. In particular, the legacy prompt-gamma
axis has the factor-1000 energy-abscissa blocker, and the frozen selection's
`ACTIVE_SHIELD` substring includes passive `ActiveShield_S3C_BGO_Kapton_*` scorers.
Both historical implementations are preserved here; neither is repaired or rerun.
"""


def write_outputs(
    config_path: Path,
    output_dir: Path,
    validated: dict[str, Any],
    flux_audit: dict[str, Any],
    line: dict[str, Any],
    identity: dict[str, Any],
    output_rows: list[dict[str, Any]],
    flux_rows: list[dict[str, Any]],
    day15: dict[str, Any],
    mission: dict[str, Any],
    *,
    force: bool,
) -> dict[str, Any]:
    prepare_output_dir(output_dir, force=force)
    flux_path = output_dir / "parma511_line_flux_by_time.csv"
    timeline_path = output_dir / "w2_modular_recomposition_by_time.csv"
    day15_path = output_dir / "day15_modular_recomposition.json"
    mission_path = output_dir / "mission_20d_modular_recomposition.json"
    result_path = output_dir / "RECOMPOSITION_RESULT.md"
    manifest_path = output_dir / "recomposition_manifest.json"
    atomic_write_text(flux_path, csv_text(flux_rows, list(flux_rows[0])))
    atomic_write_text(timeline_path, csv_text(output_rows, list(output_rows[0])))
    atomic_write_json(day15_path, day15)
    atomic_write_json(mission_path, mission)
    atomic_write_text(result_path, result_markdown(day15, mission))
    artifacts = {}
    for path in (flux_path, timeline_path, day15_path, mission_path, result_path):
        artifacts[path.name] = {"path": rel(path), "sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "schema": "o8-parma511-modular-recomposition-manifest-v1",
        "status": day15["status"],
        "generated_at_utc": now_utc(),
        "scope": "offline replacement of only the atmospheric annihilation mono-line module",
        "script": {"path": rel(Path(__file__)), "sha256": sha256(Path(__file__))},
        "config": {"path": rel(config_path), "sha256": sha256(config_path)},
        "input_authorities": validated["authority_hashes"],
        "protected_files_after_run": validated["protected_hashes"],
        "line_input": line,
        "parma_flux_evaluation": flux_audit,
        "formula_identity_self_test": identity,
        "prompt_gamma_line_occupancy_dedup_provenance": validated["occupancy_dedup_audit"],
        "recomposed_occupancy_formula_validation": mission[
            "recomposed_occupancy_formula_validation"
        ],
        "invariants": {
            "time_bins_81": len(output_rows) == 81,
            "elapsed_days_20": close(float(mission["elapsed_days"]), 20.0),
            "day15_index_60": int(day15["day15_index_zero_based"]) == 60,
            "legacy_sidecar_removed": day15["composition"]["legacy_sidecar_removed"] is True,
            "legacy_sidecar_occupancy_omitted_separately_once": mission[
                "recomposed_occupancy_formula_validation"
            ]["legacy_sidecar_occupancy_omitted_separately_once"] is True,
            "legacy_sidecar_not_subtracted_from_prompt_occupancy": day15["composition"][
                "legacy_sidecar_subtracted_from_prompt_occupancy"
            ] is False,
            "day15_prompt_gamma_line_occupancy_removal_matches_audit": close(
                float(day15["occupancy_and_live_factor"]["prompt_gamma_misplaced_line_hz_removed"]),
                float(validated["occupancy_dedup_audit"]["removed_event_rate_day15_hz"]),
            ),
            "prompt_occupancy_nonnegative_after_dedup_all_81_bins": all(
                float(row["prompt_event_rate_hz_after_line_occupancy_dedup"]) >= 0.0
                for row in output_rows
            ),
            "total_occupancy_nonnegative_all_81_bins": all(
                float(row["coincidence_occupancy_rate_hz_recomposed"]) >= 0.0
                for row in output_rows
            ),
            "recomposed_occupancy_formula_passes_all_81_bins": mission[
                "recomposed_occupancy_formula_validation"
            ]["status"] == "PASS_81BIN_PROMPT_GAMMA_LINE_OCCUPANCY_DEDUP_FORMULA",
            "w2_prompt_gamma_line_dedup_delta_zero": day15["composition"]["prompt_gamma_line_dedup_delta_W2_cps"] == 0.0,
            "broad_prompt_gamma_line_dedup_delta_zero": day15["composition"]["prompt_gamma_line_dedup_delta_broad_480_550_cps"] == 0.0,
            "all_other_modules_reused": day15["composition"]["all_other_modules_reused"] is True,
        },
        "execution_attestation": day15["no_rerun_attestation"],
        "outputs": artifacts,
    }
    require(all(manifest["invariants"].values()), "one or more output invariants failed")
    atomic_write_json(manifest_path, manifest)
    return manifest


def highstat_aggregate_schema_self_test(config: dict[str, Any], day15_base: dict[str, str]) -> dict[str, Any]:
    """Exercise the future completed-campaign input path with an ephemeral fixture."""
    with tempfile.TemporaryDirectory(prefix="o8_parma511_recomposition_schema_") as tmp_name:
        tmp = Path(tmp_name)
        response_dir = tmp / "response"
        response_dir.mkdir(parents=True)
        provenance_path = tmp / "provenance.json"
        te_s = 100_000.0
        atomic_write_json(
            provenance_path,
            {
                "status": "PASS_STREAM_PARSE_COMPLETE",
                "sim_footer": {"TE_s": te_s},
                "counts": {"tes_or_active_events": 12_000},
            },
        )
        event_rows: list[dict[str, Any]] = []
        for event_id in range(400):
            event_rows.append(
                {
                    "event_id": event_id,
                    "dir_z": 0.0,
                    "measured_total_keV": 511.0,
                    "measured_multiplicity": 1,
                    "active_total_keV": 0.0,
                    "raw_w2": True,
                    "active_w2": True,
                    "final_w2": True,
                    "topology_class": "single",
                }
            )
        event_rows.append(
            {
                "event_id": 400,
                "dir_z": 0.0,
                "measured_total_keV": 500.0,
                "measured_multiplicity": 1,
                "active_total_keV": 0.0,
                "raw_w2": False,
                "active_w2": False,
                "final_w2": False,
                "topology_class": "keep",
            }
        )
        primary_path = response_dir / "primary_event_response.csv"
        atomic_write_text(primary_path, csv_text(event_rows, list(event_rows[0])))
        response_path = response_dir / "response_64seed_summary.json"
        response = {
            "schema": "o8-parma511-line-step05-response-v1",
            "status": "DIAGNOSTIC_ONLY_LINE_MODULE_RESPONSE_NOT_MANUSCRIPT_PASS",
            "proposal": "parma80",
            "input_parse": {"path": str(provenance_path), "sha256": sha256(provenance_path)},
            "detector_response": {
                "step05_sha256": config["authorities"]["frozen_step05_selection"]["sha256"],
                "active_veto_predicate_blocker": "Synthetic fixture preserves the frozen ACTIVE_SHIELD match that includes passive Kapton wrappers.",
            },
            "primary_420eV": {
                "w2_frozen_step05_pass_events": 400,
                "paired_reweight": {
                    "80": {
                        "selected_events": 400,
                        "importance_weighted_rate_cps": 0.004,
                        "mc_stat_sigma_cps": 0.0002,
                        "importance_effective_sample_size": 400.0,
                    }
                },
            },
            "primary_detector_rate_gate": {
                "passes_detector_rate_gate": True,
                "status": "PASS_PARMA511_LINE_MODULE_RATE_GATE",
            },
            "artifacts": {
                str(primary_path): {"sha256": sha256(primary_path), "bytes": primary_path.stat().st_size}
            },
        }
        atomic_write_json(response_path, response)
        receipt_path = tmp / "aggregate_receipt.json"
        atomic_write_json(
            receipt_path,
            {
                "schema": "o8-parma511-line-campaign-aggregate-v1",
                "status": "CAMPAIGN_COMPACT_AGGREGATE_COMPLETE_DIAGNOSTIC_ONLY",
                "included_batch_indices": [0, 1],
                "incomplete_batch_indices": [],
                "allow_partial": False,
                "response": {
                    "summary": str(response_path),
                    "summary_sha256": sha256(response_path),
                    "primary_gate": response["primary_detector_rate_gate"],
                },
            },
        )
        parsed = parse_line_input(config, receipt_path, day15_base)
        checks = {
            "recognized_complete_aggregate": parsed["input_kind"] == "final_line_campaign_aggregate",
            "final_input_gate_passes": parsed["passes_final_input_gate"] is True,
            "w2_rate_is_count_over_TE": close(float(parsed["w2_rate_day15_cps"]), 0.004),
            "exact_occupancy_is_tes_or_active_over_TE": close(float(parsed["line_occupancy_day15_hz"]), 0.12),
            "broad_selection_count": int(parsed["broad_selected_events"]) == 401,
            "garwood_upper_exceeds_central": float(parsed["w2_upper95_day15_cps"]) > float(parsed["w2_rate_day15_cps"]),
            "temporary_fixture_outside_retained_products": True,
        }
        require(all(checks.values()), f"high-stat aggregate schema self-test failed: {checks}")
        return {
            "status": "PASS_FINAL_CAMPAIGN_AGGREGATE_SCHEMA_SELF_TEST",
            "checks": checks,
            "temporary_fixture_removed_on_exit": True,
        }


def run_self_test(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    validate_scope_contract(config)
    validated = load_and_validate_authorities(config)
    identity = identity_regression(config, validated["mission_rows"])
    fluxes, flux_audit = evaluate_line_fluxes(config, validated["trajectory_rows"], validated["day15_index"])
    toy_days = [1.0, 2.0, 3.0]
    toy_z = [1.0, 2.0, 4.0]
    require_close(time_or_extrapolate(toy_days, toy_z, 3.0), 2.5, "crossing interpolation self-test")
    require_close(time_or_extrapolate([1.0, 2.0], [0.5, 1.0], 2.0), 8.0, "sqrt-time extrapolation self-test")
    aggregate_schema_test = highstat_aggregate_schema_self_test(
        config, validated["mission_rows"][validated["day15_index"]]
    )
    diagnostic_input = authority_path(config, "default_diagnostic_line_input")
    diagnostic_line = parse_line_input(
        config,
        diagnostic_input,
        validated["mission_rows"][validated["day15_index"]],
    )
    diagnostic_rows, _, diagnostic_day15, diagnostic_mission = recompose(
        config, validated, fluxes, diagnostic_line, identity
    )
    occupancy_formula = diagnostic_mission["recomposed_occupancy_formula_validation"]
    occupancy_checks = {
        "checked_all_81_bins": int(occupancy_formula["checked_bins"]) == 81,
        "formula_status_passes": occupancy_formula["status"]
        == "PASS_81BIN_PROMPT_GAMMA_LINE_OCCUPANCY_DEDUP_FORMULA",
        "day15_removed_rate_matches_dedup_audit": close(
            float(occupancy_formula["day15_removed_prompt_gamma_line_occupancy_hz"]),
            float(validated["occupancy_dedup_audit"]["removed_event_rate_day15_hz"]),
        ),
        "prompt_nonnegative_all_bins": all(
            float(row["prompt_event_rate_hz_after_line_occupancy_dedup"]) >= 0.0
            for row in diagnostic_rows
        ),
        "total_occupancy_nonnegative_all_bins": all(
            float(row["coincidence_occupancy_rate_hz_recomposed"]) >= 0.0
            for row in diagnostic_rows
        ),
        "legacy_sidecar_omitted_separately_once": occupancy_formula[
            "legacy_sidecar_occupancy_omitted_separately_once"
        ] is True,
        "legacy_sidecar_not_subtracted_from_prompt": occupancy_formula[
            "legacy_sidecar_subtracted_from_prompt_occupancy"
        ] is False,
        "w2_selected_rate_delta_stays_zero": diagnostic_day15["composition"][
            "prompt_gamma_line_dedup_delta_W2_cps"
        ] == 0.0,
        "broad_selected_rate_delta_stays_zero": diagnostic_day15["composition"][
            "prompt_gamma_line_dedup_delta_broad_480_550_cps"
        ] == 0.0,
    }
    require(
        all(occupancy_checks.values()),
        f"prompt-gamma occupancy recomposition self-test failed: {occupancy_checks}",
    )
    return {
        "schema": "o8-parma511-modular-recomposition-self-test-v1",
        "status": "PASS_OFFLINE_MODULAR_RECOMPOSITION_SELF_TEST",
        "tested_at_utc": now_utc(),
        "config": {"path": rel(config_path), "sha256": sha256(config_path)},
        "authority_hashes": validated["authority_hashes"],
        "protected_hashes": validated["protected_hashes"],
        "retained_formula_identity": identity,
        "prompt_gamma_line_occupancy_semantics": validated["occupancy_dedup_audit"],
        "recomposed_81bin_occupancy_formula": {
            "checks": occupancy_checks,
            "validation": occupancy_formula,
        },
        "parma_flux_evaluation": flux_audit,
        "trajectory": {
            "time_bins": len(validated["trajectory_rows"]),
            "day15_index": validated["day15_index"],
            "unique_depths": len({row["depth_g_cm2"] for row in validated["trajectory_rows"]}),
            "flux_min_ph_cm2_s": min(fluxes),
            "flux_max_ph_cm2_s": max(fluxes),
        },
        "analytic_checks": {
            "linear_crossing_day": 2.5,
            "sqrt_time_extrapolation_day": 8.0,
        },
        "final_campaign_input_schema": aggregate_schema_test,
        "execution_attestation": {
            "cosima_launched": False,
            "transport_launched": False,
            "only_hash_locked_parma_line_driver_called": True,
        },
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    value.add_argument("--line-input", type=Path, help="diagnostic JSON, line response summary, or final campaign aggregate receipt")
    value.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    value.add_argument("--force", action="store_true", help="replace only this script's named files inside --output-dir")
    value.add_argument("--self-test", action="store_true", help="validate authorities/formulas and exit without mission-output generation")
    value.add_argument("--self-test-output", type=Path, help="optional JSON path for the self-test report")
    return value


def main() -> None:
    args = parser().parse_args()
    config_path = args.config.resolve()
    config = read_json(config_path)
    require(config.get("schema") == "o8-parma511-modular-recomposition-config-v1", "config schema changed")
    if args.self_test:
        report = run_self_test(config_path, config)
        if args.self_test_output:
            target = args.self_test_output.resolve()
            if target.exists() and not args.force:
                raise RecompositionError(f"refusing to overwrite self-test output without --force: {rel(target)}")
            atomic_write_json(target, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    validate_scope_contract(config)
    validated = load_and_validate_authorities(config)
    identity = identity_regression(config, validated["mission_rows"])
    fluxes, flux_audit = evaluate_line_fluxes(config, validated["trajectory_rows"], validated["day15_index"])
    line_input = args.line_input.resolve() if args.line_input else authority_path(config, "default_diagnostic_line_input")
    day15_base = validated["mission_rows"][validated["day15_index"]]
    line = parse_line_input(config, line_input, day15_base)
    output_rows, flux_rows, day15, mission = recompose(config, validated, fluxes, line, identity)
    output_dir = args.output_dir.resolve()
    manifest = write_outputs(
        config_path,
        output_dir,
        validated,
        flux_audit,
        line,
        identity,
        output_rows,
        flux_rows,
        day15,
        mission,
        force=args.force,
    )
    print(json.dumps({"status": manifest["status"], "output_dir": rel(output_dir), "outputs": manifest["outputs"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except RecompositionError as exc:
        raise SystemExit(f"ERROR: {exc}")
