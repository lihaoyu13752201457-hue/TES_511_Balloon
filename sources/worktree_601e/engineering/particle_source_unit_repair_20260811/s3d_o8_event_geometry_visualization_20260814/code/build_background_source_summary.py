#!/usr/bin/env python3
"""Build auditable S3d-O8 prompt/delayed background-source summaries.

The delayed table is one selected W2 detector event per row.  The prompt table
contains three active-veto W2 survivors, of which two pass the official Step05
selection.  Production-projectile/channel information is deliberately kept in
a separate output because it exists for only 25 of the 420 delayed rows and its
weight is an activation-production contribution, not a selected W2 rate.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def neff(sum_w: float, sum_w2: float) -> float:
    return float(sum_w * sum_w / sum_w2) if sum_w2 > 0 else 0.0


def grouped_rows(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    rate_column: str,
    scope: str,
    selection: str,
    dimension: str,
    evidence_class: str,
    note: str,
) -> list[dict]:
    total = float(frame[rate_column].sum())
    rows: list[dict] = []
    grouped = frame.groupby(columns, dropna=False, sort=False)[rate_column]
    records = []
    for key, weights in grouped:
        keys = key if isinstance(key, tuple) else (key,)
        sum_w = float(weights.sum())
        sum_w2 = float(np.square(weights.to_numpy(dtype=float)).sum())
        records.append((keys, len(weights), sum_w, sum_w2))
    records.sort(key=lambda item: (-item[2], tuple(str(v) for v in item[0])))
    for rank, (keys, n_rows, sum_w, sum_w2) in enumerate(records, start=1):
        labels = [f"{column}={value}" for column, value in zip(columns, keys)]
        rows.append(
            {
                "scope": scope,
                "selection": selection,
                "dimension": dimension,
                "rank": rank,
                "group_label": " | ".join(labels),
                "rows": int(n_rows),
                "rate_cps": sum_w,
                "fraction_of_selection": sum_w / total if total > 0 else np.nan,
                "sum_weight_sq_cps2": sum_w2,
                "event_neff": neff(sum_w, sum_w2),
                "evidence_class": evidence_class,
                "note": note,
            }
        )
    return rows


def main() -> None:
    delayed = pd.read_csv(DATA / "delayed_selected_event_ledger.csv")
    points = pd.read_csv(DATA / "delayed_source_point_ledger.csv")
    links = pd.read_csv(DATA / "delayed_partial_production_origin_links.csv")
    prompt = pd.read_csv(DATA / "prompt_events.csv")

    delayed_weight = "w2_rate_cps"
    prompt_weight = "event_weight_cps"
    delayed_total = float(delayed[delayed_weight].sum())
    delayed_sumw2 = float(np.square(delayed[delayed_weight]).sum())
    step05 = prompt[prompt["step05_pass"].astype(bool)].copy()
    prompt_total = float(step05[prompt_weight].sum())
    prompt_sumw2 = float(np.square(step05[prompt_weight]).sum())
    combined_total = delayed_total + prompt_total

    summary: list[dict] = []
    combined_streams = [
        ("delayed", len(delayed), delayed_total, delayed_sumw2),
        ("prompt_step05", len(step05), prompt_total, prompt_sumw2),
    ]
    combined_streams.sort(key=lambda row: -row[2])
    for rank, (label, n_rows, rate, sumw2) in enumerate(combined_streams, start=1):
        summary.append(
            {
                "scope": "combined",
                "selection": "S3d-O8 W2: delayed full + prompt Step05",
                "dimension": "stream",
                "rank": rank,
                "group_label": label,
                "rows": n_rows,
                "rate_cps": rate,
                "fraction_of_selection": rate / combined_total,
                "sum_weight_sq_cps2": sumw2,
                "event_neff": neff(rate, sumw2),
                "evidence_class": "FACT",
                "note": "Rates are comparable cps selections; prompt uses only Step05-pass events.",
            }
        )

    delayed_specs = [
        (["incident_family"], "incident_family"),
        (["exact_material"], "exact_material"),
        (["source_volume"], "source_volume"),
        (["source_isotope"], "source_isotope"),
        (
            ["source_volume", "source_isotope", "incident_family"],
            "source_volume_x_isotope_x_incident_family",
        ),
    ]
    for columns, dimension in delayed_specs:
        summary.extend(
            grouped_rows(
                delayed,
                columns,
                rate_column=delayed_weight,
                scope="delayed",
                selection="full 420-row W2 selected ledger",
                dimension=dimension,
                evidence_class="FACT",
                note=(
                    "incident_family is the activation incident-primary family branch "
                    "carried by the inventory/lineage.  It does not by itself identify "
                    "the particle that directly created the isotope."
                ),
            )
        )

    step05 = step05.assign(
        pair_to_annihilation_host=(
            step05["observed_pair_host_nearest_cc"].fillna("UNKNOWN")
            + " -> "
            + step05["observed_annihilation_host_nearest_cc"].fillna("UNKNOWN")
        )
    )
    for columns, dimension in [
        (["family"], "incident_family"),
        (["observed_pair_host_nearest_cc"], "pair_host"),
        (["observed_annihilation_host_nearest_cc"], "annihilation_host"),
        (["pair_to_annihilation_host"], "pair_to_annihilation_host"),
    ]:
        summary.extend(
            grouped_rows(
                step05,
                columns,
                rate_column=prompt_weight,
                scope="prompt",
                selection="official Step05-pass W2 prompt events",
                dimension=dimension,
                evidence_class="FACT",
                note=(
                    "Host is the nearest recorded CC deposit to the IA interaction, "
                    "matched within 0.01 cm; CC samples are not complete Geant4 paths."
                ),
            )
        )

    summary_frame = pd.DataFrame(summary)
    summary_frame.to_csv(DATA / "agent_background_source_summary.csv", index=False)

    origin = (
        links.groupby(
            ["transport_primary", "interacting_particle", "creator_process"],
            dropna=False,
        )
        .agg(
            linked_rows=("delayed_local_event_id", "size"),
            unique_linked_events=("delayed_local_event_id", "nunique"),
            production_rate_contribution_s_1=(
                "production_rate_contribution_s-1",
                "sum",
            ),
            day15_activity_contribution_Bq=(
                "day15_activity_contribution_Bq",
                "sum",
            ),
        )
        .reset_index()
        .sort_values(
            ["production_rate_contribution_s_1", "linked_rows"],
            ascending=[False, False],
        )
    )
    origin.insert(0, "rank", np.arange(1, len(origin) + 1))
    origin.insert(1, "evidence_class", "FACT_FOR_LINKED_SUBSET_ONLY")
    origin["coverage_note"] = (
        "Only 25/420 selected delayed rows have an exact production-origin link; "
        "do not extrapolate this distribution to the unscanned 395 rows."
    )
    origin.to_csv(DATA / "agent_verified_origin_links_summary.csv", index=False)

    essential = [
        "incident_family",
        "source_point_id",
        "source_isotope",
        "source_volume",
        "exact_material",
        "source_IF_x_cm",
        "source_IF_y_cm",
        "source_IF_z_cm",
        delayed_weight,
    ]
    event_key_duplicates = int(
        delayed.duplicated(["source_file", "delayed_local_event_id"]).sum()
    )
    point_key_duplicates = int(points["source_point_id"].duplicated().sum())
    point_ids_missing = sorted(set(delayed["source_point_id"]) - set(points["source_point_id"]))
    linked_events = links[["delayed_source_file", "delayed_local_event_id"]].drop_duplicates()
    top_points = points.sort_values(
        ["selected_w2_rate_cps", "source_point_id"], ascending=[False, True]
    ).head(10)

    audit = {
        "dataset_grain": {
            "delayed_selected_event_ledger": "one selected S3d-O8 W2 detector event per row",
            "delayed_source_point_ledger": "one unique delayed source coordinate/key per row",
            "prompt_events": "one traced active-veto W2 prompt survivor per row",
            "verified_origin_links": "one exact selected-event to activation-production-origin link per row",
        },
        "facts": {
            "delayed_rows": int(len(delayed)),
            "delayed_total_w2_rate_cps": delayed_total,
            "delayed_event_neff": neff(delayed_total, delayed_sumw2),
            "delayed_event_key_duplicates": event_key_duplicates,
            "delayed_essential_null_cells": int(delayed[essential].isna().sum().sum()),
            "delayed_event_weight_equals_w2_rate_all_rows": bool(
                np.allclose(delayed["event_weight_cps"], delayed[delayed_weight], rtol=0, atol=1e-15)
            ),
            "source_point_rows": int(len(points)),
            "source_point_key_duplicates": point_key_duplicates,
            "delayed_source_point_orphan_ids": point_ids_missing,
            "event_vs_point_rate_residual_cps": float(
                delayed_total - points["selected_w2_rate_cps"].sum()
            ),
            "verified_origin_link_rows": int(len(links)),
            "verified_origin_unique_selected_events": int(len(linked_events)),
            "verified_origin_selected_event_coverage": float(len(linked_events) / len(delayed)),
            "unknown_or_unlinked_selected_events": int(len(delayed) - len(linked_events)),
            "prompt_traced_active_veto_w2_rows": int(len(prompt)),
            "prompt_step05_rows": int(len(step05)),
            "prompt_step05_rate_cps": prompt_total,
            "prompt_step05_event_neff": neff(prompt_total, prompt_sumw2),
            "prompt_step05_active_deposit_zero_all_rows": bool(
                (
                    (step05["bgo_raw_sum_keV"] == 0)
                    & (step05["plastic_raw_sum_keV"] == 0)
                    & (step05["active_cc_hit_count"] == 0)
                ).all()
            ),
            "combined_delayed_plus_prompt_step05_rate_cps": combined_total,
        },
        "risk_findings": [
            {
                "severity": "HIGH",
                "confidence": "HIGH",
                "finding": (
                    "Activation projectile/channel ancestry is exact for only 25/420 "
                    "selected delayed events (5.95%)."
                ),
                "impact": (
                    "The verified-origin projectile distribution cannot be treated as "
                    "the projectile mix of all delayed W2 background."
                ),
                "required_label": "UNKNOWN for the remaining 395 rows",
            },
            {
                "severity": "HIGH",
                "confidence": "HIGH",
                "finding": (
                    "Delayed weighted evidence is low-Neff and quantized: family-specific "
                    "selected rows carry one constant event weight."
                ),
                "impact": (
                    "Single p/n/alpha events create large equal-height ranking steps; the "
                    "apparent ordering among equal-rate source points is not resolved."
                ),
            },
            {
                "severity": "HIGH",
                "confidence": "HIGH",
                "finding": "Official Step05 prompt evidence contains only two equal-weight events.",
                "impact": (
                    "Prompt-host fractions are mechanism examples, not stable population fractions."
                ),
            },
        ],
        "near_field_figure_recommendation": {
            "tes_centroid_IF_cm": [0.0, -0.0775, -5.2],
            "axial_exact_section": "Instrument-frame y'=0 exact mesh section",
            "axial_plot_range_cm": {"x_prime": [-5.1, 5.1], "z_prime": [-10.2, 2.5]},
            "point_semantics": (
                "Plot source coordinates by orthographic x'-z' projection and state each "
                "point's true y'; do not imply the point lies in the y'=0 section."
            ),
            "top10_point_ids_by_selected_w2_rate": top_points["source_point_id"].tolist(),
            "top10_tie_warning": (
                "P0060/P0061/P0062/P0063/P0064/P0065/P0066 are equal-weight single-p "
                "events; their internal rank is arbitrary."
            ),
        },
    }
    (ROOT / "audit" / "agent_background_source_summary_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    assert event_key_duplicates == 0
    assert point_key_duplicates == 0
    assert not point_ids_missing
    assert int(delayed[essential].isna().sum().sum()) == 0
    assert abs(audit["facts"]["event_vs_point_rate_residual_cps"]) < 1e-12
    assert len(linked_events) == 25
    assert len(step05) == 2
    print(DATA / "agent_background_source_summary.csv")
    print(DATA / "agent_verified_origin_links_summary.csv")
    print(ROOT / "audit" / "agent_background_source_summary_audit.json")


if __name__ == "__main__":
    main()
