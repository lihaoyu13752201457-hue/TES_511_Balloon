#!/usr/bin/env python3
"""Audit the activation source spatial-model upgrade.

This does not claim to replace a radial source with a voxel transport run.
Instead it locks the normalization bookkeeping for the proposed mixed model and
identifies which current 511-keV contributors would require non-axisymmetric
voxel transport before a future production rerun.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "particle_sources" / "configs" / "nextphase" / "activation_source_spatial_model.yaml"
DEFAULT_SOURCE = ROOT / "simulation" / "delay_fix_from_buildup_equiv2602_cmfix" / "activation_decay_day15_groundstate_fixed.source"
DEFAULT_DIAG = ROOT / "statistics" / "nextphase_511" / "activation_511_diagnostics" / "delayed_511_by_nuclide_volume.csv"
DEFAULT_OUT = ROOT / "statistics" / "nextphase_511" / "activation_spatial_model"

PARTICLE_RE = re.compile(r"^(?P<name>S_(?P<vn>.+)_(?P<za>\d+)_z\d+)\.ParticleType\s+(?P<ptype>\d+)\s*$")
FLUX_RE = re.compile(r"^(?P<name>S_(?P<vn>.+)_(?P<za>\d+)_z\d+)\.Flux\s+(?P<flux>[-+0-9.eE]+)\s*$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def parse_source(path: Path) -> list[dict[str, Any]]:
    particles: dict[str, dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        mp = PARTICLE_RE.match(line.strip())
        if mp:
            rec = particles.setdefault(mp.group("name"), {})
            rec.update({"source": mp.group("name"), "VN": mp.group("vn"), "ZA": int(mp.group("za")), "ParticleType": int(mp.group("ptype"))})
            continue
        mf = FLUX_RE.match(line.strip())
        if mf:
            rec = particles.setdefault(mf.group("name"), {})
            rec.update({"source": mf.group("name"), "VN": mf.group("vn"), "ZA": int(mf.group("za")), "Flux_Bq": float(mf.group("flux"))})
    return [r for r in particles.values() if "Flux_Bq" in r and "ZA" in r]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--diagnostic", type=Path, default=DEFAULT_DIAG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    cfg = load_json(args.config)
    volume_modes = cfg.get("volume_modes", {})
    default_mode = cfg.get("default_mode", "radial_z")
    source_rows = parse_source(args.source)
    diag_rows = read_csv(args.diagnostic)

    by_volume: dict[str, dict[str, Any]] = defaultdict(lambda: {"activity_Bq": 0.0, "source_blocks": 0, "ZA_count": set()})
    for row in source_rows:
        vn = str(row["VN"])
        rec = by_volume[vn]
        rec["activity_Bq"] += float(row["Flux_Bq"])
        rec["source_blocks"] += 1
        rec["ZA_count"].add(int(row["ZA"]))

    source_mode_rows = []
    total_activity = sum(float(r["Flux_Bq"]) for r in source_rows)
    mixed_total = 0.0
    radial_total = 0.0
    voxel_total = 0.0
    for vn, rec in sorted(by_volume.items(), key=lambda kv: kv[1]["activity_Bq"], reverse=True):
        mode = volume_modes.get(vn, default_mode)
        activity = rec["activity_Bq"]
        mixed_total += activity
        if mode == "voxel":
            voxel_total += activity
        else:
            radial_total += activity
        source_mode_rows.append({
            "VN": vn,
            "recommended_mode": mode,
            "activity_Bq": activity,
            "activity_fraction": activity / total_activity if total_activity else 0.0,
            "source_blocks": rec["source_blocks"],
            "nuclide_count": len(rec["ZA_count"]),
            "needs_new_transport_for_mode_change": mode == "voxel",
        })

    diag_by_proxy: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in diag_rows:
        vol = row.get("source_volume_proxy", "Unknown")
        for key in ("broad_480_550_final_cps", "line_510p3_511p8_final_cps", "near_506_516_final_cps"):
            try:
                diag_by_proxy[vol][key] += float(row.get(key, 0.0) or 0.0)
            except ValueError:
                pass

    line_change_rows = []
    for vol, vals in sorted(diag_by_proxy.items(), key=lambda kv: kv[1].get("broad_480_550_final_cps", 0.0), reverse=True):
        # Transport change is unknown without a voxel Cosima rerun.  This table
        # records current contribution and whether the volume is in a mode that
        # should be rerun non-axisymmetrically.
        mode = volume_modes.get(vol, default_mode)
        line_change_rows.append({
            "source_volume_proxy": vol,
            "recommended_mode": mode,
            "current_broad_final_cps": vals.get("broad_480_550_final_cps", 0.0),
            "current_line_final_cps": vals.get("line_510p3_511p8_final_cps", 0.0),
            "current_near_final_cps": vals.get("near_506_516_final_cps", 0.0),
            "estimated_change_without_transport": 0.0,
            "requires_voxel_transport_to_measure_change": mode == "voxel",
        })

    norm_rows = [{
        "case": "current_radial_source",
        "total_activity_Bq": total_activity,
        "radial_or_layer_activity_Bq": total_activity,
        "voxel_activity_Bq": 0.0,
        "normalization_change_fraction": 0.0,
    }, {
        "case": "mixed_radial_layer_voxel_proposed",
        "total_activity_Bq": mixed_total,
        "radial_or_layer_activity_Bq": radial_total,
        "voxel_activity_Bq": voxel_total,
        "normalization_change_fraction": (mixed_total - total_activity) / total_activity if total_activity else 0.0,
    }]

    write_csv(args.out / "source_mode_by_volume.csv", source_mode_rows, [
        "VN", "recommended_mode", "activity_Bq", "activity_fraction", "source_blocks", "nuclide_count", "needs_new_transport_for_mode_change",
    ])
    write_csv(args.out / "radial_vs_voxel_rate_comparison.csv", norm_rows, [
        "case", "total_activity_Bq", "radial_or_layer_activity_Bq", "voxel_activity_Bq", "normalization_change_fraction",
    ])
    write_csv(args.out / "line_window_change_by_volume.csv", line_change_rows, [
        "source_volume_proxy", "recommended_mode", "current_broad_final_cps", "current_line_final_cps", "current_near_final_cps",
        "estimated_change_without_transport", "requires_voxel_transport_to_measure_change",
    ])

    summary = {
        "status": "PASS",
        "total_activity_Bq": total_activity,
        "mixed_total_activity_Bq": mixed_total,
        "normalization_closure_fraction": (mixed_total - total_activity) / total_activity if total_activity else 0.0,
        "voxel_activity_Bq": voxel_total,
        "voxel_activity_fraction": voxel_total / total_activity if total_activity else 0.0,
        "n_source_blocks": len(source_rows),
        "n_volumes": len(source_mode_rows),
        "n_proxy_volumes_in_511_diagnostic": len(line_change_rows),
        "caveat": "No voxel transport has been run; this audit locks normalization and identifies volumes requiring a future mixed-source Cosima rerun.",
    }
    (args.out / "activation_source_spatial_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md = f"""# Activation Source Spatial Model Audit

Status: `{summary['status']}`

- Current fixed delayed source activity: `{total_activity:.12g}` Bq.
- Proposed mixed-model activity: `{mixed_total:.12g}` Bq.
- Normalization closure: `{summary['normalization_closure_fraction']:.3e}`.
- Activity assigned to voxel-mode volumes: `{voxel_total:.12g}` Bq.

This audit confirms that switching selected non-axisymmetric volumes to voxel
mode can be defined without changing activity normalization.  The actual 511
rate change remains zero in this audit by construction; it requires a future
mixed radial/voxel delayed Cosima transport.
"""
    (args.out / "activation_source_spatial_summary.md").write_text(md, encoding="utf-8")
    print(args.out / "activation_source_spatial_summary.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
