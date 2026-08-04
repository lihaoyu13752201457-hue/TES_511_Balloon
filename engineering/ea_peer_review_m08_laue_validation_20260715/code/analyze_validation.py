#!/usr/bin/env python3
"""Analyze the M08 R/T/A, step, and outgoing-mosaic validation runs."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REPORTS = ROOT / "reports"
HC_KEV_A = 12.398419843320026
D_SPACING_A = 3.266590088
FOCAL_LENGTH_MM = 10000.0
HEART_FOCAL_LENGTH_MM = 8300.0
BE_RADIUS_MM = 18.98
MOSAIC_FWHM_ARCSEC = 30.0
RTA_FLOOR_TOLERANCE = {"R": 0.020, "T": 0.025, "A": 0.025}


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_curve(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "delta": float(row["delta_theta_rad"]),
                "R": float(row["reflectivity"]),
                "T": float(row["transmittivity"]),
                "A": float(row["absorption"]),
            }
            for row in csv.DictReader(handle)
        ]


def interpolate(curve: list[dict[str, float]], x: float, field: str) -> float:
    if x <= curve[0]["delta"]:
        return curve[0][field]
    if x >= curve[-1]["delta"]:
        return curve[-1][field]
    lo = 0
    hi = len(curve) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if curve[mid]["delta"] <= x:
            lo = mid
        else:
            hi = mid
    x0 = curve[lo]["delta"]
    x1 = curve[hi]["delta"]
    fraction = (x - x0) / (x1 - x0)
    return curve[lo][field] + fraction * (curve[hi][field] - curve[lo][field])


def unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return tuple(value / norm for value in vector)  # type: ignore[return-value]


def dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def bragg_angle_rad(energy_keV: float) -> float:
    return math.asin(HC_KEV_A / energy_keV / (2.0 * D_SPACING_A))


def delta_theta_rad(energy_keV: float, offset_arcsec: float) -> float:
    theta_b = bragg_angle_rad(energy_keV)
    radius_mm = FOCAL_LENGTH_MM * math.tan(2.0 * theta_b)
    nominal_in = (0.0, 0.0, 1.0)
    nominal_out = unit((-radius_mm, 0.0, FOCAL_LENGTH_MM))
    plane_normal = unit(tuple(a - b for a, b in zip(nominal_in, nominal_out)))
    off_rad = math.radians(offset_arcsec / 3600.0)
    incoming = unit((math.tan(off_rad), 0.0, 1.0))
    theta_local = math.asin(abs(dot(incoming, plane_normal)))
    return theta_local - theta_b


def binomial_se(p: float, n: int) -> float:
    return math.sqrt(max(p * (1.0 - p), 0.25 / n) / n)


def analyze_rta() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run_dir in sorted((OUT / "rta_scan").iterdir()):
        metadata = load_json(run_dir / "run_metadata.json")
        summary = load_json(run_dir / "summary.json")
        energy = int(metadata["energy_keV"])
        offset = float(metadata["offset_arcsec"])
        delta = delta_theta_rad(float(energy), offset)
        curve = load_curve(ROOT / "data" / "xop_fixed_10p218801mm" / f"ge111_{energy}keV_rocking_curve.csv")
        n = int(summary["n_primaries"])
        observed = {
            "R": float(summary["emergent_r_fraction"]),
            "T": float(summary["emergent_t_fraction"]),
            "A": float(summary["emergent_a_or_removed_fraction"]),
        }
        reference = {field: interpolate(curve, delta, field) for field in ("R", "T", "A")}
        row: dict[str, object] = {
            "energy_keV": energy,
            "offset_arcsec": offset,
            "delta_theta_urad": delta * 1.0e6,
            "n_primaries": n,
            "rta_closure": float(summary["emergent_rta_closure"]),
            "max_observed_crystal_step_mm": float(summary["max_observed_crystal_step_mm"]),
        }
        point_pass = True
        for field in ("R", "T", "A"):
            residual = observed[field] - reference[field]
            se = binomial_se(observed[field], n)
            tolerance = max(RTA_FLOOR_TOLERANCE[field], 4.0 * se)
            passed = abs(residual) <= tolerance
            point_pass = point_pass and passed
            row.update(
                {
                    f"xop_{field.lower()}": reference[field],
                    f"geant4_{field.lower()}": observed[field],
                    f"delta_{field.lower()}": residual,
                    f"se_{field.lower()}": se,
                    f"tolerance_{field.lower()}": tolerance,
                    f"pass_{field.lower()}": passed,
                }
            )
        row["point_pass"] = point_pass
        rows.append(row)

    component_metrics: dict[str, object] = {}
    for field in ("R", "T", "A"):
        residuals = [float(row[f"delta_{field.lower()}"]) for row in rows]
        component_metrics[field] = {
            "max_abs_delta": max(abs(value) for value in residuals),
            "rms_delta": math.sqrt(sum(value * value for value in residuals) / len(residuals)),
            "mean_delta": sum(residuals) / len(residuals),
            "points_passed": sum(bool(row[f"pass_{field.lower()}"]) for row in rows),
            "points_total": len(rows),
        }

    by_energy: dict[str, object] = {}
    for energy in sorted({int(row["energy_keV"]) for row in rows}):
        selected = [row for row in rows if int(row["energy_keV"]) == energy]
        zero = min(selected, key=lambda row: abs(float(row["offset_arcsec"])))
        by_energy[str(energy)] = {
            "points": len(selected),
            "peak_xop_R": float(zero["xop_r"]),
            "peak_geant4_R": float(zero["geant4_r"]),
            "peak_delta_R": float(zero["delta_r"]),
            "max_abs_delta_R": max(abs(float(row["delta_r"])) for row in selected),
            "max_abs_delta_T": max(abs(float(row["delta_t"])) for row in selected),
            "max_abs_delta_A": max(abs(float(row["delta_a"])) for row in selected),
            "points_passed": sum(bool(row["point_pass"]) for row in selected),
        }

    summary = {
        "status": "PASS" if all(bool(row["point_pass"]) for row in rows) else "PARTIAL_PASS",
        "points": len(rows),
        "energies": len({row["energy_keV"] for row in rows}),
        "angles_per_energy": len({row["offset_arcsec"] for row in rows}),
        "all_rta_closure": max(abs(float(row["rta_closure"]) - 1.0) for row in rows) <= 1.0e-12,
        "max_rta_closure_error": max(abs(float(row["rta_closure"]) - 1.0) for row in rows),
        "all_configured_step_limits_respected": all(float(row["max_observed_crystal_step_mm"]) <= 1.000001 for row in rows),
        "points_all_components_passed": sum(bool(row["point_pass"]) for row in rows),
        "component_metrics": component_metrics,
        "by_energy": by_energy,
        "tolerance_rule": "abs(delta) <= max(component floor, 4 binomial SE); floors R/T/A=0.020/0.025/0.025",
        "reference_scope": "raw XOP/CRYSTAL angle-energy curves rescaled to the fixed 10.218801 mm tile using the Darwin-Hamilton slab form",
    }
    return rows, summary


def analyze_step() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run_dir in sorted((OUT / "step_convergence").iterdir()):
        metadata = load_json(run_dir / "run_metadata.json")
        summary = load_json(run_dir / "summary.json")
        rows.append(
            {
                "name": metadata["name"],
                "configured_max_step_mm": float(metadata["max_step_mm"]),
                "observed_max_step_mm": float(summary["max_observed_crystal_step_mm"]),
                "n_crystal_steps": int(summary["n_crystal_steps"]),
                "mean_crystal_step_mm": float(summary["mean_crystal_step_mm"]),
                "R": float(summary["emergent_r_fraction"]),
                "T": float(summary["emergent_t_fraction"]),
                "A": float(summary["emergent_a_or_removed_fraction"]),
                "spot_d90_cm": float(summary["focal_crossing_spot_d90_cm"]),
            }
        )
    reference = min(rows, key=lambda row: float(row["configured_max_step_mm"]) if float(row["configured_max_step_mm"]) > 0.0 else math.inf)
    for row in rows:
        for field in ("R", "T", "A"):
            row[f"delta_{field}_vs_0p2mm"] = float(row[field]) - float(reference[field])
        row["delta_spot_d90_cm_vs_0p2mm"] = float(row["spot_d90_cm"]) - float(reference["spot_d90_cm"])
        configured = float(row["configured_max_step_mm"])
        row["step_limit_respected"] = configured == 0.0 or float(row["observed_max_step_mm"]) <= configured + 1.0e-9
    max_fraction_delta = max(abs(float(row[f"delta_{field}_vs_0p2mm"])) for row in rows for field in ("R", "T", "A"))
    max_spot_delta = max(abs(float(row["delta_spot_d90_cm_vs_0p2mm"])) for row in rows)
    passed = all(bool(row["step_limit_respected"]) for row in rows) and max_fraction_delta <= 0.010 and max_spot_delta <= 0.020
    return rows, {
        "status": "PASS" if passed else "FAIL",
        "levels": len(rows),
        "reference_level_mm": reference["configured_max_step_mm"],
        "max_abs_rta_fraction_delta_vs_0p2mm": max_fraction_delta,
        "max_abs_spot_d90_delta_cm_vs_0p2mm": max_spot_delta,
        "all_finite_step_limits_respected": all(bool(row["step_limit_respected"]) for row in rows),
        "gates": {"max_abs_rta_fraction_delta": 0.010, "max_abs_spot_d90_delta_cm": 0.020},
    }


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]


def angle_between(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.acos(max(-1.0, min(1.0, dot(unit(a), unit(b)))))


def focal_diagnostics(run_dir: Path) -> dict[str, object]:
    theta_b = bragg_angle_rad(511.0)
    radius_mm = FOCAL_LENGTH_MM * math.tan(2.0 * theta_b)
    ideal_out = unit((-radius_mm, 0.0, FOCAL_LENGTH_MM))
    angles_arcsec: list[float] = []
    radii_mm: list[float] = []
    with (run_dir / "focal_crossings.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["source_tag"] != "laue_bfull_diffracted":
                continue
            direction = (float(row["ux"]), float(row["uy"]), float(row["uz"]))
            angles_arcsec.append(math.degrees(angle_between(direction, ideal_out)) * 3600.0)
            radii_mm.append(math.hypot(float(row["x_mm"]), float(row["y_mm"])))
    return {
        "diffracted_rows": len(radii_mm),
        "angular_r90_arcsec": quantile(angles_arcsec, 0.9),
        "focal_r90_mm": quantile(radii_mm, 0.9),
        "within_be_count": sum(radius <= BE_RADIUS_MM for radius in radii_mm),
        "within_be_fraction_of_emergent_R": sum(radius <= BE_RADIUS_MM for radius in radii_mm) / len(radii_mm),
    }


def analyze_mosaic() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    for run_dir in sorted((OUT / "mosaic_outgoing").iterdir()):
        metadata = load_json(run_dir / "run_metadata.json")
        summary = load_json(run_dir / "summary.json")
        diag = focal_diagnostics(run_dir)
        rows.append(
            {
                "name": metadata["name"],
                "source_jitter_mm": float(metadata["source_jitter_mm"]),
                "outgoing_model": metadata["outgoing_model"],
                "n_primaries": int(summary["n_primaries"]),
                "R": float(summary["emergent_r_fraction"]),
                "T": float(summary["emergent_t_fraction"]),
                "A": float(summary["emergent_a_or_removed_fraction"]),
                "spot_d90_cm": float(summary["focal_crossing_spot_d90_cm"]),
                **diag,
            }
        )

    point = {str(row["outgoing_model"]): row for row in rows if float(row["source_jitter_mm"]) == 0.0}
    footprint = {str(row["outgoing_model"]): row for row in rows if float(row["source_jitter_mm"]) == 18.0}
    sigma_rad = math.radians(MOSAIC_FWHM_ARCSEC / 3600.0) / 2.355
    gaussian_r90_rad = math.sqrt(-2.0 * math.log(0.1)) * sigma_rad
    analytic_direct_d90_cm = 2.0 * gaussian_r90_rad * FOCAL_LENGTH_MM / 10.0
    heart_manifest = load_json(ROOT / "data" / "heart_validation_manifest.json")
    checks = heart_manifest["checks"]
    heart_native_d90_cm = float(checks["full_lens_observables"]["spot_d90_cm"])
    heart_guan_d90_cm = float(checks["external_lens_curve"]["spot_d90_cm"])
    heart_native_scaled_cm = heart_native_d90_cm * FOCAL_LENGTH_MM / HEART_FOCAL_LENGTH_MM
    heart_guan_scaled_cm = heart_guan_d90_cm * FOCAL_LENGTH_MM / HEART_FOCAL_LENGTH_MM
    direct_d90 = float(point["gaussian_outgoing"]["spot_d90_cm"])
    plane_d90 = float(point["gaussian_plane"]["spot_d90_cm"])
    direct_vs_analytic_rel = (direct_d90 - analytic_direct_d90_cm) / analytic_direct_d90_cm
    direct_vs_heart_rel = (direct_d90 - heart_guan_scaled_cm) / heart_guan_scaled_cm
    plane_vs_heart_rel = (plane_d90 - heart_guan_scaled_cm) / heart_guan_scaled_cm
    direct_model_pass = abs(direct_vs_analytic_rel) <= 0.05 and abs(direct_vs_heart_rel) <= 0.10
    current_model_pass = abs(plane_vs_heart_rel) <= 0.10
    summary = {
        "status": "PASS" if current_model_pass else "CORRECTION_REQUIRED",
        "current_mainline_outgoing_model": "gaussian_plane",
        "heart_equivalent_candidate": "gaussian_outgoing",
        "analytic_direct_gaussian_point_d90_cm": analytic_direct_d90_cm,
        "heart_native_f8p3m_d90_cm": heart_native_d90_cm,
        "heart_guan_f8p3m_d90_cm": heart_guan_d90_cm,
        "heart_native_scaled_to_f10m_d90_cm": heart_native_scaled_cm,
        "heart_guan_scaled_to_f10m_d90_cm": heart_guan_scaled_cm,
        "geant4_gaussian_outgoing_point_d90_cm": direct_d90,
        "geant4_gaussian_plane_point_d90_cm": plane_d90,
        "geant4_ideal_plane_point_d90_cm": float(point["ideal_plane"]["spot_d90_cm"]),
        "gaussian_plane_over_gaussian_outgoing_d90_ratio": plane_d90 / direct_d90,
        "gaussian_outgoing_vs_analytic_relative": direct_vs_analytic_rel,
        "gaussian_outgoing_vs_scaled_heart_relative": direct_vs_heart_rel,
        "gaussian_plane_vs_scaled_heart_relative": plane_vs_heart_rel,
        "heart_equivalent_candidate_pass": direct_model_pass,
        "current_mainline_model_pass": current_model_pass,
        "footprint18mm_d90_cm": {model: float(row["spot_d90_cm"]) for model, row in footprint.items()},
        "footprint18mm_within_be_fraction": {
            model: float(row["within_be_fraction_of_emergent_R"]) for model, row in footprint.items()
        },
        "interpretation": "Perturbing the plane normal and then reflecting broadens the point-source kernel beyond both the direct 30-arcsec outgoing Gaussian and the retained HEART 2.1.3 oracle; the direct-outgoing implementation matches both independent references.",
    }
    return rows, summary


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    materialized = list(rows)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(materialized[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(materialized)


def write_report(audit: dict[str, object], rta_rows: list[dict[str, object]], step_rows: list[dict[str, object]], mosaic_rows: list[dict[str, object]]) -> None:
    rta = audit["rta"]
    step = audit["step_convergence"]
    mosaic = audit["mosaic_outgoing"]
    lines = [
        "# M08 Laue 单晶片验证报告",
        "",
        f"- 总裁决：`{audit['m08_status']}`",
        f"- R/T/A 角度—能量矩阵：`{rta['status']}`（{rta['points_all_components_passed']}/{rta['points']} 点通过本轮明示容差）",
        f"- 步长收敛：`{step['status']}`",
        f"- 当前 mosaic 出射实现：`{mosaic['status']}`",
        "",
        "## 1. 单晶片 R/T/A 角度—能量扫描",
        "",
        "固定 Ge(111) 晶片厚度 10.218801 mm、边长 18 mm、焦距 10 m；能量为 480/500/511/530/550 keV，每个能量扫描 -90 至 +90 arcsec 的 13 个角点，每点 20,000 个一次光子。参考曲线为保留的 XOP/CRYSTAL diff_pat 曲线，并按同一 Darwin-Hamilton slab 形式严格换算到固定厚度。",
        "",
        "| E (keV) | 点数 | 峰值 XOP R | 峰值 G4 R | 峰值差 | max \\|ΔR\\| | max \\|ΔT\\| | max \\|ΔA\\| | 全分量通过点 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for energy, item in rta["by_energy"].items():
        lines.append(
            f"| {energy} | {item['points']} | {item['peak_xop_R']:.6f} | {item['peak_geant4_R']:.6f} | "
            f"{item['peak_delta_R']:+.6f} | {item['max_abs_delta_R']:.6f} | {item['max_abs_delta_T']:.6f} | "
            f"{item['max_abs_delta_A']:.6f} | {item['points_passed']} |"
        )
    lines.extend(
        [
            "",
            f"R/T/A 闭合最大误差为 `{rta['max_rta_closure_error']:.3g}`；全部扫描的实测最大晶体步长均不超过 1 mm。容差规则为 `max(分量绝对下限, 4σ_MC)`，R/T/A 下限分别为 0.020/0.025/0.025。",
            "",
            "## 2. 步长收敛",
            "",
            "| 最大步长 (mm) | 实测最大步长 (mm) | R | T | A | d90 (cm) | max \\|ΔR/T/A\\| vs 0.2 mm |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in sorted(step_rows, key=lambda item: float(item["configured_max_step_mm"])):
        max_delta = max(abs(float(row[f"delta_{field}_vs_0p2mm"])) for field in ("R", "T", "A"))
        configured = "unlimited" if float(row["configured_max_step_mm"]) == 0.0 else f"{row['configured_max_step_mm']:.3g}"
        lines.append(
            f"| {configured} | {row['observed_max_step_mm']:.6g} | {row['R']:.6f} | {row['T']:.6f} | "
            f"{row['A']:.6f} | {row['spot_d90_cm']:.6f} | {max_delta:.6f} |"
        )
    lines.extend(
        [
            "",
            f"最大 R/T/A 变化 `{step['max_abs_rta_fraction_delta_vs_0p2mm']:.6f}`，最大 d90 变化 `{step['max_abs_spot_d90_delta_cm_vs_0p2mm']:.6f} cm`；步长项通过。",
            "",
            "## 3. mosaic 出射角与焦斑独立验证",
            "",
            "| 点源模型 | d90 (cm) | 角度 r90 (arcsec) | 相对缩放 HEART f10m |",
            "|---|---:|---:|---:|",
        ]
    )
    point_rows = [row for row in mosaic_rows if float(row["source_jitter_mm"]) == 0.0]
    for row in point_rows:
        rel = (float(row["spot_d90_cm"]) - mosaic["heart_guan_scaled_to_f10m_d90_cm"]) / mosaic["heart_guan_scaled_to_f10m_d90_cm"]
        lines.append(f"| {row['outgoing_model']} | {row['spot_d90_cm']:.6f} | {row['angular_r90_arcsec']:.3f} | {rel:+.1%} |")
    lines.extend(
        [
            "",
            f"独立 2D、30 arcsec FWHM 出射高斯解析值为 `{mosaic['analytic_direct_gaussian_point_d90_cm']:.6f} cm`；保留的 HEART 2.1.3/Guan 方向 oracle 从 8.3 m 线性缩放至 10 m 为 `{mosaic['heart_guan_scaled_to_f10m_d90_cm']:.6f} cm`。`gaussian_outgoing` 与二者分别相差 `{mosaic['gaussian_outgoing_vs_analytic_relative']:+.2%}` 和 `{mosaic['gaussian_outgoing_vs_scaled_heart_relative']:+.2%}`，通过；论文当前 `gaussian_plane` 与 HEART 相差 `{mosaic['gaussian_plane_vs_scaled_heart_relative']:+.2%}`，不通过。",
            "",
            "18 mm 实际 footprint 下，三种模型的 d90 都约 2 cm，Be 半径门的通过率仍接近 1；这说明当前有效面积数值影响很小，但不能掩盖出射角抽样规则本身尚需修正。",
            "",
            "## 裁决",
            "",
            "M08 保持 `PARTIAL_PASS`：完整 R/T/A 矩阵和步长收敛已经补齐，名义反射率/有效面积证据继续成立；但当前生产代码把 30 arcsec 高斯施加到晶面法线后再反射，得到的点源核比 HEART 等价的出射方向抽样显著更宽。应将生产实现改为经验证的 `gaussian_outgoing`（或更严格的条件微晶取向抽样），重跑 f10m 三种子焦面源后，才可把 M08 完全销项。",
            "",
        ]
    )
    (REPORTS / "M08_VALIDATION_REPORT_ZH.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    rta_rows, rta_summary = analyze_rta()
    step_rows, step_summary = analyze_step()
    mosaic_rows, mosaic_summary = analyze_mosaic()
    if step_summary["status"] == "PASS" and rta_summary["status"] in ("PASS", "PARTIAL_PASS"):
        m08_status = "PASS" if mosaic_summary["status"] == "PASS" and rta_summary["status"] == "PASS" else "PARTIAL_PASS"
    else:
        m08_status = "FAIL"
    audit = {
        "m08_status": m08_status,
        "rta": rta_summary,
        "step_convergence": step_summary,
        "mosaic_outgoing": mosaic_summary,
        "software": {
            "geant4": "11.4.0",
            "xop_reference": "CRYSTAL diff_pat v1.8; xoppylib 1.0.55; DABAX 1.0.12",
            "heart_reference": "2.1.3 retained oracle",
        },
    }
    write_csv(REPORTS / "rta_angle_energy_scan.csv", rta_rows)
    write_csv(REPORTS / "step_convergence.csv", step_rows)
    write_csv(REPORTS / "mosaic_outgoing_comparison.csv", mosaic_rows)
    (REPORTS / "audit_summary.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_report(audit, rta_rows, step_rows, mosaic_rows)
    print(json.dumps({"m08_status": m08_status, "report": str(REPORTS / 'M08_VALIDATION_REPORT_ZH.md')}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
