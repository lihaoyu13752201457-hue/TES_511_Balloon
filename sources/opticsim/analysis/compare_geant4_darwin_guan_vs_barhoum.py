#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_per_ring(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def compare(guan_dir: Path, barhoum_dir: Path, out_dir: Path) -> dict[str, Any]:
    guan = read_json(guan_dir / "summary.json")
    barhoum = read_json(barhoum_dir / "summary.json")
    guan_rings = read_per_ring(guan_dir / "per_ring_summary.csv")
    barhoum_rings = {int(row["ring_id"]): row for row in read_per_ring(barhoum_dir / "per_ring_summary.csv")}
    rows: list[dict[str, Any]] = []
    max_mean_delta = 0.0
    max_sample_delta = 0.0
    for row in guan_rings:
        ring_id = int(row["ring_id"])
        ref = barhoum_rings[ring_id]
        mean_delta = float(row["mean_p_diff"]) - float(ref["mean_p_diff"])
        sample_delta = float(row["diffraction_fraction"]) - float(ref["diffraction_fraction"])
        max_mean_delta = max(max_mean_delta, abs(mean_delta))
        max_sample_delta = max(max_sample_delta, abs(sample_delta))
        rows.append(
            {
                "ring_id": ring_id,
                "design_energy_keV": float(row["design_energy_keV"]),
                "guan_mean_p_diff": float(row["mean_p_diff"]),
                "barhoum_mean_p_diff": float(ref["mean_p_diff"]),
                "delta_mean_p_diff": mean_delta,
                "guan_diffraction_fraction": float(row["diffraction_fraction"]),
                "barhoum_diffraction_fraction": float(ref["diffraction_fraction"]),
                "delta_diffraction_fraction": sample_delta,
            }
        )

    summary = {
        "comparison": "compiled_geant4_darwin_guan_process_vs_barhoum_style_process",
        "guan_dir": str(guan_dir.relative_to(ROOT) if guan_dir.is_relative_to(ROOT) else guan_dir),
        "barhoum_dir": str(barhoum_dir.relative_to(ROOT) if barhoum_dir.is_relative_to(ROOT) else barhoum_dir),
        "n_primaries_guan": guan["n_primaries"],
        "n_primaries_barhoum": barhoum["n_primaries"],
        "guan_model": guan["model"],
        "barhoum_model": barhoum["model"],
        "guan_registered_process": guan.get("registered_process"),
        "guan_registered_in_geant4_em_category": guan.get("registered_in_geant4_em_category"),
        "barhoum_diffraction_fraction": barhoum["diffraction_fraction"],
        "guan_diffraction_fraction": guan["diffraction_fraction"],
        "delta_diffraction_fraction": guan["diffraction_fraction"] - barhoum["diffraction_fraction"],
        "barhoum_absorption_fraction": barhoum["absorption_fraction"],
        "guan_absorption_fraction": guan["absorption_fraction"],
        "delta_absorption_fraction": guan["absorption_fraction"] - barhoum["absorption_fraction"],
        "barhoum_transmission_fraction": barhoum["transmission_fraction"],
        "guan_transmission_fraction": guan["transmission_fraction"],
        "delta_transmission_fraction": guan["transmission_fraction"] - barhoum["transmission_fraction"],
        "barhoum_spot_d90_cm": barhoum["spot_d90_cm"],
        "guan_spot_d90_cm": guan["spot_d90_cm"],
        "delta_spot_d90_cm": guan["spot_d90_cm"] - barhoum["spot_d90_cm"],
        "max_abs_delta_mean_p_diff_by_ring": max_mean_delta,
        "max_abs_delta_sampled_diffraction_fraction_by_ring": max_sample_delta,
        "guan_uses_external_efficiency_table_for_physics": guan.get("uses_external_efficiency_table_for_physics"),
        "guan_online_physics_backend": guan.get("online_physics_backend"),
        "interpretation": (
            "The Guan/Reiazi-style compiled C++ process uses the same Ge(111) geometry as the Barhoum-style "
            "baseline, but computes Darwin-Hamilton mosaic probabilities online instead of reading the 01 "
            "pAbs/pDiff/pTrans efficiency table. Mean p_diff agreement now tests online-model closure against "
            "the table-driven baseline; sampled branch fractions include normal Monte Carlo fluctuation."
        ),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "barhoum_comparison_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (out_dir / "barhoum_comparison_per_ring.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_markdown(out_dir / "GEANT4_DARWIN_GUAN_PROCESS_VS_BARHOUM.md", summary, rows)
    return summary


def write_markdown(path: Path, summary: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Compiled Geant4 Darwin/Guan-style Process vs Barhoum-style Process",
        "",
        "## Geant4 底层原理",
        "",
        "Geant4 tracking 通过 `G4ProcessManager` 调用每个 process 的 GPIL/DoIt 接口。"
        "Barhoum-style 和本 Guan-style executable 都是真实编译运行的 `G4VDiscreteProcess`，"
        "并通过 gamma 的 process manager 参与 tracking。",
        "",
        "区别在于物理后端和代码组织：Barhoum-style process 直接在 `PostStepDoIt` 内查 01 概率表；"
        "Guan/Reiazi-style process 把在线 Darwin-Hamilton/Bragg 判断拆到 `GuanDarwinDynamicalModel`，"
        "`GuanStyleLaueBraggProcess` 只负责 Geant4 step 条件、branch sampling 和 secondary 生成。",
        "",
        "## Summary",
        "",
        f"- Guan-style compiled process: `{summary['guan_model']}`",
        f"- Barhoum-style process: `{summary['barhoum_model']}`",
        f"- Guan registered process: `{summary['guan_registered_process']}`",
        f"- Guan registered in Geant4 EM category: `{summary['guan_registered_in_geant4_em_category']}`",
        f"- Guan uses 01 efficiency table for physics: `{summary['guan_uses_external_efficiency_table_for_physics']}`",
        f"- Guan online backend: `{summary['guan_online_physics_backend']}`",
        f"- Diffraction fraction: Guan `{summary['guan_diffraction_fraction']:.6f}`, Barhoum `{summary['barhoum_diffraction_fraction']:.6f}`, delta `{summary['delta_diffraction_fraction']:+.6f}`",
        f"- Absorption fraction: Guan `{summary['guan_absorption_fraction']:.6f}`, Barhoum `{summary['barhoum_absorption_fraction']:.6f}`, delta `{summary['delta_absorption_fraction']:+.6f}`",
        f"- Transmission fraction: Guan `{summary['guan_transmission_fraction']:.6f}`, Barhoum `{summary['barhoum_transmission_fraction']:.6f}`, delta `{summary['delta_transmission_fraction']:+.6f}`",
        f"- Spot D90: Guan `{summary['guan_spot_d90_cm']:.6f} cm`, Barhoum `{summary['barhoum_spot_d90_cm']:.6f} cm`, delta `{summary['delta_spot_d90_cm']:+.6f} cm`",
        f"- Max per-ring mean p_diff delta: `{summary['max_abs_delta_mean_p_diff_by_ring']:.6e}`",
        "",
        "## Per-ring p_diff",
        "",
        "| ring | keV | Guan mean p_diff | Barhoum mean p_diff | delta |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['ring_id']} | {row['design_energy_keV']:.0f} | {row['guan_mean_p_diff']:.6f} | "
            f"{row['barhoum_mean_p_diff']:.6f} | {row['delta_mean_p_diff']:+.3e} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This is a compiled C++/Geant4 model/process split implementation, not a copy of Guan/Reiazi source code. "
            "It is registered as an application-level discrete process for gamma, not as a Geant4 toolkit EM-category patch. "
            "The 02 backend no longer reads the 01 branch-probability CSV during tracking; it still uses compact Ge(111) "
            "attenuation/extinction constants anchored to the local validation chain, so a direct XOP reproduction remains "
            "the next publication-grade check.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def resolve(path: str) -> Path:
    out = Path(path)
    return out if out.is_absolute() else ROOT / out


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare compiled Guan-style Geant4 Laue process with Barhoum-style output.")
    parser.add_argument("--guan-dir", default="runs/geant4_laue_darwin_guan_process")
    parser.add_argument("--barhoum-dir", default="runs/geant4_laue_multiring_darwin")
    parser.add_argument("--out", default="runs/geant4_laue_darwin_guan_process")
    args = parser.parse_args()
    summary = compare(resolve(args.guan_dir), resolve(args.barhoum_dir), resolve(args.out))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
