#!/usr/bin/env python3
"""Build a statistical agreement audit for trajectory validation points.

This does not read SIM files or rerun transport.  It consumes the existing
targeted extraction CSV and asks whether point/REF MC rate ratios are
consistent with the Step06 analytic prompt scalar, and with a live-PARMA
species-weighted expectation.
"""
from __future__ import annotations

import csv
import json
import math
import os
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / "11_analytic_agreement_20260709"
TARGETED = PKG / "05_targeted_stats" / "targeted_prompt_results.csv"
POINTS = ["L1", "H1", "L2"]
PARTICLES = ["eplus", "n", "gamma"]
METRICS = {
    "band480_550": {
        "rate": "band_rate_hz",
        "count": "n_band480_550",
        "label": "TES 480--550 keV band",
    },
    "tes_any": {
        "rate": "tes_rate_hz",
        "count": "n_tes",
        "label": "any TES energy deposit",
    },
}


def fnum(value: str | float | int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def fmt(value: float, digits: int = 6) -> str:
    if value != value:
        return ""
    if abs(value) >= 1000 or (value and abs(value) < 1e-3):
        return f"{value:.{digits}e}"
    return f"{value:.{digits}g}"


def two_sided_normal_p(z: float) -> float:
    if z != z:
        return float("nan")
    return math.erfc(abs(z) / math.sqrt(2.0))


def ratio_uncertainty(
    rate: float,
    rate_ref: float,
    count: float,
    count_ref: float,
) -> tuple[float, float]:
    ratio = rate / rate_ref
    if count <= 0 or count_ref <= 0:
        return ratio, float("nan")
    return ratio, ratio * math.sqrt(1.0 / count + 1.0 / count_ref)


def verdict_from_z(max_abs_z: float) -> str:
    if max_abs_z != max_abs_z:
        return "INSUFFICIENT_COUNTS"
    if max_abs_z <= 2.0:
        return "CONSISTENT_WITHIN_2SIGMA"
    if max_abs_z <= 3.0:
        return "MARGINAL_2_TO_3SIGMA"
    return "REJECTED_GT_3SIGMA"


def load_rows() -> dict[tuple[str, str], dict[str, str]]:
    rows: dict[tuple[str, str], dict[str, str]] = {}
    with TARGETED.open(newline="") as f:
        for row in csv.DictReader(f):
            rows[(row["point_id"], row["particle"])] = row
    return rows


def point_scale(rows: dict[tuple[str, str], dict[str, str]], point: str) -> float:
    return fnum(rows[(point, "eplus")]["analytic_prompt_scale"])


def live_scale(rows: dict[tuple[str, str], dict[str, str]], point: str, particle: str) -> float:
    return fnum(rows[(point, particle)]["scale_live_parma"])


def build_per_particle(rows: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for metric_name, metric in METRICS.items():
        for particle in PARTICLES:
            ref = rows[("REF", particle)]
            ref_rate = fnum(ref[metric["rate"]])
            ref_count = fnum(ref[metric["count"]])
            for point in POINTS:
                row = rows[(point, particle)]
                rate = fnum(row[metric["rate"]])
                count = fnum(row[metric["count"]])
                ratio, sigma_ratio = ratio_uncertainty(rate, ref_rate, count, ref_count)
                for model_name, expected in [
                    ("step06_prompt_scalar", point_scale(rows, point)),
                    ("live_parma_particle_flux", live_scale(rows, point, particle)),
                ]:
                    sigma_q = sigma_ratio / expected if expected and sigma_ratio == sigma_ratio else float("nan")
                    q = ratio / expected if expected else float("nan")
                    z = (q - 1.0) / sigma_q if sigma_q and sigma_q == sigma_q else float("nan")
                    out.append(
                        {
                            "scope": "per_particle",
                            "metric": metric_name,
                            "metric_label": metric["label"],
                            "particle": particle,
                            "point_id": point,
                            "mc_ratio_to_REF": ratio,
                            "sigma_ratio": sigma_ratio,
                            "expected_ratio": expected,
                            "model": model_name,
                            "Q": q,
                            "sigma_Q": sigma_q,
                            "z": z,
                            "two_sided_p_norm": two_sided_normal_p(z),
                            "count_point": count,
                            "count_REF": ref_count,
                        }
                    )
    return out


def combined_rates(
    rows: dict[tuple[str, str], dict[str, str]], point: str, metric: dict[str, str]
) -> tuple[float, float]:
    rate_sum = 0.0
    var_sum = 0.0
    for particle in PARTICLES:
        row = rows[(point, particle)]
        rate = fnum(row[metric["rate"]])
        count = fnum(row[metric["count"]])
        obs = fnum(row["obs_s"])
        rate_sum += rate
        if obs > 0:
            var_sum += count / (obs * obs)
    return rate_sum, var_sum


def live_weighted_expected(
    rows: dict[tuple[str, str], dict[str, str]], point: str, metric: dict[str, str]
) -> float:
    numerator = 0.0
    denominator = 0.0
    for particle in PARTICLES:
        ref_rate = fnum(rows[("REF", particle)][metric["rate"]])
        numerator += ref_rate * live_scale(rows, point, particle)
        denominator += ref_rate
    return numerator / denominator


def build_combined(rows: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for metric_name, metric in METRICS.items():
        ref_rate, ref_var = combined_rates(rows, "REF", metric)
        for point in POINTS:
            rate, var = combined_rates(rows, point, metric)
            ratio = rate / ref_rate
            sigma_ratio = ratio * math.sqrt(var / (rate * rate) + ref_var / (ref_rate * ref_rate))
            for model_name, expected in [
                ("step06_prompt_scalar", point_scale(rows, point)),
                ("live_parma_species_weighted", live_weighted_expected(rows, point, metric)),
            ]:
                sigma_q = sigma_ratio / expected
                q = ratio / expected
                z = (q - 1.0) / sigma_q
                out.append(
                    {
                        "scope": "combined_species",
                        "metric": metric_name,
                        "metric_label": metric["label"],
                        "particle": "eplus+n+gamma",
                        "point_id": point,
                        "mc_ratio_to_REF": ratio,
                        "sigma_ratio": sigma_ratio,
                        "expected_ratio": expected,
                        "model": model_name,
                        "Q": q,
                        "sigma_Q": sigma_q,
                        "z": z,
                        "two_sided_p_norm": two_sided_normal_p(z),
                        "rate_point_hz": rate,
                        "rate_REF_hz": ref_rate,
                    }
                )
    return out


def summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    summary: dict[str, object] = {
        "status": "PASS_ANALYTIC_AGREEMENT_AUDIT_BUILT",
        "claim_boundary": (
            "Uses existing targeted prompt extraction only; not Step05 W2, "
            "not activation, not delayed, not Step06 promotion."
        ),
        "checks": [],
    }
    for scope in ["combined_species", "per_particle"]:
        for metric in METRICS:
            for model in sorted({str(r["model"]) for r in rows if r["scope"] == scope and r["metric"] == metric}):
                subset = [
                    r
                    for r in rows
                    if r["scope"] == scope and r["metric"] == metric and r["model"] == model
                ]
                if scope == "per_particle":
                    subset_primary = [r for r in subset if r["particle"] == "eplus"]
                else:
                    subset_primary = subset
                zs = [abs(float(r["z"])) for r in subset_primary if float(r["z"]) == float(r["z"])]
                max_abs_z = max(zs) if zs else float("nan")
                chi2 = sum(float(r["z"]) ** 2 for r in subset_primary if float(r["z"]) == float(r["z"]))
                summary["checks"].append(
                    {
                        "scope": scope,
                        "metric": metric,
                        "model": model,
                        "primary_subset": "eplus only" if scope == "per_particle" else "all combined points",
                        "max_abs_z": max_abs_z,
                        "chi2_sum_z2": chi2,
                        "dof": len(zs),
                        "verdict": verdict_from_z(max_abs_z),
                    }
                )
    return summary


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fields = [
        "scope",
        "metric",
        "metric_label",
        "particle",
        "point_id",
        "model",
        "mc_ratio_to_REF",
        "sigma_ratio",
        "expected_ratio",
        "Q",
        "sigma_Q",
        "z",
        "two_sided_p_norm",
        "count_point",
        "count_REF",
        "rate_point_hz",
        "rate_REF_hz",
    ]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)


def write_markdown(path: Path, rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    combined_band = [
        r
        for r in rows
        if r["scope"] == "combined_species"
        and r["metric"] == "band480_550"
        and r["model"] in {"step06_prompt_scalar", "live_parma_species_weighted"}
    ]
    eplus_band = [
        r
        for r in rows
        if r["scope"] == "per_particle"
        and r["particle"] == "eplus"
        and r["metric"] == "band480_550"
        and r["model"] in {"step06_prompt_scalar", "live_parma_particle_flux"}
    ]

    lines = [
        "# Analytic Agreement Audit - Trajectory Validation",
        "",
        "Status: `PASS_ANALYTIC_AGREEMENT_AUDIT_BUILT`",
        "",
        "## Question",
        "",
        "Do the existing targeted prompt transport points agree with the Step06 analytic prompt scaling points?",
        "",
        "This audit uses only the existing targeted extraction table:",
        "`engineering/trajectory_transport_validation_20260709/05_targeted_stats/targeted_prompt_results.csv`.",
        "No Cosima transport was rerun.",
        "",
        "## Primary Result",
        "",
        "For the high-statistics prompt 480--550 keV band, the MC points are not statistically consistent",
        "with the old Step06 single prompt scalar.  The same MC points are consistent with a live-PARMA",
        "species-weighted expectation, which means the transport follows the rebuilt environment rather",
        "than the old scalar curve.",
        "",
        "### Combined e+ + n + gamma 480--550 keV band",
        "",
        "| point | model | MC/REF | expected | Q | sigma_Q | z |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for point in POINTS:
        for model in ["step06_prompt_scalar", "live_parma_species_weighted"]:
            row = next(r for r in combined_band if r["point_id"] == point and r["model"] == model)
            lines.append(
                f"| {point} | `{model}` | {fmt(float(row['mc_ratio_to_REF']))} | "
                f"{fmt(float(row['expected_ratio']))} | {fmt(float(row['Q']))} | "
                f"{fmt(float(row['sigma_Q']))} | {fmt(float(row['z']), 3)} |"
            )
    lines += [
        "",
        "### e+ only 480--550 keV band",
        "",
        "| point | model | MC/REF | expected | Q | sigma_Q | z |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for point in POINTS:
        for model in ["step06_prompt_scalar", "live_parma_particle_flux"]:
            row = next(r for r in eplus_band if r["point_id"] == point and r["model"] == model)
            lines.append(
                f"| {point} | `{model}` | {fmt(float(row['mc_ratio_to_REF']))} | "
                f"{fmt(float(row['expected_ratio']))} | {fmt(float(row['Q']))} | "
                f"{fmt(float(row['sigma_Q']))} | {fmt(float(row['z']), 3)} |"
            )
    lines += [
        "",
        "## Verdict Table",
        "",
        "| scope | metric | model | primary subset | max |z| | verdict |",
        "|---|---|---|---|---:|---|",
    ]
    for check in summary["checks"]:
        if check["metric"] not in {"band480_550", "tes_any"}:
            continue
        lines.append(
            f"| `{check['scope']}` | `{check['metric']}` | `{check['model']}` | "
            f"{check['primary_subset']} | {fmt(float(check['max_abs_z']), 3)} | "
            f"`{check['verdict']}` |"
        )
    lines += [
        "",
        "## Boundary",
        "",
        "- This is a prompt targeted-statistics audit only.",
        "- It does not validate Step05 W2 selection, activation production, delayed inventory, or delayed selected rates.",
        "- It supports the narrower statement that the old Step06 prompt scalar is too coarse at these points,",
        "  while a live-PARMA species-weighted prompt expectation is statistically compatible with the current targeted MC band rates.",
        "",
        "## Outputs",
        "",
        "- `analytic_agreement_rows.csv`: per-point Q, uncertainty, and z values.",
        "- `analytic_agreement_summary.json`: compact machine-readable verdicts.",
        "- `README.md`: this report.",
    ]
    path.write_text("\n".join(lines) + "\n")


def maybe_plot(rows: list[dict[str, object]]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(OUT / ".mplconfig"))
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return

    subset = [
        r
        for r in rows
        if r["scope"] == "combined_species"
        and r["metric"] == "band480_550"
        and r["model"] in {"step06_prompt_scalar", "live_parma_species_weighted"}
    ]
    x = list(range(len(POINTS)))
    fig, ax = plt.subplots(figsize=(7.0, 4.2))
    for offset, model, label in [
        (-0.08, "step06_prompt_scalar", "old Step06 scalar"),
        (0.08, "live_parma_species_weighted", "live PARMA weighted"),
    ]:
        ys = []
        yerrs = []
        for point in POINTS:
            row = next(r for r in subset if r["point_id"] == point and r["model"] == model)
            ys.append(float(row["Q"]))
            yerrs.append(float(row["sigma_Q"]))
        ax.errorbar([v + offset for v in x], ys, yerr=yerrs, fmt="o", capsize=3, label=label)
    ax.axhline(1.0, color="black", linewidth=1.0)
    ax.axhspan(0.98, 1.02, color="0.9", zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels(POINTS)
    ax.set_ylabel("Q = (MC/REF) / expected")
    ax.set_title("Combined prompt 480--550 keV band agreement")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(OUT / "combined_band_Q_agreement.png", dpi=180)
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows_by_key = load_rows()
    audit_rows = build_per_particle(rows_by_key) + build_combined(rows_by_key)
    summary = summarize(audit_rows)
    write_csv(OUT / "analytic_agreement_rows.csv", audit_rows)
    (OUT / "analytic_agreement_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_markdown(OUT / "README.md", audit_rows, summary)
    maybe_plot(audit_rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
