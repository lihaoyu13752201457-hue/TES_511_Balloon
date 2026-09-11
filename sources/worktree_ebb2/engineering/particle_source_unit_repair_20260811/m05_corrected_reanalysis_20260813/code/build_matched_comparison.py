#!/usr/bin/env python3
"""Build the day-15 M05 reference budget and matched geometry comparison."""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import check_inputs


HERE = Path(__file__).resolve()
PACKAGE = HERE.parent.parent
ROOT = check_inputs.ROOT
COMMON = PACKAGE / "outputs/04_common_response"
ACTIVATION = PACKAGE / "outputs/02_activation/day15_inventory.csv"
OUTPUT = PACKAGE / "outputs/05_matched_comparison"
GEOMETRIES = ("Mass_model_511", "S3d_O8")
FAMILIES = ("p", "n", "alpha", "gamma", "eminus", "eplus", "muminus", "muplus")
ELEMENTS = (
    "n", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og",
)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def isotope_label(za: int) -> str:
    z, a = divmod(za, 1000)
    return f"{ELEMENTS[z]}-{a}"


def aggregate(
    rows: list[dict[str, str]], keys: tuple[str, ...], total_by_geometry: dict[str, float],
    stream_total: dict[tuple[str, str], float] | None = None,
) -> list[dict[str, Any]]:
    groups: defaultdict[tuple[str, ...], list[float]] = defaultdict(lambda: [0.0, 0.0, 0.0])
    for row in rows:
        key = tuple(row[name] for name in keys)
        weight = float(row["event_weight_cps"])
        groups[key][0] += 1
        groups[key][1] += weight
        groups[key][2] += weight * weight
    output = []
    for key, value in groups.items():
        record: dict[str, Any] = {name: item for name, item in zip(keys, key)}
        geometry = record["geometry"]
        record.update(
            {
                "selected_events": int(value[0]),
                "rate_cps": value[1],
                "rate_stat_sigma_cps": math.sqrt(value[2]),
                "fraction_of_total_background": value[1] / total_by_geometry[geometry],
            }
        )
        if stream_total is not None and "stream" in record:
            record["fraction_of_stream"] = value[1] / stream_total[(geometry, record["stream"])]
        output.append(record)
    return sorted(output, key=lambda row: (GEOMETRIES.index(row["geometry"]), -row["rate_cps"], *(str(row[name]) for name in keys[1:])))


def support_flag(events: int) -> str:
    if events == 0:
        return "ZERO_MC_SURVIVOR__USE_UPPER_LIMIT"
    if events < 10:
        return "LOW_MC_SUPPORT"
    return "FINITE_MC_SUPPORT"


def ratio_with_independent_mc_sigma(numerator: float, numerator_sigma: float, denominator: float, denominator_sigma: float) -> tuple[float, float]:
    ratio = numerator / denominator
    sigma = ratio * math.sqrt((numerator_sigma / numerator) ** 2 + (denominator_sigma / denominator) ** 2)
    return ratio, sigma


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f".{output.name}.work-", dir=output.parent))
    try:
        common_summary = json.loads((COMMON / "summary.json").read_text(encoding="utf-8"))
        activation_summary = json.loads((ACTIVATION.parent / "day15_summary.json").read_text(encoding="utf-8"))
        lineage = read_csv(COMMON / "selected_background_w2_lineage.csv")
        cutflow = read_csv(COMMON / "common_cutflow.csv")
        background = read_csv(COMMON / "background_prompt_delayed_cutflow.csv")
        signal = read_csv(COMMON / "signal_acceptance_effective_area.csv")
        paired_signal = read_csv(COMMON / "signal_paired_comparison.csv")
        psf = read_csv(COMMON / "signal_psf.csv")
        inventory = read_csv(ACTIVATION)

        final_background = {
            (row["geometry"], row["window_id"]): row
            for row in background
            if row["response_state"] == "measured" and row["stage"] == "side_compton_fov_pass"
        }
        final_signal = {
            (row["geometry"], row["window_id"]): row
            for row in signal
            if row["response_state"] == "measured" and row["stage"] == "side_compton_fov_pass"
        }
        total_by_geometry = {
            geometry: float(final_background[(geometry, "w2_510p58_511p42")]["total_background_rate_cps"])
            for geometry in GEOMETRIES
        }
        final_components = [
            row for row in cutflow
            if row["response_state"] == "measured" and row["stage"] == "side_compton_fov_pass"
            and row["window_id"] == "w2_510p58_511p42" and row["stream"] in {"prompt", "delayed"}
        ]
        component = {(row["geometry"], row["stream"], row["family"]): row for row in final_components}
        stream_total = {
            (geometry, stream): sum(float(component[(geometry, stream, family)]["weighted_value"]) for family in FAMILIES)
            for geometry in GEOMETRIES for stream in ("prompt", "delayed")
        }
        family_budget = []
        for geometry in GEOMETRIES:
            for stream in ("prompt", "delayed"):
                for family in FAMILIES:
                    row = component[(geometry, stream, family)]
                    events = int(row["selected_events"])
                    rate = float(row["weighted_value"])
                    family_budget.append(
                        {
                            "geometry": geometry, "stream": stream, "family": family,
                            "selected_events": events, "rate_cps": rate,
                            "rate_stat_sigma_cps": float(row["weighted_stat_sigma"]),
                            "rate_lower95_cps": float(row["weighted_lower95"]),
                            "rate_upper95_cps": float(row["weighted_upper95"]),
                            "fraction_of_stream": rate / stream_total[(geometry, stream)],
                            "fraction_of_total_background": rate / total_by_geometry[geometry],
                            "support_flag": support_flag(events),
                        }
                    )
        delayed = [row for row in lineage if row["stream"] == "delayed"]
        material = {(row["geometry"], row["source_volume"]): row["material_category"] for row in inventory}
        half_life: dict[int, float] = {}
        for row in inventory:
            if row["source_disposition"] == "transported_ground_state":
                half_life[int(row["source_parent_ZA"])] = float(row["half_life_s"])
        for row in delayed:
            row["material_category"] = material[(row["geometry"], row["source_volume"])]
            za = int(row["source_parent_ZA"])
            row["isotope_label"] = isotope_label(za)
            row["half_life_s"] = str(half_life[za])

        parent = aggregate(delayed, ("geometry", "source_parent_ZA", "isotope_label", "half_life_s"), total_by_geometry)
        material_rows = aggregate(delayed, ("geometry", "material_category"), total_by_geometry)
        volume = aggregate(delayed, ("geometry", "source_volume", "material_category"), total_by_geometry)
        delayed_family = [row for row in family_budget if row["stream"] == "delayed"]
        for collection in (parent, material_rows, volume):
            for row in collection:
                row["fraction_of_delayed"] = row["rate_cps"] / stream_total[(row["geometry"], "delayed")]

        all_materials = sorted({row["material_category"] for row in inventory})
        present_materials = {(row["geometry"], row["material_category"]) for row in material_rows}
        for geometry in GEOMETRIES:
            for category in all_materials:
                if (geometry, category) not in present_materials:
                    material_rows.append(
                        {
                            "geometry": geometry, "material_category": category, "selected_events": 0,
                            "rate_cps": 0.0, "rate_stat_sigma_cps": 0.0,
                            "fraction_of_total_background": 0.0, "fraction_of_delayed": 0.0,
                            "support_flag": "ZERO_MC_SURVIVOR__NOT_ZERO_PHYSICAL_RATE",
                        }
                    )
        for row in material_rows:
            row.setdefault("support_flag", support_flag(int(row["selected_events"])))
        material_rows.sort(key=lambda row: (GEOMETRIES.index(row["geometry"]), -float(row["rate_cps"]), row["material_category"]))

        cross = aggregate(
            delayed,
            ("geometry", "family", "source_parent_ZA", "isotope_label", "half_life_s", "material_category"),
            total_by_geometry,
        )
        for row in cross:
            row["fraction_of_delayed"] = row["rate_cps"] / stream_total[(row["geometry"], "delayed")]
            row["support_flag"] = support_flag(int(row["selected_events"]))

        parent_top_other = []
        for geometry in GEOMETRIES:
            rows = [row for row in parent if row["geometry"] == geometry]
            top, other = rows[:10], rows[10:]
            for rank, row in enumerate(top, 1):
                parent_top_other.append({"rank_or_group": rank, **row, "support_flag": support_flag(int(row["selected_events"]))})
            if other:
                other_rate = math.fsum(float(row["rate_cps"]) for row in other)
                parent_top_other.append(
                    {
                        "rank_or_group": "other", "geometry": geometry, "source_parent_ZA": "",
                        "isotope_label": "other", "half_life_s": "",
                        "selected_events": sum(int(row["selected_events"]) for row in other),
                        "rate_cps": other_rate,
                        "rate_stat_sigma_cps": math.sqrt(math.fsum(float(row["rate_stat_sigma_cps"]) ** 2 for row in other)),
                        "fraction_of_total_background": other_rate / total_by_geometry[geometry],
                        "fraction_of_delayed": other_rate / stream_total[(geometry, "delayed")],
                        "support_flag": "AGGREGATED_OTHER",
                    }
                )

        mass_w2 = final_background[("Mass_model_511", "w2_510p58_511p42")]
        mass_reference = [
            {
                "component": "prompt", "mc_support_events": int(mass_w2["prompt_events"]),
                "rate_cps": float(mass_w2["prompt_rate_cps"]),
                "mc_counting_sigma_cps": float(mass_w2["prompt_stat_sigma_cps"]),
                "fraction_of_total_background": float(mass_w2["prompt_rate_cps"]) / float(mass_w2["total_background_rate_cps"]),
                "note": "weighted family sum; component-level intervals are in w2_stream_family_budget.csv",
            },
            {
                "component": "delayed_day15_transported_ground_state", "mc_support_events": int(mass_w2["delayed_events"]),
                "rate_cps": float(mass_w2["delayed_rate_cps"]),
                "mc_counting_sigma_cps": float(mass_w2["delayed_stat_sigma_cps"]),
                "fraction_of_total_background": float(mass_w2["delayed_rate_cps"]) / float(mass_w2["total_background_rate_cps"]),
                "note": "transport-counting MC only; source-position sampling is separate",
            },
            {
                "component": "total_background", "mc_support_events": int(mass_w2["prompt_events"]) + int(mass_w2["delayed_events"]),
                "rate_cps": float(mass_w2["total_background_rate_cps"]),
                "mc_counting_sigma_cps": float(mass_w2["total_background_stat_sigma_cps"]),
                "fraction_of_total_background": 1.0,
                "note": "support-event count is not a physical count; heterogeneous weights combined in quadrature",
            },
        ]

        comparison = []
        for window_id in ("broad_480_550", "w2_510p58_511p42"):
            mass_b = final_background[("Mass_model_511", window_id)]
            o8_b = final_background[("S3d_O8", window_id)]
            mass_s = final_signal[("Mass_model_511", window_id)]
            o8_s = final_signal[("S3d_O8", window_id)]
            bm = float(mass_b["total_background_rate_cps"])
            bo = float(o8_b["total_background_rate_cps"])
            sm = float(mass_b["total_background_stat_sigma_cps"])
            so = float(o8_b["total_background_stat_sigma_cps"])
            am = float(mass_s["selected_effective_area_cm2"])
            ao = float(o8_s["selected_effective_area_cm2"])
            ratio, ratio_sigma = ratio_with_independent_mc_sigma(bo, so, bm, sm)
            prompt_ratio, prompt_ratio_sigma = ratio_with_independent_mc_sigma(
                float(o8_b["prompt_rate_cps"]), float(o8_b["prompt_stat_sigma_cps"]),
                float(mass_b["prompt_rate_cps"]), float(mass_b["prompt_stat_sigma_cps"]),
            )
            delayed_ratio, delayed_ratio_sigma = ratio_with_independent_mc_sigma(
                float(o8_b["delayed_rate_cps"]), float(o8_b["delayed_stat_sigma_cps"]),
                float(mass_b["delayed_rate_cps"]), float(mass_b["delayed_stat_sigma_cps"]),
            )
            comparison.append(
                {
                    "scope": "day15_central_common_response_diagnostic",
                    "window_id": window_id,
                    "Mass_prompt_events": int(mass_b["prompt_events"]),
                    "Mass_prompt_cps": float(mass_b["prompt_rate_cps"]),
                    "S3d_O8_prompt_events": int(o8_b["prompt_events"]),
                    "S3d_O8_prompt_cps": float(o8_b["prompt_rate_cps"]),
                    "S3d_O8_over_Mass_prompt": prompt_ratio,
                    "S3d_O8_over_Mass_prompt_independent_mc_sigma_approx": prompt_ratio_sigma,
                    "prompt_evidence_flag": "LOW_MC_SUPPORT" if min(int(mass_b["prompt_events"]), int(o8_b["prompt_events"])) < 10 else "FINITE_MC_SUPPORT",
                    "Mass_delayed_events": int(mass_b["delayed_events"]),
                    "Mass_delayed_cps": float(mass_b["delayed_rate_cps"]),
                    "S3d_O8_delayed_events": int(o8_b["delayed_events"]),
                    "S3d_O8_delayed_cps": float(o8_b["delayed_rate_cps"]),
                    "S3d_O8_over_Mass_delayed": delayed_ratio,
                    "S3d_O8_over_Mass_delayed_independent_mc_sigma_approx": delayed_ratio_sigma,
                    "delayed_evidence_flag": "MC_COUNTING_ONLY__SOURCE_MIX_SYSTEMATIC_NOT_INCLUDED",
                    "Mass_background_cps": bm, "Mass_background_stat_sigma_cps": sm,
                    "S3d_O8_background_cps": bo, "S3d_O8_background_stat_sigma_cps": so,
                    "S3d_O8_over_Mass_background": ratio,
                    "S3d_O8_over_Mass_background_independent_mc_sigma_approx": ratio_sigma,
                    "central_background_reduction_fraction": 1.0 - ratio,
                    "Mass_selected_aeff_cm2": am, "S3d_O8_selected_aeff_cm2": ao,
                    "S3d_O8_over_Mass_selected_aeff": ao / am,
                    "central_signal_loss_fraction": 1.0 - ao / am,
                    "Mass_aeff_over_sqrt_background": am / math.sqrt(bm),
                    "S3d_O8_aeff_over_sqrt_background": ao / math.sqrt(bo),
                    "S3d_O8_over_Mass_background_limited_coefficient": (ao / math.sqrt(bo)) / (am / math.sqrt(bm)),
                    "coefficient_unit": "cm2/sqrt(cps)",
                    "interpretation": "detector-plane diagnostic only; mission time fold and source-mix/systematic intervals deferred",
                }
            )

        prompt_family = [row for row in family_budget if row["stream"] == "prompt"]
        write_csv(work / "w2_stream_family_budget.csv", family_budget)
        write_csv(work / "mass_reference_w2_budget.csv", mass_reference)
        write_csv(work / "w2_prompt_family_budget.csv", prompt_family)
        write_csv(work / "w2_delayed_family_breakdown.csv", delayed_family)
        write_csv(work / "w2_delayed_parent_breakdown.csv", parent)
        write_csv(work / "w2_delayed_parent_top10_plus_other.csv", parent_top_other)
        write_csv(work / "w2_delayed_material_breakdown.csv", material_rows)
        write_csv(work / "w2_delayed_volume_breakdown.csv", volume)
        write_csv(work / "w2_delayed_family_parent_material_supplement.csv", cross)
        write_csv(work / "matched_day15_comparison.csv", comparison)

        w2 = comparison[1]
        top_parent = {
            geometry: [row for row in parent if row["geometry"] == geometry][:10]
            for geometry in GEOMETRIES
        }
        summary = {
            "schema_version": 1,
            "status": "PASS__M05_CORRECTED_MATCHED_DAY15_COMPARISON__PROMOTION_DEFERRED",
            "w2": w2,
            "top_delayed_parents": top_parent,
            "selected_background_events": len(lineage),
            "input_status": {
                "common_response": common_summary["status"],
                "activation": activation_summary["status"],
            },
            "source_mix_boundary": "The stride-5 position-source mixture uncertainty is separate from event-count MC sigma.",
            "holdout_boundary": "S3d-O8 0.0998092689784 Bq known excited-state activity and unresolved rows are excluded from transported delayed rates.",
            "authority_boundary": "DAY15_MATCHED_COMPARISON_COMPLETE__NOT_MISSION_SIGNIFICANCE_SENSITIVITY_OR_GEOMETRY_PROMOTION_AUTHORITY",
        }
        (work / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = [
            "# Corrected-keV matched day-15 comparison", "", f"Status: `{summary['status']}`", "",
            "| Quantity (W2, measured, veto+Step05) | Mass_model_511 | S3d-O8 | O8/Mass |",
            "|---|---:|---:|---:|",
            f"| total background (cps) | {w2['Mass_background_cps']:.8g} | {w2['S3d_O8_background_cps']:.8g} | {w2['S3d_O8_over_Mass_background']:.6g} |",
            f"| selected effective area (cm²) | {w2['Mass_selected_aeff_cm2']:.8g} | {w2['S3d_O8_selected_aeff_cm2']:.8g} | {w2['S3d_O8_over_Mass_selected_aeff']:.6g} |",
            f"| Aeff/sqrt(B), central diagnostic | {w2['Mass_aeff_over_sqrt_background']:.8g} | {w2['S3d_O8_aeff_over_sqrt_background']:.8g} | {w2['S3d_O8_over_Mass_background_limited_coefficient']:.6g} |",
            "", "The central day-15 comparison is not a mission fold or a geometry-promotion decision. Source-position subsampling, state holdouts, optics systematics, and time evolution remain separate.", "",
        ]
        (work / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
        manifest = {
            "schema_version": 1, "status": summary["status"], "analysis_code": str(HERE.relative_to(ROOT)),
            "inputs": [
                str((COMMON / "summary.json").relative_to(ROOT)),
                str((ACTIVATION.parent / "day15_summary.json").relative_to(ROOT)),
                str(ACTIVATION.relative_to(ROOT)),
            ],
            "files": [{"path": str(path.relative_to(work)), "bytes": path.stat().st_size} for path in sorted(work.iterdir()) if path.is_file()],
            "hash_policy": "No large artifacts read or hashed; stage04/02 published tables only.",
        }
        (work / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.rename(work, output)
        print(f"{summary['status']}: {output}")
        return summary
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise


if __name__ == "__main__":
    run()
