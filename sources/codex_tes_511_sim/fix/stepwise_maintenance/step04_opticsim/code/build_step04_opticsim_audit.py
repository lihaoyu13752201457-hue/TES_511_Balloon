#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT = Path(__file__).resolve()
STEP_DIR = SCRIPT.parents[1]
FIX_ROOT = SCRIPT.parents[3]
OUTPUT_DIR = STEP_DIR / "outputs"
SMOKE_DIR = OUTPUT_DIR / "opticsim_laue_guan_smoke5000"
OPTICSIM_ROOT = Path("/home/ubuntu/opticsim")

OPTICSIM_LAUE_SOURCE = OPTICSIM_ROOT / "geant4_app/src/laue_multiring_darwin_guan_demo.cc"
OPTICSIM_LAUE_README = OPTICSIM_ROOT / "systems/laue/README.md"
OPTICSIM_GUAN_README = OPTICSIM_ROOT / "systems/laue_darwin_guan/README.md"
RING_CONFIG = OPTICSIM_ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv"

BRIDGE_SUITE = FIX_ROOT / "particle_sources/run_configs/opticsim_bridge/current_source_suite.json"
BRIDGE_CASES = FIX_ROOT / "particle_sources/run_configs/opticsim_bridge/opticsim_bridge_cases.json"
BRIDGE_TOOL = FIX_ROOT / "tools/opticsim_phase_space_bridge.py"
LAUE_BRIDGE_SOURCE = FIX_ROOT / "particle_sources/run_configs/opticsim_bridge/Opticsim_laue_multiring_science.source"
LAUE_BRIDGE_SMOKE = FIX_ROOT / "particle_sources/run_configs/opticsim_bridge/Opticsim_laue_multiring_science_smoke1000.source"
LAUE_EVENTLIST = FIX_ROOT / "sources/opticsim_bridge/laue_multiring_science/Opticsim_laue_multiring_science.eventlist.dat"

V404_CASES = FIX_ROOT / "particle_sources/configs/astro_source_cases/source_cases_511_ABC_v2.yaml"
V404_ANCHORS = FIX_ROOT / "particle_sources/configs/astro_source_cases/literature_flux_anchors.yaml"
V404_SOURCE_CARDS = [
    FIX_ROOT / "particle_sources/run_configs/astro_cases/Science511_C_V404_v404_kT30_no_shift.source",
    FIX_ROOT / "particle_sources/run_configs/astro_cases/Science511_C_V404_v404_redshift_z0p10_narrow_proxy.source",
]
V404_SPECTRA_DIR = FIX_ROOT / "sources/astro_spectra_511"

AUDIT_JSON = OUTPUT_DIR / "step04_opticsim_audit.json"
WRL_PATH = OUTPUT_DIR / "laue_smoke5000_particles.wrl"
PNG_PATH = OUTPUT_DIR / "laue_smoke5000_2d_schematic.png"
STAGE_SUMMARY_CSV = OUTPUT_DIR / "laue_smoke5000_stage_summary.csv"
README_PATH = STEP_DIR / "README.md"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(FIX_ROOT))
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value == "":
        return default
    return float(value)


def as_int(row: dict[str, str], key: str, default: int = 0) -> int:
    value = row.get(key, "")
    if value == "":
        return default
    return int(float(value))


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


def file_record(path: Path) -> dict[str, object]:
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


def git_latest_commit() -> dict[str, object]:
    lines = run_git(["log", "-1", "--format=%H%n%ci%n%s"]).splitlines()
    status = run_git(["status", "--short", "--untracked-files=no"])
    return {
        "repo": str(OPTICSIM_ROOT),
        "commit": lines[0] if len(lines) > 0 else "",
        "date": lines[1] if len(lines) > 1 else "",
        "subject": lines[2] if len(lines) > 2 else "",
        "tracked_worktree_clean": status == "",
        "tracked_status_short": status,
    }


def read_ring_config(path: Path) -> list[dict[str, object]]:
    rings: list[dict[str, object]] = []
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
            }
        )
    return rings


def vec(row: dict[str, str], prefix: str) -> tuple[float, float, float]:
    if prefix == "pos":
        return as_float(row, "x_mm"), as_float(row, "y_mm"), as_float(row, "z_mm")
    return as_float(row, f"ux_{prefix}"), as_float(row, f"uy_{prefix}"), as_float(row, f"uz_{prefix}")


def normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if n <= 0.0:
        return 0.0, 0.0, 1.0
    return v[0] / n, v[1] / n, v[2] / n


def add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] + b[0], a[1] + b[1], a[2] + b[2]


def sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def mul(v: tuple[float, float, float], s: float) -> tuple[float, float, float]:
    return v[0] * s, v[1] * s, v[2] * s


def endpoint_maps(rows: list[dict[str, str]]) -> dict[int, tuple[float, float, float]]:
    return {as_int(row, "event_id"): vec(row, "pos") for row in rows}


def forward_to_z(
    pos: tuple[float, float, float],
    direction: tuple[float, float, float],
    target_z: float,
    fallback_length_mm: float,
) -> tuple[float, float, float]:
    d = normalize(direction)
    if abs(d[2]) > 1.0e-12:
        t = (target_z - pos[2]) / d[2]
        if t > 0.0 and math.isfinite(t):
            return add(pos, mul(d, t))
    return add(pos, mul(d, fallback_length_mm))


def segment_for_history(
    row: dict[str, str],
    phase_by_event: dict[int, tuple[float, float, float]],
    transmitted_by_event: dict[int, tuple[float, float, float]],
    focal_length_mm: float,
) -> tuple[
    tuple[tuple[float, float, float], tuple[float, float, float]],
    tuple[str, tuple[tuple[float, float, float], tuple[float, float, float]]],
]:
    event_id = as_int(row, "event_id")
    pos = vec(row, "pos")
    din = normalize(vec(row, "in"))
    dout = normalize(vec(row, "out"))
    stage = row.get("stage", "").strip().upper()
    incident = (sub(pos, mul(din, 500.0)), pos)

    if stage == "DIFFRACT":
        end = phase_by_event.get(event_id)
        if end is None:
            end = forward_to_z(pos, dout, focal_length_mm, 2000.0)
        return incident, ("DIFFRACT", (pos, end))
    if stage == "TRANSMIT":
        end = transmitted_by_event.get(event_id)
        if end is None:
            end = forward_to_z(pos, dout, focal_length_mm, 2000.0)
        return incident, ("TRANSMIT", (pos, end))
    end = add(pos, mul(din, 80.0))
    return incident, ("ABSORB", (pos, end))


def scaled(p: tuple[float, float, float]) -> tuple[float, float, float]:
    return p[0] * 0.1, p[1] * 0.1, p[2] * 0.1


def write_lineset(
    handle,
    name: str,
    segments: list[tuple[tuple[float, float, float], tuple[float, float, float]]],
    color: tuple[float, float, float],
    transparency: float = 0.0,
) -> None:
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
        sx, sy, sz = scaled(start)
        ex, ey, ez = scaled(end)
        handle.write(f"      {sx:.6g} {sy:.6g} {sz:.6g}, {ex:.6g} {ey:.6g} {ez:.6g},\n")
    handle.write("    ] }\n")
    handle.write("    coordIndex [\n")
    for idx in range(len(segments)):
        handle.write(f"      {2 * idx}, {2 * idx + 1}, -1,\n")
    handle.write("    ]\n")
    handle.write("  }\n")
    handle.write("}\n\n")


def ring_segments(rings: list[dict[str, object]], focal_length_mm: float) -> dict[str, list]:
    out: dict[str, list] = {"RINGS": [], "FOCAL": []}
    for ring in rings:
        radius = float(ring["radius_mm"])
        z = 0.0
        points = 180
        for idx in range(points):
            a0 = 2.0 * math.pi * idx / points
            a1 = 2.0 * math.pi * (idx + 1) / points
            p0 = (radius * math.cos(a0), radius * math.sin(a0), z)
            p1 = (radius * math.cos(a1), radius * math.sin(a1), z)
            out["RINGS"].append((p0, p1))
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


def write_wrl(
    path: Path,
    histories: list[dict[str, str]],
    phase_rows: list[dict[str, str]],
    transmitted_rows: list[dict[str, str]],
    rings: list[dict[str, object]],
    summary: dict,
) -> dict[str, object]:
    phase_by_event = endpoint_maps(phase_rows)
    transmitted_by_event = endpoint_maps(transmitted_rows)
    focal = float(summary.get("focal_length_mm", 8300.0))
    incident_segments = []
    outcome_segments: dict[str, list] = {"DIFFRACT": [], "TRANSMIT": [], "ABSORB": []}
    for row in histories:
        incident, (stage, outcome) = segment_for_history(row, phase_by_event, transmitted_by_event, focal)
        incident_segments.append(incident)
        outcome_segments.setdefault(stage, []).append(outcome)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("#VRML V2.0 utf8\n")
        handle.write("WorldInfo {\n")
        handle.write('  title "Step04 Laue opticsim smoke5000 particle audit"\n')
        handle.write("  info [\n")
        handle.write(f'    "histories_used={len(histories)}"\n')
        handle.write(f'    "incident_segments={len(incident_segments)}"\n')
        handle.write(f'    "diffracted_segments={len(outcome_segments.get("DIFFRACT", []))}"\n')
        handle.write(f'    "transmitted_segments={len(outcome_segments.get("TRANSMIT", []))}"\n')
        handle.write(f'    "absorbed_segments={len(outcome_segments.get("ABSORB", []))}"\n')
        handle.write('    "coordinates are opticsim mm scaled by 0.1 for display"\n')
        handle.write("  ]\n")
        handle.write("}\n")
        handle.write('NavigationInfo { type [ "EXAMINE", "ANY" ] }\n')
        handle.write("Background { skyColor [ 0.02 0.025 0.03 ] }\n\n")
        write_lineset(handle, "INCIDENT_5000", incident_segments, (0.17, 0.46, 0.95), 0.55)
        write_lineset(handle, "DIFFRACTED_TO_FOCUS", outcome_segments["DIFFRACT"], (0.96, 0.18, 0.12), 0.15)
        write_lineset(handle, "TRANSMITTED_TO_FOCAL_PLANE", outcome_segments["TRANSMIT"], (0.70, 0.72, 0.75), 0.35)
        write_lineset(handle, "ABSORBED_SHORT_STUBS", outcome_segments["ABSORB"], (1.0, 0.62, 0.10), 0.2)
        guide_segments = ring_segments(rings, focal)
        write_lineset(handle, "LAUE_RING_GUIDES", guide_segments["RINGS"], (0.2, 0.85, 0.62), 0.05)
        write_lineset(handle, "FOCAL_PLANE_MARKER", guide_segments["FOCAL"], (0.95, 0.92, 0.45), 0.0)

    return {
        "path": rel(path),
        "histories_used": len(histories),
        "incident_segments": len(incident_segments),
        "outcome_segments_by_stage": {stage: len(items) for stage, items in sorted(outcome_segments.items())},
        "guide_segments": {stage: len(items) for stage, items in guide_segments.items()},
        "coordinate_display_scale": "x,y,z = opticsim_mm * 0.1",
        "line_count": line_count(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def write_2d_schematic(
    path: Path,
    histories: list[dict[str, str]],
    phase_rows: list[dict[str, str]],
    transmitted_rows: list[dict[str, str]],
    rings: list[dict[str, object]],
    summary: dict,
) -> dict[str, object]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    phase_by_event = endpoint_maps(phase_rows)
    transmitted_by_event = endpoint_maps(transmitted_rows)
    focal = float(summary.get("focal_length_mm", 8300.0))
    colors = {
        "DIFFRACT": "#d73027",
        "TRANSMIT": "#6b7280",
        "ABSORB": "#f59e0b",
    }

    fig, ax = plt.subplots(figsize=(11.0, 6.6), dpi=180)
    for row in histories:
        incident, (stage, outcome) = segment_for_history(row, phase_by_event, transmitted_by_event, focal)
        for a, b, color, alpha, lw in [
            (incident[0], incident[1], "#2b6cb0", 0.035, 0.35),
            (outcome[0], outcome[1], colors.get(stage, "#111827"), 0.055 if stage != "DIFFRACT" else 0.08, 0.45),
        ]:
            za = a[2] / 1000.0
            zb = b[2] / 1000.0
            ra = math.hypot(a[0], a[1])
            rb = math.hypot(b[0], b[1])
            ax.plot([za, zb], [ra, rb], color=color, alpha=alpha, linewidth=lw)

    for ring in rings:
        radius = float(ring["radius_mm"])
        ax.scatter([0.0], [radius], s=16, color="#059669", zorder=5)
        ax.text(0.05, radius + 0.7, f"R{ring['ring_id']} {ring['design_energy_keV']:.0f} keV", fontsize=7, color="#065f46")

    ax.axvline(0.0, color="#111827", linewidth=0.9, alpha=0.65)
    ax.axvline(focal / 1000.0, color="#7c2d12", linewidth=0.9, alpha=0.65)
    ax.text(0.02, 2.0, "Laue rings", fontsize=8, color="#111827")
    ax.text(focal / 1000.0 - 0.68, 2.0, "focal plane", fontsize=8, color="#7c2d12")
    ax.set_xlabel("z position (m)")
    ax.set_ylabel("radial distance from optical axis (mm)")
    ax.set_title("Step04 Laue opticsim smoke: 5000 histories, radial-z projection")
    ax.set_xlim(-0.56, focal / 1000.0 + 0.35)
    ax.set_ylim(0.0, max(float(r["radius_mm"]) for r in rings) + 18.0)
    ax.grid(True, color="#d1d5db", linewidth=0.45, alpha=0.7)

    legend_lines = [
        plt.Line2D([0], [0], color="#2b6cb0", lw=2, label="incident"),
        plt.Line2D([0], [0], color=colors["DIFFRACT"], lw=2, label="diffracted"),
        plt.Line2D([0], [0], color=colors["TRANSMIT"], lw=2, label="transmitted"),
        plt.Line2D([0], [0], color=colors["ABSORB"], lw=2, label="absorbed"),
    ]
    ax.legend(handles=legend_lines, loc="upper right", frameon=True, framealpha=0.92, fontsize=8)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path)
    plt.close(fig)

    return {
        "path": rel(path),
        "histories_used": len(histories),
        "projection": "radial distance r=sqrt(x^2+y^2) versus z, using opticsim mm converted to m for z labels",
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def summarize_stages(histories: list[dict[str, str]]) -> list[dict[str, object]]:
    by_key: defaultdict[tuple[str, int], int] = defaultdict(int)
    for row in histories:
        by_key[(row.get("stage", ""), as_int(row, "ring_id", -1))] += 1
    rows = []
    for (stage, ring_id), count in sorted(by_key.items()):
        rows.append({"stage": stage, "ring_id": ring_id, "histories": count})
    return rows


def parse_homogeneous_beam(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if ".Beam HomogeneousBeam " not in line:
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        return {
            "source_card": rel(path),
            "line": line,
            "x": float(parts[2]),
            "y": float(parts[3]),
            "z": float(parts[4]),
            "dx": float(parts[5]),
            "dy": float(parts[6]),
            "dz": float(parts[7]),
            "radius": float(parts[8]),
        }
    return None


def text_contains(path: Path, needle: str) -> bool:
    if not path.exists():
        return False
    return needle in path.read_text(encoding="utf-8", errors="ignore")


def build_audit() -> dict[str, object]:
    summary = read_json(SMOKE_DIR / "summary.json")
    histories = read_csv(SMOKE_DIR / "optics_history.csv")
    phase_rows = read_csv(SMOKE_DIR / "phase_space.csv")
    transmitted_rows = read_csv(SMOKE_DIR / "transmitted_space.csv")
    rings = read_ring_config(RING_CONFIG)

    stage_counter = Counter(row.get("stage", "") for row in histories)
    ring_counter = Counter(as_int(row, "ring_id", -1) for row in histories)
    stage_rows = summarize_stages(histories)
    write_csv(STAGE_SUMMARY_CSV, stage_rows, ["stage", "ring_id", "histories"])

    wrl_record = write_wrl(WRL_PATH, histories, phase_rows, transmitted_rows, rings, summary)
    png_record = write_2d_schematic(PNG_PATH, histories, phase_rows, transmitted_rows, rings, summary)

    bridge_evidence = {
        "current_suite": file_record(BRIDGE_SUITE),
        "bridge_cases": file_record(BRIDGE_CASES),
        "bridge_tool": file_record(BRIDGE_TOOL),
        "laue_bridge_source_card": file_record(LAUE_BRIDGE_SOURCE),
        "laue_bridge_smoke_source_card": file_record(LAUE_BRIDGE_SMOKE),
        "laue_eventlist_payload": file_record(LAUE_EVENTLIST),
        "interpretation": (
            "The fix archive contains Laue opticsim bridge manifests and source cards, "
            "but the referenced EventList payload and bridge tool are absent in this worktree. "
            "The current Step04 evidence therefore uses a fresh latest-commit opticsim Guan Laue smoke run."
        ),
    }

    v404_beams = [item for item in (parse_homogeneous_beam(path) for path in V404_SOURCE_CARDS) if item]
    v404_evidence = {
        "case_config": file_record(V404_CASES),
        "literature_anchors": file_record(V404_ANCHORS),
        "source_cards": [file_record(path) for path in V404_SOURCE_CARDS],
        "spectra_dir_exists": V404_SPECTRA_DIR.exists(),
        "contains_transient_point_source_handling": text_contains(V404_CASES, "transient_point_source_with_Aeff_E"),
        "contains_spi_v404_anchor": text_contains(V404_ANCHORS, "SPI_V404_ANNIHILATION_FEATURE"),
        "homogeneous_beams": v404_beams,
        "interpretation": (
            "V404 exists as a literature-anchored transient point-source benchmark and old post-optics "
            "HomogeneousBeam source cards. Those cards inject a focused beam at z=127.66 with radius 18.0, "
            "which is stale relative to the current cmfix Gate-A 12.766/1.8 convention and is not yet a "
            "latest-Laue EventList-coupled production source."
        ),
    }

    audit = {
        "step": "step04_opticsim",
        "status": "PASS_WITH_CAVEATS",
        "created_from": str(SCRIPT),
        "scope": {
            "scheme": "Laue optics only",
            "channel_optics_used": False,
            "opticsim_repo": str(OPTICSIM_ROOT),
        },
        "opticsim_latest_commit": git_latest_commit(),
        "opticsim_source_evidence": {
            "laue_guan_demo": file_record(OPTICSIM_LAUE_SOURCE),
            "laue_readme": file_record(OPTICSIM_LAUE_README),
            "laue_darwin_guan_readme": file_record(OPTICSIM_GUAN_README),
            "ring_config": file_record(RING_CONFIG),
        },
        "smoke5000": {
            "directory": rel(SMOKE_DIR),
            "summary": summary,
            "history_rows": len(histories),
            "phase_space_rows": len(phase_rows),
            "transmitted_rows": len(transmitted_rows),
            "stage_counts": dict(sorted(stage_counter.items())),
            "ring_counts": {str(k): v for k, v in sorted(ring_counter.items())},
            "stage_summary_csv": file_record(STAGE_SUMMARY_CSV),
            "source_files": {
                "optics_history": file_record(SMOKE_DIR / "optics_history.csv"),
                "phase_space": file_record(SMOKE_DIR / "phase_space.csv"),
                "transmitted_space": file_record(SMOKE_DIR / "transmitted_space.csv"),
                "summary_json": file_record(SMOKE_DIR / "summary.json"),
                "opticsim_internal_wrl": file_record(SMOKE_DIR / "laue_multiring_scene.wrl"),
            },
        },
        "rings": rings,
        "generated_visuals": {
            "wrl_5000_particles": wrl_record,
            "schematic_2d": png_record,
        },
        "bridge_evidence": bridge_evidence,
        "v404_source_basis": v404_evidence,
        "conclusion": {
            "opticsim_introduction_current_archive": "partial_bridge_scaffold_present_payload_absent",
            "latest_laue_smoke_available": True,
            "wrl_based_on_5000_smoke_histories": wrl_record["histories_used"] == 5000,
            "v404_basis_available": True,
            "v404_production_laue_coupling_available": False,
            "next_required_for_science_run": (
                "Generate a current EventList bridge from the latest Guan Laue phase_space.csv using the "
                "current detector coordinate convention before treating V404 or other science cases as "
                "production Laue-coupled detector sources."
            ),
        },
    }

    AUDIT_JSON.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_JSON.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return audit


def write_readme(audit: dict[str, object]) -> None:
    smoke = audit["smoke5000"]
    summary = smoke["summary"]
    commit = audit["opticsim_latest_commit"]
    visuals = audit["generated_visuals"]
    v404 = audit["v404_source_basis"]
    bridge = audit["bridge_evidence"]

    text = f"""# Step04 Opticsim Laue Audit

Status: `PASS_WITH_CAVEATS`.

This step answers the optics handoff questions after Step03. The selected scheme is Laue optics only; channel optics is not used here.

## Main Conclusion

- Step03 is complete. This directory is Step04.
- Latest opticsim Laue evidence is based on `/home/ubuntu/opticsim` commit `{commit['commit']}` from `{commit['date']}`: `{commit['subject']}`.
- The 5000-particle smoke run completed with `{summary['n_diffracted']}` diffracted, `{summary['n_transmitted']}` transmitted, and `{summary['n_absorbed']}` absorbed histories out of `{summary['n_primaries']}` primaries.
- The generated WRL at `{visuals['wrl_5000_particles']['path']}` uses all `{visuals['wrl_5000_particles']['histories_used']}` smoke histories. It is not the internal opticsim WRL, because the C++ demo intentionally caps its quick scene.
- The 2D schematic is `{visuals['schematic_2d']['path']}`.
- The fix archive has Laue opticsim bridge manifests/source cards, but the referenced EventList payload and bridge tool are absent in this worktree. So the present production detector source should not be described as already fully latest-Laue-coupled.
- V404 exists as a literature-anchored transient point-source benchmark, but the old V404 source cards are post-optics `HomogeneousBeam` cards and are stale relative to the current cmfix detector coordinate convention.

## Laue Principle

The opticsim run uses a five-ring Ge(111) Laue lens for the 480-550 keV band with focal length `{summary['focal_length_mm']}` mm. The latest demo is `geant4_app/src/laue_multiring_darwin_guan_demo.cc`. It registers `GuanStyleLaueBraggProcess` as a discrete gamma process and computes branch probabilities online through a Darwin-Hamilton mosaic model with virtual crystallite plane-normal sampling.

Important scope points:

- `uses_external_efficiency_table_for_physics = {str(summary['uses_external_efficiency_table_for_physics']).lower()}`.
- `geant4_bottom_code_modified = {str(summary['geant4_bottom_code_modified']).lower()}`.
- This is a compiled opticsim Geant4 application, not a Geant4 toolkit EM-category patch.
- The detector/Cosima coupling should be done by exporting focal-plane phase space and converting it to a MEGAlib EventList source; this Step04 did not silently substitute a channel-optics model.

## Files Produced

- `outputs/opticsim_laue_guan_smoke5000/`: fresh latest-commit opticsim smoke output.
- `{visuals['wrl_5000_particles']['path']}`: all 5000 histories as incident plus outcome line segments, with ring and focal-plane guides.
- `{visuals['schematic_2d']['path']}`: radial-z 2D projection of the same histories.
- `outputs/laue_smoke5000_stage_summary.csv`: stage by ring counts.
- `outputs/step04_opticsim_audit.json`: machine-readable evidence, hashes, and caveats.
- `SOURCE_MODEL_EXPLAINER.html`: visual source-model explanation for point,
  diffuse, prompt, delayed, atmosphere, and source-to-detector coupling.
- `outputs/source_model_smoke.wrl`: documentation-only source-model WRL smoke.

## Source Model Supplement

The source-model supplement is produced by:

```bash
python3 stepwise_maintenance/step04_opticsim/code/build_step04_source_model_explainer.py
```

It answers the current source-choice questions before the production EventList
bridge is built:

- The Laue lens mass model should be included in prompt cosmic-ray and delayed
  activation studies once it is ready for smoke transport, even if the mass
  optimization is not final.
- Prompt atmospheric gamma rays can be scattered or diffracted by the same
  material if their energy and direction satisfy the geometry; charged prompt
  particles are not focused, but they can create prompt hits and activation.
- Delayed activation is a local instrumental background from detector/lens
  material, not a far-field point source.  Its photons can still propagate or
  scatter through the optics/detector geometry.
- A V404 or compact-GC point source is a sky direction.  A far-field start
  sphere or entrance plane spreads Monte Carlo start positions over an aperture;
  it is not by itself the source's angular extent.
- Diffuse 511 keV emission is a sky intensity distribution over solid angle
  such as a bulge/disk model.  It is not physically "random over the whole
  downward plane", although a plane sampler can be used as a detector-side
  approximation after sky-to-aperture projection.
- Atmospheric transmission is already included in source-rate folding through
  `R = F_511 * A_opt * T_atm`; the fixed-trigger Cosima source card is not the
  physical flux normalization.

## V404 Source Basis

The current V404 basis is in:

- `{v404['case_config']['path']}`
- `{v404['literature_anchors']['path']}`
- `{v404['source_cards'][0]['path']}`
- `{v404['source_cards'][1]['path']}`

The config marks V404 as `transient_point_source_with_Aeff_E` and points to the `SPI_V404_ANNIHILATION_FEATURE` literature anchor. The old source cards replay it as a focused post-optics beam, for example:

```text
{v404['homogeneous_beams'][0]['line'] if v404['homogeneous_beams'] else 'no HomogeneousBeam line found'}
```

That is an old far-field-to-post-optics simplification: the sky point source was not transported through a current Laue lens in Cosima. It represented the result of an assumed effective-area optics response as a homogeneous beam entering the detector window. The z/r values `127.66/18.0` are the old 10x convention; the current cmfix Gate-A source convention is `12.766/1.8`. Also, `{rel(V404_SPECTRA_DIR)}` is absent, so those old V404 cards are not runnable as a current production payload without regenerating inputs.

## Bridge Status

The archive does contain opticsim bridge metadata:

- `{bridge['current_suite']['path']}`
- `{bridge['bridge_cases']['path']}`
- `{bridge['laue_bridge_source_card']['path']}`
- `{bridge['laue_bridge_smoke_source_card']['path']}`

But the local evidence is incomplete:

- Bridge tool exists: `{bridge['bridge_tool']['exists']}`.
- Referenced Laue EventList exists: `{bridge['laue_eventlist_payload']['exists']}`.

Therefore the honest Step04 conclusion is: Laue opticsim has been introduced as a scaffold/manifest and has now been re-smoked from the latest opticsim commit, but a current production science source still needs a fresh EventList bridge from the latest Guan Laue `phase_space.csv`.

## Function Summary

- `read_csv`, `read_json`: load smoke and config tables.
- `git_latest_commit`: records the exact opticsim commit and tracked worktree state.
- `file_record`: records existence, size, line count, and SHA-256 for evidence files.
- `read_ring_config`: parses the five-ring Ge(111) Laue lens configuration.
- `segment_for_history`: converts one opticsim history row into incident and outcome line segments.
- `write_wrl`: writes the 5000-history VRML scene.
- `write_2d_schematic`: writes the radial-z PNG schematic.
- `build_audit`: combines opticsim, bridge, V404, smoke, and visualization evidence into JSON.
- `write_readme`: writes this README from the audit result.
- `main`: runs the full Step04 audit generation.

## Rebuild

```bash
python3 stepwise_maintenance/step04_opticsim/code/build_step04_opticsim_audit.py
```
"""
    README_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    audit = build_audit()
    write_readme(audit)
    print(json.dumps({
        "audit": rel(AUDIT_JSON),
        "readme": rel(README_PATH),
        "wrl": rel(WRL_PATH),
        "png": rel(PNG_PATH),
        "histories_used": audit["generated_visuals"]["wrl_5000_particles"]["histories_used"],
    }, indent=2))


if __name__ == "__main__":
    main()
