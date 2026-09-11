from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


KEY_FILES = [
    "README.md",
    "docs/physics_assumptions.md",
    "docs/validation_matrix.md",
    "data/reflectivity/README.md",
    "config/cam511_channel_baseline.yaml",
    "config/detector_tes_bgo.yaml",
    "CMakeLists.txt",
    "external_baseline/channel_raytrace_py/channel_raytrace.py",
    "external_baseline/channel_raytrace_py/reflectivity_table.py",
    "external_baseline/channel_raytrace_py/parratt_reflectivity.py",
    "external_baseline/detector_response_py/detector_response.py",
    "external_baseline/io_contract_py/io_contract.py",
    "geant4_app/include/optics/ReflectivityTable.hh",
    "geant4_app/src/optics/GammaChannelReflection.cc",
    "geant4_app/src/optics/ReflectivityTable.cc",
    "geant4_app/src/channel_two_wall_table_demo.cc",
    "geant4_app/src/channel_single_curved_demo.cc",
    "geant4_app/src/detector_only_demo.cc",
    "geant4_app/src/laue_one_ring_demo.cc",
    "geant4_app/src/channel_4ring_effective_demo.cc",
    "analysis/freeze_baseline.py",
    "analysis/compare_to_baseline.py",
    "analysis/scan_single_curved_geometry.py",
    "analysis/scan_single_curved_gap.py",
    "analysis/estimate_channel_geometry_constraints.py",
    "analysis/reconcile_channel_bounce_path.py",
    "analysis/run_project_audit.py",
    "analysis/build_gpt_pro_review_packet.py",
    "analysis/validate_io_contract.py",
    "analysis/crosscheck_wsi_parratt.py",
    "records/2026-05-18_bounce_path_reconciliation.md",
    "reports/project_audit/audit_report.md",
    "reports/opticsim_progress_report.pdf",
]


SUMMARY_FILES = {
    "channel_4ring_python": "runs/channel_4ring_calibrated_v2/summary.json",
    "detector_python": "runs/detector_only_4ring_calibrated_v2/summary.json",
    "wsi_crosscheck": "runs/wsi_parratt_crosscheck/summary.json",
    "geant4_two_wall_table": "runs/geant4_channel_two_wall_table/summary.json",
    "geant4_single_curved": "runs/geant4_channel_single_curved_bend12m_constant/summary.json",
    "geant4_single_curved_table": "runs/geant4_channel_single_curved_bend12m_table/summary.json",
    "geant4_single_curved_scan": "runs/geant4_channel_single_curved_scan/summary.json",
    "geant4_single_curved_gap_scan": "runs/geant4_channel_single_curved_gap_scan/summary.json",
    "channel_geometry_constraints": "runs/channel_geometry_constraints/summary.json",
    "channel_bounce_path_reconciliation": "runs/channel_bounce_path_reconciliation/summary.json",
    "baseline": "reports/baseline/baseline_metrics.json",
    "geant4_detector_1k": "runs/geant4_detector_only_1k/summary.json",
    "geant4_laue": "runs/geant4_laue_one_ring/summary.json",
    "geant4_channel": "runs/geant4_channel_4ring_effective/summary.json",
    "audit": "reports/project_audit/audit_summary.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(rel: str) -> dict[str, object]:
    with (ROOT / rel).open() as f:
        return json.load(f)


def build_manifest() -> dict[str, object]:
    files = []
    for rel in KEY_FILES:
        path = ROOT / rel
        files.append(
            {
                "path": rel,
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256(path) if path.exists() else None,
            }
        )
    summaries = {name: load_json(rel) for name, rel in SUMMARY_FILES.items() if (ROOT / rel).exists()}
    return {"files": files, "summaries": summaries}


def build_markdown(manifest: dict[str, object]) -> str:
    s = manifest["summaries"]
    channel = s["channel_4ring_python"]
    detector = s["detector_python"]
    wsi = s["wsi_crosscheck"]
    two_wall_table = s.get("geant4_two_wall_table", {})
    single_curved = s.get("geant4_single_curved", {})
    single_curved_table = s.get("geant4_single_curved_table", {})
    single_curved_scan = s.get("geant4_single_curved_scan", {})
    single_curved_gap = s.get("geant4_single_curved_gap_scan", {})
    geometry_constraints = s.get("channel_geometry_constraints", {})
    bounce_path = s.get("channel_bounce_path_reconciliation", {})
    g4det = s["geant4_detector_1k"]
    g4laue = s["geant4_laue"]
    g4channel = s["geant4_channel"]
    audit = s.get("audit", {})

    lines = [
        "# GPT Pro Review Packet: 500-511 keV Focusing Optics Simulation",
        "",
        "## Review Objective",
        "",
        "Please audit whether this repository is a credible staged research implementation of the supplied Codex guide for 500-511 keV Laue/channel optics and detector handoff. The intended claim is project-review readiness for the next research phase, not a final publication-grade instrument model.",
        "",
        "## Current Verdict Requested",
        "",
        "Decide whether the project is ready to proceed from scaffold/prototype implementation to focusing-optics physics-refinement work: curved channel wall geometry, per-bounce W/Si table-driven reflection, dynamical Laue diffraction tables, and non-xraydb optical-constant provenance. Detector mass-model refinement is deliberately out of the current mainline except as a staged interface regression guard.",
        "",
        "## Top-Level Evidence",
        "",
        f"- Python 4-ring calibrated channel: transmissivity `{channel['transmissivity']:.5f}`, Aeff `{channel['effective_area_cm2']:.4f} cm2`, spot d90 `{channel['spot_d90_cm']:.4f} cm`.",
        f"- W/Si Parratt cross-check: `{wsi['status']}`, rows `{wsi['n_rows']}`, max_abs_delta_R `{wsi['max_abs_delta_R']}`.",
        f"- Geant4 two-wall table-driven channel nucleus: survival `{two_wall_table.get('survival_fraction', 0.0):.3f}` at theta `{two_wall_table.get('theta_rad', 0.0):.2e} rad`, boundary rows `{two_wall_table.get('n_boundary', 0)}`.",
        f"- Geant4 single curved channel v0: constant-R survival `{single_curved.get('survival_fraction', 0.0):.3f}`, mean grazing `{single_curved.get('mean_grazing_angle_rad', 0.0):.2e} rad`; W/Si table survival `{single_curved_table.get('survival_fraction', 0.0):.3f}`.",
        f"- Geant4 single curved scan: best boundary-hit W/Si survival `{single_curved_scan.get('best_table_survival_with_boundary', {}).get('survival_fraction', 0.0):.3f}` near theta `{single_curved_scan.get('best_table_survival_with_boundary', {}).get('mean_grazing_angle_rad', 0.0):.2e} rad`; 46mm/12m bend theta `{single_curved_scan.get('closest_to_12m_bend', {}).get('mean_grazing_angle_rad', 0.0):.2e} rad`.",
        f"- Geant4 single curved gap scan: best W/Si survival at 46mm/12m bend `{single_curved_gap.get('best_table_survival_12m_bend', {}).get('survival_fraction', 0.0):.3f}`; minimum constant-R 12m mean theta `{single_curved_gap.get('min_constant_theta_12m_bend', {}).get('mean_grazing_angle_rad', 0.0):.2e} rad`.",
        f"- Four-ring geometry constraint estimate: configured bends require up to `{geometry_constraints.get('max_required_bounces_from_config_bend', 0.0):.2f}` small-angle reflections at calibrated theta; max required/effective bounce ratio `{geometry_constraints.get('max_bounce_ratio_config_to_effective', 0.0):.2f}`.",
        f"- Channel bounce/path reconciliation: current effective bounces `{bounce_path.get('effective_model_bounce_range', [0, 0])[0]:.0f}-{bounce_path.get('effective_model_bounce_range', [0, 0])[1]:.0f}`, calibrated-theta requirement `{bounce_path.get('required_bounce_range_at_calibrated_theta', [0, 0])[0]:.2f}-{bounce_path.get('required_bounce_range_at_calibrated_theta', [0, 0])[1]:.2f}`, lineage clue `{bounce_path.get('literature_reflection_range', [0, 0])[0]}-{bounce_path.get('literature_reflection_range', [0, 0])[1]}`.",
        "- Literature cross-check: the OSTI accepted manuscript for Shirazi et al. 2020 says the same channel-optics lineage used many-reflection ray tracing, with 17-38 reflections for its 122 keV strawman parallel-beam case.",
        f"- Geant4 channel 4-ring effective scaffold: transmissivity `{g4channel['transmissivity']:.5f}`, Aeff `{g4channel['effective_area_cm2']:.4f} cm2`, spot d90 `{g4channel['spot_d90_cm']:.4f} cm`.",
        f"- Geant4 Laue one-ring toy: diffraction fraction `{g4laue['diffraction_fraction']:.3f}` for `{g4laue['n_primaries']}` events.",
        f"- Python detector-only calibrated backend: selected line-window events `{detector['n_selected_line_window']}`, peak FWHM `{detector['measured_peak_fwhm_eV']:.2f} eV`.",
        f"- Geant4 detector-only scaffold: `{g4det['n_simulated']}` events, `{g4det['n_hits']}` raw hits, TES detection fraction `{g4det['tes_detection_fraction']:.3f}`.",
        f"- Project audit status: `{'PASS' if audit.get('ok') else 'MISSING/FAIL'}` across `{len(audit.get('commands', []))}` checks.",
        "",
        "## Claim Boundaries",
        "",
        "| Claim | Evidence | Explicit Limit |",
        "| --- | --- | --- |",
        "| Staged optics-detector handoff works | IO contract validates phase_space, optics_history, hits, event_summary and crosslinks | Does not require one continuous Geant4 world |",
        "| 511-CAM-like channel benchmark is reproduced at scaffold level | Python calibrated and Geant4 effective runs match throughput/Aeff/spot scale | Effective survival/focus, not curved wall-by-wall channel geometry |",
        "| Per-bounce Geant4 channel reflection can use W/Si R/A/T tables | `channel_two_wall_table_demo` logs boundary-level R/A/T, directions and actions | Two-wall validation nucleus, not full curved 4-ring optics |",
        "| Curved-wall Geant4 geometry path has started | `channel_single_curved_demo` writes phase_space and boundary history with the same reflection process | v0 diagnostic; segment convergence and local grazing-angle mismatch remain open |",
        "| The simple 12 m single-channel curved interpretation is falsified for current W/Si table | Gap scan keeps 46mm/12m W/Si survival at zero and analytic constraints show missing bounce count | Does not yet identify the final Shirazi/IDL wall geometry; it narrows the next physics task |",
        "| The many-bounce path is now bracketed as a diagnostic | Bounce/path reconciliation compares current 1-3 bounces, 6-13 calibrated-theta need, and the 17-38 lineage clue | The literature clue is not directly imported as a 511-CAM parameter |",
        "| The missing bounce/path model is supported by literature | Shirazi et al. 2020 accepted manuscript reports 17-38 reflections in its soft gamma-ray concentrator ray tracing | Not directly the 511-CAM four-ring table; used as lineage evidence, not as a direct parameter import |",
        "| W/Si table arithmetic is internally cross-checked | Manual Parratt recursion matches xraydb multilayer table | Still uses xraydb/Chantler optical constants |",
        "| Laue Geant4 process path is proven | LaueToyProcess writes contract outputs and focuses p_diff=1 photons | Constant toy probabilities, not dynamical diffraction |",
        "| Detector handoff remains usable | Python calibrated backend and Geant4 raw-edep scaffold both write detector contracts | Detector mass-model refinement is not part of the current optics-mainline push |",
        "",
        "## Reproduction Commands",
        "",
        "```bash",
        "python3 reports/build_progress_pdf.py",
        "python3 analysis/freeze_baseline.py --out reports/baseline",
        "python3 analysis/compare_to_baseline.py --baseline reports/baseline/baseline_metrics.json --current reports/baseline/baseline_metrics.json",
        "python3 analysis/run_project_audit.py --out reports/project_audit",
        "python3 analysis/build_gpt_pro_review_packet.py",
        "```",
        "",
        "Selected direct runs:",
        "",
        "```bash",
        "python3 analysis/crosscheck_wsi_parratt.py --out runs/wsi_parratt_crosscheck",
        "/tmp/opticsim-build/channel_two_wall_table_demo --n 1000 --energy-keV 511 --theta-rad 1.5e-4 --reflectivity-table data/reflectivity/WSi_511keV_parratt_grid.csv --out runs/geant4_channel_two_wall_table --seed 20260517",
        "/tmp/opticsim-build/channel_single_curved_demo --n 20 --R 1 --A 0 --T 0 --segments 64 --bend-angle-rad 0.003833333333 --out runs/geant4_channel_single_curved_bend12m_constant --seed 20260517",
        "python3 analysis/scan_single_curved_geometry.py --out runs/geant4_channel_single_curved_scan",
        "python3 analysis/scan_single_curved_gap.py --out runs/geant4_channel_single_curved_gap_scan",
        "python3 analysis/estimate_channel_geometry_constraints.py --out runs/channel_geometry_constraints",
        "python3 analysis/reconcile_channel_bounce_path.py --out runs/channel_bounce_path_reconciliation",
        "/tmp/opticsim-build/laue_one_ring_demo 2000 runs/geant4_laue_one_ring 20260517",
        "/tmp/opticsim-build/channel_4ring_effective_demo 20000 runs/geant4_channel_4ring_effective 20260517",
        "/tmp/opticsim-build/detector_only_demo runs/channel_4ring_calibrated_v2/phase_space.csv runs/geant4_detector_only_1k 1000 20260517",
        "```",
        "",
        "## Key Artifacts",
        "",
        "- `reports/opticsim_progress_report.pdf`",
        "- `reports/project_audit/audit_report.md`",
        "- `docs/validation_matrix.md`",
        "- `docs/physics_assumptions.md`",
        "- `runs/wsi_parratt_crosscheck/summary.json`",
        "- `runs/geant4_channel_two_wall_table/summary.json`",
        "- `runs/geant4_channel_single_curved_bend12m_constant/summary.json`",
        "- `runs/geant4_channel_single_curved_bend12m_table/summary.json`",
        "- `runs/geant4_channel_single_curved_scan/summary.json`",
        "- `runs/geant4_channel_single_curved_gap_scan/summary.json`",
        "- `runs/channel_geometry_constraints/summary.json`",
        "- `runs/channel_bounce_path_reconciliation/summary.json`",
        "- `reports/baseline/baseline_metrics.json`",
        "- `runs/geant4_channel_4ring_effective/summary.json`",
        "- `runs/geant4_laue_one_ring/summary.json`",
        "- `runs/geant4_detector_only_1k/summary.json`",
        "",
        "## Questions For GPT Pro",
        "",
        "1. Is the staged phase-space/hits contract a scientifically acceptable architecture for this long-baseline optics + detector problem?",
        "2. Are the current scaffold boundaries stated clearly enough to prevent overclaiming?",
        "3. Given the gap scan and bounce-count constraint, what is the most plausible interpretation of the Shirazi/IDL channel geometry that avoids confusing total focusing deflection with local grazing angle?",
        "4. Are the benchmark tolerances and current validation matrix sufficient for a project-stage review?",
        "5. What additional evidence would be required before turning this into a publication-level simulation claim?",
        "",
        "## Key File Hashes",
        "",
        "| Path | SHA256 |",
        "| --- | --- |",
    ]
    for row in manifest["files"]:
        if row["exists"]:
            lines.append(f"| `{row['path']}` | `{row['sha256']}` |")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a GPT Pro review packet for the opticsim project.")
    parser.add_argument("--out-md", default="reports/gpt_pro_review_packet.md")
    parser.add_argument("--out-manifest", default="reports/gpt_pro_review_manifest.json")
    args = parser.parse_args()

    manifest = build_manifest()
    out_manifest = ROOT / args.out_manifest
    out_manifest.parent.mkdir(parents=True, exist_ok=True)
    with out_manifest.open("w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    (ROOT / args.out_md).write_text(build_markdown(manifest), encoding="utf-8")
    print(ROOT / args.out_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
