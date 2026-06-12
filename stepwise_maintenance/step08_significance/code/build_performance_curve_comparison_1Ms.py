#!/usr/bin/env python3
"""Build a 3-sigma performance-curve comparison including 1 Ms exposure."""

from __future__ import annotations

import csv
import json
import math
import os
import argparse
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-newgeo")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "stepwise_maintenance" / "step08_significance" / "outputs" / "performance_curve_comparison_1Ms"
V3P5_LABEL = "fullstat_v2"
V3P5_CUMULATIVE = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{V3P5_LABEL}" / "cumulative_significance_by_case.csv"
V3P5_TD = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{V3P5_LABEL}" / "step08_v3p5_centerfinger_time_dependent_summary.json"

REFERENCE_FLUX = 1.0e-4
SECONDS_PER_DAY = 86400.0
T20_S = 20.0 * SECONDS_PER_DAY
EXPOSURES_S = [1.0e4, 1.0e5, 1.0e6, T20_S]
YEAR_S = 365.25 * SECONDS_PER_DAY

# DEMO2 numbers below are legacy pre-fix headline Step08 time folds. They are
# retained only as historical comparison markers after the 2026-06-12 review
# reproduced an x8.0116 delayed-source normalization inflation in the old
# mainline activation source. They are not current sensitivity authority.
MAINLINE_CASES = [
    {
        "case_id": "DEMO2_W1_mission_axis",
        "label": "DEMO2 legacy W1 mission-axis",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "Z20d": 0.7669158563686436,
        "source": "core_md/VALIDATION.md step08_significance A_ref_Z20d",
        "method": "legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling",
    },
    {
        "case_id": "DEMO2_W2_line",
        "label": "DEMO2 legacy W2 line",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "Z20d": 2.735425315169172,
        "source": "core_md/VALIDATION.md line_window_sensitivity line_pm_3sigma_Z20d_time",
        "method": "legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling",
    },
    {
        "case_id": "DEMO2_W2_spot_r90",
        "label": "DEMO2 legacy W2 spot_r90",
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "Z20d": 4.50779,
        "source": "core_md/README.md focused-spot detector-coupled spatial sidecar",
        "method": "legacy_pre_fix_documented_20d_Z_sqrt_exposure_scaling",
    },
]

V3P5_CASES = [
    {
        "case_id": "v3p5_broad_480_550",
        "analysis_case_id": "A_point_broad_480_550_F0.0001",
        "label": "v3p5 broad 480-550",
        "source": "v3p5 Step08 cumulative_significance_by_case.csv",
    },
    {
        "case_id": "v3p5_W2",
        "analysis_case_id": "A_point_w2_510p58_511p42_F0.0001",
        "label": "v3p5 W2",
        "source": "v3p5 Step08 cumulative_significance_by_case.csv",
    },
]

BENCHMARKS_1MS = [
    {
        "case_id": "511CAM_Fig11_digitized_511keV",
        "label": "511-CAM Fig.11",
        "family": "external_1Ms",
        "exposure_s": 1.0e6,
        "flux_3sigma_ph_cm2_s": 2.7e-6,
        "method": "digitized_from_511CAM_Fig11_right_panel_at_511keV",
        "source": "511-CAM paper Fig.11, local rendered PDF /tmp/511cam_page16-16.png",
    },
    {
        "case_id": "SPI_511keV_1Ms_public",
        "label": "INTEGRAL/SPI",
        "family": "external_1Ms",
        "exposure_s": 1.0e6,
        "flux_3sigma_ph_cm2_s": 5.0e-5,
        "method": "published_3sigma_1e6s_511keV_narrow_line",
        "source": "SPI 511 keV line sensitivity public value; see arXiv:astro-ph/0310793 and SPI instrument sensitivity references",
    },
    {
        "case_id": "COSI_SMEX_scaled_to_1Ms",
        "label": "COSI scaled to 1 Ms",
        "family": "external_1Ms_scaled",
        "exposure_s": 1.0e6,
        "flux_3sigma_ph_cm2_s": 1.2e-5 * math.sqrt((2.0 * YEAR_S) / 1.0e6),
        "native_exposure_s": 2.0 * YEAR_S,
        "native_flux_3sigma_ph_cm2_s": 1.2e-5,
        "method": "sqrt_time_scaled_from_published_2yr_3sigma_narrow_line_point_source_sensitivity",
        "source": "Tomsick et al. 2023 COSI mission paper, arXiv:2308.12362",
    },
]

CAM511_DIGITIZED_POINTS = [
    {"energy_keV": 510.63, "flux_3sigma_ph_cm2_s": 3.4e-6, "source": "Fig.11 blue 511-CAM curve digitized from rendered page"},
    {"energy_keV": 510.88, "flux_3sigma_ph_cm2_s": 2.4e-6, "source": "Fig.11 blue 511-CAM curve digitized from rendered page"},
    {"energy_keV": 511.13, "flux_3sigma_ph_cm2_s": 3.1e-6, "source": "Fig.11 blue 511-CAM curve digitized from rendered page"},
    {"energy_keV": 511.38, "flux_3sigma_ph_cm2_s": 3.2e-6, "source": "Fig.11 blue 511-CAM curve digitized from rendered page"},
]


def configure_v3p5(label: str) -> None:
    global V3P5_LABEL, V3P5_CUMULATIVE, V3P5_TD

    V3P5_LABEL = label
    V3P5_CUMULATIVE = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{label}" / "cumulative_significance_by_case.csv"
    V3P5_TD = ROOT / "stepwise_maintenance" / "step08_significance" / f"outputs_v3p5_centerfinger_{label}" / "step08_v3p5_centerfinger_time_dependent_summary.json"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for row in rows:
            for key in row:
                if key not in fields:
                    fields.append(key)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fmt(value: float, ndigits: int = 6) -> str:
    if value == 0:
        return "0"
    if abs(value) < 1.0e-3 or abs(value) >= 1.0e5:
        return f"{value:.{ndigits}e}"
    return f"{value:.{ndigits}g}"


def flux3_from_z(reference_flux: float, z: float) -> float:
    return reference_flux * 3.0 / z if z > 0.0 else math.inf


def z_scaled_from_20d(z20d: float, exposure_s: float) -> float:
    return z20d * math.sqrt(exposure_s / T20_S)


def v3p5_case_rows(analysis_case_id: str) -> list[dict[str, float]]:
    rows = []
    for row in read_csv(V3P5_CUMULATIVE):
        if row["analysis_case_id"] != analysis_case_id:
            continue
        rows.append(
            {
                "elapsed_s": float(row["elapsed_stop_day"]) * SECONDS_PER_DAY,
                "Z": float(row["counting_Z"]),
                "source_counts": float(row["cumulative_source_counts"]),
                "background_counts": float(row["cumulative_background_counts"]),
            }
        )
    rows.sort(key=lambda item: item["elapsed_s"])
    return rows


def interpolate_z(rows: list[dict[str, float]], exposure_s: float) -> float:
    if not rows:
        return 0.0
    if exposure_s <= rows[0]["elapsed_s"]:
        first = rows[0]
        return first["Z"] * math.sqrt(exposure_s / first["elapsed_s"]) if first["elapsed_s"] > 0 else 0.0
    for prev, cur in zip(rows, rows[1:]):
        if exposure_s <= cur["elapsed_s"]:
            if cur["elapsed_s"] == prev["elapsed_s"]:
                return cur["Z"]
            f = (exposure_s - prev["elapsed_s"]) / (cur["elapsed_s"] - prev["elapsed_s"])
            # Interpolate source/background counts, then recompute Z.
            s = prev["source_counts"] + f * (cur["source_counts"] - prev["source_counts"])
            b = prev["background_counts"] + f * (cur["background_counts"] - prev["background_counts"])
            return s / math.sqrt(b) if b > 0 else 0.0
    last = rows[-1]
    return last["Z"] * math.sqrt(exposure_s / last["elapsed_s"]) if last["elapsed_s"] > 0 else 0.0


def build_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in MAINLINE_CASES:
        for exposure_s in EXPOSURES_S:
            z = z_scaled_from_20d(case["Z20d"], exposure_s)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "label": case["label"],
                    "family": "DEMO2_legacy_pre_fix",
                    "exposure_s": exposure_s,
                    "exposure_Ms": exposure_s / 1.0e6,
                    "exposure_day": exposure_s / SECONDS_PER_DAY,
                    "Z_at_reference_flux": z,
                    "flux_3sigma_ph_cm2_s": flux3_from_z(case["reference_flux_ph_cm2_s"], z),
                    "method": case["method"],
                    "source": case["source"],
                }
            )
    for case in V3P5_CASES:
        curve = v3p5_case_rows(case["analysis_case_id"])
        for exposure_s in EXPOSURES_S:
            z = interpolate_z(curve, exposure_s)
            rows.append(
                {
                    "case_id": case["case_id"],
                    "label": case["label"],
                    "family": f"v3p5_centerfinger_{V3P5_LABEL}",
                    "exposure_s": exposure_s,
                    "exposure_Ms": exposure_s / 1.0e6,
                    "exposure_day": exposure_s / SECONDS_PER_DAY,
                    "Z_at_reference_flux": z,
                    "flux_3sigma_ph_cm2_s": flux3_from_z(REFERENCE_FLUX, z),
                    "method": "v3p5_time_dependent_cumulative_interpolation",
                    "source": case["source"],
                }
            )
    for bench in BENCHMARKS_1MS:
        row = {
            "case_id": bench["case_id"],
            "label": bench["label"],
            "family": bench["family"],
            "exposure_s": bench["exposure_s"],
            "exposure_Ms": bench["exposure_s"] / 1.0e6,
            "exposure_day": bench["exposure_s"] / SECONDS_PER_DAY,
            "Z_at_reference_flux": "",
            "flux_3sigma_ph_cm2_s": bench["flux_3sigma_ph_cm2_s"],
            "method": bench["method"],
            "source": bench["source"],
        }
        if "native_exposure_s" in bench:
            row["native_exposure_s"] = bench["native_exposure_s"]
            row["native_flux_3sigma_ph_cm2_s"] = bench["native_flux_3sigma_ph_cm2_s"]
        rows.append(row)
    one_ms = {row["case_id"]: row for row in rows if abs(float(row["exposure_s"]) - 1.0e6) < 1.0e-9}
    best = min(one_ms.values(), key=lambda row: float(row["flux_3sigma_ph_cm2_s"]))
    summary = {
        "status": "PASS_PERFORMANCE_CURVE_COMPARISON_1MS",
        "claim_level": "L1_3SIGMA_FLUX_LIMIT_EXPOSURE_SCALING_COMPARISON",
        "exposure_s_requested": 1.0e6,
        "one_Ms": {
            key: {
                "label": row["label"],
                "flux_3sigma_ph_cm2_s": row["flux_3sigma_ph_cm2_s"],
                "Z_at_1e-4": row["Z_at_reference_flux"],
                "method": row["method"],
            }
            for key, row in sorted(one_ms.items())
        },
        "best_one_Ms_case": {
            "case_id": best["case_id"],
            "label": best["label"],
            "flux_3sigma_ph_cm2_s": best["flux_3sigma_ph_cm2_s"],
        },
        "best_1Ms": {
            "case_id": best["case_id"],
            "label": best["label"],
            "flux_3sigma_ph_cm2_s": best["flux_3sigma_ph_cm2_s"],
        },
        "inputs": {
            "v3p5_cumulative": rel(V3P5_CUMULATIVE),
            "v3p5_time_dependent_summary": rel(V3P5_TD),
            "v3p5_label": V3P5_LABEL,
            "mainline_legacy_pre_fix_reference": ["core_md/README.md", "core_md/VALIDATION.md"],
            "external_benchmark_sources": {
                "511CAM": "511-CAM Fig.11 rendered from /tmp/511cam.pdf",
                "SPI": "arXiv:astro-ph/0310793 / SPI public 511 keV narrow-line sensitivity",
                "COSI": "arXiv:2308.12362",
            },
        },
        "outputs": {
            "summary_json": rel(OUT / "performance_curve_comparison_1Ms_summary.json"),
            "csv": rel(OUT / "performance_curve_comparison_1Ms.csv"),
            "cam511_digitized_csv": rel(OUT / "cam511_fig11_digitized_points.csv"),
            "markdown": rel(OUT / "performance_curve_comparison_1Ms.md"),
            "figure": rel(OUT / "performance_curve_comparison_1Ms.png"),
        },
        "limitations": [
            f"v3p5 curves use the `{V3P5_LABEL}` Step08 products available in this checkout.",
            "DEMO2 curves are legacy pre-fix documented 20-day headline values scaled as sqrt(exposure); they are retained only as historical markers after the x8.0116 delayed-source normalization review hold.",
            "COSI is converted to a 1 Ms point by sqrt(time) scaling from a published 2-year all-sky narrow-line sensitivity, so it is a comparison marker, not an observing-strategy equivalence.",
            "511-CAM is digitized from the rendered Fig.11 right panel and should be treated as figure-derived.",
            "All values are Gaussian S/sqrt(B) 3-sigma flux limits, not a low-count exact Poisson construction.",
        ],
    }
    return rows, summary


def plot(rows: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(row["case_id"], []).append(row)
    for case_id, items in by_case.items():
        items.sort(key=lambda row: float(row["exposure_s"]))
        label = items[0]["label"]
        family = items[0]["family"]
        if family.startswith("external"):
            ax.scatter(
                [float(row["exposure_s"]) for row in items],
                [float(row["flux_3sigma_ph_cm2_s"]) for row in items],
                marker="*",
                s=95,
                label=label,
            )
        else:
            style = "-" if family.startswith("v3p5") else "--"
            ax.plot(
                [float(row["exposure_s"]) for row in items],
                [float(row["flux_3sigma_ph_cm2_s"]) for row in items],
                marker="o",
                ls=style,
                label=label,
            )
    ax.axvline(1.0e6, color="0.25", lw=1.0, ls=":", label="1 Ms")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Exposure (s)")
    ax.set_ylabel("3sigma flux limit (ph cm^-2 s^-1)")
    ax.set_title("511 keV 3sigma performance comparison")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "performance_curve_comparison_1Ms.png", dpi=190)
    plt.close(fig)


def markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    one_ms_rows = [row for row in rows if abs(float(row["exposure_s"]) - 1.0e6) < 1.0e-9]
    one_ms_rows.sort(key=lambda row: float(row["flux_3sigma_ph_cm2_s"]))
    lines = [
        "# 1 Ms 3sigma Performance Curve Comparison",
        "",
        f"Status: `{summary['status']}`.",
        "",
        f"Claim level: {summary['claim_level']}.",
        "",
        "`1 Ms` here means `1,000,000 s` exposure. Flux limits are Gaussian `S/sqrt(B)=3` limits.",
        "",
        "## 1 Ms Result",
        "",
        "| rank | case | 3sigma flux ph cm^-2 s^-1 | Z at 1e-4 | method |",
        "| ---: | --- | ---: | ---: | --- |",
    ]
    for idx, row in enumerate(one_ms_rows, start=1):
        lines.append(
            f"| {idx} | {row['label']} | {fmt(float(row['flux_3sigma_ph_cm2_s']))} | {fmt(float(row['Z_at_reference_flux'])) if row['Z_at_reference_flux'] != '' else ''} | {row['method']} |"
        )
    lines.extend(
        [
            "",
            f"Best 1 Ms case: `{summary['best_one_Ms_case']['label']}` with `F_3sigma={fmt(float(summary['best_one_Ms_case']['flux_3sigma_ph_cm2_s']))} ph cm^-2 s^-1`.",
            "",
            "## Outputs",
            "",
            f"- CSV: `{summary['outputs']['csv']}`",
            f"- 511-CAM digitized CSV: `{summary['outputs']['cam511_digitized_csv']}`",
            f"- figure: `{summary['outputs']['figure']}`",
            f"- summary JSON: `{summary['outputs']['summary_json']}`",
            "",
            "## Limitations",
            "",
        ]
    )
    for item in summary["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v3p5-label", default="fullstat_v2", help="v3p5 Step08 output label to compare")
    args = ap.parse_args()

    configure_v3p5(args.v3p5_label)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, summary = build_rows()
    write_csv(OUT / "performance_curve_comparison_1Ms.csv", rows)
    write_csv(OUT / "cam511_fig11_digitized_points.csv", CAM511_DIGITIZED_POINTS)
    plot(rows)
    write_json(OUT / "performance_curve_comparison_1Ms_summary.json", summary)
    (OUT / "performance_curve_comparison_1Ms.md").write_text(markdown(summary, rows), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "best_1Ms": summary["best_one_Ms_case"], "out": rel(OUT)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
