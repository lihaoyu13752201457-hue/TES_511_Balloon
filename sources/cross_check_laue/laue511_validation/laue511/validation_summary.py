from __future__ import annotations

import csv
import json
import math
from pathlib import Path


def build_validation_manifest(root: str | Path) -> dict[str, object]:
    root = Path(root)
    reports = root / "reports"
    benchmarks = root / "benchmarks"

    historical = _load_json(reports / "geant4_current_crosscheck/metrics.json")
    rebuilt = _load_json(reports / "geant4_rebuilt_5k_crosscheck/metrics.json")
    focal = _load_json(reports / "focal_convention_audit/metrics.json")
    external_handoff = _load_json(reports / "external_lens_handoff/metrics.json")
    full_lens = _load_json(reports / "full_lens_observables/metrics.json")
    python_lens = _load_json(reports / "python_full_lens_reference/metrics.json")
    bridge_diff = _load_json(reports / "cosima_bridge_current_audit/metrics.json")
    bridge_trans = _load_json(reports / "cosima_bridge_transmitted_current_audit/metrics.json")
    pytte = _load_json(benchmarks / "xrt_pytte/summary.json")
    kohnle = _load_json(benchmarks / "kohnle1998/summary.json")
    table_lens = _table_lens_closure_check(benchmarks / "opticsim_table_lens/summary.json")
    crystalpy = _optional_external_curve_check(
        benchmarks / "crystalpy/summary.json",
        "benchmarks/crystalpy/summary.json",
    )
    xop_crystal = _optional_external_curve_check(
        benchmarks / "xop_crystal/summary.json",
        "benchmarks/xop_crystal/summary.json",
    )
    external_lens_import_ready = _external_lens_import_ready_check(root)
    external_lens_request_ready = _external_lens_request_ready_check(root)
    external_lens_curve = _external_lens_curve_check(
        benchmarks / "reference_outputs/external_lens_observables/summary.json",
        benchmarks / "reference_outputs/EXTERNAL_SOURCE_STATUS.md",
    )
    bfull_offaxis = _bfull_offaxis_scan_check(reports / "bfull_offaxis_scan/summary.json")
    bfull_single_tile_xop = _bfull_single_tile_xop_scan_check(
        reports / "bfull_single_tile_xop_scan/summary.json"
    )
    bfull_rocking_curve_map = _bfull_rocking_curve_map_status_check(
        reports / "bfull_rocking_curve_map_status/summary.json"
    )
    bfull_full_lens_xop_map = _bfull_full_lens_xop_map_scan_check(
        reports / "bfull_full_lens_xop_map_scan/summary.json"
    )

    checks = {
        "historical_probability_kernel": _probability_check(historical, require_vector=False),
        "rebuilt_probability_kernel_and_vectors": _probability_check(rebuilt, require_vector=True),
        "focal_convention": {
            "ok": focal["max_abs_p_diff_delta"] <= 1.0e-3 and focal["max_abs_delta_theta_entry_arcsec"] <= 1.0,
            "max_abs_p_diff_delta": focal["max_abs_p_diff_delta"],
            "max_abs_delta_theta_entry_arcsec": focal["max_abs_delta_theta_entry_arcsec"],
        },
        "external_lens_handoff": _external_lens_handoff_check(external_handoff),
        "full_lens_observables": _full_lens_observables_check(full_lens),
        "python_full_lens_reference": _python_full_lens_reference_check(python_lens),
        "cosima_bridge_diffract": _bridge_check(bridge_diff),
        "cosima_bridge_transmit": _bridge_check(bridge_trans),
        "pytte_check": {"ok": bool(pytte["ok"]), "n_cases": pytte["n_cases"]},
        "kohnle1998_check": {
            "ok": bool(kohnle["ok"]),
            "n_cases": kohnle["n_cases"],
            "endpoint_max_abs_error": kohnle["endpoint_max_abs_error"],
        },
        "opticsim_table_lens_closure": table_lens,
        "crystalpy_curve": crystalpy,
        "xop_crystal_curve": xop_crystal,
        "external_lens_import_ready": external_lens_import_ready,
        "external_lens_request_ready": external_lens_request_ready,
        "external_lens_curve": external_lens_curve,
        "bfull_offaxis_scan": bfull_offaxis,
        "bfull_single_tile_xop_scan": bfull_single_tile_xop,
        "bfull_rocking_curve_map_status": bfull_rocking_curve_map,
        "bfull_full_lens_xop_map_scan": bfull_full_lens_xop_map,
    }
    required_now = [
        name
        for name in checks
        if name
        not in {
            "external_lens_curve",
            "bfull_offaxis_scan",
            "bfull_single_tile_xop_scan",
            "bfull_rocking_curve_map_status",
            "bfull_full_lens_xop_map_scan",
        }
    ]
    required_ok = all(checks[name]["ok"] for name in required_now)
    external_status = str(external_lens_curve["status"])
    bfull_status = str(bfull_offaxis["status"])
    bfull_single_status = str(bfull_single_tile_xop["status"])
    bfull_map_status = str(bfull_rocking_curve_map["status"])
    bfull_full_lens_map_status = str(bfull_full_lens_xop_map["status"])
    if (
        not required_ok
        or external_status == "needs_attention"
        or bfull_status == "needs_attention"
        or bfull_single_status == "needs_attention"
        or bfull_map_status == "needs_attention"
        or bfull_full_lens_map_status == "needs_attention"
    ):
        status = "needs_attention"
    elif external_lens_curve["ok"]:
        status = "crosscheck_pass_external_lens_observables_imported"
    else:
        status = "crosscheck_pass_external_lens_curve_pending"
    return {
        "status": status,
        "production_validation_ready": False,
        "required_now": required_now,
        "checks": checks,
        "artifacts": {
            "historical_geant4": "reports/geant4_current_crosscheck",
            "rebuilt_geant4_smoke": "reports/geant4_rebuilt_5k_crosscheck",
            "focal_convention": "reports/focal_convention_audit",
            "external_lens_handoff": "reports/external_lens_handoff",
            "heart_adapter_feasibility": "reports/heart_adapter_feasibility",
            "bfull_offaxis_scan": "reports/bfull_offaxis_scan",
            "bfull_single_tile_xop_scan": "reports/bfull_single_tile_xop_scan",
            "bfull_rocking_curve_map_status": "reports/bfull_rocking_curve_map_status",
            "bfull_full_lens_xop_map_scan": "reports/bfull_full_lens_xop_map_scan",
            "full_lens_observables": "reports/full_lens_observables",
            "python_full_lens_reference": "reports/python_full_lens_reference",
            "cosima_bridge_diffract": "reports/cosima_bridge_current_audit",
            "cosima_bridge_transmit": "reports/cosima_bridge_transmitted_current_audit",
            "pytte": "benchmarks/xrt_pytte",
            "kohnle1998": "benchmarks/kohnle1998",
            "opticsim_table_lens": "benchmarks/opticsim_table_lens",
            "crystalpy": "benchmarks/crystalpy",
            "xop_crystal": "benchmarks/xop_crystal",
            "external_lens_schema": "benchmarks/reference_outputs/EXTERNAL_LENS_OBSERVABLES_SCHEMA.md",
            "external_lens_hits_schema": "benchmarks/reference_outputs/EXTERNAL_LENS_HITS_SCHEMA.md",
            "external_lens_request": "benchmarks/reference_outputs/external_lens_oracle_request.json",
            "heart_adapter_request": "benchmarks/reference_outputs/heart_lens_adapter_request.json",
            "heart_independent_plane_normal_patch": "benchmarks/reference_outputs/heart_independent_plane_normal.patch",
            "heart_patched_full_lens_hdf5": "benchmarks/reference_outputs/heart_patched_full_lens.h5",
            "heart_patched_full_lens_run_summary": "benchmarks/reference_outputs/heart_patched_full_lens_run_summary.json",
            "heart_patched_full_lens_guan_direction_hdf5": "benchmarks/reference_outputs/heart_patched_full_lens_guan_direction.h5",
            "heart_patched_full_lens_guan_direction_run_summary": "benchmarks/reference_outputs/heart_patched_full_lens_guan_direction_run_summary.json",
            "external_lens_observables": "benchmarks/reference_outputs/external_lens_observables",
            "external_lens_tile_table": "benchmarks/reference_outputs/external_lens_oracle_tiles.csv",
            "external_source_status": "benchmarks/reference_outputs/EXTERNAL_SOURCE_STATUS.md",
            "lll_status": "benchmarks/reference_outputs/LLL_NOT_AVAILABLE.md",
        },
    }


def write_validation_summary(path: str | Path, manifest: dict[str, object]) -> None:
    path = Path(path)
    lines = [
        "# Laue 511 Cross-Check Summary",
        "",
        f"Status: `{manifest['status']}`",
        f"Production validation ready: `{manifest['production_validation_ready']}`",
        "",
        "## Checks",
        "",
        "| check | ok | key evidence |",
        "|---|---:|---|",
    ]
    checks = manifest["checks"]
    for name, check in checks.items():
        lines.append(f"| `{name}` | `{check['ok']}` | {_evidence_text(name, check)} |")
    if checks["external_lens_curve"]["ok"]:
        interpretation = [
            "The current package passes the internal Geant4/Python kernel checks, focal convention audit, external lens handoff audit, full-lens observable audit, Python-only full-lens reference check, bridge provenance audit, a five-ring opticsim table-vs-online closure check, imported single-crystal/XOP-CRYSTAL checks, external full-lens import/request readiness checks, and an imported HEART-derived full-lens detector-image check.",
            "The production validation flag remains false because this repository is a cross-check package; the imported HEART route validates the current package observables but does not turn this directory into the final production validation record.",
        ]
    else:
        interpretation = [
            "The current package passes the internal Geant4/Python kernel checks, focal convention audit, external lens handoff audit, full-lens observable audit, Python-only full-lens reference check, bridge provenance audit, a five-ring opticsim table-vs-online closure check, imported single-crystal/XOP-CRYSTAL checks, and the external full-lens import/request readiness checks.",
            "A direct external full-lens oracle such as LLL or HEART remains pending, so this is a cross-check package rather than a final production validation record.",
        ]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            *interpretation,
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _probability_check(metrics: dict[str, object], require_vector: bool) -> dict[str, object]:
    max_prob_delta = max(metrics["probability_max_abs_delta"].values())
    max_branch_z = max(abs(value) for row in metrics["ring_metrics"] for value in row["branch_z"].values())
    vector_ok = None
    if require_vector:
        vector = metrics["vector_diagnostics"]
        vector_ok = (
            bool(vector["available"])
            and vector["n_diffracted_with_model"] == vector["n_diffracted"]
            and vector["max_angle_code_vs_recorded_reflect_rad"] <= 1.0e-6
        )
    return {
        "ok": max_prob_delta <= 1.0e-8
        and max_branch_z <= 3.0
        and bool(metrics["phase_space_validation"]["ok"])
        and bool(metrics["transmitted_space_validation"]["ok"])
        and (vector_ok is not False),
        "rows_checked": metrics["n_history_rows_checked"],
        "max_probability_delta": max_prob_delta,
        "max_branch_z": max_branch_z,
        "vector_required": require_vector,
        "vector_ok": vector_ok,
    }


def _bridge_check(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "ok": bool(metrics["ok"]),
        "n_rows": metrics["n_rows"],
        "history_joined_rows": metrics["history_joined_rows"],
        "missing_ring_id_rows": metrics["missing_ring_id_rows"],
        "missing_tile_id_rows": metrics["missing_tile_id_rows"],
    }


def _external_lens_handoff_check(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "ok": bool(metrics["ok"]),
        "import_ok": bool(metrics["import_ok"]),
        "work_dir_removed": bool(metrics["work_dir_removed"]),
        "agreement_checks": metrics["agreement_checks"],
        "n_rows": metrics["n_rows"],
    }


def _full_lens_observables_check(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "ok": bool(metrics["ok"]),
        "max_phase_intersection_delta_mm": metrics["max_phase_intersection_delta_mm"],
        "spot_d90_cm": metrics["spot_d90_cm"],
        "expected_diffracted_area_cm2": metrics["expected_diffracted_area_cm2"],
        "observed_diffracted_area_cm2": metrics["observed_diffracted_area_cm2"],
        "effective_area_delta_cm2": metrics["effective_area_delta_cm2"],
    }


def _python_full_lens_reference_check(metrics: dict[str, object]) -> dict[str, object]:
    return {
        "ok": bool(metrics["ok"]),
        "diffracted_area_reference_cm2": metrics["diffracted_area_reference_cm2"],
        "observed_diffracted_area_cm2": metrics["observed_diffracted_area_cm2"],
        "diffracted_area_delta_cm2": metrics["diffracted_area_delta_cm2"],
        "max_abs_branch_z": metrics["max_abs_branch_z"],
    }


def _optional_external_curve_check(path: Path, evidence: str) -> dict[str, object]:
    if not path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": evidence,
        }
    summary = _load_json(path)
    return {
        "ok": bool(summary["ok"]),
        "status": "imported" if summary["ok"] else "needs_attention",
        "evidence": evidence,
        "n_rows": summary["n_rows"],
        "peak_reflectivity": summary.get("peak_reflectivity"),
        "max_flux_conservation_residual": summary.get("max_flux_conservation_residual"),
    }


def _table_lens_closure_check(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": "benchmarks/opticsim_table_lens/summary.json",
        }
    summary = _load_json(path)
    return {
        "ok": bool(summary["ok"]),
        "status": "imported" if summary["ok"] else "needs_attention",
        "evidence": "benchmarks/opticsim_table_lens/summary.json",
        "delta_diffraction_fraction": summary["delta_diffraction_fraction"],
        "delta_spot_d90_cm": summary["delta_spot_d90_cm"],
        "max_abs_delta_mean_p_diff_by_ring": summary["max_abs_delta_mean_p_diff_by_ring"],
        "max_abs_delta_sampled_diffraction_fraction_by_ring": summary[
            "max_abs_delta_sampled_diffraction_fraction_by_ring"
        ],
    }


def _external_lens_curve_check(summary_path: Path, status_evidence: Path) -> dict[str, object]:
    if summary_path.exists():
        summary = _load_json(summary_path)
        lens = summary.get("lens_metrics", {})
        comparison = summary.get("comparison", {})
        return {
            "ok": bool(summary["ok"]),
            "status": "imported" if summary["ok"] else "needs_attention",
            "evidence": _workspace_relative(summary_path),
            "n_rows": summary.get("n_rows"),
            "source_tools": summary.get("source_tools", []),
            "source_versions": summary.get("source_versions", []),
            "diffracted_area_cm2": lens.get("diffracted_area_cm2"),
            "spot_d90_cm": lens.get("spot_d90_cm"),
            "diffracted_area_minus_current_observed_cm2": comparison.get(
                "diffracted_area_minus_current_observed_cm2"
            ),
            "spot_d90_minus_current_observed_cm": comparison.get("spot_d90_minus_current_observed_cm"),
        }
    return {
        "ok": False,
        "status": "pending",
        "evidence": _workspace_relative(status_evidence),
    }


def _bfull_offaxis_scan_check(summary_path: Path) -> dict[str, object]:
    if not summary_path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": "reports/bfull_offaxis_scan/summary.json",
        }
    summary = _load_json(summary_path)
    em_category = bool(summary.get("all_registered_in_geant4_em_category", False))
    g4vemprocess = bool(summary.get("all_process_base_g4vemprocess", False))
    ok = bool(summary["ok"]) and em_category and g4vemprocess
    return {
        "ok": ok,
        "status": "imported" if ok else "needs_attention",
        "evidence": "reports/bfull_offaxis_scan/summary.json",
        "n_per_offset": summary["n_per_offset"],
        "observed_peak_to_min_ratio": summary["observed_peak_to_min_ratio"],
        "ring2_observed_peak_to_min_ratio": summary["ring2_observed_peak_to_min_ratio"],
        "ring2_xop_peak_to_min_ratio": summary["ring2_xop_peak_to_min_ratio"],
        "all_registered_in_geant4_em_category": em_category,
        "all_process_base_g4vemprocess": g4vemprocess,
        "all_transmitted_space_rows_match_summary": summary.get("all_transmitted_space_rows_match_summary", False),
    }


def _bfull_single_tile_xop_scan_check(summary_path: Path) -> dict[str, object]:
    if not summary_path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": "reports/bfull_single_tile_xop_scan/summary.json",
        }
    summary = _load_json(summary_path)
    em_category = bool(summary.get("all_registered_in_geant4_em_category", False))
    g4vemprocess = bool(summary.get("all_process_base_g4vemprocess", False))
    ok = bool(summary["ok"]) and em_category and g4vemprocess
    return {
        "ok": ok,
        "status": "imported" if ok else "needs_attention",
        "evidence": "reports/bfull_single_tile_xop_scan/summary.json",
        "n_per_offset": summary["n_per_offset"],
        "ring_id": summary["ring_id"],
        "tile_id": summary["tile_id"],
        "xop_peak_reflectivity_in_scan": summary["xop_peak_reflectivity_in_scan"],
        "observed_peak_interaction_fraction": summary["observed_peak_interaction_fraction"],
        "max_recorded_p_reflect_minus_xop": summary["max_recorded_p_reflect_minus_xop"],
        "all_registered_in_geant4_em_category": em_category,
        "all_process_base_g4vemprocess": g4vemprocess,
        "all_transmitted_space_rows_match_summary": summary.get("all_transmitted_space_rows_match_summary", False),
    }


def _bfull_rocking_curve_map_status_check(summary_path: Path) -> dict[str, object]:
    if not summary_path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": "reports/bfull_rocking_curve_map_status/summary.json",
        }
    summary = _load_json(summary_path)
    status = str(summary.get("status", "needs_attention"))
    return {
        "ok": bool(summary.get("all_rings_covered")),
        "status": status,
        "evidence": "reports/bfull_rocking_curve_map_status/summary.json",
        "covered_ring_ids": summary.get("covered_ring_ids", []),
        "missing_ring_ids": summary.get("missing_ring_ids", []),
        "map_csv": summary.get("map_csv", ""),
        "coverage_csv": summary.get("coverage_csv", ""),
    }


def _bfull_full_lens_xop_map_scan_check(summary_path: Path) -> dict[str, object]:
    if not summary_path.exists():
        return {
            "ok": False,
            "status": "pending",
            "evidence": "reports/bfull_full_lens_xop_map_scan/summary.json",
        }
    summary = _load_json(summary_path)
    em_category = bool(summary.get("all_registered_in_geant4_em_category", False))
    g4vemprocess = bool(summary.get("all_process_base_g4vemprocess", False))
    ok = bool(summary["ok"]) and em_category and g4vemprocess
    return {
        "ok": ok,
        "status": "imported" if ok else "needs_attention",
        "evidence": "reports/bfull_full_lens_xop_map_scan/summary.json",
        "n_per_offset": summary["n_per_offset"],
        "observed_peak_to_min_ratio": summary["observed_peak_to_min_ratio"],
        "max_recorded_p_reflect_minus_xop_map": summary["max_recorded_p_reflect_minus_xop_map"],
        "all_per_ring_sources_external": summary["all_per_ring_sources_external"],
        "all_registered_in_geant4_em_category": em_category,
        "all_process_base_g4vemprocess": g4vemprocess,
        "all_transmitted_space_rows_match_summary": summary.get("all_transmitted_space_rows_match_summary", False),
    }


def _external_lens_import_ready_check(root: Path) -> dict[str, object]:
    files = {
        "schema": root / "benchmarks/reference_outputs/EXTERNAL_LENS_OBSERVABLES_SCHEMA.md",
        "hits_schema": root / "benchmarks/reference_outputs/EXTERNAL_LENS_HITS_SCHEMA.md",
        "schema_example": root / "benchmarks/reference_outputs/external_lens_observables_schema_example.csv",
        "tool": root / "tools/import_external_lens_observables.py",
        "hits_tool": root / "tools/import_external_lens_hits.py",
        "heart_hdf5_tool": root / "tools/import_heart_detector_image.py",
        "heart_summary_rebuild_tool": root / "tools/rebuild_heart_detector_from_tile_summary.py",
        "module": root / "laue511/external_lens.py",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    return {
        "ok": not missing,
        "status": "ready" if not missing else "missing",
        "missing": missing,
        "evidence": "benchmarks/reference_outputs/EXTERNAL_LENS_OBSERVABLES_SCHEMA.md",
    }


def _external_lens_request_ready_check(root: Path) -> dict[str, object]:
    files = {
        "request_json": root / "benchmarks/reference_outputs/external_lens_oracle_request.json",
        "heart_request_json": root / "benchmarks/reference_outputs/heart_lens_adapter_request.json",
        "rings_csv": root / "benchmarks/reference_outputs/external_lens_oracle_rings.csv",
        "tiles_csv": root / "benchmarks/reference_outputs/external_lens_oracle_tiles.csv",
        "tool": root / "tools/export_external_lens_request.py",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    if missing:
        return {
            "ok": False,
            "status": "missing",
            "missing": missing,
            "evidence": "benchmarks/reference_outputs/external_lens_oracle_request.json",
        }
    request = _load_json(files["request_json"])
    heart_request = _load_json(files["heart_request_json"])
    rings_csv = _read_csv(files["rings_csv"])
    tiles_csv = _read_csv(files["tiles_csv"])
    ring_config = _read_csv(root / "data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    full_lens = _load_json(root / "reports/full_lens_observables/metrics.json")
    python_ref = _load_json(root / "reports/python_full_lens_reference/metrics.json")
    target = request.get("comparison_targets", {})
    comparison_targets_ok = (
        _close(target.get("current_opticsim_observed_diffracted_area_cm2"), full_lens["observed_diffracted_area_cm2"])
        and _close(target.get("current_opticsim_spot_d90_cm"), full_lens["spot_d90_cm"])
        and _close(target.get("python_reference_diffracted_area_cm2"), python_ref["diffracted_area_reference_cm2"])
        and _close(target.get("geometric_area_cm2"), python_ref["geometric_area_cm2"])
    )
    request_rings_ok = _request_rings_match_config(request.get("rings", []), ring_config)
    rings_csv_ok = _rings_csv_match_config(rings_csv, ring_config)
    tiles_csv_ok = _tiles_csv_match_config(tiles_csv, ring_config, full_lens["focal_z_mm"])
    coordinate_ok = _close(
        request.get("coordinate_convention", {}).get("focal_plane_z_mm"),
        full_lens["focal_z_mm"],
    )
    heart_adapter_ok = (
        heart_request.get("source_request") == "external_lens_oracle_request.json"
        and heart_request.get("requested_hit_table_schema") == "EXTERNAL_LENS_HITS_SCHEMA.md"
        and heart_request.get("requested_tile_table") == "external_lens_oracle_tiles.csv"
        and str(heart_request.get("heart", {}).get("head_commit_checked", ""))
    )
    ok = (
        comparison_targets_ok
        and request_rings_ok
        and rings_csv_ok
        and tiles_csv_ok
        and coordinate_ok
        and bool(heart_adapter_ok)
    )
    return {
        "ok": ok,
        "status": "ready" if ok else "stale",
        "missing": [],
        "comparison_targets_ok": comparison_targets_ok,
        "request_rings_ok": request_rings_ok,
        "rings_csv_ok": rings_csv_ok,
        "tiles_csv_ok": tiles_csv_ok,
        "coordinate_ok": coordinate_ok,
        "heart_adapter_ok": bool(heart_adapter_ok),
        "evidence": "benchmarks/reference_outputs/external_lens_oracle_request.json",
    }


def _evidence_text(name: str, check: dict[str, object]) -> str:
    if "max_probability_delta" in check:
        return f"rows={check['rows_checked']}, max probability delta={check['max_probability_delta']:.3g}, max |z|={check['max_branch_z']:.2f}"
    if name.startswith("cosima_bridge"):
        return f"{check['history_joined_rows']}/{check['n_rows']} rows joined"
    if name == "focal_convention":
        return f"max p_diff shift={check['max_abs_p_diff_delta']:.3g}, max angle={check['max_abs_delta_theta_entry_arcsec']:.3g} arcsec"
    if name == "external_lens_handoff":
        return f"rows={check['n_rows']}, import={check['import_ok']}, tmp removed={check['work_dir_removed']}"
    if name == "full_lens_observables":
        return (
            f"phase hit delta={check['max_phase_intersection_delta_mm']:.3g} mm, "
            f"spot d90={check['spot_d90_cm']:.3g} cm, "
            f"Aeff delta={check['effective_area_delta_cm2']:.3g} cm2"
        )
    if name == "python_full_lens_reference":
        return (
            f"Aeff ref={check['diffracted_area_reference_cm2']:.3g} cm2, "
            f"delta={check['diffracted_area_delta_cm2']:.3g} cm2, "
            f"max |z|={check['max_abs_branch_z']:.2f}"
        )
    if name == "kohnle1998_check":
        return f"endpoint max abs error={check['endpoint_max_abs_error']:.3g}"
    if name == "pytte_check":
        return f"cases={check['n_cases']}"
    if name == "opticsim_table_lens_closure":
        return (
            f"delta diff frac={check['delta_diffraction_fraction']:.3g}, "
            f"max per-ring p_diff delta={check['max_abs_delta_mean_p_diff_by_ring']:.3g}, "
            f"spot d90 delta={check['delta_spot_d90_cm']:.3g} cm"
        )
    if check.get("n_rows") is not None and check.get("peak_reflectivity") is not None:
        return f"rows={check['n_rows']}, peak={check['peak_reflectivity']:.3g}, flux residual={check['max_flux_conservation_residual']:.3g}"
    if name in {"external_lens_import_ready", "external_lens_request_ready"}:
        return str(check.get("status", ""))
    if name == "external_lens_curve" and check.get("status") == "imported":
        return (
            f"Aeff={check['diffracted_area_cm2']:.3g} cm2, "
            f"spot d90={check['spot_d90_cm']:.3g} cm, "
            f"delta Aeff={check['diffracted_area_minus_current_observed_cm2']:.3g} cm2"
        )
    if name == "bfull_offaxis_scan" and check.get("status") == "imported":
        return (
            f"n/offset={check['n_per_offset']}, "
            f"obs peak/min={check['observed_peak_to_min_ratio']:.3g}, "
            f"ring2 obs={check['ring2_observed_peak_to_min_ratio']:.3g}, "
            f"ring2 XOP={check['ring2_xop_peak_to_min_ratio']:.3g}, "
            f"all G4VEm={check['all_process_base_g4vemprocess']}, "
            f"trans rows={check['all_transmitted_space_rows_match_summary']}"
        )
    if name == "bfull_single_tile_xop_scan" and check.get("status") == "imported":
        return (
            f"ring/tile={check['ring_id']}/{check['tile_id']}, "
            f"n/offset={check['n_per_offset']}, "
            f"XOP peak={check['xop_peak_reflectivity_in_scan']:.3g}, "
            f"obs peak={check['observed_peak_interaction_fraction']:.3g}, "
            f"max p delta={check['max_recorded_p_reflect_minus_xop']:.3g}, "
            f"all G4VEm={check['all_process_base_g4vemprocess']}, "
            f"trans rows={check['all_transmitted_space_rows_match_summary']}"
        )
    if name == "bfull_rocking_curve_map_status":
        return (
            f"status={check.get('status')}, "
            f"covered={check.get('covered_ring_ids')}, "
            f"missing={check.get('missing_ring_ids')}"
        )
    if name == "bfull_full_lens_xop_map_scan" and check.get("status") == "imported":
        return (
            f"n/offset={check['n_per_offset']}, "
            f"obs peak/min={check['observed_peak_to_min_ratio']:.3g}, "
            f"max p delta={check['max_recorded_p_reflect_minus_xop_map']:.3g}, "
            f"all external={check['all_per_ring_sources_external']}, "
            f"all G4VEm={check['all_process_base_g4vemprocess']}, "
            f"trans rows={check['all_transmitted_space_rows_match_summary']}"
        )
    return str(check.get("status", ""))


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _request_rings_match_config(request_rings: object, config_rows: list[dict[str, str]]) -> bool:
    if not isinstance(request_rings, list) or len(request_rings) != len(config_rows):
        return False
    for request_ring, config_row in zip(request_rings, config_rows):
        if not isinstance(request_ring, dict):
            return False
        if not _ring_row_matches(request_ring, config_row):
            return False
    return True


def _rings_csv_match_config(rings_csv: list[dict[str, str]], config_rows: list[dict[str, str]]) -> bool:
    if len(rings_csv) != len(config_rows):
        return False
    return all(_ring_row_matches(row, config) for row, config in zip(rings_csv, config_rows))


def _tiles_csv_match_config(tiles_csv: list[dict[str, str]], config_rows: list[dict[str, str]], focal_z_mm: object) -> bool:
    expected_rows = sum(int(float(row["n_tiles"])) for row in config_rows)
    required = {
        "ring_id",
        "tile_id",
        "design_energy_keV",
        "center_x_mm",
        "center_y_mm",
        "center_z_mm",
        "focal_x_mm",
        "focal_y_mm",
        "focal_z_mm",
        "incoming_ux",
        "incoming_uy",
        "incoming_uz",
        "expected_diffracted_ux",
        "expected_diffracted_uy",
        "expected_diffracted_uz",
        "ideal_plane_normal_x",
        "ideal_plane_normal_y",
        "ideal_plane_normal_z",
        "radial_axis_x",
        "radial_axis_y",
        "radial_axis_z",
        "tangential_axis_x",
        "tangential_axis_y",
        "tangential_axis_z",
        "slab_normal_x",
        "slab_normal_y",
        "slab_normal_z",
        "tile_size_mm",
        "thickness_mm",
        "material",
        "h",
        "k",
        "l",
        "d_spacing_A",
    }
    if len(tiles_csv) != expected_rows or not tiles_csv or not required.issubset(tiles_csv[0]):
        return False
    config_by_ring = {int(float(row["ring_id"])): row for row in config_rows}
    seen: set[tuple[int, int]] = set()
    focal_z = float(focal_z_mm)
    for row in tiles_csv:
        try:
            ring_id = int(float(row["ring_id"]))
            tile_id = int(float(row["tile_id"]))
        except ValueError:
            return False
        config = config_by_ring.get(ring_id)
        if config is None:
            return False
        n_tiles = int(float(config["n_tiles"]))
        if not 0 <= tile_id < n_tiles or (ring_id, tile_id) in seen:
            return False
        seen.add((ring_id, tile_id))
        if not _tile_row_matches(row, config, tile_id, focal_z):
            return False
    return len(seen) == expected_rows


def _tile_row_matches(row: dict[str, object], config: dict[str, str], tile_id: int, focal_z: float) -> bool:
    n_tiles = int(float(config["n_tiles"]))
    radius_mm = float(config["radius_mm"])
    thickness_mm = float(config["thickness_mm"])
    phi = 2.0 * math.pi * tile_id / n_tiles
    cos_phi = math.cos(phi)
    sin_phi = math.sin(phi)
    center = (radius_mm * cos_phi, radius_mm * sin_phi, -0.5 * thickness_mm)
    outgoing = _unit((-center[0], -center[1], focal_z - center[2]))
    plane_normal = _unit((-outgoing[0], -outgoing[1], 1.0 - outgoing[2]))
    expected = {
        "design_energy_keV": config["design_energy_keV"],
        "center_x_mm": center[0],
        "center_y_mm": center[1],
        "center_z_mm": center[2],
        "focal_x_mm": 0.0,
        "focal_y_mm": 0.0,
        "focal_z_mm": focal_z,
        "incoming_ux": 0.0,
        "incoming_uy": 0.0,
        "incoming_uz": 1.0,
        "expected_diffracted_ux": outgoing[0],
        "expected_diffracted_uy": outgoing[1],
        "expected_diffracted_uz": outgoing[2],
        "ideal_plane_normal_x": plane_normal[0],
        "ideal_plane_normal_y": plane_normal[1],
        "ideal_plane_normal_z": plane_normal[2],
        "radial_axis_x": cos_phi,
        "radial_axis_y": sin_phi,
        "radial_axis_z": 0.0,
        "tangential_axis_x": -sin_phi,
        "tangential_axis_y": cos_phi,
        "tangential_axis_z": 0.0,
        "slab_normal_x": 0.0,
        "slab_normal_y": 0.0,
        "slab_normal_z": 1.0,
        "tile_size_mm": config["tile_size_mm"],
        "thickness_mm": config["thickness_mm"],
        "h": config["h"],
        "k": config["k"],
        "l": config["l"],
        "d_spacing_A": config["d_spacing_A"],
    }
    numeric_ok = all(_close(row.get(key), value, tolerance=1.0e-9) for key, value in expected.items())
    return numeric_ok and str(row.get("material")) == config["material"]


def _ring_row_matches(row: dict[str, object], config: dict[str, str]) -> bool:
    numeric = ("ring_id", "design_energy_keV", "radius_mm", "n_tiles", "tile_size_mm", "thickness_mm", "h", "k", "l", "d_spacing_A")
    for key in numeric:
        if not _close(row.get(key), config[key]):
            return False
    return str(row.get("material")) == config["material"]


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    return (v[0] / n, v[1] / n, v[2] / n)


def _close(left: object, right: object, tolerance: float = 1.0e-12) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return False


def _workspace_relative(path: Path) -> str:
    parts = path.parts
    if "benchmarks" in parts:
        index = parts.index("benchmarks")
        return str(Path(*parts[index:]))
    return str(path)
