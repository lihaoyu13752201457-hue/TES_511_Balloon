#!/usr/bin/env python3
"""Build an auditable deep breakdown of the top-five delayed W2 hosts.

The output deliberately keeps three different notions separate:

1. ``incident_family``: the external activation/inventory branch;
2. exact linked ``interacting_particle`` and ``creator_process``: the particle
   and Geant4 process at the retained isotope-production vertex; and
3. delayed-transport ``has_annihilation_ia``/``has_pair_ia`` event flags.

The exact-production scan covers only a subset and therefore never fills
missing direct mechanisms by inference.
"""

from __future__ import annotations

import json
import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
AUDIT = ROOT / "audit"
CATALOG = Path(
    "/home/ubuntu/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813/outputs/03_delayed/catalog/S3d_O8"
)
MATERIALS = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/"
    "geometry/Materials_DEMO2_DR_v3p5.geo"
)


def neff(weights: pd.Series) -> float:
    total = float(weights.sum())
    total_sq = float(np.square(weights.to_numpy(float)).sum())
    return total * total / total_sq if total_sq else 0.0


def compact_flags() -> dict[tuple[str, int, str], tuple[bool, bool]]:
    result: dict[tuple[str, int, str], tuple[bool, bool]] = {}
    for path in sorted(CATALOG.glob("*.pkl")):
        with path.open("rb") as handle:
            payload = pickle.load(handle)
        for index in range(len(payload["local_id"])):
            key = (
                str(payload["tag"][index]),
                int(payload["local_id"][index]),
                str(payload["source_file"][index]),
            )
            if key in result:
                raise RuntimeError(f"duplicate compact key: {key}")
            result[key] = (
                bool(payload["has_pair_ia"][index]),
                bool(payload["has_annihilation_ia"][index]),
            )
    return result


def material_definition(material: str) -> str:
    lines = MATERIALS.read_text().splitlines()
    density = None
    components: list[str] = []
    for raw in lines:
        fields = raw.split()
        if not fields:
            continue
        if fields[0] == f"{material}.Density" and len(fields) >= 2:
            density = fields[1]
        elif fields[0] == f"{material}.Component" and len(fields) >= 3:
            components.append(f"{fields[1]}:{fields[2]}")
    if not components and material == "Copper":
        return "MEGAlib standard Copper"
    return f"density={density} g/cm3; components=" + ",".join(components)


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    delayed = pd.read_csv(DATA / "delayed_selected_event_ledger.csv")
    origins = pd.read_csv(DATA / "delayed_partial_production_origin_links.csv")
    flags = compact_flags()
    keys = [
        (str(row.incident_family), int(row.delayed_local_event_id), str(row.source_file))
        for row in delayed.itertuples(index=False)
    ]
    missing = [key for key in keys if key not in flags]
    if missing:
        raise RuntimeError(f"missing compact flags: {missing[:3]}")
    delayed[["has_pair_ia", "has_annihilation_ia"]] = [flags[key] for key in keys]

    volume_rates = delayed.groupby("source_volume")["w2_rate_cps"].sum().sort_values(ascending=False)
    top5 = list(volume_rates.head(5).index)
    total_rate = float(delayed["w2_rate_cps"].sum())

    matrix_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    mechanism_rows: list[dict[str, object]] = []

    origin_key = ["incident_family", "delayed_source_file", "delayed_local_event_id"]
    delayed_key = ["incident_family", "source_file", "delayed_local_event_id"]
    origin_join = origins.merge(
        delayed[delayed_key + ["w2_rate_cps"]],
        left_on=origin_key,
        right_on=delayed_key,
        how="left",
        validate="one_to_one",
    )
    if origin_join["w2_rate_cps"].isna().any():
        raise RuntimeError("exact origin link orphan")

    for rank, volume in enumerate(top5, 1):
        selected = delayed[delayed["source_volume"] == volume].copy()
        rate = float(selected["w2_rate_cps"].sum())
        linked = origin_join[origin_join["source_volume"] == volume].copy()
        linked_rate = float(linked["w2_rate_cps"].sum())

        by_iso_family = (
            selected.groupby(["source_isotope", "incident_family"], as_index=False)
            .agg(rows=("w2_rate_cps", "size"), w2_rate_cps=("w2_rate_cps", "sum"))
            .sort_values("w2_rate_cps", ascending=False)
        )
        for row in by_iso_family.itertuples(index=False):
            matrix_rows.append(
                {
                    "rank": rank,
                    "source_volume": volume,
                    "exact_material": selected["exact_material"].iloc[0],
                    "source_isotope": row.source_isotope,
                    "incident_family": row.incident_family,
                    "selected_rows": int(row.rows),
                    "w2_rate_cps": float(row.w2_rate_cps),
                    "fraction_of_volume_w2": float(row.w2_rate_cps) / rate,
                    "fraction_of_full_delayed_w2": float(row.w2_rate_cps) / total_rate,
                    "direct_production_semantics": (
                        "UNKNOWN unless a matching row exists in delayed_top5_exact_production_mechanisms.csv"
                    ),
                }
            )

        grouped_mechanisms = (
            linked.groupby(
                [
                    "transport_primary",
                    "interacting_particle",
                    "creator_process",
                    "source_isotope",
                ],
                as_index=False,
            )
            .agg(linked_rows=("w2_rate_cps", "size"), linked_w2_rate_cps=("w2_rate_cps", "sum"))
            .sort_values("linked_w2_rate_cps", ascending=False)
        )
        for row in grouped_mechanisms.itertuples(index=False):
            mechanism_rows.append(
                {
                    "rank": rank,
                    "source_volume": volume,
                    "exact_material": selected["exact_material"].iloc[0],
                    "source_isotope": row.source_isotope,
                    "transport_primary": row.transport_primary,
                    "interacting_particle": row.interacting_particle,
                    "creator_process": row.creator_process,
                    "linked_rows": int(row.linked_rows),
                    "linked_w2_rate_cps": float(row.linked_w2_rate_cps),
                    "fraction_of_volume_w2_exact_linked_to_this_mechanism": float(
                        row.linked_w2_rate_cps
                    )
                    / rate,
                    "evidence_class": "FACT_FOR_EXACT_LINKED_SELECTED_EVENTS_ONLY",
                }
            )

        isotope_text = "; ".join(
            f"{iso}={value:.9g} cps ({100*value/rate:.2f}%)"
            for iso, value in selected.groupby("source_isotope")["w2_rate_cps"]
            .sum()
            .sort_values(ascending=False)
            .items()
        )
        family_text = "; ".join(
            f"{family}={value:.9g} cps ({100*value/rate:.2f}%)"
            for family, value in selected.groupby("incident_family")["w2_rate_cps"]
            .sum()
            .sort_values(ascending=False)
            .items()
        )
        mechanism_text = "; ".join(
            f"{row.transport_primary}->{row.interacting_particle}/{row.creator_process}"
            f"->{row.source_isotope}: {row.linked_w2_rate_cps:.9g} cps"
            for row in grouped_mechanisms.itertuples(index=False)
        )
        summary_rows.append(
            {
                "rank": rank,
                "source_volume": volume,
                "exact_material": selected["exact_material"].iloc[0],
                "material_definition": material_definition(str(selected["exact_material"].iloc[0])),
                "selected_rows": len(selected),
                "selected_event_neff": neff(selected["w2_rate_cps"]),
                "w2_rate_cps": rate,
                "fraction_of_full_delayed_w2": rate / total_rate,
                "parent_isotope_breakdown": isotope_text,
                "incident_family_breakdown": family_text,
                "compact_has_annihilation_rows": int(selected["has_annihilation_ia"].sum()),
                "compact_has_pair_rows": int(selected["has_pair_ia"].sum()),
                "exact_origin_linked_rows": len(linked),
                "exact_origin_linked_w2_rate_cps": linked_rate,
                "exact_origin_linked_fraction_of_volume_w2": linked_rate / rate,
                "exact_linked_direct_mechanisms": mechanism_text,
                "entry_interpretation": (
                    "All selected events contain ANNI and no PAIR IA: near-field beta+ annihilation is the supported W2 mechanism. "
                    "The compact flag alone does not prove the specific annihilation photon is the TES ancestor."
                ),
            }
        )

    summary = pd.DataFrame(summary_rows)
    matrix = pd.DataFrame(matrix_rows)
    mechanisms = pd.DataFrame(mechanism_rows)
    summary.to_csv(DATA / "delayed_top5_chain_summary.csv", index=False)
    matrix.to_csv(DATA / "delayed_top5_isotope_family_matrix.csv", index=False)
    mechanisms.to_csv(DATA / "delayed_top5_exact_production_mechanisms.csv", index=False)

    top_selected = delayed[delayed["source_volume"].isin(top5)]
    checks = {
        "full_delayed_rows_420": len(delayed) == 420,
        "full_delayed_rate": math.isclose(total_rate, 0.05447975222726722, abs_tol=1.0e-12),
        "top5_rows_205": len(top_selected) == 205,
        "top5_rate": math.isclose(float(top_selected["w2_rate_cps"].sum()), 0.042210754475009174, abs_tol=1.0e-12),
        "top5_all_have_annihilation_ia": bool(top_selected["has_annihilation_ia"].all()),
        "top5_no_pair_ia": bool((~top_selected["has_pair_ia"]).all()),
        "top5_exact_origin_link_rows_22": len(origin_join[origin_join["source_volume"].isin(top5)]) == 22,
        "all_summary_numeric_finite": bool(
            np.isfinite(summary.select_dtypes(include=[np.number]).to_numpy()).all()
        ),
    }
    payload = {
        "status": "PASS_DELAYED_TOP5_CHAIN_AUDIT" if all(checks.values()) else "FAIL_DELAYED_TOP5_CHAIN_AUDIT",
        "checks": checks,
        "top5_fraction_of_full_delayed_w2": float(top_selected["w2_rate_cps"].sum()) / total_rate,
        "top5_exact_origin_linked_w2_fraction": float(
            origin_join[origin_join["source_volume"].isin(top5)]["w2_rate_cps"].sum()
        )
        / float(top_selected["w2_rate_cps"].sum()),
        "evidence_boundary": {
            "incident_family": "external activation/inventory branch; not necessarily the direct isotope-producing particle",
            "exact_origin": "direct interacting particle/process only for 22 exact-linked selected events in the top five",
            "annihilation_flag": "event contains ANNI IA; specific TES ancestry requires raw IA-to-HTsim tracing",
        },
    }
    with (AUDIT / "delayed_top5_chain_validation.json").open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    if not all(checks.values()):
        raise SystemExit(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
