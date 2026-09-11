#!/usr/bin/env python3
"""Build a 10-file GPT Pro package focused on geometry optimization direction."""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent

PREVIOUS_CLUE = ROOT / "engineering/geometry_optimization_20260704/07_clue_1p5e5_20260707"
COMPLEMENT = ROOT / "engineering/geometry_optimization_20260704/09_gpt_complement_ingress_veto_bpe_20260707"
OUT = ROOT / "engineering/geometry_optimization_20260704/10_gpt_geometry_optimization_direction_20260707"

FILES = {
    "01_README_AND_PROMPT.md",
    "02_fact_summary.json",
    "03_geometry_2d_detail.png",
    "04_geometry_3d_wrl.wrl",
    "05_geoopt_added_geometry_manifest.json",
    "06_geoopt_added_volumes.geo",
    "07_w2_particle_trajectories_enriched.csv",
    "08_w2_event_veto_flags.csv",
    "09_w2_entry_angle_veto_summary.csv",
    "10_plastic_bpe_neutron_effects.csv",
}


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_inputs() -> None:
    copies = [
        (PREVIOUS_CLUE / "geo_opt_s1_bottomw_b4c_2d_detail.png", OUT / "03_geometry_2d_detail.png"),
        (PREVIOUS_CLUE / "geo_opt_s1_bottomw_b4c.wrl", OUT / "04_geometry_3d_wrl.wrl"),
        (PREVIOUS_CLUE / "geoopt_added_geometry_manifest.json", OUT / "05_geoopt_added_geometry_manifest.json"),
        (PREVIOUS_CLUE / "geoopt_added_volumes.geo", OUT / "06_geoopt_added_volumes.geo"),
        (COMPLEMENT / "03_w2_particle_trajectories_enriched.csv", OUT / "07_w2_particle_trajectories_enriched.csv"),
        (COMPLEMENT / "07_w2_event_veto_flags.csv", OUT / "08_w2_event_veto_flags.csv"),
    ]
    for src, dst in copies:
        shutil.copyfile(src, dst)


def build_entry_angle_veto_summary() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for row in read_csv(COMPLEMENT / "04_w2_entry_geometry_counts.csv"):
        rows.append(
            {
                "record_type": "entry_class_count",
                "source_family": row["source_family"],
                "category": row["entry_class"],
                "subcategory": "",
                "bin_lo_deg": "",
                "bin_hi_deg": "",
                "count": row["count"],
                "fraction": row["share_within_particle"],
                "notes": row["definition"],
            }
        )

    for row in read_csv(COMPLEMENT / "05_w2_theta_phi_binned_counts.csv"):
        rows.append(
            {
                "record_type": f"{row['angle_kind']}_angle_bin_count",
                "source_family": row["source_family"],
                "category": row["entry_class"],
                "subcategory": row["angle_kind"],
                "bin_lo_deg": row["bin_lo_deg"],
                "bin_hi_deg": row["bin_hi_deg"],
                "count": row["count"],
                "fraction": "",
                "notes": "local detector-frame angle bin; see 02_fact_summary.json for theta/phi definition",
            }
        )

    for row in read_csv(COMPLEMENT / "06_w2_veto_cutflow_by_particle.csv"):
        raw = float(row["w2_raw_events"]) if row["w2_raw_events"] else 0.0
        for key, label in [
            ("plastic_skin_veto_events", "plastic_skin_veto"),
            ("non_plastic_active_veto_events", "non_plastic_active_veto"),
            ("compton_fov_veto_events", "compton_fov_veto"),
            ("final_pass_events", "final_pass"),
        ]:
            count = float(row[key])
            rows.append(
                {
                    "record_type": "veto_priority_cutflow",
                    "source_family": row["source_family"],
                    "category": label,
                    "subcategory": "",
                    "bin_lo_deg": "",
                    "bin_hi_deg": "",
                    "count": int(count),
                    "fraction": count / raw if raw else "",
                    "notes": "priority order: plastic skin, non-plastic active, Compton/FoV, final pass",
                }
            )

    write_csv(
        OUT / "09_w2_entry_angle_veto_summary.csv",
        rows,
        ["record_type", "source_family", "category", "subcategory", "bin_lo_deg", "bin_hi_deg", "count", "fraction", "notes"],
    )
    return rows


def build_effects_file() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for row in read_csv(COMPLEMENT / "08_plastic_skin_veto_effect.csv"):
        rows.append(
            {
                "record_type": "plastic_skin_effect",
                "topic": row["topic"],
                "metric": row["metric"],
                "source_family_or_local_id": "",
                "value": row["value"],
                "unit": row["unit"],
                "value_2": "",
                "unit_2": "",
                "context": row["count_or_rate_context"],
                "interpretation": row["interpretation"],
            }
        )

    for row in read_csv(COMPLEMENT / "09_bpe_neutron_activation_effect.csv"):
        rows.append(
            {
                "record_type": "bpe_shield_stack_effect",
                "topic": row["topic"],
                "metric": row["metric"],
                "source_family_or_local_id": "",
                "value": row["geo_opt_value"],
                "unit": row["unit"],
                "value_2": row["mass_model_value"],
                "unit_2": f"Mass_model_511 {row['unit']}".strip(),
                "context": f"geo_over_mass={row['geo_over_mass']}; relative_change_percent={row['relative_change_percent']}",
                "interpretation": row["interpretation"],
            }
        )

    for row in read_csv(COMPLEMENT / "10_w2_neutron_energy_depth_events.csv"):
        rows.append(
            {
                "record_type": "w2_neutron_depth_event",
                "topic": "neutron_energy_depth_proxy",
                "metric": row["status"],
                "source_family_or_local_id": row["local_id"],
                "value": row["depth_projection_cm"],
                "unit": "cm depth_projection",
                "value_2": row["init_energy_keV"],
                "unit_2": "keV initial neutron energy",
                "context": f"entry={row['entry_class']}; theta={row['theta_local_deg']}; phi={row['phi_local_deg']}; first_hit={row['first_hit_category']}::{row['first_hit_volume']}; plotted={row['plotted']}",
                "interpretation": "first-hit depth proxy event row; not continuous Geant4 energy-loss-vs-depth scoring",
            }
        )

    write_csv(
        OUT / "10_plastic_bpe_neutron_effects.csv",
        rows,
        ["record_type", "topic", "metric", "source_family_or_local_id", "value", "unit", "value_2", "unit_2", "context", "interpretation"],
    )
    return rows


def build_fact_summary(entry_angle_rows: list[dict[str, Any]], effect_rows: list[dict[str, Any]]) -> dict[str, Any]:
    base = read_json(COMPLEMENT / "02_fact_summary.json")
    trajectories = read_csv(COMPLEMENT / "03_w2_particle_trajectories_enriched.csv")
    veto_flags = read_csv(COMPLEMENT / "07_w2_event_veto_flags.csv")
    return {
        "package": "10_gpt_geometry_optimization_direction_20260707",
        "status": "PASS_GPT_GEOMETRY_OPTIMIZATION_PACKAGE_BUILT",
        "goal": "Ask GPT Pro for next geometry optimization directions, not another data-summary pass.",
        "scope": base["scope"],
        "read_order": [
            "01_README_AND_PROMPT.md",
            "02_fact_summary.json",
            "03_geometry_2d_detail.png",
            "04_geometry_3d_wrl.wrl",
            "05_geoopt_added_geometry_manifest.json",
            "06_geoopt_added_volumes.geo",
            "07_w2_particle_trajectories_enriched.csv",
            "08_w2_event_veto_flags.csv",
            "09_w2_entry_angle_veto_summary.csv",
            "10_plastic_bpe_neutron_effects.csv",
        ],
        "why_this_regrouping": (
            "The previous complement package was very data-heavy. This regrouping adds CAD-like geometry context "
            "and keeps the event-level particle/veto evidence needed for optimization reasoning."
        ),
        "w2_event_counts_by_particle": dict(sorted(Counter(r["source_family"] for r in trajectories).items())),
        "veto_priority_counts": dict(sorted(Counter(r["veto_priority_layer"] for r in veto_flags).items())),
        "entry_counts_by_source_family": base["entry_counts_by_source_family"],
        "atm511_source_definition": base["atm511_source_definition"],
        "veto_priority_definition": base["veto_priority_definition"],
        "entry_definition": base["entry_definition"],
        "included_geometry_files": {
            "2d_png": "03_geometry_2d_detail.png",
            "wrl": "04_geometry_3d_wrl.wrl",
            "added_geometry_manifest": "05_geoopt_added_geometry_manifest.json",
            "added_volumes_geo": "06_geoopt_added_volumes.geo",
        },
        "included_data_files": {
            "trajectory_events": "07_w2_particle_trajectories_enriched.csv",
            "veto_flags": "08_w2_event_veto_flags.csv",
            "entry_angle_veto_summary": "09_w2_entry_angle_veto_summary.csv",
            "plastic_bpe_neutron_effects": "10_plastic_bpe_neutron_effects.csv",
        },
        "row_counts": {
            "trajectory_events": len(trajectories),
            "veto_flags": len(veto_flags),
            "entry_angle_veto_summary": len(entry_angle_rows),
            "plastic_bpe_neutron_effects": len(effect_rows),
        },
        "major_caveats": base["major_caveats"],
    }


def write_readme(summary: dict[str, Any]) -> None:
    prompt = """我上传了当前 TES 511 keV 探测器 geo-opt S1/BPE/W5 几何、W2 线窗背景事件轨迹、入口位置分类、veto 标志、塑闪 veto 效果、BPE/中子活化效果数据。

请不要主要复述数据结论。我已经完成初步分析，现在需要你基于这些文件提出下一轮几何优化方向。

重点任务：
1. 根据 W2 背景事件的入射位置和轨迹，判断哪些几何区域最值得优先修改。
2. 分别针对 e+、neutron、atm511、activation，提出可执行的几何或 veto 优化方案。
3. 判断哪些方案可能真实降低 TES W2 本底，哪些只是看起来合理但风险大。
4. 给出一个优先级排序：最高优先、次高优先、暂不建议。
5. 对每个建议说明：预期压制的背景成分、可能副作用、需要跑什么最小验证模拟。

请特别关注 side_wall、side_window、top、bottom、envelope_miss 的泄漏路径，以及 plastic skin veto、non-plastic active veto、Compton/FoV veto、BPE shield stack 的实际作用。目标是找到下一轮最值得测试的几何改动，而不是重新总结已有分析。

几何图和 WRL 用于帮助你理解空间结构；真正的优化判断请以 W2 事件轨迹和 veto/entry CSV 为主。
"""
    lines = [
        "# GPT Pro Geometry Optimization Package",
        "",
        "This directory intentionally contains exactly 10 files. It replaces the previous data-only complement package when the goal is to ask GPT Pro for optimization directions.",
        "",
        "## Use This Prompt",
        "",
        "```text",
        prompt.strip(),
        "```",
        "",
        "## File Roles",
        "",
        "- `03_geometry_2d_detail.png`: quick geometry overview.",
        "- `04_geometry_3d_wrl.wrl`: CAD-like 3D context.",
        "- `05_geoopt_added_geometry_manifest.json` and `06_geoopt_added_volumes.geo`: added plastic/BPE/W geometry definitions.",
        "- `07_w2_particle_trajectories_enriched.csv`: one W2 raw TES event per row with source point, direction, TES centroid, entry class, and veto priority.",
        "- `08_w2_event_veto_flags.csv`: explicit event-level plastic, active, and Compton/FoV veto flags.",
        "- `09_w2_entry_angle_veto_summary.csv`: compact entry/angle/veto aggregate table.",
        "- `10_plastic_bpe_neutron_effects.csv`: plastic-veto, BPE/shield-stack activation, and W2 neutron-depth evidence in one table.",
        "",
        "## Caveats",
        "",
    ]
    for caveat in summary["major_caveats"]:
        lines.append(f"- {caveat}")
    (OUT / "01_README_AND_PROMPT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    copy_inputs()
    entry_angle_rows = build_entry_angle_veto_summary()
    effect_rows = build_effects_file()
    summary = build_fact_summary(entry_angle_rows, effect_rows)
    (OUT / "02_fact_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_readme(summary)

    files = sorted(p.name for p in OUT.iterdir() if p.is_file())
    if files != sorted(FILES):
        raise RuntimeError(f"package file mismatch: expected {sorted(FILES)}, got {files}")
    print(json.dumps({"status": "PASS", "output_dir": rel(OUT), "file_count": len(files), "files": files}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
