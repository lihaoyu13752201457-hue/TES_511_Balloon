from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SUMMARY_FILES = {
    "channel_python": "runs/channel_4ring_calibrated_v2/summary.json",
    "geant4_channel_effective": "runs/geant4_channel_4ring_effective/summary.json",
    "geant4_laue": "runs/geant4_laue_multiring_darwin/summary.json",
    "detector_python": "runs/detector_only_4ring_calibrated_v2/summary.json",
    "geant4_detector": "runs/geant4_detector_only_1k/summary.json",
    "wsi_crosscheck": "runs/wsi_parratt_crosscheck/summary.json",
}

KEY_FILES = [
    "CODEX_NEXT_STEPS_OPTICSIM.md",
    "README.md",
    "CMakeLists.txt",
    "docs/physics_assumptions.md",
    "docs/validation_matrix.md",
    "config/cam511_channel_baseline.yaml",
    "data/reflectivity/WSi_511keV_parratt_grid.csv",
    "external_baseline/channel_raytrace_py/channel_raytrace.py",
    "external_baseline/channel_raytrace_py/reflectivity_table.py",
    "external_baseline/channel_raytrace_py/two_wall.py",
    "geant4_app/include/optics/GammaChannelReflection.hh",
    "geant4_app/include/optics/ReflectivityTable.hh",
    "geant4_app/src/optics/GammaChannelReflection.cc",
    "geant4_app/src/optics/ReflectivityTable.cc",
    "geant4_app/src/channel_two_wall_demo.cc",
    "geant4_app/src/channel_two_wall_table_demo.cc",
    "geant4_app/src/channel_single_curved_demo.cc",
    "geant4_app/src/channel_4ring_effective_demo.cc",
    "analysis/scan_single_curved_geometry.py",
    "analysis/scan_single_curved_gap.py",
    "analysis/estimate_channel_geometry_constraints.py",
    "analysis/reconcile_channel_bounce_path.py",
    "analysis/run_project_audit.py",
    "analysis/build_gpt_pro_review_packet.py",
    "reports/opticsim_progress_report.pdf",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def maybe_git_hash() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def load_json(rel: str) -> dict[str, Any]:
    with (ROOT / rel).open() as f:
        return json.load(f)


def select_metrics() -> dict[str, Any]:
    summaries = {name: load_json(rel) for name, rel in SUMMARY_FILES.items()}
    detector = summaries["detector_python"]
    selected_fraction = detector["n_selected_line_window"] / detector["n_input_photons"]
    return {
        "channel_python": {
            "transmissivity": summaries["channel_python"]["transmissivity"],
            "effective_area_cm2": summaries["channel_python"]["effective_area_cm2"],
            "spot_d90_cm": summaries["channel_python"]["spot_d90_cm"],
        },
        "geant4_channel_effective": {
            "transmissivity": summaries["geant4_channel_effective"]["transmissivity"],
            "effective_area_cm2": summaries["geant4_channel_effective"]["effective_area_cm2"],
            "spot_d90_cm": summaries["geant4_channel_effective"]["spot_d90_cm"],
        },
        "geant4_laue": {
            "diffraction_fraction": summaries["geant4_laue"]["diffraction_fraction"],
            "n_primaries": summaries["geant4_laue"]["n_primaries"],
        },
        "detector_python": {
            "measured_peak_fwhm_eV": detector["measured_peak_fwhm_eV"],
            "n_selected_line_window": detector["n_selected_line_window"],
            "n_input_photons": detector["n_input_photons"],
            "selected_fraction_total": selected_fraction,
        },
        "geant4_detector": {
            "n_simulated": summaries["geant4_detector"]["n_simulated"],
            "n_hits": summaries["geant4_detector"]["n_hits"],
            "tes_detection_fraction": summaries["geant4_detector"]["tes_detection_fraction"],
        },
        "wsi_crosscheck": {
            "status": summaries["wsi_crosscheck"]["status"],
            "n_rows": summaries["wsi_crosscheck"]["n_rows"],
            "max_abs_delta_R": summaries["wsi_crosscheck"]["max_abs_delta_R"],
        },
    }


def build_manifest() -> dict[str, Any]:
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
    return {
        "git_commit": maybe_git_hash(),
        "files": files,
        "summary_files": SUMMARY_FILES,
    }


def write_report(metrics: dict[str, Any], manifest: dict[str, Any], path: Path) -> None:
    lines = [
        "# Frozen Baseline Metrics",
        "",
        "This snapshot protects the current scaffold while Geant4 channel optics is upgraded.",
        "Detector metrics are retained only as a staged-interface regression guard; detector mass-model work is not the current optics priority.",
        "",
        f"Git commit: `{manifest['git_commit'] or 'not-a-git-worktree'}`",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    rows = [
        ("channel_python.transmissivity", metrics["channel_python"]["transmissivity"]),
        ("channel_python.effective_area_cm2", metrics["channel_python"]["effective_area_cm2"]),
        ("channel_python.spot_d90_cm", metrics["channel_python"]["spot_d90_cm"]),
        ("geant4_channel_effective.transmissivity", metrics["geant4_channel_effective"]["transmissivity"]),
        ("geant4_channel_effective.effective_area_cm2", metrics["geant4_channel_effective"]["effective_area_cm2"]),
        ("geant4_channel_effective.spot_d90_cm", metrics["geant4_channel_effective"]["spot_d90_cm"]),
        ("geant4_laue.diffraction_fraction", metrics["geant4_laue"]["diffraction_fraction"]),
        ("detector_python.measured_peak_fwhm_eV", metrics["detector_python"]["measured_peak_fwhm_eV"]),
        ("detector_python.n_selected_line_window", metrics["detector_python"]["n_selected_line_window"]),
        ("detector_python.selected_fraction_total", metrics["detector_python"]["selected_fraction_total"]),
        ("wsi_crosscheck.max_abs_delta_R", metrics["wsi_crosscheck"]["max_abs_delta_R"]),
    ]
    for name, value in rows:
        if isinstance(value, float):
            lines.append(f"| `{name}` | `{value:.12g}` |")
        else:
            lines.append(f"| `{name}` | `{value}` |")
    lines.append("")
    lines.append(f"Hashed files: `{sum(1 for row in manifest['files'] if row['exists'])}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze current opticsim scaffold metrics for regression checks.")
    parser.add_argument("--out", default="reports/baseline")
    args = parser.parse_args()

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    metrics = select_metrics()
    manifest = build_manifest()
    with (out / "baseline_metrics.json").open("w") as f:
        json.dump(metrics, f, indent=2, sort_keys=True)
        f.write("\n")
    with (out / "baseline_manifest.json").open("w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    write_report(metrics, manifest, out / "baseline_report.md")
    print(out / "baseline_metrics.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
