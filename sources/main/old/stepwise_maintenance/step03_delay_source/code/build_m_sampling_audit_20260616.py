#!/usr/bin/env python3
"""Audit exact-position delayed-source M sampling against existing outputs."""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
OUT = ROOT / "outputs" / "reports" / "m_sampling_audit_20260616"

sys.path.insert(0, str(SCRIPT_DIR))
import build_step03_exactpos_distribution_figure as distfig  # noqa: E402

TABLE = ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/exactpos_weighted_rpip_table.csv"
TABLE_SUMMARY = ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/exactpos_weighted_rpip_summary.json"
CONVERGENCE = ROOT / "outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_summary.json"
CONVERGENCE_CASES = ROOT / "outputs/reports/v3p5_exactpos_convergence_20260614/v3p5_exactpos_convergence_cases.csv"

CASES = [
    ("M5000_seed260613", ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos/exactpos_delayed_source_manifest.json"),
    ("M5000_seed260614", ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m05000_s260614/exactpos_delayed_source_manifest.json"),
    ("M20000_seed260613", ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m20000_s260613/exactpos_delayed_source_manifest.json"),
    ("M50000_seed260613", ROOT / "runs/step02_delay_fix_v3p5_centerfinger_fullstat_v2_exactpos_m50000_s260613/exactpos_delayed_source_manifest.json"),
]


def tag_from_source_file(name: str) -> str:
    match = re.search(r"Background_([^_]+)_", name)
    return match.group(1) if match else "unknown"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fkey(za: int, x: float, y: float, z: float) -> str:
    return f"{int(za)}|{x:.6f}|{y:.6f}|{z:.6f}"


def total_variation(expected: pd.Series, observed: pd.Series) -> float:
    e, o = expected.align(observed, fill_value=0.0)
    return float(0.5 * np.abs(e - o).sum())


def weighted_quantile(values: pd.Series, weights: pd.Series, qs: list[float]) -> list[float]:
    v = values.to_numpy(dtype=float)
    w = weights.to_numpy(dtype=float)
    order = np.argsort(v)
    v = v[order]
    w = w[order]
    cdf = np.cumsum(w)
    cdf /= cdf[-1]
    return [float(np.interp(q, cdf, v)) for q in qs]


def binned_tv(values: np.ndarray, weights: np.ndarray, samples: np.ndarray, bins: int = 20) -> float:
    lo = float(np.min(values))
    hi = float(np.max(values))
    if math.isclose(lo, hi):
        return 0.0
    expected, edges = np.histogram(values, bins=bins, range=(lo, hi), weights=weights)
    observed, _ = np.histogram(samples, bins=edges)
    expected = expected / expected.sum()
    observed = observed / observed.sum()
    return float(0.5 * np.abs(expected - observed).sum())


def load_exact_table() -> pd.DataFrame:
    df = pd.read_csv(TABLE)
    df = df[df["sample_weight"] > 0].copy()
    df["ZA"] = df["ZA"].astype(int)
    df["tag"] = df["source_file"].map(tag_from_source_file)
    df["category"] = df["VN"].map(distfig.category_for_volume)
    df["nuclide"] = df["ZA"].map(distfig.nuclide_label)
    df["key"] = [fkey(za, x, y, z) for za, x, y, z in zip(df["ZA"], df["x_cm"], df["y_cm"], df["z_cm"])]
    return df


def build_lookup(df: pd.DataFrame) -> dict[str, dict]:
    grouped = (
        df.groupby(["key", "tag", "category", "VN", "ZA"], dropna=False)["sample_weight"]
        .sum()
        .reset_index()
        .sort_values(["key", "sample_weight"], ascending=[True, False])
    )
    lookup: dict[str, dict] = {}
    for key, group in grouped.groupby("key", sort=False):
        row = group.iloc[0]
        lookup[str(key)] = {
            "tag": str(row["tag"]),
            "category": str(row["category"]),
            "VN": str(row["VN"]),
            "ambiguous_matches": int(len(group)),
        }
    return lookup


def parse_source_card(path: Path) -> pd.DataFrame:
    by_id: dict[int, dict] = defaultdict(dict)
    source_ref_count = 0
    particle_re = re.compile(r"^RP_(\d+)\.ParticleType\s+(\d+)\s*$")
    beam_re = re.compile(r"^RP_(\d+)\.Beam\s+PointSource\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$")
    flux_re = re.compile(r"^RP_(\d+)\.Flux\s+([-+0-9.eE]+)\s*$")
    run_source_re = re.compile(r"^DecayRun\.Source\s+RP_(\d+)\s*$")
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if run_source_re.match(line):
                source_ref_count += 1
                continue
            m = particle_re.match(line)
            if m:
                by_id[int(m.group(1))]["ZA"] = int(m.group(2))
                continue
            m = beam_re.match(line)
            if m:
                by_id[int(m.group(1))]["x_cm"] = float(m.group(2))
                by_id[int(m.group(1))]["y_cm"] = float(m.group(3))
                by_id[int(m.group(1))]["z_cm"] = float(m.group(4))
                continue
            m = flux_re.match(line)
            if m:
                by_id[int(m.group(1))]["flux_Bq"] = float(m.group(2))
    rows = []
    for idx in sorted(by_id):
        row = by_id[idx]
        if {"ZA", "x_cm", "y_cm", "z_cm", "flux_Bq"} <= row.keys():
            rows.append({"id": idx, **row})
    df = pd.DataFrame(rows)
    if not df.empty:
        df["key"] = [fkey(za, x, y, z) for za, x, y, z in zip(df["ZA"], df["x_cm"], df["y_cm"], df["z_cm"])]
    df.attrs["source_ref_count"] = source_ref_count
    return df


def top_fraction(series: pd.Series, n: int) -> float:
    total = float(series.sum())
    if total <= 0:
        return 0.0
    return float(series.sort_values(ascending=False).head(n).sum() / total)


def summarize_exact(df: pd.DataFrame, table_summary: dict) -> dict:
    total = float(df["sample_weight"].sum())
    by_species = df.groupby("ZA")["sample_weight"].sum().sort_values(ascending=False)
    by_tag = df.groupby("tag")["sample_weight"].sum().sort_values(ascending=False)
    by_category = df.groupby("category")["sample_weight"].sum().sort_values(ascending=False)
    return {
        "table": rel(TABLE),
        "summary": rel(TABLE_SUMMARY),
        "status": table_summary.get("status"),
        "rows": int(len(df)),
        "total_activity_Bq_from_table": total,
        "fixed_total_activity_Bq_from_summary": float(table_summary["fixed_total_activity_Bq"]),
        "relative_activity_delta": float((total - float(table_summary["fixed_total_activity_Bq"])) / float(table_summary["fixed_total_activity_Bq"])),
        "species_count": int(by_species.size),
        "row_weight_effective_sample_size": float(total * total / np.sum(np.square(df["sample_weight"].to_numpy(dtype=float)))),
        "species_weight_effective_sample_size": float(total * total / np.sum(np.square(by_species.to_numpy(dtype=float)))),
        "top20_species_activity_fraction": top_fraction(by_species, 20),
        "top50_species_activity_fraction": top_fraction(by_species, 50),
        "top100_species_activity_fraction": top_fraction(by_species, 100),
        "top200_species_activity_fraction": top_fraction(by_species, 200),
        "top500_species_activity_fraction": top_fraction(by_species, 500),
        "expected_draws_at_M5000_by_incident_family": {str(k): float(5000.0 * v / total) for k, v in by_tag.items()},
        "category_activity_fraction": {str(k): float(v / total) for k, v in by_category.items()},
        "coordinate_weighted_quantiles": {
            axis: weighted_quantile(df[f"{axis}_cm"], df["sample_weight"], [0.05, 0.5, 0.95])
            for axis in ["x", "y", "z"]
        },
    }


def summarize_case(label: str, manifest_path: Path, exact: pd.DataFrame, lookup: dict[str, dict]) -> tuple[dict, dict, list[dict]]:
    manifest = json.loads(manifest_path.read_text())
    source_path = ROOT / manifest["source"]
    sample = parse_source_card(source_path)
    if sample.empty:
        raise RuntimeError(f"No source blocks parsed from {source_path}")
    source_ref_count = int(sample.attrs.get("source_ref_count", 0))

    match_rows = []
    unmatched = 0
    ambiguous = 0
    for key in sample["key"]:
        meta = lookup.get(str(key))
        if meta is None:
            unmatched += 1
            match_rows.append({"tag": "unmatched", "category": "unmatched", "VN": "unmatched", "ambiguous_matches": 0})
        else:
            ambiguous += int(meta["ambiguous_matches"] > 1)
            match_rows.append(meta)
    match = pd.DataFrame(match_rows)
    sample = pd.concat([sample.reset_index(drop=True), match.reset_index(drop=True)], axis=1)

    total_activity = float(manifest["fixed_total_activity_Bq"])
    m = int(manifest["n_pointsource_blocks"])
    exact_species = exact.groupby("ZA")["sample_weight"].sum() / total_activity
    sample_species = sample.groupby("ZA").size() / len(sample)
    exact_tag = exact.groupby("tag")["sample_weight"].sum() / total_activity
    sample_tag = sample[sample["tag"] != "unmatched"].groupby("tag").size() / len(sample)
    exact_category = exact.groupby("category")["sample_weight"].sum() / total_activity
    sample_category = sample[sample["category"] != "unmatched"].groupby("category").size() / len(sample)

    coordinate = {}
    weights = exact["sample_weight"].to_numpy(dtype=float)
    for axis in ["x", "y", "z"]:
        col = f"{axis}_cm"
        expected_mean = float(np.average(exact[col], weights=weights))
        expected_var = float(np.average((exact[col].to_numpy(dtype=float) - expected_mean) ** 2, weights=weights))
        observed_mean = float(sample[col].mean())
        stderr = math.sqrt(expected_var / m) if expected_var > 0 else 0.0
        coordinate[axis] = {
            "expected_weighted_mean_cm": expected_mean,
            "sample_mean_cm": observed_mean,
            "mean_delta_cm": observed_mean - expected_mean,
            "mean_delta_sigma": (observed_mean - expected_mean) / stderr if stderr > 0 else 0.0,
            "expected_q05_q50_q95_cm": weighted_quantile(exact[col], exact["sample_weight"], [0.05, 0.5, 0.95]),
            "sample_q05_q50_q95_cm": [float(v) for v in sample[col].quantile([0.05, 0.5, 0.95]).to_list()],
            "histogram_tv_20bin": binned_tv(exact[col].to_numpy(dtype=float), weights, sample[col].to_numpy(dtype=float), bins=20),
        }

    rows = []
    for za, expected_prob in exact_species.sort_values(ascending=False).head(20).items():
        expected = m * float(expected_prob)
        observed = int((sample["ZA"] == za).sum())
        sigma = math.sqrt(expected * (1.0 - float(expected_prob))) if expected > 0 else 0.0
        rows.append(
            {
                "case": label,
                "ZA": int(za),
                "nuclide": distfig.nuclide_label(int(za)),
                "expected_draws": expected,
                "observed_draws": observed,
                "delta_sigma": (observed - expected) / sigma if sigma > 0 else 0.0,
            }
        )

    exact_species_activity = exact.groupby("ZA")["sample_weight"].sum().sort_values(ascending=False)
    sample_species_counts = sample.groupby("ZA").size()
    missed_rows = []
    for za, activity_bq in exact_species_activity.items():
        observed = int(sample_species_counts.get(za, 0))
        if observed != 0:
            continue
        expected_draws = m * float(activity_bq) / total_activity
        family_activity = exact[exact["ZA"] == za].groupby("tag")["sample_weight"].sum().sort_values(ascending=False)
        category_activity = exact[exact["ZA"] == za].groupby("category")["sample_weight"].sum().sort_values(ascending=False)
        missed_rows.append(
            {
                "case": label,
                "M": m,
                "seed": int(manifest["seed"]),
                "ZA": int(za),
                "nuclide": distfig.nuclide_label(int(za)),
                "activity_Bq": float(activity_bq),
                "activity_fraction": float(activity_bq / total_activity),
                "expected_draws": expected_draws,
                "miss_probability_if_multinomial": float(math.exp(-expected_draws)) if expected_draws < 700 else 0.0,
                "dominant_incident_family": str(family_activity.index[0]) if len(family_activity) else "",
                "dominant_incident_family_activity_Bq": float(family_activity.iloc[0]) if len(family_activity) else 0.0,
                "dominant_category": str(category_activity.index[0]) if len(category_activity) else "",
                "dominant_category_activity_Bq": float(category_activity.iloc[0]) if len(category_activity) else 0.0,
            }
        )

    missed_total_activity = float(sum(row["activity_Bq"] for row in missed_rows))
    missed_expected_draws = float(sum(row["expected_draws"] for row in missed_rows))
    missed_by_family = defaultdict(float)
    missed_by_category = defaultdict(float)
    for row in missed_rows:
        missed_by_family[row["dominant_incident_family"]] += row["activity_Bq"]
        missed_by_category[row["dominant_category"]] += row["activity_Bq"]

    fluxes = sample["flux_Bq"].to_numpy(dtype=float)
    source_flux_sum = float(fluxes.sum())
    return (
        {
            "label": label,
            "manifest": rel(manifest_path),
            "source": rel(source_path),
            "manifest_status": manifest.get("status"),
            "sampling_audit_status": manifest.get("sampling_audit", {}).get("status"),
            "M": m,
            "seed": int(manifest["seed"]),
            "source_ref_count": source_ref_count,
            "parsed_pointsource_blocks": int(len(sample)),
            "manifest_sum_flux_Bq": float(manifest["sum_flux_check_Bq"]),
            "source_text_sum_flux_Bq": source_flux_sum,
            "source_text_flux_relative_delta": float((source_flux_sum - total_activity) / total_activity),
            "manifest_flux_relative_delta": float((float(manifest["sum_flux_check_Bq"]) - total_activity) / total_activity),
            "flux_min_Bq": float(np.min(fluxes)),
            "flux_max_Bq": float(np.max(fluxes)),
            "matched_back_to_exact_table_fraction": float(1.0 - unmatched / len(sample)),
            "ambiguous_coordinate_key_fraction": float(ambiguous / len(sample)),
            "distinct_species_drawn": int(sample["ZA"].nunique()),
            "manifest_distinct_species_drawn": int(manifest.get("distinct_species_drawn", -1)),
            "missed_nuclides_count": int(len(missed_rows)),
            "missed_nuclides_total_activity_Bq": missed_total_activity,
            "missed_nuclides_total_activity_fraction": float(missed_total_activity / total_activity),
            "missed_nuclides_expected_draws_sum": missed_expected_draws,
            "missed_nuclides_activity_Bq_by_dominant_incident_family": dict(sorted(missed_by_family.items(), key=lambda kv: kv[1], reverse=True)),
            "missed_nuclides_activity_Bq_by_dominant_category": dict(sorted(missed_by_category.items(), key=lambda kv: kv[1], reverse=True)),
            "species_total_variation": total_variation(exact_species, sample_species),
            "incident_family_total_variation": total_variation(exact_tag, sample_tag),
            "category_total_variation": total_variation(exact_category, sample_category),
            "top20_species_manifest_max_abs_sigma_delta": float(manifest.get("sampling_audit", {}).get("top20_max_abs_sigma_delta", float("nan"))),
            "top20_species_manifest_chi2": float(manifest.get("sampling_audit", {}).get("top20_expected_species_chi2", float("nan"))),
            "max_abs_coordinate_mean_sigma": float(max(abs(v["mean_delta_sigma"]) for v in coordinate.values())),
            "max_coordinate_histogram_tv_20bin": float(max(v["histogram_tv_20bin"] for v in coordinate.values())),
            "coordinate_checks": coordinate,
        },
        {f"{row['case']}|{row['ZA']}": row for row in rows},
        missed_rows,
    )


def summarize_transport() -> dict:
    conv = json.loads(CONVERGENCE.read_text())
    cases = []
    with CONVERGENCE_CASES.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("has_transport_backed_rate") == "True":
                cases.append(row)
    delayed = np.array([float(c["w2_delayed_cps"]) for c in cases])
    background = np.array([float(c["w2_background_cps"]) for c in cases])
    z20d = np.array([float(c["Z20d"]) for c in cases])
    return {
        "summary": rel(CONVERGENCE),
        "case_table": rel(CONVERGENCE_CASES),
        "status": conv.get("status"),
        "evaluation": conv.get("evaluation", {}),
        "recomputed": {
            "transport_backed_cases": len(cases),
            "w2_delayed_cps_min_max": [float(delayed.min()), float(delayed.max())],
            "w2_background_cps_min_max": [float(background.min()), float(background.max())],
            "Z20d_min_max": [float(z20d.min()), float(z20d.max())],
            "w2_delayed_relative_range": float((delayed.max() - delayed.min()) / delayed.mean()),
            "w2_background_relative_range": float((background.max() - background.min()) / background.mean()),
            "Z20d_relative_range": float((z20d.max() - z20d.min()) / z20d.mean()),
        },
        "cases": cases,
    }


def write_markdown(summary: dict, rows: list[dict], missed_rows: list[dict]) -> None:
    md = OUT / "m_sampling_audit_report.md"
    exact = summary["exact_table"]
    transport = summary["transport"]["recomputed"]
    lines = [
        "# Exact-position delayed-source M sampling audit",
        "",
        "## Conclusion",
        "",
        f"- Status: `{summary['status']}`.",
        "- Scope: validates source-card M sampling and existing transport-backed M/seed convergence; it does not run new Cosima transport.",
        f"- Exact-position table rows: {exact['rows']:,}; activity: {exact['total_activity_Bq_from_table']:.12g} Bq.",
        f"- M/seed transport-backed cases: {transport['transport_backed_cases']}; W2 background relative range: {transport['w2_background_relative_range']:.6f}; Z20d relative range: {transport['Z20d_relative_range']:.6f}.",
        "",
        "## Source-card cases",
        "",
        "| case | M | seed | flux rel. delta | match frac. | species TV | family TV | category TV | max coord mean sigma | max coord hist TV |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for c in summary["source_card_cases"]:
        lines.append(
            f"| {c['label']} | {c['M']} | {c['seed']} | {c['manifest_flux_relative_delta']:.3e} | "
            f"{c['matched_back_to_exact_table_fraction']:.6f} | {c['species_total_variation']:.4f} | "
            f"{c['incident_family_total_variation']:.4f} | {c['category_total_variation']:.4f} | "
            f"{c['max_abs_coordinate_mean_sigma']:.3f} | {c['max_coordinate_histogram_tv_20bin']:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Missed nuclides",
            "",
            "| case | missed ZA count | missed activity (Bq) | activity fraction | expected missed draws | dominant missed family | dominant missed category |",
            "|---|---:|---:|---:|---:|---|---|",
        ]
    )
    for c in summary["source_card_cases"]:
        fam = next(iter(c["missed_nuclides_activity_Bq_by_dominant_incident_family"]), "")
        cat = next(iter(c["missed_nuclides_activity_Bq_by_dominant_category"]), "")
        lines.append(
            f"| {c['label']} | {c['missed_nuclides_count']} | {c['missed_nuclides_total_activity_Bq']:.6g} | "
            f"{c['missed_nuclides_total_activity_fraction']:.3e} | {c['missed_nuclides_expected_draws_sum']:.3f} | "
            f"{fam} | {cat} |"
        )
    lines.extend(
        [
            "",
            f"Detailed missed-nuclide rows are written to `{summary['outputs']['missed_nuclides_csv']}`.",
            "",
            "## Transport convergence",
            "",
            f"- Delayed W2 rate range: {transport['w2_delayed_cps_min_max'][0]:.8g}--{transport['w2_delayed_cps_min_max'][1]:.8g} s^-1.",
            f"- Total W2 background range: {transport['w2_background_cps_min_max'][0]:.8g}--{transport['w2_background_cps_min_max'][1]:.8g} s^-1.",
            f"- Z20d range: {transport['Z20d_min_max'][0]:.8g}--{transport['Z20d_min_max'][1]:.8g}.",
            "",
            "## Interpretation",
            "",
            "- M=5000 is not a full enumeration of all rare RPIP rows/species, and should not be used to claim convergence of every rare isotope or spatial subpopulation.",
            "- For the current hard-window rate and 20-day sensitivity, the activity is exactly conserved in the manifest and the existing M/seed transport sweep keeps the total W2 background and Z20d within the acceptance criteria recorded in the convergence summary.",
        ]
    )
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with (OUT / "m_sampling_audit_top20_species_deviation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["case", "ZA", "nuclide", "expected_draws", "observed_draws", "delta_sigma"],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)

    missed_fields = [
        "case",
        "M",
        "seed",
        "ZA",
        "nuclide",
        "activity_Bq",
        "activity_fraction",
        "expected_draws",
        "miss_probability_if_multinomial",
        "dominant_incident_family",
        "dominant_incident_family_activity_Bq",
        "dominant_category",
        "dominant_category_activity_Bq",
    ]
    with (OUT / "m_sampling_audit_missed_nuclides.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=missed_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(missed_rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    exact = load_exact_table()
    lookup = build_lookup(exact)
    table_summary = json.loads(TABLE_SUMMARY.read_text())

    case_summaries = []
    top_rows = []
    missed_rows = []
    for label, manifest_path in CASES:
        case_summary, rows_by_key, case_missed_rows = summarize_case(label, manifest_path, exact, lookup)
        case_summaries.append(case_summary)
        top_rows.extend(rows_by_key.values())
        missed_rows.extend(case_missed_rows)

    transport = summarize_transport()
    problems = []
    if abs(summarize_exact(exact, table_summary)["relative_activity_delta"]) > 1e-10:
        problems.append("exact table activity does not match fixed source total")
    for c in case_summaries:
        if c["parsed_pointsource_blocks"] != c["M"] or c["source_ref_count"] != c["M"]:
            problems.append(f"{c['label']} source block count mismatch")
        if abs(c["manifest_flux_relative_delta"]) > 1e-14:
            problems.append(f"{c['label']} manifest flux is not exactly conserved")
        if c["matched_back_to_exact_table_fraction"] < 0.999:
            problems.append(f"{c['label']} source positions do not match exact table")
    evaluation = transport["evaluation"]
    if evaluation.get("status") != "PASS_EXACTPOS_TRANSPORT_CONVERGENCE":
        problems.append("transport convergence summary is not PASS")

    summary = {
        "status": "PASS_M_SAMPLING_AUDIT" if not problems else "FAIL_M_SAMPLING_AUDIT",
        "scope": "Source-card M sampling plus existing transport-backed M/seed convergence for exact-position delayed activation.",
        "exact_table": summarize_exact(exact, table_summary),
        "source_card_cases": case_summaries,
        "transport": transport,
        "problems": problems,
        "outputs": {
            "summary_json": rel(OUT / "m_sampling_audit_summary.json"),
            "report_md": rel(OUT / "m_sampling_audit_report.md"),
            "top20_species_deviation_csv": rel(OUT / "m_sampling_audit_top20_species_deviation.csv"),
            "missed_nuclides_csv": rel(OUT / "m_sampling_audit_missed_nuclides.csv"),
        },
    }
    (OUT / "m_sampling_audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown(summary, top_rows, missed_rows)
    print(json.dumps({"status": summary["status"], "outputs": summary["outputs"]}, indent=2))


if __name__ == "__main__":
    main()
