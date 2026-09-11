from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import xraydb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from external_baseline.channel_raytrace_py.parratt_reflectivity import (  # noqa: E402
    MultilayerSpec,
    ReflectivityGridRow,
    compute_reflectivity_rows,
    write_reflectivity_csv,
)


def read_rings(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rings(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "ring_id",
        "radius_cm",
        "bending_angle_deg",
        "length_cm",
        "width_cm",
        "thickness_mm",
        "n_tiles",
        "n_bounce_calibrated",
        "theta_calibrated_rad",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in fieldnames})


def dense_theta_grid() -> np.ndarray:
    broad = np.geomspace(1.0e-8, 5.0e-3, 600)
    transition = np.linspace(1.20e-4, 1.70e-4, 2501)
    merged = np.unique(np.concatenate([broad, transition]))
    return np.sort(merged)


def lookup_linear(rows: list[ReflectivityGridRow], theta_rad: float) -> ReflectivityGridRow:
    rows = sorted(rows, key=lambda row: row.theta_rad)
    if theta_rad <= rows[0].theta_rad:
        return rows[0]
    if theta_rad >= rows[-1].theta_rad:
        return rows[-1]
    for lower, upper in zip(rows, rows[1:]):
        if lower.theta_rad <= theta_rad <= upper.theta_rad:
            if upper.theta_rad == lower.theta_rad:
                return lower
            frac = (theta_rad - lower.theta_rad) / (upper.theta_rad - lower.theta_rad)
            values = asdict(lower)
            values["theta_rad"] = theta_rad
            values["R"] = lower.R + frac * (upper.R - lower.R)
            values["A"] = lower.A + frac * (upper.A - lower.A)
            values["T"] = lower.T + frac * (upper.T - lower.T)
            norm = values["R"] + values["A"] + values["T"]
            values["R"] /= norm
            values["A"] /= norm
            values["T"] /= norm
            values["source"] = values["source"] + ":dense_linear"
            return ReflectivityGridRow(**values)
    return min(rows, key=lambda row: abs(row.theta_rad - theta_rad))


def theta_for_required_R(rows: list[ReflectivityGridRow], required_R: float) -> float:
    sorted_rows = sorted(rows, key=lambda row: row.theta_rad)
    for lower, upper in zip(sorted_rows, sorted_rows[1:]):
        if (lower.R - required_R) * (upper.R - required_R) <= 0.0:
            lo = lower.theta_rad
            hi = upper.theta_rad
            for _ in range(70):
                mid = 0.5 * (lo + hi)
                mid_R = lookup_linear(sorted_rows, mid).R
                if abs(mid_R - required_R) < 1.0e-10:
                    return mid
                if (lookup_linear(sorted_rows, lo).R - required_R) * (mid_R - required_R) <= 0.0:
                    hi = mid
                else:
                    lo = mid
            return 0.5 * (lo + hi)
    return min(sorted_rows, key=lambda row: abs(row.R - required_R)).theta_rad


def critical_angle_rad(rho_high: float, rho_low: float, energy_keV: float) -> float:
    return 2.038e-2 * math.sqrt(max(0.0, rho_high - rho_low)) / energy_keV


def simple_table(headers: list[str], rows: list[list[object]]) -> str:
    head = "".join(f"<th>{html.escape(str(cell))}</th>" for cell in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def write_html(path: Path, summary: dict) -> None:
    rings = summary["rings"]
    calib_rows = [
        [
            ring["ring_id"],
            ring["bend_deg"],
            ring["n_bounce_calibrated"],
            f"{ring['theta_dense_calibrated_rad']:.9g}",
            f"{ring['required_single_bounce_R']:.6f}",
            f"{ring['dense_lookup_R']:.6f}",
            f"{ring['exact_R_at_theta']:.6f}",
            f"{ring['required_bounces_for_bend_at_theta']:.2f}",
        ]
        for ring in rings
    ]
    finding_rows = [
        ["论文公开参数", "较高", "四环半径、长度、W/Si 30/150 nm、12 m、80%、50.89 cm2来自511-CAM论文。"],
        ["W/Si反射表", "中等", "使用xraydb/Parratt和Chantler光学常数；不是原论文IMD表，粗糙度/吸收处理未完全一致。"],
        ["headline透过率", "中等偏低", "可数值复现80%，但靠ring-calibrated theta/bounce，不是从公开几何自然推出。"],
        ["焦斑D90", "低", "当前Geant4直接按3.6 cm目标抽样，不是墙面几何和散射误差自然形成。"],
        ["wall-by-wall几何", "未完成", "当前是入口边界上的参数化多次反射过程，不是每层/每壁真实追踪。"],
    ]
    paper_rows = [
        [
            ring["ring_id"],
            ring["paper_bend_bounces"],
            f"{ring['paper_bend_theta_rad']:.9g}",
            f"{ring['paper_bend_R_power_n']:.4f}",
            f"{ring['paper_bend_with_open_fraction']:.4f}",
            f"{ring['paper_bend_with_open_fraction_and_si_length_absorption']:.4f}",
        ]
        for ring in rings
    ]
    css = """
    body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif;line-height:1.58;margin:0;background:#f5f7fa;color:#17202a}
    main{max-width:1060px;margin:0 auto;padding:30px 18px 60px}
    section{background:white;border:1px solid #d8dee8;border-radius:8px;margin:0 0 20px;padding:26px 32px}
    h1{font-size:32px;margin:0 0 8px} h2{font-size:23px;color:#1f5f99;margin:0 0 12px}
    table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px} th,td{border-bottom:1px solid #d8dee8;padding:8px;text-align:left;vertical-align:top} th{background:#eef3f8}
    .warn{border-left:4px solid #b33a32;background:#fff6f4;padding:10px 14px}.ok{border-left:4px solid #2e7d45;background:#f4fbf6;padding:10px 14px}
    code{background:#edf1f5;border-radius:4px;padding:2px 5px}
    """
    text = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Channel Physics Confidence Audit</title><style>{css}</style></head>
<body><main>
<section>
<h1>511-CAM Channel Geant4 物理可信度复核</h1>
<p class="warn">结论先行：当前性能不能称为“100%完全物理推导”。它是表驱动、参数化、校准后的Geant4 scaffold；工程链路可信，但wall-by-wall物理闭合还没有完成。</p>
<p>本审计修正了临界角附近反射表网格过粗的问题，生成了更密的W/Si 511 keV表，并重新给出ring-calibrated theta。</p>
</section>
<section>
<h2>核心量级检查</h2>
<p>W/Si按论文临界角公式估算：<code>theta_c = {summary['critical_angle_rad']:.6g} rad = {summary['critical_angle_deg']:.5g} deg</code>。当前校准theta在这个量级附近，因此局部角度不是离谱的；问题在于bounce/path/open-area记账没有闭合。</p>
{simple_table(["ring", "bend deg", "校准bounce", "新theta rad", "目标单次R", "密表R", "直接R", "若靠2Ntheta需bounce"], calib_rows)}
</section>
<section>
<h2>证据分级</h2>
{simple_table(["对象", "可信度", "理由"], finding_rows)}
</section>
<section>
<h2>新增改善：论文公式项逐项拆开</h2>
<p>按2020 JATIS公式的精神，把bend角要求的多次反射、open fraction和Si通道长度吸收拆开估算。这里使用当前W/Si Parratt表和xraydb的Si 511 keV衰减系数 <code>{summary['si_mu_cm_inv_511kev']:.6g} cm^-1</code>。</p>
{simple_table(["ring", "bend所需bounce", "theta rad", "R^N", "R^N×open", "R^N×open×Si长度透过"], paper_rows)}
<p>同一个压力测试也已经进入Geant4应用层：<code>channel_4ring_multibounce_demo --theta-policy paper_bend --open-fraction-policy paper_once --path-absorption-policy si_length</code>，输出在 <code>{html.escape(summary['geant4_strict_path_absorption_run'])}</code>。</p>
<p class="warn">这不是最终答案，而是反证/压力测试：一旦把Si厘米级路径吸收也纳入，公开参数直接组合会比80%低得多，说明原论文内部的path/open-area/absorption记账必须恢复，不能靠校准theta掩盖。</p>
</section>
<section>
<h2>公开文献对照</h2>
<p>511-CAM论文只给了四环、W/Si层厚、12 m焦距、3.6 cm焦斑、80% transmissivity和50.89 cm2有效面积。2020 JATIS/OSTI论文给出更细的通道公式：每次反射R、每段吸收、open fraction和几何可用面积，并说明原始链路是IMD + IDL ray tracing + MEGAlib。</p>
<p class="warn">我们现在没有原IDL代码，也没有IMD输出表；因此只能做参数化Geant4复现和诊断，不能宣称完整复原论文内部实现。</p>
</section>
<section>
<h2>输出文件</h2>
<p>密反射表：<code>{html.escape(summary['dense_reflectivity_table'])}</code></p>
<p>更新后的ring配置：<code>{html.escape(summary['updated_ring_config'])}</code></p>
<p>审计JSON：<code>{html.escape(summary['summary_json'])}</code></p>
</section>
</main></body></html>
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit physical confidence of the 511-CAM Channel scaffold.")
    parser.add_argument("--ring-config", default="data/channel/cam511_channel_rings.csv")
    parser.add_argument("--dense-table", default="data/reflectivity/WSi_511keV_parratt_grid_dense.csv")
    parser.add_argument("--out", default="runs/channel/physics_confidence_audit")
    parser.add_argument("--html", default="records/2026-05-20_channel_physics_confidence_audit.html")
    parser.add_argument("--target", type=float, default=0.80)
    args = parser.parse_args()

    spec = MultilayerSpec()
    rows = compute_reflectivity_rows(spec, E_keV=511.0, theta_rad=dense_theta_grid())
    write_reflectivity_csv(ROOT / args.dense_table, rows)

    rings = read_rings(ROOT / args.ring_config)
    updated_rings: list[dict[str, str]] = []
    audit_rings = []
    theta_c = critical_angle_rad(spec.high_Z_density_g_cm3, spec.low_Z_density_g_cm3, 511.0)
    mu_si = float(xraydb.material_mu("Si", 511000.0, density=spec.low_Z_density_g_cm3))
    open_fraction = spec.open_fraction
    for ring in rings:
        n_bounce = int(ring["n_bounce_calibrated"])
        required_R = args.target ** (1.0 / max(1, n_bounce))
        theta = theta_for_required_R(rows, required_R)
        dense_row = lookup_linear(rows, theta)
        exact_row = compute_reflectivity_rows(spec, E_keV=511.0, theta_rad=[theta])[0]
        bend_rad = math.radians(float(ring["bending_angle_deg"]))
        paper_bounces = max(1, int(math.ceil(bend_rad / (2.0 * 1.5e-4))))
        paper_theta = bend_rad / (2.0 * paper_bounces)
        paper_row = compute_reflectivity_rows(spec, E_keV=511.0, theta_rad=[paper_theta])[0]
        paper_Rn = paper_row.R ** paper_bounces
        si_length_transmission = math.exp(-mu_si * float(ring["length_cm"]))
        ring_updated = dict(ring)
        ring_updated["theta_calibrated_rad"] = f"{theta:.17g}"
        updated_rings.append(ring_updated)
        audit_rings.append(
            {
                "ring_id": int(ring["ring_id"]),
                "bend_deg": float(ring["bending_angle_deg"]),
                "n_bounce_calibrated": n_bounce,
                "theta_dense_calibrated_rad": theta,
                "required_single_bounce_R": required_R,
                "dense_lookup_R": dense_row.R,
                "exact_R_at_theta": exact_row.R,
                "exact_minus_dense_R": exact_row.R - dense_row.R,
                "required_bounces_for_bend_at_theta": bend_rad / (2.0 * theta),
                "required_bounces_for_bend_at_critical_angle": bend_rad / (2.0 * theta_c),
                "paper_bend_bounces": paper_bounces,
                "paper_bend_theta_rad": paper_theta,
                "paper_bend_single_bounce_R": paper_row.R,
                "paper_bend_R_power_n": paper_Rn,
                "paper_bend_with_open_fraction": paper_Rn * open_fraction,
                "si_length_transmission": si_length_transmission,
                "paper_bend_with_open_fraction_and_si_length_absorption": paper_Rn * open_fraction * si_length_transmission,
            }
        )

    write_rings(ROOT / args.ring_config, updated_rings)

    out = ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "status": "AUDIT_COMPLETE_NOT_FULL_PHYSICS_CLOSURE",
        "critical_angle_rad": theta_c,
        "critical_angle_deg": math.degrees(theta_c),
        "dense_reflectivity_table": args.dense_table,
        "updated_ring_config": args.ring_config,
        "summary_json": f"{args.out}/summary.json",
        "geant4_strict_path_absorption_run": "runs/channel/geant4_4ring_multibounce_paper_formula_strict",
        "headline_performance_is_fully_first_principles": False,
        "main_reason": "Transmissivity and spot are benchmark-calibrated; original IMD/IDL channel path and open-area accounting are not recovered.",
        "si_mu_cm_inv_511kev": mu_si,
        "open_fraction": open_fraction,
        "rings": audit_rings,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_html(ROOT / args.html, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
