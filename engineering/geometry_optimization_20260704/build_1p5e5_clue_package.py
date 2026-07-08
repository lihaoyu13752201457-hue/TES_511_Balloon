#!/usr/bin/env python3
"""Build a compact clue package for the 20-day 1.5e-5 optimization gap."""

from __future__ import annotations

import csv
import json
import math
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "engineering/geometry_optimization_20260704/07_clue_1p5e5_20260707"

STEP05_RATES = ROOT / "stepwise_maintenance/step05_veto_time_axis/outputs_geo_opt_s1_bpe_w5_fullstat_v1_l1/step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_rates.csv"
STEP08_SUMMARY = ROOT / "stepwise_maintenance/step08_significance/outputs_geo_opt_s1_bpe_w5_fullstat_v1/step08_geo_opt_s1_bpe_w5_fullstat_v1_time_dependent_summary.json"
PLASTIC_TAG = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_prompt_by_tag_comparison.csv"
PLASTIC_DIRECT = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/plastic_veto_on_off_direct_rate_comparison.csv"
NP_AUDIT = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/geo_opt_neutron_plastic_audit_summary.json"
ATM_SUMMARY = ROOT / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708/p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json"
GEOM_MANIFEST = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geo_opt_s1_bottomw_b4c_manifest.json"
GEOM_GEO = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo"
GEOM_MAT = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/geometry/Materials_DEMO2_DR_v3p5.geo"
GEOM_PNG = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c_2d_detail.png"
GEOM_WRL = ROOT / "engineering/geometry_optimization_20260704/01_geo_opt_s1_bottomw_b4c/figures/geo_opt_s1_bottomw_b4c.wrl"
NEUTRON_PNG = ROOT / "engineering/geometry_optimization_20260704/05_neutron_plastic_audit_20260707/figures/neutron_energy_depth_hexbin.png"

TARGET_F3 = 1.5e-5


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow(row)


def f3_from_total(current_f3: float, current_total: float, total: float) -> float:
    return current_f3 * math.sqrt(total / current_total)


def rate(rows: list[dict[str, str]], **match: str) -> float:
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            return float(row["rate_s-1"])
    raise KeyError(match)


def plastic_rate(rows: list[dict[str, str]], **match: str) -> float:
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            return float(row["plastic_on_rate_s-1"])
    raise KeyError(match)


def plastic_off_rate(rows: list[dict[str, str]], **match: str) -> float:
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            return float(row["plastic_off_rate_s-1"])
    raise KeyError(match)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    step05 = read_csv(STEP05_RATES)
    plastic_tag = read_csv(PLASTIC_TAG)
    direct = read_csv(PLASTIC_DIRECT)
    step08 = json.loads(STEP08_SUMMARY.read_text())
    np_audit = json.loads(NP_AUDIT.read_text())
    atm = json.loads(ATM_SUMMARY.read_text())
    manifest = json.loads(GEOM_MANIFEST.read_text())

    checks = step08["checks"]
    sidecar = atm["sidecar_included_nominal"]
    current_f3 = float(sidecar["F3_20d_new_ph_cm2_s"])
    current_total = float(sidecar["background_new_cps"])
    no_atm_total = rate(step05, window="w2_510p58_511p42", stream="prompt", stage="side_compton_fov_pass") + rate(
        step05, window="w2_510p58_511p42", stream="delayed", stage="side_compton_fov_pass"
    )
    eplus = plastic_rate(plastic_tag, window="w2_510p58_511p42", tag="eplus", stage="side_compton_fov_pass")
    neutron = plastic_rate(plastic_tag, window="w2_510p58_511p42", tag="n", stage="side_compton_fov_pass")
    delayed = rate(step05, window="w2_510p58_511p42", stream="delayed", stage="side_compton_fov_pass")
    atm511 = float(sidecar["atm511_added_cps"])
    target_total = current_total * (TARGET_F3 / current_f3) ** 2

    components = [
        {
            "component": "prompt_eplus_residual_after_current_plastic",
            "current_cps": eplus,
            "fraction_of_current_total": eplus / current_total,
            "evidence": "plastic_veto_on_off_prompt_by_tag_comparison.csv w2/eplus/side_compton_fov_pass",
            "tested_suppression": "current plastic reduces e+ W2 final from 0.0359890 to 0.0237663 cps (-33.96%)",
            "needed_for_1p5e5": "roughly >=94-95% additional rejection if atm511 and neutron are each reduced ~90%",
        },
        {
            "component": "prompt_neutron_residual",
            "current_cps": neutron,
            "fraction_of_current_total": neutron / current_total,
            "evidence": "plastic_veto_on_off_prompt_by_tag_comparison.csv w2/n/side_compton_fov_pass",
            "tested_suppression": "current plastic gives 0% extra W2 neutron rejection; activation audit shows ~25% internal activity reduction vs Mass",
            "needed_for_1p5e5": "roughly >=88-90% additional rejection if atm511 is reduced ~90% and e+ ~95%",
        },
        {
            "component": "atmospheric_511_sidecar_s1_nominal",
            "current_cps": atm511,
            "fraction_of_current_total": atm511 / current_total,
            "evidence": "p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json S1 nominal 4pi sidecar replay",
            "tested_suppression": "4pi sidecar includes upward albedo plus downward residual-atmosphere bins; active veto is not the primary handle for neutral 511 photons",
            "needed_for_1p5e5": "approximately >=90% rejection, likely via physical FoV/collimator/profile reconstruction, not scintillator skin",
        },
        {
            "component": "delayed_activation_residual",
            "current_cps": delayed,
            "fraction_of_current_total": delayed / current_total,
            "evidence": "step05_geo_opt_s1_bpe_w5_fullstat_v1_l1_rates.csv w2/delayed/side_compton_fov_pass",
            "tested_suppression": "internal activation -25.6% and CsI activity -29.6% vs Mass; delayed is a smaller term than e+/n/ATM511 in the current sidecar baseline",
            "needed_for_1p5e5": "not the first lever, but if prompt+atm are solved it becomes the floor",
        },
        {
            "component": "target_total_budget",
            "current_cps": target_total,
            "fraction_of_current_total": target_total / current_total,
            "evidence": "derived from F3 scaling at fixed signal acceptance",
            "tested_suppression": f"must reduce total background by {(1 - target_total / current_total) * 100:.2f}%",
            "needed_for_1p5e5": f"current total {current_total:.12g} cps -> target {target_total:.12g} cps",
        },
    ]

    scenario_defs = [
        ("current_with_s1_4pi_atm511_sidecar", eplus, neutron, delayed, atm511, "baseline after sidecar replay"),
        ("remove_atm511_only", eplus, neutron, delayed, 0.0, "tests value of perfect atmospheric line rejection alone"),
        ("remove_eplus_only", 0.0, neutron, delayed, atm511, "tests value of perfect residual e+ rejection alone"),
        ("remove_eplus_and_atm511", 0.0, neutron, delayed, 0.0, "still above 1.5e-5 because neutron+delayed remain"),
        ("remove_eplus_neutron_atm511", 0.0, 0.0, delayed, 0.0, "only this perfect prompt+atm removal beats target with current signal"),
        ("atm90_eplus95_neutron90", eplus * 0.05, neutron * 0.10, delayed, atm511 * 0.10, "minimal plausible algebraic target package; unverified"),
        ("atm100_eplus90_neutron80", eplus * 0.10, neutron * 0.20, delayed, 0.0, "near-miss package showing 90/80 is not enough"),
    ]
    budget_rows: list[dict[str, object]] = []
    for name, ep, nn, dd, aa, note in scenario_defs:
        total = ep + nn + dd + aa
        budget_rows.append(
            {
                "scenario": name,
                "eplus_cps": ep,
                "neutron_cps": nn,
                "delayed_cps": dd,
                "atm511_cps": aa,
                "total_cps": total,
                "projected_F3_20d": f3_from_total(current_f3, current_total, total),
                "meets_1p5e5": f3_from_total(current_f3, current_total, total) <= TARGET_F3,
                "note": note,
            }
        )

    lever_rows = [
        {
            "lever": "A. Physical atmospheric-511 FoV gate",
            "targets": "atmospheric_511_sidecar_s1_nominal",
            "current_evidence": "full 4pi sidecar transport: neutral 511 photons mostly need angular/FoV control; r3 analytic corrected-axis collimator rejected 101/101 but was not physically modeled",
            "needed_effect": ">=90% of the S1 nominal atmospheric line term",
            "why_it_may_work": "511 photons are neutral and not caught by plastic; only angular acceptance, coded aperture/profile likelihood, or a real detector-side collimator can reject them",
            "main_risk": "signal throughput/shadowing; current r3 axis result is axis-dependent and unvalidated",
            "next_validation": "build physical collimator/FoV geometry and replay both optics signal and atm511 unit flux",
        },
        {
            "lever": "B. Inner charged/annihilation veto for residual e+",
            "targets": "prompt_eplus_residual_after_current_plastic",
            "current_evidence": "outer plastic catches 19/62 W2 e+ TES-window events; 35 final e+ events remain at 0.023766 cps",
            "needed_effect": ">=94-95% of the remaining e+ rate",
            "why_it_may_work": "the residual e+ probably annihilate after entering/passive inner materials without depositing enough in outer plastic; veto must be closer to the passive stop/annihilation surfaces",
            "main_risk": "cryogenic/mechanical feasibility; added passive material can create new 511 sites; accidental veto rate",
            "next_validation": "event-origin audit for the 35 residual e+ W2 final events, then test active inner side/window/bottom liners or active segmented shell",
        },
        {
            "lever": "C. Thicker graded neutron moderator/capture system",
            "targets": "prompt_neutron_residual plus delayed_activation_residual",
            "current_evidence": "1 cm BPE-like envelope reduces internal activation ~25%; W2 neutron residual is 0.008821 cps; plastic gives no W2 neutron veto delta",
            "needed_effect": ">=88-90% of W2 neutron residual, plus further activation reduction if prompt+atm are solved",
            "why_it_may_work": "current neutron primary median is ~2.7 MeV and p90 ~7.7 MeV; 1 cm BPE is too thin for order-of-magnitude moderation",
            "main_risk": "mass/volume and capture-gamma production; BPE outside plastic would create passive e+ stopping unless active plastic remains outermost",
            "next_validation": "transport A/B of 3/5/10 cm active plastic or PE moderator plus inner B/Li capture layer, with capture-gamma scoring",
        },
        {
            "lever": "D. Event-topology/profile-likelihood reconstruction",
            "targets": "all non-focused backgrounds",
            "current_evidence": "current Step08 is counting only; no spatial/profile likelihood gain applied; r3 package assumed 1.28-1.40 full-recon gain only for 30d estimates",
            "needed_effect": "factor 2.72 in flux if used alone, or 1.3-1.5 as a multiplier after hardware rejection",
            "why_it_may_work": "focused signal has optics-constrained focal topology while atmospheric/charged/neutron events are less correlated",
            "main_risk": "must be proven with event-level position/topology; cannot be claimed from current counting summaries",
            "next_validation": "build final-event topology table and run likelihood cut on signal vs e+/n/atm511 final events",
        },
        {
            "lever": "E. Larger signal effective area/exposure",
            "targets": "sensitivity numerator rather than background",
            "current_evidence": "current signal at F0=1e-4 is ~0.0011846 cps; F3 target needs 2.72x more Z at current background",
            "needed_effect": "2.72x signal, or 148 days exposure at unchanged signal/background",
            "why_it_may_work": "mathematically straightforward but outside shield-only optimization",
            "main_risk": "not an answer to positron/neutron/atm511 exclusion",
            "next_validation": "only consider if detector/background route cannot reach required suppression",
        },
    ]

    geom_subset = {
        "source_manifest": str(GEOM_MANIFEST.relative_to(ROOT)),
        "geometry_setup": manifest["geometry_setup"],
        "geometry_file": manifest["geometry_file"],
        "wrl": manifest["wrl"],
        "detail_png": manifest["detail_png"],
        "current_revision": manifest["current_revision"],
        "total_added_mass_kg": manifest["total_added_mass_kg"],
        "patch_volumes": [
            {
                "name": v["name"],
                "material": v["material"],
                "mass_kg": v["mass_kg"],
                "active_detector_entry": v["active_detector_entry"],
                "role": v["role"],
                "shape": v["shape"],
                "position_cm": v["position_cm"],
            }
            for v in manifest["patch_volumes"]
        ],
    }

    event_rate = np_audit["plastic_veto"]["eplus_plastic_hits"]["event_rate_s-1"]
    event_rows = [
        {
            "topic": "eplus_w2_tes_window",
            "count_or_rate": np_audit["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]["counts"]["tes_window_events"],
            "value_cps": np_audit["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]["rates"]["tes_window_rate_s-1"],
            "clue": "62 W2 e+ TES-window events before active veto",
        },
        {
            "topic": "eplus_vetoed_only_by_plastic",
            "count_or_rate": np_audit["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]["counts"]["vetoed_only_when_plastic_is_active_events"],
            "value_cps": np_audit["plastic_veto"]["eplus_w2_matched_plastic_only_veto"]["rates"]["vetoed_only_when_plastic_is_active_rate_s-1"],
            "clue": "current plastic catches only a minority of W2 e+ candidates",
        },
        {
            "topic": "eplus_final_after_current_veto",
            "count_or_rate": round(eplus / event_rate),
            "value_cps": eplus,
            "clue": "residual dominant component; must be traced to passive stop/annihilation volumes",
        },
        {
            "topic": "neutron_final_w2",
            "count_or_rate": 13,
            "value_cps": neutron,
            "clue": "plastic on/off has no W2 neutron delta; CsI/active cuts already reduced raw neutron but residual remains",
        },
        {
            "topic": "atm511_w2_raw_active_final",
            "count_or_rate": f"{atm['windows']['w2_510p58_511p42']['raw_events']} raw / {atm['windows']['w2_510p58_511p42']['active_veto_pass_events']} active-pass / {atm['windows']['w2_510p58_511p42']['side_compton_fov_pass_events']} final",
            "value_cps": atm511,
            "clue": "neutral 511 background is mainly controlled by geometry/FoV, not active veto",
        },
        {
            "topic": "activation_internal_reduction",
            "count_or_rate": "geo vs Mass",
            "value_cps": np_audit["activation"]["summary"]["geo_internal_excluding_added_layers_Bq"] / np_audit["activation"]["summary"]["mass_internal_Bq"],
            "clue": "internal fixed activity is 74.4% of Mass, not an order-of-magnitude reduction",
        },
        {
            "topic": "neutron_primary_energy_depth",
            "count_or_rate": "median/p90",
            "value_cps": f"{np_audit['neutron_energy_depth']['summary']['geo']['sample_median_primary_energy_keV']} / {np_audit['neutron_energy_depth']['summary']['geo']['sample_p90_primary_energy_keV']} keV",
            "clue": "MeV neutrons imply 1 cm BPE is too thin for 10x suppression",
        },
    ]

    summary = {
        "status": "NO_VERIFIED_20D_1P5E_MINUS5_SCHEME_FOUND",
        "target": {"F3_20d_ph_cm2_s": TARGET_F3, "fixed_signal_assumption": True},
        "current_geo_opt_with_s1_4pi_atm511_sidecar": {
            "F3_20d_ph_cm2_s": current_f3,
            "background_cps": current_total,
            "background_target_cps_for_1p5e5": target_total,
            "required_total_background_reduction_fraction": 1.0 - target_total / current_total,
            "signal_counts_20d_at_F0_1e_4": checks["A_reference_w2_source_counts"],
            "background_counts_without_atm511_20d": checks["A_reference_w2_background_counts"],
        },
        "component_cps": {
            "eplus": eplus,
            "neutron": neutron,
            "delayed": delayed,
            "atm511_sidecar_s1_nominal": atm511,
            "sum": eplus + neutron + delayed + atm511,
        },
        "hard_requirement_if_delayed_unchanged": {
            "allowance_for_eplus_neutron_atm511_cps": target_total - delayed,
            "example_package_that_meets_target": "atm511 90% rejection + residual e+ 95% rejection + residual neutron 90% rejection",
            "example_package_F3": f3_from_total(current_f3, current_total, eplus * 0.05 + neutron * 0.10 + delayed + atm511 * 0.10),
        },
        "why_current_mods_are_insufficient": [
            "Plastic skin helps residual e+ but leaves 0.023766 cps, the largest term.",
            "BPE/W/plastic stack reduces activation only at ~25% level; W2 neutron final rate remains 0.008821 cps.",
            "Atmospheric 511 is now modeled as a 4pi sidecar at the Step06 day-15 environment; active veto is still not the primary handle.",
            f"Even perfect removal of e+ plus atm511 leaves neutron+delayed at projected F3 ~{f3_from_total(current_f3, current_total, neutron + delayed):.3g}.",
        ],
        "files_in_this_clue_package": [
            "README.md",
            "evidence_summary.json",
            "background_budget.csv",
            "optimization_levers.csv",
            "event_clues.csv",
            "geoopt_added_geometry_manifest.json",
            "geoopt_added_volumes.geo",
            "geo_opt_s1_bottomw_b4c_2d_detail.png",
            "geo_opt_s1_bottomw_b4c.wrl",
            "neutron_energy_depth_hexbin.png",
        ],
    }

    (OUT / "evidence_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    (OUT / "geoopt_added_geometry_manifest.json").write_text(json.dumps(geom_subset, indent=2, sort_keys=True) + "\n")
    write_csv(
        OUT / "background_budget.csv",
        components + budget_rows,
        [
            "component",
            "current_cps",
            "fraction_of_current_total",
            "evidence",
            "tested_suppression",
            "needed_for_1p5e5",
            "scenario",
            "eplus_cps",
            "neutron_cps",
            "delayed_cps",
            "atm511_cps",
            "total_cps",
            "projected_F3_20d",
            "meets_1p5e5",
            "note",
        ],
    )
    write_csv(
        OUT / "optimization_levers.csv",
        lever_rows,
        ["lever", "targets", "current_evidence", "needed_effect", "why_it_may_work", "main_risk", "next_validation"],
    )
    write_csv(OUT / "event_clues.csv", event_rows, ["topic", "count_or_rate", "value_cps", "clue"])

    material_lines: list[str] = []
    in_material = False
    for line in GEOM_MAT.read_text().splitlines():
        if line.startswith("Material PlasticScintillator") or line.startswith("Material BoratedPolyethylene5wtB"):
            in_material = True
        elif line.startswith("Material ") and in_material:
            in_material = False
        if in_material:
            material_lines.append(line)

    geo_lines = [line for line in GEOM_GEO.read_text().splitlines() if "GeoOpt_" in line]
    geo_text = [
        "# Extracted GeoOpt-added material and volume lines.",
        f"# Source material file: {GEOM_MAT.relative_to(ROOT)}",
        f"# Source geometry file: {GEOM_GEO.relative_to(ROOT)}",
        "",
        *material_lines,
        "",
        *geo_lines,
        "",
    ]
    (OUT / "geoopt_added_volumes.geo").write_text("\n".join(geo_text))

    shutil.copy2(GEOM_PNG, OUT / "geo_opt_s1_bottomw_b4c_2d_detail.png")
    shutil.copy2(GEOM_WRL, OUT / "geo_opt_s1_bottomw_b4c.wrl")
    shutil.copy2(NEUTRON_PNG, OUT / "neutron_energy_depth_hexbin.png")

    readme = f"""# 20-day 1.5e-5 Optimization Clue Package

Status: `NO_VERIFIED_20D_1P5E_MINUS5_SCHEME_FOUND`

This package is a compact handoff for external review. It uses the current
geo-opt S1/BPE/W5 branch plus the atmospheric-511 4pi sidecar replay, without promoting the
geometry or modifying the original Mass/511 geometry.

## Bottom line

Current S1 nominal 4pi ATM511-sidecar-included W2 performance is `{current_f3:.12g} ph cm^-2 s^-1`
at 20 days. At fixed signal acceptance, the requested `1.5e-5` requires total
background to fall from `{current_total:.12g} cps` to `{target_total:.12g} cps`,
an `{(1 - target_total / current_total) * 100:.2f}%` reduction.

Current W2 components:

- residual prompt e+: `{eplus:.12g} cps`
- residual prompt neutron: `{neutron:.12g} cps`
- delayed activation: `{delayed:.12g} cps`
- S1 nominal 4pi atmospheric 511 sidecar: `{atm511:.12g} cps`

The algebraic package that barely reaches the target is approximately:
atmospheric 511 rejection >=90%, residual e+ rejection >=95%, and residual
neutron rejection >=90%, with delayed activation unchanged. Current evidence
does not validate any of those three high-efficiency rejections.

## Interpretation

1. The current plastic skin is real and useful, but not enough. It reduces W2
   prompt e+ from `0.0359890` to `{eplus:.7g} cps`, leaving the dominant term.
2. The BPE/plastic/W stack reduces internal activation by about 25%, not by an
   order of magnitude. W2 neutron residual remains `{neutron:.7g} cps`.
3. Atmospheric 511 is modeled with the EXPACS-like 4pi sidecar at the Step06
   day-15 environment. It remains a geometry/FoV problem more than an active
   veto problem.
4. Perfectly removing e+ plus atmospheric 511 still leaves neutron+delayed at
   projected F3 ~`{f3_from_total(current_f3, current_total, neutron + delayed):.3g}`,
   so all three non-delayed components need simultaneous suppression.

## Files

- `evidence_summary.json`: machine-readable summary and required reductions.
- `background_budget.csv`: component rates plus scenario algebra.
- `optimization_levers.csv`: candidate levers, evidence level, risks, validation.
- `event_clues.csv`: compact event/count clues for e+, neutron, atm511.
- `geoopt_added_geometry_manifest.json`: added-volume manifest subset.
- `geoopt_added_volumes.geo`: extracted GeoOpt material/volume lines.
- `geo_opt_s1_bottomw_b4c_2d_detail.png`: 2D geometry detail.
- `geo_opt_s1_bottomw_b4c.wrl`: WRL visual geometry.
- `neutron_energy_depth_hexbin.png`: neutron energy/depth diagnostic.

## Source evidence outside this package

- Step05 rates: `{STEP05_RATES.relative_to(ROOT)}`
- Step08 summary: `{STEP08_SUMMARY.relative_to(ROOT)}`
- Neutron/plastic audit: `{NP_AUDIT.relative_to(ROOT)}`
- Atmospheric 511 replay: `{ATM_SUMMARY.relative_to(ROOT)}`
- Geometry manifest: `{GEOM_MANIFEST.relative_to(ROOT)}`
"""
    (OUT / "README.md").write_text(readme)

    files = sorted(p.name for p in OUT.iterdir() if p.is_file())
    print(json.dumps({"outdir": str(OUT.relative_to(ROOT)), "file_count": len(files), "files": files}, indent=2))


if __name__ == "__main__":
    main()
