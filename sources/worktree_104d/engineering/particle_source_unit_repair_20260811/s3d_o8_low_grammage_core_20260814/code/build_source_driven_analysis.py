#!/usr/bin/env python3
"""Build the reproducible, source-driven S3d-O8 optimization analysis.

This is post-processing only.  It streams the existing prompt truth table and
mission activity table, writes compact durable summaries, and evaluates two
explicit screening proxies for shrink-only geometry candidates.  It does not
run transport and does not promote a geometry.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
PACKAGE = Path(__file__).resolve().parents[1]
DATA = PACKAGE / "data"
ANALYSIS = PACKAGE / "analysis"
FIGURES = PACKAGE / "figures"

REANALYSIS = ROOT / (
    "engineering/particle_source_unit_repair_20260811/"
    "m05_corrected_reanalysis_20260813"
)
MISSION = REANALYSIS / "outputs/06_mission"
PROMPT_TRUTH_TMP = Path(
    "/tmp/s3d_o8_prompt_event_trace_20260813/"
    "s3d_o8_prompt_w2_and_broad_survivor_truth.csv"
)
PROMPT_DURABLE = DATA / "prompt_w2_event_summary.csv"
DELAYED_COORDS = DATA / "frozen_delayed_source_coordinates.csv"
DELAYED_BUDGET = DATA / "frozen_delayed_budget_by_volume.csv"
GEOMETRY_MANIFEST = DATA / "lc1_geometry_manifest.json"
SUMMARY = DATA / "source_driven_optimization_summary.json"

BASELINE_AEFF_CM2 = 15.041700000000004
FROZEN_AEFF_CM2 = 13.628520000000004
REFERENCE_FLUX = 1.0e-4
TARGET_F3 = 3.0e-5
FROZEN_PROMPT_CPS = 0.016921464065444387
FROZEN_DELAYED_CPS = 0.023205673996914644
FROZEN_DELAYED_SIGMA_CPS = 0.006687297298104163
FROZEN_PROMPT_COUNTS_20D = 27807.0882801

RING_CENTERS_CM = {1: -2.65, 2: -1.45, 3: -0.25, 4: 0.95, 5: 2.15}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def truth(value: str) -> bool:
    return value.lower() in {"1", "true", "yes"}


def world_to_if(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    """World -> InstrumentFrame for InstrumentFrame = World Ry(+45 deg)."""
    x, y, z = vector
    c = math.sqrt(0.5)
    return (c * (x - z), y, c * (x + z))


def prompt_summary() -> dict:
    fields = [
        "family", "local_event_id", "event_weight_cps", "measured_total_keV",
        "measured_multiplicity", "bgo_keV_raw_sum", "plastic_keV_raw_sum",
        "pass_veto50", "step05_pass", "step05_class", "init_energy_keV",
        "init_x_cm", "init_y_cm", "init_z_cm", "init_dir_x", "init_dir_y",
        "init_dir_z", "if_dir_x", "if_dir_y", "if_dir_z",
        "if_theta_from_plus_x_deg", "if_azimuth_about_x_deg",
        "first_key_ia_process", "relevant_pair_volume", "path_type",
        "source_file",
    ]
    if PROMPT_TRUTH_TMP.exists():
        rows = []
        with PROMPT_TRUTH_TMP.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if not truth(row["in_w2_pre"]):
                    continue
                direction = world_to_if(tuple(float(row[k]) for k in (
                    "init_dir_x", "init_dir_y", "init_dir_z"
                )))
                dx, dy, dz = direction
                theta = math.degrees(math.acos(max(-1.0, min(1.0, dx))))
                azimuth = math.degrees(math.atan2(dz, dy)) % 360.0
                out = {key: row.get(key, "") for key in fields}
                out.update({
                    "if_dir_x": dx,
                    "if_dir_y": dy,
                    "if_dir_z": dz,
                    "if_theta_from_plus_x_deg": theta,
                    "if_azimuth_about_x_deg": azimuth,
                })
                rows.append(out)
        with PROMPT_DURABLE.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    else:
        with PROMPT_DURABLE.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

    family_counts = defaultdict(int)
    family_veto_pass = defaultdict(int)
    gamma_theta = {(0, 45): [0, 0], (45, 90): [0, 0], (90, 135): [0, 0], (135, 180): [0, 0]}
    gamma_energy = {(0, 2000): [0, 0], (2000, 4000): [0, 0], (4000, 6000): [0, 0],
                    (6000, 10000): [0, 0], (10000, float("inf")): [0, 0]}
    survivors = []
    for row in rows:
        family = row["family"]
        passed = truth(str(row["pass_veto50"]))
        family_counts[family] += 1
        family_veto_pass[family] += int(passed)
        if family == "gamma":
            theta = float(row["if_theta_from_plus_x_deg"])
            energy = float(row["init_energy_keV"])
            for bounds, count in gamma_theta.items():
                if bounds[0] <= theta <= bounds[1] if bounds[1] == 180 else bounds[0] <= theta < bounds[1]:
                    count[0] += 1
                    count[1] += int(passed)
                    break
            for bounds, count in gamma_energy.items():
                if bounds[0] <= energy < bounds[1]:
                    count[0] += 1
                    count[1] += int(passed)
                    break
        if passed:
            survivors.append({
                "local_event_id": int(row["local_event_id"]),
                "energy_keV": float(row["init_energy_keV"]),
                "theta_from_plus_x_deg": float(row["if_theta_from_plus_x_deg"]),
                "azimuth_about_x_deg": float(row["if_azimuth_about_x_deg"]),
                "pair_host": row["relevant_pair_volume"],
                "step05_pass": truth(str(row["step05_pass"])),
                "bgo_keV": float(row["bgo_keV_raw_sum"]),
                "plastic_keV": float(row["plastic_keV_raw_sum"]),
            })
    return {
        "w2_pre_veto_events": len(rows),
        "family_counts": dict(sorted(family_counts.items())),
        "family_veto50_pass": dict(sorted(family_veto_pass.items())),
        "veto50_rejected": len(rows) - len(survivors),
        "veto50_survivors": survivors,
        "gamma_w2_pre_veto_direction_bins": [
            {"theta_lo_deg": lo, "theta_hi_deg": hi, "events": value[0], "veto50_survivors": value[1]}
            for (lo, hi), value in gamma_theta.items()
        ],
        "gamma_w2_pre_veto_energy_bins_keV": [
            {"energy_lo_keV": lo, "energy_hi_keV": None if math.isinf(hi) else hi,
             "events": value[0], "veto50_survivors": value[1]}
            for (lo, hi), value in gamma_energy.items()
        ],
        "direction_scope": (
            "Directions are for gamma events already selected into measured W2 before veto; "
            "they are not a denominator-complete incident angular distribution."
        ),
    }


def write_prompt_rays() -> Path:
    # Exact ray lengths come from the baseline geometry membership audit.
    rows = [
        {
            "local_event_id": 3883, "frozen_pass": False, "energy_keV": 4148.29,
            "entry_class": "bottom_oblique", "theta_from_plus_x_deg": 82.220,
            "plastic_path_cm": 1.049, "bpe_path_cm": 2.099, "al_mech_path_cm": 0.315,
            "bgo_path_cm": 3.148, "outer_w_path_cm": 0.199,
            "pair_host": "Nb_MagShield_Inner_Cylinder_2mm",
            "mechanism": "uncollided gamma; pair in inner Nb; annihilation near MuMetal; single 511 gamma to TES",
        },
        {
            "local_event_id": 19932, "frozen_pass": True, "energy_keV": 5768.82,
            "entry_class": "plus_x_plus_z_oblique_side", "theta_from_plus_x_deg": 135.231,
            "plastic_path_cm": 1.323, "bpe_path_cm": 2.645, "al_mech_path_cm": 0.397,
            "bgo_path_cm": 5.290, "outer_w_path_cm": 0.0,
            "pair_host": "DR_MixingChamber_Cu",
            "mechanism": "uncollided gamma; pair/annihilation in mixing-chamber Cu; single 511 gamma to TES",
        },
        {
            "local_event_id": 8081, "frozen_pass": False, "energy_keV": 6345.94,
            "entry_class": "plus_x_minus_y_oblique_side", "theta_from_plus_x_deg": 144.795,
            "plastic_path_cm": 1.011, "bpe_path_cm": 2.022, "al_mech_path_cm": 0.303,
            "bgo_path_cm": 4.044, "outer_w_path_cm": 0.0,
            "pair_host": "Nb_MagShield_Inner_Cylinder_2mm",
            "mechanism": "uncollided gamma; pair in inner Nb; annihilation after positron migration; Step05 rejects",
        },
    ]
    out = DATA / "prompt_veto_leak_ray_paths.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return out


def load_delayed() -> list[dict]:
    with DELAYED_COORDS.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["weight"] = float(row["event_weight_cps"])
        row["radius"] = float(row["component_r_cm"])
        row["axial"] = float(row["component_axial_cm"])
    return rows


def coordinate_keep(row: dict, *, thin_mxc: bool) -> bool:
    volume, radius, axial = row["source_volume"], row["radius"], row["axial"]
    if volume == "ColdPlate_MXC_50mK_SD_anchor":
        return radius <= 12.0 and (not thin_mxc or axial <= 0.0)
    if volume == "Cu_50mK_StillLike_Can_bottom_cap_2mm":
        return axial >= 0.0
    if volume == "Cu_SubstrateSupport_SolidDisk_L0_deepest":
        return abs(axial) <= 0.075
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L"):
        layer = int(volume.split("_L", 1)[1].split("_", 1)[0])
        return abs(axial - RING_CENTERS_CM[layer]) <= 0.075
    if volume == "Nb_MagShield_Inner_Cylinder_2mm":
        return radius <= 4.05
    return True


def mass_fraction(row: dict, *, thin_mxc: bool) -> float:
    volume = row["source_volume"]
    fractions = {
        "ColdPlate_MXC_50mK_SD_anchor": (12.0 / 15.0) ** 2,
        "Cu_50mK_StillLike_Can_bottom_cap_2mm": 0.5,
        "DR_MixingChamber_Cu": (1.8 / 2.2) ** 2 * (0.6 / 1.8),
        "Cu_SubstrateSupport_SolidDisk_L0_deepest": 1.5 / 3.5,
        "Nb_MagShield_Inner_Cylinder_2mm": (4.05**2 - 4.0**2) / (4.2**2 - 4.0**2),
    }
    if volume.startswith("Cu_SubstrateSupport_OpenRing_L"):
        value = 0.5
    else:
        value = fractions.get(volume, 1.0)
    if thin_mxc and volume == "ColdPlate_MXC_50mK_SD_anchor":
        value *= 0.5
    return value


def proxy_multipliers(rows: list[dict]) -> dict[str, list[float]]:
    return {
        "frozen_reference": [1.0 for _ in rows],
        "LC1_CuNb_event_coordinate_excision": [float(coordinate_keep(r, thin_mxc=False)) for r in rows],
        "LC1_CuNb_uniform_activity_mass": [mass_fraction(r, thin_mxc=False) for r in rows],
        "LC2_CuNb_MXC3mm_event_coordinate_excision": [float(coordinate_keep(r, thin_mxc=True)) for r in rows],
        "LC2_CuNb_MXC3mm_uniform_activity_mass": [mass_fraction(r, thin_mxc=True) for r in rows],
    }


def mission_fold(rows: list[dict], multipliers: dict[str, list[float]]) -> dict:
    timeline = []
    with (MISSION / "mission_timeline.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["geometry"] == "S3d_O8":
                timeline.append(row)
    time_ids = {row["time_bin_id"] for row in timeline}
    selected_keys = {(row["family"], row["source_parent_ZA"]) for row in rows}
    scales = {}
    with (MISSION / "family_parent_activity_by_time.csv").open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["geometry"] != "S3d_O8" or row["time_bin_id"] not in time_ids:
                continue
            key = (row["incident_family"], row["source_parent_ZA"])
            if key in selected_keys:
                scales[(row["time_bin_id"], *key)] = float(
                    row["activity_scale_to_constant_environment_day15_inventory"]
                )

    folded = {name: 0.0 for name in multipliers}
    for time in timeline:
        tid = time["time_bin_id"]
        live_weight = float(time["accidental_live_factor"]) * float(time["trajectory_quadrature_weight_s"])
        for name, factors in multipliers.items():
            delayed_cps = 0.0
            for row, factor in zip(rows, factors):
                scale = scales.get((tid, row["family"], row["source_parent_ZA"]), 0.0)
                delayed_cps += row["weight"] * factor * scale
            folded[name] += delayed_cps * live_weight

    mission_summary = json.loads((MISSION / "summary.json").read_text(encoding="utf-8"))
    baseline_source_counts = mission_summary["geometries"]["S3d_O8"]["source_counts_20d"]
    signal_counts = baseline_source_counts * FROZEN_AEFF_CM2 / BASELINE_AEFF_CM2
    target_background_counts = (signal_counts * TARGET_F3 / (3.0 * REFERENCE_FLUX)) ** 2
    # Preserve the already frozen common-scenario prompt fold.  The candidate
    # proxies do not contain a denominator-complete prompt transport from which
    # to redefine that scalar.  A candidate full chain must replace it.
    prompt_counts = FROZEN_PROMPT_COUNTS_20D
    out = {}
    for name, delayed_counts in folded.items():
        total_current_prompt = delayed_counts + prompt_counts
        f3_current = 3.0 * REFERENCE_FLUX * math.sqrt(total_current_prompt) / signal_counts
        f3_zero_prompt = 3.0 * REFERENCE_FLUX * math.sqrt(delayed_counts) / signal_counts
        prompt_only_feasible = delayed_counts <= target_background_counts
        if prompt_only_feasible:
            allowed_prompt = target_background_counts - delayed_counts
            required_suppression = max(0.0, 1.0 - allowed_prompt / prompt_counts)
            additional_delayed_reduction = 0.0
        else:
            allowed_prompt = None
            required_suppression = None
            additional_delayed_reduction = (
                (delayed_counts - target_background_counts) / delayed_counts
            )
        out[name] = {
            "delayed_counts_20d": delayed_counts,
            "prompt_counts_20d_if_current": prompt_counts,
            "total_counts_20d_if_current_prompt": total_current_prompt,
            "f3_if_current_prompt": f3_current,
            "f3_if_zero_prompt": f3_zero_prompt,
            "allowed_prompt_counts_20d_for_target": allowed_prompt,
            "required_prompt_suppression_fraction_for_target": required_suppression,
            "target_feasible_by_prompt_suppression_only": prompt_only_feasible,
            "additional_delayed_reduction_required_fraction_if_zero_prompt": (
                additional_delayed_reduction
            ),
            "target_crossed_if_zero_prompt": prompt_only_feasible,
        }
    return {
        "signal_counts_20d": signal_counts,
        "target_background_counts_20d": target_background_counts,
        "target_f3": TARGET_F3,
        "reference_flux_ph_cm2_s": REFERENCE_FLUX,
        "proxies": out,
        "boundary": (
            "The family-parent activity/time fold is exact for the retained event weights and original mission scenario. "
            "Every candidate proxy conditionally preserves the frozen signal S20/Aeff and the pre-existing "
            "frozen-scenario 20-day prompt scalar. Candidate retention factors are screening proxies, not new "
            "focused-signal, prompt, activation, delayed-transport, or common-response closure."
        ),
    }


def aggregate_delayed(rows: list[dict]) -> dict:
    output = {}
    for label, key in (
        ("family", "family"), ("parent_ZA", "source_parent_ZA"), ("volume", "source_volume")
    ):
        groups = defaultdict(lambda: {"rate": 0.0, "sumw2": 0.0, "events": 0})
        for row in rows:
            value = groups[row[key]]
            value["rate"] += row["weight"]
            value["sumw2"] += row["weight"] ** 2
            value["events"] += 1
        output[label] = [
            {
                "key": name,
                "events": value["events"],
                "rate_cps": value["rate"],
                "mc_sigma_cps": math.sqrt(value["sumw2"]),
                "mc_neff": value["rate"] ** 2 / value["sumw2"] if value["sumw2"] else 0.0,
            }
            for name, value in sorted(groups.items(), key=lambda item: -item[1]["rate"])
        ]
    return output


def plot(summary: dict) -> Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.0), constrained_layout=True)
    volumes = summary["delayed_origin"]["volume"][:8]
    labels = [row["key"].replace("Cu_SubstrateSupport_", "").replace("ColdPlate_", "") for row in volumes]
    values = [row["rate_cps"] for row in volumes]
    errors = [row["mc_sigma_cps"] for row in volumes]
    y = list(range(len(labels)))
    axes[0].barh(y, values, xerr=errors, color="#4477AA", alpha=0.9, capsize=2)
    axes[0].set_yticks(y, labels, fontsize=8)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Frozen delayed W2 rate (cps)")
    axes[0].set_title("Detector-selected activation sources")
    axes[0].grid(axis="x", alpha=0.25)

    mission = summary["mission_gate"]
    names = [
        "frozen_reference",
        "LC1_CuNb_event_coordinate_excision",
        "LC1_CuNb_uniform_activity_mass",
        "LC2_CuNb_MXC3mm_event_coordinate_excision",
        "LC2_CuNb_MXC3mm_uniform_activity_mass",
    ]
    short = ["Frozen", "LC1 coord", "LC1 mass", "LC2 coord", "LC2 mass"]
    delayed = [mission["proxies"][name]["delayed_counts_20d"] for name in names]
    prompt = [mission["proxies"][name]["prompt_counts_20d_if_current"] for name in names]
    x = list(range(len(names)))
    axes[1].bar(x, delayed, label="delayed proxy", color="#228833")
    axes[1].bar(x, prompt, bottom=delayed, label="current prompt", color="#CC6677")
    axes[1].axhline(mission["target_background_counts_20d"], color="black", ls="--", lw=1.2,
                    label="F3 target count gate")
    axes[1].set_xticks(x, short, rotation=25, ha="right")
    axes[1].set_ylabel("20-day background counts")
    axes[1].set_title("Mission gate: proxy, not transport authority")
    axes[1].legend(fontsize=8)
    axes[1].grid(axis="y", alpha=0.25)
    out = FIGURES / "source_budget_and_candidate_gate.png"
    fig.savefig(out, dpi=180)
    plt.close(fig)
    return out


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    prompt = prompt_summary()
    ray_path = write_prompt_rays()
    delayed_rows = load_delayed()
    multipliers = proxy_multipliers(delayed_rows)
    constant_day15 = {
        name: {
            "delayed_rate_cps": sum(r["weight"] * f for r, f in zip(delayed_rows, factors)),
            "mc_sigma_cps_from_retained_weight_factors": math.sqrt(sum((r["weight"] * f) ** 2 for r, f in zip(delayed_rows, factors))),
            "mc_neff": (
                sum(r["weight"] * f for r, f in zip(delayed_rows, factors)) ** 2
                / sum((r["weight"] * f) ** 2 for r, f in zip(delayed_rows, factors))
            ),
        }
        for name, factors in multipliers.items()
    }
    manifest = json.loads(GEOMETRY_MANIFEST.read_text(encoding="utf-8"))
    summary = {
        "schema_version": 1,
        "status": "SOURCE_DIAGNOSIS_AND_SCREENING_COMPLETE__NO_GEOMETRY_PROMOTION_AUTHORITY",
        "geometry": "S3d_O8",
        "baseline": {
            "aeff_cm2": BASELINE_AEFF_CM2,
            "prompt_cps": 0.03384292813088877,
            "delayed_cps": 0.054479752227267225,
            "total_cps": 0.08832268035815599,
            "mission_f3": 6.923750509150677e-5,
        },
        "frozen_selection": {
            "aeff_cm2": FROZEN_AEFF_CM2,
            "prompt_cps": FROZEN_PROMPT_CPS,
            "delayed_cps": FROZEN_DELAYED_CPS,
            "delayed_mc_sigma_cps": FROZEN_DELAYED_SIGMA_CPS,
            "total_cps": FROZEN_PROMPT_CPS + FROZEN_DELAYED_CPS,
            "mission_f3": 5.14899369e-5,
        },
        "prompt_origin": prompt,
        "prompt_ray_path_csv": {"path": str(ray_path.relative_to(ROOT)), "sha256": sha256(ray_path)},
        "prompt_mechanism": (
            "All three W2 veto leaks are 4.15-6.35 MeV primary gamma pair/annihilation chains. "
            "Each crosses the existing active shield with exactly zero recorded BGO/plastic energy; "
            "the pair target is internal Cu or Nb.  The evidence does not identify an aperture leak."
        ),
        "delayed_origin": aggregate_delayed(delayed_rows),
        "constant_environment_day15_proxies": constant_day15,
        "mission_gate": mission_fold(delayed_rows, multipliers),
        "candidate_mass_kg": {
            key: value for key, value in manifest["mass_model"].items()
            if key.endswith("total_kg")
        },
        "candidate_interpretation": {
            "event_coordinate_excision": (
                "Set contributions from selected historical source points outside the reduced shape to zero and retain all others. "
                "This is an unchanged-coupling empirical replay, not a physical lower or upper bound."
            ),
            "uniform_activity_mass": (
                "Scale each affected historical source contribution by analytic remaining material fraction. "
                "This assumes uniform activation and unchanged detector coupling and is not a confidence bound."
            ),
        },
        "recommended_route": [
            "Keep the current 4 cm side / 3 cm bottom BGO as the reference shield; do not treat threshold lowering or gap patching as the solution.",
            "First reconcile the real near-TES bill of materials, especially the SilverSinterProxy density and mass.",
            "Screen a system-level low-grammage core: 3 mm MXC plate with preserved interface, 1 mm can bottom, thinner Cu supports, and reduced mixing-chamber Cu.",
            "Treat Nb 2 -> 1 mm as a conditional engineering candidate; retain 0.5 mm only as a sensitivity/stress extreme. Both require magnetic FEM and cold field/noise tests.",
            "Only after the source angular distribution is statistically resolved consider a local external BGO sector; whole-shell thickening and added high-Z passive material are low priority.",
            "Use BPE/H+B changes only after a dedicated neutron-current/activation fold demonstrates net benefit under the mass budget.",
        ],
        "claim_boundaries": [
            "Prompt final support is two events; the frozen prompt is one event.",
            "Frozen delayed support is 135 rows but has low weighted effective sample size and is dominated by n and p high-weight rows.",
            "The LC1/LC2 candidate projections do not include new BUILDUP, inventory, delayed transport, or common-response closure.",
            "Candidate F3 and prompt-suppression budgets conditionally preserve frozen S20=1490.80222983 counts, Aeff=13.62852 cm2, and current prompt=27807.0882801 counts; candidate focused-signal closure has not been run.",
            "Thermal, structural, magnetic, service-routing, and real-material BOM adequacy are outside the transport model.",
        ],
        "inputs": {
            "prompt_w2_summary": {"path": str(PROMPT_DURABLE.relative_to(ROOT)), "sha256": sha256(PROMPT_DURABLE)},
            "delayed_source_coordinates": {"path": str(DELAYED_COORDS.relative_to(ROOT)), "sha256": sha256(DELAYED_COORDS)},
            "delayed_budget_by_volume": {"path": str(DELAYED_BUDGET.relative_to(ROOT)), "sha256": sha256(DELAYED_BUDGET)},
            "mission_timeline": {"path": str((MISSION / "mission_timeline.csv").relative_to(ROOT)), "sha256": sha256(MISSION / "mission_timeline.csv")},
            "family_parent_activity": {"path": str((MISSION / "family_parent_activity_by_time.csv").relative_to(ROOT)), "sha256": sha256(MISSION / "family_parent_activity_by_time.csv")},
            "geometry_manifest": {"path": str(GEOMETRY_MANIFEST.relative_to(ROOT)), "sha256": sha256(GEOMETRY_MANIFEST)},
        },
    }
    figure = plot(summary)
    summary["figure"] = {"path": str(figure.relative_to(ROOT)), "sha256": sha256(figure)}
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(SUMMARY)


if __name__ == "__main__":
    main()
