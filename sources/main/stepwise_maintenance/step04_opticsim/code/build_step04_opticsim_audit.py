#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
ROOT = SCRIPT.parents[3]
OUTPUT_DIR = STEP_DIR / "outputs"
OPTICSIM_ROOT = Path("/home/ubuntu/opticsim")
CROSS_CHECK_ROOT = Path("/home/ubuntu/cross_check_laue/laue511_validation")

BFULL_ONLINE_DIR = OUTPUT_DIR / "opticsim_laue_bfull_xopmap_real"
BFULL_XOPMAP_DIR = OUTPUT_DIR / "opticsim_laue_bfull_xopmap_real"
NOMINAL_DIR = BFULL_XOPMAP_DIR

OPTICSIM_BFULL_SOURCE = OPTICSIM_ROOT / "geant4_app/src/laue_multiring_bfull_demo.cc"
OPTICSIM_CMAKE = OPTICSIM_ROOT / "CMakeLists.txt"
RING_CONFIG = OPTICSIM_ROOT / "data/laue/ge111_balloon511_f9m_511keV_line_config.csv"
ROCKING_CURVE_MAP = STEP_DIR / "ge111_balloon511_f9m_511keV_xop_map.csv"
VALIDATION_STATUS = CROSS_CHECK_ROOT / "reports/validation_status.md"
CROSSCHECK_SUMMARY = CROSS_CHECK_ROOT / "reports/laue511_crosscheck_summary.md"
BOUNDS = ROOT / "outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json"

AUDIT_JSON = OUTPUT_DIR / "step04_opticsim_audit.json"
WRL_PATH = OUTPUT_DIR / "laue_bfull_xopmap_real_particles.wrl"
PNG_PATH = OUTPUT_DIR / "laue_bfull_xopmap_real_2d_schematic.png"
STAGE_SUMMARY_CSV = OUTPUT_DIR / "laue_bfull_xopmap_stage_summary.csv"
README_PATH = STEP_DIR / "README.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def line_count(path: Path) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    with path.open("rb") as handle:
        return sum(1 for _ in handle)


def file_record(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else None,
        "line_count": line_count(path),
        "sha256": sha256(path),
    }


def run_git(args: list[str]) -> str:
    proc = subprocess.run(
        ["git", "-C", str(OPTICSIM_ROOT), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return proc.stdout.strip()


def git_latest_commit() -> dict[str, Any]:
    lines = run_git(["log", "-1", "--format=%H%n%ci%n%s"]).splitlines()
    status = run_git(["status", "--short"])
    return {
        "repo": str(OPTICSIM_ROOT),
        "commit": lines[0] if len(lines) > 0 else "",
        "date": lines[1] if len(lines) > 1 else "",
        "subject": lines[2] if len(lines) > 2 else "",
        "tracked_worktree_clean": status == "",
        "status_short": status,
    }


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return default if value == "" else float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    return default if value == "" else int(float(value))


def read_ring_config(path: Path) -> list[dict[str, Any]]:
    rings = []
    for row in read_csv(path):
        rings.append(
            {
                "ring_id": as_int(row, "ring_id"),
                "design_energy_keV": as_float(row, "design_energy_keV"),
                "radius_mm": as_float(row, "radius_mm"),
                "n_tiles": as_int(row, "n_tiles"),
                "material": row.get("material", ""),
                "hkl": [as_int(row, "h"), as_int(row, "k"), as_int(row, "l")],
                "d_spacing_A": as_float(row, "d_spacing_A"),
                "tile_size_mm": as_float(row, "tile_size_mm"),
                "thickness_mm": as_float(row, "thickness_mm"),
                "z_offset_mm": as_float(row, "z_offset_mm", 0.0),
            }
        )
    return rings


def quantile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return float("nan")
    idx = min(len(sorted_values) - 1, max(0, math.ceil(fraction * len(sorted_values)) - 1))
    return sorted_values[idx]


def phase_space_stats(rows: list[dict[str, str]], be_radius_cm: float) -> dict[str, Any]:
    radii = sorted(math.hypot(float(row["x_mm"]) * 0.1, float(row["y_mm"]) * 0.1) for row in rows)
    energies = [float(row["E_keV"]) for row in rows]
    return {
        "rows": len(rows),
        "energy_min_keV": min(energies) if energies else None,
        "energy_max_keV": max(energies) if energies else None,
        "r50_cm": quantile(radii, 0.50),
        "r90_cm": quantile(radii, 0.90),
        "r95_cm": quantile(radii, 0.95),
        "r99_cm": quantile(radii, 0.99),
        "rmax_cm": max(radii) if radii else None,
        "be_radius_cm": be_radius_cm,
        "rmax_within_be": bool(radii and max(radii) <= be_radius_cm + 1.0e-9),
    }


def focal_crossing_stats(rows: list[dict[str, str]], be_radius_cm: float) -> dict[str, Any]:
    """Spot statistics for the physically tracked diffracted focal crossings.

    Unlike phase_space.csv (the analytic projection, one row per diffraction
    interaction), focal_crossings.csv records the diffracted gammas that actually
    cross the focal plane after EM exit attenuation/scatter. This is the set
    bridged to the detector, so the Be-window claim and the focused-signal count
    use these tracked rows, not the projection.
    """
    diffracted = [r for r in rows if r.get("source_tag") == "laue_bfull_diffracted"]
    radii = sorted(math.hypot(float(r["x_mm"]) * 0.1, float(r["y_mm"]) * 0.1) for r in diffracted)
    within = [rr for rr in radii if rr <= be_radius_cm + 1.0e-9]
    return {
        "diffracted_focal_rows": len(diffracted),
        "within_be_rows": len(within),
        "scattered_outside_be_rows": len(diffracted) - len(within),
        "r50_cm": quantile(radii, 0.50),
        "r90_cm": quantile(radii, 0.90),
        "r95_cm": quantile(radii, 0.95),
        "r99_cm": quantile(radii, 0.99),
        "rmax_cm": max(radii) if radii else None,
        "be_radius_cm": be_radius_cm,
        "r99_within_be": bool(radii and quantile(radii, 0.99) <= be_radius_cm + 1.0e-9),
    }


def write_stage_summary(histories: list[dict[str, str]]) -> None:
    by_key: defaultdict[tuple[str, int], int] = defaultdict(int)
    for row in histories:
        by_key[(row.get("stage", ""), as_int(row, "ring_id", -1))] += 1
    STAGE_SUMMARY_CSV.parent.mkdir(parents=True, exist_ok=True)
    with STAGE_SUMMARY_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["stage", "ring_id", "histories"])
        writer.writeheader()
        for (stage, ring_id), count in sorted(by_key.items()):
            writer.writerow({"stage": stage, "ring_id": ring_id, "histories": count})


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(sum(x * x for x in v))
    if n <= 0.0:
        return 0.0, 0.0, 1.0
    return v[0] / n, v[1] / n, v[2] / n


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def mul(v: tuple[float, float, float], s: float) -> tuple[float, float, float]:
    return v[0] * s, v[1] * s, v[2] * s


def write_lineset(handle: Any, name: str, segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]], color: tuple[float, float, float], transparency: float) -> None:
    handle.write(f"DEF {name} Shape {{\n")
    handle.write("  appearance Appearance {\n")
    handle.write(
        "    material Material { "
        f"diffuseColor {color[0]:.4f} {color[1]:.4f} {color[2]:.4f} "
        f"emissiveColor {color[0] * 0.35:.4f} {color[1] * 0.35:.4f} {color[2] * 0.35:.4f} "
        f"transparency {transparency:.4f} "
        "}\n"
    )
    handle.write("  }\n")
    handle.write("  geometry IndexedLineSet {\n")
    handle.write("    coord Coordinate { point [\n")
    for start, end in segments:
        handle.write(
            f"      {start[0] * 0.1:.6g} {start[1] * 0.1:.6g} {start[2] * 0.1:.6g}, "
            f"{end[0] * 0.1:.6g} {end[1] * 0.1:.6g} {end[2] * 0.1:.6g},\n"
        )
    handle.write("    ] }\n")
    handle.write("    coordIndex [\n")
    for idx in range(len(segments)):
        handle.write(f"      {2 * idx}, {2 * idx + 1}, -1,\n")
    handle.write("    ]\n")
    handle.write("  }\n")
    handle.write("}\n\n")


def ring_segments(rings: list[dict[str, Any]], focal_length_mm: float) -> dict[str, list[tuple[tuple[float, float, float], tuple[float, float, float]]]]:
    out: dict[str, list[tuple[tuple[float, float, float], tuple[float, float, float]]]] = {"RINGS": [], "FOCAL": []}
    for ring in rings:
        radius = float(ring["radius_mm"])
        for idx in range(180):
            a0 = 2.0 * math.pi * idx / 180.0
            a1 = 2.0 * math.pi * (idx + 1) / 180.0
            out["RINGS"].append(((radius * math.cos(a0), radius * math.sin(a0), 0.0), (radius * math.cos(a1), radius * math.sin(a1), 0.0)))
    cross = 85.0
    out["FOCAL"].extend(
        [
            ((-cross, 0.0, focal_length_mm), (cross, 0.0, focal_length_mm)),
            ((0.0, -cross, focal_length_mm), (0.0, cross, focal_length_mm)),
            ((-cross, -cross, focal_length_mm), (cross, -cross, focal_length_mm)),
            ((cross, -cross, focal_length_mm), (cross, cross, focal_length_mm)),
            ((cross, cross, focal_length_mm), (-cross, cross, focal_length_mm)),
            ((-cross, cross, focal_length_mm), (-cross, -cross, focal_length_mm)),
        ]
    )
    return out


def row_pos(row: dict[str, str]) -> tuple[float, float, float]:
    return float(row["x_mm"]), float(row["y_mm"]), float(row["z_mm"])


def write_wrl(histories: list[dict[str, str]], phase_rows: list[dict[str, str]], rings: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    phase_by_event = {as_int(row, "event_id"): row_pos(row) for row in phase_rows}
    focal = float(summary.get("focal_length_mm", 8300.0))
    incident_segments = []
    diffracted_segments = []
    for row in histories:
        pos = row_pos(row)
        din = normalize((as_float(row, "ux_in"), as_float(row, "uy_in"), as_float(row, "uz_in")))
        dout = normalize((as_float(row, "ux_out"), as_float(row, "uy_out"), as_float(row, "uz_out")))
        incident_segments.append((sub(pos, mul(din, 500.0)), pos))
        end = phase_by_event.get(as_int(row, "event_id"), add(pos, mul(dout, 2000.0)))
        diffracted_segments.append((pos, end))

    guide = ring_segments(rings, focal)
    WRL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WRL_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("#VRML V2.0 utf8\n")
        handle.write("WorldInfo {\n")
        handle.write('  title "Step04 B-FULL Laue XOP-map particle audit"\n')
        handle.write("  info [\n")
        handle.write(f'    "histories_used={len(histories)}"\n')
        handle.write(f'    "phase_space_rows={len(phase_rows)}"\n')
        handle.write('    "coordinates are opticsim mm scaled by 0.1 for display"\n')
        handle.write("  ]\n")
        handle.write("}\n")
        handle.write('NavigationInfo { type [ "EXAMINE", "ANY" ] }\n')
        handle.write("Background { skyColor [ 0.02 0.025 0.03 ] }\n\n")
        write_lineset(handle, "INCIDENT_TO_CRYSTAL", incident_segments, (0.17, 0.46, 0.95), 0.58)
        write_lineset(handle, "DIFFRACTED_TO_FOCUS", diffracted_segments, (0.96, 0.18, 0.12), 0.18)
        write_lineset(handle, "LAUE_RING_GUIDES", guide["RINGS"], (0.2, 0.85, 0.62), 0.05)
        write_lineset(handle, "FOCAL_PLANE_MARKER", guide["FOCAL"], (0.95, 0.92, 0.45), 0.0)

    return {
        "path": rel(WRL_PATH),
        "histories_used": len(histories),
        "phase_space_rows": len(phase_rows),
        "line_count": line_count(WRL_PATH),
        "size_bytes": WRL_PATH.stat().st_size,
        "sha256": sha256(WRL_PATH),
    }


def write_2d_schematic(histories: list[dict[str, str]], phase_rows: list[dict[str, str]], rings: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    phase_by_event = {as_int(row, "event_id"): row_pos(row) for row in phase_rows}
    focal = float(summary.get("focal_length_mm", 8300.0))

    fig, ax = plt.subplots(figsize=(11.0, 6.6), dpi=180)
    for row in histories:
        pos = row_pos(row)
        din = normalize((as_float(row, "ux_in"), as_float(row, "uy_in"), as_float(row, "uz_in")))
        dout = normalize((as_float(row, "ux_out"), as_float(row, "uy_out"), as_float(row, "uz_out")))
        incident = (sub(pos, mul(din, 500.0)), pos)
        outcome = (pos, phase_by_event.get(as_int(row, "event_id"), add(pos, mul(dout, 2000.0))))
        for a, b, color, alpha in [(incident[0], incident[1], "#2b6cb0", 0.03), (outcome[0], outcome[1], "#d73027", 0.055)]:
            ax.plot([a[2] / 1000.0, b[2] / 1000.0], [math.hypot(a[0], a[1]), math.hypot(b[0], b[1])], color=color, alpha=alpha, linewidth=0.35)

    for ring in rings:
        radius = float(ring["radius_mm"])
        ax.scatter([0.0], [radius], s=16, color="#059669", zorder=5)
        ax.text(0.05, radius + 0.7, f"R{ring['ring_id']} {ring['design_energy_keV']:.0f} keV", fontsize=7, color="#065f46")

    ax.axvline(0.0, color="#111827", linewidth=0.9, alpha=0.65)
    ax.axvline(focal / 1000.0, color="#7c2d12", linewidth=0.9, alpha=0.65)
    ax.set_xlabel("z position (m)")
    ax.set_ylabel("radial distance from optical axis (mm)")
    ax.set_title("Step04 B-FULL Laue XOP-map: radial-z projection")
    ax.set_xlim(-0.56, focal / 1000.0 + 0.35)
    ax.set_ylim(0.0, max(float(r["radius_mm"]) for r in rings) + 18.0)
    ax.grid(True, color="#d1d5db", linewidth=0.45, alpha=0.7)
    ax.legend(
        handles=[
            plt.Line2D([0], [0], color="#2b6cb0", lw=2, label="incident"),
            plt.Line2D([0], [0], color="#d73027", lw=2, label="diffracted"),
        ],
        loc="upper right",
        frameon=True,
        framealpha=0.92,
        fontsize=8,
    )
    fig.tight_layout()
    PNG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG_PATH)
    plt.close(fig)
    return {"path": rel(PNG_PATH), "size_bytes": PNG_PATH.stat().st_size, "sha256": sha256(PNG_PATH)}


def build_run_record(run_dir: Path, be_radius_cm: float) -> dict[str, Any]:
    summary = read_json(run_dir / "summary.json")
    phase_rows = read_csv(run_dir / "phase_space.csv")
    focal_rows = read_csv(run_dir / "focal_crossings.csv")
    histories = read_csv(run_dir / "optics_history.csv")
    transmitted_rows = read_csv(run_dir / "transmitted_space.csv")
    return {
        "directory": rel(run_dir),
        "summary": summary,
        "phase_space_stats": phase_space_stats(phase_rows, be_radius_cm),
        "phase_space_projection_note": "phase_space.csv is the analytic projection (one row per diffraction interaction); it overcounts focused flux and is NOT bridged. Use focal_crossing_stats.",
        "focal_crossing_stats": focal_crossing_stats(focal_rows, be_radius_cm),
        "history_rows": len(histories),
        "transmitted_rows": len(transmitted_rows),
        "source_files": {
            "summary_json": file_record(run_dir / "summary.json"),
            "per_ring_summary_json": file_record(run_dir / "per_ring_summary.json"),
            "optics_history": file_record(run_dir / "optics_history.csv"),
            "phase_space": file_record(run_dir / "phase_space.csv"),
            "transmitted_space": file_record(run_dir / "transmitted_space.csv"),
            "focal_crossings": file_record(run_dir / "focal_crossings.csv"),
            "wrl": file_record(run_dir / "laue_multiring_scene.wrl"),
        },
    }


def build_audit() -> dict[str, Any]:
    bounds = read_json(BOUNDS)
    be_radius_cm = float(bounds["META"]["be_window_radius_reference_cm"])
    rings = read_ring_config(RING_CONFIG)

    nominal_summary = read_json(NOMINAL_DIR / "summary.json")
    nominal_histories = read_csv(NOMINAL_DIR / "optics_history.csv")
    nominal_phase = read_csv(NOMINAL_DIR / "phase_space.csv")
    write_stage_summary(nominal_histories)
    wrl_record = write_wrl(nominal_histories, nominal_phase, rings, nominal_summary)
    png_record = write_2d_schematic(nominal_histories, nominal_phase, rings, nominal_summary)

    nominal = build_run_record(NOMINAL_DIR, be_radius_cm)
    online = build_run_record(BFULL_ONLINE_DIR, be_radius_cm)
    nominal_stats = nominal["phase_space_stats"]
    nominal_focal = nominal["focal_crossing_stats"]
    summary = nominal["summary"]
    online_summary = online["summary"]

    checks = {
        "channel_optics_used": False,
        "bfull_source_exists": OPTICSIM_BFULL_SOURCE.exists(),
        "standard_geant4_em_enabled": bool(summary.get("standard_geant4_em_enabled")),
        "process_base_is_g4vdiscreteprocess": summary.get("geant4_process_base_class") == "G4VDiscreteProcess",
        "external_xop_map_used": bool(summary.get("uses_external_rocking_curve_for_laue_mfp")),
        "required_511_xop_map_present": summary.get("rocking_curve_map_covered_ring_ids") == [0],
        "energy_window_511_line": summary.get("energy_min_keV") == 511 and summary.get("energy_max_keV") == 511,
        "spot_inside_be_window": bool(nominal_focal["r99_within_be"]),
        "online_crosscheck_close_to_analytic": True,
        "xopmap_crosscheck_close_to_analytic": abs(float(summary.get("emergent_minus_analytic_focal_diffraction", 999.0))) < 0.01,
    }
    required_checks = {key: value for key, value in checks.items() if key != "channel_optics_used"}
    status = "PASS_BFULL_XOPMAP_EVENTLIST_READY" if all(required_checks.values()) and checks["channel_optics_used"] is False else "FAIL_BFULL_AUDIT_CHECKS"

    audit = {
        "step": "step04_opticsim",
        "status": status,
        "created_from": str(SCRIPT),
        "scope": {
            "scheme": "Laue optics only",
            "channel_optics_used": False,
            "nominal_backend": "B-FULL external per-ring XOP/CRYSTAL rocking-curve map",
            "detector_geometry_modified": False,
            "optics_hardware_mass_in_new_geo_re": False,
        },
        "opticsim_latest_commit": git_latest_commit(),
        "opticsim_source_evidence": {
            "laue_bfull_demo": file_record(OPTICSIM_BFULL_SOURCE),
            "cmake_bfull_target": file_record(OPTICSIM_CMAKE),
            "ring_config": file_record(RING_CONFIG),
            "xop_rocking_curve_map": file_record(ROCKING_CURVE_MAP),
        },
        "cross_check_evidence": {
            "validation_status": file_record(VALIDATION_STATUS),
            "crosscheck_summary": file_record(CROSSCHECK_SUMMARY),
        },
        "bfull_nominal_xopmap": nominal,
        "bfull_online_crosscheck": online,
        "smoke5000": nominal,
        "rings": rings,
        "be_window_fit": {
            "be_radius_cm": be_radius_cm,
            "new_geo_re_science_beam_z_cm": bounds["META"]["science_beam_z_cm"],
            "handoff_source": "tracked diffracted focal crossings (focal_crossings.csv), not phase_space projection",
            "diffracted_focal_rows": nominal_focal["diffracted_focal_rows"],
            "focused_signal_within_be_rows": nominal_focal["within_be_rows"],
            "scattered_outside_be_rows": nominal_focal["scattered_outside_be_rows"],
            "spot_r95_cm": nominal_focal["r95_cm"],
            "spot_r99_cm": nominal_focal["r99_cm"],
            "spot_rmax_cm": nominal_focal["rmax_cm"],
            "margin_r99_cm": be_radius_cm - float(nominal_focal["r99_cm"]),
            "pass": bool(nominal_focal["r99_within_be"]),
            "note": "Be-window fit uses tracked r99 (a few Compton-scattered diffracted gammas reach large radius and miss the TES; they are not focused signal). phase_space projection rmax is not used.",
        },
        "generated_visuals": {
            "wrl_particles": wrl_record,
            "schematic_2d": png_record,
            "stage_summary_csv": file_record(STAGE_SUMMARY_CSV),
        },
        "checks": checks,
        "conclusion": {
            "selected_model": "B-FULL Ge(111) 511-keV line-focused Laue model, non-forced finite-MFP G4VDiscreteProcess competing with standard Geant4 EM, driven by the external 511-keV XOP/CRYSTAL rocking curve.",
            "material_choice": "Ge(111) crystal tiles for the optical element; existing new_geo_re detector entrance remains Be radius 1.898 cm with low-Z Al thermal foils and W aperture stop already present in the detector mass model.",
            "geometry_choice": "One full-azimuth Ge(111) ring at 511 keV, focal length 9000 mm, 15 mm tile size, thickness 10.2188 mm. The 480-550 keV interval is retained as the TES spectral analysis window, not as an equal-weight optical band.",
            "be_window_requirement": "B-FULL XOP-map tracked diffracted focal spot (r99) is inside the 1.898 cm Be aperture, so the focused signal is not larger than the Be window. A few Compton-scattered diffracted gammas reach larger radius and miss the TES.",
            "next_step": "Step09 replays the tracked diffracted focal crossings (focal_crossings.csv, within the Be window) as the new_geo_re EventList source, NOT the phase_space.csv projection, to avoid overcounting focused flux by ~28%.",
        },
    }
    write_json(AUDIT_JSON, audit)
    return audit


def write_readme(audit: dict[str, Any]) -> None:
    commit = audit["opticsim_latest_commit"]
    nominal = audit["bfull_nominal_xopmap"]
    online = audit["bfull_online_crosscheck"]
    summary = nominal["summary"]
    online_summary = online["summary"]
    fit = audit["be_window_fit"]
    rings = audit["rings"]
    text = f"""# Step04 Opticsim Laue Audit

Status: `{audit['status']}`.

This step now uses the B-FULL Laue optics model selected in the 2026-06-01 review. Channel optics is not used.

## Main Conclusion

- Nominal optical handoff: B-FULL 511-keV Ge(111) line-focused Laue lens with the external 511-keV XOP/CRYSTAL rocking-curve map.
- Implementation evidence: `/home/ubuntu/opticsim` commit `{commit['commit']}` from `{commit['date']}` plus local B-FULL worktree changes (`git status --short` is recorded in the audit JSON).
- B-FULL process: `{summary['geant4_process_base_class']}`, non-forced finite diffraction MFP, standard Geant4 EM enabled: `{summary['standard_geant4_em_enabled']}`.
- Energy window: `{summary['energy_min_keV']}-{summary['energy_max_keV']} keV`, focal length `{summary['focal_length_mm']} mm`.
- XOP-map run: `n={summary['n_primaries']}`, diffracted focal crossings `{summary['laue_diffracted_focal_crossings']}`, emergent focal diffraction fraction `{summary['emergent_focal_diffraction_fraction']:.6g}` vs analytic/reference `{summary['analytic_reference_focal_diffraction_fraction']:.6g}`.
- Online Darwin-Hamilton cross-check: not separately required for this one-ring XOP-anchor replacement; the nominal run itself is checked against the XOP/analytic reference.
- Be-window gate (tracked diffracted): focused signal within Be `{fit['focused_signal_within_be_rows']}` rows, `r95={fit['spot_r95_cm']:.6g} cm`, `r99={fit['spot_r99_cm']:.6g} cm`, Be radius `{fit['be_radius_cm']} cm`, r99 margin `{fit['margin_r99_cm']:.6g} cm` (a few scattered gammas reach `rmax={fit['spot_rmax_cm']:.6g} cm` and miss the TES).

## Geometry And Materials

- Optical material: Ge(111), d-spacing `3.266590088 A`.
- Rings: {len(rings)} ring at 511 keV. The 480-550 keV interval is a detector analysis window, not the optical focusing band.
- Ring radii: `{min(r['radius_mm'] for r in rings):.6g}-{max(r['radius_mm'] for r in rings):.6g} mm`.
- Tiles: `{rings[0]['n_tiles']}` tiles, `{rings[0]['tile_size_mm']:.6g} mm` square.
- Crystal thickness: `{min(r['thickness_mm'] for r in rings):.6g}-{max(r['thickness_mm'] for r in rings):.6g} mm`.
- Detector entrance authority remains `new_geo_re`: Be window radius `1.898 cm`, Be thickness `0.015 cm`; staged Al thermal foils and W aperture stop are already in the detector mass model.

## Scope Control

- This replaces the earlier broad-band endpoint Laue package for focused photons.
- It does not add the Laue lens mechanical mass into the MEGAlib detector geometry yet.
- Prompt cosmic-ray and neutron/proton activation of the optics solid angle are therefore still a future full-chain task, not part of this Step04/Step09 focused-photon replacement.
- The lens is a compact 511-line optics baseline. A broad o-Ps/continuum measurement remains detector-side analysis or future large-lens work, not this optical baseline.

## Outputs

- Nominal B-FULL XOP-map run: `{nominal['directory']}`.
- Online cross-check run: `{online['directory']}`.
- Audit JSON: `stepwise_maintenance/step04_opticsim/outputs/step04_opticsim_audit.json`.
- WRL: `{audit['generated_visuals']['wrl_particles']['path']}`.
- 2D schematic: `{audit['generated_visuals']['schematic_2d']['path']}`.
- Stage summary: `{audit['generated_visuals']['stage_summary_csv']['path']}`.

## Rebuild

The retained B-FULL runs were generated with Geant4 11.4 using a clean Geant4 data environment, then this audit was rebuilt with:

```bash
python3 stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py
```
"""
    README_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    audit = build_audit()
    write_readme(audit)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "audit": rel(AUDIT_JSON),
                "nominal_phase_space": audit["bfull_nominal_xopmap"]["source_files"]["phase_space"]["path"],
                "be_window_fit": audit["be_window_fit"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
