#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--heart-src", required=True, help="Path to a checked-out HEART source tree.")
    parser.add_argument("--out-dir", default=str(ROOT / "reports/heart_adapter_feasibility"))
    parser.add_argument(
        "--tile-table",
        default=str(ROOT / "benchmarks/reference_outputs/external_lens_oracle_tiles.csv"),
    )
    args = parser.parse_args()

    heart_src = Path(args.heart_src)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics = build_report(heart_src, Path(args.tile_table))
    (out_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "report.md").write_text(_markdown(metrics), encoding="utf-8")
    print(json.dumps({"ok": metrics["ok"], "out": str(out_dir)}, indent=2, sort_keys=True))
    return 0 if metrics["ok"] else 1


def build_report(heart_src: Path, tile_table: Path) -> dict[str, object]:
    files = {
        "start_docs": heart_src / "docs/files/start.rst",
        "flat_crystal": heart_src / "HEART/components/FlatCrystal.py",
        "ray_tracer": heart_src / "HEART/ray_tracer.py",
    }
    missing = [name for name, path in files.items() if not path.exists()]
    evidence = {} if missing else _source_evidence(files)
    geometry = _tile_geometry(tile_table)
    full_lens_runner_ready = False
    ok = not missing and all(item["found"] for item in evidence.values()) and geometry["ok"]
    return {
        "ok": ok,
        "status": "audited_not_directly_comparable" if ok else "needs_attention",
        "heart_source": str(heart_src),
        "heart_commit": _git_head(heart_src),
        "missing_files": missing,
        "full_lens_runner_ready": full_lens_runner_ready,
        "direct_heart_runner_is_current_lens_oracle": False,
        "reason": (
            "HEART's flat-crystal model uses the crystal surface normal as the mean mosaic "
            "crystallite/diffracting-plane normal, while the current Laue lens needs a "
            "mechanical slab normal separate from each tile's Ge(111) diffracting-plane normal."
        ),
        "required_adapter_capability": (
            "The external runner must map external_lens_oracle_tiles.csv ideal_plane_normal_* "
            "to the Ge(111) diffracting-plane normal independently of slab_normal_*."
        ),
        "source_evidence": evidence,
        "tile_geometry": geometry,
    }


def _source_evidence(files: dict[str, Path]) -> dict[str, dict[str, object]]:
    return {
        "flat_axis_n_is_surface_normal": _find_text(
            files["flat_crystal"],
            "Surface normal of the crystal",
        ),
        "miller_indices_do_not_define_orientation": _find_text(
            files["start_docs"],
            "used to calculate the Bragg angles and structure factors",
        ),
        "mosaic_distribution_centered_on_surface_normal": _find_text(
            files["start_docs"],
            "angle between the crystallite surface normal",
        ),
        "ray_tracer_reads_crystal_surface_normal": _find_text(
            files["ray_tracer"],
            "photon.c_norm[:] = get_crystal_normal(crystal, pos)",
        ),
        "ray_tracer_rotates_crystallite_from_surface_normal": _find_text(
            files["ray_tracer"],
            "rodrigues_rotation(k=cross(photon.c_norm, photon.ray)",
        ),
    }


def _find_text(path: Path, needle: str) -> dict[str, object]:
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if needle in line:
            return {
                "found": True,
                "file": _path_tail(path),
                "line": lineno,
                "needle": needle,
            }
    return {"found": False, "file": _path_tail(path), "line": None, "needle": needle}


def _tile_geometry(tile_table: Path) -> dict[str, object]:
    rows = _read_csv(tile_table)
    angles_deg = []
    focal_values = set()
    for row in rows:
        slab = _unit(
            (
                float(row["slab_normal_x"]),
                float(row["slab_normal_y"]),
                float(row["slab_normal_z"]),
            )
        )
        plane = _unit(
            (
                float(row["ideal_plane_normal_x"]),
                float(row["ideal_plane_normal_y"]),
                float(row["ideal_plane_normal_z"]),
            )
        )
        dot_abs = min(1.0, abs(_dot(slab, plane)))
        angles_deg.append(math.degrees(math.acos(dot_abs)))
        focal_values.add(round(float(row["focal_z_mm"]), 9))
    return {
        "ok": len(rows) == 360 and len(focal_values) == 1,
        "tile_rows": len(rows),
        "focal_z_mm": next(iter(focal_values)) if len(focal_values) == 1 else None,
        "min_abs_angle_slab_to_ideal_plane_normal_deg": min(angles_deg),
        "max_abs_angle_slab_to_ideal_plane_normal_deg": max(angles_deg),
        "mean_abs_angle_slab_to_ideal_plane_normal_deg": sum(angles_deg) / len(angles_deg),
        "interpretation": (
            "The current tile table intentionally separates slab_normal_* from ideal_plane_normal_*; "
            "their near-orthogonality is expected for this transmission Laue geometry."
        ),
    }


def _markdown(metrics: dict[str, object]) -> str:
    evidence = metrics["source_evidence"]
    geometry = metrics["tile_geometry"]
    lines = [
        "# HEART Adapter Feasibility",
        "",
        f"Status: `{metrics['status']}`",
        f"HEART commit checked: `{metrics['heart_commit']}`",
        f"Direct HEART runner ready as current-lens oracle: `{metrics['full_lens_runner_ready']}`",
        "",
        "## Finding",
        "",
        str(metrics["reason"]),
        "",
        "A comparable external full-lens run must keep the mechanical slab normal and the Ge(111) diffracting-plane normal independently controllable.",
        "",
        "## Source Evidence",
        "",
        "| evidence | found | source |",
        "|---|---:|---|",
    ]
    for name, item in evidence.items():
        source = f"{item['file']}:{item['line']}" if item["line"] else item["file"]
        lines.append(f"| `{name}` | `{item['found']}` | `{source}` |")
    lines.extend(
        [
            "",
            "## Tile Geometry",
            "",
            f"- tile rows: `{geometry['tile_rows']}`",
            f"- focal z: `{geometry['focal_z_mm']} mm`",
            f"- min slab-vs-plane-normal angle: `{geometry['min_abs_angle_slab_to_ideal_plane_normal_deg']:.6f} deg`",
            f"- max slab-vs-plane-normal angle: `{geometry['max_abs_angle_slab_to_ideal_plane_normal_deg']:.6f} deg`",
            "",
            "## Required Next Step",
            "",
            str(metrics["required_adapter_capability"]),
            "",
        ]
    )
    return "\n".join(lines)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _git_head(path: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def _path_tail(path: Path) -> str:
    parts = path.parts
    if "HEART" in parts:
        return str(Path(*parts[parts.index("HEART") + 1 :]))
    return str(path)


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(v: tuple[float, float, float]) -> tuple[float, float, float]:
    n = math.sqrt(_dot(v, v))
    return (v[0] / n, v[1] / n, v[2] / n)


if __name__ == "__main__":
    raise SystemExit(main())
